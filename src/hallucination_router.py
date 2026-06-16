"""Route by hallucination, not overlap (experimental/frontier).

Research question (pre-registered):
  The Separation Tax study (src/separation_tax_phase.py) showed that the "when to
  separate" decision is dominated by *which input made Whisper hallucinate*: separated
  tracks blow up at low overlap (injected silence), mixed audio blows up at high overlap.
  Whisper's own compression ratio flags those catastrophes reference-free (AUC 1.0).

  That motivates a bolder routing thesis: **route by hallucination, not by overlap.**
  For each utterance, transcribe both candidates (mixed and silence-trimmed separated),
  score each by a reference-free degeneracy signal (max segment compression ratio), and
  pick the *less hallucinated* one -- WITHOUT estimating the overlap ratio at all.

  RQ1 (generalization): On a held-out split (50 dev / 50 test) reconstructed from the
     synthetic_split manifest, does the reference-free hallucination router beat the fixed
     baselines and approach the oracle (min-CER) selector?
  RQ2 (the bold claim): Does hallucination routing -- which needs NO overlap knowledge --
     match or beat an overlap-threshold router that is *given the TRUE overlap ratio* and
     the crossover r*≈0.17 learned by the phase study?

Hypotheses:
  H1: regret(hallucination_router) << regret(fixed_mixed) and << regret(fixed_sep) on test.
  H2: regret(hallucination_router) <= regret(overlap_router_with_true_overlap) on test.

What is useful even if H2 fails: if the true-overlap router wins, it quantifies how much
information overlap carries beyond what reference-free degeneracy captures -- still a
falsifiable, computed result.

Labels: experimental/frontier; references are synthetic/silver (Whisper-small on clean
snippets); ASR = Whisper-tiny (offline). CER is post-hoc evaluation only and is never a
routing input (the router uses only the reference-free compression-ratio signal). The
overlap_router uses the manifest's overlap ratio, which is a *generation* parameter, not a
reference/label -- and it is included precisely as the baseline the thesis competes against.
Stable tables are untouched; outputs go to results/frontier/hallucination_router/.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT
from .evaluate_cer import compute_cer
from .generate_synthetic_overlap import build_mixture, read_mono_audio
from .separation_tax_phase import (
    GUARD_THRESHOLD,
    _rel,
    load_snippet_reference,
    transcribe_with_signals,
    trim_silence,
)

MANIFEST = PROJECT_ROOT / "results" / "tables" / "synthetic_split_manifest.csv"
SNIPPETS_DIR = PROJECT_ROOT / "resources" / "snippets"
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "hallucination_router"
CROSSOVER = 0.17  # mean-ΔCER crossover learned by the separation-tax phase study

# Routing policies evaluated. "halluc_2way"/"halluc_3way" are the reference-free thesis;
# "overlap_router" is the baseline that is GIVEN the true overlap ratio.
POLICIES = ["fixed_mixed", "fixed_sep", "fixed_sep_trim", "halluc_2way", "halluc_3way", "overlap_router"]


# --------------------------------------------------------------------------------------
# Pure routing logic (unit-tested; no Whisper / no audio)
# --------------------------------------------------------------------------------------
def route_min_degeneracy(degeneracy: dict[str, float], allowed: list[str]) -> str:
    """Pick the candidate in `allowed` with the lowest reference-free degeneracy score.
    Stable tie-break by the order of `allowed`."""
    best = None
    best_score = float("inf")
    for name in allowed:
        score = degeneracy.get(name, float("inf"))
        if score < best_score:
            best_score = score
            best = name
    return best if best is not None else allowed[0]


def route_by_overlap(overlap_ratio: float, threshold: float = CROSSOVER) -> str:
    """Baseline that is GIVEN the true overlap ratio: below the crossover separation hurts
    (use mixed), at/above it separation helps (use the trimmed separated route)."""
    return "fixed_mixed" if overlap_ratio < threshold else "fixed_sep_trim"


def _mean(xs: list[float]) -> float:
    return round(sum(xs) / len(xs), 6) if xs else 0.0


def summarize_routing(rows: list[dict[str, Any]], split: str | None = None) -> dict[str, Any]:
    """Per-policy mean CER + regret vs the oracle (min-CER selector), optionally for one split."""
    sub = [r for r in rows if split is None or r.get("split") == split]
    if not sub:
        return {"split": split or "all", "n": 0}
    oracle = [float(r["cer_oracle"]) for r in sub]
    out: dict[str, Any] = {"split": split or "all", "n": len(sub), "mean_cer": {}, "regret_vs_oracle": {}}
    mean_oracle = _mean(oracle)
    out["mean_cer"]["oracle"] = mean_oracle
    for policy in POLICIES:
        vals = [float(r[f"cer_{policy}"]) for r in sub]
        out["mean_cer"][policy] = _mean(vals)
        out["regret_vs_oracle"][policy] = round(_mean(vals) - mean_oracle, 6)
    ranked = sorted(out["regret_vs_oracle"].items(), key=lambda kv: kv[1])
    out["best_reference_free"] = next(
        (k for k, _ in ranked if k != "overlap_router"), ranked[0][0]
    )
    out["best_overall"] = ranked[0][0]
    return out


# --------------------------------------------------------------------------------------
# Whisper-dependent driver
# --------------------------------------------------------------------------------------
def _read_manifest() -> list[dict[str, Any]]:
    with MANIFEST.open("r", newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def run(out_dir: Path, limit: int | None = None) -> dict[str, Any]:
    import whisper

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = _read_manifest()
    if limit:
        manifest = manifest[:limit]
    model = whisper.load_model("tiny")
    print(f"[halluc-router] model=tiny cases={len(manifest)}", flush=True)

    fieldnames = [
        "sample_id", "split", "overlap_ratio",
        "cer_mixed", "cer_sep", "cer_sep_trim",
        "deg_mixed", "deg_sep", "deg_sep_trim",
        "cer_fixed_mixed", "cer_fixed_sep", "cer_fixed_sep_trim",
        "cer_halluc_2way", "cer_halluc_3way", "cer_overlap_router", "cer_oracle",
        "choice_halluc_2way", "choice_halluc_3way", "choice_overlap_router",
    ]
    rows: list[dict[str, Any]] = []
    curve_path = out_dir / "routing_curve.csv"
    with curve_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for i, m in enumerate(manifest):
            con = SNIPPETS_DIR / str(m["con_source"])
            pro = SNIPPETS_DIR / str(m["pro_source"])
            ref = load_snippet_reference(con) + load_snippet_reference(pro)
            ratio = float(m["overlap_ratio"])
            s1, s2 = read_mono_audio(con), read_mono_audio(pro)
            mixed, t1, t2, _ = build_mixture(s1, s2, ratio)

            mx = transcribe_with_signals(model, mixed, "greedy")
            o1 = transcribe_with_signals(model, t1, "greedy")
            o2 = transcribe_with_signals(model, t2, "greedy")
            tt1, tt2 = trim_silence(t1), trim_silence(t2)
            ot1 = transcribe_with_signals(model, tt1, "greedy")
            ot2 = transcribe_with_signals(model, tt2, "greedy")

            cer_mixed = compute_cer(ref, mx["text"])["cer"]
            cer_sep = compute_cer(ref, o1["text"] + o2["text"])["cer"]
            cer_sep_trim = compute_cer(ref, ot1["text"] + ot2["text"])["cer"]
            deg_mixed = mx["max_compression_ratio"]
            deg_sep = max(o1["max_compression_ratio"], o2["max_compression_ratio"])
            deg_sep_trim = max(ot1["max_compression_ratio"], ot2["max_compression_ratio"])

            cer_by = {"fixed_mixed": cer_mixed, "fixed_sep": cer_sep, "fixed_sep_trim": cer_sep_trim}
            deg_by = {"fixed_mixed": deg_mixed, "fixed_sep": deg_sep, "fixed_sep_trim": deg_sep_trim}

            choice2 = route_min_degeneracy(deg_by, ["fixed_mixed", "fixed_sep_trim"])
            choice3 = route_min_degeneracy(deg_by, ["fixed_mixed", "fixed_sep", "fixed_sep_trim"])
            choice_ov = route_by_overlap(ratio)

            row = {
                "sample_id": m["sample_id"], "split": m.get("split", ""), "overlap_ratio": ratio,
                "cer_mixed": round(cer_mixed, 6), "cer_sep": round(cer_sep, 6), "cer_sep_trim": round(cer_sep_trim, 6),
                "deg_mixed": round(deg_mixed, 4), "deg_sep": round(deg_sep, 4), "deg_sep_trim": round(deg_sep_trim, 4),
                "cer_fixed_mixed": round(cer_mixed, 6),
                "cer_fixed_sep": round(cer_sep, 6),
                "cer_fixed_sep_trim": round(cer_sep_trim, 6),
                "cer_halluc_2way": round(cer_by[choice2], 6),
                "cer_halluc_3way": round(cer_by[choice3], 6),
                "cer_overlap_router": round(cer_by[choice_ov], 6),
                "cer_oracle": round(min(cer_mixed, cer_sep, cer_sep_trim), 6),
                "choice_halluc_2way": choice2, "choice_halluc_3way": choice3, "choice_overlap_router": choice_ov,
            }
            writer.writerow(row)
            rows.append(row)
            if (i + 1) % 20 == 0:
                print(f"[halluc-router] {i + 1}/{len(manifest)} cases", flush=True)
        fh.flush()

    summary = {
        "n": len(rows),
        "crossover_threshold": CROSSOVER,
        "guard_threshold": GUARD_THRESHOLD,
        "by_split": {s: summarize_routing(rows, s) for s in ("dev", "test")},
        "all": summarize_routing(rows, None),
    }
    (out_dir / "routing_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[halluc-router] wrote {_rel(curve_path)} and routing_summary.json", flush=True)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Route by hallucination, not overlap (experimental/frontier).")
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N manifest rows (smoke).")
    parser.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(Path(args.out_dir), limit=args.limit)


if __name__ == "__main__":
    main()
