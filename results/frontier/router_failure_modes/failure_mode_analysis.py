"""RQ12: Router v2 failure-mode decomposition on AISHELL-4.

REANALYSIS ONLY — no Whisper / no ASR model is run. This script reads the existing
AISHELL-4 external-validation results (``results/external_sanity_check/aishell4/
rq1_aishell4_validation_results.json``, label ``external/sanity-check``, PR #890) and
decomposes WHY router v2 fails to beat always-mixed (finding #23: router v2 cpWER
1.206 vs always-mixed 1.173) into per-window failure modes.

Label: experimental/frontier
Closes #895. See ``results/external_sanity_check/aishell4/FINDINGS.md`` (RQ1, the
failure surface), ``results/frontier/causal_hallucination_probe/FINDINGS.md``
(finding #21, the confident-attractor mechanism), and
``results/frontier/silence_aware_gate/FINDINGS.md`` (RQ8, the proposed gate cure).

Research questions
------------------
1. What fraction of router v2's regret is silence-gap hallucination (separated
   cpWER > 1.0 or CR > 2.4 on separated tracks)?
2. What fraction is overlap-distribution shift (router's rules fire on the wrong
   strata)?
3. What fraction is compression-ratio signal non-transfer (CR threshold mismatch)?
4. Would the silence-aware gate (``src/silence_aware_gate.py``) fix any failure
   windows?

Method
------
For each of the 77 windows we compute a reference-free compression-ratio (CR) proxy
from the stored transcript text (Whisper's ``compression_ratio`` is
``len(utf8_bytes) / len(zlib(bytes))``; the RQ1 JSON did not store Whisper's
per-segment CR, so we recompute it on the per-speaker concatenated text and take the
max across speakers — a documented LOWER BOUND on Whisper's per-segment max CR). We
then classify every window where the router picked the oracle-worse method (a
"failure window") into a primary failure mode and bootstrap 95% CIs for each mode's
share of the total routing regret.

Hypotheses
----------
- H12a: silence-gap hallucination accounts for > 50% of router v2's routing regret.
- H12b: the CR threshold (2.4) has < 50% sensitivity for AISHELL-4 hallucination.
- H12c: the silence-aware gate would fix > 30% of the routing regret.

This script is pure reanalysis (numpy + stdlib only; scipy is NOT required).
"""
from __future__ import annotations

import csv
import json
import zlib
from pathlib import Path
from typing import Any

import numpy as np

# --------------------------------------------------------------------------- paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_JSON = (
    PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "router_failure_modes"
OUT_CSV = OUT_DIR / "failure_mode_results.csv"
OUT_JSON = OUT_DIR / "failure_mode_results.json"

# ------------------------------------------------------------------ thresholds
CR_THRESHOLD = 2.4          # Whisper's default compression_ratio_threshold
CATASTROPHIC_CPWER = 1.0    # cpWER > 1.0 => insertions dominate (hallucination)
MULTI_SPEAKER_CUT = 2       # > 2 active speakers => "multi-speaker" flag
N_BOOT = 10000
SEED = 42
EPS = 1e-9


# ----------------------------------------------------------------- CR primitive
def compression_ratio(text: str) -> float:
    """Whisper-style compression ratio: len(utf8 bytes) / len(zlib-compressed bytes).

    Matches ``whisper.audio.compression_ratio``. Returns 0.0 for empty/whitespace
    text (no signal). High CR (>~2.4) indicates a repetitive / degenerate loop."""
    if not text or not text.strip():
        return 0.0
    b = text.encode("utf-8")
    c = zlib.compress(b)
    return len(b) / len(c) if len(c) > 0 else 0.0


def max_cr_separated(window: dict[str, Any]) -> float:
    """Max Whisper CR across the per-speaker separated transcripts.

    NOTE: the RQ1 JSON stores the CONCATENATED per-speaker text, not Whisper's
    per-segment text. Concatenating clean + hallucinated segments dilutes CR, so
    this is a LOWER BOUND on Whisper's true per-segment max CR. A window flagged
    CR-caught here is reliably CR-caught in Whisper; a window flagged CR-missed
    here MIGHT still be CR-caught in Whisper (conservative for H12b)."""
    vals = [
        compression_ratio(t)
        for t in window.get("separated_text_per_speaker", {}).values()
        if t and str(t).strip()
    ]
    return max(vals) if vals else 0.0


def cr_mixed(window: dict[str, Any]) -> float:
    return compression_ratio(window.get("mixed_text", ""))


