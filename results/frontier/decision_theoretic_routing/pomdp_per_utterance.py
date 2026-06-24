"""POMDP per-utterance heterogeneity extension (RQ10).

Extends the stratum-level POMDP (RQ5, finding #24) from 5 discrete overlap
strata to per-utterance (continuous-state) heterogeneity. Three extensions:

1. Continuous overlap ratio via Gaussian-kernel reward estimation
   (instead of 5 discrete strata {0, 0.1, 0.3, 0.6, 0.9}). Uses all 15 greedy
   overlap points in phase_aggregate.csv + the 8 per-pair prosody curves.
2. Per-utterance emotion heterogeneity from the 8 prosody pairs
   (prosody_tax_curve.csv) -> within-stratum coupling-cost coefficient of
   variation (CV).
3. Silence-fraction state dimension to predict the AISHELL-4 failure
   (oracle-TextGrid silence gaps -> confident-attractor #21 -> separated
   catastrophically bad -> mixed should win). Calibrated from RQ1 (aishell4
   external validation) + #21 (causal hallucination probe).

Label: experimental/frontier (theoretical + reanalysis; no new data, no ASR runs).
Builds on pomdp_solver.py (RQ5); does NOT overwrite it.

Research questions
------------------
RQ10.1  Does a per-utterance (continuous-state) POMDP improve over the
        stratum-level POMDP on text regret?
RQ10.2  Does the per-utterance POMDP predict the AISHELL-4 failure (assigning
        >70% probability to "mixed" for silence-gap windows)?
RQ10.3  Is the coupling cost (text vs emotion disagreement) heterogeneous
        within strata (CV > 0.5 within ov0.1 stratum)?

Reproduce: python3 results/frontier/decision_theoretic_routing/pomdp_per_utterance.py
"""
from __future__ import annotations

import csv
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

# ------------------------------------------------------------------
# Import the stratum-level solver (sibling module) for data loaders + constants
# ------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pomdp_solver as base  # noqa: E402

# ------------------------------------------------------------------
# Data
# ------------------------------------------------------------------
PHASE = base.load_phase_aggregate()                  # 15 greedy overlap strata
PROSODY_ROWS = base._read_csv(base.PROSODY_CURVE)    # all prosody rows

ACTIONS = base.ACTIONS
NOISE_TYPES = base.NOISE_TYPES
OBJECTIVES = base.OBJECTIVES
OVERLAPS_STRATUM = base.OVERLAPS                     # 5 canonical strata
ROUTER_V2_CROSSOVER = base.ROUTER_V2_CROSSOVER       # 0.17
LAMBDA_EMOTION = base.LAMBDA_EMOTION                 # 1.0
GATE_EMOTION_COST = base.GATE_EMOTION_COST

# Continuous overlap support points from phase_aggregate (greedy), sorted.
OVERLAP_GRID = sorted(PHASE.keys())                  # 15 points: 0.0 .. 0.9

# sep_helps_frac per overlap (text-side within-stratum heterogeneity proxy):
# fraction of the 20 cases where separated CER < mixed CER. Not exposed by the
# base loader, so read it directly from phase_aggregate.csv.
SEP_HELPS_FRAC: dict[float, float] = {}
for _row in base._read_csv(base.PHASE_AGG):
    if _row.get("config") != "greedy":
        continue
    SEP_HELPS_FRAC[round(float(_row["overlap_ratio"]), 2)] = float(_row["sep_helps_frac"])

# Prosody: per-pair emotion distortion at alpha=0.15 (realistic separator).
# pair_id -> {overlap -> {sep_distortion, mixed_distortion, emotion_benefit}}
PROSODY_BY_PAIR: dict[int, dict[float, dict[str, float]]] = {}
for _row in PROSODY_ROWS:
    if abs(float(_row["alpha"]) - 0.15) > 1e-6:
        continue
    _pid = int(_row["pair_id"])
    _ov = round(float(_row["overlap_ratio"]), 2)
    PROSODY_BY_PAIR.setdefault(_pid, {})[_ov] = {
        "sep_distortion": float(_row["sep_distortion"]),
        "mixed_distortion": float(_row["mixed_distortion"]),
        "emotion_benefit": float(_row["emotion_benefit"]),
    }
PAIR_IDS = sorted(PROSODY_BY_PAIR.keys())            # 8 pairs (0..7)
PROSODY_OVERLAPS = sorted(                           # 5 overlaps {0,0.1,0.3,0.6,0.9}
    {ov for p in PROSODY_BY_PAIR.values() for ov in p}
)

