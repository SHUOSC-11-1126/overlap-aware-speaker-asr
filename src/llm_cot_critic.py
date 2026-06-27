"""RQ52: Chain-of-thought (CoT) LLM critic for Mode S detection.

CoT prompting structures the LLM's reasoning into 5 explicit steps before a
verdict: (1) language identification, (2) repetition check, (3) semantic
coherence, (4) insertion artifacts, (5) final verdict. This differs from RQ34's
zero-shot direct-verdict prompt (which asks for an immediate JSON verdict) and
RQ41's multi-call self-consistency ensemble (which votes across temperatures).

Background
----------
- RQ34 (zero-shot, deepseek-r1:7b, PR #951): 52.5% false-positive rate, 0% Mode S
  sensitivity at 90% specificity. The LLM reads Mode S as reliable speech (RQ36).
- RQ41 (5-call ensemble, T=0.0-0.8, PR #961): 62.5% FP (worse than single-call).

RQ52 asks whether explicit step-by-step reasoning (forcing the LLM to articulate
what makes a transcript hallucinated *before* committing to a verdict) overcomes
the ~50% FP rate of zero-shot.

Hypotheses (pre-registered)
---------------------------
- H52a: CoT Mode S sensitivity > 50% at 90% specificity (beats zero-shot's 0%).
- H52b: CoT false-positive rate < 50% (beats zero-shot's 52.5%).
- H52c: CoT AUC > 0.60 (beats random and zero-shot's near-chance).

Kill: Mode S sensitivity <= 50% (H52a), FP >= 50% (H52b), or AUC <= 0.60 (H52c).

Design
------
- REFERENCE-FREE: the LLM sees ONLY the separated transcript (never the reference
  or mixed decode). Respects the hard safety rule (no CER/reference as routing
  input).
- DEPENDENCY-INJECTED LLM: ``LLMFn = Callable[[str], str]``. Unit tests use a fake;
  the real backend is local deepseek-r1 via ollama (offline, T=0.0 for determinism).
- The continuous hallucination score (for AUC + calibration) maps
  (verdict, confidence) -> [0, 1]: ``confidence`` if hallucinated, else
  ``1 - confidence``. This reuses RQ34's convention so results are comparable.

Labels: experimental/frontier + qualitative/demo (LLM outputs). Reference issue RQ52.
Source data: results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json
(external/sanity-check, read-only — NOT modified).
"""
from __future__ import annotations

import json
import math
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .config import PROJECT_ROOT

LLMFn = Callable[[str], str]

# Mode S / hallucination thresholds (lifted from RQ13/RQ16/RQ19/RQ34 for comparability)
LANG_ID_ENTROPY_THRESHOLD = 0.409   # RQ13 >=90%-specificity operating point
LENGTH_RATIO_THRESHOLD = 2.0        # RQ14 insertion_dominated proxy
CR_THRESHOLD = 2.4                  # Whisper default / RQ14 repetition guard
CATASTROPHIC_CPWER = 1.0            # cpWER > 1.0 => hallucination label
TARGET_SPECIFICITY = 0.90
N_BOOT = 10000
SEED = 42
EPS = 1e-9

OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "llm_cot_critic"


# ======================================================================================
# Pure prompt + parsing logic (no ollama) -- unit tested with an injected fake LLM
# ======================================================================================
def strip_think(text: str) -> str:
    """Remove deepseek-r1 ``<think>...</think>`` reasoning blocks.

    An unclosed/truncated think block is dropped entirely (everything from
    ``<think>`` on), so partial reasoning never leaks into the answer. Adapted
    from RQ34/RQ41's ``strip_think``."""
    text = re.sub(r"(?s)<think>.*?</think>", "", text)
    text = re.sub(r"(?s)<think>.*$", "", text)  # unclosed
    return text.strip()


