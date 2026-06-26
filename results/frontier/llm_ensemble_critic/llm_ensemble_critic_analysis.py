"""RQ41: Multi-call LLM ensemble critic for Mode S — analysis driver.

Runs a self-consistency ensemble of N=5 deepseek-r1:7b calls (temperatures 0.0-0.8)
on each of the 77 AISHELL-4 windows' separated transcripts, votes on whether each is
a hallucination, and calibrates at 90% specificity on the 40 non-hallucinated tracks.
Compares the ensemble to (a) the single-call baseline (the temperature=0.0 call, a
proxy for RQ34's single deepseek-r1:7b call) and (b) the n-gram KL divergence
baseline (KL between separated and mixed character trigram distributions).

Hypotheses
----------
- H41a: Ensemble FP rate < 30% (vs single-call 52.5%) at raw majority vote.
- H41b: Ensemble Mode S sensitivity > 50% at 90% specificity.
- H41c: Ensemble catches window 22 (the coherent Mode S track single-call misses).

Method
------
- 5 calls per window at temperatures [0.0, 0.2, 0.4, 0.6, 0.8]. Majority vote on the
  ``hallucinated`` boolean; confidence = mean of per-call confidences.
- Cache by (transcript_hash, temperature); cache saved every 5 calls (resumable).
- Empty separated transcripts (silence windows, all non-hallucinated) are
  short-circuited (no LLM call) to avoid wasting calls and ambiguous empty-text
  judgments.
- Calibrate at 90% specificity on the 40 non-hallucinated tracks (one-sided: flag if
  yes-vote-fraction >= threshold). Bootstrap 95% CIs (10,000 resamples, seed=42,
  fixed full-sample threshold).
- The single-call baseline uses the temperature=0.0 call's verdict as the score
  (1.0 if hallucinated, 0.0 if not); calibrated the same way.
- The n-gram KL baseline uses KL(sep_trigram || mix_trigram); calibrated two-sidedly
  (both orientations) at 90% specificity, matching RQ19's method.

Label: experimental/frontier + qualitative/demo (LLM outputs). Reference issue #954.
Source data: results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json
(external/sanity-check, read-only — NOT modified).

Reproduce: python3 results/frontier/llm_ensemble_critic/llm_ensemble_critic_analysis.py
"""
from __future__ import annotations

import csv
import json
import math
import sys
import threading
import time
import unicodedata
import zlib
from pathlib import Path
from typing import Any

import numpy as np

# Make the repo src importable when run as a script
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from src.llm_ensemble_critic import (  # noqa: E402
    CATASTROPHIC_CPWER,
    CR_THRESHOLD,
    ENSEMBLE_TEMPERATURES,
    EPS,
    LANG_ID_ENTROPY_THRESHOLD,
    LENGTH_RATIO_THRESHOLD,
    N_BOOT,
    SEED,
    TARGET_SPECIFICITY,
    bootstrap_ci,
    cache_key,
    calibrate_threshold,
    ceiling_analysis,
    ensemble_judge,
    flag_at,
    load_cache,
    ngram_kl,
    ollama_llm,
    save_cache,
)

