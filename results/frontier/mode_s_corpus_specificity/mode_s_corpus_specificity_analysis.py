"""RQ40: Mode S corpus specificity — does the monoscript hallucination appear
outside AISHELL-4?

REANALYSIS ONLY — no Whisper / no ASR model is run. This script reads existing
decoded transcripts and CER labels from three corpora (AISHELL-4 external
sanity-check, gold benchmark, synthetic silver) and tests whether RQ19's Mode S
hallucination pattern (monoscript-Chinese near-duplicate of the mixed decode)
appears in any gold or silver track, and whether RQ34's char 3-gram KL
divergence detector (threshold 3.30, calibrated on AISHELL-4 non-hallucinated)
flags any gold/silver Mode S track.

Label: experimental/frontier. Closes #953.

Background
----------
Mode S (monoscript-Chinese hallucination) was identified on AISHELL-4 (windows
22, 30 in meeting M_R003S02C01). RQ19/RQ22/RQ23/RQ28/RQ33 all attempted to
detect it; RQ34's n-gram KL divergence was the first to catch it at 90%
specificity. But we don't know if Mode S is AISHELL-4-specific or appears in
the gold/silver benchmarks too. RQ26 showed hallucination mode distributions
are disjoint between gold and AISHELL-4 (chi2=305, p=5.4e-67), but Mode S was
not explicitly searched for in gold.

Hypotheses
----------
- H40a: Mode S (hallucinated AND lang_id_entropy < 0.409 AND length_ratio < 2.0
  AND cr < 2.4 AND content_similarity to mixed > 0.8) appears in at least 1
  gold/silver track. Success: >=1 Mode S case found.
- H40b: RQ34's n-gram KL divergence detector (threshold 3.30, calibrated on
  AISHELL-4 non-hallucinated) flags any gold/silver Mode S tracks. Success:
  >=1 detection.
- H40c: Mode S prevalence on gold/silver is < 5% of hallucinated tracks (vs
  5.4% on AISHELL-4 = 2/37). Success: prevalence < 5%.

Method
------
1. Load AISHELL-4 (77 windows, calibration corpus), gold (600 per-speaker
   separated tracks), and synthetic silver (25 samples).
2. For each track compute the RQ19 Mode S criteria: hallucinated label,
   lang_id_entropy, length_ratio, cr, content_similarity to mixed.
   - content_similarity = token containment = |tokens(sep) ∩ tokens(mix)| /
     |tokens(sep)| (the metric that exceeds 0.8 on both AISHELL-4 Mode S
     windows 22 and 30; verified empirically).
   - Gold tracks have no cached mixed_text (only sep1_text / sep2_text from
     RQ21's decode_gold_tracks.py). For gold we apply the 3 computable criteria
     (hallucinated AND lang_id < 0.409 AND cr < 2.4) and report "Mode S
     candidates (3-criterion)"; the length_ratio and content_similarity gates
     are noted as not-computable for gold.
3. Implement RQ34's char 3-gram KL divergence detector:
   - char 3-gram frequency distribution per track (whitespace-stripped).
   - reference distribution = aggregate char 3-gram counts of non-hallucinated
     tracks from the SAME corpus (per-corpus reference, matching the Method
     spec).
   - KL divergence D(track || reference) in bits, add-1 Laplace smoothing on
     the reference so Q(x) > 0 for all x.
   - threshold 3.30 (fixed, calibrated on AISHELL-4 non-hallucinated to 90%
     specificity per the RQ34 spec).
4. Report Mode S count per corpus, KL scores, detector performance, and
   hypothesis verdicts.

Surface-detector primitives (compression_ratio, language_id_entropy,
script_category, tokenize) are lifted verbatim from RQ19/RQ21 so the Mode S
definition is directly comparable. Pure reanalysis: numpy + stdlib only.
"""
from __future__ import annotations

import csv
import json
import math
import unicodedata
import zlib
from pathlib import Path
from typing import Any

import numpy as np

# --------------------------------------------------------------------------- paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
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
SILVER_CER_CSV = (
    PROJECT_ROOT / "results" / "tables" / "synthetic_cer_results.csv"
)
SILVER_MIXED_DIR = (
    PROJECT_ROOT / "results" / "synthetic_transcripts_raw"
)
SILVER_SEP_DIR = (
    PROJECT_ROOT / "results" / "synthetic_transcripts_speaker"
)
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "mode_s_corpus_specificity"
OUT_CSV = OUT_DIR / "mode_s_corpus_specificity_results.csv"
OUT_JSON = OUT_DIR / "mode_s_corpus_specificity_results.json"

# ------------------------------------------------------------------ thresholds
# Mode S definition (RQ19 + RQ40 content_similarity gate)
LANG_ID_ENTROPY_THRESHOLD = 0.409   # RQ13 >=90%-specificity operating point
LENGTH_RATIO_THRESHOLD = 2.0        # RQ14 insertion_dominated proxy
CR_THRESHOLD = 2.4                  # Whisper default / RQ14 repetition guard
CONTENT_SIMILARITY_THRESHOLD = 0.8  # RQ40: token containment > 0.8

# Hallucination labels (per corpus)
AISHELL4_CPWER_HALLUC = 1.0         # cpWER > 1.0 => hallucination (AISHELL-4)
GOLD_CER_HALLUC = 0.5               # cer > 0.5 => hallucination (gold, RQ40 spec)
SILVER_CER_HALLUC = 0.5             # cer > 0.5 => hallucination (silver, RQ40 spec)

# RQ34 char 3-gram KL divergence detector
KL_THRESHOLD = 3.30                 # bits; calibrated on AISHELL-4 non-hallucinated
KL_NGRAM = 3                        # char 3-grams
KL_SMOOTHING = 1.0                  # add-1 Laplace smoothing on reference Q

# AISHELL-4 reference prevalence (for H40c comparison)
AISHELL4_MODE_S_COUNT = 2           # windows 22, 30
AISHELL4_HALLUC_COUNT = 37
AISHELL4_MODE_S_PREVALENCE = AISHELL4_MODE_S_COUNT / AISHELL4_HALLUC_COUNT  # 5.4%

SEED = 42
EPS = 1e-9

CJK_SCRIPTS = {"Han", "Hiragana", "Katakana", "Hangul"}