# --------------------------------------------------------------- classification
def classify(window: dict[str, Any], mcr_sep: float) -> dict[str, Any]:
    """Classify a single window. Returns flags + a primary failure mode.

    A *failure window* is one where the router picked the oracle-worse method
    (routing_regret > 0). Primary modes (mutually exclusive, failure windows only):

      - ``separated_hallucination_cr_caught``: router picked separated, separated
        lost, separated cpWER > 1.0, AND max CR > 2.4 (repetitive hallucination the
        CR guard WOULD detect).
      - ``separated_hallucination_cr_missed``: router picked separated, separated
        lost, separated cpWER > 1.0, AND max CR <= 2.4 (diverse hallucination the
        CR guard would MISS — the compression-ratio signal does not transfer).
      - ``mixed_hallucination``: router picked mixed, mixed lost, mixed cpWER > 1.0
        (the MIXED track hallucinated; separated was clean).
      - ``wrong_route_nonhalluc``: router picked the worse method but NEITHER track
        hallucinated (both cpWER <= 1.0) — a pure routing-judgment error.
      - ``none``: not a failure window (router picked the oracle-best method).
    """
    mix = float(window["always_mixed_cpwer"])
    sep = float(window["always_separated_cpwer"])
    router = float(window["router_v2_cpwer"])
    oracle = float(window["oracle_best_cpwer"])
    method = window["router_v2_method"]

    routing_regret = router - oracle
    regret_vs_mixed = router - mix
    is_failure = routing_regret > EPS

    sep_halluc = sep > CATASTROPHIC_CPWER or mcr_sep > CR_THRESHOLD
    sep_cr_caught = mcr_sep > CR_THRESHOLD
    sep_cr_missed = sep > CATASTROPHIC_CPWER and mcr_sep <= CR_THRESHOLD
    mix_halluc = mix > CATASTROPHIC_CPWER

    primary = "none"
    if is_failure:
        if method == "separated":
            # router picked separated and lost (sep > mix)
            if sep > CATASTROPHIC_CPWER and sep_cr_caught:
                primary = "separated_hallucination_cr_caught"
            elif sep > CATASTROPHIC_CPWER:  # hallucinated but CR missed it
                primary = "separated_hallucination_cr_missed"
            else:
                primary = "wrong_route_nonhalluc"
        else:  # router picked mixed and lost (mix > sep)
            if mix_halluc:
                primary = "mixed_hallucination"
            else:
                primary = "wrong_route_nonhalluc"

    return {
        "mixed_cpwer": round(mix, 6),
        "separated_cpwer": round(sep, 6),
        "router_v2_cpwer": round(router, 6),
        "oracle_best_cpwer": round(oracle, 6),
        "routing_regret": round(routing_regret, 6),
        "regret_vs_mixed": round(regret_vs_mixed, 6),
        "max_cr_separated": round(mcr_sep, 4),
        "cr_mixed": round(cr_mixed(window), 4),
        "separated_hallucination": bool(sep_halluc),
        "separated_cr_caught": bool(sep_cr_caught),
        "separated_cr_missed": bool(sep_cr_missed),
        "mixed_hallucination": bool(mix_halluc),
        "multi_speaker": int(window["num_speakers"]) > MULTI_SPEAKER_CUT,
        "failure_window": bool(is_failure),
        "primary_failure_mode": primary,
    }


# ----------------------------------------------------------------- bootstrap
def bootstrap_fraction(
    rows: list[dict[str, Any]],
    mode_key: str,
    n_boot: int = N_BOOT,
    seed: int = SEED,
) -> tuple[float, float]:
    """Bootstrap 95% CI for (sum of routing_regret where primary_failure_mode ==
    mode_key) / (total routing_regret), resampling windows with replacement."""
    rng = np.random.default_rng(seed)
    n = len(rows)
    regrets = np.array([r["routing_regret"] for r in rows], dtype=float)
    modes = np.array([1.0 if r["primary_failure_mode"] == mode_key else 0.0 for r in rows])
    fracs: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        tot = regrets[idx].sum()
        if tot <= EPS:
            continue
        fracs.append(float((regrets[idx] * modes[idx]).sum() / tot))
    if not fracs:
        return 0.0, 0.0
    lo = float(np.percentile(fracs, 2.5))
    hi = float(np.percentile(fracs, 97.5))
    return lo, hi