SRC_JSON = (
    PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "llm_ensemble_critic"
OUT_CSV = OUT_DIR / "llm_ensemble_results.csv"
OUT_JSON = OUT_DIR / "llm_ensemble_results.json"
CACHE_PATH = OUT_DIR / "llm_ensemble_cache.json"

CJK_SCRIPTS = {"Han", "Hiragana", "Katakana", "Hangul"}
MAX_WORKERS = 4  # ollama --parallel 4
NGRAM_N = 3


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


def max_across_speakers(window: dict[str, Any], fn) -> float:
    vals = [
        fn(str(t))
        for t in window.get("separated_text_per_speaker", {}).values()
        if t is not None and str(t).strip()
    ]
    return max(vals) if vals else 0.0


def length_ratio(window: dict[str, Any]) -> float:
    sep = float(window.get("separated_total_length", 0) or 0)
    mix = float(window.get("mixed_text_length", 0) or 0)
    return sep / max(1.0, mix)


def separated_concat(window: dict[str, Any]) -> str:
    parts = [
        str(t).strip()
        for t in window.get("separated_text_per_speaker", {}).values()
        if t is not None and str(t).strip()
    ]
    return "".join(parts)


# ----------------------------------------------------------------- main analysis
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(SRC_JSON.read_text(encoding="utf-8"))
    windows = data["windows"]
    n = len(windows)

    # --- build per-window rows (labels + surface features + transcripts)
    base_rows: list[dict[str, Any]] = []
    for w in windows:
        sep_cpwer = float(w["always_separated_cpwer"])
        halluc = sep_cpwer > CATASTROPHIC_CPWER
        ent = max_across_speakers(w, language_id_entropy)
        mcr = max_across_speakers(w, compression_ratio)
        lr = length_ratio(w)
        mode_s = (halluc and ent < LANG_ID_ENTROPY_THRESHOLD
                  and lr < LENGTH_RATIO_THRESHOLD and mcr < CR_THRESHOLD)
        sep_text = separated_concat(w)
        mix_text = str(w.get("mixed_text", "") or "")
        base_rows.append({
            "window_id": w["window_id"],
            "always_separated_cpwer": round(sep_cpwer, 6),
            "hallucinated": bool(halluc),
            "mode_s": bool(mode_s),
            "lang_id_entropy": round(ent, 6),
            "length_ratio": round(lr, 6),
            "cr": round(mcr, 6),
            "num_speakers": w["num_speakers"],
            "sep_text": sep_text,
            "mix_text": mix_text,
            "sep_len": len(sep_text),
        })

    n_halluc = sum(1 for r in base_rows if r["hallucinated"])
    n_nonhalluc = n - n_halluc
    n_mode_s = sum(1 for r in base_rows if r["mode_s"])
    mode_s_ids = [r["window_id"] for r in base_rows if r["mode_s"]]
    n_empty = sum(1 for r in base_rows if not r["sep_text"].strip())

    print(f"=== RQ41: LLM ensemble critic (AISHELL-4, {n} tracks) ===", flush=True)
    print(f"Label: experimental/frontier + qualitative/demo  |  Source: {SRC_JSON.relative_to(PROJECT_ROOT)}", flush=True)
    print(f"Hallucinated: {n_halluc}  |  non-hallucinated: {n_nonhalluc}  |  Mode S: {n_mode_s} ({mode_s_ids})", flush=True)
    print(f"Empty sep transcripts (short-circuited, no LLM call): {n_empty}", flush=True)
    print(f"Non-empty windows x 5 calls = {(n - n_empty) * 5} calls  |  temps={ENSEMBLE_TEMPERATURES}", flush=True)
    print(f"max_workers={MAX_WORKERS} (ollama --parallel 4)", flush=True)
    print(flush=True)

    # --- load resumable cache
    cache = load_cache(CACHE_PATH)
    print(f"[cache] loaded {len(cache)} cached responses from {CACHE_PATH.name}", flush=True)
    cache_lock = threading.Lock()

    # --- run the ensemble on every window
    llm = ollama_llm(model="deepseek-r1:7b", num_predict=1000)
    t_start = time.time()
    total_new = 0
    for i, r in enumerate(base_rows):
        agg = ensemble_judge(
            r["sep_text"], llm,
            temperatures=ENSEMBLE_TEMPERATURES,
            cache=cache, cache_lock=cache_lock, cache_path=CACHE_PATH,
            save_every=5, max_workers=MAX_WORKERS,
        )
        r["ensemble"] = agg
        total_new += agg.get("n_new_calls", 0)
        elapsed = time.time() - t_start
        done = i + 1
        if agg.get("n_new_calls", 0) > 0:
            rate = agg["n_new_calls"] / max(1e-6, elapsed) if total_new > 0 else 0.0
            eta = (n - done) * (elapsed / max(1, done))
            print(
                f"[ensemble] {done}/{n} win={r['window_id']} "
                f"yes={agg['yes_count']}/5 maj={'Y' if agg['hallucinated_majority'] else 'N'} "
                f"conf={agg['mean_confidence']:.2f} "
                f"halluc={r['hallucinated']} ms={r['mode_s']} "
                f"new={agg['n_new_calls']} hits={agg['n_cache_hits']} "
                f"elapsed={elapsed:.0f}s eta~{eta:.0f}s",
                flush=True,
            )
        else:
            print(
                f"[ensemble] {done}/{n} win={r['window_id']} (all cached) "
                f"yes={agg['yes_count']}/5 maj={'Y' if agg['hallucinated_majority'] else 'N'}",
                flush=True,
            )

    # final cache save
    with cache_lock:
        save_cache(CACHE_PATH, dict(cache))
    print(f"[cache] saved {len(cache)} responses to {CACHE_PATH.name}", flush=True)
    print(f"[ensemble] done in {time.time() - t_start:.0f}s, {total_new} new calls", flush=True)
    print(flush=True)

    # --- compute scores for the three detectors
    for r in base_rows:
        ens = r["ensemble"]
        # Ensemble score = yes-vote fraction (0.0-1.0); majority vote = threshold 0.6 (>=3/5)
        r["ensemble_score"] = ens["yes_vote_fraction"]
        r["ensemble_majority"] = ens["hallucinated_majority"]
        r["ensemble_mean_confidence"] = ens["mean_confidence"]
        r["ensemble_yes_count"] = ens["yes_count"]
        # Single-call baseline = the temperature=0.0 call's verdict (1.0 yes / 0.0 no)
        t0_call = next((c for c in ens["per_call"] if abs(c["temperature"] - 0.0) < 1e-9), None)
        if t0_call is not None:
            h0 = t0_call.get("hallucinated")
            r["singlecall_score"] = 1.0 if h0 is True else (0.0 if h0 is False else 0.5)
            r["singlecall_hallucinated"] = bool(h0) if h0 is not None else False
            r["singlecall_confidence"] = t0_call.get("confidence")
        else:
            r["singlecall_score"] = 0.0
            r["singlecall_hallucinated"] = False
            r["singlecall_confidence"] = None
        # n-gram KL baseline (sep vs mix)
        r["ngram_kl"] = round(ngram_kl(r["sep_text"], r["mix_text"], n=NGRAM_N), 6)

    # --- calibrate each detector at 90% specificity on the 40 non-hallucinated tracks
    neg_idx = [i for i, r in enumerate(base_rows) if not r["hallucinated"]]
    pos_ms_idx = [i for i, r in enumerate(base_rows) if r["mode_s"]]
    pos_ah_idx = [i for i, r in enumerate(base_rows) if r["hallucinated"]]

    def scores_at(key: str, idxs: list[int]) -> list[float]:
        return [float(base_rows[i][key]) for i in idxs]

    # Ensemble (one-sided high: flag if yes-vote-fraction >= threshold)
    ens_neg = scores_at("ensemble_score", neg_idx)
    ens_ms = scores_at("ensemble_score", pos_ms_idx)
    ens_ah = scores_at("ensemble_score", pos_ah_idx)
    ens_op = calibrate_threshold(ens_neg, ens_ms, ens_ah, TARGET_SPECIFICITY)
    ens_ceil = ceiling_analysis(ens_neg, ens_ms, [0.50, 0.70, 0.80, 0.90, 0.95])

    # Single-call (one-sided high: flag if score >= threshold; score in {0,1})
    sc_neg = scores_at("singlecall_score", neg_idx)
    sc_ms = scores_at("singlecall_score", pos_ms_idx)
    sc_ah = scores_at("singlecall_score", pos_ah_idx)
    sc_op = calibrate_threshold(sc_neg, sc_ms, sc_ah, TARGET_SPECIFICITY)
    sc_ceil = ceiling_analysis(sc_neg, sc_ms, [0.50, 0.70, 0.80, 0.90, 0.95])

    # n-gram KL (two-sided: try both orientations at 90% spec)
    kl_neg = scores_at("ngram_kl", neg_idx)
    kl_ms = scores_at("ngram_kl", pos_ms_idx)
    kl_ah = scores_at("ngram_kl", pos_ah_idx)
    # two-sided calibration for KL
    kl_op = _calibrate_two_sided(kl_neg, kl_ms, kl_ah, TARGET_SPECIFICITY)
    kl_ceil = _ceiling_two_sided(kl_neg, kl_ms, [0.50, 0.70, 0.80, 0.90, 0.95])

    # --- raw majority-vote operating point (H41a)
    # majority vote = flag if yes_count >= 3 (yes_vote_fraction >= 0.6)
    ens_maj_fp = sum(1 for i in neg_idx if base_rows[i]["ensemble_majority"])
    ens_maj_fp_rate = ens_maj_fp / n_nonhalluc if n_nonhalluc else 0.0
    ens_maj_tp_ms = sum(1 for i in pos_ms_idx if base_rows[i]["ensemble_majority"])
    ens_maj_tp_ah = sum(1 for i in pos_ah_idx if base_rows[i]["ensemble_majority"])
    # single-call raw (temp 0.0) FP rate
    sc_raw_fp = sum(1 for i in neg_idx if base_rows[i]["singlecall_hallucinated"])
    sc_raw_fp_rate = sc_raw_fp / n_nonhalluc if n_nonhalluc else 0.0
    sc_raw_tp_ms = sum(1 for i in pos_ms_idx if base_rows[i]["singlecall_hallucinated"])
    sc_raw_tp_ah = sum(1 for i in pos_ah_idx if base_rows[i]["singlecall_hallucinated"])

    # --- per-window flags at the 90%-specificity operating point
    for r in base_rows:
        r["ensemble_flag_90spec"] = bool(flag_at(r["ensemble_score"], ens_op["threshold"]))
        r["singlecall_flag_90spec"] = bool(flag_at(r["singlecall_score"], sc_op["threshold"]))
        r["ngram_kl_flag_90spec"] = bool(_flag_two_sided(r["ngram_kl"], kl_op["direction"], kl_op["threshold"]))

    # --- window 22 specifically (H41c)
    win22 = next((r for r in base_rows if r["window_id"] == 22), None)
    win30 = next((r for r in base_rows if r["window_id"] == 30), None)
    win22_ens_calls = [c.get("hallucinated") for c in win22["ensemble"]["per_call"]] if win22 else []
    win30_ens_calls = [c.get("hallucinated") for c in win30["ensemble"]["per_call"]] if win30 else []

    # --- bootstrap CIs at the calibrated operating points (fixed full-sample threshold)
    ens_scores_arr = np.array([r["ensemble_score"] for r in base_rows], dtype=float)
    sc_scores_arr = np.array([r["singlecall_score"] for r in base_rows], dtype=float)
    kl_scores_arr = np.array([r["ngram_kl"] for r in base_rows], dtype=float)
    ms_labels = np.array([1.0 if r["mode_s"] else 0.0 for r in base_rows], dtype=float)
    ah_labels = np.array([1.0 if r["hallucinated"] else 0.0 for r in base_rows], dtype=float)
    neg_labels = np.array([0.0 if r["hallucinated"] else 1.0 for r in base_rows], dtype=float)

    # ensemble CIs
    ens_sens_ms_ci = bootstrap_ci(ens_scores_arr, ms_labels, ens_op["threshold"], "sensitivity", N_BOOT, SEED)
    ens_sens_ah_ci = bootstrap_ci(ens_scores_arr, ah_labels, ens_op["threshold"], "sensitivity", N_BOOT, SEED)
    ens_spec_ci = bootstrap_ci(ens_scores_arr, neg_labels, ens_op["threshold"], "specificity", N_BOOT, SEED)
    # single-call CIs
    sc_sens_ms_ci = bootstrap_ci(sc_scores_arr, ms_labels, sc_op["threshold"], "sensitivity", N_BOOT, SEED)
    sc_sens_ah_ci = bootstrap_ci(sc_scores_arr, ah_labels, sc_op["threshold"], "sensitivity", N_BOOT, SEED)
    sc_spec_ci = bootstrap_ci(sc_scores_arr, neg_labels, sc_op["threshold"], "specificity", N_BOOT, SEED)
    # n-gram KL CIs (two-sided)
    kl_sens_ms_ci = _bootstrap_two_sided(kl_scores_arr, ms_labels, kl_op["direction"], kl_op["threshold"], "sensitivity")
    kl_sens_ah_ci = _bootstrap_two_sided(kl_scores_arr, ah_labels, kl_op["direction"], kl_op["threshold"], "sensitivity")
    kl_spec_ci = _bootstrap_two_sided(kl_scores_arr, neg_labels, kl_op["direction"], kl_op["threshold"], "specificity")

    # --- hypothesis verdicts
    h41a_supported = ens_maj_fp_rate < 0.30
    h41b_supported = ens_op["sensitivity_mode_s"] > 0.50 and ens_op["specificity"] >= 0.90
    h41c_supported = bool(win22 and win22["ensemble_majority"])  # majority flags window 22

    # --- assemble summary
    summary: dict[str, Any] = {
        "label": "experimental/frontier + qualitative/demo",
        "rq": "RQ41: Multi-call LLM ensemble critic for Mode S",
        "closes_issue": 954,
        "source_data": str(SRC_JSON.relative_to(PROJECT_ROOT)),
        "source_label": "external/sanity-check",
        "method": (
            "self-consistency ensemble of N=5 deepseek-r1:7b calls (temperatures 0.0-0.8) on the "
            "separated transcript (reference-free; LLM never sees the reference or mixed decode). "
            "Majority vote on the hallucinated boolean; confidence = mean of per-call confidences. "
            "Calibrated at 90% specificity on the 40 non-hallucinated tracks (one-sided: flag if "
            "yes-vote-fraction >= threshold). Bootstrap 95% CIs (10,000 resamples, seed=42, fixed "
            "full-sample threshold). Compared to single-call (temperature=0.0) and n-gram KL "
            "(KL between separated and mixed character trigram distributions, two-sided calibration)."
        ),
        "meeting_id": data["meeting_id"],
        "n_windows": n,
        "n_hallucinated_tracks": n_halluc,
        "n_nonhallucinated_tracks": n_nonhalluc,
        "n_mode_s_tracks": n_mode_s,
        "mode_s_window_ids": mode_s_ids,
        "n_empty_sep_transcripts": n_empty,
        "n_llm_calls_total": (n - n_empty) * 5,
        "n_llm_calls_new": total_new,
        "n_llm_calls_cached": (n - n_empty) * 5 - total_new,
        "ensemble_config": {
            "n_calls_per_window": 5,
            "temperatures": ENSEMBLE_TEMPERATURES,
            "majority_vote_threshold": "yes_count >= 3 (yes_vote_fraction >= 0.6)",
            "cache_key": "(sha1(transcript)[:16], temperature)",
            "max_workers": MAX_WORKERS,
        },
        "mode_s_definition": (
            "hallucinated (cpWER>1.0) AND lang_id_entropy<0.409 AND length_ratio<2.0 AND cr<2.4 "
            "(escapes every surface detector; the RQ16 corrected-router residual)"
        ),
        "thresholds": {
            "lang_id_entropy": LANG_ID_ENTROPY_THRESHOLD,
            "length_ratio": LENGTH_RATIO_THRESHOLD,
            "cr": CR_THRESHOLD,
            "target_specificity": TARGET_SPECIFICITY,
        },
        "ensemble_at_90pct_spec": {
            **ens_op,
            "sensitivity_mode_s_ci_95": [round(ens_sens_ms_ci[0], 6), round(ens_sens_ms_ci[1], 6)],
            "sensitivity_all_hallucinated_ci_95": [round(ens_sens_ah_ci[0], 6), round(ens_sens_ah_ci[1], 6)],
            "specificity_ci_95": [round(ens_spec_ci[0], 6), round(ens_spec_ci[1], 6)],
            "ceiling_analysis": ens_ceil,
        },
        "ensemble_raw_majority_vote": {
            "operating_point": "flag if yes_count >= 3 (yes_vote_fraction >= 0.6)",
            "fp_rate": round(ens_maj_fp_rate, 6),
            "fp": ens_maj_fp,
            "specificity": round(1.0 - ens_maj_fp_rate, 6),
            "sensitivity_mode_s": round(ens_maj_tp_ms / n_mode_s, 6) if n_mode_s else 0.0,
            "sensitivity_all_hallucinated": round(ens_maj_tp_ah / n_halluc, 6) if n_halluc else 0.0,
            "tp_mode_s": ens_maj_tp_ms,
            "tp_all_hallucinated": ens_maj_tp_ah,
        },
        "singlecall_temp0_at_90pct_spec": {
            **sc_op,
            "sensitivity_mode_s_ci_95": [round(sc_sens_ms_ci[0], 6), round(sc_sens_ms_ci[1], 6)],
            "sensitivity_all_hallucinated_ci_95": [round(sc_sens_ah_ci[0], 6), round(sc_sens_ah_ci[1], 6)],
            "specificity_ci_95": [round(sc_spec_ci[0], 6), round(sc_spec_ci[1], 6)],
            "ceiling_analysis": sc_ceil,
        },
        "singlecall_temp0_raw": {
            "operating_point": "flag if temperature=0.0 call says hallucinated (score=1.0)",
            "fp_rate": round(sc_raw_fp_rate, 6),
            "fp": sc_raw_fp,
            "specificity": round(1.0 - sc_raw_fp_rate, 6),
            "sensitivity_mode_s": round(sc_raw_tp_ms / n_mode_s, 6) if n_mode_s else 0.0,
            "sensitivity_all_hallucinated": round(sc_raw_tp_ah / n_halluc, 6) if n_halluc else 0.0,
            "tp_mode_s": sc_raw_tp_ms,
            "tp_all_hallucinated": sc_raw_tp_ah,
        },
        "ngram_kl_at_90pct_spec": {
            **kl_op,
            "sensitivity_mode_s_ci_95": [round(kl_sens_ms_ci[0], 6), round(kl_sens_ms_ci[1], 6)],
            "sensitivity_all_hallucinated_ci_95": [round(kl_sens_ah_ci[0], 6), round(kl_sens_ah_ci[1], 6)],
            "specificity_ci_95": [round(kl_spec_ci[0], 6), round(kl_spec_ci[1], 6)],
            "ceiling_analysis": kl_ceil,
        },
        "window_22_detail": {
            "window_id": 22,
            "mode_s": True,
            "ensemble_majority_hallucinated": bool(win22["ensemble_majority"]) if win22 else None,
            "ensemble_yes_count": win22["ensemble_yes_count"] if win22 else None,
            "ensemble_mean_confidence": win22["ensemble_mean_confidence"] if win22 else None,
            "per_call_hallucinated": win22_ens_calls,
            "singlecall_hallucinated": bool(win22["singlecall_hallucinated"]) if win22 else None,
            "singlecall_confidence": win22["singlecall_confidence"] if win22 else None,
            "ngram_kl": win22["ngram_kl"] if win22 else None,
            "sep_text_excerpt": (win22["sep_text"][:100] + "...") if win22 and len(win22["sep_text"]) > 100 else (win22["sep_text"] if win22 else ""),
            "note": "the coherent Mode S track (near-duplicate of mixed) that the single-call misses",
        },
        "window_30_detail": {
            "window_id": 30,
            "mode_s": True,
            "ensemble_majority_hallucinated": bool(win30["ensemble_majority"]) if win30 else None,
            "ensemble_yes_count": win30["ensemble_yes_count"] if win30 else None,
            "ensemble_mean_confidence": win30["ensemble_mean_confidence"] if win30 else None,
            "per_call_hallucinated": win30_ens_calls,
            "singlecall_hallucinated": bool(win30["singlecall_hallucinated"]) if win30 else None,
            "singlecall_confidence": win30["singlecall_confidence"] if win30 else None,
            "ngram_kl": win30["ngram_kl"] if win30 else None,
            "sep_text_excerpt": (win30["sep_text"][:100] + "...") if win30 and len(win30["sep_text"]) > 100 else (win30["sep_text"] if win30 else ""),
            "note": "the repetitive Mode S track that the single-call catches",
        },
        "hypothesis_verdicts": {
            "H41a": {
                "statement": "Ensemble FP rate < 30% (vs single-call 52.5%) at raw majority vote",
                "ensemble_fp_rate": round(ens_maj_fp_rate, 6),
                "singlecall_fp_rate": round(sc_raw_fp_rate, 6),
                "ensemble_specificity": round(1.0 - ens_maj_fp_rate, 6),
                "singlecall_specificity": round(1.0 - sc_raw_fp_rate, 6),
                "supported": bool(h41a_supported),
                "reason": (
                    f"Ensemble raw majority vote FP rate = {ens_maj_fp_rate:.1%} ({ens_maj_fp}/{n_nonhalluc}) "
                    f"vs single-call {sc_raw_fp_rate:.1%} ({sc_raw_fp}/{n_nonhalluc}). "
                    f"{'FP < 30% target met.' if h41a_supported else 'FP >= 30% target NOT met.'}"
                ),
            },
            "H41b": {
                "statement": "Ensemble Mode S sensitivity > 50% at 90% specificity",
                "ensemble_sensitivity_mode_s": ens_op["sensitivity_mode_s"],
                "ensemble_specificity": ens_op["specificity"],
                "ensemble_threshold": ens_op["threshold"],
                "bootstrap_ci_95_mode_s_sensitivity": [round(ens_sens_ms_ci[0], 6), round(ens_sens_ms_ci[1], 6)],
                "supported": bool(h41b_supported),
                "reason": (
                    f"At >= 90% specificity (threshold={ens_op['threshold']:.2f}, spec={ens_op['specificity']:.1%}), "
                    f"ensemble Mode S sensitivity = {ens_op['sensitivity_mode_s']:.0%} "
                    f"({ens_op['tp_mode_s']}/{n_mode_s}). "
                    f"{'sens > 50% target met.' if h41b_supported else 'sens <= 50% target NOT met.'}"
                ),
            },
            "H41c": {
                "statement": "Ensemble catches window 22 (the coherent Mode S track single-call misses)",
                "window22_ensemble_majority": bool(win22["ensemble_majority"]) if win22 else False,
                "window22_yes_count": win22["ensemble_yes_count"] if win22 else 0,
                "window22_per_call": win22_ens_calls,
                "window22_singlecall": bool(win22["singlecall_hallucinated"]) if win22 else False,
                "supported": bool(h41c_supported),
                "reason": (
                    f"Window 22 ensemble majority = {'HALLUCINATED' if h41c_supported else 'not hallucinated'} "
                    f"({win22['ensemble_yes_count'] if win22 else 0}/5 yes votes, "
                    f"per-call: {win22_ens_calls}). Single-call temp=0.0 = "
                    f"{'HALLUCINATED' if (win22 and win22['singlecall_hallucinated']) else 'not hallucinated'}."
                ),
            },
        },
    }

    # --- write CSV (per-window)
    csv_fields = [
        "window_id", "hallucinated", "mode_s",
        "ensemble_score", "ensemble_majority", "ensemble_yes_count", "ensemble_mean_confidence",
        "ensemble_flag_90spec",
        "singlecall_score", "singlecall_hallucinated", "singlecall_confidence",
        "singlecall_flag_90spec",
        "ngram_kl", "ngram_kl_flag_90spec",
        "lang_id_entropy", "length_ratio", "cr", "num_speakers", "sep_len",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        wr = csv.DictWriter(f, fieldnames=csv_fields)
        wr.writeheader()
        for r in base_rows:
            wr.writerow({k: r.get(k, "") for k in csv_fields})

    # --- write JSON (summary + per-window, without the long per-call responses)
    summary["per_window"] = [
        {k: v for k, v in r.items()
         if k not in ("sep_text", "mix_text", "ensemble")}
        | {"sep_text_excerpt": (r["sep_text"][:80] + "...") if len(r["sep_text"]) > 80 else r["sep_text"]}
        for r in base_rows
    ]
    OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # --- console report
    print(f"=== Results ===", flush=True)
    print(f"Ensemble raw majority vote: FP={ens_maj_fp_rate:.1%} ({ens_maj_fp}/{n_nonhalluc}), "
          f"sens_MS={ens_maj_tp_ms}/{n_mode_s}, sens_AH={ens_maj_tp_ah}/{n_halluc}", flush=True)
    print(f"Single-call raw (t=0.0):    FP={sc_raw_fp_rate:.1%} ({sc_raw_fp}/{n_nonhalluc}), "
          f"sens_MS={sc_raw_tp_ms}/{n_mode_s}, sens_AH={sc_raw_tp_ah}/{n_halluc}", flush=True)
    print(flush=True)
    print(f"At 90% specificity:", flush=True)
    print(f"  Ensemble:   thresh={ens_op['threshold']:.2f} spec={ens_op['specificity']:.1%} "
          f"sens_MS={ens_op['sensitivity_mode_s']:.0%} sens_AH={ens_op['sensitivity_all_hallucinated']:.1%}", flush=True)
    print(f"  Single-call: thresh={sc_op['threshold']:.2f} spec={sc_op['specificity']:.1%} "
          f"sens_MS={sc_op['sensitivity_mode_s']:.0%} sens_AH={sc_op['sensitivity_all_hallucinated']:.1%}", flush=True)
    print(f"  n-gram KL:  dir={kl_op['direction']} thresh={kl_op['threshold']:.4f} spec={kl_op['specificity']:.1%} "
          f"sens_MS={kl_op['sensitivity_mode_s']:.0%} sens_AH={kl_op['sensitivity_all_hallucinated']:.1%}", flush=True)
    print(flush=True)
    print(f"Window 22 (coherent Mode S): ensemble={'HALL' if h41c_supported else 'OK'} "
          f"({win22['ensemble_yes_count'] if win22 else 0}/5 yes), singlecall={'HALL' if (win22 and win22['singlecall_hallucinated']) else 'OK'}", flush=True)
    print(f"Window 30 (repetitive Mode S): ensemble={'HALL' if (win30 and win30['ensemble_majority']) else 'OK'} "
          f"({win30['ensemble_yes_count'] if win30 else 0}/5 yes), singlecall={'HALL' if (win30 and win30['singlecall_hallucinated']) else 'OK'}", flush=True)
    print(flush=True)
    print(f"Hypothesis verdicts:", flush=True)
    print(f"  H41a (ensemble FP < 30% at majority vote): {'SUPPORTED' if h41a_supported else 'NOT SUPPORTED'} "
          f"(FP={ens_maj_fp_rate:.1%} vs single {sc_raw_fp_rate:.1%})", flush=True)
    print(f"  H41b (ensemble sens_MS > 50% at 90% spec): {'SUPPORTED' if h41b_supported else 'NOT SUPPORTED'} "
          f"(sens_MS={ens_op['sensitivity_mode_s']:.0%}, spec={ens_op['specificity']:.1%})", flush=True)
    print(f"  H41c (ensemble catches window 22): {'SUPPORTED' if h41c_supported else 'NOT SUPPORTED'} "
          f"(majority={'yes' if h41c_supported else 'no'}, {win22['ensemble_yes_count'] if win22 else 0}/5)", flush=True)
    print(flush=True)
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}", flush=True)
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}", flush=True)
    print(f"Wrote: {CACHE_PATH.relative_to(PROJECT_ROOT)} ({len(cache)} entries)", flush=True)