def build_cot_prompt(transcript: str) -> str:
    """Construct the 5-step chain-of-thought critic prompt (RQ52 spec).

    The LLM is forced to reason step-by-step about (1) language mixing, (2)
    repetition, (3) semantic coherence, (4) insertion artifacts, BEFORE giving a
    final YES/NO verdict. This is the key difference from RQ34's zero-shot
    direct-verdict prompt. The verdict + confidence are emitted on fixed final
    lines for reliable parsing."""
    return (
        "You are a speech recognition quality auditor. Analyze the following "
        "Chinese ASR transcript step by step.\n\n"
        f"Transcript: {transcript}\n\n"
        "Step 1: Identify the main language(s) used. Is it monolingual Chinese, "
        "or does it mix scripts (Latin, Katakana, Hangul)?\n"
        "Step 2: Check for repetition. Are there repeated phrases or loops?\n"
        "Step 3: Check for semantic coherence. Does the text form coherent "
        "sentences, or is it fragmented/gibberish?\n"
        "Step 4: Check for insertion artifacts. Are there extra characters, "
        "words, or speaker streams that shouldn't be there?\n"
        "Step 5: Based on steps 1-4, is this transcript likely hallucinated "
        "(ASR-generated artifacts) or clean? Answer YES (hallucinated) or NO "
        "(clean).\n\n"
        "Provide your reasoning for each step, then give the final verdict on "
        "the last two lines in EXACTLY this format:\n"
        "VERDICT: YES\n"
        "CONFIDENCE: 0.0\n"
        "where CONFIDENCE is a decimal between 0 and 1 (1 = very certain)."
    )


def parse_cot_verdict(response: str) -> dict[str, Any]:
    """Parse the CoT LLM response into ``{hallucinated, confidence, verdict_raw}``.

    Strategy (after think-stripping):
      1. Search for ``VERDICT: YES``/``NO`` (case-insensitive). Accept
         ``是``/``否``/``true``/``false``/``hallucinated``/``clean`` as aliases.
      2. Search for ``CONFIDENCE: x`` (float, clamped to [0, 1]).
      3. If no VERDICT line is found, fall back to a last-occurrence YES/NO scan
         of the body (CoT may phrase the verdict in prose).
      4. ``hallucinated`` defaults to False, ``confidence`` to 0.5,
         ``verdict_raw`` to the matched verdict string (or "" if none).

    Returns a dict with keys ``hallucinated`` (bool), ``confidence`` (float),
    ``verdict_raw`` (str).
    """
    body = strip_think(response)
    hallucinated = False
    confidence = 0.5
    verdict_raw = ""

    # --- VERDICT line (preferred: explicit "VERDICT:" prefix)
    m = re.search(r"VERDICT\s*[:：]\s*([^\n]+)", body, re.IGNORECASE)
    if m:
        ans = m.group(1).strip().strip('"“”').lower()
        verdict_raw = m.group(1).strip()
        hallucinated = _verdict_to_bool(ans)

    # --- CONFIDENCE line
    mc = re.search(r"CONFIDENCE\s*[:：]\s*(-?[0-9]*\.?[0-9]+)", body, re.IGNORECASE)
    if mc:
        try:
            confidence = max(0.0, min(1.0, float(mc.group(1))))
        except ValueError:
            pass

    # --- fallback: if no VERDICT line, scan for a trailing YES/NO in the body
    if not m:
        # last occurrence of yes/no (CoT may state the verdict in prose)
        yes_matches = list(re.finditer(
            r"\b(yes|是|true|hallucinated)\b", body, re.IGNORECASE))
        no_matches = list(re.finditer(
            r"\b(no|否|false|clean)\b", body, re.IGNORECASE))
        if yes_matches and no_matches:
            # whichever appears last wins
            if yes_matches[-1].start() > no_matches[-1].start():
                hallucinated = True
                verdict_raw = yes_matches[-1].group(0)
            else:
                hallucinated = False
                verdict_raw = no_matches[-1].group(0)
        elif yes_matches:
            hallucinated = True
            verdict_raw = yes_matches[-1].group(0)
        elif no_matches:
            hallucinated = False
            verdict_raw = no_matches[-1].group(0)

    return {
        "hallucinated": bool(hallucinated),
        "confidence": float(confidence),
        "verdict_raw": verdict_raw,
    }


def _verdict_to_bool(ans: str) -> bool:
    """Map a verdict string to True (hallucinated) / False (clean).

    Accepts: yes/是/true/y/1/hallucinated -> True;
             no/否/false/n/0/clean/not -> False. Defaults to False."""
    ans = ans.strip().lower()
    if ans in ("yes", "是", "true", "y", "1", "hallucinated"):
        return True
    if ans in ("no", "否", "false", "n", "0", "clean", "not"):
        return False
    if ans.startswith("yes"):
        return True
    if ans.startswith("no"):
        return False
    return False


def hallucination_score(hallucinated: bool, confidence: float) -> float:
    """Map (verdict, confidence) to a continuous hallucination-probability score in [0, 1].

    - hallucinated=True with confidence c  -> score = c (high = likely hallucinated).
    - hallucinated=False with confidence c -> score = 1 - c (low = likely clean).

    This matches RQ34's ``hallucination_score`` so the two critics are directly
    comparable under threshold calibration and AUC. Confidence is clamped to [0, 1]."""
    confidence = max(0.0, min(1.0, float(confidence)))
    return float(confidence) if hallucinated else float(1.0 - confidence)


