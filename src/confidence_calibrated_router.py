"""Confidence-Calibrated Router (CCR) -- experimental/frontier.

Research question (pre-registered):
  The hallucination_router proved that Whisper's max compression ratio alone can
  route mixed-vs-separated with near-oracle performance (AUC 1.0 for catastrophe
  detection).  But it ignores two other per-segment signals Whisper exposes:
  no_speech_prob and avg_logprob.  The reference_free_qe analysis showed that
  compression_ratio is the strongest single signal, but did not test whether a
  multi-signal composite outperforms it for *routing* (pick-the-better-candidate)
  as opposed to quality *estimation* (predict absolute CER).

  This module asks:

  RQ1 (graded routing): Does a multi-signal composite confidence score
     outperform the single-signal compression-ratio router when picking the
     better of {mixed, separated, separated+trim}?
  RQ2 (signal contribution): Which signals add marginal value beyond
     compression_ratio alone?
  RQ3 (robustness): Does the best composite generalize across overlap tiers,
     or does it overfit to the high-overlap regime where compression_ratio is
     already dominant?

  Hypotheses:
    H1: A weighted composite (CR + NSP + repetition) has lower routing regret
        than CR alone, especially at low-overlap where the signal is subtle.
    H2: no_speech_prob contributes most at low overlap (silence-injection tail),
        while compression_ratio dominates at high overlap.
    H3: The composite's advantage is largest on the "hard" regime where
        |CER_mixed - CER_sep| < 0.1 (near-tie samples where single signals
        are ambiguous).

  Labels: experimental/frontier.  Uses existing phase_curve.csv (no new ASR).
  CER is evaluation target only, never a routing input.  Stable tables untouched;
  outputs go to results/frontier/confidence_calibrated_router/.

  What is useful even if hypotheses fail:
    If CR alone remains optimal, that is itself a finding: the extra signals are
    redundant for routing, which simplifies deployable systems.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Callable

from .config import PROJECT_ROOT

PHASE_CURVE = PROJECT_ROOT / "results" / "frontier" / "separation_tax" / "phase_curve.csv"
HALLUC_ROUTER_CURVE = (
    PROJECT_ROOT / "results" / "frontier" / "hallucination_router" / "routing_curve.csv"
)
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "confidence_calibrated_router"

# Known degeneracy thresholds from Whisper defaults and the QE study.
CR_THRESHOLD = 2.4
NSP_THRESHOLD = 0.6


# ---- Pure signal extraction (unit-testable, no I/O) ----------------------------

def extract_signals(row: dict[str, Any], arm: str) -> dict[str, float]:
    """Extract available confidence signals for a candidate arm from a phase_curve row.

    Arms: 'mixed', 'sep' (raw separated), 'sep_trim' (silence-trimmed separated).
    Returns a dict of signal_name -> value.  Missing values default to 0.0.
    """
    if arm == "mixed":
        return {
            "compression_ratio": _f(row.get("cr_mixed", 0.0)),
            "no_speech_prob": 0.0,  # not available for mixed in phase_curve
            "repetition_count": _f(row.get("rep_mixed", 0.0)),
        }
    elif arm == "sep":
        return {
            "compression_ratio": max(
                _f(row.get("cr_sep1", 0.0)), _f(row.get("cr_sep2", 0.0))
            ),
            "no_speech_prob": max(
                _f(row.get("nsp_sep1", 0.0)), _f(row.get("nsp_sep2", 0.0))
            ),
            "repetition_count": _f(row.get("rep_sep1", 0.0))
            + _f(row.get("rep_sep2", 0.0)),
        }
    elif arm == "sep_trim":
        # sep_trim uses same separation signals (they come from the same tracks,
        # just trimmed).  The CR/NSP may differ after trim, but phase_curve only
        # records the untrimmed signals.  We use the sep signals as proxy.
        return {
            "compression_ratio": max(
                _f(row.get("cr_sep1", 0.0)), _f(row.get("cr_sep2", 0.0))
            ),
            "no_speech_prob": max(
                _f(row.get("nsp_sep1", 0.0)), _f(row.get("nsp_sep2", 0.0))
            ),
            "repetition_count": _f(row.get("rep_sep1", 0.0))
            + _f(row.get("rep_sep2", 0.0)),
        }
    raise ValueError(f"Unknown arm: {arm}")


def get_cer(row: dict[str, Any], arm: str) -> float:
    """Get CER for an arm from a phase_curve row."""
    key = f"cer_{arm}"
    return _f(row.get(key, float("nan")))


# ---- Scoring functions: signal dict -> confidence score (higher = better) -------

def score_cr_only(signals: dict[str, float]) -> float:
    """Baseline: inverse compression ratio only (matches hallucination_router)."""
    cr = signals["compression_ratio"]
    return 1.0 / (1.0 + cr)


def score_cr_nsp(signals: dict[str, float]) -> float:
    """Two-signal composite: CR + no_speech_prob."""
    cr = signals["compression_ratio"]
    nsp = signals["no_speech_prob"]
    # Both are degeneracy signals (higher = worse).  Normalize to [0,1] confidences.
    cr_conf = 1.0 / (1.0 + cr)
    nsp_conf = 1.0 - nsp
    return 0.6 * cr_conf + 0.4 * nsp_conf


def score_cr_nsp_rep(signals: dict[str, float]) -> float:
    """Three-signal composite: CR + NSP + repetition."""
    cr = signals["compression_ratio"]
    nsp = signals["no_speech_prob"]
    rep = signals["repetition_count"]
    cr_conf = 1.0 / (1.0 + cr)
    nsp_conf = 1.0 - min(nsp, 1.0)
    rep_conf = 1.0 / (1.0 + rep)
    return 0.5 * cr_conf + 0.3 * nsp_conf + 0.2 * rep_conf


def score_cr_log(signals: dict[str, float]) -> float:
    """Logarithmic CR scaling (emphasizes differences at low CR)."""
    cr = signals["compression_ratio"]
    import math

    return 1.0 / (1.0 + math.log1p(cr))


def score_threshold_gate(signals: dict[str, float]) -> float:
    """Threshold-based gating: flag degenerate if ANY signal exceeds threshold,
    otherwise use CR confidence.  Binary gate + continuous fallback."""
    cr = signals["compression_ratio"]
    nsp = signals["no_speech_prob"]
    if cr > CR_THRESHOLD or nsp > NSP_THRESHOLD:
        return 0.0  # flagged as degenerate
    return 1.0 / (1.0 + cr)


# All scoring methods for systematic comparison.
SCORING_METHODS: dict[str, Callable[[dict[str, float]], float]] = {
    "cr_only": score_cr_only,
    "cr_nsp": score_cr_nsp,
    "cr_nsp_rep": score_cr_nsp_rep,
    "cr_log": score_cr_log,
    "threshold_gate": score_threshold_gate,
}


# ---- Routing logic (unit-testable) ---------------------------------------------

def route_by_confidence(
    scores: dict[str, float],
    allowed: list[str] | None = None,
) -> str:
    """Pick the arm with the highest confidence score.  Stable tie-break by order."""
    if allowed is None:
        allowed = list(scores.keys())
    if not allowed:
        return ""
    best = None
    best_score = -float("inf")
    for arm in allowed:
        s = scores.get(arm, -float("inf"))
        if s > best_score:
            best_score = s
            best = arm
    return best if best is not None else allowed[0]


def evaluate_routing_policies(
    rows: list[dict[str, Any]],
    arms: list[str],
    split: str | None = None,
) -> dict[str, Any]:
    """Evaluate all scoring methods + baselines against the oracle.

    Returns per-policy mean CER and regret vs oracle, optionally filtered by split.
    """
    sub = [r for r in rows if split is None or r.get("config") == "greedy"]
    if split:
        sub = [r for r in sub if True]  # phase_curve doesn't have split; keep all

    if not sub:
        return {"split": split or "all", "n": 0}

    # Collect per-policy CER values
    policy_cer: dict[str, list[float]] = {m: [] for m in SCORING_METHODS}
    policy_cer["fixed_mixed"] = []
    policy_cer["fixed_sep"] = []
    policy_cer["oracle"] = []

    for row in sub:
        cers = {arm: get_cer(row, arm) for arm in arms}
        # skip rows where any arm has NaN CER
        if any(c != c for c in cers.values()):
            continue

        oracle_cer = min(cers.values())
        policy_cer["fixed_mixed"].append(cers["mixed"])
        policy_cer["fixed_sep"].append(cers.get("sep", cers.get("mixed", 0.0)))
        policy_cer["oracle"].append(oracle_cer)

        # Score each arm with each method
        signals = {arm: extract_signals(row, arm) for arm in arms}
        for method_name, score_fn in SCORING_METHODS.items():
            arm_scores = {arm: score_fn(signals[arm]) for arm in arms}
            chosen = route_by_confidence(arm_scores, arms)
            policy_cer[method_name].append(cers[chosen])

    def mean(xs: list[float]) -> float:
        return round(sum(xs) / len(xs), 6) if xs else 0.0

    n = len(policy_cer["oracle"])
    if n == 0:
        return {"split": split or "all", "n": 0}

    oracle_mean = mean(policy_cer["oracle"])
    result: dict[str, Any] = {
        "split": split or "all",
        "n": n,
        "arms": arms,
        "mean_cer": {},
        "regret_vs_oracle": {},
    }
    for policy, cers in policy_cer.items():
        m = mean(cers)
        result["mean_cer"][policy] = m
        result["regret_vs_oracle"][policy] = round(m - oracle_mean, 6)

    ranked = sorted(result["regret_vs_oracle"].items(), key=lambda kv: kv[1])
    result["best_policy"] = ranked[0][0]  # includes oracle (always 0 regret)
    result["best_reference_free"] = next(
        (k for k, _ in ranked if k != "oracle"), ranked[0][0]
    )
    return result


def analyze_regret_by_overlap(
    rows: list[dict[str, Any]],
    arms: list[str],
) -> list[dict[str, Any]]:
    """Per-overlap-ratio analysis of routing regret for each scoring method.

    This reveals H3: whether the composite advantage concentrates at specific
    overlap regimes.
    """
    greedy = [r for r in rows if r.get("config") == "greedy"]
    ratios = sorted({float(r["overlap_ratio"]) for r in greedy})
    out: list[dict[str, Any]] = []

    for ratio in ratios:
        at_ratio = [r for r in greedy if _f(r["overlap_ratio"]) == ratio]
        result = evaluate_routing_policies(at_ratio, arms)
        result["overlap_ratio"] = ratio
        out.append(result)
    return out


def hard_regime_analysis(
    rows: list[dict[str, Any]],
    arms: list[str],
    margin: float = 0.1,
) -> dict[str, Any]:
    """H3 test: evaluate routing on "hard" samples where |CER_mixed - CER_sep| < margin.

    These are the samples where single-signal routing is most ambiguous.
    """
    greedy = [r for r in rows if r.get("config") == "greedy"]
    hard = []
    easy = []
    for r in greedy:
        cer_m = get_cer(r, "mixed")
        cer_s = get_cer(r, "sep_trim" if "sep_trim" in arms else "sep")
        if cer_m != cer_m or cer_s != cer_s:
            continue
        if abs(cer_m - cer_s) < margin:
            hard.append(r)
        else:
            easy.append(r)

    hard_result = evaluate_routing_policies(hard, arms) if hard else {"n": 0}
    easy_result = evaluate_routing_policies(easy, arms) if easy else {"n": 0}

    # Compare: how much does the best composite improve over cr_only in hard vs easy?
    improvement = {}
    for regime_name, regime_result in [("hard", hard_result), ("easy", easy_result)]:
        if regime_result.get("n", 0) == 0:
            continue
        cr_regret = regime_result.get("regret_vs_oracle", {}).get("cr_only", 0.0)
        for method in SCORING_METHODS:
            if method == "cr_only":
                continue
            method_regret = regime_result.get("regret_vs_oracle", {}).get(method, 0.0)
            key = f"{regime_name}_{method}_vs_cr_only"
            improvement[key] = round(cr_regret - method_regret, 6)

    return {
        "margin": margin,
        "n_hard": hard_result.get("n", 0),
        "n_easy": easy_result.get("n", 0),
        "hard": hard_result,
        "easy": easy_result,
        "improvement": improvement,
    }


def signal_contribution_analysis(
    rows: list[dict[str, Any]],
    arms: list[str],
) -> dict[str, Any]:
    """RQ2: measure the marginal contribution of each signal beyond CR alone.

    Reports the regret reduction when adding each signal.
    """
    result_2way = evaluate_routing_policies(rows, arms)
    cr_regret = result_2way.get("regret_vs_oracle", {}).get("cr_only", 0.0)

    contributions = {}
    for method in SCORING_METHODS:
        if method == "cr_only":
            continue
        method_regret = result_2way.get("regret_vs_oracle", {}).get(method, 0.0)
        contributions[method] = {
            "regret": method_regret,
            "improvement_over_cr_only": round(cr_regret - method_regret, 6),
        }

    return {
        "baseline_cr_only_regret": cr_regret,
        "contributions": contributions,
        "best_method": min(contributions.items(), key=lambda kv: kv[1]["regret"])[0]
        if contributions
        else "cr_only",
    }


# ---- Driver (reads existing data -- no ASR runs) --------------------------------

def run(out_dir: Path) -> dict[str, Any]:
    """Main analysis driver.  Reads phase_curve.csv and produces full CCR analysis."""
    if not PHASE_CURVE.exists():
        raise FileNotFoundError(
            f"Missing phase curve data: {PHASE_CURVE.relative_to(PROJECT_ROOT)}. "
            "Run 'python -m src.separation_tax_phase' first."
        )

    with PHASE_CURVE.open("r", newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    # Filter to greedy config (matches the hallucination_router evaluation)
    greedy = [r for r in rows if r.get("config") == "greedy"]
    arms_3way = ["mixed", "sep", "sep_trim"]
    arms_2way = ["mixed", "sep_trim"]

    out_dir.mkdir(parents=True, exist_ok=True)

    # ---- RQ1: Main routing evaluation ------------------------------------------
    eval_3way = evaluate_routing_policies(greedy, arms_3way)
    eval_2way = evaluate_routing_policies(greedy, arms_2way)

    # ---- RQ2: Signal contribution ----------------------------------------------
    contrib_3way = signal_contribution_analysis(greedy, arms_3way)
    contrib_2way = signal_contribution_analysis(greedy, arms_2way)

    # ---- Per-overlap-ratio analysis (RQ3 robustness) ---------------------------
    per_ratio_3way = analyze_regret_by_overlap(greedy, arms_3way)
    per_ratio_2way = analyze_regret_by_overlap(greedy, arms_2way)

    # ---- Hard regime analysis (H3) ---------------------------------------------
    hard_3way = hard_regime_analysis(greedy, arms_3way, margin=0.1)
    hard_2way = hard_regime_analysis(greedy, arms_2way, margin=0.1)

    # ---- Comparison with hallucination_router if available ----------------------
    halluc_comparison = {}
    if HALLUC_ROUTER_CURVE.exists():
        with HALLUC_ROUTER_CURVE.open("r", newline="", encoding="utf-8-sig") as fh:
            halluc_rows = list(csv.DictReader(fh))
        halluc_summary = _compare_with_halluc_router(halluc_rows, greedy)

    # ---- Write outputs ----------------------------------------------------------
    summary = {
        "n_greedy_rows": len(greedy),
        "scoring_methods": list(SCORING_METHODS.keys()),
        "eval_3way": eval_3way,
        "eval_2way": eval_2way,
        "signal_contribution_3way": contrib_3way,
        "signal_contribution_2way": contrib_2way,
        "hard_regime_3way": hard_3way,
        "hard_regime_2way": hard_2way,
    }

    if HALLUC_ROUTER_CURVE.exists():
        summary["hallucination_router_comparison"] = halluc_comparison

    (out_dir / "ccr_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Per-ratio CSV
    _write_per_ratio_csv(per_ratio_3way, out_dir / "regret_by_ratio_3way.csv")
    _write_per_ratio_csv(per_ratio_2way, out_dir / "regret_by_ratio_2way.csv")

    # Policy comparison CSV
    _write_policy_comparison_csv(eval_3way, out_dir / "policy_comparison_3way.csv")
    _write_policy_comparison_csv(eval_2way, out_dir / "policy_comparison_2way.csv")

    # Figure
    try:
        render_figure(per_ratio_3way, out_dir)
    except Exception as exc:
        print(f"[ccr] figure skipped: {exc}", flush=True)

    print(
        f"[ccr] n={len(greedy)} best_3way={eval_3way.get('best_policy')} "
        f"best_2way={eval_2way.get('best_policy')} "
        f"wrote {OUT_DIR.relative_to(PROJECT_ROOT)}",
        flush=True,
    )
    return summary


def _compare_with_halluc_router(
    halluc_rows: list[dict[str, Any]], ccr_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """Compare CCR against the hallucination_router on the same synthetic split."""
    # Hallucination router summary: mean regret per policy
    def mean(xs: list[float]) -> float:
        return round(sum(xs) / len(xs), 6) if xs else 0.0

    halluc_oracle = [_f(r.get("cer_oracle", 0)) for r in halluc_rows]
    halluc_oracle_mean = mean(halluc_oracle)

    halluc_regret = {}
    for policy in ("fixed_mixed", "fixed_sep", "fixed_sep_trim",
                    "halluc_2way", "halluc_3way", "overlap_router"):
        vals = [_f(r.get(f"cer_{policy}", 0)) for r in halluc_rows]
        halluc_regret[policy] = round(mean(vals) - halluc_oracle_mean, 6)

    return {
        "halluc_n": len(halluc_rows),
        "halluc_regret": halluc_regret,
        "note": "CCR uses phase_curve data; hallucination_router uses its own re-transcription."
        "  Direct comparison is indicative, not controlled.",
    }


def _write_per_ratio_csv(
    per_ratio: list[dict[str, Any]], path: Path
) -> None:
    """Write per-overlap-ratio regret comparison CSV."""
    if not per_ratio:
        return
    methods = list(SCORING_METHODS.keys()) + ["fixed_mixed", "fixed_sep", "oracle"]
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(["overlap_ratio", "n"] + [f"regret_{m}" for m in methods])
        for r in per_ratio:
            regrets = r.get("regret_vs_oracle", {})
            row = [r.get("overlap_ratio", ""), r.get("n", 0)]
            row += [regrets.get(m, "") for m in methods]
            writer.writerow(row)


def _write_policy_comparison_csv(eval_result: dict[str, Any], path: Path) -> None:
    """Write flat policy comparison CSV."""
    mean_cer = eval_result.get("mean_cer", {})
    regret = eval_result.get("regret_vs_oracle", {})
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(["policy", "mean_cer", "regret_vs_oracle", "reference_free"])
        for policy in sorted(mean_cer.keys()):
            ref_free = "yes" if policy != "oracle" else "no(oracle)"
            writer.writerow([policy, mean_cer[policy], regret.get(policy, ""), ref_free])


# ---- Visualization ---------------------------------------------------------------

def render_figure(per_ratio: list[dict[str, Any]], out_dir: Path) -> Path | None:
    """Plot: regret vs overlap ratio for each scoring method."""
    if not per_ratio:
        return None

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ratios = [r["overlap_ratio"] for r in per_ratio]
    methods = list(SCORING_METHODS.keys())

    fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    colors = {
        "cr_only": "#e45756",
        "cr_nsp": "#4c78a8",
        "cr_nsp_rep": "#72b7b2",
        "cr_log": "#f58518",
        "threshold_gate": "#54a24b",
    }

    for method in methods:
        regrets = [
            r.get("regret_vs_oracle", {}).get(method, 0.0) for r in per_ratio
        ]
        ax.plot(
            ratios, regrets, "-o",
            color=colors.get(method, "gray"),
            label=method, markersize=4,
        )

    # Add oracle (regret=0) and fixed baselines
    for baseline, style in [("fixed_mixed", ":"), ("fixed_sep", "--")]:
        regrets = [
            r.get("regret_vs_oracle", {}).get(baseline, 0.0) for r in per_ratio
        ]
        ax.plot(ratios, regrets, style, color="gray", alpha=0.5, label=baseline)

    ax.axhline(0.0, color="black", lw=0.8, label="oracle")
    ax.set_xlabel("overlap ratio")
    ax.set_ylabel("routing regret (mean CER - oracle CER)")
    ax.set_title("Confidence-Calibrated Router: regret vs overlap ratio (Whisper-tiny, zh)")
    ax.legend(fontsize=8, ncol=2)
    ax.grid(alpha=0.3)

    fig.tight_layout()
    fig_path = out_dir / "ccr_regret_by_ratio.png"
    fig.savefig(fig_path, dpi=160)
    plt.close(fig)
    print(f"[ccr] wrote {fig_path.relative_to(PROJECT_ROOT)}", flush=True)
    return fig_path


# ---- Helpers --------------------------------------------------------------------

def _f(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Confidence-Calibrated Router: multi-signal reference-free routing (frontier)."
    )
    parser.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(Path(args.out_dir))


if __name__ == "__main__":
    main()