# ----------------------------------------------------------------- two-sided helpers
# (for the n-gram KL baseline, which is non-directional: high KL = diverse hallucination,
#  low KL = Mode S near-duplicate. Both orientations are tried, matching RQ19.)
def _calibrate_two_sided(
    neg_scores: list[float],
    pos_scores_mode_s: list[float],
    pos_scores_all_halluc: list[float],
    target_spec: float = TARGET_SPECIFICITY,
) -> dict[str, Any]:
    n_neg = len(neg_scores)
    n_ms = len(pos_scores_mode_s)
    n_ah = len(pos_scores_all_halluc)
    candidates = sorted(set(neg_scores) | set(pos_scores_mode_s) | set(pos_scores_all_halluc))
    best: dict[str, Any] | None = None
    for direction in ("high", "low"):
        for t in candidates:
            if direction == "high":
                fp = sum(1 for s in neg_scores if s >= t - EPS)
                tp_ms = sum(1 for s in pos_scores_mode_s if s >= t - EPS)
                tp_ah = sum(1 for s in pos_scores_all_halluc if s >= t - EPS)
            else:
                fp = sum(1 for s in neg_scores if s <= t + EPS)
                tp_ms = sum(1 for s in pos_scores_mode_s if s <= t + EPS)
                tp_ah = sum(1 for s in pos_scores_all_halluc if s <= t + EPS)
            spec = 1.0 - (fp / n_neg) if n_neg else 1.0
            sens_ms = (tp_ms / n_ms) if n_ms else 0.0
            sens_ah = (tp_ah / n_ah) if n_ah else 0.0
            if spec < target_spec - EPS:
                continue
            cand = {
                "direction": direction, "threshold": float(t),
                "specificity": float(spec),
                "sensitivity_mode_s": float(sens_ms),
                "sensitivity_all_hallucinated": float(sens_ah),
                "tp_mode_s": int(tp_ms), "fp": int(fp), "tn": int(n_neg - fp),
                "fn_mode_s": int(n_ms - tp_ms),
                "tp_all_hallucinated": int(tp_ah), "fn_all_hallucinated": int(n_ah - tp_ah),
            }
            if best is None:
                best = cand
                continue
            better = (
                sens_ms > best["sensitivity_mode_s"] + EPS
                or (abs(sens_ms - best["sensitivity_mode_s"]) <= EPS
                    and sens_ah > best["sensitivity_all_hallucinated"] + EPS)
                or (abs(sens_ms - best["sensitivity_mode_s"]) <= EPS
                    and abs(sens_ah - best["sensitivity_all_hallucinated"]) <= EPS
                    and spec > best["specificity"] + EPS)
            )
            if better:
                best = cand
    if best is None:
        best = {
            "direction": "none", "threshold": float("inf"), "specificity": 1.0,
            "sensitivity_mode_s": 0.0, "sensitivity_all_hallucinated": 0.0,
            "tp_mode_s": 0, "fp": 0, "tn": int(n_neg), "fn_mode_s": int(n_ms),
            "tp_all_hallucinated": 0, "fn_all_hallucinated": int(n_ah),
        }
    return best