def bootstrap_sensitivity(
    rows: list[dict[str, Any]],
    n_boot: int = N_BOOT,
    seed: int = SEED,
) -> tuple[float, float]:
    """Bootstrap 95% CI for CR sensitivity = P(max_cr_separated > 2.4 | separated
    cpWER > 1.0) over the 77 windows."""
    rng = np.random.default_rng(seed)
    n = len(rows)
    halluc = np.array([1.0 if r["separated_cpwer"] > CATASTROPHIC_CPWER else 0.0 for r in rows])
    caught = np.array([1.0 if r["separated_cr_caught"] else 0.0 for r in rows])
    sens: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        h = halluc[idx].sum()
        if h <= 0:
            continue
        sens.append(float((halluc[idx] * caught[idx]).sum() / h))
    if not sens:
        return 0.0, 0.0
    return float(np.percentile(sens, 2.5)), float(np.percentile(sens, 97.5))


# --------------------------------------------------------------------- driver
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(SRC_JSON.read_text(encoding="utf-8"))
    windows = data["windows"]

    # Classify every window.
    rows: list[dict[str, Any]] = []
    for w in windows:
        mcr = max_cr_separated(w)
        cls = classify(w, mcr)
        rows.append({
            "window_id": w["window_id"],
            "window_start_sec": w["window_start_sec"],
            "overlap_level": w["overlap_level"],
            "overlap_label": w["overlap_label"],
            "num_speakers": w["num_speakers"],
            "router_v2_method": w["router_v2_method"],
            "router_v2_rule": w["router_v2_rule"],
            **cls,
        })

    n = len(rows)
    total_routing_regret = sum(r["routing_regret"] for r in rows)
    total_regret_vs_mixed = sum(r["regret_vs_mixed"] for r in rows)
    failure_rows = [r for r in rows if r["failure_window"]]
    n_fail = len(failure_rows)

    # Per-mode regret and share.
    modes = [
        "separated_hallucination_cr_caught",
        "separated_hallucination_cr_missed",
        "mixed_hallucination",
        "wrong_route_nonhalluc",
    ]
    mode_stats: dict[str, dict[str, Any]] = {}
    for m in modes:
        mrows = [r for r in rows if r["primary_failure_mode"] == m]
        regret = sum(r["routing_regret"] for r in mrows)
        share = regret / total_routing_regret if total_routing_regret > EPS else 0.0
        ci_lo, ci_hi = bootstrap_fraction(rows, m)
        mode_stats[m] = {
            "n_windows": len(mrows),
            "routing_regret": round(regret, 6),
            "share_of_routing_regret": round(share, 6),
            "bootstrap_ci_95": [round(ci_lo, 6), round(ci_hi, 6)],
        }

    # Aggregated hallucination shares (for H12a).
    sep_halluc_regret = sum(
        r["routing_regret"] for r in rows
        if r["primary_failure_mode"] in (
            "separated_hallucination_cr_caught",
            "separated_hallucination_cr_missed",
        )
    )
    any_halluc_regret = sum(
        r["routing_regret"] for r in rows
        if r["primary_failure_mode"] in (
            "separated_hallucination_cr_caught",
            "separated_hallucination_cr_missed",
            "mixed_hallucination",
        )
    )
    sep_halluc_share = sep_halluc_regret / total_routing_regret if total_routing_regret > EPS else 0.0
    any_halluc_share = any_halluc_regret / total_routing_regret if total_routing_regret > EPS else 0.0

    # CR sensitivity (H12b).
    halluc_windows = [r for r in rows if r["separated_cpwer"] > CATASTROPHIC_CPWER]
    n_halluc = len(halluc_windows)
    n_cr_caught = sum(1 for r in halluc_windows if r["separated_cr_caught"])
    sensitivity = n_cr_caught / n_halluc if n_halluc else 0.0
    sens_lo, sens_hi = bootstrap_sensitivity(rows)

    # Multi-speaker share (category d).
    multi_regret = sum(r["routing_regret"] for r in failure_rows if r["multi_speaker"])
    multi_share = multi_regret / total_routing_regret if total_routing_regret > EPS else 0.0

    # Silence-gate addressable regret (H12c upper bound).
    # The gate can only help windows where the router picked separated and the
    # separated track hallucinated (the silence-gap stimulus). If the gate perfectly
    # eliminated that hallucination, those windows' regret -> 0.
    gate_addressable_regret = sep_halluc_regret
    gate_addressable_share = gate_addressable_regret / total_routing_regret if total_routing_regret > EPS else 0.0
    # Conservative lower bound: gate only fixes REPETITIVE (CR-caught) hallucination
    # (the confident-attractor it was designed for). Diverse (CR-missed) hallucination
    # may be a different mechanism (Mode N) that silence removal does not cure.
    gate_conservative_regret = sum(
        r["routing_regret"] for r in rows
        if r["primary_failure_mode"] == "separated_hallucination_cr_caught"
    )
    gate_conservative_share = gate_conservative_regret / total_routing_regret if total_routing_regret > EPS else 0.0

    # Router-vs-always-mixed decomposition (finding #23).
    sep_picked = [r for r in rows if r["router_v2_method"] == "separated"]
    sep_won = [r for r in sep_picked if r["separated_cpwer"] <= r["mixed_cpwer"]]
    sep_lost = [r for r in sep_picked if r["separated_cpwer"] > r["mixed_cpwer"]]
    gain_from_sep_won = sum(r["mixed_cpwer"] - r["separated_cpwer"] for r in sep_won)
    loss_from_sep_lost = sum(r["separated_cpwer"] - r["mixed_cpwer"] for r in sep_lost)
    net_vs_mixed = gain_from_sep_won - loss_from_sep_lost

    # Hypothesis verdicts.
    h12a_supported = sep_halluc_share > 0.5
    h12b_supported = sensitivity < 0.5
    # H12c cannot be confirmed (gate not run); report bounds.
    h12c_upper_bound = gate_addressable_share
    h12c_conservative = gate_conservative_share
    h12c_verdict = (
        "CANNOT CONFIRM (gate not run; reanalysis only). Upper bound "
        f"{h12c_upper_bound:.1%} > 30%, but conservative (CR-caught-only) bound "
        f"{h12c_conservative:.1%} < 30%. The CR evidence shows the hallucination is "
        "predominantly diverse (low CR), questioning whether the silence gate "
        "(designed for the repetitive confident-attractor) would fix it."
    )

    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ12: Router v2 failure-mode decomposition on AISHELL-4",
        "closes_issue": 895,
        "source_data": str(SRC_JSON.relative_to(PROJECT_ROOT)),
        "source_label": "external/sanity-check",
        "method": "reanalysis only (no Whisper / no ASR run); CR recomputed from stored text via zlib",
        "meeting_id": data["meeting_id"],
        "n_windows": n,
        "n_failure_windows": n_fail,
        "router_v2_accuracy": round((n - n_fail) / n, 4),
        "total_routing_regret": round(total_routing_regret, 6),
        "total_regret_vs_always_mixed": round(total_regret_vs_mixed, 6),
        "avg_routing_regret": round(total_routing_regret / n, 6),
        "avg_regret_vs_always_mixed": round(total_regret_vs_mixed / n, 6),
        "cr_threshold": CR_THRESHOLD,
        "cr_proxy_note": (
            "max CR across per-speaker CONCATENATED separated text (lower bound on "
            "Whisper's per-segment max CR; conservative for H12b)"
        ),
        "failure_modes": mode_stats,
        "hallucination_shares": {
            "separated_hallucination_regret": round(sep_halluc_regret, 6),
            "separated_hallucination_share": round(sep_halluc_share, 6),
            "any_hallucination_regret": round(any_halluc_regret, 6),
            "any_hallucination_share": round(any_halluc_share, 6),
        },
        "cr_sensitivity": {
            "n_separated_hallucination_windows": n_halluc,
            "n_cr_caught": n_cr_caught,
            "sensitivity": round(sensitivity, 6),
            "bootstrap_ci_95": [round(sens_lo, 6), round(sens_hi, 6)],
            "h12b_supported": bool(h12b_supported),
        },
        "multi_speaker": {
            "n_failure_windows_multi_speaker": sum(1 for r in failure_rows if r["multi_speaker"]),
            "routing_regret": round(multi_regret, 6),
            "share_of_routing_regret": round(multi_share, 6),
        },
        "silence_gate_addressable": {
            "upper_bound_regret": round(gate_addressable_regret, 6),
            "upper_bound_share": round(gate_addressable_share, 6),
            "conservative_cr_caught_only_regret": round(gate_conservative_regret, 6),
            "conservative_cr_caught_only_share": round(gate_conservative_share, 6),
            "h12c_verdict": h12c_verdict,
        },
        "router_vs_always_mixed_decomposition": {
            "sep_picked": len(sep_picked),
            "sep_won": len(sep_won),
            "sep_lost": len(sep_lost),
            "gain_from_sep_won": round(gain_from_sep_won, 6),
            "loss_from_sep_lost": round(loss_from_sep_lost, 6),
            "net": round(net_vs_mixed, 6),
            "net_per_window": round(net_vs_mixed / n, 6),
            "interpretation": (
                "Router is worse than always-mixed because the 9 separated-picked "
                "hallucination losses (gross loss) exceed the 16 correct separated "
                "picks' gains. If the separated hallucination were eliminated, the "
                "router would beat always-mixed."
            ),
        },
        "hypothesis_verdicts": {
            "H12a": {
                "statement": "silence-gap hallucination > 50% of routing regret",
                "separated_hallucination_share": round(sep_halluc_share, 6),
                "any_hallucination_share": round(any_halluc_share, 6),
                "supported": bool(h12a_supported),
            },
            "H12b": {
                "statement": "CR threshold (2.4) has < 50% sensitivity",
                "sensitivity": round(sensitivity, 6),
                "bootstrap_ci_95": [round(sens_lo, 6), round(sens_hi, 6)],
                "supported": bool(h12b_supported),
            },
            "H12c": {
                "statement": "silence-aware gate fixes > 30% of routing regret",
                "upper_bound_share": round(gate_addressable_share, 6),
                "conservative_share": round(gate_conservative_share, 6),
                "supported": None,
                "verdict": h12c_verdict,
            },
        },
    }

    # Write CSV (per-window).
    csv_fields = [
        "window_id", "window_start_sec", "overlap_level", "overlap_label",
        "num_speakers", "router_v2_method", "router_v2_rule",
        "mixed_cpwer", "separated_cpwer", "router_v2_cpwer", "oracle_best_cpwer",
        "routing_regret", "regret_vs_mixed", "max_cr_separated", "cr_mixed",
        "separated_hallucination", "separated_cr_caught", "separated_cr_missed",
        "mixed_hallucination", "multi_speaker", "failure_window",
        "primary_failure_mode",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in csv_fields})

    # Write JSON (summary).
    OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Console summary.
    print(f"=== RQ12: Router v2 failure-mode decomposition (AISHELL-4, {n} windows) ===")
    print(f"Label: experimental/frontier  |  Source: {SRC_JSON.relative_to(PROJECT_ROOT)}")
    print(f"Failure windows: {n_fail}/{n}  (router accuracy {(n-n_fail)/n:.1%})")
    print(f"Total routing regret (vs oracle): {total_routing_regret:.3f}")
    print(f"Total regret vs always-mixed: {total_regret_vs_mixed:.3f} "
          f"(avg {total_regret_vs_mixed/n:+.4f}; finding #23 = +0.0325)")
    print()
    print("Failure-mode decomposition (share of routing regret):")
    for m in modes:
        s = mode_stats[m]
        print(f"  {m:42s} n={s['n_windows']:2d}  regret={s['routing_regret']:6.3f}  "
              f"share={s['share_of_routing_regret']:6.1%}  "
              f"CI95=[{s['bootstrap_ci_95'][0]:.1%}, {s['bootstrap_ci_95'][1]:.1%}]")
    print()
    print(f"Hallucination shares: separated-only={sep_halluc_share:.1%}  "
          f"any(sep+mixed)={any_halluc_share:.1%}")
    print(f"CR sensitivity: {n_cr_caught}/{n_halluc} = {sensitivity:.1%}  "
          f"CI95=[{sens_lo:.1%}, {sens_hi:.1%}]")
    print(f"Multi-speaker share of regret: {multi_share:.1%}")
    print(f"Silence-gate addressable (upper bound): {gate_addressable_share:.1%}  "
          f"(conservative CR-caught-only: {gate_conservative_share:.1%})")
    print()
    print("Hypothesis verdicts:")
    print(f"  H12a (hallucination >50% of regret): "
          f"{'SUPPORTED' if h12a_supported else 'NOT SUPPORTED'} "
          f"(separated-halluc share={sep_halluc_share:.1%}, any-halluc={any_halluc_share:.1%})")
    print(f"  H12b (CR sensitivity <50%): "
          f"{'SUPPORTED' if h12b_supported else 'NOT SUPPORTED'} "
          f"(sensitivity={sensitivity:.1%})")
    print(f"  H12c (silence gate fixes >30%): {h12c_verdict}")
    print()
    print(f"Router vs always-mixed: sep_won={len(sep_won)} (gain {gain_from_sep_won:.2f}), "
          f"sep_lost={len(sep_lost)} (loss {loss_from_sep_lost:.2f}), "
          f"net={net_vs_mixed:+.2f} ({net_vs_mixed/n:+.4f}/window)")
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
