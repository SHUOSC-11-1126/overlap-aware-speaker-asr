"""RQ34: LLM-based semantic critic for Mode S detection.

Mode S (monoscript-Chinese near-duplicate hallucinations, windows 22 & 30 on
AISHELL-4) has escaped every SURFACE detector (RQ19/22/23/28 all got 0%
sensitivity at 90% specificity). Every prior detector uses surface features
(compression ratio, lang-id entropy, length ratio, content-similarity). None
use semantic understanding. This module tests whether a local LLM
(deepseek-r1:7b via ollama) can detect Mode S by SEMANTIC analysis of the
separated transcript.

A character n-gram KL-divergence fallback is also provided. It tests whether
Mode S has a detectable CHARACTER-DISTRIBUTION anomaly relative to the 40
non-hallucinated tracks. This runs when ollama is unavailable and is also
useful as a distributional baseline against the LLM's semantic approach.

The LLM is dependency-injected (``LLMFn = Callable[[str], str]``); unit tests
use a fake. The real backend is local deepseek-r1 via ollama's HTTP API
(offline; weights already on disk). Labels: experimental/frontier for the
n-gram fallback, qualitative/demo for the LLM-based outputs (LLM judgments are
not deterministic across versions and are qualitative unless evaluated against
a reference, which is what this module does).

Hypotheses
----------
- H34a: LLM semantic critic catches both Mode S windows at 90% specificity
  (sensitivity = 100% at 90% specificity).
- H34b: LLM semantic critic achieves > 95% sensitivity on all AISHELL-4
  hallucinations (37 tracks).
- H34c: LLM semantic critic outperforms lang-id entropy on Mode S
  (Mode S sensitivity > 0%, vs lang-id's 0%).

Kill: if Mode S sensitivity = 0% at 90% specificity (H34a/H34c) or all-halluc
sensitivity <= 95% (H34b).
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
import zlib
from typing import Any, Callable

import numpy as np

LLMFn = Callable[[str], str]

# ---------------------------------------------------------------- thresholds
LANG_ID_ENTROPY_THRESHOLD = 0.409   # RQ13 >=90%-specificity operating point
LENGTH_RATIO_THRESHOLD = 2.0        # RQ14 insertion_dominated proxy
CR_THRESHOLD = 2.4                  # Whisper default / RQ14 repetition guard
CATASTROPHIC_CPWER = 1.0            # cpWER > 1.0 => hallucination label
TARGET_SPECIFICITY = 0.90
N_BOOT = 10000
SEED = 42
EPS = 1e-9

CJK_SCRIPTS = {"Han", "Hiragana", "Katakana", "Hangul"}


# ----------------------------------------------------------------- CR primitive
def compression_ratio(text: str) -> float:
    """Whisper-style compression ratio: len(utf8 bytes) / len(zlib-compressed bytes).

    Matches ``whisper.audio.compression_ratio`` and RQ12/RQ13/RQ16/RQ19. Returns
    0.0 for empty/whitespace text. High CR (>~2.4) = repetitive loop."""
    if not text or not text.strip():
        return 0.0
    b = text.encode("utf-8")
    c = zlib.compress(b)
    return len(b) / len(c) if len(c) > 0 else 0.0


# ------------------------------------------------------------- script detection
def script_category(ch: str) -> str:
    """Map a character to a coarse Unicode script category (RQ13 verbatim)."""
    if ch.isspace():
        return "Space"
    name = unicodedata.name(ch, "")
    if not name:
        return "Other"
    first = name.split()[0]
    if first == "CJK":
        return "Han"
    if first == "LATIN" or "LATIN" in name:
        return "Latin"
    if first == "HIRAGANA":
        return "Hiragana"
    if first == "KATAKANA":
        return "Katakana"
    if first == "HANGUL":
        return "Hangul"
    if first == "CYRILLIC":
        return "Cyrillic"
    if first == "ARABIC":
        return "Arabic"
    if first == "GREEK":
        return "Greek"
    if first == "DIGIT":
        return "Digit"
    cat = unicodedata.category(ch)
    if cat.startswith("P") or cat.startswith("S"):
        return "Punct"
    return "Other"


def language_id_entropy(text: str) -> float:
    """Shannon entropy (bits) over the script-category distribution (RQ13 verbatim)."""
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


def max_across_speakers(window: dict[str, Any], fn: Callable[[str], float]) -> float:
    """Max of fn(text) over per-speaker separated transcripts (RQ12/RQ13 convention)."""
    vals = [
        fn(str(t))
        for t in window.get("separated_text_per_speaker", {}).values()
        if t is not None and str(t).strip()
    ]
    return max(vals) if vals else 0.0


def length_ratio(window: dict[str, Any]) -> float:
    """RQ8/RQ14 silence-gap text proxy: separated_total_length / mixed_text_length."""
    sep = float(window.get("separated_total_length", 0) or 0)
    mix = float(window.get("mixed_text_length", 0) or 0)
    return sep / max(1.0, mix)


def separated_concat(window: dict[str, Any]) -> str:
    """Concatenate the per-speaker separated texts (stripped) into one string."""
    parts = [
        str(t).strip()
        for t in window.get("separated_text_per_speaker", {}).values()
        if t is not None and str(t).strip()
    ]
    return "".join(parts)


def label_window(window: dict[str, Any]) -> dict[str, Any]:
    """Compute surface features + labels for one window (RQ12/RQ13/RQ19 consistent).

    Returns dict with: hallucinated, mode_s, diverse_hallucination, lang_id_entropy,
    length_ratio, cr, separated_text, separated_cpwer."""
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
        "separated_text": separated_concat(window),
        "num_speakers": int(window.get("num_speakers", 0)),
    }


# ======================================================================================
# LLM critic: prompt, response parsing (PURE, unit tested with injected fake LLM)
# ======================================================================================
def strip_think(text: str) -> str:
    """Remove deepseek-r1 ``<think>...</think>`` reasoning. An unclosed/truncated
    think block is dropped entirely (everything from ``<think>`` on), so partial
    reasoning never leaks into the answer."""
    text = re.sub(r"(?s)<think>.*?</think>", "", text)
    text = re.sub(r"(?s)<think>.*$", "", text)  # unclosed
    return text.strip()


def build_critic_prompt(separated_text: str) -> str:
    """Construct the semantic-critic prompt (fixed template, RQ34 spec).

    The LLM is asked to evaluate whether the separated transcript contains
    hallucinated content, considering semantic sense, repetitiveness/genericness,
    and unusual character patterns. Responds as a JSON object."""
    return (
        "You are a speech recognition quality auditor. Below is a transcript from a "
        "multi-speaker meeting audio that was processed by a speech separator and then "
        "transcribed by Whisper.\n\n"
        f"Transcript:\n{separated_text}\n\n"
        "Evaluate whether this transcript likely contains hallucinated content (text that "
        "doesn't correspond to actual speech). Consider:\n"
        "1. Does the text make semantic sense as meeting speech?\n"
        "2. Is the text suspiciously repetitive or generic?\n"
        "3. Does the text contain unusual character patterns?\n\n"
        'Respond with a JSON object: {"hallucinated": true/false, "confidence": 0.0-1.0, "reason": "..."}'
    )


def _extract_json_object(text: str) -> str | None:
    """Extract the first balanced ``{...}`` substring from `text`. Returns None if
    no brace pair is found. Handles nested braces by counting depth."""
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
    return None  # unbalanced


def parse_llm_response(text: str) -> dict[str, Any]:
    """Parse the LLM's response into ``{hallucinated, confidence, reason}``.

    Strategy:
      1. Strip ``<think>`` blocks.
      2. Try to extract and ``json.loads`` a ``{...}`` object.
      3. If JSON fails, fall back to regex extraction of ``hallucinated`` (true/false)
         and ``confidence`` (float) fields.
      4. ``hallucinated`` defaults to False, ``confidence`` to 0.5, ``reason`` to "".
      5. ``confidence`` is clamped to [0, 1].
    """
    body = strip_think(text)
    hallucinated = False
    confidence = 0.5
    reason = ""

    obj_str = _extract_json_object(body)
    if obj_str is not None:
        try:
            obj = json.loads(obj_str)
            if isinstance(obj, dict):
                if "hallucinated" in obj:
                    hallucinated = _to_bool(obj["hallucinated"])
                if "confidence" in obj:
                    confidence = _to_float(obj["confidence"], 0.5)
                if "reason" in obj and isinstance(obj["reason"], str):
                    reason = obj["reason"]
        except (json.JSONDecodeError, ValueError):
            pass  # fall through to regex

    # regex fallback (always runs if JSON didn't set a clear value, or to confirm)
    if obj_str is None:
        m = re.search(r'"?hallucinated"?\s*[:=]\s*"?(true|false)"?', body, re.IGNORECASE)
        if m:
            hallucinated = m.group(1).lower() == "true"
        mc = re.search(r'"?confidence"?\s*[:=]\s*"?([0-9]*\.?[0-9]+)"?', body, re.IGNORECASE)
        if mc:
            confidence = _to_float(mc.group(1), 0.5)
        mr = re.search(r'"?reason"?\s*[:=]\s*"([^"]*)"', body, re.IGNORECASE)
        if mr:
            reason = mr.group(1)

    confidence = max(0.0, min(1.0, confidence))
    return {"hallucinated": bool(hallucinated), "confidence": float(confidence), "reason": reason}


def _to_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "y")
    return False


def _to_float(v: Any, default: float) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def hallucination_score(hallucinated: bool, confidence: float) -> float:
    """Map the LLM's (hallucinated, confidence) to a hallucination-probability score in [0, 1].

    - If the LLM says hallucinated=True with confidence c, score = c (high = likely hallucinated).
    - If the LLM says hallucinated=False with confidence c, score = 1 - c (low = likely clean).

    This gives a single scalar where higher = more likely hallucinated, suitable for
    threshold calibration at a target specificity. Confidence is clamped to [0, 1]."""
    confidence = max(0.0, min(1.0, float(confidence)))
    return float(confidence) if hallucinated else float(1.0 - confidence)


def judge_window(separated_text: str, llm: LLMFn) -> dict[str, Any]:
    """Call the LLM critic on one separated transcript and parse the response.

    Returns the parsed dict ``{hallucinated, confidence, reason}`` plus the raw
    response text (for caching/debugging). If the separated text is empty, returns
    a default non-hallucinated judgment without calling the LLM."""
    if not separated_text or not separated_text.strip():
        return {"hallucinated": False, "confidence": 0.5, "reason": "empty transcript", "raw": ""}
    raw = llm(build_critic_prompt(separated_text))
    parsed = parse_llm_response(raw)
    parsed["raw"] = raw
    return parsed


# ======================================================================================
# Character n-gram KL-divergence fallback (PURE, unit tested)
# ======================================================================================
def char_ngrams(text: str, n: int = 3) -> dict[str, int]:
    """Count character n-grams (whitespace stripped) in `text`. Returns a counts dict."""
    s = "".join(text.split())
    counts: dict[str, int] = {}
    if len(s) < n:
        if s:
            counts[s] = 1
        return counts
    for i in range(len(s) - n + 1):
        gram = s[i:i + n]
        counts[gram] = counts.get(gram, 0) + 1
    return counts


def char_distribution(text: str, n: int = 3, vocab: set[str] | None = None) -> dict[str, float]:
    """Normalised character n-gram probability distribution of `text`.

    If `vocab` is given, the distribution is restricted to that vocabulary (unseen
    grams get 0.0 before smoothing). Additive (Laplace) smoothing of `eps` is applied
    by the caller via ``kl_divergence``; this function returns raw probabilities that
    sum to 1 over the observed grams."""
    counts = char_ngrams(text, n)
    total = sum(counts.values())
    if total <= 0:
        return {} if vocab is None else {g: 0.0 for g in vocab}
    if vocab is None:
        return {g: c / total for g, c in counts.items()}
    return {g: counts.get(g, 0) / total for g in vocab}


def average_distributions(distributions: list[dict[str, float]]) -> dict[str, float]:
    """Element-wise average of a list of probability distributions. Keys are the union;
    missing keys are treated as 0.0. Returns a distribution that sums to ~1."""
    if not distributions:
        return {}
    keys: set[str] = set()
    for d in distributions:
        keys.update(d.keys())
    n = len(distributions)
    return {k: sum(d.get(k, 0.0) for d in distributions) / n for k in keys}


def kl_divergence(p: dict[str, float], q: dict[str, float], eps: float = EPS) -> float:
    """KL(p || q) = sum p * log(p / q), with additive smoothing eps on both distributions.

    Keys are the union of p and q. Smoothing ensures no log(0). Returns 0.0 if p is
    empty. High KL = p is very different from q (anomalous)."""
    keys = set(p.keys()) | set(q.keys())
    if not keys:
        return 0.0
    total = 0.0
    for k in keys:
        pk = p.get(k, 0.0) + eps
        qk = q.get(k, 0.0) + eps
        total += pk * math.log(pk / qk)
    return float(total)


def compute_anomaly_score(
    text: str, ref_distribution: dict[str, float], n: int = 3, eps: float = EPS,
) -> float:
    """KL-divergence anomaly score of `text` relative to a reference n-gram distribution.

    The text's distribution is computed over its OWN vocabulary (so novel n-grams not
    in the reference are retained), then KL(text || ref) is computed over the union
    vocabulary. Novel n-grams contribute a large KL term (the text has probability
    mass on grams the reference never sees), which is exactly the anomaly signal.
    High score = the text's character n-gram distribution is anomalous relative to the
    reference (the average of the 40 non-hallucinated tracks)."""
    if not text or not text.strip() or not ref_distribution:
        return 0.0
    dist = char_distribution(text, n)  # own vocab — novel grams retained
    return kl_divergence(dist, ref_distribution, eps=eps)


def build_reference_distribution(
    texts: list[str], n: int = 3,
) -> dict[str, float]:
    """Build the average character n-gram distribution from a list of reference texts
    (the 40 non-hallucinated tracks). Each text's distribution is over its own
    vocabulary; the average is over the union vocabulary."""
    dists = [char_distribution(t, n) for t in texts if t and t.strip()]
    return average_distributions(dists)


# ======================================================================================
# Threshold calibration + evaluation (PURE, unit tested)
# ======================================================================================
def calibrate_threshold_at_specificity(
    neg_scores: list[float], pos_scores: list[float] | None = None,
    target_spec: float = TARGET_SPECIFICITY,
) -> dict[str, Any]:
    """Pick the threshold `t` that achieves the highest sensitivity while keeping
    specificity >= target_spec.

    Flag if score >= t (high score = hallucination). Candidate thresholds are drawn
    from the union of neg_scores and pos_scores: a pos_score that sits between two
    neg_scores is an optimal operating point (it flags that positive without adding
    false positives). Among candidates meeting the specificity floor, the SMALLEST
    threshold (most permissive, highest sensitivity) is chosen. If no threshold
    meets the floor, returns t = +inf (flags nothing, specificity = 1.0)."""
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

    `labels`: 1 = hallucinated, 0 = non-hallucinated. Returns tp, fp, tn, fn,
    sensitivity, specificity, precision."""
    n = len(scores)
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
        "n": n,
    }