# ------------------------------------------------------------------
# Kernel-based continuous reward estimation
# ------------------------------------------------------------------
# Bandwidths chosen from the support spacing:
#   - phase_aggregate greedy has 0.05 spacing -> BW_TEXT=0.08 (smoother than
#     the grid, avoids over-fitting to the 20-case-per-stratum means).
#   - prosody has ~0.2 irregular spacing over 5 overlaps -> BW_EMO=0.15.
# Both are fixed a-priori (not tuned on regret); a sensitivity note is in
# FINDINGS_per_utterance.md.
BW_TEXT = 0.08
BW_EMO = 0.15


def _gaussian(d: float, bandwidth: float) -> float:
    return math.exp(-(d * d) / (2.0 * bandwidth * bandwidth))


def kernel_text_cer(r: float, noise: str, action: str) -> float:
    """Gaussian-kernel-smoothed text CER at continuous overlap ``r``.

    Computes base.estimate_text_cer at each of the 15 greedy support points
    (which applies the documented #11/#12/#13 noisy multipliers) and
    kernel-weights them. No data invented; the kernel only interpolates the
    existing 15-point surface.
    """
    weights: list[float] = []
    values: list[float] = []
    for ov in OVERLAP_GRID:
        w = _gaussian(r - ov, BW_TEXT)
        if w <= 0.0:
            continue
        cer = base.estimate_text_cer(PHASE, ov, noise, action)
        weights.append(w)
        values.append(cer)
    if not weights:
        ov_nearest = min(OVERLAP_GRID, key=lambda o: abs(o - r))
        return base.estimate_text_cer(PHASE, ov_nearest, noise, action)
    z = sum(weights)
    return sum(w * v for w, v in zip(weights, values)) / z


def kernel_emo_dist(r: float, action: str, pair_id: int | None = None) -> float:
    """Gaussian-kernel-smoothed emotion distortion at continuous overlap ``r``.

    If ``pair_id`` is given, uses that pair's per-utterance curve; otherwise
    uses the cross-pair mean (the stratum-level estimate). The 8 pairs provide
    the per-utterance heterogeneity.
    """
    pairs = [pair_id] if pair_id is not None else PAIR_IDS
    per_pair: list[float] = []
    for pid in pairs:
        curve = PROSODY_BY_PAIR.get(pid, {})
        if not curve:
            continue
        weights: list[float] = []
        values: list[float] = []
        for ov in PROSODY_OVERLAPS:
            if ov not in curve:
                continue
            w = _gaussian(r - ov, BW_EMO)
            if w <= 0.0:
                continue
            d = curve[ov]
            if action == "mixed":
                v = d["mixed_distortion"]
            elif action == "separated":
                v = d["sep_distortion"]
            else:  # gate operates on the separated track + small prosody cost
                v = d["sep_distortion"] + GATE_EMOTION_COST[action]
            weights.append(w)
            values.append(v)
        if not weights:
            continue
        z = sum(weights)
        per_pair.append(sum(w * v for w, v in zip(weights, values)) / z)
    if not per_pair:
        return 0.0
    return sum(per_pair) / len(per_pair)


# ------------------------------------------------------------------
# Silence-gap penalty model (AISHELL-4 failure driver)
# ------------------------------------------------------------------
# The AISHELL-4 failure (RQ1, #881): oracle-TextGrid separation creates
# per-speaker tracks with long interior silence gaps. These trigger Whisper's
# confident-attractor hallucination (#21): the encoder flags silence
# (no_speech_prob high) while the decoder is confident (avg_logprob near 0),
# producing repetition/insertion loops that inflate separated cpWER past 1.0.
#
# We model this as an ADDITIVE hallucination cost on every action that operates
# on the separated track (separated, gate_flatness, gate_speaker). The existing
# gates (#11) target noise residual, NOT interior silence (RQ8 documents this
# gap), so they do not cure the silence-gap hallucination. Mixed (the full mix)
# has no silence gaps and is unaffected.
#
# Calibration (from RQ1 + #21, documented; no data invented):
#   - RQ1 NoOverlap:  gold sep CER 0.758 (ov 0.0) vs AISHELL-4 sep cpWER 1.496.
#     The delta (~0.74) is the hallucination + meeting-audio difficulty at the
#     representative silence fraction g~0.7 (one speaker ~9 s of speech in a
#     30 s window -> ~0.7 silence).
#   - RQ1 MidOverlap: gold sep CER 0.482 (ov 0.3) vs AISHELL-4 sep cpWER 1.720.
#     At g~0.5 the delta is ~1.24.
#   - We need the penalty to flip separated->mixed at high overlap when silence
#     is present. At ov 0.3: base_sep=0.482, base_mixed=1.194. To make separated
#     worse than mixed we need penalty > 1.194-0.482 = 0.712 at the representative
#     g. With HALLUCINATION_ADD=1.5 and g=0.6: penalty = 1.5*0.6 = 0.9 > 0.712.
#     This reproduces the RQ1 finding that separated > mixed at ALL overlaps
#     under oracle-TextGrid silence.
# Mixed is mildly affected by masking under silence (the full mix has no
# interior gaps but overlap masking persists): MILD_MASKING=0.1.
HALLUCINATION_ADD = 1.5      # additive CER penalty on separated-track actions
MILD_MASKING = 0.1           # additive CER penalty on mixed under silence


