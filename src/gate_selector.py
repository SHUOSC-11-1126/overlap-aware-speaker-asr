"""Reference-free multi-gate SELECTOR: which separation-hallucination cure, keyed on the audio alone.

Pre-registered research question (closes the arc opened by findings #11/#12)
--------------------------------------------------------------------------
The noise-robust-gate study (#11, `noise_robust_gate.py`) found a spectral-flatness gate cures the
separation-hallucination tail under BROADBAND noise but fails under babble (speech-like residual ->
no flatness signal). The speaker-conditioned-gate study (#12, `speaker_conditioned_gate.py`) found a
Resemblyzer speaker embedding cures MODERATE babble (5-10 dB) where flatness cannot, but is neutral/
harmful on white/pink and FAILS at 0 dB babble. Its synthesis asserted -- but never tested -- that
"the residual region's own spectral flatness" is the right reference-free key to pick between the two
gates (high -> broadband -> flatness gate; low -> speech-like -> speaker gate).

That asserted key has a sharp, falsifiable risk baked into the #12 grid: at 0 dB babble the residual
is speech-like (low flatness -> the naive rule says "speaker gate"), yet there the speaker gate is the
WORST arm (CER 3.16 vs flatness 1.41 vs raw-sep 2.93). A pure-flatness key must mis-route exactly
where the stakes are highest. So this module pairs the flatness key with a reference-free CATASTROPHE
GUARD: the speaker-similarity contrast (the bimodality gap between the target window cluster and the
residual window cluster). When that contrast collapses there is no recoverable target left, so the
selector falls back to the flatness gate (the data's safe choice at 0 dB).

Hypotheses (CER is post-hoc only; never an input to any pick):
  H1  The reference-free selector's pooled mean CER (over all noise x SNR x overlap) is LOWER than
      every fixed single strategy: raw separation, always-flatness, and always-speaker.
  H2  The selector's pooled catastrophic tail rate P(CER>1) is <= the best single gate's.
  H3  Residual spectral flatness separates broadband (white/pink) from babble residual with high
      AUC (so the broadband/speech-like branch is well-keyed), AND the similarity-contrast guard is
      necessary to avoid the 0 dB babble mis-route (a pure-flatness selector should NOT beat
      always-flatness; adding the guard should).
  Useful-either-way  If the selector cannot beat always-flatness even with the guard, residual
      flatness is an insufficient routing key -- a real negative result that refines the project's
      reference-free-router thesis at the gate level.

Method (reference-free w.r.t. transcripts/CER; uses only the audio + an injected speaker embedder):
  Per separated track, slide GE2E windows, estimate the dominant-speaker reference embedding from the
  top-energy windows, score every window's cosine similarity to it, find the target/residual valley,
  and read three signals off the residual (low-similarity) windows: their mean spectral flatness, the
  similarity-contrast gap, and the residual fraction. A per-utterance rule combines the two tracks'
  signals into one choice in {none, flatness, speaker}. The chosen arm's already-computed transcript
  is the selector's output -- the pick adds NO transcription cost.

Labels: experimental/frontier; references synthetic/silver; ASR Whisper-tiny; speaker embedder
Resemblyzer GE2E (offline, optional frontier dep). No gold tables touched; outputs to
results/frontier/gate_selector/.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from .config import PROJECT_ROOT
from .noise_robust_gate import adaptive_flatness_threshold, track_flatness
from .speaker_conditioned_gate import (
    HOP,
    WIN,
    EmbedFn,  # type: callable(wav: np.ndarray) -> np.ndarray (a speaker-window embedder)
    cosine_sims,
    frame_windows,
    reference_embedding,
    window_energies,
)

OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "gate_selector"
CATASTROPHIC_CER = 1.0

# A-priori decision thresholds (set from the reference-free signal PHYSICS / distributions, never
# from CER). FLAT_HI: broadband noise frames have spectral flatness near 1, voiced speech well below
# ~0.3, so 0.40 is the natural broadband/speech-like boundary. MIN_SIM_GAP: when the target and
# residual window-similarity clusters are < this far apart the track has no recoverable target split
# (the 0 dB babble regime), so the speaker gate is unsafe. Both are reported with a sensitivity sweep
# in FINDINGS; the selector itself uses these fixed values.
FLAT_HI = 0.40
MIN_SIM_GAP = 0.06

# Selector arm <-> CER column it realizes.
_ARM_CER = {"none": "cer_sep", "flatness": "cer_flatness_gate", "speaker": "cer_speaker_gate"}


# ======================================================================================
# Pure decision logic (no resemblyzer, no Whisper) -- unit tested with an injected fake embedder
# ======================================================================================
def select_gate(signal: dict[str, Any], flat_hi: float = FLAT_HI, min_sim_gap: float = MIN_SIM_GAP) -> str:
    """A-priori pick in {none, flatness, speaker} from one track-or-utterance signal. No CER input.

    none      no clear residual region to crop -> leave the track alone (raw separation).
    flatness  broadband residual (high flatness) OR speech-like-but-collapsed (guard fired): the
              flatness gate is the safe choice in both cases per the #11/#12 grid.
    speaker   speech-like residual WITH a recoverable target/residual contrast (moderate babble).
    """
    if not signal.get("has_residual", False):
        return "none"
    if float(signal["residual_flatness"]) >= flat_hi:
        return "flatness"
    if float(signal["sim_gap"]) < min_sim_gap:  # catastrophe guard: no recoverable target left
        return "flatness"
    return "speaker"


def select_gate_utterance(
    track_signals: list[dict[str, Any]], flat_hi: float = FLAT_HI, min_sim_gap: float = MIN_SIM_GAP
) -> str:
    """Combine the two separated tracks into one per-utterance pick. Broadband decision uses the
    MEAN residual flatness across tracks that have a residual; the guard uses the WORST (min) sim
    contrast, so one collapsed track is enough to fall back to the safe flatness gate."""
    has = [s for s in track_signals if s.get("has_residual", False)]
    if not has:
        return "none"
    combined = {
        "has_residual": True,
        "residual_flatness": float(np.mean([float(s["residual_flatness"]) for s in has])),
        "sim_gap": float(np.min([float(s["sim_gap"]) for s in has])),
    }
    return select_gate(combined, flat_hi, min_sim_gap)


def residual_window_signal(
    wav: np.ndarray,
    embed_window: EmbedFn,
    win: int = WIN,
    hop: int = HOP,
    top_frac: float = 0.4,
    lo_pct: float = 20.0,
    hi_pct: float = 80.0,
    **thr_kwargs: Any,
) -> dict[str, Any]:
    """Reference-free per-track signal for gate selection. Identifies the residual (low-speaker-
    similarity) window region via the similarity valley, then reads three numbers off it:

      residual_flatness  mean spectral flatness of the residual windows (high -> broadband noise,
                         low -> speech-like babble). The #12-asserted selection key.
      sim_gap            hi_pct - lo_pct percentile spread of window similarities -- the target/
                         residual contrast. Collapses toward 0 when no recoverable target remains.
      residual_frac      fraction of windows below the valley threshold.
      has_residual       a clear two-cluster split exists (valley found and 0 < residual_frac < 1).
    """
    x = np.asarray(wav, dtype=np.float32)
    windows = frame_windows(x.size, win, hop)
    empty = {"has_residual": False, "residual_flatness": 0.0, "sim_gap": 0.0, "residual_frac": 0.0}
    if len(windows) < 2:
        return empty
    embs = np.array([np.asarray(embed_window(x[s:e]), dtype=np.float64) for s, e in windows])
    sims = cosine_sims(embs, reference_embedding(embs, window_energies(x, windows), top_frac))
    sim_gap = float(np.percentile(sims, hi_pct) - np.percentile(sims, lo_pct))
    thr = adaptive_flatness_threshold(sims, lo_pct=lo_pct, hi_pct=hi_pct, **thr_kwargs)
    if thr is None:
        return {**empty, "sim_gap": sim_gap}
    residual_idx = [i for i, (s, e) in enumerate(windows) if sims[i] < thr]
    residual_frac = len(residual_idx) / len(windows)
    if not residual_idx or residual_frac >= 1.0:
        return {**empty, "sim_gap": sim_gap}
    flats = []
    for i in residual_idx:
        s, e = windows[i]
        fl = track_flatness(x[s:e])
        if fl.size:
            flats.append(float(np.mean(fl)))
    residual_flatness = float(np.mean(flats)) if flats else 1.0
    return {
        "has_residual": True,
        "residual_flatness": residual_flatness,
        "sim_gap": sim_gap,
        "residual_frac": float(residual_frac),
    }


# ======================================================================================
# Oracle + selection accuracy + aggregation (pure, unit tested)
# ======================================================================================
def _arm_cer(row: dict[str, Any], arm: str) -> float:
    return float(row[_ARM_CER[arm]])


def oracle_best_arm(row: dict[str, Any]) -> str:
    """Arm in {none, flatness, speaker} with the lowest CER for this utterance (the oracle that
    an upper-bound selector would pick). 'none' == raw separation, no gate."""
    return min(_ARM_CER, key=lambda arm: _arm_cer(row, arm))


def selection_is_oracle_optimal(row: dict[str, Any], eps: float = 1e-9) -> bool:
    """Did the selector's chosen arm achieve the oracle CER (allowing ties)?"""
    chosen = _arm_cer(row, row["selected_gate"])
    best = min(_arm_cer(row, a) for a in _ARM_CER)
    return chosen <= best + eps


