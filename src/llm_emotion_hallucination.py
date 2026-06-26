"""RQ36: LLM emotion reading from hallucinated transcripts (experimental/frontier).

Thread 3 of the project established that a local LLM (deepseek-r1:7b) reads implicit
emotion ~7x better than a lexicon. The objective-aware decoupled router routes text by
ASR signal and emotion read from the *separated* track. This module asks the safety
question those studies left open: **what happens when the transcript the LLM reads
emotion from is itself hallucinated?** If the LLM reads emotion from hallucinated text,
the emotion-routing signal is reading noise. If the LLM can instead *detect* that the
text is unreliable, that self-knowledge is a safety mechanism for emotion-gated routing.

This module is the testable helper layer (pure data loading, prompt construction,
response parsing, statistics). The driver / orchestration (ollama calls, caching,
result assembly) lives in
``results/frontier/llm_emotion_hallucination/llm_emotion_hallucination_analysis.py``.
Unit tests: ``tests/test_llm_emotion_hallucination.py``.

Hypotheses (RQ36)
-----------------
- H36a: LLM emotion readings on hallucinated transcripts have higher uncertainty
  (confidence variance) than on clean. Success: F-statistic > 2.0. Kill: F <= 2.0.
- H36b: LLM can classify transcripts as "reliable" vs "unreliable" with AUC > 0.80.
  Kill: AUC <= 0.80. (The LLM's own ``reliable`` field is the classifier; the label is
  the ground-truth hallucination flag.)
- H36c: LLM emotion readings on Mode S (monoscript-Chinese hallucinations that escape
  every surface detector, RQ19) are indistinguishable from clean. Success: Mode S
  mean confidence within 1 SD of the clean mean. Kill: outside 1 SD.

Data sources
------------
- AISHELL-4 (primary, has Mode S): ``rq1_aishell4_validation_results.json`` — 77
  windows. Hallucination label = ``always_separated_cpwer > 1.0`` (37 hallucinated =
  2 Mode S + 35 diverse; 40 clean). Mode S window ids = [22, 30] (from RQ19/RQ29).
  Transcript = concatenated ``separated_text_per_speaker`` (the track the
  objective-aware router reads emotion from).
- Gold benchmark (secondary): ``gold_track_texts.json`` (decoded sep2 text) joined with
  ``separation_tax/phase_curve.csv`` (``cer_sep2`` for the label). Hallucination label =
  ``cer_sep2 > 1.0``. NOTE: the task brief named ``causal_hallucination_probe/
  probe_rows.csv`` as the gold source, but that file stores only reduced metrics, not
  decoded text; ``gold_track_texts.json`` is the project's decoded gold-text cache and
  is the faithful substitute. This substitution is documented in FINDINGS.md.

Labels: experimental/frontier (statistical layer); the LLM emotion readings themselves
are qualitative/demo (LLM judgments, not ground truth). CER / cpWER are post-hoc only
and never a routing input.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Callable

import numpy as np
from scipy import stats  # type: ignore[import-untyped]

# --------------------------------------------------------------------------- constants
CATASTROPHIC_CPWER = 1.0  # AISHELL-4 hallucination threshold (cpWER > 1.0 => insertions dominate)
GOLD_CER_CATASTROPHIC = 1.0  # gold sep2 CER threshold (matches the probe's catastrophic definition)
MODE_S_WINDOW_IDS = [22, 30]  # the 2 monoscript-Chinese hallucinations (RQ19/RQ29)
OLLAMA_MODEL = "deepseek-r1:7b"
EMOTION_CATEGORIES = [
    "neutral",
    "happy",
    "angry",
    "sad",
    "surprised",
    "fearful",
    "disgusted",
]

PROMPT_TEMPLATE = (
    "You are an emotion analysis system. Read the following meeting speech "
    "transcript and assess the speaker's emotional state.\n\n"
    "Transcript:\n{text}\n\n"
    "Respond with a JSON object:\n"
    '{{"emotion": "neutral/happy/angry/sad/surprised/fearful/disgusted",\n'
    ' "arousal": 1-5 (1=calm, 5=excited),\n'
    ' "valence": 1-5 (1=negative, 5=positive),\n'
    ' "confidence": 0.0-1.0,\n'
    ' "reliable": true/false (is this transcript reliable enough for emotion reading?)\n'
    "}}"
)


# ----------------------------------------------------------------- prompt construction
def build_prompt(transcript: str) -> str:
    """Build the emotion-reading prompt for the LLM."""
    return PROMPT_TEMPLATE.format(text=transcript)


# --------------------------------------------------------------- response parsing
def _strip_think(raw: str) -> str:
    """Remove <think>...</think> reasoning blocks emitted by deepseek-r1."""
    return re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL | re.IGNORECASE)


def _extract_json_object(text: str) -> str | None:
    """Extract the first balanced ``{...}`` substring from text. Returns None if absent."""
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
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _defaults() -> dict[str, Any]:
    """Safe default emotion dict for unparsable responses (fail-open on reliability)."""
    return {
        "emotion": "neutral",
        "arousal": 3,
        "valence": 3,
        "confidence": 0.5,
        "reliable": True,  # fail-open: assume reliable when we cannot tell
        "parsed_ok": False,
    }


def parse_llm_response(raw: str) -> dict[str, Any]:
    """Parse a deepseek-r1 emotion-reading response into a typed dict.

    Handles (a) JSON after a ``<think>`` reasoning block, (b) code-fenced JSON,
    (c) bare JSON, and (d) malformed text via per-field regex fallback. Always
    returns a dict with keys ``emotion, arousal, valence, confidence, reliable,
    parsed_ok``. ``parsed_ok`` is True only when strict JSON parsing succeeded.
    Scalar fields are clamped to their valid ranges.
    """
    if not raw or not raw.strip():
        return _defaults()
    body = _strip_think(raw)
    # Strip markdown code fences if present.
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", body, flags=re.DOTALL | re.IGNORECASE)
    json_str: str | None = None
    if fenced:
        json_str = fenced.group(1)
    else:
        json_str = _extract_json_object(body)

    out = _defaults()
    parsed = False
    if json_str:
        try:
            obj = json.loads(json_str)
            if isinstance(obj, dict):
                out["emotion"] = str(obj.get("emotion", out["emotion"])).strip().lower()
                out["arousal"] = int(round(float(obj.get("arousal", out["arousal"]))))
                out["valence"] = int(round(float(obj.get("valence", out["valence"]))))
                out["confidence"] = float(obj.get("confidence", out["confidence"]))
                out["reliable"] = bool(obj.get("reliable", out["reliable"]))
                parsed = True
        except (ValueError, TypeError):
            parsed = False

    if not parsed:
        # Regex fallback: recover scalar fields from loose text.
        m_emo = re.search(r'"?emotion"?\s*[:=]\s*"?([a-zA-Z]+)"?', body, flags=re.IGNORECASE)
        if m_emo:
            out["emotion"] = m_emo.group(1).strip().lower()
        m_a = re.search(r'"?arousal"?\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)', body, flags=re.IGNORECASE)
        if m_a:
            try:
                out["arousal"] = int(round(float(m_a.group(1))))
            except ValueError:
                pass
        m_v = re.search(r'"?valence"?\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)', body, flags=re.IGNORECASE)
        if m_v:
            try:
                out["valence"] = int(round(float(m_v.group(1))))
            except ValueError:
                pass
        m_c = re.search(r'"?confidence"?\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)', body, flags=re.IGNORECASE)
        if m_c:
            try:
                out["confidence"] = float(m_c.group(1))
            except ValueError:
                pass
        m_r = re.search(r'"?reliable"?\s*[:=]\s*(true|false)', body, flags=re.IGNORECASE)
        if m_r:
            out["reliable"] = m_r.group(1).strip().lower() == "true"

    # Normalise / clamp.
    if out["emotion"] not in EMOTION_CATEGORIES:
        out["emotion"] = "neutral"
    out["arousal"] = int(_clamp(out["arousal"], 1, 5))
    out["valence"] = int(_clamp(out["valence"], 1, 5))
    out["confidence"] = round(_clamp(out["confidence"], 0.0, 1.0), 6)
    out["parsed_ok"] = parsed
    return out


# ------------------------------------------------------------------- hashing / cache
def transcript_hash(text: str) -> str:
    """Stable short hash of a transcript for cache keys (sha1, first 16 hex)."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def load_cache(path: Path) -> dict[str, Any]:
    """Load the LLM response cache; empty dict if missing or malformed."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_cache(path: Path, cache: dict[str, Any]) -> None:
    """Atomically write the cache as UTF-8 JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


