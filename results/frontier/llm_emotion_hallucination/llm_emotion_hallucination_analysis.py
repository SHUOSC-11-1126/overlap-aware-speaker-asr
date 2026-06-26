"""RQ36 driver: LLM emotion reading from hallucinated transcripts.

Orchestrates the analysis: loads AISHELL-4 + gold-benchmark tracks, calls
deepseek-r1:7b via ollama for each transcript (with a persistent cache so the run
resumes after interruptions and re-runs are cheap), evaluates H36a/H36b/H36c, and
writes the results JSON + console summary. The testable helpers live in
``src/llm_emotion_hallucination.py`` (unit-tested in
``tests/test_llm_emotion_hallucination.py``); this script is the I/O driver.

Labels: the statistical analysis layer is experimental/frontier; the LLM emotion
readings themselves are qualitative/demo (LLM judgments, not ground truth). CER /
cpWER are post-hoc only and never a routing input. Closes #943. Mode B (Focused
Extension).

Run:
    python3 results/frontier/llm_emotion_hallucination/llm_emotion_hallucination_analysis.py

Outputs (next to this script):
    llm_responses_cache.json   — cached LLM responses keyed by transcript hash
    llm_emotion_hallucination_results.json — full results + per-track rows + verdicts
    FINDINGS.md                — human-readable findings (written by the separate
                                 write_findings step; this driver writes the JSON
                                 that findings are generated from)
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Make src/ importable when run from anywhere.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.llm_emotion_hallucination import (  # noqa: E402
    GOLD_CER_CATASTROPHIC,
    MODE_S_WINDOW_IDS,
    OLLAMA_MODEL,
    evaluate_hypotheses,
    get_llm_emotion,
    lexicon_emotion_metrics,
    load_aishell4_windows,
    load_cache,
    load_gold_tracks,
    save_cache,
)

# --------------------------------------------------------------------------- paths
AISHELL4_JSON = (
    PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
GOLD_TEXT_JSON = (
    PROJECT_ROOT
    / "results"
    / "frontier"
    / "gold_detector_comparison"
    / "gold_track_texts.json"
)
GOLD_CURVE_CSV = (
    PROJECT_ROOT / "results" / "frontier" / "separation_tax" / "phase_curve.csv"
)
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "llm_emotion_hallucination"
CACHE_PATH = OUT_DIR / "llm_responses_cache.json"
RESULTS_JSON = OUT_DIR / "llm_emotion_hallucination_results.json"

CALL_TIMEOUT_SEC = 120  # per ollama call
SAVE_EVERY = 5  # persist cache every N calls


def ollama_available(model: str = OLLAMA_MODEL) -> bool:
    """True iff the ollama CLI and the requested model are available."""
    if shutil.which("ollama") is None:
        return False
    try:
        r = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, timeout=20
        )
        return r.returncode == 0 and model in r.stdout
    except (subprocess.SubprocessError, OSError):
        return False


def run_llm_analysis(rows: list[dict[str, Any]], cache: dict[str, Any]) -> list[dict[str, Any]]:
    """Call the LLM for every non-empty transcript, populating each row with the
    parsed emotion fields. Skips empty transcripts (silent windows). Persists the
    cache periodically."""
    n = len(rows)
    calls_made = 0
    t0 = time.time()
    for i, row in enumerate(rows):
        transcript = row.get("transcript", "")
        if not transcript or not transcript.strip():
            row.update(
                {
                    "emotion": None,
                    "arousal": None,
                    "valence": None,
                    "confidence": None,
                    "reliable": None,
                    "parsed_ok": False,
                    "skipped": "empty_transcript",
                }
            )
            continue
        parsed = get_llm_emotion(transcript, cache, timeout=CALL_TIMEOUT_SEC)
        row.update(
            {
                "emotion": parsed.get("emotion"),
                "arousal": parsed.get("arousal"),
                "valence": parsed.get("valence"),
                "confidence": parsed.get("confidence"),
                "reliable": parsed.get("reliable"),
                "parsed_ok": parsed.get("parsed_ok", False),
                "skipped": False,
            }
        )
        if "_error" in parsed:
            row["llm_error"] = parsed["_error"]
        calls_made += 1
        if calls_made % SAVE_EVERY == 0:
            save_cache(CACHE_PATH, cache)
            elapsed = time.time() - t0
            avg = elapsed / calls_made if calls_made else 0.0
            print(
                f"  [{i+1}/{n}] {row['track_id']} parsed_ok={parsed.get('parsed_ok')} "
                f"conf={parsed.get('confidence')} reliable={parsed.get('reliable')} "
                f"emotion={parsed.get('emotion')} | {calls_made} calls, {avg:.1f}s/call",
                flush=True,
            )
    save_cache(CACHE_PATH, cache)
    return rows


def run_lexicon_fallback(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Lexicon-based fallback when ollama is unavailable. Computes emotion word
    density + diversity per transcript (no `confidence` / `reliable` fields, so
    H36a/H36b are not computable; only the hallucinated-vs-clean density comparison
    is reported)."""
    for row in rows:
        m = lexicon_emotion_metrics(row.get("transcript", ""))
        row.update(
            {
                "emotion_word_density": m["emotion_word_density"],
                "emotion_diversity": m["emotion_diversity"],
                "parsed_ok": True,
                "skipped": False,
                "method": "lexicon_fallback",
            }
        )
    return rows