def _mean(xs: list[float]) -> float:
    return round(float(np.mean(xs)), 6) if xs else 0.0


def _tail(xs: list[float], threshold: float = CATASTROPHIC_CER) -> float:
    return round(sum(1 for c in xs if c > threshold) / len(xs), 6) if xs else 0.0


_FIXED_ARMS = ["mixed", "sep", "flatness_gate", "speaker_gate"]


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {"n": len(rows)}
    for arm in _FIXED_ARMS:
        cers = [float(r[f"cer_{arm}"]) for r in rows]
        out[f"mean_cer_{arm}"] = _mean(cers)
        out[f"tail_{arm}"] = _tail(cers)
    sel = [float(r["cer_selector"]) for r in rows]
    orc = [min(_arm_cer(r, a) for a in _ARM_CER) for r in rows]
    out["mean_cer_selector"] = _mean(sel)
    out["tail_selector"] = _tail(sel)
    out["mean_cer_oracle"] = _mean(orc)
    out["tail_oracle"] = _tail(orc)
    out["regret_vs_oracle"] = round(out["mean_cer_selector"] - out["mean_cer_oracle"], 6)
    out["selection_accuracy"] = round(
        sum(1 for r in rows if selection_is_oracle_optimal(r)) / len(rows), 6
    ) if rows else 0.0
    dist: dict[str, int] = {}
    for r in rows:
        dist[r["selected_gate"]] = dist.get(r["selected_gate"], 0) + 1
    out["selection_dist"] = dist
    return out


