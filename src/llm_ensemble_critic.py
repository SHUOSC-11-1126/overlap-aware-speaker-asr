"""RQ41: Multi-call LLM ensemble critic for Mode S (experimental/frontier).

Self-consistency ensemble of N=5 deepseek-r1:7b calls (temperatures 0.0-0.8) that
votes on whether a separated ASR transcript is a hallucination. The goal is to
reduce the single-call false-positive rate enough to make the LLM deployable at 90%
specificity on the AISHELL-4 Mode S residual (windows 22, 30).

Background (RQ19/RQ34): a single deepseek-r1:7b call achieves 0% Mode S sensitivity
at 90% specificity (52.5% false-positive rate). It catches window 30 (repetitive) but
misses window 22 (coherent near-duplicate Chinese). Self-consistency (majority vote
across multiple calls at different temperatures) may improve reliability.

Design commitments:
  1. REFERENCE-FREE. The LLM sees ONLY the separated transcript (never the reference
     or the mixed decode). This matches RQ34's single-call setup and respects the
     hard safety rule (no CER/reference as routing input).
  2. DEPENDENCY-INJECTED LLM. ``LLMFn = Callable[[str, float], str]`` takes (prompt,
     temperature) and returns the raw response. Unit tests use a fake; the real
     backend is local deepseek-r1 via ollama (offline).
  3. RESUMABLE CACHE. Responses are cached by (transcript_hash, temperature) so the
     ~305-call ensemble can be interrupted and resumed. Cache is saved every 5 calls.

The prompt and think-stripping parser are adapted from ``src/llm_asr_critic.py``
(RQ34's single-call critic), extended to return a boolean hallucination verdict +
confidence instead of a continuous quality score.

Labels: experimental/frontier + qualitative/demo (LLM outputs). Reference issue #954.
Source data: results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json
(external/sanity-check, read-only).
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import urllib.request
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .config import PROJECT_ROOT

LLMFn = Callable[[str, float], str]  # (prompt, temperature) -> raw response text
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "llm_ensemble_critic"

# Ensemble configuration
ENSEMBLE_TEMPERATURES = [0.0, 0.2, 0.4, 0.6, 0.8]
N_ENSEMBLE = len(ENSEMBLE_TEMPERATURES)

# Mode S / hallucination thresholds (lifted from RQ13/RQ16/RQ19 for comparability)
LANG_ID_ENTROPY_THRESHOLD = 0.409   # RQ13 >=90%-specificity operating point
LENGTH_RATIO_THRESHOLD = 2.0        # RQ14 insertion_dominated proxy
CR_THRESHOLD = 2.4                  # Whisper default / RQ14 repetition guard
CATASTROPHIC_CPWER = 1.0            # cpWER > 1.0 => hallucination label
TARGET_SPECIFICITY = 0.90
N_BOOT = 10000
SEED = 42
EPS = 1e-9


# ======================================================================================
# Pure prompt + parsing logic (no ollama) -- unit tested with an injected fake LLM
# ======================================================================================
def strip_think(text: str) -> str:
    """Remove deepseek-r1 ``<think>...</think>`` reasoning. An unclosed/truncated think
    block is dropped entirely (everything from ``<think>`` on), so partial reasoning
    never leaks into the answer. Adapted from ``src/llm_asr_critic.strip_think``."""
    text = re.sub(r"(?s)<think>.*?</think>", "", text)
    text = re.sub(r"(?s)<think>.*$", "", text)  # unclosed
    return text.strip()


def build_hallucination_prompt(transcript: str) -> str:
    """Reference-free hallucination prompt. The LLM sees ONLY the separated transcript
    and must decide if it is a hallucination (recognition error, repetition loop,
    gibberish, or text unrelated to normal speech). Returns a boolean verdict +
    confidence. Adapted from RQ34's ``build_judge_prompt`` (score -> boolean)."""
    return (
        "你是中文语音识别质量评审。判断下面这句语音识别结果是否为“幻觉”——"
        "即明显的识别错误、重复循环、乱码或与正常语音无关的文本。"
        "如果基本通顺合理（即使有个别小错别字），则判定为非幻觉。"
        "只在最后两行输出：第一行 “HALLUCINATED: yes” 或 “HALLUCINATED: no”，"
        "第二行 “CONFIDENCE: x”，x 为 0 到 1 的小数（1=非常确定，0=非常不确定），"
        "不要解释。\n"
        f"识别结果：{transcript}\n"
    )


