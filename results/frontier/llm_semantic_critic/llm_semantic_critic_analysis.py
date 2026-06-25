"""RQ34: LLM-based semantic critic for Mode S detection — analysis driver.

Runs the deepseek-r1:7b semantic critic (via ollama) on all 77 AISHELL-4 windows'
separated transcripts, plus a character 3-gram KL-divergence fallback, and evaluates
whether semantic analysis catches the 2 Mode S windows (22, 30) that escape every
surface detector (RQ19/22/23/28).

Label: experimental/frontier (n-gram fallback) + qualitative/demo (LLM judgments).
Source data: results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json
(label external/sanity-check, read-only). No gold tables touched. Closes #941.

Hypotheses
----------
- H34a: LLM catches both Mode S windows at 90% specificity (sens = 100% at 90% spec).
- H34b: LLM achieves > 95% sensitivity on all 37 AISHELL-4 hallucinations.
- H34c: LLM outperforms lang-id entropy on Mode S (Mode S sens > 0%).

Usage
-----
    python3 results/frontier/llm_semantic_critic/llm_semantic_critic_analysis.py

LLM responses are cached to llm_raw_responses.json; re-runs load from cache (fast).
If ollama is unavailable, only the n-gram fallback runs.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

# make src importable when run as a script
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from src.llm_semantic_critic import (  # noqa: E402
    CATASTROPHIC_CPWER,
    CR_THRESHOLD,
    LANG_ID_ENTROPY_THRESHOLD,
    LENGTH_RATIO_THRESHOLD,
    N_BOOT,
    SEED,
    TARGET_SPECIFICITY,
    bootstrap_sensitivity_ci,
    bootstrap_specificity_ci,
    build_reference_distribution,
    calibrate_threshold_at_specificity,
    compute_anomaly_score,
    compression_ratio,
    evaluate_at_threshold,
    hallucination_score,
    judge_window,
    label_window,
    language_id_entropy,
    max_across_speakers,
    ollama_available,
    ollama_llm,
    parse_llm_response,
    separated_concat,
    subgroup_sensitivity,
)

SRC_JSON = (
    PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "llm_semantic_critic"
OUT_CSV = OUT_DIR / "llm_semantic_critic_results.csv"
OUT_JSON = OUT_DIR / "llm_semantic_critic_results.json"
CACHE_JSON = OUT_DIR / "llm_raw_responses.json"
FINDINGS_MD = OUT_DIR / "FINDINGS.md"

LLM_MODEL = "deepseek-r1:7b"
LLM_NUM_PREDICT = 1024


def load_source() -> dict[str, Any]:
    return json.loads(SRC_JSON.read_text(encoding="utf-8"))


def run_llm_critic(
    windows: list[dict[str, Any]], labels: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run the LLM critic on each window's separated text, with on-disk caching.

    Returns a list of parsed responses (hallucinated, confidence, reason, raw) per
    window. Loads from cache if available; otherwise calls the LLM and saves
    incrementally (so a partial run can be resumed)."""
    cache: dict[str, Any] = {"model": LLM_MODEL, "responses": {}}
    if CACHE_JSON.exists():
        try:
            cache = json.loads(CACHE_JSON.read_text(encoding="utf-8"))
            if cache.get("model") != LLM_MODEL:
                cache = {"model": LLM_MODEL, "responses": {}}
        except (json.JSONDecodeError, ValueError):
            cache = {"model": LLM_MODEL, "responses": {}}

    use_llm = ollama_available(model=LLM_MODEL)
    if not use_llm:
        print(f"[llm] ollama/{LLM_MODEL} not available — skipping LLM critic.")
        return [{"hallucinated": False, "confidence": 0.5, "reason": "ollama unavailable",
                 "raw": ""} for _ in windows]

    llm = ollama_llm(model=LLM_MODEL, num_predict=LLM_NUM_PREDICT)
    results: list[dict[str, Any]] = []
    n_cached = 0
    n_called = 0
    for i, (w, lbl) in enumerate(zip(windows, labels)):
        key = str(w["window_id"])
        if key in cache["responses"]:
            r = cache["responses"][key]
            # ensure parsed fields are present
            if "hallucinated" not in r:
                r.update(parse_llm_response(r.get("raw", "")))
            results.append(r)
            n_cached += 1
            continue
        sep_text = lbl["separated_text"]
        if not sep_text or not sep_text.strip():
            r = {"hallucinated": False, "confidence": 0.5, "reason": "empty transcript", "raw": ""}
            results.append(r)
            cache["responses"][key] = r
            continue
        t0 = time.time()
        raw = llm(build_critic_prompt_cached(sep_text))
        dt = time.time() - t0
        parsed = parse_llm_response(raw)
        r = {**parsed, "raw": raw, "call_time_sec": round(dt, 2)}
        results.append(r)
        cache["responses"][key] = r
        n_called += 1
        print(f"  [llm] window {w['window_id']:3d}: hallucinated={parsed['hallucinated']}, "
              f"confidence={parsed['confidence']:.2f}, {dt:.1f}s "
              f"({'cached' if key in cache['responses'] else 'new'})")
        # save cache incrementally so partial runs can resume
        CACHE_JSON.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")
    print(f"[llm] {n_cached} cached, {n_called} new calls")
    return results


