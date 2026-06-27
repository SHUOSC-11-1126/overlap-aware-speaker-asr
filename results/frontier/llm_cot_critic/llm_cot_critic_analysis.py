"""RQ52: Chain-of-thought (CoT) LLM critic for Mode S — analysis driver.

Runs a single deepseek-r1:7b call PER window with a 5-step chain-of-thought
prompt (language -> repetition -> coherence -> insertion -> verdict) on the
max-lang-id-entropy separated track's transcript (worst-case speaker), then
calibrates at 90% specificity on the 40 non-hallucinated tracks and compares
to RQ34 (zero-shot direct verdict) and RQ41 (5-call ensemble).

Background
----------
- RQ34 (zero-shot, PR #951): 52.5% FP, 0% Mode S sensitivity at 90% specificity.
- RQ41 (ensemble, PR #961): 62.5% FP (worse than single-call), 0% Mode S at 90% spec.
- RQ36 (PR #956): the LLM reads Mode S as reliable speech.

RQ52 asks whether explicit step-by-step reasoning (articulating what makes a
transcript hallucinated BEFORE the verdict) overcomes the ~50% FP rate.

Hypotheses (pre-registered)
---------------------------
- H52a: CoT Mode S sensitivity > 50% at 90% specificity (beats zero-shot's 0%).
- H52b: CoT false-positive rate < 50% (beats zero-shot's 52.5%).
- H52c: CoT AUC > 0.60 (beats random and zero-shot's near-chance).

Method
------
- For each of the 77 windows, take the MAX-lang-id-entropy separated track's
  transcript (wor-case speaker). Empty transcripts (silence windows) are
  short-circuited (no LLM call).
- Single deepseek-r1:7b call at T=0.0 (deterministic, unlike RQ41's T=0.0-0.8).
- Continuous score = hallucination_score(verdict, confidence) in [0, 1]:
  confidence if hallucinated, else 1 - confidence (RQ34 convention).
- Calibrate at 90% specificity on the 40 non-hallucinated tracks (one-sided:
  flag if score >= threshold). Bootstrap 95% CIs (10,000 resamples, seed=42).
- AUC via rank-based Mann-Whitney U over all 77 windows.
- RQ34 comparison: load RQ34's cached responses, recompute FP/sensitivity/AUC
  with the SAME metric functions (apples-to-apples). RQ34 used concatenated
  text, so the comparison is approximate (noted in FINDINGS).
- RQ41 comparison: load RQ41's published results JSON.

Label: experimental/frontier + qualitative/demo (LLM outputs).
Source data: results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json
(external/sanity-check, read-only — NOT modified).

Reproduce: python3 results/frontier/llm_cot_critic/llm_cot_critic_analysis.py
"""
from __future__ import annotations

import csv
import json
import math
import sys
import time
import unicodedata
import zlib
from pathlib import Path
from typing import Any

import numpy as np

# Make the repo src importable when run as a script
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from src.llm_cot_critic import (  # noqa: E402
    CATASTROPHIC_CPWER,
    CR_THRESHOLD,
    LANG_ID_ENTROPY_THRESHOLD,
    LENGTH_RATIO_THRESHOLD,
    N_BOOT,
    SEED,
    TARGET_SPECIFICITY,
    bootstrap_ci,
    build_cot_prompt,
    cache_key,
    calibrate_threshold_at_specificity,
    evaluate_at_threshold,
    false_positive_rate,
    hallucination_score,
    judge_window_cot,
    load_cache,
    ollama_available,
    ollama_llm,
    parse_cot_verdict,
    roc_auc,
    save_cache,
    subgroup_sensitivity,
)