def aggregate_selector(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Pooled + per-(noise_type, snr) summary: fixed-arm / selector / oracle mean CER and tail,
    selector regret vs oracle, and selection accuracy (fraction of utterances where the pick was
    oracle-optimal). CER is post-hoc only."""
    by_condition: list[dict[str, Any]] = []
    keys = sorted({(r["noise_type"], float(r["snr_db"])) for r in rows})
    for ntype, snr in keys:
        at = [r for r in rows if r["noise_type"] == ntype and float(r["snr_db"]) == snr]
        by_condition.append({"noise_type": ntype, "snr_db": snr, **_summarize(at)})
    return {"pooled": _summarize(rows), "by_condition": by_condition}


def _rank_auc(pos: list[float], neg: list[float]) -> float | None:
    """P(a random 'pos' value > a random 'neg' value), ties = 0.5. None if either side empty."""
    if not pos or not neg:
        return None
    wins = sum(1.0 if p > n else 0.5 if p == n else 0.0 for p in pos for n in neg)
    return round(wins / (len(pos) * len(neg)), 6)


def _flats_for(rows: list[dict[str, Any]], ntype: str) -> list[float]:
    return [float(r["residual_flatness_max"]) for r in rows
            if r["noise_type"] == ntype and float(r["residual_flatness_max"]) > 0]


def pairwise_flatness_auc(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """H3 signal check, reference-free (no CER): can residual flatness tell the noise TYPES apart?
    The selector's whole premise is that flatness keys 'broadband -> flatness gate' vs 'speech-like
    -> speaker gate'. This reports the pairwise rank-AUC and per-type means so a confound is visible:
    if pink (which behaves like broadband for the gates' purposes but is spectrally 1/f-tilted, not
    flat) is NOT separable from babble, residual flatness alone cannot route them differently."""
    white, pink, bab = _flats_for(rows, "white"), _flats_for(rows, "pink"), _flats_for(rows, "babble")
    return {
        "auc_white_vs_babble": _rank_auc(white, bab),
        "auc_pink_vs_babble": _rank_auc(pink, bab),
        "auc_white_vs_pink": _rank_auc(white, pink),
        "mean_residual_flatness": {"white": _mean(white), "pink": _mean(pink), "babble": _mean(bab)},
        "n": {"white": len(white), "pink": len(pink), "babble": len(bab)},
    }


def oracle_composition(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """How often each arm {none, flatness, speaker} is the oracle-best, pooled and per (noise, snr).
    Shows where gating helps at all: a cell dominated by 'none' means the right move is NOT to gate,
    which bounds how much any gate selector can win there."""
    def comp(rs: list[dict[str, Any]]) -> dict[str, int]:
        d: dict[str, int] = {"none": 0, "flatness": 0, "speaker": 0}
        for r in rs:
            d[oracle_best_arm({k: float(r[k]) for k in _ARM_CER.values()})] += 1
        return d

    by: list[dict[str, Any]] = []
    for ntype, snr in sorted({(r["noise_type"], float(r["snr_db"])) for r in rows}):
        at = [r for r in rows if r["noise_type"] == ntype and float(r["snr_db"]) == snr]
        by.append({"noise_type": ntype, "snr_db": snr, **comp(at)})
    return {"pooled": comp(rows), "by_condition": by}


def residual_flatness_auc(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Back-compat one-number framing (broadband {white,pink} vs babble). Retained, but
    `pairwise_flatness_auc` is the honest view because it exposes the pink/babble confound."""
    broad = [float(r["residual_flatness_max"]) for r in rows
             if r["noise_type"] in ("white", "pink") and float(r["residual_flatness_max"]) > 0]
    bab = _flats_for(rows, "babble")
    return {
        "auc_broadband_vs_babble": _rank_auc(broad, bab),
        "mean_residual_flatness_broadband": _mean(broad),
        "mean_residual_flatness_babble": _mean(bab),
        "n_broadband": len(broad),
        "n_babble": len(bab),
    }


def sweep_flat_hi(rows: list[dict[str, Any]], values: list[float], min_sim_gap: float = MIN_SIM_GAP) -> list[dict[str, Any]]:
    """Analysis-only sensitivity sweep: re-decide each utterance at different flat_hi and report
    the resulting pooled selector CER. Shows whether H1 hinges on a knife-edge threshold. Uses the
    per-utterance signals stored on each row; CER only scores the outcome, never the pick."""
    out: list[dict[str, Any]] = []
    for fh in values:
        sel_cers: list[float] = []
        for r in rows:
            sig = {
                "has_residual": bool(r["has_residual"]),
                "residual_flatness": float(r["residual_flatness_sel"]),
                "sim_gap": float(r["sim_gap_sel"]),
            }
            arm = select_gate(sig, flat_hi=fh, min_sim_gap=min_sim_gap)
            sel_cers.append(_arm_cer(r, arm))
        out.append({"flat_hi": fh, "mean_cer_selector": _mean(sel_cers), "tail_selector": _tail(sel_cers)})
    return out


# ======================================================================================
# Whisper + resemblyzer driver
# ======================================================================================
NOISE_TYPES = ["white", "pink", "babble"]
NOISE_SNR: list[float] = [10.0, 5.0, 0.0]
OVERLAPS = [0.1, 0.3]


def run_selector_grid(out_dir: Path, num_pairs: int, noise_types: list[str], overlaps: list[float] | None = None) -> dict[str, Any]:
    import whisper

    from .evaluate_cer import compute_cer
    from .generate_synthetic_overlap import build_mixture, read_mono_audio
    from .noise_robust_gate import add_noise_field, flatness_relenergy_trim, make_noise
    from .separation_tax_phase import SNIPPETS_DIR, select_pairs, transcribe_with_signals
    from .speaker_conditioned_gate import resemblyzer_embedder, speaker_gate_trim

    out_dir.mkdir(parents=True, exist_ok=True)
    plans = select_pairs(num_pairs)
    overlaps = list(OVERLAPS if overlaps is None else overlaps)
    all_snips = {p.name: read_mono_audio(p).samples for p in sorted(SNIPPETS_DIR.glob("*.wav"))}
    model = whisper.load_model("tiny")
    embed = resemblyzer_embedder()
    print(f"[selector] pairs={len(plans)} types={noise_types} snr={NOISE_SNR} overlaps={overlaps}", flush=True)

    def tx(a: np.ndarray) -> str:
        return transcribe_with_signals(model, a, "greedy")["text"]

    rows: list[dict[str, Any]] = []
    for pi, plan in enumerate(plans):
        s1, s2 = read_mono_audio(plan.con_path), read_mono_audio(plan.pro_path)
        ref = plan.con_text + plan.pro_text
        babble_src = [v for k, v in all_snips.items() if k not in (plan.con_path.name, plan.pro_path.name)]
        for overlap in overlaps:
            mixed, t1, t2, _ = build_mixture(s1, s2, overlap)
            for kind in noise_types:
                for snr in NOISE_SNR:
                    sd = pi * 137 + int(round(overlap * 100)) + int(snr) * 7 + noise_types.index(kind) * 31
                    mx = add_noise_field(mixed, snr, make_noise(kind, mixed.size, sd, babble_src))
                    n1 = add_noise_field(t1, snr, make_noise(kind, t1.size, sd + 1, babble_src))
                    n2 = add_noise_field(t2, snr, make_noise(kind, t2.size, sd + 2, babble_src))
                    f1, f2 = flatness_relenergy_trim(n1), flatness_relenergy_trim(n2)
                    g1, g2 = speaker_gate_trim(n1, embed, min_gap=0.10), speaker_gate_trim(n2, embed, min_gap=0.10)
                    # reference-free per-track signals + per-utterance pick
                    sig1 = residual_window_signal(n1, embed, min_gap=0.10)
                    sig2 = residual_window_signal(n2, embed, min_gap=0.10)
                    selected = select_gate_utterance([sig1, sig2])
                    arm_cer = {
                        "mixed": compute_cer(ref, tx(mx))["cer"],
                        "sep": compute_cer(ref, tx(n1) + tx(n2))["cer"],
                        "flatness_gate": compute_cer(ref, tx(f1) + tx(f2))["cer"],
                        "speaker_gate": compute_cer(ref, tx(g1) + tx(g2))["cer"],
                    }
                    realized = {"none": arm_cer["sep"], "flatness": arm_cer["flatness_gate"],
                                "speaker": arm_cer["speaker_gate"]}[selected]
                    has_res = bool(sig1["has_residual"] or sig2["has_residual"])
                    res_flats = [s["residual_flatness"] for s in (sig1, sig2) if s["has_residual"]]
                    gaps = [s["sim_gap"] for s in (sig1, sig2) if s["has_residual"]]
                    rows.append({
                        "pair_id": pi, "overlap_ratio": overlap, "noise_type": kind, "snr_db": snr,
                        "selected_gate": selected,
                        "cer_mixed": round(arm_cer["mixed"], 6),
                        "cer_sep": round(arm_cer["sep"], 6),
                        "cer_flatness_gate": round(arm_cer["flatness_gate"], 6),
                        "cer_speaker_gate": round(arm_cer["speaker_gate"], 6),
                        "cer_selector": round(realized, 6),
                        "has_residual": int(has_res),
                        "residual_flatness_sel": round(float(np.mean(res_flats)), 6) if res_flats else 0.0,
                        "residual_flatness_max": round(float(np.max(res_flats)), 6) if res_flats else 0.0,
                        "sim_gap_sel": round(float(np.min(gaps)), 6) if gaps else 0.0,
                    })
        print(f"[selector] pair {pi + 1}/{len(plans)} done", flush=True)

    curve = out_dir / "selector_curve.csv"
    with curve.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    agg = aggregate_selector(rows)
    summary = build_summary(rows)
    (out_dir / "selector_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    pw = summary["residual_flatness_pairwise"]
    print(f"[selector] pooled={agg['pooled']['mean_cer_selector']} "
          f"flat={agg['pooled']['mean_cer_flatness_gate']} spk={agg['pooled']['mean_cer_speaker_gate']} "
          f"oracle={agg['pooled']['mean_cer_oracle']} acc={agg['pooled']['selection_accuracy']}", flush=True)
    print(f"[selector] flatness AUC white/babble={pw['auc_white_vs_babble']} "
          f"pink/babble={pw['auc_pink_vs_babble']} white/pink={pw['auc_white_vs_pink']}", flush=True)
    try:
        render_figure(out_dir, summary)
    except Exception as exc:  # figure is a presentation nicety; never fail the run on it
        print(f"[selector] figure skipped: {exc}", flush=True)
    print(f"[selector] wrote {curve} + selector_summary.json (rows={len(rows)})", flush=True)
    return {"summary": summary, "n_rows": len(rows)}


def render_figure(out_dir: Path, summary: dict[str, Any]) -> Path | None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pooled = summary["pooled"]
    by_cond = summary["by_condition"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.6))

    # left: pooled mean CER per strategy
    strat = [("sep", "raw sep"), ("flatness_gate", "always flatness"),
             ("speaker_gate", "always speaker"), ("selector", "selector (ref-free)"),
             ("oracle", "oracle")]
    vals = [pooled[f"mean_cer_{k}"] for k, _ in strat]
    colors = ["#999999", "#e45756", "#4c78a8", "#54a24b", "#000000"]
    ax1.bar(range(len(strat)), vals, color=colors)
    ax1.set_xticks(range(len(strat)))
    ax1.set_xticklabels([lab for _, lab in strat], rotation=20, ha="right", fontsize=9)
    ax1.set_ylabel("pooled mean CER (lower better)")
    ax1.set_title(f"Pooled over all noise x SNR (acc={pooled['selection_accuracy']:.2f})")
    ax1.grid(alpha=0.3, axis="y")
    for i, v in enumerate(vals):
        ax1.text(i, v, f"{v:.2f}", ha="center", va="bottom", fontsize=8)

    # right: selector vs flatness vs speaker per babble SNR (where the routing matters most)
    bab = sorted([r for r in by_cond if r["noise_type"] == "babble"], key=lambda r: r["snr_db"])
    if bab:
        x = np.arange(len(bab))
        w = 0.25
        for i, (k, lab, c) in enumerate([("flatness_gate", "flatness", "#e45756"),
                                          ("speaker_gate", "speaker", "#4c78a8"),
                                          ("selector", "selector", "#54a24b")]):
            ax2.bar(x + (i - 1) * w, [r[f"mean_cer_{k}"] for r in bab], w, color=c, label=lab)
        ax2.axhline(1.0, color="black", lw=0.8, ls=":")
        ax2.set_xticks(x)
        ax2.set_xticklabels([f"{r['snr_db']:g} dB" for r in bab])
        ax2.set_xlabel("babble input SNR")
        ax2.set_ylabel("mean separated CER")
        ax2.set_title("Babble: where flatness vs speaker disagree")
        ax2.legend(fontsize=9)
        ax2.grid(alpha=0.3, axis="y")
    fig.suptitle("Reference-free gate selector vs fixed gates and oracle (Whisper-tiny, zh)")
    fig.tight_layout()
    fig_path = out_dir / "gate_selector.png"
    fig.savefig(fig_path, dpi=160)
    plt.close(fig)
    print(f"[selector] wrote {fig_path}", flush=True)
    return fig_path


def build_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """All reference-free analysis derived from a completed grid: pooled/per-condition CER for every
    arm + selector + oracle, the pairwise residual-flatness separability (H3 signal check), the
    oracle arm composition, and the a-priori-threshold sensitivity sweep. CER only ever scores
    outcomes here; the selector's picks were fixed at run time from audio signals alone."""
    agg = aggregate_selector(rows)
    return {
        "pooled": agg["pooled"],
        "by_condition": agg["by_condition"],
        "residual_flatness_pairwise": pairwise_flatness_auc(rows),
        "residual_flatness_broadband": residual_flatness_auc(rows),
        "oracle_composition": oracle_composition(rows),
        "best_typed_policy_ceiling": best_typed_policy(rows),
        "flat_hi_sweep": sweep_flat_hi(rows, [0.05, 0.08, 0.10, 0.12, 0.15, 0.20, 0.30, 0.40, 0.50, 0.60]),
        "thresholds": {"flat_hi": FLAT_HI, "min_sim_gap": MIN_SIM_GAP},
    }


def _read_curve(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def best_typed_policy(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """ANALYSIS-ONLY ceiling (uses CER, so labeled oracle): the best possible noise-TYPE -> arm map.
    For each noise type pick the single arm {none, flatness, speaker} that minimizes that type's mean
    CER, then report the pooled CER of that fixed per-type policy. This is the ceiling of ANY perfect
    reference-free noise-type classifier (residual flatness already separates the types at AUC 1.0),
    so if this ceiling does not beat the no-separation baseline, no flatness-keyed selector can."""
    types = sorted({r["noise_type"] for r in rows})
    chosen: dict[str, str] = {}
    for t in types:
        at = [r for r in rows if r["noise_type"] == t]
        chosen[t] = min(_ARM_CER, key=lambda a: _mean([_arm_cer(r, a) for r in at]))
    cers = [_arm_cer(r, chosen[r["noise_type"]]) for r in rows]
    return {"per_type_arm": chosen, "mean_cer": _mean(cers), "tail": _tail(cers),
            "mean_cer_mixed_baseline": _mean([float(r["cer_mixed"]) for r in rows])}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Reference-free multi-gate selector experiment (frontier).")
    p.add_argument("--pairs", type=int, default=8)
    p.add_argument("--types", type=str, default="white,pink,babble", help="comma-separated noise types")
    p.add_argument("--overlaps", type=str, default="0.1,0.3", help="comma-separated overlap ratios")
    p.add_argument("--figure", action="store_true", help="Render the figure from an existing summary and exit.")
    p.add_argument("--from-csv", type=str, default="", help="Recompute summary+figure from an existing selector_curve.csv (no Whisper) and exit.")
    p.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    if args.from_csv:
        rows = _read_curve(Path(args.from_csv))
        summary = build_summary(rows)
        (out_dir / "selector_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        render_figure(out_dir, summary)
        pooled, pw = summary["pooled"], summary["residual_flatness_pairwise"]
        print(f"[selector] (from-csv) pooled selector={pooled['mean_cer_selector']} "
              f"flat={pooled['mean_cer_flatness_gate']} spk={pooled['mean_cer_speaker_gate']} "
              f"sep={pooled['mean_cer_sep']} oracle={pooled['mean_cer_oracle']} acc={pooled['selection_accuracy']}")
        print(f"[selector] (from-csv) flatness AUC white/babble={pw['auc_white_vs_babble']} "
              f"pink/babble={pw['auc_pink_vs_babble']}")
        return
    if args.figure:
        summary = json.loads((out_dir / "selector_summary.json").read_text(encoding="utf-8"))
        render_figure(out_dir, summary)
        return
    run_selector_grid(out_dir, args.pairs, [t.strip() for t in args.types.split(",") if t.strip()],
                      [float(o) for o in args.overlaps.split(",") if o.strip()])


if __name__ == "__main__":
    main()