def parse_hallucination(response: str) -> tuple[bool | None, float | None]:
    """Parse ``HALLUCINATED: yes/no`` and ``CONFIDENCE: x`` from a raw LLM response
    (after think-stripping). Returns ``(hallucinated, confidence)`` where either may be
    ``None`` if absent / unparseable. ``yes``/``是``/``true`` -> True; ``no``/``否``/``false``
    -> False. Confidence is clamped to [0, 1]."""
    body = strip_think(response)
    h: bool | None = None
    conf: float | None = None
    # HALLUCINATED: yes/no (case-insensitive); accept 是/否 and true/false too
    m = re.search(r"HALLUCINATED\s*[:：]\s*([^\n]+)", body, re.IGNORECASE)
    if m:
        ans = m.group(1).strip().strip('"“”').lower()
        if ans in ("yes", "是", "true", "y", "1", " hallucinated"):
            h = True
        elif ans in ("no", "否", "false", "n", "0", "not"):
            h = False
        elif ans.startswith("yes"):
            h = True
        elif ans.startswith("no"):
            h = False
    m2 = re.search(r"CONFIDENCE\s*[:：]\s*(-?[0-9]*\.?[0-9]+)", body, re.IGNORECASE)
    if m2:
        conf = max(0.0, min(1.0, float(m2.group(1))))
    return h, conf


def majority_vote(votes: list[bool]) -> bool:
    """Majority vote over a list of boolean verdicts. Ties (e.g. 2-2 with an odd
    count cannot tie; 5 calls -> 3+ wins) resolve to True only if strictly more than
    half vote True. None entries (unparseable) are ignored; if all are None, returns
    False (conservative: do not flag)."""
    valid = [v for v in votes if v is not None]
    if not valid:
        return False
    return sum(1 for v in valid if v) > len(valid) / 2


def mean_confidence(confidences: list[float | None]) -> float:
    """Mean of per-call confidences, ignoring None entries. Returns 0.0 if all None."""
    valid = [c for c in confidences if c is not None]
    if not valid:
        return 0.0
    return float(np.mean(valid))


def yes_count(votes: list[bool | None]) -> int:
    """Number of 'yes' (hallucinated) votes, ignoring None entries."""
    return sum(1 for v in votes if v is True)