SRC_JSON = (
    PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "llm_cot_critic"
OUT_CSV = OUT_DIR / "llm_cot_critic_results.csv"
OUT_JSON = OUT_DIR / "llm_cot_critic_results.json"
CACHE_JSON = OUT_DIR / "llm_cot_cache.json"
FINDINGS_MD = OUT_DIR / "FINDINGS.md"

# RQ34 / RQ41 comparison sources (read-only)
RQ34_CACHE = PROJECT_ROOT / "results" / "frontier" / "llm_semantic_critic" / "llm_raw_responses.json"
RQ41_RESULTS = PROJECT_ROOT / "results" / "frontier" / "llm_ensemble_critic" / "llm_ensemble_results.json"

LLM_MODEL = "deepseek-r1:7b"
LLM_NUM_PREDICT = 1024


# ----------------------------------------------------------------- surface primitives
# (lifted from RQ13/RQ19 so the Mode S definition is directly comparable)
def script_category(ch: str) -> str:
    if ch.isspace():
        return "Space"
    name = unicodedata.name(ch, "")
    if not name:
        return "Other"
    first = name.split()[0]
    if first == "CJK":
        return "Han"
    if "LATIN" in name:
        return "Latin"
    if first in ("HIRAGANA", "KATAKANA", "HANGUL"):
        return first
    cat = unicodedata.category(ch)
    if cat.startswith("P") or cat.startswith("S"):
        return "Punct"
    return "Other"


def language_id_entropy(text: str) -> float:
    if not text or not text.strip():
        return 0.0
    counts: dict[str, int] = {}
    for ch in text:
        sc = script_category(ch)
        counts[sc] = counts.get(sc, 0) + 1
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    h = 0.0
    for c in counts.values():
        p = c / total
        if p > 0:
            h -= p * math.log2(p)
    return h


def compression_ratio(text: str) -> float:
    if not text or not text.strip():
        return 0.0
    b = text.encode("utf-8")
    c = zlib.compress(b)
    return len(b) / len(c) if len(c) > 0 else 0.0


def length_ratio(window: dict[str, Any]) -> float:
    sep = float(window.get("separated_total_length", 0) or 0)
    mix = float(window.get("mixed_text_length", 0) or 0)
    return sep / max(1.0, mix)


def max_entropy_speaker_text(window: dict[str, Any]) -> str:
    """Return the transcript of the separated speaker with the HIGHEST lang-id
    entropy (worst-case speaker). If all speakers are empty, returns "".

    This is the RQ52 text-input convention: the most script-diverse speaker is
    the most likely to carry hallucination artifacts, so we audit that track.
    For Mode S windows (low entropy by definition) this reduces to the single
    non-empty speaker, matching the concatenated-text convention."""
    speakers = window.get("separated_text_per_speaker", {})
    best_text = ""
    best_ent = -1.0
    for _spk, text in speakers.items():
        t = str(text) if text is not None else ""
        if not t.strip():
            continue
        ent = language_id_entropy(t)
        if ent > best_ent:
            best_ent = ent
            best_text = t.strip()
    return best_text


def max_across_speakers(window: dict[str, Any], fn) -> float:
    vals = [
        fn(str(t))
        for t in window.get("separated_text_per_speaker", {}).values()
        if t is not None and str(t).strip()
    ]
    return max(vals) if vals else 0.0


def label_window(window: dict[str, Any]) -> dict[str, Any]:
    """Compute surface features + labels for one window (RQ12/RQ13/RQ19 consistent)."""
    sep_cpwer = float(window["always_separated_cpwer"])
    ent = max_across_speakers(window, language_id_entropy)
    mcr = max_across_speakers(window, compression_ratio)
    lr = length_ratio(window)
    halluc = sep_cpwer > CATASTROPHIC_CPWER
    mode_s = (halluc and ent < LANG_ID_ENTROPY_THRESHOLD
              and lr < LENGTH_RATIO_THRESHOLD and mcr < CR_THRESHOLD)
    diverse = halluc and ent > LANG_ID_ENTROPY_THRESHOLD
    return {
        "window_id": window["window_id"],
        "hallucinated": bool(halluc),
        "mode_s": bool(mode_s),
        "diverse_hallucination": bool(diverse),
        "lang_id_entropy": float(ent),
        "length_ratio": float(lr),
        "cr": float(mcr),
        "separated_cpwer": float(sep_cpwer),
        "audit_text": max_entropy_speaker_text(window),
        "num_speakers": int(window.get("num_speakers", 0)),
    }


# ----------------------------------------------------------------- LLM critic runner
def run_cot_critic(
    windows: list[dict[str, Any]], labels: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run the CoT critic on each window's worst-case-speaker transcript, with
    on-disk caching. Returns parsed responses per window. Loads from cache if
    available; otherwise calls the LLM and saves incrementally (resumable)."""
    cache: dict[str, Any] = {"model": LLM_MODEL, "prompt": "cot_5step", "responses": {}}
    if CACHE_JSON.exists():
        try:
            loaded = json.loads(CACHE_JSON.read_text(encoding="utf-8"))
            if (isinstance(loaded, dict) and loaded.get("model") == LLM_MODEL
                    and loaded.get("prompt") == "cot_5step"):
                cache = loaded
        except (json.JSONDecodeError, ValueError):
            pass

    use_llm = ollama_available(model=LLM_MODEL)
    if not use_llm:
        print(f"[cot] ollama/{LLM_MODEL} not available — skipping CoT critic.")
        return [{"hallucinated": False, "confidence": 0.5, "verdict_raw": "",
                 "reason": "ollama unavailable", "raw": ""} for _ in windows]

    llm = ollama_llm(model=LLM_MODEL, num_predict=LLM_NUM_PREDICT)
    results: list[dict[str, Any]] = []
    n_cached = 0
    n_called = 0
    t_start = time.time()
    for i, (w, lbl) in enumerate(zip(windows, labels)):
        wid = str(w["window_id"])
        text = lbl["audit_text"]
        key = cache_key(text) if text.strip() else f"empty_{wid}"
        if key in cache["responses"]:
            r = cache["responses"][key]
            if "hallucinated" not in r:
                r.update(parse_cot_verdict(r.get("raw", "")))
            results.append(r)
            n_cached += 1
            continue
        if not text.strip():
            r = {"hallucinated": False, "confidence": 0.5, "verdict_raw": "",
                 "reason": "empty transcript", "raw": ""}
            results.append(r)
            cache["responses"][key] = r
            continue
        t0 = time.time()
        raw = llm(build_cot_prompt(text))
        dt = time.time() - t0
        parsed = parse_cot_verdict(raw)
        r = {**parsed, "reason": parsed.get("verdict_raw", ""), "raw": raw,
             "call_time_sec": round(dt, 2)}
        results.append(r)
        cache["responses"][key] = r
        n_called += 1
        elapsed = time.time() - t_start
        print(f"  [cot] {i + 1}/{len(windows)} win={w['window_id']:3d}: "
              f"verdict={'YES' if parsed['hallucinated'] else 'NO'} "
              f"conf={parsed['confidence']:.2f} {dt:.1f}s "
              f"(halluc={lbl['hallucinated']} ms={lbl['mode_s']}) "
              f"elapsed={elapsed:.0f}s", flush=True)
        # save cache incrementally so partial runs can resume
        CACHE_JSON.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")
    print(f"[cot] {n_cached} cached, {n_called} new calls", flush=True)
    return results


# ----------------------------------------------------------------- RQ34 comparison
def load_rq34_comparison(labels: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Load RQ34's cached zero-shot responses and recompute FP/sensitivity/AUC
    with RQ52's metric functions (apples-to-apples). RQ34 used concatenated text,
    so this is an approximate comparison. Returns None if cache unavailable."""
    if not RQ34_CACHE.exists():
        return None
    try:
        rq34 = json.loads(RQ34_CACHE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return None
    responses = rq34.get("responses", {})
    # map window_id -> (hallucinated, confidence); RQ34 used JSON verdicts
    scores: list[float] = []
    verdicts: list[bool] = []
    n_missing = 0
    for lbl in labels:
        wid = str(lbl["window_id"])
        r = responses.get(wid)
        if r is None:
            n_missing += 1
            scores.append(0.5)
            verdicts.append(False)
        else:
            h = bool(r.get("hallucinated", False))
            c = float(r.get("confidence", 0.5))
            verdicts.append(h)
            scores.append(hallucination_score(h, c))
    halluc_flags = [lbl["hallucinated"] for lbl in labels]
    mode_s_flags = [lbl["mode_s"] for lbl in labels]
    label_arr = [1 if h else 0 for h in halluc_flags]
    neg_scores = [s for s, h in zip(scores, halluc_flags) if not h]
    pos_scores = [s for s, h in zip(scores, halluc_flags) if h]
    cal = calibrate_threshold_at_specificity(neg_scores, pos_scores, TARGET_SPECIFICITY)
    threshold = cal["threshold"]
    overall = evaluate_at_threshold(scores, label_arr, threshold)
    ms = subgroup_sensitivity(scores, mode_s_flags, threshold)
    auc = roc_auc(scores, label_arr)
    fp_rate = false_positive_rate(scores, label_arr, threshold)
    # raw FP rate (no calibration): flag if verdict == True (score = confidence >= 0.5ish)
    raw_fp = sum(1 for v, h in zip(verdicts, halluc_flags) if v and not h)
    raw_fp_rate = raw_fp / sum(1 for h in halluc_flags if not h)
    raw_tp_ms = sum(1 for v, m in zip(verdicts, mode_s_flags) if v and m)
    return {
        "detector": "rq34_zero_shot (deepseek-r1:7b, cached)",
        "threshold": round(threshold, 6),
        "specificity": round(overall["specificity"], 6),
        "sensitivity_all_hallucinated": round(overall["sensitivity"], 6),
        "sensitivity_mode_s": round(ms["sensitivity"], 6),
        "auc": round(auc, 6),
        "fp_rate_at_90spec": round(fp_rate, 6),
        "raw_fp_rate": round(raw_fp_rate, 6),
        "raw_tp_mode_s": raw_tp_ms,
        "n_mode_s": ms["n"],
        "tp_all": overall["tp"], "fp": overall["fp"],
        "tn": overall["tn"], "fn_all": overall["fn"],
        "tp_mode_s": ms["tp"],
        "n_missing_responses": n_missing,
        "note": "RQ34 used concatenated all-speaker text; metrics recomputed with RQ52 functions.",
    }


def load_rq41_comparison() -> dict[str, Any] | None:
    """Load RQ41's published ensemble results for comparison. Returns None if
    the results file is unavailable."""
    if not RQ41_RESULTS.exists():
        return None
    try:
        rq41 = json.loads(RQ41_RESULTS.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return None
    ens = rq41.get("ensemble_at_90pct_spec", {})
    ens_raw = rq41.get("ensemble_raw_majority_vote", {})
    sc = rq41.get("singlecall_temp0_raw", {})
    return {
        "detector": "rq41_ensemble (5-call, T=0.0-0.8, cached)",
        "ensemble_fp_rate_raw": ens_raw.get("fp_rate"),
        "ensemble_sensitivity_mode_s_raw": ens_raw.get("sensitivity_mode_s"),
        "ensemble_specificity_90spec": ens.get("specificity"),
        "ensemble_sensitivity_mode_s_90spec": ens.get("sensitivity_mode_s"),
        "singlecall_fp_rate_raw": sc.get("fp_rate"),
        "singlecall_sensitivity_mode_s_raw": sc.get("sensitivity_mode_s"),
        "note": "RQ41 used concatenated all-speaker text; metrics from published results JSON.",
    }


# ----------------------------------------------------------------- main
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(SRC_JSON.read_text(encoding="utf-8"))
    windows = data["windows"]
    n = len(windows)

    # --- per-window labels + surface features + audit transcripts
    labels = [label_window(w) for w in windows]
    n_halluc = sum(1 for l in labels if l["hallucinated"])
    n_nonhalluc = n - n_halluc
    n_mode_s = sum(1 for l in labels if l["mode_s"])
    n_diverse = sum(1 for l in labels if l["diverse_hallucination"])
    mode_s_ids = [l["window_id"] for l in labels if l["mode_s"]]
    n_empty = sum(1 for l in labels if not l["audit_text"].strip())

    print(f"=== RQ52: CoT LLM critic (AISHELL-4, {n} tracks) ===", flush=True)
    print(f"Label: experimental/frontier + qualitative/demo  |  Source: {SRC_JSON.relative_to(PROJECT_ROOT)}", flush=True)
    print(f"Hallucinated: {n_halluc}  |  non-hallucinated: {n_nonhalluc}  "
          f"|  Mode S: {n_mode_s} ({mode_s_ids})  |  diverse: {n_diverse}", flush=True)
    print(f"Empty audit transcripts (short-circuited, no LLM call): {n_empty}", flush=True)
    print(f"Non-empty windows x 1 call = {n - n_empty} calls  |  T=0.0 (deterministic)", flush=True)
    print(flush=True)

    # --- run CoT critic (cached)
    print("[1/3] Running CoT critic (deepseek-r1:7b via ollama, T=0.0)...", flush=True)
    cot_responses = run_cot_critic(windows, labels)
    cot_scores = [
        hallucination_score(r["hallucinated"], r["confidence"]) for r in cot_responses
    ]
    cot_verdicts = [bool(r["hallucinated"]) for r in cot_responses]

    # --- compute CoT metrics
    print("[2/3] Computing metrics...", flush=True)
    halluc_flags = [l["hallucinated"] for l in labels]
    mode_s_flags = [l["mode_s"] for l in labels]
    label_arr = [1 if h else 0 for h in halluc_flags]

    neg_scores = [s for s, h in zip(cot_scores, halluc_flags) if not h]
    pos_scores = [s for s, h in zip(cot_scores, halluc_flags) if h]
    cal = calibrate_threshold_at_specificity(neg_scores, pos_scores, TARGET_SPECIFICITY)
    threshold = cal["threshold"]
    overall = evaluate_at_threshold(cot_scores, label_arr, threshold)
    ms = subgroup_sensitivity(cot_scores, mode_s_flags, threshold)
    div = subgroup_sensitivity(
        cot_scores, [l["diverse_hallucination"] for l in labels], threshold)
    auc = roc_auc(cot_scores, label_arr)
    fp_rate_90 = false_positive_rate(cot_scores, label_arr, threshold)

    # raw FP rate (no calibration): flag if verdict == True
    raw_fp = sum(1 for v, h in zip(cot_verdicts, halluc_flags) if v and not h)
    raw_fp_rate = raw_fp / n_nonhalluc if n_nonhalluc else 0.0
    raw_tp_ms = sum(1 for v, m in zip(cot_verdicts, mode_s_flags) if v and m)
    raw_tp_ah = sum(1 for v, h in zip(cot_verdicts, halluc_flags) if v and h)

    # bootstrap CIs
    scores_arr = np.array(cot_scores, dtype=float)
    ah_labels_arr = np.array(label_arr, dtype=float)
    ms_labels_arr = np.array([1 if m else 0 for m in mode_s_flags], dtype=float)
    neg_labels_arr = np.array([0.0 if h else 1.0 for h in halluc_flags], dtype=float)
    sens_ah_ci = bootstrap_ci(scores_arr, ah_labels_arr, threshold, "sensitivity", N_BOOT, SEED)
    sens_ms_ci = bootstrap_ci(scores_arr, ms_labels_arr, threshold, "sensitivity", N_BOOT, SEED)
    spec_ci = bootstrap_ci(scores_arr, neg_labels_arr, threshold, "specificity", N_BOOT, SEED)

    # --- RQ34 / RQ41 comparison
    print("[3/3] Loading RQ34/RQ41 comparison...", flush=True)
    rq34_cmp = load_rq34_comparison(labels)
    rq41_cmp = load_rq41_comparison()

    # --- per-window detail for Mode S
    ms_detail = []
    for lbl, r, s in zip(labels, cot_responses, cot_scores):
        if lbl["mode_s"]:
            ms_detail.append({
                "window_id": lbl["window_id"],
                "verdict": "YES" if r["hallucinated"] else "NO",
                "confidence": round(r["confidence"], 4),
                "score": round(s, 6),
                "verdict_raw": r.get("verdict_raw", ""),
                "audit_text_excerpt": (lbl["audit_text"][:120] + "...") if len(lbl["audit_text"]) > 120 else lbl["audit_text"],
            })

    # --- hypothesis verdicts
    h52a_supported = ms["sensitivity"] > 0.50 and overall["specificity"] >= TARGET_SPECIFICITY - 1e-9
    h52b_supported = raw_fp_rate < 0.50
    h52c_supported = auc > 0.60

    # pre-format comparison strings for clean f-string reason fields
    rq34_ms_str = f"{rq34_cmp['sensitivity_mode_s']:.0%}" if rq34_cmp else "N/A"
    rq34_fp_str = f"{rq34_cmp['raw_fp_rate']:.1%}" if rq34_cmp else "52.5%"
    rq34_auc_str = f"{rq34_cmp['auc']:.4f}" if rq34_cmp else "N/A"

    # --- per-window rows for CSV
    rows: list[dict[str, Any]] = []
    for w, lbl, r, s in zip(windows, labels, cot_responses, cot_scores):
        rows.append({
            "window_id": w["window_id"],
            "hallucinated": int(lbl["hallucinated"]),
            "mode_s": int(lbl["mode_s"]),
            "diverse_hallucination": int(lbl["diverse_hallucination"]),
            "lang_id_entropy": round(lbl["lang_id_entropy"], 6),
            "length_ratio": round(lbl["length_ratio"], 6),
            "cr": round(lbl["cr"], 6),
            "separated_cpwer": round(lbl["separated_cpwer"], 6),
            "cot_hallucinated": int(r["hallucinated"]),
            "cot_confidence": round(r["confidence"], 6),
            "cot_score": round(s, 6),
            "audit_text_len": len(lbl["audit_text"]),
        })

    use_llm = ollama_available(model=LLM_MODEL)
    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "llm_label": "qualitative/demo",
        "rq": "RQ52: Chain-of-thought LLM critic for Mode S",
        "source_data": str(SRC_JSON.relative_to(PROJECT_ROOT)),
        "source_label": "external/sanity-check",
        "method": (
            "Single deepseek-r1:7b call per window at T=0.0 with a 5-step chain-of-thought "
            "prompt (language -> repetition -> coherence -> insertion -> verdict) on the "
            "max-lang-id-entropy separated track's transcript (worst-case speaker). Empty "
            "transcripts short-circuited. Score = hallucination_score(verdict, confidence) "
            "in [0,1]. Calibrated at 90% specificity on 40 non-hallucinated tracks. AUC via "
            "rank-based Mann-Whitney U. Compared to RQ34 (zero-shot) and RQ41 (ensemble)."
        ),
        "meeting_id": data["meeting_id"],
        "n_windows": n,
        "n_hallucinated": n_halluc,
        "n_nonhallucinated": n_nonhalluc,
        "n_mode_s": n_mode_s,
        "n_diverse_hallucination": n_diverse,
        "mode_s_window_ids": mode_s_ids,
        "n_empty_audit_transcripts": n_empty,
        "hallucination_label": "always_separated_cpwer > 1.0 (37/40 split, RQ12)",
        "mode_s_definition": (
            "hallucinated AND lang_id_entropy < 0.409 AND length_ratio < 2.0 AND cr < 2.4"
        ),
        "llm_backend": {
            "model": LLM_MODEL,
            "available": bool(use_llm),
            "temperature": 0.0,
            "num_predict": LLM_NUM_PREDICT,
            "prompt_template": "5-step CoT (language, repetition, coherence, insertion, verdict)",
            "text_input": "max-lang-id-entropy separated speaker track (worst-case speaker)",
        },
        "cot_at_90pct_spec": {
            "threshold": round(threshold, 6),
            "specificity": round(overall["specificity"], 6),
            "specificity_ci_95": [round(spec_ci[0], 6), round(spec_ci[1], 6)],
            "sensitivity_all_hallucinated": round(overall["sensitivity"], 6),
            "sensitivity_all_hallucinated_ci_95": [round(sens_ah_ci[0], 6), round(sens_ah_ci[1], 6)],
            "sensitivity_mode_s": round(ms["sensitivity"], 6),
            "sensitivity_mode_s_ci_95": [round(sens_ms_ci[0], 6), round(sens_ms_ci[1], 6)],
            "sensitivity_diverse": round(div["sensitivity"], 6),
            "fp_rate": round(fp_rate_90, 6),
            "tp_all": overall["tp"], "fp": overall["fp"],
            "tn": overall["tn"], "fn_all": overall["fn"],
            "tp_mode_s": ms["tp"], "n_mode_s": ms["n"],
            "tp_diverse": div["tp"], "n_diverse": div["n"],
        },
        "cot_raw_verdict": {
            "operating_point": "flag if LLM verdict == YES (hallucinated)",
            "fp_rate": round(raw_fp_rate, 6),
            "fp": raw_fp,
            "specificity": round(1.0 - raw_fp_rate, 6),
            "sensitivity_mode_s": round(raw_tp_ms / n_mode_s, 6) if n_mode_s else 0.0,
            "sensitivity_all_hallucinated": round(raw_tp_ah / n_halluc, 6) if n_halluc else 0.0,
            "tp_mode_s": raw_tp_ms,
            "tp_all_hallucinated": raw_tp_ah,
        },
        "auc": round(auc, 6),
        "mode_s_detail": ms_detail,
        "rq34_comparison": rq34_cmp,
        "rq41_comparison": rq41_cmp,
        "hypothesis_verdicts": {
            "H52a": {
                "statement": "CoT Mode S sensitivity > 50% at 90% specificity (beats zero-shot's 0%)",
                "success_criterion": "sensitivity_mode_s > 50% at specificity >= 90%",
                "sensitivity_mode_s": round(ms["sensitivity"], 6),
                "specificity": round(overall["specificity"], 6),
                "ci_95_mode_s_sensitivity": [round(sens_ms_ci[0], 6), round(sens_ms_ci[1], 6)],
                "rq34_sensitivity_mode_s": rq34_cmp["sensitivity_mode_s"] if rq34_cmp else None,
                "supported": bool(h52a_supported),
                "reason": (
                    f"CoT Mode S sensitivity = {ms['sensitivity']:.0%} ({ms['tp']}/{ms['n']}) "
                    f"at {overall['specificity']:.1%} specificity. "
                    f"RQ34 zero-shot = {rq34_ms_str}. "
                    f"{'> 50% target met.' if h52a_supported else '<= 50% target NOT met.'}"
                ),
            },
            "H52b": {
                "statement": "CoT false-positive rate < 50% (beats zero-shot's 52.5%)",
                "success_criterion": "raw_fp_rate < 50%",
                "raw_fp_rate": round(raw_fp_rate, 6),
                "rq34_raw_fp_rate": rq34_cmp["raw_fp_rate"] if rq34_cmp else 0.525,
                "supported": bool(h52b_supported),
                "reason": (
                    f"CoT raw FP rate = {raw_fp_rate:.1%} ({raw_fp}/{n_nonhalluc}). "
                    f"RQ34 zero-shot = {rq34_fp_str}. "
                    f"{'< 50% target met.' if h52b_supported else '>= 50% target NOT met.'}"
                ),
            },
            "H52c": {
                "statement": "CoT AUC > 0.60 (beats random and zero-shot's near-chance)",
                "success_criterion": "auc > 0.60",
                "auc": round(auc, 6),
                "rq34_auc": rq34_cmp["auc"] if rq34_cmp else None,
                "supported": bool(h52c_supported),
                "reason": (
                    f"CoT AUC = {auc:.4f}. "
                    f"RQ34 AUC = {rq34_auc_str}. "
                    f"{'> 0.60 target met.' if h52c_supported else '<= 0.60 target NOT met.'}"
                ),
            },
        },
        "per_window": rows,
    }

    # --- write CSV
    csv_fields = [
        "window_id", "hallucinated", "mode_s", "diverse_hallucination",
        "lang_id_entropy", "length_ratio", "cr", "separated_cpwer",
        "cot_hallucinated", "cot_confidence", "cot_score", "audit_text_len",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        wr = csv.DictWriter(f, fieldnames=csv_fields)
        wr.writeheader()
        for r in rows:
            wr.writerow({k: r.get(k, "") for k in csv_fields})

    # --- write JSON
    OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    # --- console report
    print(flush=True)
    print(f"=== Results ===", flush=True)
    print(f"CoT raw verdict: FP={raw_fp_rate:.1%} ({raw_fp}/{n_nonhalluc}), "
          f"sens_MS={raw_tp_ms}/{n_mode_s}, sens_AH={raw_tp_ah}/{n_halluc}", flush=True)
    print(f"CoT AUC = {auc:.4f}", flush=True)
    print(flush=True)
    print(f"At 90% specificity (threshold={threshold:.4f}, spec={overall['specificity']:.1%}):", flush=True)
    print(f"  sens_MS={ms['sensitivity']:.0%} ({ms['tp']}/{ms['n']})  "
          f"sens_AH={overall['sensitivity']:.1%}  FP_rate={fp_rate_90:.1%}", flush=True)
    print(flush=True)
    if rq34_cmp:
        print(f"RQ34 zero-shot: FP={rq34_cmp['raw_fp_rate']:.1%}, "
              f"sens_MS={rq34_cmp['sensitivity_mode_s']:.0%}, "
              f"AUC={rq34_cmp['auc']:.4f}", flush=True)
    if rq41_cmp:
        print(f"RQ41 ensemble:  FP={rq41_cmp['ensemble_fp_rate_raw']:.1%}, "
              f"sens_MS={rq41_cmp['ensemble_sensitivity_mode_s_raw']:.0%}", flush=True)
    print(flush=True)
    print(f"Mode S detail:", flush=True)
    for d in ms_detail:
        print(f"  win {d['window_id']}: verdict={d['verdict']} conf={d['confidence']:.2f} "
              f"score={d['score']:.3f}", flush=True)
    print(flush=True)
    print(f"Hypothesis verdicts:", flush=True)
    print(f"  H52a (sens_MS > 50% at 90% spec): {'SUPPORTED' if h52a_supported else 'NOT SUPPORTED'} "
          f"(sens_MS={ms['sensitivity']:.0%}, spec={overall['specificity']:.1%})", flush=True)
    print(f"  H52b (FP < 50%): {'SUPPORTED' if h52b_supported else 'NOT SUPPORTED'} "
          f"(FP={raw_fp_rate:.1%})", flush=True)
    print(f"  H52c (AUC > 0.60): {'SUPPORTED' if h52c_supported else 'NOT SUPPORTED'} "
          f"(AUC={auc:.4f})", flush=True)
    print(flush=True)
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}", flush=True)
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}", flush=True)
    print(f"Wrote: {CACHE_JSON.relative_to(PROJECT_ROOT)}", flush=True)


if __name__ == "__main__":
    main()