def build_critic_prompt_cached(separated_text: str) -> str:
    """Build the critic prompt (imported lazily to avoid circular import)."""
    from src.llm_semantic_critic import build_critic_prompt
    return build_critic_prompt(separated_text)


def run_ngram_fallback(
    labels: list[dict[str, Any]], n: int = 3,
) -> tuple[list[float], dict[str, float]]:
    """Run the character n-gram KL-divergence fallback.

    Builds the reference distribution from the 40 non-hallucinated tracks, then
    computes each track's KL anomaly score. Returns (scores, ref_distribution)."""
    neg_texts = [lbl["separated_text"] for lbl in labels if not lbl["hallucinated"]]
    ref_dist = build_reference_distribution(neg_texts, n=n)
    scores = [compute_anomaly_score(lbl["separated_text"], ref_dist, n=n) for lbl in labels]
    return scores, ref_dist


def evaluate_detector(
    scores: list[float], labels: list[dict[str, Any]], detector_name: str,
) -> dict[str, Any]:
    """Calibrate a detector at 90% specificity and evaluate on all subgroups.

    Returns threshold, overall + subgroup metrics, bootstrap CIs."""
    n = len(scores)
    halluc_flags = [lbl["hallucinated"] for lbl in labels]
    mode_s_flags = [lbl["mode_s"] for lbl in labels]
    diverse_flags = [lbl["diverse_hallucination"] for lbl in labels]

    neg_scores = [s for s, h in zip(scores, halluc_flags) if not h]
    pos_scores = [s for s, h in zip(scores, halluc_flags) if h]
    cal = calibrate_threshold_at_specificity(neg_scores, pos_scores, TARGET_SPECIFICITY)
    threshold = cal["threshold"]

    label_arr = np.array([1 if h else 0 for h in halluc_flags], dtype=float)
    score_arr = np.array(scores, dtype=float)
    overall = evaluate_at_threshold(scores, [1 if h else 0 for h in halluc_flags], threshold)
    ms = subgroup_sensitivity(scores, mode_s_flags, threshold)
    div = subgroup_sensitivity(scores, diverse_flags, threshold)

    sens_ci = bootstrap_sensitivity_ci(score_arr, label_arr, threshold, N_BOOT, SEED)
    spec_ci = bootstrap_specificity_ci(score_arr, label_arr, threshold, N_BOOT, SEED)

    # bootstrap CI for Mode S sensitivity (fixed threshold)
    ms_labels = np.array([1 if m else 0 for m in mode_s_flags], dtype=float)
    ms_sens_ci = bootstrap_sensitivity_ci(score_arr, ms_labels, threshold, N_BOOT, SEED)

    return {
        "detector": detector_name,
        "threshold": round(threshold, 6),
        "specificity": round(overall["specificity"], 6),
        "specificity_ci_95": [round(spec_ci[0], 6), round(spec_ci[1], 6)],
        "sensitivity_all_hallucinated": round(overall["sensitivity"], 6),
        "sensitivity_all_hallucinated_ci_95": [round(sens_ci[0], 6), round(sens_ci[1], 6)],
        "sensitivity_mode_s": round(ms["sensitivity"], 6),
        "sensitivity_mode_s_ci_95": [round(ms_sens_ci[0], 6), round(ms_sens_ci[1], 6)],
        "sensitivity_diverse": round(div["sensitivity"], 6),
        "tp_all": overall["tp"], "fp": overall["fp"],
        "tn": overall["tn"], "fn_all": overall["fn"],
        "tp_mode_s": ms["tp"], "n_mode_s": ms["n"],
        "tp_diverse": div["tp"], "n_diverse": div["n"],
        "n_hallucinated": overall["tp"] + overall["fn"],
        "n_nonhallucinated": overall["fp"] + overall["tn"],
        "mode_s_window_ids": [lbl["window_id"] for lbl in labels if lbl["mode_s"]],
        "flagged_window_ids": [lbl["window_id"] for lbl, s in zip(labels, scores)
                                if s >= threshold - 1e-9],
        "mode_s_scores": {str(lbl["window_id"]): round(s, 6)
                          for lbl, s in zip(labels, scores) if lbl["mode_s"]},
    }