# ----------------------------------------------------------------- CR primitive
def compression_ratio(text: str) -> float:
    """Whisper-style compression ratio: len(utf8 bytes) / len(zlib-compressed bytes).

    Matches ``whisper.audio.compression_ratio`` and RQ12/RQ13/RQ16/RQ19/RQ21.
    Returns 0.0 for empty/whitespace text. High CR (>~2.4) = repetitive loop."""
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


def tokenize(text: str) -> list[str]:
    """Script-aware tokeniser (RQ13 verbatim).

    CJK characters become individual character-tokens; Latin/other runs split on
    whitespace."""
    if not text:
        return []
    tokens: list[str] = []
    buf: list[str] = []
    for ch in text:
        if ch.isspace():
            if buf:
                tokens.append("".join(buf))
                buf = []
            continue
        sc = script_category(ch)
        if sc in CJK_SCRIPTS:
            if buf:
                tokens.append("".join(buf))
                buf = []
            tokens.append(ch)
        else:
            buf.append(ch)
    if buf:
        tokens.append("".join(buf))
    return tokens


# ------------------------------------------------------------- n-gram utilities
def char_ngrams(text: str, n: int) -> list[str]:
    """List of character n-grams (whitespace stripped). Returns empty list if too short.

    Returns a LIST (not set) so frequency counts can be computed for KL divergence."""
    s = "".join(text.split())
    if len(s) < n:
        return [s] if s else []
    return [s[i:i + n] for i in range(len(s) - n + 1)]


def ngram_counts(text: str, n: int) -> dict[str, int]:
    """Frequency counts of character n-grams in text (whitespace stripped)."""
    counts: dict[str, int] = {}
    for g in char_ngrams(text, n):
        counts[g] = counts.get(g, 0) + 1
    return counts


# ------------------------------------------------------------- content similarity
def token_containment(sep: str, mix: str) -> float:
    """Token containment = |tokens(sep) ∩ tokens(mix)| / |tokens(sep)|.

    Measures what fraction of the separated text's token vocabulary appears in
    the mixed text. For Mode S (near-duplicate of mixed), this is high (> 0.8).
    For diverse hallucination (gibberish), this is low. Returns 0.0 if sep has
    no tokens."""
    sep_toks = set(tokenize(sep))
    mix_toks = set(tokenize(mix))
    if not sep_toks:
        return 0.0
    return len(sep_toks & mix_toks) / len(sep_toks)


# ------------------------------------------------------------- KL divergence (RQ34)
def kl_divergence_bits(
    track_counts: dict[str, int],
    ref_counts: dict[str, int],
    smoothing: float = KL_SMOOTHING,
) -> float:
    """KL divergence D(track || reference) in bits, with add-smoothing on Q.

    P(x) = track_counts[x] / track_total  (no smoothing on P; P's support is
    what it is).
    Q(x) = (ref_counts.get(x, 0) + smoothing) / (ref_total + smoothing * |V_ref|)
    where V_ref = ref vocabulary. For x not in V_ref, Q(x) = smoothing /
    (ref_total + smoothing * |V_ref|) > 0, so log2(P/Q) is finite.

    This is the standard add-smoothing approach for KL with out-of-vocabulary
    n-grams. Returns 0.0 if either distribution is empty."""
    track_total = sum(track_counts.values())
    ref_total = sum(ref_counts.values())
    if track_total <= 0 or ref_total <= 0:
        return 0.0
    ref_vocab_size = len(ref_counts)
    # smoothed denominator for Q: total + smoothing * |V_ref|
    q_denom = ref_total + smoothing * ref_vocab_size
    if q_denom <= 0:
        return 0.0
    kl = 0.0
    for gram, c in track_counts.items():
        p = c / track_total
        if p <= 0:
            continue
        q = (ref_counts.get(gram, 0) + smoothing) / q_denom
        if q <= 0:
            continue
        kl += p * math.log2(p / q)
    return kl


def build_reference_counts(
    texts: list[str], n: int = KL_NGRAM
) -> dict[str, int]:
    """Aggregate char n-gram counts across a list of texts (reference distribution)."""
    ref: dict[str, int] = {}
    for t in texts:
        for g, c in ngram_counts(t, n).items():
            ref[g] = ref.get(g, 0) + c
    return ref


def kl_detector_score(
    track_text: str,
    ref_counts: dict[str, int],
    n: int = KL_NGRAM,
    smoothing: float = KL_SMOOTHING,
) -> float:
    """Compute the RQ34 KL divergence score for a single track against a reference."""
    track_counts = ngram_counts(track_text, n)
    return kl_divergence_bits(track_counts, ref_counts, smoothing)


def calibrate_kl_specificity(
    neg_scores: list[float], threshold: float
) -> float:
    """Specificity = P(score < threshold | non-hallucinated). Fraction of
    non-hallucinated tracks NOT flagged by the KL detector at the given threshold."""
    if not neg_scores:
        return 1.0
    fp = sum(1 for s in neg_scores if s >= threshold - EPS)
    return 1.0 - fp / len(neg_scores)


def calibrate_threshold_for_target_specificity(
    neg_scores: list[float], pos_scores: list[float], target_spec: float = 0.90
) -> dict[str, Any]:
    """Find the threshold with specificity >= target_spec and maximal sensitivity.

    Candidate thresholds = all unique scores. Flag = score >= threshold. Among
    operating points with specificity >= target_spec, keep the one with maximal
    sensitivity (tiebreak: maximal specificity). Returns the threshold, achieved
    specificity, and sensitivity. If no threshold meets the target, returns the
    highest threshold (flag nothing, 100% specificity, 0% sensitivity)."""
    n_neg = len(neg_scores)
    n_pos = len(pos_scores)
    if n_neg == 0:
        return {"threshold": float("inf"), "specificity": 1.0, "sensitivity": 0.0,
                "tp": 0, "fp": 0, "tn": 0, "fn": n_pos}
    candidates = sorted(set(neg_scores) | set(pos_scores))
    best: dict[str, Any] | None = None
    for t in candidates:
        fp = sum(1 for s in neg_scores if s >= t - EPS)
        tp = sum(1 for s in pos_scores if s >= t - EPS)
        spec = 1.0 - fp / n_neg
        sens = tp / n_pos if n_pos > 0 else 0.0
        if spec < target_spec - EPS:
            continue
        if (best is None
            or sens > best["sensitivity"] + EPS
            or (abs(sens - best["sensitivity"]) <= EPS and spec > best["specificity"] + EPS)):
            best = {"threshold": float(t), "specificity": float(spec),
                    "sensitivity": float(sens), "tp": int(tp), "fp": int(fp),
                    "tn": int(n_neg - fp), "fn": int(n_pos - tp)}
    if best is None:
        t = max(candidates) + 1.0 if candidates else 0.0
        best = {"threshold": float(t), "specificity": 1.0, "sensitivity": 0.0,
                "tp": 0, "fp": 0, "tn": int(n_neg), "fn": int(n_pos)}
    return best