# ----------------------------------------------------------------- ollama invocation
def call_ollama(
    prompt: str, model: str = OLLAMA_MODEL, timeout: int = 120
) -> str:
    """Call ``ollama run <model>`` with the prompt on stdin; return raw stdout.

    Raises on non-zero exit or timeout. The driver wraps this in try/except to
    produce a negative-cache entry on failure.
    """
    r = subprocess.run(
        ["ollama", "run", model],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if r.returncode != 0:
        raise RuntimeError(f"ollama exited {r.returncode}: {r.stderr.strip()[:200]}")
    return r.stdout


def get_llm_emotion(
    transcript: str,
    cache: dict[str, Any],
    call_fn: Callable[[str], str] = call_ollama,
    model: str = OLLAMA_MODEL,
    timeout: int = 120,
) -> dict[str, Any]:
    """Return the parsed emotion dict for ``transcript``, using and updating ``cache``.

    On a cache hit, the cached parsed dict is returned and ``call_fn`` is NOT invoked.
    On a cache miss, ``call_fn(build_prompt(transcript))`` is called; the parsed result
    is stored in ``cache`` under ``transcript_hash(transcript)`` (negative cache on
    failure, so a broken call is not retried forever).
    """
    key = transcript_hash(transcript)
    if key in cache:
        cached = cache[key]
        if isinstance(cached, dict):
            return cached
    # Cache miss: call.
    try:
        raw = call_fn(build_prompt(transcript))
        parsed = parse_llm_response(raw)
        parsed["_raw_preview"] = raw[-200:] if isinstance(raw, str) else ""
    except Exception as e:  # noqa: BLE001 - negative cache any failure
        parsed = _defaults()
        parsed["_error"] = str(e)[:200]
    cache[key] = parsed
    return parsed


# ------------------------------------------------------------------- data loading
def _concat_separated(window: dict[str, Any]) -> str:
    """Concatenate per-speaker separated transcripts (the objective-aware router's
    emotion source track). Empty speakers are skipped."""
    parts = [
        str(t)
        for t in window.get("separated_text_per_speaker", {}).values()
        if t is not None and str(t).strip()
    ]
    return "".join(parts)


def load_aishell4_windows(json_path: Path) -> list[dict[str, Any]]:
    """Load the 77 AISHELL-4 windows into analysis rows.

    Each row: ``{track_id, window_id, source, transcript, always_separated_cpwer,
    hallucinated, mode_s, diverse, num_speakers, overlap_label}``.
    """
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for w in data.get("windows", []):
        wid = w["window_id"]
        sep_cpwer = float(w["always_separated_cpwer"])
        transcript = _concat_separated(w)
        if not transcript.strip():
            # Fallback to mixed_text if separated is empty (rare; keeps the row analyzable).
            transcript = str(w.get("mixed_text", ""))
        halluc = sep_cpwer > CATASTROPHIC_CPWER
        mode_s = wid in MODE_S_WINDOW_IDS
        rows.append(
            {
                "track_id": f"aishell4_w{wid:02d}",
                "window_id": wid,
                "source": "aishell4",
                "transcript": transcript,
                "mixed_text": str(w.get("mixed_text", "")),
                "always_separated_cpwer": sep_cpwer,
                "hallucinated": halluc,
                "mode_s": mode_s,
                "diverse": halluc and not mode_s,
                "num_speakers": int(w.get("num_speakers", 0)),
                "overlap_label": w.get("overlap_label", ""),
            }
        )
    return rows


def load_gold_tracks(
    text_json: Path,
    curve_csv: Path,
    n_clean_control: int = 40,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Load gold benchmark tracks with decoded sep2 text + cer_sep2 label.

    Catastrophic = ``cer_sep2 > GOLD_CER_CATASTROPHIC`` (all included). Clean control =
    a deterministic stride sample of ``n_clean_control`` tracks from the clean pool
    (no randomness in default stride mode; ``seed`` only used if clean pool smaller
    than needed and we fall back to sampling — kept for API stability).

    Each row: ``{track_id, source, transcript, cer_sep2, cr_sep2, hallucinated}``.
    """
    gt = json.loads(Path(text_json).read_text(encoding="utf-8"))
    # Index phase_curve by (con, pro, overlap) -> row.
    pc: dict[tuple[str, str, str], dict[str, str]] = {}
    with Path(curve_csv).open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            key = (
                r["con"].replace(".wav", ""),
                r["pro"].replace(".wav", ""),
                f"{float(r['overlap_ratio']):.2f}",
            )
            pc[key] = r

    cat_rows: list[dict[str, Any]] = []
    clean_rows: list[dict[str, Any]] = []
    for t in gt.get("tracks", []):
        key = (
            t["con"].replace(".wav", ""),
            t["pro"].replace(".wav", ""),
            f"{float(t['overlap_ratio']):.2f}",
        )
        meta = pc.get(key)
        if meta is None:
            continue
        try:
            cer2 = float(meta["cer_sep2"])
            cr2 = float(meta.get("cr_sep2", "0") or "0")
        except (ValueError, KeyError):
            continue
        transcript = str(t.get("sep2_text", "")).strip()
        if not transcript:
            continue
        halluc = cer2 > GOLD_CER_CATASTROPHIC
        row = {
            "track_id": f"gold_{key[0]}_{key[1]}_{key[2]}",
            "source": "gold",
            "con": key[0],
            "pro": key[1],
            "overlap_ratio": float(key[2]),
            "transcript": transcript,
            "cer_sep2": cer2,
            "cr_sep2": cr2,
            "hallucinated": halluc,
        }
        (cat_rows if halluc else clean_rows).append(row)

    # Deterministic stride sample of clean controls (no RNG dependence for the default).
    if len(clean_rows) > n_clean_control:
        stride = len(clean_rows) / n_clean_control
        clean_rows = [clean_rows[int(i * stride)] for i in range(n_clean_control)]
    elif len(clean_rows) < n_clean_control:
        # Fall back to RNG sampling with replacement only if stride under-samples.
        rng = np.random.default_rng(seed)
        idx = rng.integers(0, len(clean_rows), size=n_clean_control) if clean_rows else []
        clean_rows = [clean_rows[i] for i in idx]
    return cat_rows + clean_rows


# ----------------------------------------------------------------- lexicon fallback
def lexicon_emotion_metrics(transcript: str) -> dict[str, float]:
    """Lexicon-based emotion fallback (used only if ollama is unavailable).

    Returns ``emotion_word_density`` (emotion-word hits / total chars) and
    ``emotion_diversity`` (unique emotion categories hit / 7), computed via the
    project's ``src.lexical_emotion`` lexicon. These are the metrics the fallback
    compares hallucinated vs clean on.
    """
    from src.lexical_emotion import lexical_emotion  # local import (avoid hard dep)

    if not transcript:
        return {"emotion_word_density": 0.0, "emotion_diversity": 0.0, "length": 0.0}
    e = lexical_emotion(transcript)
    n_chars = max(e.get("length", 0), 1)
    # Count distinct emotion categories touched by the lexicon (pos/neg/high-arousal).
    cats_hit = 0
    if e.get("n_pos", 0) > 0:
        cats_hit += 1
    if e.get("n_neg", 0) > 0:
        cats_hit += 1
    if e.get("n_high_arousal", 0) > 0:
        cats_hit += 1
    hits = e.get("n_pos", 0) + e.get("n_neg", 0) + e.get("n_high_arousal", 0)
    return {
        "emotion_word_density": round(hits / n_chars, 6),
        "emotion_diversity": round(cats_hit / 3.0, 6),  # 3 lexicon categories max
        "length": float(n_chars),
    }


# ----------------------------------------------------------------- statistics
def compute_f_test(
    conf_halluc: list[float], conf_clean: list[float]
) -> dict[str, Any]:
    """F-test of equal variances: F = var(halluc) / var(clean).

    Returns ``{f_stat, p_value, var_halluc, var_clean, df1, df2}``. Safe on empty
    inputs (returns NaN f_stat). Uses the larger-variance numerator convention so
    F >= 1 and the p-value is two-sided.
    """
    a = np.asarray(conf_halluc, dtype=float)
    b = np.asarray(conf_clean, dtype=float)
    a = a[~np.isnan(a)]
    b = b[~np.isnan(b)]
    if len(a) < 2 or len(b) < 2:
        return {
            "f_stat": float("nan"),
            "p_value": float("nan"),
            "var_halluc": float(np.var(a, ddof=1)) if len(a) >= 2 else 0.0,
            "var_clean": float(np.var(b, ddof=1)) if len(b) >= 2 else 0.0,
            "df1": max(len(a) - 1, 0),
            "df2": max(len(b) - 1, 0),
        }
    va = float(np.var(a, ddof=1))
    vb = float(np.var(b, ddof=1))
    # Directional F per the hypothesis: var(halluc) / var(clean).
    f_directional = va / vb if vb > 0 else float("nan")
    # Two-sided p-value: put the larger variance in the numerator (standard F-test).
    if min(va, vb) <= 0:
        p_value = float("nan")
        f_two_sided = float("nan")
    else:
        f_two_sided = max(va, vb) / min(va, vb)
        try:
            p_value = 2.0 * min(
                float(stats.f.cdf(f_two_sided, len(a) - 1, len(b) - 1)),
                float(stats.f.sf(f_two_sided, len(a) - 1, len(b) - 1)),
            )
            p_value = min(p_value, 1.0)
        except Exception:  # noqa: BLE001
            p_value = float("nan")
    return {
        "f_stat": round(f_directional, 6),
        "p_value": round(float(p_value), 6) if not np.isnan(p_value) else float("nan"),
        "var_halluc": round(va, 6),
        "var_clean": round(vb, 6),
        "df1": len(a) - 1,
        "df2": len(b) - 1,
        "f_two_sided": round(float(f_two_sided), 6) if not np.isnan(f_two_sided) else float("nan"),
    }


def compute_auc(scores: list[float], labels: list[int]) -> float:
    """ROC AUC via the Mann-Whitney U identity (rank-based, tie-aware).

    ``labels``: 1 = positive (e.g. hallucinated), 0 = negative (clean). Higher
    ``scores`` should indicate more positive. Returns 0.5 on degenerate input.
    """
    s = np.asarray(scores, dtype=float)
    y = np.asarray(labels, dtype=int)
    mask = ~np.isnan(s)
    s, y = s[mask], y[mask]
    n_pos = int((y == 1).sum())
    n_neg = int((y == 0).sum())
    if n_pos == 0 or n_neg == 0:
        return 0.5
    ranks = stats.rankdata(s, method="average")  # type: ignore[attr-defined]
    sum_pos_ranks = float(ranks[y == 1].sum())
    u = sum_pos_ranks - n_pos * (n_pos + 1) / 2.0
    return float(u / (n_pos * n_neg))


def mode_s_comparison(
    mode_s_conf: list[float], clean_conf: list[float]
) -> dict[str, Any]:
    """H36c: are Mode S confidence values within 1 SD of the clean mean?

    Returns ``{mode_s_mean, mode_s_n, clean_mean, clean_sd, within_1sd,
    max_deviation_sd}``. ``within_1sd`` is True iff EVERY Mode S value is within
    1 SD of the clean mean (strict reading of "indistinguishable"). If clean_sd is
    0, any deviation counts as outside.
    """
    ms = np.asarray([x for x in mode_s_conf if not np.isnan(x)], dtype=float)
    cl = np.asarray([x for x in clean_conf if not np.isnan(x)], dtype=float)
    if len(cl) == 0:
        return {
            "mode_s_mean": float("nan") if len(ms) == 0 else float(np.mean(ms)),
            "mode_s_n": int(len(ms)),
            "clean_mean": float("nan"),
            "clean_sd": float("nan"),
            "within_1sd": True,  # vacuously: cannot reject
            "max_deviation_sd": float("nan"),
        }
    clean_mean = float(np.mean(cl))
    clean_sd = float(np.std(cl, ddof=1)) if len(cl) >= 2 else 0.0
    if len(ms) == 0:
        return {
            "mode_s_mean": float("nan"),
            "mode_s_n": 0,
            "clean_mean": clean_mean,
            "clean_sd": clean_sd,
            "within_1sd": True,
            "max_deviation_sd": float("nan"),
        }
    if clean_sd <= 0:
        devs = np.abs(ms - clean_mean)
        within = bool(np.all(devs == 0))
        max_dev_sd = float(np.max(devs)) if len(devs) else 0.0
    else:
        devs_sd = np.abs(ms - clean_mean) / clean_sd
        within = bool(np.all(devs_sd <= 1.0))
        max_dev_sd = float(np.max(devs_sd))
    return {
        "mode_s_mean": round(float(np.mean(ms)), 6),
        "mode_s_n": int(len(ms)),
        "clean_mean": round(clean_mean, 6),
        "clean_sd": round(clean_sd, 6),
        "within_1sd": within,
        "max_deviation_sd": round(max_dev_sd, 6),
    }


def evaluate_hypotheses(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate H36a / H36b / H36c from analysis rows.

    Each row must have: ``dataset, hallucinated, mode_s, confidence, reliable,
    parsed_ok``. Only successfully parsed rows (``parsed_ok`` truthy) contribute to
    the confidence-based tests (H36a/H36c); H36b uses the ``reliable`` field for all
    rows (a failure default of reliable=True counts as a clean prediction).
    """
    # AISHELL-4 is the primary dataset for all three hypotheses (Mode S lives there).
    aishell = [r for r in rows if r.get("source") == "aishell4" or r.get("dataset") == "aishell4"]
    if not aishell:
        aishell = rows  # fall back to whatever is passed

    parsed = [r for r in aishell if r.get("parsed_ok")]
    conf_halluc = [float(r["confidence"]) for r in parsed if r.get("hallucinated") and r.get("confidence") is not None]
    conf_clean = [float(r["confidence"]) for r in parsed if not r.get("hallucinated") and r.get("confidence") is not None]

    # H36a: variance comparison.
    f = compute_f_test(conf_halluc, conf_clean)
    h36a_supported = f["f_stat"] > 2.0 if not np.isnan(f["f_stat"]) else False

    # H36b: reliable field as classifier. Label = hallucinated (1) / clean (0).
    # Score = 1 - reliable (unreliable -> higher score -> predicts hallucinated).
    labels_b = [1 if r.get("hallucinated") else 0 for r in aishell]
    scores_b = [0.0 if r.get("reliable") else 1.0 for r in aishell]
    auc_reliable = compute_auc(scores_b, labels_b)
    # Secondary continuous score: 1 - confidence (lower confidence -> predicts hallucinated).
    scores_conf = [1.0 - float(r.get("confidence") or 0.5) for r in aishell]
    auc_confidence = compute_auc(scores_conf, labels_b)
    h36b_supported = auc_reliable > 0.80

    # H36c: Mode S vs clean.
    mode_s_conf = [float(r["confidence"]) for r in parsed if r.get("mode_s") and r.get("confidence") is not None]
    ms = mode_s_comparison(mode_s_conf, conf_clean)
    h36c_supported = ms["within_1sd"]

    return {
        "h36a": {
            "statement": "LLM confidence variance on hallucinated > clean (F > 2.0)",
            "f_stat": f["f_stat"],
            "p_value": f["p_value"],
            "var_halluc": f["var_halluc"],
            "var_clean": f["var_clean"],
            "df1": f["df1"],
            "df2": f["df2"],
            "n_halluc": len(conf_halluc),
            "n_clean": len(conf_clean),
            "supported": bool(h36a_supported),
        },
        "h36b": {
            "statement": "LLM `reliable` field classifies hallucinated vs clean (AUC > 0.80)",
            "auc_reliable": round(auc_reliable, 6),
            "auc_confidence_secondary": round(auc_confidence, 6),
            "n": len(aishell),
            "supported": bool(h36b_supported),
        },
        "h36c": {
            "statement": "Mode S confidence within 1 SD of clean mean (indistinguishable)",
            "mode_s_mean": ms["mode_s_mean"],
            "mode_s_n": ms["mode_s_n"],
            "clean_mean": ms["clean_mean"],
            "clean_sd": ms["clean_sd"],
            "max_deviation_sd": ms["max_deviation_sd"],
            "within_1sd": ms["within_1sd"],
            "supported": bool(h36c_supported),
        },
    }