def lexicon_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarise the lexicon fallback: hallucinated vs clean density/diversity."""
    import numpy as np

    def stat(vals):
        a = np.asarray([v for v in vals if v is not None], dtype=float)
        if len(a) == 0:
            return {"n": 0, "mean": None, "std": None}
        return {"n": int(len(a)), "mean": round(float(np.mean(a)), 6),
                "std": round(float(np.std(a, ddof=1)) if len(a) >= 2 else 0.0, 6)}

    out: dict[str, Any] = {}
    for dataset in sorted({r["source"] for r in rows}):
        for metric in ("emotion_word_density", "emotion_diversity"):
            for label, halluc in (("hallucinated", True), ("clean", False)):
                vals = [r.get(metric) for r in rows
                        if r["source"] == dataset and r["hallucinated"] == halluc]
                out[f"{dataset}_{metric}_{label}"] = stat(vals)
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=== RQ36: LLM emotion reading from hallucinated transcripts ===")
    print(f"Label: experimental/frontier (stats) / qualitative/demo (LLM readings)")
    print(f"Mode B (Focused Extension). Closes #943.")
    print()

    # 1. Load data.
    aishell_rows = load_aishell4_windows(AISHELL4_JSON)
    gold_rows = load_gold_tracks(GOLD_TEXT_JSON, GOLD_CURVE_CSV, n_clean_control=40)
    # Tag source for evaluate_hypotheses (load_aishell4 already sets source=aishell4;
    # load_gold sets source=gold). Mark dataset for evaluate_hypotheses.
    for r in aishell_rows:
        r["dataset"] = "aishell4"
    for r in gold_rows:
        r["dataset"] = "gold"
        r["mode_s"] = False  # Mode S is an AISHELL-4-only concept

    n_aishell_halluc = sum(1 for r in aishell_rows if r["hallucinated"])
    n_aishell_clean = sum(1 for r in aishell_rows if not r["hallucinated"])
    n_aishell_modes = sum(1 for r in aishell_rows if r["mode_s"])
    n_gold_cat = sum(1 for r in gold_rows if r["hallucinated"])
    n_gold_clean = sum(1 for r in gold_rows if not r["hallucinated"])
    print(f"AISHELL-4: {len(aishell_rows)} windows "
          f"({n_aishell_halluc} hallucinated = {n_aishell_modes} Mode S + "
          f"{n_aishell_halluc - n_aishell_modes} diverse; {n_aishell_clean} clean)")
    print(f"  Mode S window ids: {MODE_S_WINDOW_IDS}")
    print(f"Gold benchmark: {len(gold_rows)} tracks ({n_gold_cat} catastrophic, "
          f"{n_gold_clean} clean control)")
    print()

    use_llm = ollama_available(OLLAMA_MODEL)
    if use_llm:
        print(f"ollama available with {OLLAMA_MODEL}: running LLM emotion reading.")
    else:
        print(f"ollama / {OLLAMA_MODEL} NOT available: using lexicon fallback "
              f"(H36a/H36b not computable; density comparison only).")

    cache = load_cache(CACHE_PATH) if use_llm else {}
    print(f"Cache: {len(cache)} cached responses loaded.")

    # 2. Run the analysis (LLM or lexicon).
    all_rows = aishell_rows + gold_rows
    if use_llm:
        t0 = time.time()
        all_rows = run_llm_analysis(all_rows, cache)
        dt = time.time() - t0
        n_called = sum(1 for r in all_rows if not r.get("skipped"))
        print(f"\nLLM calls: {n_called} in {dt:.1f}s "
              f"({dt/n_called:.1f}s/call)" if n_called else "\nno calls")
    else:
        all_rows = run_lexicon_fallback(all_rows)

    # 3. Evaluate hypotheses (LLM path only; lexicon path gets a density summary).
    if use_llm:
        verdicts = evaluate_hypotheses(all_rows)
        # Also per-dataset verdicts for cross-dataset robustness.
        aishell_verdicts = evaluate_hypotheses([r for r in all_rows if r["dataset"] == "aishell4"])
        gold_verdicts_h36ab = evaluate_hypotheses([r for r in all_rows if r["dataset"] == "gold"])
    else:
        verdicts = {"note": "ollama unavailable; H36a/H36b/H36c not computable."}
        aishell_verdicts = verdicts
        gold_verdicts_h36ab = verdicts

    # 4. Assemble results.
    n_parsed_aishell = sum(1 for r in aishell_rows if r.get("parsed_ok"))
    n_parsed_gold = sum(1 for r in gold_rows if r.get("parsed_ok"))
    n_failures = sum(1 for r in all_rows if r.get("llm_error"))

    summary: dict[str, Any] = {
        "label": "experimental/frontier" if use_llm else "experimental/frontier",
        "llm_readings_label": "qualitative/demo",
        "rq": "RQ36: LLM emotion reading from hallucinated transcripts",
        "closes_issue": 943,
        "mode": "B (Focused Extension)",
        "method": (
            f"deepseek-r1:7b via ollama; emotion-reading prompt; "
            f"{CALL_TIMEOUT_SEC}s per-call timeout; transcript-hash cache"
            if use_llm
            else "lexicon fallback (ollama unavailable); emotion word density + diversity"
        ),
        "ollama_available": bool(use_llm),
        "ollama_model": OLLAMA_MODEL if use_llm else None,
        "data_sources": {
            "aishell4": {
                "path": str(AISHELL4_JSON.relative_to(PROJECT_ROOT)),
                "label": "external/sanity-check",
                "n_windows": len(aishell_rows),
                "n_hallucinated": n_aishell_halluc,
                "n_mode_s": n_aishell_modes,
                "n_diverse": n_aishell_halluc - n_aishell_modes,
                "n_clean": n_aishell_clean,
                "mode_s_window_ids": MODE_S_WINDOW_IDS,
                "hallucination_label": "always_separated_cpwer > 1.0",
                "transcript": "concatenated separated_text_per_speaker (mixed_text fallback for empty)",
                "n_parsed": n_parsed_aishell,
            },
            "gold": {
                "text_path": str(GOLD_TEXT_JSON.relative_to(PROJECT_ROOT)),
                "curve_path": str(GOLD_CURVE_CSV.relative_to(PROJECT_ROOT)),
                "label": "experimental/frontier",
                "n_tracks": len(gold_rows),
                "n_catastrophic": n_gold_cat,
                "n_clean_control": n_gold_clean,
                "hallucination_label": f"cer_sep2 > {GOLD_CER_CATASTROPHIC}",
                "transcript": "sep2_text (decoded gold separated track)",
                "substitution_note": (
                    "Task brief named causal_hallucination_probe/probe_rows.csv as the "
                    "gold source, but that file stores only reduced metrics, not decoded "
                    "text. gold_track_texts.json is the project's decoded gold-text cache "
                    "(RQ21) joined with phase_curve.csv for the cer_sep2 label. Faithful "
                    "substitution; documented in FINDINGS.md."
                ),
                "n_parsed": n_parsed_gold,
            },
        },
        "n_llm_failures": n_failures,
        "hypotheses": {
            "h36a": {
                "statement": "LLM confidence variance on hallucinated > clean (F > 2.0)",
                "success_criterion": "F-statistic > 2.0",
                "kill_criterion": "F <= 2.0",
                **(aishell_verdicts.get("h36a", {}) if use_llm else {}),
            },
            "h36b": {
                "statement": "LLM `reliable` field classifies hallucinated vs clean (AUC > 0.80)",
                "success_criterion": "AUC > 0.80",
                "kill_criterion": "AUC <= 0.80",
                **(aishell_verdicts.get("h36b", {}) if use_llm else {}),
            },
            "h36c": {
                "statement": "Mode S confidence within 1 SD of clean mean (indistinguishable)",
                "success_criterion": "Mode S within 1 SD of clean mean",
                "kill_criterion": "Mode S outside 1 SD",
                **(aishell_verdicts.get("h36c", {}) if use_llm else {}),
            },
        },
        "cross_dataset_gold": gold_verdicts_h36ab if use_llm else None,
        "lexicon_fallback_summary": lexicon_summary(all_rows) if not use_llm else None,
        "per_track_rows": all_rows,
    }

    RESULTS_JSON.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nResults written to: {RESULTS_JSON.relative_to(PROJECT_ROOT)}")

    # 5. Console summary.
    print("\n=== Hypothesis verdicts (AISHELL-4, primary) ===")
    if use_llm:
        for h in ("h36a", "h36b", "h36c"):
            v = aishell_verdicts.get(h, {})
            verdict = "SUPPORTED" if v.get("supported") else "NOT SUPPORTED"
            print(f"  {h}: {verdict}")
            if h == "h36a":
                print(f"    F={v.get('f_stat')} (var_halluc={v.get('var_halluc')} vs "
                      f"var_clean={v.get('var_clean')}, n_halluc={v.get('n_halluc')}, "
                      f"n_clean={v.get('n_clean')}, p={v.get('p_value')})")
            elif h == "h36b":
                print(f"    AUC(reliable)={v.get('auc_reliable')} "
                      f"(secondary AUC(1-confidence)={v.get('auc_confidence_secondary')})")
            elif h == "h36c":
                print(f"    Mode S mean={v.get('mode_s_mean')} (n={v.get('mode_s_n')}) vs "
                      f"clean mean={v.get('clean_mean')} sd={v.get('clean_sd')}; "
                      f"within 1 SD={v.get('within_1sd')} (max dev={v.get('max_deviation_sd')} SD)")
        print("\n=== Cross-dataset (gold benchmark) ===")
        for h in ("h36a", "h36b"):
            v = gold_verdicts_h36ab.get(h, {})
            verdict = "SUPPORTED" if v.get("supported") else "NOT SUPPORTED"
            print(f"  {h}: {verdict} "
                  f"(F={v.get('f_stat')}, AUC={v.get('auc_reliable')})")
    else:
        print("  ollama unavailable; lexicon fallback only.")
        ls = summary["lexicon_fallback_summary"]
        for k, v in ls.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
