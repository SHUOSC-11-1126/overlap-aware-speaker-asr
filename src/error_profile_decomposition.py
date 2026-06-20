"""Error Profile Decomposition by Model -- experimental/frontier (Issue #865).

Research question (pre-registered):
  The Model Scale Analysis (#859) showed base has flat CER=0.200 across all
  overlaps while tiny has CER=0.467.  But CER hides error structure.  This
  module decomposes errors by type (substitution/deletion/insertion) per model
  per overlap ratio to understand what KINDS of errors each model makes.

  RQ1 (error types): Does base have fewer insertion/repetition errors
     (hallucination-driven) than tiny?
  RQ2 (error shift): Do base's errors shift toward substitution (genuine
     acoustic ambiguity) rather than insertion (hallucination)?
  RQ3 (overlap dependence): Does the error profile change with overlap ratio
     even when total CER doesn't (for base)?

  Hypotheses:
    H1: Base has fewer insertion errors than tiny (less hallucination).
    H2: Base's errors are substitution-dominated; tiny's are insertion-dominated.
    H3: Error profile changes with overlap for tiny but not for base.

  Labels: experimental/frontier. References are synthetic/silver. Models: tiny
  + base. Stable tables untouched; outputs go to
  results/frontier/error_profile_decomposition/.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from .config import PROJECT_ROOT
from .evaluate_cer import compute_cer
from .evaluate_error_types import levenshtein_alignment_counts
from .generate_synthetic_overlap import build_mixture, read_mono_audio
from .separation_tax_phase import (
    load_snippet_reference,
    select_pairs,
    trim_silence,
    transcribe_with_signals,
)

OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "error_profile_decomposition"


# ---- Pure error decomposition (unit-testable) ------------------------------------

def decompose_errors(ref: str, hyp: str) -> dict[str, Any]:
    """Decompose errors into substitution/deletion/insertion counts + rates."""
    subs, dels, ins, dist = levenshtein_alignment_counts(ref, hyp)
    ref_len = max(len(ref), 1)
    total = subs + dels + ins
    return {
        "ref_length": len(ref),
        "hyp_length": len(hyp),
        "edit_distance": dist,
        "cer": round(dist / ref_len, 6),
        "n_substitutions": subs,
        "n_deletions": dels,
        "n_insertions": ins,
        "n_total_errors": total,
        "substitution_frac": round(subs / max(total, 1), 4),
        "deletion_frac": round(dels / max(total, 1), 4),
        "insertion_frac": round(ins / max(total, 1), 4),
        "is_hallucination_dominated": ins > subs + dels,
    }


def compare_error_profiles(
    profile_a: dict[str, Any], profile_b: dict[str, Any],
) -> dict[str, Any]:
    """Compare two error profiles (e.g., base vs tiny)."""
    return {
        "cer_delta": round(profile_b["cer"] - profile_a["cer"], 6),
        "substitution_frac_delta": round(
            profile_b["substitution_frac"] - profile_a["substitution_frac"], 4
        ),
        "insertion_frac_delta": round(
            profile_b["insertion_frac"] - profile_a["insertion_frac"], 4
        ),
        "deletion_frac_delta": round(
            profile_b["deletion_frac"] - profile_a["deletion_frac"], 4
        ),
        "a_more_hallucination_dominated": profile_a["is_hallucination_dominated"],
        "b_more_hallucination_dominated": profile_b["is_hallucination_dominated"],
    }


# ---- Driver (runs ASR + decomposition) -------------------------------------------

def run(
    out_dir: Path,
    num_pairs: int = 5,
    model_names: list[str] | None = None,
    quick: bool = False,
) -> dict[str, Any]:
    """Run the error profile decomposition experiment."""
    import whisper

    if model_names is None:
        model_names = ["tiny", "base"]

    out_dir.mkdir(parents=True, exist_ok=True)
    models = {}
    for name in model_names:
        print(f"[profile] loading Whisper-{name}...", flush=True)
        models[name] = whisper.load_model(name)

    ratios = [0.0, 0.15, 0.35, 0.60, 0.90] if quick else [
        0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45,
        0.50, 0.60, 0.70, 0.80, 0.90,
    ]
    plans = select_pairs(num_pairs)
    active = sorted(models.keys())
    print(f"[profile] models={active} pairs={len(plans)} ratios={len(ratios)}", flush=True)

    # Build fieldnames
    fieldnames = ["pair_id", "con", "pro", "overlap_ratio"]
    for m in active:
        fieldnames += [
            f"cer_{m}", f"sub_{m}", f"del_{m}", f"ins_{m}",
            f"sub_frac_{m}", f"del_frac_{m}", f"ins_frac_{m}",
            f"halluc_dominated_{m}",
        ]

    rows: list[dict[str, Any]] = []
    curve_path = out_dir / "profile_curve.csv"

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

                row: dict[str, Any] = {
                    "pair_id": pi, "con": plan.con_path.name,
                    "pro": plan.pro_path.name, "overlap_ratio": ratio,
                }

                for mname, model in models.items():
                    s1r = transcribe_with_signals(model, t1_trim, "greedy")
                    s2r = transcribe_with_signals(model, t2_trim, "greedy")
                    hyp = s1r["text"] + s2r["text"]

                    decomp = decompose_errors(ref, hyp)
                    row[f"cer_{mname}"] = decomp["cer"]
                    row[f"sub_{mname}"] = decomp["n_substitutions"]
                    row[f"del_{mname}"] = decomp["n_deletions"]
                    row[f"ins_{mname}"] = decomp["n_insertions"]
                    row[f"sub_frac_{mname}"] = decomp["substitution_frac"]
                    row[f"del_frac_{mname}"] = decomp["deletion_frac"]
                    row[f"ins_frac_{mname}"] = decomp["insertion_frac"]
                    row[f"halluc_dominated_{mname}"] = decomp["is_hallucination_dominated"]

                writer.writerow(row)
                rows.append(row)

            fh.flush()
            print(f"[profile] pair {pi + 1}/{len(plans)} done", flush=True)

    summary = analyze(rows, active, out_dir)
    print(f"[profile] n={len(rows)} wrote {OUT_DIR.relative_to(PROJECT_ROOT)}", flush=True)
    return summary


def analyze(
    rows: list[dict[str, Any]], models: list[str], out_dir: Path,
) -> dict[str, Any]:
    """Analyze error profile decomposition results."""

    def _mean(xs: list[float]) -> float:
        vals = [x for x in xs if x == x]
        return round(sum(vals) / len(vals), 6) if vals else 0.0

    summary: dict[str, Any] = {"n": len(rows), "models": models, "per_model": {}}

    for m in models:
        cer = [float(r[f"cer_{m}"]) for r in rows]
        sub_frac = [float(r[f"sub_frac_{m}"]) for r in rows]
        del_frac = [float(r[f"del_frac_{m}"]) for r in rows]
        ins_frac = [float(r[f"ins_frac_{m}"]) for r in rows]
        halluc = [1 if r[f"halluc_dominated_{m}"] else 0 for r in rows]

        # Per-overlap analysis
        ratios = sorted({float(r["overlap_ratio"]) for r in rows})
        per_ratio = []
        for ratio in ratios:
            at = [r for r in rows if float(r["overlap_ratio"]) == ratio]
            per_ratio.append({
                "overlap_ratio": ratio,
                "mean_cer": _mean([float(r[f"cer_{m}"]) for r in at]),
                "mean_sub_frac": _mean([float(r[f"sub_frac_{m}"]) for r in at]),
                "mean_del_frac": _mean([float(r[f"del_frac_{m}"]) for r in at]),
                "mean_ins_frac": _mean([float(r[f"ins_frac_{m}"]) for r in at]),
                "halluc_dominated_frac": _mean([1 if r[f"halluc_dominated_{m}"] else 0 for r in at]),
            })

        summary["per_model"][m] = {
            "mean_cer": _mean(cer),
            "mean_substitution_frac": _mean(sub_frac),
            "mean_deletion_frac": _mean(del_frac),
            "mean_insertion_frac": _mean(ins_frac),
            "halluc_dominated_frac": _mean([float(h) for h in halluc]),
            "per_ratio": per_ratio,
        }

    # Cross-model comparison
    if len(models) >= 2:
        m1, m2 = models[0], models[1]
        p1 = summary["per_model"][m1]
        p2 = summary["per_model"][m2]
        summary["cross_model"] = {
            "comparison": f"{m1} vs {m2}",
            "cer_delta": round(p2["mean_cer"] - p1["mean_cer"], 6),
            "insertion_frac_delta": round(p2["mean_insertion_frac"] - p1["mean_insertion_frac"], 4),
            "substitution_frac_delta": round(p2["mean_substitution_frac"] - p1["mean_substitution_frac"], 4),
        }

    # Hypotheses
    if "tiny" in models and "base" in models:
        pt = summary["per_model"]["tiny"]
        pb = summary["per_model"]["base"]
        summary["hypotheses"] = {
            "h1_base_fewer_insertions": pb["mean_insertion_frac"] < pt["mean_insertion_frac"],
            "h2_base_substitution_dominated": pb["mean_substitution_frac"] > pb["mean_insertion_frac"],
            "h2_tiny_insertion_dominated": pt["mean_insertion_frac"] > pt["mean_substitution_frac"],
            "h3_base_profile_stable": _profile_stable(pb["per_ratio"]),
            "h3_tiny_profile_variable": not _profile_stable(pt["per_ratio"]),
        }

    # Write outputs
    (out_dir / "profile_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    try:
        render_figure(summary, out_dir)
    except Exception as exc:
        print(f"[profile] figure skipped: {exc}", flush=True)

    return summary


def _profile_stable(per_ratio: list[dict[str, Any]], threshold: float = 0.15) -> bool:
    """Check if substitution_frac is stable across overlap ratios (std < threshold)."""
    fracs = [r["mean_sub_frac"] for r in per_ratio if r["mean_sub_frac"] == r["mean_sub_frac"]]
    if len(fracs) < 2:
        return True
    return float(np.std(fracs)) < threshold


def render_figure(summary: dict[str, Any], out_dir: Path) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    models = summary["models"]
    fig, axes = plt.subplots(1, len(models), figsize=(7 * len(models), 5), squeeze=False)
    axes = axes[0]

    for idx, m in enumerate(models):
        ax = axes[idx]
        pr = summary["per_model"][m]["per_ratio"]
        ratios = [r["overlap_ratio"] for r in pr]
        sub = [r["mean_sub_frac"] for r in pr]
        dels = [r["mean_del_frac"] for r in pr]
        ins = [r["mean_ins_frac"] for r in pr]

        ax.stackplot(ratios, sub, dels, ins,
                     labels=["Substitution", "Deletion", "Insertion"],
                     colors=["#4c78a8", "#f58518", "#e45756"], alpha=0.8)
        ax.set_xlabel("overlap ratio")
        ax.set_ylabel("Error type fraction")
        ax.set_title(f"Whisper-{m} error profile")
        ax.legend(loc="upper right", fontsize=8)
        ax.set_ylim(0, 1)
        ax.grid(alpha=0.3)

    fig.suptitle("Error Profile Decomposition: substitution vs deletion vs insertion", fontsize=11)
    fig.tight_layout()
    fig_path = out_dir / "error_profile_by_model.png"
    fig.savefig(fig_path, dpi=160)
    plt.close(fig)
    return fig_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Error Profile Decomposition (frontier).")
    parser.add_argument("--pairs", type=int, default=5)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(Path(args.out_dir), num_pairs=args.pairs, quick=args.quick)


if __name__ == "__main__":
    main()
