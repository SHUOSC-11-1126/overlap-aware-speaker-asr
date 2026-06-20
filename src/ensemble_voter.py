"""Multi-Model Ensemble Voter for overlap-aware ASR -- experimental/frontier.

Research question (pre-registered):
  The CCR study showed that single-model compression_ratio is near-optimal for
  routing mixed-vs-separated.  But that only uses ONE model's internal confidence.
  This module asks a fundamentally different question: does AGREEMENT between
  multiple Whisper model sizes (tiny, base, small) predict transcript quality
  better than any single model's confidence signals?

  The intuition: if all three models produce nearly identical text, the transcript
  is likely correct (high inter-model consensus → high confidence).  If they
  disagree, at least one is hallucinating — the disagreement magnitude tells us
  how risky the transcript is.

  RQ1 (signal quality): Does inter-model agreement (measured by pairwise CER
     between model outputs) correlate with transcript quality (CER vs reference)?
     We report Spearman correlation and detection AUC.
  RQ2 (routing): Does an agreement-based router outperform the compression-ratio
     router for picking the better of {mixed, separated}?
  RQ3 (complement): Is inter-model agreement complementary to compression_ratio?
     Does combining them (CR + agreement) beat either alone?
  RQ4 (cost): How much extra compute does multi-model voting require vs single-model?

  Hypotheses:
    H1: Pairwise model agreement has moderate positive correlation with quality
        (Spearman > 0.3 vs true CER).
    H2: The agreement router has lower regret than CR-only on "hard" samples
        (where |CER_mixed - CER_sep| < 0.1).
    H3: Combining CR + agreement beats either signal alone.

  Labels: experimental/frontier. References are synthetic/silver (Whisper-small on
  clean snippets). ASR = Whisper-{tiny,base,small}. CER is evaluation target only,
  never a routing input. Stable tables untouched; outputs go to
  results/frontier/ensemble_voter/.

  What is useful even if hypotheses fail:
    If agreement does NOT improve routing, that is a finding: inter-model diversity
    is redundant with single-model confidence for this task, saving compute.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT
from .evaluate_cer import compute_cer, repetition_count_from_text
from .generate_synthetic_overlap import build_mixture, read_mono_audio
from .separation_tax_phase import (
    _to_float,
    load_snippet_reference,
    select_pairs,
    trim_silence,
    rank_auc,
    bootstrap_ci,
    WHISPER_CONFIGS,
)

TARGET_SR = 16000
ENSEMBLE_MODELS = ["tiny", "base"]
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "ensemble_voter"


# ---- Pure agreement metrics (unit-testable, no I/O) ------------------------------

def text_cer(text_a: str, text_b: str) -> float:
    """Character error rate between two texts (treats text_a as reference)."""
    if not text_a:
        return 0.0 if not text_b else 1.0
    result = compute_cer(text_a, text_b)
    return result["cer"]


def symmetric_cer(text_a: str, text_b: str) -> float:
    """Symmetric agreement: average of both directions of CER."""
    return (text_cer(text_a, text_b) + text_cer(text_b, text_a)) / 2.0


def length_ratio(text_a: str, text_b: str) -> float:
    """Ratio of text lengths.  1.0 = perfect agreement on length."""
    la, lb = len(text_a), len(text_b)
    if la == 0 and lb == 0:
        return 1.0
    if la == 0 or lb == 0:
        return 0.0
    return min(la, lb) / max(la, lb)


def agreement_score(texts: dict[str, str]) -> float:
    """Composite agreement score across all model pairs.  Higher = more agreement.

    Combines pairwise symmetric CER (lower = more agreement) and length ratios.
    Returns a score in [0, 1] where 1 = perfect agreement.
    """
    models = sorted(texts.keys())
    if len(models) < 2:
        return 1.0
    pairs = []
    for i, m1 in enumerate(models):
        for m2 in models[i + 1:]:
            pairs.append((m1, m2))
    if not pairs:
        return 1.0

    cer_scores = []
    lr_scores = []
    for m1, m2 in pairs:
        scer = symmetric_cer(texts[m1], texts[m2])
        cer_scores.append(1.0 / (1.0 + scer * 10))  # map CER to [0,1] confidence
        lr_scores.append(length_ratio(texts[m1], texts[m2]))

    return sum(cer_scores + lr_scores) / (len(cer_scores) + len(lr_scores))


def ensemble_confidence(
    texts: dict[str, str],
    cr_signals: dict[str, float] | None = None,
) -> dict[str, float]:
    """Compute ensemble confidence metrics from multi-model transcripts.

    Returns multiple confidence signals for analysis.
    """
    agr = agreement_score(texts)

    result = {"agreement": agr}

    # Also compute: min/max individual agreement
    models = sorted(texts.keys())
    if len(models) >= 2:
        pairwise = []
        for i, m1 in enumerate(models):
            for m2 in models[i + 1:]:
                pairwise.append(symmetric_cer(texts[m1], texts[m2]))
        result["min_pairwise_cer"] = min(pairwise)
        result["max_pairwise_cer"] = max(pairwise)
        result["mean_pairwise_cer"] = sum(pairwise) / len(pairwise)

    # Length variance across models
    lengths = [len(texts[m]) for m in models]
    if lengths:
        mean_len = sum(lengths) / len(lengths)
        if mean_len > 0:
            result["length_cv"] = (
                (sum((l - mean_len) ** 2 for l in lengths) / len(lengths)) ** 0.5
                / mean_len
            )
        else:
            result["length_cv"] = 0.0

    # Repetition consensus: do all models produce similar repetition counts?
    reps = [repetition_count_from_text(texts[m]) for m in models]
    result["max_repetition"] = max(reps) if reps else 0
    result["repetition_spread"] = max(reps) - min(reps) if reps else 0

    # Combined: agreement + compression_ratio (RQ3)
    if cr_signals:
        cr_conf = {m: 1.0 / (1.0 + cr_signals.get(m, 0.0)) for m in models}
        mean_cr_conf = sum(cr_conf.values()) / len(cr_conf) if cr_conf else 0.0
        result["combined_agreement_cr"] = 0.5 * agr + 0.5 * mean_cr_conf

    return result


# ---- Routing by ensemble agreement (unit-testable) --------------------------------

def route_by_agreement(
    agreement: dict[str, float],
    allowed: list[str] | None = None,
) -> str:
    """Pick the arm with highest ensemble agreement.  Tie-break by order."""
    if allowed is None:
        allowed = list(agreement.keys())
    if not allowed:
        return ""
    best = None
    best_score = -1.0
    for arm in allowed:
        s = agreement.get(arm, -1.0)
        if s > best_score:
            best_score = s
            best = arm
    return best if best is not None else allowed[0]


# ---- Multi-model transcription driver (requires Whisper) -------------------------

def transcribe_multi_model(
    audio: Any,
    models: dict[str, Any],
    language: str = "zh",
) -> dict[str, dict[str, Any]]:
    """Run multiple Whisper models on the same audio.  Returns per-model results."""
    results = {}
    for name, model in models.items():
        cfg = WHISPER_CONFIGS["greedy"]
        audio_arr = __import__("numpy").ascontiguousarray(
            __import__("numpy").asarray(audio, dtype=__import__("numpy").float32)
        )
        t0 = time.perf_counter()
        out = model.transcribe(audio_arr, language=language, verbose=False, fp16=False, **cfg)
        runtime = time.perf_counter() - t0
        segs = out.get("segments", [])
        text = str(out.get("text", "")).strip()
        results[name] = {
            "text": text,
            "n_segments": len(segs),
            "runtime_sec": round(runtime, 3),
            "max_cr": float(max((s.get("compression_ratio", 0.0) for s in segs), default=0.0)),
            "max_nsp": float(max((s.get("no_speech_prob", 0.0) for s in segs), default=0.0)),
            "mean_logprob": float(
                __import__("numpy").mean([s.get("avg_logprob", 0.0) for s in segs])
            ) if segs else 0.0,
        }
    return results


# ---- Driver (runs ASR on synthetic data) -------------------------------------------

def run(
    out_dir: Path,
    num_pairs: int = 5,
    model_names: list[str] | None = None,
    quick: bool = False,
) -> dict[str, Any]:
    """Main analysis driver.  Runs multi-model ASR and computes agreement analysis."""
    import whisper as whisper_module

    if model_names is None:
        model_names = ENSEMBLE_MODELS

    out_dir.mkdir(parents=True, exist_ok=True)

    # Load all models upfront
    models = {}
    for name in model_names:
        print(f"[ensemble] loading Whisper-{name}...", flush=True)
        models[name] = whisper_module.load_model(name)
    # Also need "small" as the primary model for the mixed/separated comparison
    if "small" not in models:
        print("[ensemble] loading Whisper-small (primary)...", flush=True)
        models["small"] = whisper_module.load_model("small")

    ratios = [0.0, 0.15, 0.35, 0.60, 0.90] if quick else [
        0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45,
        0.50, 0.60, 0.70, 0.80, 0.90,
    ]
    plans = select_pairs(num_pairs)

    fieldnames = [
        "pair_id", "con", "pro", "overlap_ratio",
        "ref_text_length",
        # Per-arm, per-model text
        "text_mixed_small", "text_mixed_tiny", "text_mixed_base",
        "text_sep_small", "text_sep_tiny", "text_sep_base",
        # Per-arm CER (vs reference)
        "cer_mixed", "cer_sep", "cer_sep_trim",
        # Agreement scores per arm
        "agr_mixed", "agr_sep",
        # Combined scores
        "combined_cr_agr_mixed", "combined_cr_agr_sep",
        # Compression ratios
        "cr_mixed_small", "cr_mixed_tiny", "cr_mixed_base",
        "cr_sep_small", "cr_sep_tiny", "cr_sep_base",
        # Runtimes
        "runtime_mixed_total", "runtime_sep_total",
        # Routing
        "choice_cr_only", "choice_agreement", "choice_combined",
    ]

    rows: list[dict[str, Any]] = []
    curve_path = out_dir / "ensemble_curve.csv"

    with curve_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()

        for pi, plan in enumerate(plans):
            s1 = read_mono_audio(plan.con_path)
            s2 = read_mono_audio(plan.pro_path)
            ref = plan.con_text + plan.pro_text

            for ratio in ratios:
                mixed, track1, track2, _ = build_mixture(s1, s2, ratio)
                t1_trim = trim_silence(track1)
                t2_trim = trim_silence(track2)

                # --- Multi-model transcription ---
                mixed_results = transcribe_multi_model(mixed, models)
                sep_results_1 = transcribe_multi_model(track1, models)
                sep_results_2 = transcribe_multi_model(track2, models)
                trim_results_1 = transcribe_multi_model(t1_trim, models)
                trim_results_2 = transcribe_multi_model(t2_trim, models)

                # --- Build per-arm texts (per model) ---
                arm_texts: dict[str, dict[str, str]] = {"mixed": {}, "sep": {}, "sep_trim": {}}
                for mname in models:
                    arm_texts["mixed"][mname] = mixed_results[mname]["text"]
                    arm_texts["sep"][mname] = (
                        sep_results_1[mname]["text"] + sep_results_2[mname]["text"]
                    )
                    arm_texts["sep_trim"][mname] = (
                        trim_results_1[mname]["text"] + trim_results_2[mname]["text"]
                    )

                # --- CER vs reference (use "small" as primary) ---
                cer_mixed = compute_cer(ref, arm_texts["mixed"].get("small", ""))["cer"]
                cer_sep = compute_cer(ref, arm_texts["sep"].get("small", ""))["cer"]
                cer_sep_trim = compute_cer(ref, arm_texts["sep_trim"].get("small", ""))["cer"]

                # --- Agreement scores ---
                agr_mixed = agreement_score(arm_texts["mixed"])
                agr_sep = agreement_score(arm_texts["sep"])

                # --- Compression ratios ---
                cr_mixed = {m: mixed_results[m]["max_cr"] for m in models}
                cr_sep = {
                    m: max(sep_results_1[m]["max_cr"], sep_results_2[m]["max_cr"])
                    for m in models
                }

                # --- Combined signals ---
                agr_scores = {"mixed": agr_mixed, "sep": agr_sep}
                cr_mixed_mean = sum(cr_mixed.values()) / len(cr_mixed)
                cr_sep_mean = sum(cr_sep.values()) / len(cr_sep)
                cr_scores = {
                    "mixed": 1.0 / (1.0 + cr_mixed_mean),
                    "sep": 1.0 / (1.0 + cr_sep_mean),
                }
                combined_scores = {
                    arm: 0.5 * agr_scores[arm] + 0.5 * cr_scores[arm]
                    for arm in agr_scores
                }

                # --- Routing ---
                cr_choice = "mixed" if cr_scores["mixed"] > cr_scores["sep"] else "sep"
                agr_choice = route_by_agreement(agr_scores, ["mixed", "sep"])
                combined_choice = route_by_agreement(combined_scores, ["mixed", "sep"])

                # --- Runtimes ---
                rt_mixed = sum(mixed_results[m]["runtime_sec"] for m in models)
                rt_sep = sum(
                    sep_results_1[m]["runtime_sec"] + sep_results_2[m]["runtime_sec"]
                    for m in models
                )

                row = {
                    "pair_id": pi, "con": plan.con_path.name, "pro": plan.pro_path.name,
                    "overlap_ratio": ratio, "ref_text_length": len(ref),
                    "text_mixed_small": arm_texts["mixed"].get("small", ""),
                    "text_mixed_tiny": arm_texts["mixed"].get("tiny", ""),
                    "text_mixed_base": arm_texts["mixed"].get("base", ""),
                    "text_sep_small": arm_texts["sep"].get("small", ""),
                    "text_sep_tiny": arm_texts["sep"].get("tiny", ""),
                    "text_sep_base": arm_texts["sep"].get("base", ""),
                    "cer_mixed": round(cer_mixed, 6),
                    "cer_sep": round(cer_sep, 6),
                    "cer_sep_trim": round(cer_sep_trim, 6),
                    "agr_mixed": round(agr_mixed, 6),
                    "agr_sep": round(agr_sep, 6),
                    "combined_cr_agr_mixed": round(combined_scores["mixed"], 6),
                    "combined_cr_agr_sep": round(combined_scores["sep"], 6),
                    "cr_mixed_small": round(cr_mixed.get("small", 0), 4),
                    "cr_mixed_tiny": round(cr_mixed.get("tiny", 0), 4),
                    "cr_mixed_base": round(cr_mixed.get("base", 0), 4),
                    "cr_sep_small": round(cr_sep.get("small", 0), 4),
                    "cr_sep_tiny": round(cr_sep.get("tiny", 0), 4),
                    "cr_sep_base": round(cr_sep.get("base", 0), 4),
                    "runtime_mixed_total": round(rt_mixed, 3),
                    "runtime_sep_total": round(rt_sep, 3),
                    "choice_cr_only": cr_choice,
                    "choice_agreement": agr_choice,
                    "choice_combined": combined_choice,
                }
                writer.writerow(row)
                rows.append(row)

            fh.flush()
            print(
                f"[ensemble] pair {pi + 1}/{len(plans)} done "
                f"({plan.con_path.name}+{plan.pro_path.name})",
                flush=True,
            )

    # --- Analysis ---
    summary = analyze(rows, out_dir)
    print(
        f"[ensemble] n={len(rows)} wrote {OUT_DIR.relative_to(PROJECT_ROOT)}",
        flush=True,
    )
    return summary


def analyze(rows: list[dict[str, Any]], out_dir: Path) -> dict[str, Any]:
    """Analyze the ensemble voting results."""

    def _mean(xs: list[float]) -> float:
        vals = [x for x in xs if x == x]
        return round(sum(vals) / len(vals), 6) if vals else 0.0

    # Overall routing comparison
    cer_mixed = [float(r["cer_mixed"]) for r in rows]
    cer_sep = [float(r["cer_sep"]) for r in rows]
    oracle = [min(m, s) for m, s in zip(cer_mixed, cer_sep)]

    policies = {}
    for policy_key in ("choice_cr_only", "choice_agreement", "choice_combined"):
        vals = []
        for r in rows:
            choice = r[policy_key]
            vals.append(float(r[f"cer_{choice}"]))
        policies[policy_key] = vals

    oracle_mean = _mean(oracle)
    result: dict[str, Any] = {
        "n": len(rows),
        "mean_cer": {
            "oracle": oracle_mean,
            "fixed_mixed": _mean(cer_mixed),
            "fixed_sep": _mean(cer_sep),
        },
        "regret_vs_oracle": {
            "fixed_mixed": round(_mean(cer_mixed) - oracle_mean, 6),
            "fixed_sep": round(_mean(cer_sep) - oracle_mean, 6),
        },
    }

    for policy_key, vals in policies.items():
        m = _mean(vals)
        result["mean_cer"][policy_key] = m
        result["regret_vs_oracle"][policy_key] = round(m - oracle_mean, 6)

    # Agreement signal analysis (RQ1)
    agr_mixed = [float(r["agr_mixed"]) for r in rows]
    agr_sep = [float(r["agr_sep"]) for r in rows]

    # Use the chosen arm's agreement as a quality predictor
    from .reference_free_qe import pearson as _pearson, spearman_corr as _spearman

    # For each row, use the agreement of the BETTER arm (oracle) as the score
    oracle_agr = []
    oracle_cer_list = []
    for r in rows:
        m_cer, s_cer = float(r["cer_mixed"]), float(r["cer_sep"])
        if m_cer < s_cer:
            oracle_agr.append(float(r["agr_mixed"]))
        else:
            oracle_agr.append(float(r["agr_sep"]))
        oracle_cer_list.append(min(m_cer, s_cer))

    spearman_agr_cer = _spearman(oracle_agr, oracle_cer_list)
    # AUC: does high agreement predict CER < threshold?
    agr_auc_05 = rank_auc(
        oracle_agr, [1 if c > 0.5 else 0 for c in oracle_cer_list]
    )
    agr_auc_10 = rank_auc(
        oracle_agr, [1 if c > 1.0 else 0 for c in oracle_cer_list]
    )

    result["agreement_signal"] = {
        "spearman_agreement_vs_cer": spearman_agr_cer,
        "auc_agreement_cer>0.5": round(agr_auc_05, 4),
        "auc_agreement_cer>1.0": round(agr_auc_10, 4),
    }

    # Compute cost overhead (RQ4)
    total_runtime_mixed = sum(float(r["runtime_mixed_total"]) for r in rows)
    total_runtime_sep = sum(float(r["runtime_sep_total"]) for r in rows)
    n_models = len(rows[0].get("text_mixed_small", "")) and 3  # tiny+base+small
    result["compute"] = {
        "total_runtime_mixed_sec": round(total_runtime_mixed, 1),
        "total_runtime_sep_sec": round(total_runtime_sep, 1),
        "n_models": 3,
        "cost_multiplier_vs_single": "3x (3 models vs 1)",
    }

    ranked = sorted(result["regret_vs_oracle"].items(), key=lambda kv: kv[1])
    result["best_policy"] = ranked[0][0]
    result["best_reference_free"] = next(
        (k for k, _ in ranked if k not in ("oracle",)), ranked[0][0]
    )

    # Write outputs
    (out_dir / "ensemble_summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_policy_csv(result, out_dir / "ensemble_policy_comparison.csv")

    try:
        render_figure(rows, result, out_dir)
    except Exception as exc:
        print(f"[ensemble] figure skipped: {exc}", flush=True)

    return result


def _write_policy_csv(result: dict[str, Any], path: Path) -> None:
    mean_cer = result.get("mean_cer", {})
    regret = result.get("regret_vs_oracle", {})
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(["policy", "mean_cer", "regret_vs_oracle", "reference_free"])
        for policy in sorted(mean_cer.keys()):
            ref_free = "yes" if policy != "oracle" else "no(oracle)"
            writer.writerow([policy, mean_cer[policy], regret.get(policy, ""), ref_free])


def render_figure(
    rows: list[dict[str, Any]], summary: dict[str, Any], out_dir: Path
) -> Path | None:
    """Plot: agreement vs CER scatter + routing regret comparison."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Left: agreement vs CER scatter
    for r in rows:
        for arm, color in [("mixed", "#4c78a8"), ("sep", "#e45756")]:
            agr = float(r[f"agr_{arm}"])
            cer = float(r[f"cer_{arm}"])
            ax1.scatter(agr, cer, c=color, alpha=0.4, s=20)

    ax1.set_xlabel("Ensemble Agreement Score (higher = more agreement)")
    ax1.set_ylabel("CER vs Reference")
    ax1.set_title("Agreement vs Quality")
    ax1.legend(
        handles=[
            plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="#4c78a8", label="mixed"),
            plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="#e45756", label="sep"),
        ]
    )
    ax1.grid(alpha=0.3)

    # Right: regret bar chart
    regret = summary.get("regret_vs_oracle", {})
    policies = [k for k in sorted(regret.keys())]
    regrets = [regret[p] for p in policies]
    colors = ["#e45756" if r > 0.1 else "#f58518" if r > 0.05 else "#54a24b" for r in regrets]
    ax2.barh(policies, regrets, color=colors)
    ax2.axvline(0, color="black", lw=0.8)
    ax2.set_xlabel("Routing Regret (mean CER − oracle CER)")
    ax2.set_title("Policy Comparison")
    ax2.grid(alpha=0.3, axis="x")

    fig.suptitle("Multi-Model Ensemble Voting Analysis (Whisper tiny+base+small)", fontsize=12)
    fig.tight_layout()
    fig_path = out_dir / "ensemble_analysis.png"
    fig.savefig(fig_path, dpi=160)
    plt.close(fig)
    print(f"[ensemble] wrote {fig_path.relative_to(PROJECT_ROOT)}", flush=True)
    return fig_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Multi-Model Ensemble Voter for overlap-aware ASR (frontier)."
    )
    parser.add_argument("--pairs", type=int, default=5, help="Number of speaker pairs.")
    parser.add_argument("--quick", action="store_true", help="Use coarse 5-point ratio grid.")
    parser.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(Path(args.out_dir), num_pairs=args.pairs, quick=args.quick)


if __name__ == "__main__":
    main()