def _flag_two_sided(score: float, direction: str, threshold: float) -> bool:
    if direction == "high":
        return score >= threshold - EPS
    if direction == "low":
        return score <= threshold + EPS
    return False


def _ceiling_two_sided(
    neg_scores: list[float],
    pos_scores_mode_s: list[float],
    spec_floors: list[float],
) -> list[dict[str, Any]]:
    n_neg = len(neg_scores)
    n_ms = len(pos_scores_mode_s)
    candidates = sorted(set(neg_scores) | set(pos_scores_mode_s))
    out: list[dict[str, Any]] = []
    for floor in spec_floors:
        best_sens = 0.0
        best_dir = "none"
        best_t = float("inf")
        best_spec = 1.0
        for direction in ("high", "low"):
            for t in candidates:
                if direction == "high":
                    fp = sum(1 for s in neg_scores if s >= t - EPS)
                    tp_ms = sum(1 for s in pos_scores_mode_s if s >= t - EPS)
                else:
                    fp = sum(1 for s in neg_scores if s <= t + EPS)
                    tp_ms = sum(1 for s in pos_scores_mode_s if s <= t + EPS)
                spec = 1.0 - (fp / n_neg) if n_neg else 1.0
                sens = (tp_ms / n_ms) if n_ms else 0.0
                if spec >= floor - EPS and sens > best_sens + EPS:
                    best_sens = sens
                    best_dir = direction
                    best_t = float(t)
                    best_spec = spec
        out.append({
            "specificity_floor": floor,
            "max_sensitivity_mode_s": round(best_sens, 6),
            "direction": best_dir,
            "threshold": round(best_t, 6),
            "achieved_specificity": round(best_spec, 6),
        })
    return out


def _bootstrap_two_sided(
    scores: np.ndarray, labels: np.ndarray, direction: str, threshold: float,
    metric: str = "sensitivity", n_boot: int = N_BOOT, seed: int = SEED,
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(scores)
    if direction == "high":
        flags = (scores >= threshold - EPS)
    elif direction == "low":
        flags = (scores <= threshold + EPS)
    else:
        flags = np.zeros(n, dtype=bool)
    vals: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        f = flags[idx]
        lab = labels[idx]
        if metric == "sensitivity":
            n_pos = int(lab.sum())
            if n_pos <= 0:
                continue
            vals.append(int((f & (lab == 1)).sum()) / n_pos)
        else:
            n_neg = int((lab == 0).sum())
            if n_neg <= 0:
                continue
            vals.append(1.0 - int((f & (lab == 0)).sum()) / n_neg)
    if not vals:
        return 0.0, 0.0
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


if __name__ == "__main__":
    main()