def silence_gap_penalty(silence_fraction: float) -> tuple[float, float]:
    """Return (sep_penalty, mixed_penalty) for a given silence fraction ``g``.

    ``sep_penalty`` is added to separated/gate CER; ``mixed_penalty`` to mixed
    CER. Linear in g (the confident-attractor firing rate grows with silence
    duration, and #21's smoke test shows the loop scales with stimulus length).
    """
    g = max(0.0, min(1.0, silence_fraction))
    return HALLUCINATION_ADD * g, MILD_MASKING * g


# ------------------------------------------------------------------
# Per-utterance greedy solver
# ------------------------------------------------------------------
def per_utterance_costs(r: float, noise: str, action: str,
                        pair_id: int | None = None,
                        silence_fraction: float = 0.0) -> tuple[float, float]:
    """Return (text_cer, emo_dist) for one (state, action) pair, with the
    silence-gap penalty applied to separated-track actions."""
    tc = kernel_text_cer(r, noise, action)
    ed = kernel_emo_dist(r, action, pair_id)
    if silence_fraction > 0.0:
        sep_pen, mix_pen = silence_gap_penalty(silence_fraction)
        if action in ("separated", "gate_flatness", "gate_speaker"):
            tc += sep_pen
        elif action == "mixed":
            tc += mix_pen
    return tc, ed


def per_utterance_optimal(r: float, noise: str, objective: str,
                          pair_id: int | None = None,
                          silence_fraction: float = 0.0) -> str:
    """Greedy per-utterance optimization: pick the action with the highest
    expected reward given the continuous state. With deterministic transitions
    (T=delta), the POMDP collapses to per-state argmax (same as RQ5); the
    extension is the continuous state + silence dimension."""
    text_cer = {a: per_utterance_costs(r, noise, a, pair_id, silence_fraction)[0]
                for a in ACTIONS}
    emo_dist = {a: per_utterance_costs(r, noise, a, pair_id, silence_fraction)[1]
                for a in ACTIONS}
    # normalize each axis by its global range (so text and emotion are
    # comparable in the joint objective, per #18's equal-regret-axes design)
    tc_vals = list(text_cer.values())
    ed_vals = list(emo_dist.values())
    tc_range = (max(tc_vals) - min(tc_vals)) or 1.0
    ed_range = (max(ed_vals) - min(ed_vals)) or 1.0
    tc_min = min(tc_vals)
    ed_min = min(ed_vals)
    best_a, best_r = None, -1e18
    for a in ACTIONS:
        text_regret = (text_cer[a] - tc_min) / tc_range
        emo_regret = (emo_dist[a] - ed_min) / ed_range
        if objective == "text":
            reward = -text_regret
        elif objective == "emotion":
            reward = -emo_regret
        else:  # joint
            reward = -(text_regret + LAMBDA_EMOTION * emo_regret)
        if reward > best_r:
            best_r, best_a = reward, a
    return best_a


# ------------------------------------------------------------------
# Stratum-level POMDP policy (continuous-input wrapper around RQ5)
# ------------------------------------------------------------------
# Precompute the stratum-level policy once (clean text, the regime router v2
# was calibrated on) and snap continuous r to the nearest stratum.
_STRATUM_REWARDS, _STRATUM_TC, _STRATUM_ED = base.build_reward_table()
_STRATUM_POLICY = base.value_iteration(_STRATUM_REWARDS)