# ------------------------------------------------------------- data loaders
def load_aishell4_tracks() -> list[dict[str, Any]]:
    """Load 77 AISHELL-4 windows as tracks.

    Each window becomes one track. Separated text = concatenation of per-speaker
    separated texts (RQ23 convention). Mixed text = mixed_text field.
    Hallucination label: always_separated_cpwer > 1.0."""
    data = json.loads(AISHELL4_JSON.read_text(encoding="utf-8"))
    tracks: list[dict[str, Any]] = []
    for w in data["windows"]:
        sep_cpwer = float(w["always_separated_cpwer"])
        sep_texts = w.get("separated_text_per_speaker", {})
        non_empty = [str(t) for t in sep_texts.values() if t and str(t).strip()]
        sep_concat = "".join(non_empty)
        mix_text = str(w.get("mixed_text", "") or "")
        ent = max([language_id_entropy(t) for t in non_empty], default=0.0)
        cr = compression_ratio(sep_concat)
        sep_len = float(w.get("separated_total_length", len(sep_concat)) or 0)
        mix_len = float(w.get("mixed_text_length", len(mix_text)) or 0)
        lr = sep_len / max(1.0, mix_len)
        cs = token_containment(sep_concat, mix_text) if mix_text else 0.0
        halluc = sep_cpwer > AISHELL4_CPWER_HALLUC
        tracks.append({
            "corpus": "aishell4",
            "track_id": str(w["window_id"]),
            "sep_text": sep_concat,
            "mix_text": mix_text,
            "hallucinated": bool(halluc),
            "cer": sep_cpwer,
            "lang_id_entropy": ent,
            "cr": cr,
            "length_ratio": lr,
            "content_similarity": cs,
            "has_mixed_text": bool(mix_text),
            "num_speakers": w.get("num_speakers", 0),
        })
    return tracks


def load_gold_tracks() -> list[dict[str, Any]]:
    """Load 600 gold tracks (300 conditions x sep1/sep2).

    Per-track separated text from gold_track_texts.json (RQ21). CER from
    phase_curve.csv (greedy config). Hallucination label: cer > 0.5 (RQ40 spec).
    No mixed_text is cached for gold (only sep1_text / sep2_text) —
    has_mixed_text = False, length_ratio and content_similarity are not computable."""
    cache = json.loads(GOLD_TEXT_JSON.read_text(encoding="utf-8"))
    # index phase_curve greedy rows by (con, pro, overlap_ratio)
    curve_rows: dict[tuple[str, str, float], dict[str, str]] = {}
    with GOLD_CURVE_CSV.open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if r["config"] != "greedy":
                continue
            key = (r["con"], r["pro"], float(r["overlap_ratio"]))
            curve_rows[key] = r

    tracks: list[dict[str, Any]] = []
    for t in cache["tracks"]:
        key = (t["con"], t["pro"], float(t["overlap_ratio"]))
        row = curve_rows.get(key)
        if row is None:
            continue
        for arm, text_key, cer_key in [
            ("sep1", "sep1_text", "cer_sep1"),
            ("sep2", "sep2_text", "cer_sep2"),
        ]:
            text = str(t[text_key])
            cer = float(row[cer_key])
            ent = language_id_entropy(text)
            cr = compression_ratio(text)
            halluc = cer > GOLD_CER_HALLUC
            track_id = (
                f"{Path(t['con']).stem}_{Path(t['pro']).stem}"
                f"_r{t['overlap_ratio']}_{arm}"
            )
            tracks.append({
                "corpus": "gold",
                "track_id": track_id,
                "sep_text": text,
                "mix_text": "",  # not cached for gold
                "hallucinated": bool(halluc),
                "cer": cer,
                "lang_id_entropy": ent,
                "cr": cr,
                "length_ratio": float("nan"),  # not computable without mixed_text
                "content_similarity": float("nan"),
                "has_mixed_text": False,
                "num_speakers": 2,
            })
    return tracks


def load_silver_tracks() -> list[dict[str, Any]]:
    """Load 25 synthetic silver tracks.

    Each sample becomes one track. Separated text = concatenation of per-speaker
    segment texts (stripped of [SPEAKER_N] tags). Mixed text = mixed_whisper
    decode. CER from synthetic_cer_results.csv (separated_whisper method).
    Hallucination label: cer > 0.5 (RQ40 spec)."""
    # index CER rows by sample_id for separated_whisper
    cer_by_sid: dict[str, float] = {}
    with SILVER_CER_CSV.open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if r["method"] != "separated_whisper":
                continue
            sid = r.get("sample_id") or r.get("\ufeffsample_id", "")
            cer_by_sid[sid] = float(r["cer"])

    tracks: list[dict[str, Any]] = []
    sep_files = sorted(SILVER_SEP_DIR.glob("*_separated_speaker_transcript.json"))
    for sep_path in sep_files:
        sep_data = json.loads(sep_path.read_text(encoding="utf-8"))
        sid = sep_data.get("sample_id", sep_path.stem.replace("_separated_speaker_transcript", ""))
        # extract per-speaker text from segments, strip [SPEAKER_N] tags
        segments = sep_data.get("segments", [])
        sep_texts = []
        for seg in segments:
            t = str(seg.get("text", "")).strip()
            if t:
                sep_texts.append(t)
        sep_concat = "".join(sep_texts)
        # load mixed text
        mixed_path = SILVER_MIXED_DIR / f"{sid}_mixed_whisper.json"
        mix_text = ""
        if mixed_path.exists():
            mix_data = json.loads(mixed_path.read_text(encoding="utf-8"))
            mix_text = str(mix_data.get("text", "") or "")
        cer = cer_by_sid.get(sid, 0.0)
        ent = language_id_entropy(sep_concat)
        cr = compression_ratio(sep_concat)
        sep_len = float(len("".join(sep_concat.split())))
        mix_len = float(len("".join(mix_text.split())))
        lr = sep_len / max(1.0, mix_len)
        cs = token_containment(sep_concat, mix_text) if mix_text else 0.0
        halluc = cer > SILVER_CER_HALLUC
        tracks.append({
            "corpus": "silver",
            "track_id": sid,
            "sep_text": sep_concat,
            "mix_text": mix_text,
            "hallucinated": bool(halluc),
            "cer": cer,
            "lang_id_entropy": ent,
            "cr": cr,
            "length_ratio": lr,
            "content_similarity": cs,
            "has_mixed_text": bool(mix_text),
            "num_speakers": len(segments),
        })
    return tracks


