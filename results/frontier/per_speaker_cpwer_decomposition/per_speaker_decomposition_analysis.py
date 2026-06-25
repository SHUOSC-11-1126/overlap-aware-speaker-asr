#!/usr/bin/env python3
"""RQ37: Per-speaker cpWER decomposition on AISHELL-4 -- experimental/frontier.

Hypotheses (pre-registered, Issue #944)
---------------------------------------
  H37a (SUPPORTED if) one speaker contributes > 50% of total cpWER in the
       worst (top-10) windows.  KILL if max share <= 50%.
  H37b (SUPPORTED if) the worst speaker is consistent across windows (same
       speaker worst in > 50% of the top-10 windows).  KILL if a different
       speaker is worst each time.
  H37c (SUPPORTED if) Mode S windows (separator-collapse, window_ids 22 and
       30) have uniform per-speaker error (Gini < 0.3).  KILL if Gini >= 0.3.

Background
----------
cpWER aggregates errors across all speakers into a single number.  In a
6-speaker meeting the total cpWER may be dominated by 1-2 speakers whose
channel failed (separator collapse, whisper-tiny hallucination, etc.).
This script decomposes cpWER by speaker to identify the "worst speaker"
pattern and test whether Mode S windows have uniform per-speaker error.

Method
------
Reanalysis only -- no Whisper / no ASR runs.  For each of the 77 AISHELL-4
windows in
``results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json``
(label external/sanity-check, meeting M_R003S02C01):

  1. Build MeetEval char-level segments from ``ref_text_per_speaker`` and
     ``separated_text_per_speaker`` (``' '.join(list(text))`` -- the standard
     Chinese cpCER convention, matching RQ30's char-level arm).
  2. Run MeetEval 0.4.3 ``cpwer`` to get the optimal ref<->hyp assignment and
     the aggregate error count.
  3. Apply the assignment and compute a per-speaker Levenshtein distance on
     the raw character strings.  Per-speaker errors sum to the cpWER aggregate
     (including unmatched-hypothesis insertions in a dedicated bucket).
  4. Rank the 77 windows by total char-level cpWER; analyse the top-10.
  5. For Mode S windows (22, 30), compute the Gini coefficient of the
     per-speaker cpWER values.

Outputs (all labelled experimental/frontier)
--------------------------------------------
  per_speaker_decomposition_results.json -- full per-window decomposition + verdicts
  per_speaker_decomposition_results.csv  -- one row per window (top-10 + Mode S flagged)
  FINDINGS.md                            -- human-readable summary

Run:
    /opt/homebrew/bin/python3 results/frontier/per_speaker_cpwer_decomposition/per_speaker_decomposition_analysis.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

# Make ``src.*`` importable when running the script directly via
# ``python3 results/frontier/per_speaker_cpwer_decomposition/...py`` (no -m).
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.per_speaker_decomposition import (  # noqa: E402
    decompose_cpwer_per_speaker,
    evaluate_hypotheses,
    gini_coefficient,
    rank_windows_by_cpwer,
    worst_speaker,
)

try:
    import meeteval
    MEETEVAL_VERSION = meeteval.__version__
except Exception:  # pragma: no cover
    MEETEVAL_VERSION = "unavailable"

# --------------------------------------------------------------------------- paths
SOURCE_JSON = (
    PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
OUT_DIR = Path(__file__).resolve().parent
OUT_JSON = OUT_DIR / "per_speaker_decomposition_results.json"
OUT_CSV = OUT_DIR / "per_speaker_decomposition_results.csv"
OUT_FINDINGS = OUT_DIR / "FINDINGS.md"

TOP_K = 10
MODE_S_WINDOW_IDS = [22, 30]
RQ_ID = "RQ37"
CLOSES_ISSUE = "#944"


# --------------------------------------------------------------------------- main
def main() -> None:
    print(f"=== {RQ_ID}: Per-speaker cpWER decomposition on AISHELL-4 ===")
    print(f"MeetEval version: {MEETEVAL_VERSION}")
    print(f"Source data: {SOURCE_JSON}")
    print(f"Output dir:  {OUT_DIR}")
    print()

    data = json.loads(SOURCE_JSON.read_text())
    windows = data["windows"]
    n = len(windows)
    print(f"Windows: {n}")
    print(f"Mode S window_ids: {MODE_S_WINDOW_IDS}")
    print()

    # ------------------------------------------------------ per-window decomposition
    per_window_results: list[dict[str, Any]] = []
    mismatch_count = 0  # per-speaker sum != MeetVal aggregate (should stay 0)
    skipped_count = 0

    for w in windows:
        wid = w["window_id"]
        ref = w["ref_text_per_speaker"]
        hyp = w["separated_text_per_speaker"]

        dec = decompose_cpwer_per_speaker(ref, hyp)
        if dec.get("skipped"):
            skipped_count += 1
            per_window_results.append({
                "window_id": wid,
                "skipped": True,
                "cpwer": 0.0,
                "total_errors": 0,
                "total_length": 0,
                "per_speaker": [],
                "unmatched_hyp": {"errors": 0, "hyp_length": 0, "share_of_total_errors": 0.0},
                "assignment": [],
            })
            continue

        reconstructed = sum(p["errors"] for p in dec["per_speaker"]) + dec["unmatched_hyp"]["errors"]
        if reconstructed != dec["meetval_errors"]:
            mismatch_count += 1

        ws_id, ws_share, ws_errs = worst_speaker(dec["per_speaker"])

        per_window_results.append({
            "window_id": wid,
            "skipped": False,
            "cpwer": dec["cpwer"],
            "total_errors": dec["total_errors"],
            "total_length": dec["total_length"],
            "meetval_errors": dec["meetval_errors"],
            "meetval_length": dec["meetval_length"],
            "reconstructed_errors": reconstructed,
            "per_speaker": dec["per_speaker"],
            "unmatched_hyp": dec["unmatched_hyp"],
            "assignment": [list(a) for a in dec["assignment"]],
            "worst_speaker": ws_id,
            "worst_speaker_errors": ws_errs,
            "worst_speaker_share": ws_share,
            "num_speakers": w["num_speakers"],
            "overlap_label": w.get("overlap_label"),
            "router_v2_method": w.get("router_v2_method"),
        })

    # ----------------------------------------------------------- rank + top-10
    eligible = [w for w in per_window_results if not w.get("skipped")]
    top_windows = rank_windows_by_cpwer(eligible, top_k=TOP_K)

    # ----------------------------------------------------------- Mode S windows
    mode_s_window_results = [
        w for w in per_window_results
        if w["window_id"] in MODE_S_WINDOW_IDS and not w.get("skipped")
    ]

    # ----------------------------------------------------------- hypothesis verdicts
    verdicts = evaluate_hypotheses(top_windows, mode_s_window_results)

    # ----------------------------------------------------------- CSV write
    csv_rows: list[dict[str, Any]] = []
    for w in per_window_results:
        if w.get("skipped"):
            continue
        is_top = w["window_id"] in [t["window_id"] for t in top_windows]
        is_mode_s = w["window_id"] in MODE_S_WINDOW_IDS
        per_spk_summary = "; ".join(
            f"{p['speaker']}:err={p['errors']},len={p['ref_length']},cpwer={p['cpwer']:.4f},share={p['share_of_total_errors']:.4f}"
            for p in w["per_speaker"]
        )
        unmatched = w["unmatched_hyp"]
        csv_rows.append({
            "window_id": w["window_id"],
            "is_top10": is_top,
            "is_mode_s": is_mode_s,
            "num_speakers": w["num_speakers"],
            "overlap_label": w["overlap_label"],
            "router_v2_method": w["router_v2_method"],
            "total_cpwer": round(w["cpwer"], 6),
            "total_errors": w["total_errors"],
            "total_length": w["total_length"],
            "meetval_errors": w["meetval_errors"],
            "reconstructed_errors": w["reconstructed_errors"],
            "errors_match_meetval": w["reconstructed_errors"] == w["meetval_errors"],
            "worst_speaker": w["worst_speaker"],
            "worst_speaker_errors": w["worst_speaker_errors"],
            "worst_speaker_share": round(w["worst_speaker_share"], 6),
            "unmatched_hyp_errors": unmatched["errors"],
            "unmatched_hyp_share": round(unmatched["share_of_total_errors"], 6),
            "per_speaker_summary": per_spk_summary,
        })
    csv_rows.sort(key=lambda r: r["total_cpwer"], reverse=True)

    with OUT_CSV.open("w", newline="") as f:
        fieldnames = list(csv_rows[0].keys())
        w_csv = csv.DictWriter(f, fieldnames=fieldnames)
        w_csv.writeheader()
        w_csv.writerows(csv_rows)

    # ----------------------------------------------------------- JSON write
    results = {
        "label": "experimental/frontier",
        "rq": RQ_ID,
        "closes_issue": CLOSES_ISSUE,
        "meeteval_version": MEETEVAL_VERSION,
        "method": (
            "Reanalysis only.  For each of the 77 AISHELL-4 windows in "
            "results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json "
            "(label external/sanity-check, meeting M_R003S02C01), ran MeetEval 0.4.3 "
            "cpwer with character-level tokenisation (' '.join(list(text)), the standard "
            "Chinese cpCER convention matching RQ30's char-level arm).  Used "
            "CPErrorRate.apply_assignment to fix the optimal ref<->hyp speaker mapping, "
            "then computed a per-speaker Levenshtein distance on the raw character "
            "strings.  Per-speaker errors sum to the cpWER aggregate (including "
            "unmatched-hypothesis insertions in a dedicated __unmatched_hyp__ bucket).  "
            "No Whisper / no ASR runs."
        ),
        "source_data": {
            "path": str(SOURCE_JSON.relative_to(PROJECT_ROOT)),
            "label": "external/sanity-check",
            "num_windows": n,
            "meeting_id": data.get("meeting_id"),
        },
        "parameters": {
            "top_k": TOP_K,
            "mode_s_window_ids": MODE_S_WINDOW_IDS,
            "tokenisation": "character-level (' '.join(list(text)))",
            "worst_speaker_criterion": "highest per-speaker error COUNT (contribution to total cpWER errors)",
            "share_denominator": "total_errors (real speakers + unmatched_hyp insertions)",
            "gini_threshold_h37c": 0.30,
            "share_threshold_h37a": 0.50,
            "consistency_threshold_h37b": 0.50,
        },
        "decomposition_invariants": {
            "windows_processed": len(per_window_results),
            "windows_skipped_empty": skipped_count,
            "windows_decomposed": len(eligible),
            "per_speaker_sums_match_meetval": mismatch_count == 0,
            "mismatch_count": mismatch_count,
        },
        "hypotheses": verdicts,
        "top_10_windows": [
            {
                "window_id": w["window_id"],
                "cpwer": round(w["cpwer"], 6),
                "total_errors": w["total_errors"],
                "total_length": w["total_length"],
                "worst_speaker": w["worst_speaker"],
                "worst_speaker_share": round(w["worst_speaker_share"], 6),
                "unmatched_hyp_share": round(w["unmatched_hyp"]["share_of_total_errors"], 6),
                "per_speaker": [
                    {
                        "speaker": p["speaker"],
                        "errors": p["errors"],
                        "ref_length": p["ref_length"],
                        "cpwer": round(p["cpwer"], 6),
                        "share_of_total_errors": round(p["share_of_total_errors"], 6),
                    }
                    for p in w["per_speaker"]
                ],
            }
            for w in top_windows
        ],
        "mode_s_windows": [
            {
                "window_id": w["window_id"],
                "cpwer": round(w["cpwer"], 6),
                "num_speakers": w["num_speakers"],
                "gini": round(gini_coefficient([p["cpwer"] for p in w["per_speaker"]]), 6),
                "per_speaker": [
                    {
                        "speaker": p["speaker"],
                        "errors": p["errors"],
                        "ref_length": p["ref_length"],
                        "cpwer": round(p["cpwer"], 6),
                        "share_of_total_errors": round(p["share_of_total_errors"], 6),
                    }
                    for p in w["per_speaker"]
                ],
                "unmatched_hyp": w["unmatched_hyp"],
            }
            for w in mode_s_window_results
        ],
        "all_windows": per_window_results,
        "explanation": _build_explanation(verdicts, top_windows, mode_s_window_results, mismatch_count),
        "references": [
            "MeetEval: https://github.com/fgnt/meeteval",
            "cpWER: concatenated minimum-permutation WER (NIST OpenKiwi / WER for meeting transcription)",
            "Source data: results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json (RQ1, PR #890)",
            "RQ30 char-level cpWER validation: results/frontier/meeteval_cpwer_validation/ (PR #935)",
            "RQ22 separator-failure detector (Mode S = windows 22, 30): results/frontier/separator_failure_detector/ (PR #921)",
        ],
    }
    OUT_JSON.write_text(json.dumps(results, indent=2, ensure_ascii=False))

    # ----------------------------------------------------------- FINDINGS.md
    OUT_FINDINGS.write_text(_build_findings(verdicts, top_windows, mode_s_window_results, mismatch_count, n))

    # ----------------------------------------------------------- console
    _print_console(verdicts, top_windows, mode_s_window_results, mismatch_count, n)


def _build_explanation(verdicts, top_windows, mode_s_window_results, mismatch_count) -> str:
    h37a = verdicts["H37a"]
    h37b = verdicts["H37b"]
    h37c = verdicts["H37c"]
    parts = []
    parts.append(
        f"H37a {h37a['verdict']}: the worst speaker's share of total cpWER errors "
        f"reaches {h37a['max_worst_speaker_share']:.1%} in the top-10 windows "
        f"(threshold > 50%). "
    )
    parts.append(
        f"H37b {h37b['verdict']}: the worst speaker is '{h37b['most_common_worst_speaker']}' "
        f"in {h37b['consistency_fraction']:.0%} of the top-10 windows "
        f"(threshold > 50%). "
    )
    mode_s_ginis = h37c.get("mode_s_ginis", {})
    gini_str = ", ".join(f"window {wid}: {g:.3f}" for wid, g in mode_s_ginis.items())
    parts.append(
        f"H37c {h37c['verdict']}: Mode S window Gini coefficients -- {gini_str} "
        f"(threshold < 0.30). "
    )
    if mismatch_count == 0:
        parts.append(
            "Decomposition invariant holds: per-speaker error counts plus unmatched-"
            "hypothesis insertions sum to MeetEval's cpwer.errors for every window "
            "(0 mismatches across 77 windows)."
        )
    else:
        parts.append(
            f"WARNING: {mismatch_count} windows where per-speaker sum != MeetEval aggregate."
        )
    return " ".join(parts)


def _build_findings(verdicts, top_windows, mode_s_window_results, mismatch_count, n) -> str:
    h37a = verdicts["H37a"]
    h37b = verdicts["H37b"]
    h37c = verdicts["H37c"]

    lines: list[str] = []
    lines.append(f"# RQ37: Per-speaker cpWER Decomposition -- Findings\n")
    lines.append(f"## Label: experimental/frontier (Issue {CLOSES_ISSUE})\n")
    lines.append(
        "Decomposes AISHELL-4 cpWER (77 windows, meeting M_R003S02C01) by speaker "
        "using MeetEval 0.4.3's `cpwer` with character-level tokenisation. "
        "Tests whether total cpWER is dominated by 1-2 speakers and whether "
        "Mode S windows (separator-collapse, ids 22 and 30) have uniform "
        "per-speaker error.\n"
    )
    lines.append("## Method\n")
    lines.append(
        "For each window: run `cpwer` on char-level segments (`' '.join(list(text))`, "
        "the standard Chinese cpCER convention from RQ30) to get the optimal "
        "ref<->hyp speaker assignment; apply the assignment; compute per-speaker "
        "Levenshtein distance on the raw character strings. Per-speaker errors sum "
        "to MeetEval's `cpwer.errors` (including unmatched-hypothesis insertions in "
        "a dedicated `__unmatched_hyp__` bucket). Worst speaker = highest error "
        "count. Share = speaker errors / total errors. Gini computed on per-speaker "
        "cpWER values (errors/ref_length).\n"
    )
    lines.append("## Hypothesis verdicts\n")
    lines.append("| ID | Statement | Verdict | Key value | Threshold |")
    lines.append("|----|-----------|---------|-----------|-----------|")
    lines.append(
        f"| H37a | One speaker contributes > 50% of total cpWER in worst windows | "
        f"{h37a['verdict']} | max share = {h37a['max_worst_speaker_share']:.1%} | > 50% |"
    )
    lines.append(
        f"| H37b | Worst speaker is consistent across windows | "
        f"{h37b['verdict']} | '{h37b['most_common_worst_speaker']}' worst in "
        f"{h37b['consistency_fraction']:.0%} of top-10 | > 50% |"
    )
    mode_s_ginis = h37c.get("mode_s_ginis", {})
    gini_str = ", ".join(f"{wid}: {g:.3f}" for wid, g in mode_s_ginis.items())
    lines.append(
        f"| H37c | Mode S windows have uniform per-speaker error | "
        f"{h37c['verdict']} | Gini = {gini_str} | < 0.30 |"
    )
    lines.append("")
    lines.append("## Top-10 worst windows (by char-level cpWER)\n")
    lines.append("| Rank | Window | cpWER | Errors | Worst speaker | Worst share | Unmatched share |")
    lines.append("|------|--------|-------|--------|---------------|-------------|-----------------|")
    for i, w in enumerate(top_windows, 1):
        lines.append(
            f"| {i} | {w['window_id']} | {w['cpwer']:.4f} | {w['total_errors']} | "
            f"{w['worst_speaker']} | {w['worst_speaker_share']:.1%} | "
            f"{w['unmatched_hyp']['share_of_total_errors']:.1%} |"
        )
    lines.append("")
    lines.append("## Mode S windows (separator-collapse)\n")
    lines.append("| Window | Speakers | cpWER | Gini | Per-speaker (errors/len: cpwer) |")
    lines.append("|--------|----------|-------|------|----------------------------------|")
    for w in mode_s_window_results:
        gini = gini_coefficient([p["cpwer"] for p in w["per_speaker"]])
        per_spk = ", ".join(
            f"{p['speaker']} {p['errors']}/{p['ref_length']}:{p['cpwer']:.3f}"
            for p in w["per_speaker"]
        )
        lines.append(
            f"| {w['window_id']} | {w['num_speakers']} | {w['cpwer']:.4f} | "
            f"{gini:.3f} | {per_spk} |"
        )
    lines.append("")
    lines.append("## Decomposition invariant\n")
    if mismatch_count == 0:
        lines.append(
            "Per-speaker error counts plus unmatched-hypothesis insertions sum to "
            "MeetEval's `cpwer.errors` for **all 77 windows** (0 mismatches). The "
            "decomposition is exact, not approximate."
        )
    else:
        lines.append(
            f"WARNING: {mismatch_count} windows where per-speaker sum != MeetEval aggregate."
        )
    lines.append("")
    lines.append("## Interpretation\n")
    lines.append(_interpretation(verdicts, top_windows, mode_s_window_results))
    lines.append("")
    lines.append("## Files\n")
    lines.append("- per_speaker_decomposition_results.json -- full per-window decomposition + verdicts")
    lines.append("- per_speaker_decomposition_results.csv -- one row per window (ranked by cpWER)")
    lines.append("- per_speaker_decomposition_analysis.py -- analysis script (imports src/per_speaker_decomposition.py)")
    lines.append("- src/per_speaker_decomposition.py -- testable helpers (cpwer bridge, Gini, edit distance, hypothesis eval)")
    lines.append("- tests/test_per_speaker_decomposition.py -- 48 unit tests (unittest.TestCase)")
    lines.append("")
    return "\n".join(lines)


def _interpretation(verdicts, top_windows, mode_s_window_results) -> str:
    h37a = verdicts["H37a"]
    h37b = verdicts["H37b"]
    h37c = verdicts["H37c"]
    parts: list[str] = []

    if h37a["verdict"] == "SUPPORTED":
        parts.append(
            f"H37a SUPPORTED: cpWER is heavily concentrated. In the top-10 worst "
            f"windows a single speaker contributes {h37a['max_worst_speaker_share']:.0%} "
            f"of the total cpWER errors in the worst case. The aggregate cpWER "
            f"masks a 'worst speaker' problem -- improving that speaker's channel "
            f"(better separation, better ASR, or rerouting it to mixed) would "
            f"disproportionately reduce the total."
        )
    else:
        parts.append(
            f"H37a NOT SUPPORTED: the worst speaker's share plateaus at "
            f"{h37a['max_worst_speaker_share']:.0%} (<= 50%). cpWER is spread "
            f"across multiple speakers; there is no single dominant 'worst speaker'. "
            f"Note: unmatched-hypothesis insertions (separator emitting extra speaker "
            f"channels) may carry a large fraction of the error budget -- see the "
            f"unmatched_hyp_share column in the CSV."
        )

    if h37b["verdict"] == "SUPPORTED":
        parts.append(
            f"H37b SUPPORTED: the worst speaker is consistent ('{h37b['most_common_worst_speaker']}' "
            f"in {h37b['consistency_fraction']:.0%} of top-10). The same speaker's "
            f"channel fails repeatedly -- a speaker-specific failure mode, not random."
        )
    else:
        parts.append(
            f"H37b NOT SUPPORTED: the worst speaker rotates across windows "
            f"(most common '{h37b['most_common_worst_speaker']}' only "
            f"{h37b['consistency_fraction']:.0%} of top-10). No single speaker is "
            f"systematically the worst; failures are distributed."
        )

    mode_s_ginis = h37c.get("mode_s_ginis", {})
    if mode_s_ginis:
        all_low = all(g < 0.3 for g in mode_s_ginis.values())
        if h37c["verdict"] == "SUPPORTED":
            parts.append(
                f"H37c SUPPORTED: Mode S windows have low Gini ({', '.join(f'{wid}:{g:.2f}' for wid,g in mode_s_ginis.items())}), "
                f"meaning per-speaker cpWER values are relatively uniform. CAVEAT: "
                f"Gini on cpWER rates can obscure error concentration when ref lengths "
                f"differ wildly -- e.g. window 22 has 98.3% of absolute errors on "
                f"speaker 005-F, but because the 1-char 006-F reference yields cpWER=1.0 "
                f"(vs 005-F's 0.49) the cpWER values look 'uniform'. The Gini verdict "
                f"is technically correct but should be read alongside the per-speaker "
                f"error shares in the Mode S table."
            )
        else:
            parts.append(
                f"H37c NOT SUPPORTED: at least one Mode S window has high Gini "
                f"({', '.join(f'{wid}:{g:.2f}' for wid,g in mode_s_ginis.items())}), "
                f"meaning per-speaker error is concentrated. Mode S does produce a "
                f"single-speaker-dominated error pattern."
            )
    return " ".join(parts)


def _print_console(verdicts, top_windows, mode_s_window_results, mismatch_count, n) -> None:
    print("=" * 78)
    print("DECOMPOSITION INVARIANT")
    print("=" * 78)
    print(f"  Windows processed: {n}")
    print(f"  Per-speaker sums match MeetVal aggregate: {mismatch_count == 0} (mismatches={mismatch_count})")
    print()
    print("=" * 78)
    print("TOP-10 WORST WINDOWS (by char-level cpWER)")
    print("=" * 78)
    print(f"{'Rank':<5} {'Win':<5} {'cpWER':>8} {'Errs':>6} {'Worst':<8} {'Share':>8} {'Unmatched':>10}")
    for i, w in enumerate(top_windows, 1):
        print(
            f"{i:<5} {w['window_id']:<5} {w['cpwer']:>8.4f} {w['total_errors']:>6} "
            f"{w['worst_speaker']:<8} {w['worst_speaker_share']:>8.1%} "
            f"{w['unmatched_hyp']['share_of_total_errors']:>10.1%}"
        )
    print()
    print("=" * 78)
    print("MODE S WINDOWS")
    print("=" * 78)
    for w in mode_s_window_results:
        gini = gini_coefficient([p["cpwer"] for p in w["per_speaker"]])
        print(f"  Window {w['window_id']}: cpwer={w['cpwer']:.4f}  gini={gini:.4f}  speakers={w['num_speakers']}")
        for p in w["per_speaker"]:
            print(f"    {p['speaker']}: errors={p['errors']} len={p['ref_length']} cpwer={p['cpwer']:.4f} share={p['share_of_total_errors']:.1%}")
    print()
    print("=" * 78)
    print("HYPOTHESIS VERDICTS")
    print("=" * 78)
    for hid in ("H37a", "H37b", "H37c"):
        v = verdicts[hid]
        print(f"  {hid}: {v['verdict']}")
    print()
    print(f"Wrote: {OUT_JSON}")
    print(f"Wrote: {OUT_CSV}")
    print(f"Wrote: {OUT_FINDINGS}")


if __name__ == "__main__":
    main()