def judge_window_cot(transcript: str, llm: LLMFn) -> dict[str, Any]:
    """Call the CoT critic on one transcript and parse the response.

    Returns the parsed dict (``hallucinated, confidence, verdict_raw``) plus the
    raw response text (for caching/debugging). If the transcript is empty, returns
    a default non-hallucinated judgment WITHOUT calling the LLM (matches RQ34/RQ41
    short-circuit convention)."""
    if not transcript or not transcript.strip():
        return {"hallucinated": False, "confidence": 0.5, "verdict_raw": "",
                "reason": "empty transcript", "raw": ""}
    raw = llm(build_cot_prompt(transcript))
    parsed = parse_cot_verdict(raw)
    parsed["raw"] = raw
    return parsed


# ======================================================================================
# AUC (rank-based Mann-Whitney U) -- PURE, unit tested
# ======================================================================================
def roc_auc(scores: list[float], labels: list[int]) -> float:
    """Rank-based ROC AUC via the Mann-Whitney U statistic.

    ``labels``: 1 = positive (hallucinated), 0 = negative (clean).
    AUC = P(score_pos > score_neg) over all positive-negative pairs, with ties
    counted as 0.5. Returns 0.5 if either class is empty (no information).

    Equivalent to sklearn's ``roc_auc_score`` for the binary case but
    dependency-free (numpy only)."""
    n_pos = sum(1 for l in labels if l == 1)
    n_neg = sum(1 for l in labels if l == 0)
    if n_pos == 0 or n_neg == 0:
        return 0.5
    arr = sorted(zip(scores, labels), key=lambda x: x[0])
    # assign ranks with tie handling (average rank for ties)
    ranks: list[float] = [0.0] * len(arr)
    i = 0
    while i < len(arr):
        j = i
        while j < len(arr) and arr[j][0] == arr[i][0]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0  # average of ranks i+1..j (1-indexed)
        for k in range(i, j):
            ranks[k] = avg_rank
        i = j
    sum_pos_ranks = sum(r for (_, l), r in zip(arr, ranks) if l == 1)
    # U = sum_pos_ranks - n_pos*(n_pos+1)/2
    u = sum_pos_ranks - n_pos * (n_pos + 1) / 2.0
    return float(u / (n_pos * n_neg))


# ======================================================================================
# Cache load/save (resumable) -- PURE, unit tested with tempfile
# ======================================================================================
def load_cache(path: Path) -> dict[str, Any]:
    """Load the CoT response cache. Returns ``{}`` if missing or malformed."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        return data
    except (json.JSONDecodeError, ValueError, OSError):
        return {}


def save_cache(path: Path, cache: dict[str, Any]) -> None:
    """Write the cache to ``path`` (pretty JSON, utf-8)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def cache_key(transcript: str) -> str:
    """Stable cache key for a transcript (sha1 of stripped text, first 16 hex chars).

    Two transcripts with identical stripped content share a key, so re-runs hit
    the cache without re-calling the LLM."""
    import hashlib
    h = hashlib.sha1(transcript.strip().encode("utf-8")).hexdigest()
    return h[:16]


# ======================================================================================
# Threshold calibration + evaluation (one-sided high: flag if score >= threshold)
# ======================================================================================
def calibrate_threshold_at_specificity(
    neg_scores: list[float], pos_scores: list[float] | None = None,
    target_spec: float = TARGET_SPECIFICITY,
) -> dict[str, Any]:
    """Pick the threshold ``t`` achieving the highest sensitivity while keeping
    specificity >= ``target_spec`` (flag if score >= t).

    Candidate thresholds are the union of neg + pos scores. Among candidates
    meeting the specificity floor, the SMALLEST threshold (most permissive) is
    chosen. If no threshold meets the floor, returns t = +inf (flags nothing,
    specificity = 1.0). Mirrors RQ34's calibration for direct comparability."""
    n_neg = len(neg_scores)
    if n_neg == 0:
        return {"threshold": float("inf"), "specificity": 1.0, "n_neg": 0, "max_fp": 0}
    max_fp = int(math.floor((1.0 - target_spec) * n_neg + EPS))
    cand_set: set[float] = set(neg_scores)
    if pos_scores:
        cand_set.update(pos_scores)
    candidates = sorted(cand_set)
    best_t = float("inf")
    best_spec = 1.0
    for t in candidates:
        fp = sum(1 for s in neg_scores if s >= t - EPS)
        if fp <= max_fp:
            best_t = t
            best_spec = 1.0 - fp / n_neg
            break  # ascending => first valid is the smallest (highest sensitivity)
    return {
        "threshold": float(best_t), "specificity": float(best_spec),
        "n_neg": n_neg, "max_fp": max_fp,
    }