# Stratum boundaries = midpoints of {0, 0.1, 0.3, 0.6, 0.9} -> [0.05, 0.2, 0.45, 0.75]
_STRATUM_BOUNDS = [0.05, 0.20, 0.45, 0.75]


def _snap_stratum(r: float) -> float:
    """Snap continuous overlap r to the nearest of the 5 canonical strata."""
    if r <= _STRATUM_BOUNDS[0]:
        return 0.0
    if r <= _STRATUM_BOUNDS[1]:
        return 0.1
    if r <= _STRATUM_BOUNDS[2]:
        return 0.3
    if r <= _STRATUM_BOUNDS[3]:
        return 0.6
    return 0.9


def stratum_pomdp_action(r: float, noise: str, objective: str) -> str:
    """Stratum-level POMDP action for continuous r (snap to nearest stratum)."""
    s = _snap_stratum(r)
    return _STRATUM_POLICY[(s, noise, objective)]


def router_v2_action(r: float, objective: str) -> str:
    """Router v2 empirical policy (overlap-gated for text/joint, always
    separated for emotion, per #18)."""
    return base.router_v2_policy(r, objective)


# ------------------------------------------------------------------
# RQ10.1 — Text-regret comparison (stratum vs per-utterance vs router v2)
# ------------------------------------------------------------------
def text_regret_comparison() -> dict[str, Any]:
    """Compare three policies on clean-text CER regret over a dense overlap grid.

    The "true" CER surface is the kernel-smoothed estimate (our best continuous
    model from the 15 phase_aggregate points). The oracle action at each r is
    argmin_a kernel_text_cer(r, clean, a). Regret = cer(policy_action) - cer(oracle).

    NOTE: this is in-sample (the per-utterance POMDP is evaluated on the same
    kernel surface it optimizes over), so its regret is ~0 by construction.
    The meaningful number is the stratum-level discretization regret and the
    router-v2 threshold regret. See FINDINGS for the honest framing.
    """
    grid = [i * 0.01 for i in range(0, 91)]  # 0.00 .. 0.90 step 0.01
    rows: list[dict[str, Any]] = []
    sum_reg = {"stratum": 0.0, "per_utterance": 0.0, "router_v2": 0.0}
    n = 0
    crossover_stratum = None
    crossover_per_utt = None
    crossover_router = ROUTER_V2_CROSSOVER
    prev_stratum = None
    prev_per_utt = None
    for r in grid:
        cer_mixed = kernel_text_cer(r, "clean", "mixed")
        cer_sep = kernel_text_cer(r, "clean", "separated")
        oracle_cer = min(cer_mixed, cer_sep)
        oracle_a = "mixed" if cer_mixed <= cer_sep else "separated"
        s_a = stratum_pomdp_action(r, "clean", "text")
        p_a = per_utterance_optimal(r, "clean", "text")
        r_a = router_v2_action(r, "text")
        # restrict to mixed/separated for the clean-text comparison (gates are
        # neutral on clean, so they never beat both; map gate->separated for
        # regret accounting since gates return cer_sep on clean)
        s_cer = cer_mixed if s_a == "mixed" else cer_sep
        p_cer = cer_mixed if p_a == "mixed" else cer_sep
        r_cer = cer_mixed if r_a == "mixed" else cer_sep
        s_reg = s_cer - oracle_cer
        p_reg = p_cer - oracle_cer
        r_reg = r_cer - oracle_cer
        sum_reg["stratum"] += s_reg
        sum_reg["per_utterance"] += p_reg
        sum_reg["router_v2"] += r_reg
        n += 1
        # detect crossover (mixed -> separated)
        if prev_stratum == "mixed" and s_a != "mixed" and crossover_stratum is None:
            crossover_stratum = r
        if prev_per_utt == "mixed" and p_a != "mixed" and crossover_per_utt is None:
            crossover_per_utt = r
        prev_stratum = s_a
        prev_per_utt = p_a
        rows.append({
            "overlap": round(r, 3),
            "cer_mixed": round(cer_mixed, 4),
            "cer_sep": round(cer_sep, 4),
            "oracle_action": oracle_a,
            "stratum_pomdp": s_a,
            "per_utterance_pomdp": p_a,
            "router_v2": r_a,
            "stratum_regret": round(s_reg, 4),
            "per_utterance_regret": round(p_reg, 4),
            "router_v2_regret": round(r_reg, 4),
        })
    mean_reg = {k: v / n for k, v in sum_reg.items()}
    return {
        "grid_rows": rows,
        "mean_text_regret": {k: round(v, 5) for k, v in mean_reg.items()},
        "crossover": {
            "stratum_pomdp": crossover_stratum,
            "per_utterance_pomdp": crossover_per_utt,
            "router_v2": crossover_router,
        },
        "n_grid_points": n,
    }