def aggregate_ensemble(per_call: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate N per-call results into an ensemble verdict.

    Each per-call dict has keys: ``hallucinated`` (bool|None), ``confidence`` (float|None),
    ``temperature`` (float), ``response`` (str, raw).

    Returns: ``{hallucinated_majority, mean_confidence, yes_count, n_calls,
    n_parseable, per_call}``.
    """
    votes = [c.get("hallucinated") for c in per_call]
    confs = [c.get("confidence") for c in per_call]
    return {
        "hallucinated_majority": bool(majority_vote(votes)),
        "mean_confidence": round(mean_confidence(confs), 6),
        "yes_count": yes_count(votes),
        "n_calls": len(per_call),
        "n_parseable": sum(1 for v in votes if v is not None),
        "yes_vote_fraction": round(yes_count(votes) / max(1, len(per_call)), 6),
        "per_call": per_call,
    }


# ======================================================================================
# n-gram KL divergence baseline (reference-free comparison; uses sep vs mix)
# ======================================================================================
def char_ngrams(text: str, n: int) -> list[str]:
    """List of character n-grams (whitespace stripped). Empty if too short."""
    s = "".join(text.split())
    if len(s) < n:
        return [s] if s else []
    return [s[i:i + n] for i in range(len(s) - n + 1)]


def ngram_distribution(text: str, n: int) -> dict[str, float]:
    """Empirical character n-gram probability distribution (normalised counts)."""
    grams = char_ngrams(text, n)
    if not grams:
        return {}
    counts: dict[str, int] = {}
    for g in grams:
        counts[g] = counts.get(g, 0) + 1
    total = sum(counts.values())
    return {g: c / total for g, c in counts.items()}


def kl_divergence(p: dict[str, float], q: dict[str, float], eps: float = 1e-9) -> float:
    """KL(p || q) with add-eps smoothing over the union vocabulary. Returns 0.0 if p
    is empty. A gram in p but absent from q contributes p*log(p/eps) (large)."""
    if not p:
        return 0.0
    vocab = set(p) | set(q)
    kl = 0.0
    for g in vocab:
        pg = p.get(g, 0.0)
        qg = q.get(g, eps)
        if pg > 0:
            kl += pg * np.log(pg / qg)
    return float(kl)


def ngram_kl(sep_text: str, mix_text: str, n: int = 3) -> float:
    """KL(sep_ngram || mix_ngram) between separated and mixed character n-gram
    distributions. High = sep is dissimilar to mix (diverse hallucination); low = sep
    is a near-duplicate of mix (Mode S profile). For empty mix, returns a large
    sentinel (sep is entirely novel -> max dissimilarity). For empty sep, returns 0.0."""
    if not sep_text or not sep_text.strip():
        return 0.0
    if not mix_text or not mix_text.strip():
        return 100.0  # sentinel: sep non-empty but mix empty -> entirely novel
    p = ngram_distribution(sep_text, n)
    q = ngram_distribution(mix_text, n)
    return max(0.0, kl_divergence(p, q))


# ======================================================================================
# Cache (resumable): key = sha1(transcript) + temperature
# ======================================================================================
def transcript_hash(transcript: str) -> str:
    """Stable SHA-1 of the transcript (for cache keying)."""
    return hashlib.sha1(transcript.encode("utf-8")).hexdigest()[:16]


def cache_key(transcript: str, temperature: float) -> str:
    """Cache key = '{hash}__t{temperature:.1f}'."""
    return f"{transcript_hash(transcript)}__t{temperature:.1f}"


def load_cache(path: Path) -> dict[str, dict[str, Any]]:
    """Load the response cache JSON. Returns {} if the file does not exist or is
    malformed (resumability: a corrupt cache should not block re-analysis)."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_cache(path: Path, cache: dict[str, dict[str, Any]]) -> None:
    """Atomically save the cache JSON (write to temp then rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


# ======================================================================================
# Ensemble judge (calls the LLM N times with cache + thread-safe writes)
# ======================================================================================
def ensemble_judge(
    transcript: str,
    llm: LLMFn,
    temperatures: list[float] | None = None,
    cache: dict[str, dict[str, Any]] | None = None,
    cache_lock: threading.Lock | None = None,
    cache_path: Path | None = None,
    save_every: int = 5,
    max_workers: int = 1,
) -> dict[str, Any]:
    """Run N LLM calls at the given temperatures on a single transcript, with caching.

    Returns the aggregated ensemble verdict (see ``aggregate_ensemble``) augmented with
    per-call responses and cache hit info. If ``cache`` is provided, cached responses
    are reused and new responses are inserted under ``cache_lock``. The cache is saved
    to ``cache_path`` every ``save_every`` new calls.

    If ``max_workers > 1``, non-cached (live) LLM calls within this transcript are
    submitted to a ``ThreadPoolExecutor(max_workers)`` so the N temperatures run
    concurrently (ollama with ``--parallel N`` handles the server-side concurrency).
    Cached calls are never submitted to the pool.

    Empty transcripts are short-circuited (no LLM call): verdict = not hallucinated,
    confidence 0.0, yes_count 0. This avoids wasting calls on silence windows (all of
    which are non-hallucinated, cpWER=1.0) and avoids ambiguous LLM judgments on empty
    text.
    """
    from concurrent.futures import ThreadPoolExecutor

    temps = temperatures if temperatures is not None else ENSEMBLE_TEMPERATURES
    # Empty transcript short-circuit (silence windows: non-hallucinated by definition)
    if not transcript or not transcript.strip():
        per_call = [
            {"temperature": t, "hallucinated": False, "confidence": 0.0,
             "response": "", "cached": False, "empty_short_circuit": True}
            for t in temps
        ]
        agg = aggregate_ensemble(per_call)
        agg["transcript_hash"] = transcript_hash(transcript) if transcript else ""
        agg["empty_short_circuit"] = True
        return agg

    if cache is None:
        cache = {}
    if cache_lock is None:
        cache_lock = threading.Lock()

    prompt = build_hallucination_prompt(transcript)

    # Phase 1: identify cached vs live calls (preserve temperature order)
    live_indices: list[int] = []  # positions in per_call needing a live call
    per_call: list[dict[str, Any]] = [{} for _ in temps]  # type: ignore
    for i, t in enumerate(temps):
        key = cache_key(transcript, t)
        with cache_lock:
            hit = cache.get(key)
        if hit is not None:
            per_call[i] = {
                "temperature": t,
                "hallucinated": hit.get("hallucinated"),
                "confidence": hit.get("confidence"),
                "response": hit.get("response", ""),
                "cached": True,
            }
        else:
            live_indices.append(i)
            per_call[i] = {"temperature": t, "_pending": True}

    # Phase 2: run live calls (optionally in parallel) and populate cache
    def _run_live(t: float) -> dict[str, Any]:
        resp = llm(prompt, t)
        h, conf = parse_hallucination(resp)
        return {"hallucinated": h, "confidence": conf, "response": resp}

    new_calls = 0
    if live_indices:
        live_temps = [temps[i] for i in live_indices]
        if max_workers > 1 and len(live_temps) > 1:
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                results = list(pool.map(_run_live, live_temps))
        else:
            results = [_run_live(t) for t in live_temps]
        for idx, res in zip(live_indices, results):
            t = temps[idx]
            per_call[idx] = {
                "temperature": t,
                "hallucinated": res["hallucinated"],
                "confidence": res["confidence"],
                "response": res["response"],
                "cached": False,
            }
            key = cache_key(transcript, t)
            with cache_lock:
                cache[key] = {
                    "hallucinated": res["hallucinated"],
                    "confidence": res["confidence"],
                    "response": res["response"],
                    "temperature": t,
                }
            new_calls += 1
            if cache_path is not None and new_calls % save_every == 0:
                with cache_lock:
                    save_cache(cache_path, dict(cache))

    # Final cache save if any new calls were made (ensures resumability on interrupt)
    if cache_path is not None and new_calls > 0:
        with cache_lock:
            save_cache(cache_path, dict(cache))

    agg = aggregate_ensemble(per_call)
    agg["transcript_hash"] = transcript_hash(transcript)
    agg["n_cache_hits"] = sum(1 for c in per_call if c.get("cached"))
    agg["n_new_calls"] = new_calls
    return agg


# ======================================================================================
# Real backend: local deepseek-r1 via ollama (offline; lazy)
# ======================================================================================
def ollama_llm(
    model: str = "deepseek-r1:7b",
    num_predict: int = 500,
    host: str = "http://localhost:11434",
    timeout: int = 300,
) -> LLMFn:
    """Return an LLMFn that calls the local ollama HTTP API. The temperature is passed
    per-call (the ensemble varies it). ``num_predict`` caps the response length to keep
    each call ~20s (deepseek-r1 reasoning is verbose)."""

    def call(prompt: str, temperature: float = 0.0) -> str:
        body = json.dumps({
            "model": model, "prompt": prompt, "stream": False,
            "options": {"temperature": float(temperature), "num_predict": num_predict},
        }).encode()
        req = urllib.request.Request(
            f"{host}/api/generate", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp).get("response", "")

    return call


# ======================================================================================
# Calibration + statistics (pure; unit tested)
# ======================================================================================
def calibrate_threshold(
    neg_scores: list[float],
    pos_scores_mode_s: list[float],
    pos_scores_all_halluc: list[float],
    target_spec: float = TARGET_SPECIFICITY,
) -> dict[str, Any]:
    """Calibrate a 'flag if score >= threshold' operating point at >= target_spec
    specificity (measured on neg_scores = non-hallucinated). Among operating points
    meeting the specificity floor, keep the one with maximal Mode S sensitivity
    (tiebreak: all-hallucinated sensitivity, then specificity).

    The score is the yes-vote-fraction (or n-gram KL); higher = more likely
    hallucination. This is one-sided (high = hallucination), unlike RQ19's two-sided
    calibration, because both the LLM yes-vote-fraction and n-gram KL are
    directional by construction.
    """
    n_neg = len(neg_scores)
    n_ms = len(pos_scores_mode_s)
    n_ah = len(pos_scores_all_halluc)
    candidates = sorted(set(neg_scores) | set(pos_scores_mode_s) | set(pos_scores_all_halluc))
    best: dict[str, Any] | None = None
    for t in candidates:
        fp = sum(1 for s in neg_scores if s >= t - EPS)
        tp_ms = sum(1 for s in pos_scores_mode_s if s >= t - EPS)
        tp_ah = sum(1 for s in pos_scores_all_halluc if s >= t - EPS)
        spec = 1.0 - (fp / n_neg) if n_neg else 1.0
        sens_ms = (tp_ms / n_ms) if n_ms else 0.0
        sens_ah = (tp_ah / n_ah) if n_ah else 0.0
        if spec < target_spec - EPS:
            continue
        cand = {
            "threshold": float(t), "specificity": float(spec),
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
            "threshold": float("inf"), "specificity": 1.0,
            "sensitivity_mode_s": 0.0, "sensitivity_all_hallucinated": 0.0,
            "tp_mode_s": 0, "fp": 0, "tn": int(n_neg), "fn_mode_s": int(n_ms),
            "tp_all_hallucinated": 0, "fn_all_hallucinated": int(n_ah),
        }
    return best


def flag_at(score: float, threshold: float) -> bool:
    """Apply a one-sided operating point: flag if score >= threshold."""
    return score >= threshold - EPS


def bootstrap_ci(
    scores: np.ndarray, labels: np.ndarray, threshold: float,
    metric: str = "sensitivity", n_boot: int = N_BOOT, seed: int = SEED,
) -> tuple[float, float]:
    """Bootstrap 95% CI for sensitivity (= P(flag | label==1)) or specificity
    (= P(not flag | label==0)) with a FIXED threshold. 10,000 resamples, seed=42."""
    rng = np.random.default_rng(seed)
    n = len(scores)
    flags = (scores >= threshold - EPS)
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


def ceiling_analysis(
    neg_scores: list[float],
    pos_scores_mode_s: list[float],
    spec_floors: list[float],
) -> list[dict[str, Any]]:
    """Max Mode S sensitivity achievable at specificity >= each floor (one-sided high)."""
    n_neg = len(neg_scores)
    n_ms = len(pos_scores_mode_s)
    candidates = sorted(set(neg_scores) | set(pos_scores_mode_s))
    out: list[dict[str, Any]] = []
    for floor in spec_floors:
        best_sens = 0.0
        best_t = float("inf")
        best_spec = 1.0
        for t in candidates:
            fp = sum(1 for s in neg_scores if s >= t - EPS)
            tp_ms = sum(1 for s in pos_scores_mode_s if s >= t - EPS)
            spec = 1.0 - (fp / n_neg) if n_neg else 1.0
            sens = (tp_ms / n_ms) if n_ms else 0.0
            if spec >= floor - EPS and sens > best_sens + EPS:
                best_sens = sens
                best_t = float(t)
                best_spec = spec
        out.append({
            "specificity_floor": floor,
            "max_sensitivity_mode_s": round(best_sens, 6),
            "threshold": round(best_t, 6),
            "achieved_specificity": round(best_spec, 6),
        })
    return out