def subgroup_sensitivity(
    scores: list[float], subgroup_mask: list[bool], threshold: float,
) -> dict[str, Any]:
    """Sensitivity within a subgroup (e.g. Mode S, or diverse hallucination).

    `subgroup_mask[i]` = True if window i is in the subgroup. Returns the fraction
    of subgroup windows flagged (score >= threshold), plus tp/n counts."""
    n_sub = sum(1 for m in subgroup_mask if m)
    if n_sub == 0:
        return {"sensitivity": 0.0, "tp": 0, "n": 0}
    tp = sum(1 for s, m in zip(scores, subgroup_mask) if m and s >= threshold - EPS)
    return {"sensitivity": tp / n_sub, "tp": tp, "n": n_sub}


def bootstrap_sensitivity_ci(
    scores: np.ndarray, labels: np.ndarray, threshold: float,
    n_boot: int = N_BOOT, seed: int = SEED,
) -> tuple[float, float]:
    """Bootstrap 95% CI for sensitivity = P(flag | label==1) with FIXED threshold."""
    rng = np.random.default_rng(seed)
    n = len(scores)
    pos_idx = np.where(labels == 1)[0]
    n_pos = len(pos_idx)
    if n_pos <= 0:
        return 0.0, 0.0
    pos_scores = scores[pos_idx]
    sens: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n_pos, size=n_pos)
        s = pos_scores[idx]
        tp = int((s >= threshold - EPS).sum())
        sens.append(tp / n_pos)
    return float(np.percentile(sens, 2.5)), float(np.percentile(sens, 97.5))