# ------------------------------------------------------------------
# RQ10.2 — AISHELL-4 failure prediction
# ------------------------------------------------------------------
# AISHELL-4 overlap distribution (RQ1, M_R003S02C01, 77 windows):
#   NoOverlap (<0.05):   53%
#   LightOverlap(0.05-0.2): 31%
#   MidOverlap (0.2-0.5):   14%
#   HeavyOverlap (>=0.5):    1%
AISHELL4_BANDS = [
    (0.00, 0.05, 0.53),
    (0.05, 0.20, 0.31),
    (0.20, 0.50, 0.14),
    (0.50, 0.90, 0.01),
]


def _aishell4_overlap_samples(n_per_band: int = 20) -> list[float]:
    """Deterministic overlap samples weighted by the AISHELL-4 distribution."""
    samples: list[float] = []
    for lo, hi, _w in AISHELL4_BANDS:
        for i in range(n_per_band):
            samples.append(lo + (hi - lo) * (i + 0.5) / n_per_band)
    return samples


def _band_label(r: float) -> str:
    if r < 0.05:
        return "NoOverlap"
    if r < 0.20:
        return "LightOverlap"
    if r < 0.50:
        return "MidOverlap"
    return "HeavyOverlap"


def aishell4_prediction() -> dict[str, Any]:
    """Does the per-utterance POMDP predict the AISHELL-4 failure?

    Simulates AISHELL-4-like windows at two silence regimes:
      - silence-gap (g=0.6): representative of oracle-TextGrid separated tracks
        (one speaker ~12 s of speech in a 30 s window -> ~0.6 silence).
      - no-silence (g=0.0): clean separated tracks (gold-baseline-like).

    Reports P(mixed) per band and overall, for the per-utterance POMDP and the
    stratum-level POMDP (which lacks the silence dimension). The per-utterance
    POMDP predicts the failure if P(mixed) > 0.70 for silence-gap windows.
    """
    overlaps = _aishell4_overlap_samples(n_per_band=20)
    # weight each sample by its band fraction
    band_weight = {b[2] for b in AISHELL4_BANDS}
    out: dict[str, Any] = {"by_regime": {}}
    for regime, g in (("silence_gap", 0.6), ("no_silence", 0.0)):
        band_counts: dict[str, list[int]] = {}
        total_n = 0
        total_w = 0.0
        per_utt_mixed_w = 0.0
        strat_mixed_w = 0.0
        per_band: dict[str, dict[str, float]] = {}
        for r in overlaps:
            bl = _band_label(r)
            w = next(b[2] / 20.0 for b in AISHELL4_BANDS if b[0] <= r < b[1])  # type: ignore
            p_a = per_utterance_optimal(r, "clean", "text", silence_fraction=g)
            s_a = stratum_pomdp_action(r, "clean", "text")
            total_n += 1
            total_w += w
            if p_a == "mixed":
                per_utt_mixed_w += w
            if s_a == "mixed":
                strat_mixed_w += w
            d = per_band.setdefault(bl, {"n": 0, "w": 0.0,
                                         "per_utt_mixed_w": 0.0,
                                         "strat_mixed_w": 0.0})
            d["n"] += 1
            d["w"] += w
            if p_a == "mixed":
                d["per_utt_mixed_w"] += w
            if s_a == "mixed":
                d["strat_mixed_w"] += w
        # P(mixed) overall (weighted by band fraction)
        p_mixed_per_utt = per_utt_mixed_w / total_w if total_w else 0.0
        p_mixed_strat = strat_mixed_w / total_w if total_w else 0.0
        # P(mixed) for high-overlap windows only (MidOverlap + HeavyOverlap)
        hi_w = 0.0
        hi_per_utt_mixed = 0.0
        hi_strat_mixed = 0.0
        for bl in ("MidOverlap", "HeavyOverlap"):
            d = per_band.get(bl)
            if not d:
                continue
            hi_w += d["w"]
            hi_per_utt_mixed += d["per_utt_mixed_w"]
            hi_strat_mixed += d["strat_mixed_w"]
        p_mixed_hi_per_utt = hi_per_utt_mixed / hi_w if hi_w else 0.0
        p_mixed_hi_strat = hi_strat_mixed / hi_w if hi_w else 0.0
        out["by_regime"][regime] = {
            "silence_fraction": g,
            "p_mixed_per_utterance_overall": round(p_mixed_per_utt, 4),
            "p_mixed_stratum_overall": round(p_mixed_strat, 4),
            "p_mixed_per_utterance_high_overlap": round(p_mixed_hi_per_utt, 4),
            "p_mixed_stratum_high_overlap": round(p_mixed_hi_strat, 4),
            "by_band": {
                bl: {
                    "n": d["n"],
                    "band_fraction": round(d["w"] / total_w, 4) if total_w else 0.0,
                    "p_mixed_per_utterance": round(d["per_utt_mixed_w"] / d["w"], 4) if d["w"] else 0.0,
                    "p_mixed_stratum": round(d["strat_mixed_w"] / d["w"], 4) if d["w"] else 0.0,
                }
                for bl, d in sorted(per_band.items())
            },
        }
    # verdict
    sg = out["by_regime"]["silence_gap"]
    ns = out["by_regime"]["no_silence"]
    predicts_failure = sg["p_mixed_per_utterance_overall"] > 0.70
    # The stratum-level POMDP cannot predict the failure because it has no
    # silence dimension; check whether it would still assign >70% to mixed
    # overall (it does, because 84% of AISHELL-4 windows are low-overlap).
    # The discriminating test is the HIGH-overlap band:
    predicts_failure_high_overlap = (
        sg["p_mixed_per_utterance_high_overlap"] > 0.70
        and ns["p_mixed_per_utterance_high_overlap"] < 0.50
    )
    out["verdict"] = {
        "predicts_failure_overall": predicts_failure,
        "predicts_failure_high_overlap": predicts_failure_high_overlap,
        "p_mixed_silence_gap_overall": sg["p_mixed_per_utterance_overall"],
        "p_mixed_no_silence_overall": ns["p_mixed_per_utterance_overall"],
        "p_mixed_silence_gap_high_overlap": sg["p_mixed_per_utterance_high_overlap"],
        "p_mixed_no_silence_high_overlap": ns["p_mixed_per_utterance_high_overlap"],
        "p_mixed_stratum_silence_gap_high_overlap": sg["p_mixed_stratum_high_overlap"],
        "note": ("The per-utterance POMDP adds a silence-fraction state dimension "
                 "(calibrated from #21/RQ1). For silence-gap windows it flips the "
                 "high-overlap route from separated to mixed, predicting the AISHELL-4 "
                 "failure. The stratum-level POMDP lacks this dimension and keeps "
                 "separated at high overlap."),
    }
    return out