def evaluate_at_threshold(
    scores: list[float], labels: list[int], threshold: float,
) -> dict[str, Any]:
    """Confusion-matrix metrics for ``flag if score >= threshold``.

    ``labels``: 1 = hallucinated, 0 = non-hallucinated. Returns tp, fp, tn, fn,
    sensitivity, specificity, precision."""
    tp = fp = tn = fn = 0
    for s, lab in zip(scores, labels):
        flagged = s >= threshold - EPS
        if flagged and lab == 1:
            tp += 1
        elif flagged and lab == 0:
            fp += 1
        elif not flagged and lab == 0:
            tn += 1
        else:
            fn += 1
    n_pos = tp + fn
    n_neg = fp + tn
    return {
        "threshold": float(threshold),
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "sensitivity": (tp / n_pos) if n_pos > 0 else 0.0,
        "specificity": (tn / n_neg) if n_neg > 0 else 1.0,
        "precision": (tp / (tp + fp)) if (tp + fp) > 0 else 0.0,
        "n": len(scores),
    }


def subgroup_sensitivity(
    scores: list[float], subgroup_mask: list[bool], threshold: float,
) -> dict[str, Any]:
    """Sensitivity within a subgroup (e.g. Mode S). Returns fraction flagged + tp/n."""
    n_sub = sum(1 for m in subgroup_mask if m)
    if n_sub == 0:
        return {"sensitivity": 0.0, "tp": 0, "n": 0}
    tp = sum(1 for s, m in zip(scores, subgroup_mask) if m and s >= threshold - EPS)
    return {"sensitivity": tp / n_sub, "tp": tp, "n": n_sub}


def false_positive_rate(scores: list[float], labels: list[int], threshold: float) -> float:
    """FP rate = P(flag | label==0) = fp / n_neg. Returns 0.0 if no negatives."""
    n_neg = sum(1 for l in labels if l == 0)
    if n_neg == 0:
        return 0.0
    fp = sum(1 for s, l in zip(scores, labels) if l == 0 and s >= threshold - EPS)
    return fp / n_neg


def bootstrap_ci(
    scores: np.ndarray, labels: np.ndarray, threshold: float,
    metric: str = "sensitivity", n_boot: int = N_BOOT, seed: int = SEED,
) -> tuple[float, float]:
    """Bootstrap 95% CI for sensitivity or specificity at a FIXED threshold.

    ``metric``: "sensitivity" = P(flag | label==1); "specificity" = P(not flag | label==0).
    Returns the 2.5th and 97.5th percentiles over the bootstrap resamples."""
    rng = np.random.default_rng(seed)
    n = len(scores)
    flags = scores >= threshold - EPS
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
        else:  # specificity
            n_neg = int((lab == 0).sum())
            if n_neg <= 0:
                continue
            vals.append(1.0 - int((f & (lab == 0)).sum()) / n_neg)
    if not vals:
        return 0.0, 0.0
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


# ======================================================================================
# Real backend: local deepseek-r1 via ollama HTTP API (offline; lazy)
# ======================================================================================
def ollama_llm(
    model: str = "deepseek-r1:7b",
    num_predict: int = 1024,
    host: str = "http://localhost:11434",
    timeout: int = 300,
) -> LLMFn:
    """Return an LLMFn that calls a local ollama model via its HTTP /api/generate endpoint.

    Temperature 0.0 for deterministic output (unlike RQ41's temperature spread).
    The HTTP API is the same backend ``ollama run`` uses; we prefer it for reliable
    response parsing (non-streaming JSON)."""
    def call(prompt: str) -> str:
        body = json.dumps({
            "model": model, "prompt": prompt, "stream": False,
            "options": {"temperature": 0.0, "num_predict": num_predict},
        }).encode()
        req = urllib.request.Request(
            f"{host}/api/generate", data=body, headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp).get("response", "")
    return call


def ollama_available(host: str = "http://localhost:11434", model: str = "deepseek-r1:7b") -> bool:
    """Check whether ollama is reachable and ``model`` is loaded."""
    try:
        with urllib.request.urlopen(f"{host}/api/tags", timeout=5) as resp:
            data = json.load(resp)
        models = [m.get("name", "") for m in data.get("models", [])]
        return any(m == model or m.startswith(model + ":") for m in models)
    except (urllib.error.URLError, OSError, ValueError, KeyError):
        return False