def lang_id_baseline(labels: list[dict[str, Any]]) -> dict[str, Any]:
    """Lang-id entropy baseline (RQ13): flag if lang_id_entropy > 0.409."""
    scores = [lbl["lang_id_entropy"] for lbl in labels]
    halluc_flags = [lbl["hallucinated"] for lbl in labels]
    mode_s_flags = [lbl["mode_s"] for lbl in labels]
    diverse_flags = [lbl["diverse_hallucination"] for lbl in labels]
    threshold = LANG_ID_ENTROPY_THRESHOLD
    overall = evaluate_at_threshold(
        scores, [1 if h else 0 for h in halluc_flags], threshold)
    ms = subgroup_sensitivity(scores, mode_s_flags, threshold)
    div = subgroup_sensitivity(scores, diverse_flags, threshold)
    return {
        "detector": "lang_id_entropy (RQ13 baseline)",
        "threshold": threshold,
        "specificity": round(overall["specificity"], 6),
        "sensitivity_all_hallucinated": round(overall["sensitivity"], 6),
        "sensitivity_mode_s": round(ms["sensitivity"], 6),
        "sensitivity_diverse": round(div["sensitivity"], 6),
        "tp_all": overall["tp"], "fp": overall["fp"],
        "tn": overall["tn"], "fn_all": overall["fn"],
        "tp_mode_s": ms["tp"], "n_mode_s": ms["n"],
        "tp_diverse": div["tp"], "n_diverse": div["n"],
        "note": "By definition Mode S has lang_id_entropy < 0.409, so this baseline misses both Mode S windows.",
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = load_source()
    windows = data["windows"]
    n = len(windows)

    # --- per-window labels + surface features
    labels = [label_window(w) for w in windows]
    n_halluc = sum(1 for l in labels if l["hallucinated"])
    n_nonhalluc = n - n_halluc
    n_mode_s = sum(1 for l in labels if l["mode_s"])
    n_diverse = sum(1 for l in labels if l["diverse_hallucination"])
    mode_s_ids = [l["window_id"] for l in labels if l["mode_s"]]

    print(f"=== RQ34: LLM semantic critic (AISHELL-4, {n} tracks) ===")
    print(f"Label: experimental/frontier + qualitative/demo (LLM)  |  Source: {SRC_JSON.relative_to(PROJECT_ROOT)}")
    print(f"Hallucinated: {n_halluc}  |  non-hallucinated: {n_nonhalluc}  "
          f"|  Mode S: {n_mode_s}  |  diverse: {n_diverse}")
    print(f"Mode S window ids: {mode_s_ids}")
    print()

    # --- LLM critic (cached)
    print("[1/3] Running LLM semantic critic (deepseek-r1:7b via ollama)...")
    llm_responses = run_llm_critic(windows, labels)
    llm_scores = [
        hallucination_score(r["hallucinated"], r["confidence"]) for r in llm_responses
    ]
    # also track raw LLM boolean decisions
    llm_bool_scores = [1.0 if r["hallucinated"] else 0.0 for r in llm_responses]

    # --- n-gram KL fallback
    print("[2/3] Running character 3-gram KL-divergence fallback...")
    ngram_scores, ref_dist = run_ngram_fallback(labels, n=3)
    ref_vocab_size = len(ref_dist)

    # --- lang-id baseline
    print("[3/3] Evaluating detectors...")
    lang_baseline = lang_id_baseline(labels)

    # --- evaluate each detector at 90% specificity
    llm_eval = evaluate_detector(llm_scores, labels, "llm_semantic_critic (deepseek-r1:7b)")
    llm_bool_eval = evaluate_detector(llm_bool_scores, labels, "llm_boolean_decision")
    ngram_eval = evaluate_detector(ngram_scores, labels, "char_3gram_kl_divergence")

    # --- hypothesis verdicts (LLM is the primary method)
    h34a_supported = (llm_eval["sensitivity_mode_s"] >= 1.0
                      and llm_eval["specificity"] >= TARGET_SPECIFICITY)
    h34b_supported = llm_eval["sensitivity_all_hallucinated"] > 0.95
    h34c_supported = llm_eval["sensitivity_mode_s"] > 0.0  # vs lang-id's 0%

    # --- per-window rows for CSV
    rows: list[dict[str, Any]] = []
    for w, lbl, llm_r, llm_s, ng_s in zip(windows, labels, llm_responses, llm_scores, ngram_scores):
        rows.append({
            "window_id": w["window_id"],
            "hallucinated": int(lbl["hallucinated"]),
            "mode_s": int(lbl["mode_s"]),
            "diverse_hallucination": int(lbl["diverse_hallucination"]),
            "lang_id_entropy": round(lbl["lang_id_entropy"], 6),
            "length_ratio": round(lbl["length_ratio"], 6),
            "cr": round(lbl["cr"], 6),
            "separated_cpwer": round(lbl["separated_cpwer"], 6),
            "llm_hallucinated": int(llm_r["hallucinated"]),
            "llm_confidence": round(llm_r["confidence"], 6),
            "llm_score": round(llm_s, 6),
            "ngram_kl_score": round(ng_s, 6),
            "llm_reason": llm_r.get("reason", "")[:200],
        })

    # --- summary
    use_llm = ollama_available(model=LLM_MODEL)
    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "llm_label": "qualitative/demo",
        "rq": "RQ34: LLM-based semantic critic for Mode S detection",
        "closes_issue": 941,
        "source_data": str(SRC_JSON.relative_to(PROJECT_ROOT)),
        "source_label": "external/sanity-check",
        "method": (
            "LLM semantic critic (deepseek-r1:7b via ollama) evaluates each separated "
            "transcript for hallucination. A character 3-gram KL-divergence fallback tests "
            "distributional anomaly. Both calibrated at 90% specificity on 40 non-hallucinated "
            "tracks. Mode S = windows 22, 30 (near-duplicate Chinese hallucinations escaping "
            "all surface detectors)."
        ),
        "meeting_id": data["meeting_id"],
        "n_windows": n,
        "n_hallucinated": n_halluc,
        "n_nonhallucinated": n_nonhalluc,
        "n_mode_s": n_mode_s,
        "n_diverse_hallucination": n_diverse,
        "mode_s_window_ids": mode_s_ids,
        "hallucination_label": "always_separated_cpwer > 1.0 (37/40 split, RQ12)",
        "mode_s_definition": (
            "hallucinated AND lang_id_entropy < 0.409 AND length_ratio < 2.0 AND cr < 2.4"
        ),
        "llm_backend": {
            "model": LLM_MODEL,
            "available": bool(use_llm),
            "temperature": 0.0,
            "num_predict": LLM_NUM_PREDICT,
            "prompt_template": "RQ34 spec (3 criteria: semantic sense, repetitiveness, character patterns)",
        },
        "ngram_fallback": {
            "n": 3,
            "reference": "average 3-gram distribution of 40 non-hallucinated tracks",
            "vocab_size": ref_vocab_size,
            "metric": "KL(text || reference), additive smoothing 1e-9",
        },
        "detectors": {
            "llm_semantic_critic": llm_eval,
            "llm_boolean_decision": llm_bool_eval,
            "char_3gram_kl_divergence": ngram_eval,
            "lang_id_entropy_baseline": lang_baseline,
        },
        "hypothesis_verdicts": {
            "H34a": {
                "statement": "LLM semantic critic catches both Mode S windows at 90% specificity",
                "success_criterion": "sensitivity_mode_s = 100% at specificity >= 90%",
                "sensitivity_mode_s": llm_eval["sensitivity_mode_s"],
                "specificity": llm_eval["specificity"],
                "ci_95_mode_s_sensitivity": llm_eval["sensitivity_mode_s_ci_95"],
                "supported": bool(h34a_supported),
                "reason": (
                    f"LLM Mode S sensitivity = {llm_eval['sensitivity_mode_s']:.0%} "
                    f"({llm_eval['tp_mode_s']}/{llm_eval['n_mode_s']}) at "
                    f"{llm_eval['specificity']:.1%} specificity. "
                    f"Mode S scores: {llm_eval['mode_s_scores']}."
                ),
            },
            "H34b": {
                "statement": "LLM semantic critic achieves > 95% sensitivity on all AISHELL-4 hallucinations",
                "success_criterion": "sensitivity_all_hallucinated > 95%",
                "sensitivity_all_hallucinated": llm_eval["sensitivity_all_hallucinated"],
                "ci_95": llm_eval["sensitivity_all_hallucinated_ci_95"],
                "supported": bool(h34b_supported),
                "reason": (
                    f"LLM all-hallucinated sensitivity = "
                    f"{llm_eval['sensitivity_all_hallucinated']:.1%} "
                    f"({llm_eval['tp_all']}/{llm_eval['n_hallucinated']}) at "
                    f"{llm_eval['specificity']:.1%} specificity."
                ),
            },
            "H34c": {
                "statement": "LLM semantic critic outperforms lang-id entropy on Mode S",
                "success_criterion": "sensitivity_mode_s > 0% (lang-id gets 0%)",
                "llm_sensitivity_mode_s": llm_eval["sensitivity_mode_s"],
                "lang_id_sensitivity_mode_s": lang_baseline["sensitivity_mode_s"],
                "supported": bool(h34c_supported),
                "reason": (
                    f"LLM Mode S sensitivity = {llm_eval['sensitivity_mode_s']:.0%} vs "
                    f"lang-id entropy = {lang_baseline['sensitivity_mode_s']:.0%}. "
                    f"{'LLM catches Mode S where lang-id cannot.' if h34c_supported else 'LLM also misses Mode S.'}"
                ),
            },
        },
        "per_window": rows,
    }

    # --- write CSV
    csv_fields = [
        "window_id", "hallucinated", "mode_s", "diverse_hallucination",
        "lang_id_entropy", "length_ratio", "cr", "separated_cpwer",
        "llm_hallucinated", "llm_confidence", "llm_score",
        "ngram_kl_score", "llm_reason",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=csv_fields)
        wr.writeheader()
        for r in rows:
            wr.writerow({k: r.get(k, "") for k in csv_fields})

    # --- write JSON
    OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    # --- console summary
    print()
    print(f"{'detector':36s} {'thresh':>9s} {'spec':>6s} {'sens_AH':>8s} {'sens_MS':>8s} {'sens_DIV':>9s}")
    for d in (llm_eval, llm_bool_eval, ngram_eval, lang_baseline):
        print(f"{d['detector']:36s} {d['threshold']:9.4f} {d['specificity']:6.1%} "
              f"{d['sensitivity_all_hallucinated']:8.1%} {d['sensitivity_mode_s']:8.1%} "
              f"{d['sensitivity_diverse']:9.1%}")
    print()
    print("Hypothesis verdicts (LLM semantic critic):")
    print(f"  H34a (Mode S sens = 100% at 90% spec): "
          f"{'SUPPORTED' if h34a_supported else 'NOT SUPPORTED'} "
          f"(sens_MS={llm_eval['sensitivity_mode_s']:.0%}, spec={llm_eval['specificity']:.1%})")
    print(f"  H34b (all-halluc sens > 95%): "
          f"{'SUPPORTED' if h34b_supported else 'NOT SUPPORTED'} "
          f"(sens_AH={llm_eval['sensitivity_all_hallucinated']:.1%})")
    print(f"  H34c (LLM Mode S sens > 0%, beats lang-id): "
          f"{'SUPPORTED' if h34c_supported else 'NOT SUPPORTED'} "
          f"(LLM sens_MS={llm_eval['sensitivity_mode_s']:.0%}, lang-id sens_MS={lang_baseline['sensitivity_mode_s']:.0%})")
    print()
    print(f"Mode S LLM scores: {llm_eval['mode_s_scores']}")
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