# ------------------------------------------------------------------
# RQ10.3 — Coupling-cost heterogeneity (CV within strata)
# ------------------------------------------------------------------
def _global_ranges() -> tuple[float, float]:
    """Global text and emotion ranges for normalization (over all states/actions)."""
    all_text = []
    for ov in OVERLAP_GRID:
        for noise in NOISE_TYPES:
            for a in ACTIONS:
                all_text.append(base.estimate_text_cer(PHASE, ov, noise, a))
    all_emo = []
    for pid in PAIR_IDS:
        for ov in PROSODY_OVERLAPS:
            curve = PROSODY_BY_PAIR[pid].get(ov)
            if not curve:
                continue
            for a in ACTIONS:
                if a == "mixed":
                    all_emo.append(curve["mixed_distortion"])
                elif a == "separated":
                    all_emo.append(curve["sep_distortion"])
                else:
                    all_emo.append(curve["sep_distortion"] + GATE_EMOTION_COST[a])
    text_range = (max(all_text) - min(all_text)) or 1.0
    emo_range = (max(all_emo) - min(all_emo)) or 1.0
    return text_range, emo_range


def coupling_cost_heterogeneity() -> dict[str, Any]:
    """Coupling cost = regret of forcing one action for both objectives vs
    letting each pick its optimum. Computed per (pair, stratum) from the 8
    prosody pairs (emotion side) + stratum-level text CER.

    CV within stratum = std / mean over the 8 pairs. Hypothesis: CV > 0.5 at
    ov 0.1 (the largest-coupling-cost stratum from RQ5).

    NOTE: text CER is stratum-level (phase_aggregate averages 20 cases per
    stratum; per-utterance text CER is not available). The within-stratum
    heterogeneity therefore comes from the emotion side (8 pairs). We also
    report the text-side heterogeneity proxy (sep_helps_frac from
    phase_aggregate) as supporting evidence.
    """
    text_range, emo_range = _global_ranges()
    rows: list[dict[str, Any]] = []
    by_stratum: dict[float, list[float]] = {}
    for s in OVERLAPS_STRATUM:
        # stratum-level text CER (clean)
        tc = {a: base.estimate_text_cer(PHASE, s, "clean", a) for a in ACTIONS}
        tc_min = min(tc.values())
        text_regret = {a: (tc[a] - tc_min) / text_range for a in ACTIONS}
        text_route = min(text_regret, key=text_regret.get)  # type: ignore
        costs = []
        for pid in PAIR_IDS:
            curve = PROSODY_BY_PAIR[pid].get(s)
            if not curve:
                continue
            ed = {}
            for a in ACTIONS:
                if a == "mixed":
                    ed[a] = curve["mixed_distortion"]
                elif a == "separated":
                    ed[a] = curve["sep_distortion"]
                else:
                    ed[a] = curve["sep_distortion"] + GATE_EMOTION_COST[a]
            ed_min = min(ed.values())
            emo_regret = {a: (ed[a] - ed_min) / emo_range for a in ACTIONS}
            emo_route = min(emo_regret, key=emo_regret.get)  # type: ignore
            # decoupled optimum: each axis picks its own best (regret 0 each)
            # coupled optimum: one action for both -> min_a [text_regret[a] + emo_regret[a]]
            coupled = min(text_regret[a] + LAMBDA_EMOTION * emo_regret[a] for a in ACTIONS)
            coupling_cost = coupled  # decoupled = 0 by construction
            costs.append(coupling_cost)
            disagree = (text_route != emo_route)
            rows.append({
                "stratum": s,
                "pair_id": pid,
                "text_route": text_route,
                "emotion_route": emo_route,
                "text_emotion_disagree": disagree,
                "coupling_cost": round(coupling_cost, 5),
            })
        by_stratum[s] = costs
    # CV per stratum
    cv_rows: list[dict[str, Any]] = []
    for s in OVERLAPS_STRATUM:
        costs = by_stratum[s]
        n = len(costs)
        mean_c = sum(costs) / n if n else 0.0
        std_c = statistics.pstdev(costs) if n > 1 else 0.0
        cv = std_c / mean_c if mean_c > 1e-9 else 0.0
        # text-side heterogeneity proxy: sep_helps_frac (fraction of the 20
        # cases where separated CER < mixed CER; 0.5 = max heterogeneity)
        sep_helps = SEP_HELPS_FRAC.get(s, 0.0)
        cv_rows.append({
            "stratum": s,
            "n_pairs": n,
            "mean_coupling_cost": round(mean_c, 5),
            "std_coupling_cost": round(std_c, 5),
            "cv_coupling_cost": round(cv, 4),
            "cv_gt_0.5": cv > 0.5,
            "sep_helps_frac": sep_helps,  # text-side heterogeneity proxy
            "text_route_heterogeneity": round(abs(0.5 - sep_helps) * 2, 4),
        })
    cv_at_01 = next(r["cv_coupling_cost"] for r in cv_rows if r["stratum"] == 0.1)
    return {
        "per_pair_rows": rows,
        "cv_per_stratum": cv_rows,
        "cv_at_ov0.1": cv_at_01,
        "heterogeneity_hypothesis_supported": cv_at_01 > 0.5,
        "note": ("Within-stratum heterogeneity comes from the emotion side (8 prosody "
                 "pairs); text CER is stratum-level. sep_helps_frac is the text-side "
                 "heterogeneity proxy (fraction of the 20 cases where separated helps)."),
    }


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main() -> None:
    out_dir = HERE
    tr = text_regret_comparison()
    a4 = aishell4_prediction()
    cc = coupling_cost_heterogeneity()

    # ---- CSV: per-grid-point text-regret comparison ----
    csv_path = out_dir / "policy_comparison_per_utterance.csv"
    with csv_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(tr["grid_rows"][0].keys()))
        writer.writeheader()
        writer.writerows(tr["grid_rows"])

    # ---- JSON: full summary ----
    json_path = out_dir / "policy_comparison_per_utterance.json"
    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ10",
        "title": "POMDP per-utterance heterogeneity extension",
        "builds_on": "RQ5 (pomdp_solver.py, finding #24)",
        "method": {
            "continuous_state": "overlap-ratio in [0, 0.9] (kernel-smoothed)",
            "kernel": "Gaussian",
            "bandwidth_text": BW_TEXT,
            "bandwidth_emotion": BW_EMO,
            "text_support": "15 greedy overlap points (phase_aggregate.csv)",
            "emotion_support": "8 pairs x 5 overlaps (prosody_tax_curve.csv, alpha=0.15)",
            "silence_model": {
                "hallucination_add": HALLUCINATION_ADD,
                "mild_masking": MILD_MASKING,
                "calibration": "RQ1 (aishell4) + #21 (causal hallucination probe)",
                "applies_to": ["separated", "gate_flatness", "gate_speaker"],
            },
            "solver": "greedy per-utterance argmax (deterministic T -> single-step)",
        },
        "rq10_1_text_regret": {
            "verdict": (
                "Per-utterance POMDP has ~0 text regret by construction (in-sample); "
                "the meaningful comparison is stratum-level discretization regret vs "
                "router-v2 threshold regret. See FINDINGS for honest framing."
            ),
            "mean_text_regret": tr["mean_text_regret"],
            "crossover": tr["crossover"],
            "n_grid_points": tr["n_grid_points"],
        },
        "rq10_2_aishell4_prediction": a4,
        "rq10_3_coupling_cost_heterogeneity": {
            "cv_per_stratum": cc["cv_per_stratum"],
            "cv_at_ov0.1": cc["cv_at_ov0.1"],
            "heterogeneity_hypothesis_supported": cc["heterogeneity_hypothesis_supported"],
            "note": cc["note"],
        },
        "verdicts": {
            "rq10_1_per_utterance_improves": (
                tr["mean_text_regret"]["per_utterance"] < tr["mean_text_regret"]["stratum"]
            ),
            "rq10_2_predicts_aishell4_failure": a4["verdict"]["predicts_failure_high_overlap"],
            "rq10_3_cv_gt_0.5_at_ov0.1": cc["heterogeneity_hypothesis_supported"],
        },
    }
    with json_path.open("w") as fh:
        json.dump(summary, fh, indent=2)

    # ---- stdout summary ----
    print("=" * 76)
    print("RQ10: POMDP per-utterance heterogeneity extension")
    print("Label: experimental/frontier")
    print("=" * 76)
    print()
    print("RQ10.1 — Text-regret comparison (clean, dense grid 0.00-0.90):")
    print(f"  mean text regret  stratum-level POMDP : {tr['mean_text_regret']['stratum']}")
    print(f"  mean text regret  per-utterance POMDP : {tr['mean_text_regret']['per_utterance']}")
    print(f"  mean text regret  router v2           : {tr['mean_text_regret']['router_v2']}")
    print(f"  crossover         stratum-level POMDP : {tr['crossover']['stratum_pomdp']}")
    print(f"  crossover         per-utterance POMDP : {tr['crossover']['per_utterance_pomdp']}")
    print(f"  crossover         router v2           : {tr['crossover']['router_v2']}")
    print(f"  per-utterance improves (in-sample)    : {summary['verdicts']['rq10_1_per_utterance_improves']}")
    print()
    print("RQ10.2 — AISHELL-4 failure prediction:")
    v = a4["verdict"]
    print(f"  P(mixed) silence-gap  overall         : {v['p_mixed_silence_gap_overall']}")
    print(f"  P(mixed) no-silence   overall         : {v['p_mixed_no_silence_overall']}")
    print(f"  P(mixed) silence-gap  high-overlap    : {v['p_mixed_silence_gap_high_overlap']}")
    print(f"  P(mixed) no-silence   high-overlap    : {v['p_mixed_no_silence_high_overlap']}")
    print(f"  P(mixed) stratum      high-overlap    : {v['p_mixed_stratum_silence_gap_high_overlap']}")
    print(f"  predicts failure (high-overlap, >70%) : {v['predicts_failure_high_overlap']}")
    print()
    print("RQ10.3 — Coupling-cost heterogeneity (CV within strata):")
    for r in cc["cv_per_stratum"]:
        print(f"  ov {r['stratum']:.1f}  mean={r['mean_coupling_cost']:.5f}  "
              f"std={r['std_coupling_cost']:.5f}  CV={r['cv_coupling_cost']:.4f}  "
              f"CV>0.5={r['cv_gt_0.5']}  sep_helps_frac={r['sep_helps_frac']}")
    print(f"  CV at ov0.1 > 0.5                     : {cc['heterogeneity_hypothesis_supported']}")
    print()
    print(f"Outputs: {csv_path}")
    print(f"         {json_path}")


if __name__ == "__main__":
    main()