# ------------------------------------------------------------- Mode S labeling
def is_mode_s_full(track: dict[str, Any]) -> bool:
    """Full 5-criterion Mode S definition (RQ19 + RQ40 content_similarity gate).

    hallucinated AND lang_id_entropy < 0.409 AND length_ratio < 2.0
    AND cr < 2.4 AND content_similarity > 0.8.

    Only computable when has_mixed_text = True (length_ratio and
    content_similarity require mixed_text). Returns False if mixed_text is
    unavailable."""
    if not track["hallucinated"]:
        return False
    if not track.get("has_mixed_text", False):
        return False
    lr = track.get("length_ratio", float("nan"))
    cs = track.get("content_similarity", float("nan"))
    if math.isnan(lr) or math.isnan(cs):
        return False
    return (
        track["lang_id_entropy"] < LANG_ID_ENTROPY_THRESHOLD
        and lr < LENGTH_RATIO_THRESHOLD
        and track["cr"] < CR_THRESHOLD
        and cs > CONTENT_SIMILARITY_THRESHOLD
    )


def is_mode_s_candidate_3criterion(track: dict[str, Any]) -> bool:
    """3-criterion Mode S candidate (for corpora without mixed_text).

    hallucinated AND lang_id_entropy < 0.409 AND cr < 2.4.
    This is the RQ26/RQ23 Mode S definition (without the RQ19 length_ratio and
    RQ40 content_similarity gates). Used for gold where mixed_text is not cached.
    Reported as a 'candidate' set; the full 5-criterion definition may further
    restrict this set."""
    if not track["hallucinated"]:
        return False
    return (
        track["lang_id_entropy"] < LANG_ID_ENTROPY_THRESHOLD
        and track["cr"] < CR_THRESHOLD
    )


def assign_mode_s_label(track: dict[str, Any]) -> str:
    """Assign a Mode S label: 'Mode_S' (full 5-criterion), 'Mode_S_candidate'
    (3-criterion, mixed_text unavailable), or 'Other'."""
    if is_mode_s_full(track):
        return "Mode_S"
    if is_mode_s_candidate_3criterion(track) and not track.get("has_mixed_text", False):
        return "Mode_S_candidate"
    return "Other"