def bootstrap_specificity_ci(
    scores: np.ndarray, labels: np.ndarray, threshold: float,
    n_boot: int = N_BOOT, seed: int = SEED,
) -> tuple[float, float]:
    """Bootstrap 95% CI for specificity = P(not flag | label==0) with FIXED threshold."""
    rng = np.random.default_rng(seed)
    neg_idx = np.where(labels == 0)[0]
    n_neg = len(neg_idx)
    if n_neg <= 0:
        return 1.0, 1.0
    neg_scores = scores[neg_idx]
    specs: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n_neg, size=n_neg)
        s = neg_scores[idx]
        fp = int((s >= threshold - EPS).sum())
        specs.append(1.0 - fp / n_neg)
    return float(np.percentile(specs, 2.5)), float(np.percentile(specs, 97.5))


# ======================================================================================
# Real backend: local deepseek-r1 via ollama HTTP API (offline; lazy)
# ======================================================================================
def ollama_llm(
    model: str = "deepseek-r1:7b",
    num_predict: int = 512,
    host: str = "http://localhost:11434",
    timeout: int = 300,
) -> LLMFn:
    """Return an LLMFn that calls a local ollama model via its HTTP /api/generate endpoint.

    Equivalent to ``ollama run <model>`` via stdin but easier to parse (non-streaming
    JSON). Temperature 0.0 for determinism. The HTTP API is the same backend
    ``ollama run`` uses; we prefer it for reliable JSON parsing."""
    import urllib.request

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
    """Check whether ollama is reachable and `model` is loaded."""
    import urllib.request
    import urllib.error
    try:
        with urllib.request.urlopen(f"{host}/api/tags", timeout=5) as resp:
            data = json.load(resp)
        models = [m.get("name", "") for m in data.get("models", [])]
        return any(m == model or m.startswith(model + ":") for m in models)
    except (urllib.error.URLError, OSError, ValueError, KeyError):
        return False