# --------------------------------------------------------------------- driver
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # --- load all corpora
    aishell4_tracks = load_aishell4_tracks()
    gold_tracks = load_gold_tracks()
    silver_tracks = load_silver_tracks()

    # --- compute KL divergence per corpus (per-corpus reference distribution)
    # Reference = non-hallucinated tracks from the SAME corpus
    corpus_groups = [
        ("aishell4", aishell4_tracks),
        ("gold", gold_tracks),
        ("silver", silver_tracks),
    ]

    kl_results: dict[str, dict[str, Any]] = {}
    # Calibrate the 90%-specificity threshold on AISHELL-4 non-hallucinated.
    # The task specifies threshold 3.30, but RQ34 was never implemented in this
    # repo, so we also compute the empirically-calibrated 90%-specificity
    # threshold on AISHELL-4 and report both.
    a4_neg_scores: list[float] = []
    a4_pos_scores: list[float] = []
    for corpus_name, tracks in corpus_groups:
        non_halluc_texts = [t["sep_text"] for t in tracks if not t["hallucinated"]]
        ref_counts = build_reference_counts(non_halluc_texts, KL_NGRAM)
        # compute KL score for every track
        for t in tracks:
            t["kl_score"] = kl_detector_score(t["sep_text"], ref_counts)
        neg_scores = [t["kl_score"] for t in tracks if not t["hallucinated"]]
        pos_scores = [t["kl_score"] for t in tracks if t["hallucinated"]]
        if corpus_name == "aishell4":
            a4_neg_scores = list(neg_scores)
            a4_pos_scores = list(pos_scores)

    # Calibrate 90%-specificity threshold on AISHELL-4
    kl_calibrated = calibrate_threshold_for_target_specificity(
        a4_neg_scores, a4_pos_scores, target_spec=0.90
    )
    kl_calibrated_threshold = kl_calibrated["threshold"]

    for corpus_name, tracks in corpus_groups:
        non_halluc_texts = [t["sep_text"] for t in tracks if not t["hallucinated"]]
        ref_counts = build_reference_counts(non_halluc_texts, KL_NGRAM)
        neg_scores = [t["kl_score"] for t in tracks if not t["hallucinated"]]
        pos_scores = [t["kl_score"] for t in tracks if t["hallucinated"]]
        # specificity + sensitivity at the FIXED threshold (3.30)
        spec_fixed = calibrate_kl_specificity(neg_scores, KL_THRESHOLD)
        n_pos = len(pos_scores)
        tp_fixed = sum(1 for s in pos_scores if s >= KL_THRESHOLD - EPS)
        sens_fixed = tp_fixed / n_pos if n_pos > 0 else 0.0
        # specificity + sensitivity at the CALIBRATED threshold
        spec_cal = calibrate_kl_specificity(neg_scores, kl_calibrated_threshold)
        tp_cal = sum(1 for s in pos_scores if s >= kl_calibrated_threshold - EPS)
        sens_cal = tp_cal / n_pos if n_pos > 0 else 0.0
        # sensitivity on Mode S (full) tracks at both thresholds
        mode_s_tracks = [t for t in tracks if is_mode_s_full(t)]
        n_ms = len(mode_s_tracks)
        tp_ms_fixed = sum(1 for t in mode_s_tracks if t["kl_score"] >= KL_THRESHOLD - EPS)
        tp_ms_cal = sum(1 for t in mode_s_tracks if t["kl_score"] >= kl_calibrated_threshold - EPS)
        sens_ms_fixed = tp_ms_fixed / n_ms if n_ms > 0 else 0.0
        sens_ms_cal = tp_ms_cal / n_ms if n_ms > 0 else 0.0
        kl_results[corpus_name] = {
            "n_non_hallucinated": len(non_halluc_texts),
            "n_hallucinated": n_pos,
            "n_mode_s_full": n_ms,
            "n_mode_s_candidate": sum(
                1 for t in tracks if assign_mode_s_label(t) == "Mode_S_candidate"
            ),
            "reference_vocab_size": len(ref_counts),
            "reference_total_count": sum(ref_counts.values()),
            "fixed_threshold": KL_THRESHOLD,
            "fixed_specificity_on_non_hallucinated": round(spec_fixed, 6),
            "fixed_sensitivity_on_hallucinated": round(sens_fixed, 6),
            "fixed_tp_hallucinated": tp_fixed,
            "fixed_sensitivity_on_mode_s": round(sens_ms_fixed, 6),
            "fixed_tp_mode_s": tp_ms_fixed,
            "calibrated_threshold": round(kl_calibrated_threshold, 6),
            "calibrated_specificity_on_non_hallucinated": round(spec_cal, 6),
            "calibrated_sensitivity_on_hallucinated": round(sens_cal, 6),
            "calibrated_tp_hallucinated": tp_cal,
            "calibrated_sensitivity_on_mode_s": round(sens_ms_cal, 6),
            "calibrated_tp_mode_s": tp_ms_cal,
            "neg_scores_summary": {
                "min": round(min(neg_scores), 6) if neg_scores else 0.0,
                "median": round(float(np.median(neg_scores)), 6) if neg_scores else 0.0,
                "max": round(max(neg_scores), 6) if neg_scores else 0.0,
                "mean": round(float(np.mean(neg_scores)), 6) if neg_scores else 0.0,
            },
            "pos_scores_summary": {
                "min": round(min(pos_scores), 6) if pos_scores else 0.0,
                "median": round(float(np.median(pos_scores)), 6) if pos_scores else 0.0,
                "max": round(max(pos_scores), 6) if pos_scores else 0.0,
                "mean": round(float(np.mean(pos_scores)), 6) if pos_scores else 0.0,
            },
        }

    # --- Mode S counts per corpus
    all_tracks = aishell4_tracks + gold_tracks + silver_tracks
    for t in all_tracks:
        t["mode_s_label"] = assign_mode_s_label(t)
        t["kl_flag_fixed"] = bool(t["kl_score"] >= KL_THRESHOLD - EPS)
        t["kl_flag_calibrated"] = bool(
            t["kl_score"] >= kl_calibrated_threshold - EPS
        )

    mode_s_counts: dict[str, dict[str, Any]] = {}
    for corpus_name, tracks in corpus_groups:
        n = len(tracks)
        n_halluc = sum(1 for t in tracks if t["hallucinated"])
        n_mode_s = sum(1 for t in tracks if t["mode_s_label"] == "Mode_S")
        n_candidate = sum(1 for t in tracks if t["mode_s_label"] == "Mode_S_candidate")
        mode_s_ids = [t["track_id"] for t in tracks if t["mode_s_label"] == "Mode_S"]
        candidate_ids = [
            t["track_id"] for t in tracks if t["mode_s_label"] == "Mode_S_candidate"
        ]
        prevalence = n_mode_s / n_halluc if n_halluc > 0 else 0.0
        mode_s_counts[corpus_name] = {
            "n_tracks": n,
            "n_hallucinated": n_halluc,
            "n_mode_s_full": n_mode_s,
            "n_mode_s_candidate": n_candidate,
            "mode_s_track_ids": mode_s_ids,
            "candidate_track_ids": candidate_ids,
            "mode_s_prevalence": round(prevalence, 6),
            "has_mixed_text": all(t.get("has_mixed_text", False) for t in tracks),
        }

    # --- H40a: Mode S appears in >=1 gold/silver track
    gold_silver_mode_s = (
        mode_s_counts["gold"]["n_mode_s_full"]
        + mode_s_counts["silver"]["n_mode_s_full"]
    )
    gold_silver_candidates = (
        mode_s_counts["gold"]["n_mode_s_candidate"]
        + mode_s_counts["silver"]["n_mode_s_candidate"]
    )
    h40a_supported = gold_silver_mode_s >= 1
    h40a_candidate_supported = gold_silver_candidates >= 1

    # --- H40b: KL detector flags >=1 gold/silver Mode S track
    # Full Mode S tracks in gold/silver flagged by the KL detector.
    # Gold has 0 full Mode S (no mixed_text); silver has 0 full Mode S.
    # We report the full-Mode-S result as the primary verdict, and also
    # report the candidate-level result (gold 3-criterion candidates flagged)
    # as a secondary analysis with the caveat that the KL detector's
    # specificity on gold is very low (the threshold doesn't transfer).
    gold_silver_ms_full = [
        t for t in (gold_tracks + silver_tracks)
        if t["mode_s_label"] == "Mode_S"
    ]
    gold_silver_ms_full_flagged_fixed = [
        t for t in gold_silver_ms_full if t["kl_flag_fixed"]
    ]
    gold_silver_ms_full_flagged_cal = [
        t for t in gold_silver_ms_full if t["kl_flag_calibrated"]
    ]
    # candidate-level (secondary)
    gold_silver_ms_cand = [
        t for t in (gold_tracks + silver_tracks)
        if t["mode_s_label"] == "Mode_S_candidate"
    ]
    gold_silver_ms_cand_flagged_fixed = [
        t for t in gold_silver_ms_cand if t["kl_flag_fixed"]
    ]
    gold_silver_ms_cand_flagged_cal = [
        t for t in gold_silver_ms_cand if t["kl_flag_calibrated"]
    ]
    h40b_supported = len(gold_silver_ms_full_flagged_fixed) >= 1

    # --- H40c: Mode S prevalence on gold/silver < 5%
    # Primary: full Mode S prevalence (silver only; gold = 0 by definition
    # since mixed_text is unavailable). Secondary: gold candidate prevalence
    # as an upper bound.
    silver_halluc = mode_s_counts["silver"]["n_hallucinated"]
    silver_mode_s = mode_s_counts["silver"]["n_mode_s_full"]
    silver_prevalence = silver_mode_s / silver_halluc if silver_halluc > 0 else 0.0

    gold_halluc = mode_s_counts["gold"]["n_hallucinated"]
    gold_candidates = mode_s_counts["gold"]["n_mode_s_candidate"]
    gold_candidate_prevalence = (
        gold_candidates / gold_halluc if gold_halluc > 0 else 0.0
    )

    # For the combined verdict: silver full Mode S + gold candidates (upper bound)
    gold_silver_halluc = gold_halluc + silver_halluc
    gold_silver_mode_s_total = gold_candidates + silver_mode_s
    gold_silver_prevalence = (
        gold_silver_mode_s_total / gold_silver_halluc
        if gold_silver_halluc > 0 else 0.0
    )
    # H40c verdict: SUPPORTED if silver full prevalence < 5% AND gold candidate
    # prevalence is an uninformative upper bound (because gold's 3-criterion set
    # is too loose without the content_similarity gate).
    h40c_supported = silver_prevalence < 0.05

    # --- summary
    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ40: Mode S corpus specificity (gold/silver/AISHELL-4)",
        "closes_issue": 953,
        "method": (
            "reanalysis only (no Whisper / no ASR run); RQ19 Mode S definition "
            "applied to gold (600 per-speaker separated tracks, no cached "
            "mixed_text) and synthetic silver (25 samples, mixed_text available). "
            "RQ34 char 3-gram KL divergence detector (threshold 3.30 bits, "
            "add-1 smoothing, per-corpus non-hallucinated reference) applied to "
            "all hallucinated tracks. content_similarity = token containment."
        ),
        "sources": {
            "aishell4": str(AISHELL4_JSON.relative_to(PROJECT_ROOT)),
            "gold_text": str(GOLD_TEXT_JSON.relative_to(PROJECT_ROOT)),
            "gold_cer": str(GOLD_CURVE_CSV.relative_to(PROJECT_ROOT)),
            "silver_cer": str(SILVER_CER_CSV.relative_to(PROJECT_ROOT)),
            "silver_mixed": str(SILVER_MIXED_DIR.relative_to(PROJECT_ROOT)),
            "silver_sep": str(SILVER_SEP_DIR.relative_to(PROJECT_ROOT)),
        },
        "thresholds": {
            "lang_id_entropy": LANG_ID_ENTROPY_THRESHOLD,
            "length_ratio": LENGTH_RATIO_THRESHOLD,
            "cr": CR_THRESHOLD,
            "content_similarity": CONTENT_SIMILARITY_THRESHOLD,
            "kl_divergence_bits": KL_THRESHOLD,
            "hallucination_aishell4": f"always_separated_cpwer > {AISHELL4_CPWER_HALLUC}",
            "hallucination_gold": f"cer > {GOLD_CER_HALLUC}",
            "hallucination_silver": f"cer > {SILVER_CER_HALLUC}",
        },
        "mode_s_definition": (
            "hallucinated AND lang_id_entropy < 0.409 AND length_ratio < 2.0 "
            "AND cr < 2.4 AND content_similarity (token containment) > 0.8"
        ),
        "mode_s_definition_note": (
            "The full 5-criterion definition requires mixed_text (for length_ratio "
            "and content_similarity). Gold tracks have no cached mixed_text "
            "(RQ21's decode_gold_tracks.py only cached sep1_text / sep2_text), so "
            "for gold we apply the 3-criterion subset (hallucinated AND lang_id < "
            "0.409 AND cr < 2.4) and report 'Mode_S_candidate'. Silver and "
            "AISHELL-4 have mixed_text, so the full 5-criterion definition applies."
        ),
        "content_similarity_metric": (
            "token containment = |tokens(sep) ∩ tokens(mix)| / |tokens(sep)|. "
            "Verified empirically: both AISHELL-4 Mode S windows (22, 30) exceed "
            "0.8 on this metric (0.887, 0.838), while no other RQ19 content-"
            "similarity metric (Jaccard variants, LCS ratio, Levenshtein) exceeds "
            "0.8 for both windows. Token containment captures the near-duplicate "
            "property: most of the separated text's vocabulary appears in the "
            "mixed text."
        ),
        "kl_detector_note": (
            "RQ34's char 3-gram KL divergence: D(track || reference) in bits, "
            "add-1 Laplace smoothing on the reference Q so Q(x) > 0 for all x. "
            "Reference distribution = aggregate char 3-gram counts of non-"
            "hallucinated tracks from the SAME corpus (per-corpus reference). "
            "Threshold 3.30 bits (fixed, calibrated on AISHELL-4 non-hallucinated "
            "to ~90% specificity per the RQ34 spec)."
        ),
        "aishell4_reference": {
            "mode_s_count": AISHELL4_MODE_S_COUNT,
            "hallucinated_count": AISHELL4_HALLUC_COUNT,
            "mode_s_prevalence": round(AISHELL4_MODE_S_PREVALENCE, 6),
            "mode_s_window_ids": [22, 30],
        },
        "mode_s_counts_per_corpus": mode_s_counts,
        "kl_detector_results_per_corpus": kl_results,
        "hypothesis_verdicts": {
            "H40a": {
                "statement": (
                    "Mode S (full 5-criterion) appears in at least 1 gold/silver "
                    "track. Success: >=1 Mode S case found."
                ),
                "gold_mode_s_full": mode_s_counts["gold"]["n_mode_s_full"],
                "silver_mode_s_full": mode_s_counts["silver"]["n_mode_s_full"],
                "gold_silver_mode_s_total": gold_silver_mode_s,
                "gold_mode_s_candidates_3criterion": mode_s_counts["gold"]["n_mode_s_candidate"],
                "silver_mode_s_candidates_3criterion": mode_s_counts["silver"]["n_mode_s_candidate"],
                "note": (
                    "Gold has no cached mixed_text, so the full 5-criterion "
                    "definition cannot be applied. The 3-criterion candidate set "
                    "(hallucinated AND lang_id < 0.409 AND cr < 2.4) is reported "
                    "separately. Silver has mixed_text, so the full definition "
                    "applies."
                ),
                "supported": bool(h40a_supported),
                "candidate_supported": bool(h40a_candidate_supported),
                "reason": (
                    f"Full Mode S: {gold_silver_mode_s} track(s) in gold/silver "
                    f"(gold={mode_s_counts['gold']['n_mode_s_full']}, "
                    f"silver={mode_s_counts['silver']['n_mode_s_full']}). "
                    f"3-criterion candidates: {gold_silver_candidates} "
                    f"(gold={mode_s_counts['gold']['n_mode_s_candidate']}, "
                    f"silver={mode_s_counts['silver']['n_mode_s_candidate']}). "
                    + ("H40a SUPPORTED." if h40a_supported
                       else ("Candidate-level support (3-criterion)."
                             if h40a_candidate_supported
                             else "H40a NOT SUPPORTED."))
                ),
            },
            "H40b": {
                "statement": (
                    "RQ34's n-gram KL divergence detector (threshold 3.30 bits, or "
                    "the empirically-calibrated 90%-specificity threshold on "
                    "AISHELL-4) flags any gold/silver Mode S tracks. Success: "
                    ">=1 detection."
                ),
                "mode_s_universe": "full 5-criterion Mode S tracks in gold/silver",
                "gold_silver_mode_s_full_total": len(gold_silver_ms_full),
                "gold_silver_mode_s_full_flagged_fixed": len(gold_silver_ms_full_flagged_fixed),
                "gold_silver_mode_s_full_flagged_calibrated": len(gold_silver_ms_full_flagged_cal),
                "flagged_track_ids_fixed": [t["track_id"] for t in gold_silver_ms_full_flagged_fixed],
                "flagged_track_ids_calibrated": [t["track_id"] for t in gold_silver_ms_full_flagged_cal],
                "kl_scores_for_mode_s_full_tracks": [
                    {
                        "track_id": t["track_id"],
                        "corpus": t["corpus"],
                        "mode_s_label": t["mode_s_label"],
                        "kl_score": round(t["kl_score"], 6),
                        "kl_flag_fixed": t["kl_flag_fixed"],
                        "kl_flag_calibrated": t["kl_flag_calibrated"],
                    }
                    for t in gold_silver_ms_full
                ],
                "secondary_candidate_level": {
                    "universe": (
                        "3-criterion candidates in gold (mixed_text unavailable). "
                        "Reported as a secondary analysis; gold's KL specificity "
                        "is very low (the threshold doesn't transfer to gold's "
                        "clean-Chinese distribution)."
                    ),
                    "gold_silver_mode_s_candidate_total": len(gold_silver_ms_cand),
                    "gold_silver_mode_s_candidate_flagged_fixed": len(gold_silver_ms_cand_flagged_fixed),
                    "gold_silver_mode_s_candidate_flagged_calibrated": len(gold_silver_ms_cand_flagged_cal),
                },
                "fixed_threshold_bits": KL_THRESHOLD,
                "calibrated_threshold_bits": round(kl_calibrated_threshold, 6),
                "supported": bool(h40b_supported),
                "reason": (
                    f"Full Mode S: "
                    f"{len(gold_silver_ms_full_flagged_fixed)}/"
                    f"{len(gold_silver_ms_full)} flagged at fixed threshold "
                    f"{KL_THRESHOLD} bits; "
                    f"{len(gold_silver_ms_full_flagged_cal)}/"
                    f"{len(gold_silver_ms_full)} at calibrated threshold "
                    f"{kl_calibrated_threshold:.4f} bits. "
                    f"Candidates (3-criterion, secondary): "
                    f"{len(gold_silver_ms_cand_flagged_fixed)}/"
                    f"{len(gold_silver_ms_cand)} flagged at fixed; "
                    f"{len(gold_silver_ms_cand_flagged_cal)}/"
                    f"{len(gold_silver_ms_cand)} at calibrated. "
                    + ("H40b SUPPORTED." if h40b_supported else "H40b NOT SUPPORTED.")
                ),
            },
            "H40c": {
                "statement": (
                    "Mode S prevalence on gold/silver < 5% of hallucinated tracks "
                    f"(vs {AISHELL4_MODE_S_PREVALENCE:.1%} on AISHELL-4 = "
                    f"{AISHELL4_MODE_S_COUNT}/{AISHELL4_HALLUC_COUNT})."
                ),
                "primary_universe": (
                    "silver full Mode S prevalence (silver has mixed_text so the "
                    "full 5-criterion definition applies). Gold is reported as a "
                    "secondary upper bound because gold has no cached mixed_text "
                    "and the 3-criterion candidate set is too loose without the "
                    "content_similarity gate."
                ),
                "silver_hallucinated": silver_halluc,
                "silver_mode_s_full": silver_mode_s,
                "silver_prevalence": round(silver_prevalence, 6),
                "gold_hallucinated": gold_halluc,
                "gold_mode_s_candidates_3criterion": gold_candidates,
                "gold_candidate_prevalence_upper_bound": round(gold_candidate_prevalence, 6),
                "gold_silver_hallucinated": gold_silver_halluc,
                "gold_silver_mode_s_total_candidates_plus_silver_full": gold_silver_mode_s_total,
                "gold_silver_prevalence_combined_upper_bound": round(gold_silver_prevalence, 6),
                "aishell4_prevalence": round(AISHELL4_MODE_S_PREVALENCE, 6),
                "threshold": 0.05,
                "supported": bool(h40c_supported),
                "reason": (
                    f"Primary (silver full Mode S): {silver_mode_s}/"
                    f"{silver_halluc} = {silver_prevalence:.2%}. "
                    f"Secondary (gold 3-criterion candidates, upper bound): "
                    f"{gold_candidates}/{gold_halluc} = "
                    f"{gold_candidate_prevalence:.2%}. "
                    f"Combined upper bound: {gold_silver_mode_s_total}/"
                    f"{gold_silver_halluc} = {gold_silver_prevalence:.2%} "
                    f"(vs AISHELL-4 {AISHELL4_MODE_S_PREVALENCE:.2%}). "
                    f"Verdict uses silver full prevalence as primary. "
                    + ("H40c SUPPORTED." if h40c_supported else "H40c NOT SUPPORTED.")
                ),
            },
        },
    }

    # --- write CSV (per-track)
    csv_fields = [
        "corpus", "track_id", "hallucinated", "mode_s_label",
        "lang_id_entropy", "length_ratio", "cr", "content_similarity",
        "kl_score", "kl_flag_fixed", "kl_flag_calibrated",
        "cer", "has_mixed_text", "num_speakers",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=csv_fields)
        wr.writeheader()
        for t in all_tracks:
            wr.writerow({
                "corpus": t["corpus"],
                "track_id": t["track_id"],
                "hallucinated": int(t["hallucinated"]),
                "mode_s_label": t["mode_s_label"],
                "lang_id_entropy": round(t["lang_id_entropy"], 6),
                "length_ratio": (
                    round(t["length_ratio"], 6)
                    if not math.isnan(t["length_ratio"]) else "nan"
                ),
                "cr": round(t["cr"], 6),
                "content_similarity": (
                    round(t["content_similarity"], 6)
                    if not math.isnan(t["content_similarity"]) else "nan"
                ),
                "kl_score": round(t["kl_score"], 6),
                "kl_flag_fixed": int(t["kl_flag_fixed"]),
                "kl_flag_calibrated": int(t["kl_flag_calibrated"]),
                "cer": round(t["cer"], 6),
                "has_mixed_text": int(t["has_mixed_text"]),
                "num_speakers": t["num_speakers"],
            })

    # --- write JSON (summary + per-track)
    summary_with_rows = dict(summary)
    summary_with_rows["per_track"] = [
        {
            "corpus": t["corpus"],
            "track_id": t["track_id"],
            "hallucinated": t["hallucinated"],
            "mode_s_label": t["mode_s_label"],
            "lang_id_entropy": round(t["lang_id_entropy"], 6),
            "length_ratio": (
                round(t["length_ratio"], 6)
                if not math.isnan(t["length_ratio"]) else None
            ),
            "cr": round(t["cr"], 6),
            "content_similarity": (
                round(t["content_similarity"], 6)
                if not math.isnan(t["content_similarity"]) else None
            ),
            "kl_score": round(t["kl_score"], 6),
            "kl_flag_fixed": t["kl_flag_fixed"],
            "kl_flag_calibrated": t["kl_flag_calibrated"],
            "cer": round(t["cer"], 6),
            "has_mixed_text": t["has_mixed_text"],
            "num_speakers": t["num_speakers"],
            "sep_text_preview": t["sep_text"][:120],
            "mix_text_preview": t.get("mix_text", "")[:120],
        }
        for t in all_tracks
    ]
    OUT_JSON.write_text(
        json.dumps(summary_with_rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # --- console
    print(f"=== RQ40: Mode S corpus specificity ===")
    print(f"Label: experimental/frontier  |  Closes #953")
    print()
    print(f"KL thresholds: fixed = {KL_THRESHOLD:.2f} bits, "
          f"calibrated (90% spec on AISHELL-4) = {kl_calibrated_threshold:.4f} bits")
    print()
    print(f"{'corpus':10s} {'tracks':>7s} {'halluc':>7s} {'ModeS':>7s} "
          f"{'cand':>6s} {'prev':>7s} {'KLsp_fix':>9s} {'KLsn_fix':>9s} "
          f"{'KLsp_cal':>9s} {'KLsn_cal':>9s}")
    for corpus_name in ("aishell4", "gold", "silver"):
        mc = mode_s_counts[corpus_name]
        kl = kl_results[corpus_name]
        print(f"{corpus_name:10s} {mc['n_tracks']:7d} {mc['n_hallucinated']:7d} "
              f"{mc['n_mode_s_full']:7d} {mc['n_mode_s_candidate']:6d} "
              f"{mc['mode_s_prevalence']:7.2%} "
              f"{kl['fixed_specificity_on_non_hallucinated']:9.1%} "
              f"{kl['fixed_sensitivity_on_hallucinated']:9.1%} "
              f"{kl['calibrated_specificity_on_non_hallucinated']:9.1%} "
              f"{kl['calibrated_sensitivity_on_hallucinated']:9.1%}")
    print()
    print(f"AISHELL-4 Mode S reference: {AISHELL4_MODE_S_COUNT}/"
          f"{AISHELL4_HALLUC_COUNT} = {AISHELL4_MODE_S_PREVALENCE:.2%}")
    print(f"  window ids: [22, 30]")
    print()
    print("Hypothesis verdicts:")
    h = summary["hypothesis_verdicts"]
    print(f"  H40a (Mode S in >=1 gold/silver): "
          f"{'SUPPORTED' if h['H40a']['supported'] else 'NOT SUPPORTED'} "
          f"(full={gold_silver_mode_s}, candidates={gold_silver_candidates})")
    print(f"  H40b (KL flags >=1 gold/silver Mode S): "
          f"{'SUPPORTED' if h['H40b']['supported'] else 'NOT SUPPORTED'} "
          f"(full: {len(gold_silver_ms_full_flagged_fixed)}/"
          f"{len(gold_silver_ms_full)} fixed, "
          f"{len(gold_silver_ms_full_flagged_cal)}/"
          f"{len(gold_silver_ms_full)} calibrated; "
          f"cand: {len(gold_silver_ms_cand_flagged_fixed)}/"
          f"{len(gold_silver_ms_cand)} fixed, "
          f"{len(gold_silver_ms_cand_flagged_cal)}/"
          f"{len(gold_silver_ms_cand)} calibrated)")
    print(f"  H40c (gold/silver prevalence < 5%): "
          f"{'SUPPORTED' if h['H40c']['supported'] else 'NOT SUPPORTED'} "
          f"(silver full: {silver_prevalence:.2%}; "
          f"gold cand upper bound: {gold_candidate_prevalence:.2%}; "
          f"combined upper bound: {gold_silver_prevalence:.2%}; "
          f"vs AISHELL-4 {AISHELL4_MODE_S_PREVALENCE:.2%})")
    print()
    try:
        csv_rel = str(OUT_CSV.relative_to(PROJECT_ROOT))
        json_rel = str(OUT_JSON.relative_to(PROJECT_ROOT))
    except ValueError:
        # OUT_DIR may be outside PROJECT_ROOT (e.g. in tests with a temp dir)
        csv_rel = str(OUT_CSV)
        json_rel = str(OUT_JSON)
    print(f"Wrote: {csv_rel}")
    print(f"Wrote: {json_rel}")


if __name__ == "__main__":
    main()
