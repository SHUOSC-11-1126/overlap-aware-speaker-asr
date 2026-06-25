"""RQ13: Diverse hallucination detector for AISHELL-4.

REANALYSIS ONLY — no Whisper / no ASR model is run. This script reads the existing
AISHELL-4 external-validation results (``results/external_sanity_check/aishell4/
rq1_aishell4_validation_results.json``, label ``external/sanity-check``, PR #890) and
builds reference-free detectors for the *diverse multilingual* hallucination that the
compression-ratio (CR) guard misses (RQ12, PR #900: CR sensitivity 2.7% on AISHELL-4
because the hallucination is diverse gibberish, not repetitive loops, so CR ~ 1.0-1.5
stays below the 2.4 threshold).

Label: experimental/frontier
Closes #903. Builds on ``results/frontier/router_failure_modes/`` (RQ12).

Research questions
------------------
1. Can a reference-free language-id entropy detector catch the diverse hallucination
   that CR misses?
2. Can a token-type diversity (TTR) detector catch it?
3. Can an ensemble of script-diversity signals beat the CR baseline at fixed
   specificity?

Method
------
For each of the 77 windows we treat the window's separated output as a "track" (the
hallucination label is window-level: ``always_separated_cpwer > 1.0`` => hallucinated;
this matches RQ12's 37 hallucinated / 40 non-hallucinated split). For each per-speaker
separated transcript we compute four reference-free scores and aggregate across
speakers by MAX (the worst-case speaker track; same convention as RQ12's
``max_cr_separated``):

  - **language-id entropy**: Shannon entropy over Unicode script categories (Han,
    Latin, Hiragana, Katakana, Hangul, ...) using ``unicodedata``. Clean Chinese is
    near-monoscript (entropy ~ 0); diverse gibberish mixes 4+ scripts (high entropy).
  - **token-type diversity (TTR)**: unique tokens / total tokens. Tokeniser is
    script-aware: CJK chars are individual tokens, Latin/other runs are split on
    whitespace. (No Chinese word segmenter is available under the numpy+stdlib-only
    constraint, so Han characters are character-tokens — a documented design choice.)
  - **character-set diversity**: distinct script categories / total non-space chars
    (a script-count proxy for distinct Unicode blocks; ``unicodedata`` exposes no
    block lookup).
  - **compression ratio (CR baseline)**: ``len(utf8)/len(zlib)``, identical to RQ12.

Each detector is calibrated to >= 90% specificity on the 40 non-hallucinated tracks
(specificity = P(not flagged | cpWER <= 1.0)); we pick the operating point on the ROC
curve with specificity >= 0.90 and maximal sensitivity. Sensitivity is then measured
on the 37 hallucinated tracks (sensitivity = P(flagged | cpWER > 1.0)). A
logistic-regression ensemble (numpy gradient descent, L2-regularised) combines the
four standardised scores and is calibrated the same way.

Hypotheses
----------
- H13a: language-id entropy sensitivity > 50% (at >= 90% specificity).
- H13b: token-type diversity sensitivity > 50% (at >= 90% specificity).
- H13c: ensemble sensitivity > 80% (at >= 90% specificity).

Bootstrap: 10,000 resamples (seed=42) of the 77 tracks with replacement, recomputing
sensitivity with the FULL-SAMPLE-FIXED threshold (threshold uncertainty is not
included; reported as a limitation).

This script is pure reanalysis (numpy + stdlib only; scipy / sklearn / Whisper are NOT
required).
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
SRC_JSON = (
    PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "diverse_hallucination_detector"
OUT_CSV = OUT_DIR / "detector_comparison.csv"
OUT_JSON = OUT_DIR / "detector_comparison.json"

# ------------------------------------------------------------------ thresholds
CATASTROPHIC_CPWER = 1.0    # cpWER > 1.0 => insertions dominate (hallucination label)
TARGET_SPECIFICITY = 0.90   # calibrate each detector to >= 90% specificity
N_BOOT = 10000
SEED = 42
EPS = 1e-9

# CJK scripts that lack whitespace word boundaries -> character-level tokens
CJK_SCRIPTS = {"Han", "Hiragana", "Katakana", "Hangul"}


# ----------------------------------------------------------------- CR primitive
def compression_ratio(text: str) -> float:
    """Whisper-style compression ratio: len(utf8 bytes) / len(zlib-compressed bytes).

    Matches ``whisper.audio.compression_ratio`` and RQ12's ``compression_ratio``.
    Returns 0.0 for empty/whitespace text. High CR (>~2.4) = repetitive loop."""
    if not text or not text.strip():
        return 0.0
    b = text.encode("utf-8")
    c = zlib.compress(b)
    return len(b) / len(c) if len(c) > 0 else 0.0


# ------------------------------------------------------------- script detection
def script_category(ch: str) -> str:
    """Map a character to a coarse Unicode script category.

    Uses ``unicodedata.name`` (the first token usually identifies the script).
    Whitespace -> "Space"; punctuation/symbols -> "Punct"; control/unknown ->
    "Other". This is a script-category proxy (``unicodedata`` exposes no block
    lookup); it is sufficient to separate Han / Latin / Hiragana / Katakana /
    Hangul / Cyrillic / Arabic / Greek, which are exactly the scripts RQ12 observed
    in AISHELL-4 diverse hallucination."""
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


# --------------------------------------------------------------- the four scores
def language_id_entropy(text: str) -> float:
    """Shannon entropy (bits) over the script-category distribution of the text.

    Clean Chinese (near-monoscript Han) -> entropy ~ 0. Diverse multilingual
    gibberish mixing Han+Latin+Katakana+Hangul -> high entropy (up to log2(k))."""
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
    """Script-aware tokeniser.

    CJK characters (Han/Hiragana/Katakana/Hangul) become individual character-tokens
    (Chinese has no whitespace word boundaries and no segmenter is available under the
    numpy+stdlib-only constraint). Latin/other runs are split on whitespace. Returns
    [] for empty/whitespace text."""
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


def token_type_diversity(text: str) -> float:
    """Type-token ratio: unique tokens / total tokens.

    Diverse gibberish has many unique tokens (TTR -> 1.0); clean speech reuses
    function words/chars (lower TTR); repetitive loops reuse one token (TTR -> 0)."""
    toks = tokenize(text)
    if not toks:
        return 0.0
    return len(set(toks)) / len(toks)


def char_set_diversity(text: str) -> float:
    """Distinct script categories / total non-space characters.

    A script-count proxy for distinct Unicode blocks (``unicodedata`` exposes no
    block lookup). Clean Chinese -> 1 script / many chars -> ~0. Diverse gibberish
    -> several scripts / few chars -> higher."""
    if not text:
        return 0.0
    scripts: set[str] = set()
    n = 0
    for ch in text:
        if ch.isspace():
            continue
        scripts.add(script_category(ch))
        n += 1
    if n <= 0:
        return 0.0
    return len(scripts) / n


# ------------------------------------------------------------- per-track aggregate
def max_across_speakers(window: dict[str, Any], fn) -> float:
    """Max of fn(text) over the per-speaker separated transcripts (worst-case track).

    Same convention as RQ12's ``max_cr_separated``: a window is flagged if ANY speaker
    track trips the detector. Empty/whitespace speaker texts contribute 0.0 and are
    effectively skipped (they never raise the max for a hallucination signal)."""
    vals = [
        fn(str(t))
        for t in window.get("separated_text_per_speaker", {}).values()
        if t is not None and str(t).strip()
    ]
    return max(vals) if vals else 0.0


# --------------------------------------------------------- threshold calibration
def roc_operating_point(
    neg_scores: list[float], pos_scores: list[float], target_spec: float = TARGET_SPECIFICITY
) -> dict[str, float]:
    """Pick the threshold with specificity >= target_spec and maximal sensitivity.

    Candidate thresholds = all unique scores. Flag = score >= threshold. Returns the
    threshold, achieved specificity, and sensitivity. If no threshold meets the
    specificity target (degenerate), returns the highest threshold (flag nothing)."""
    n_neg = len(neg_scores)
    n_pos = len(pos_scores)
    candidates = sorted(set(neg_scores) | set(pos_scores))
    best: dict[str, float] | None = None
    for t in candidates:
        fp = sum(1 for s in neg_scores if s >= t - EPS)
        tp = sum(1 for s in pos_scores if s >= t - EPS)
        spec = 1.0 - (fp / n_neg) if n_neg else 1.0
        sens = (tp / n_pos) if n_pos else 0.0
        if spec >= target_spec - EPS:
            if best is None or sens > best["sensitivity"] + EPS or (
                abs(sens - best["sensitivity"]) <= EPS and spec > best["specificity"]
            ):
                best = {
                    "threshold": float(t),
                    "specificity": float(spec),
                    "sensitivity": float(sens),
                    "tp": float(tp),
                    "fp": float(fp),
                    "tn": float(n_neg - fp),
                    "fn": float(n_pos - tp),
                }
    if best is None:
        # No threshold meets the target; flag nothing (specificity 1.0, sensitivity 0).
        t = (max(neg_scores + pos_scores) + 1.0) if (neg_scores or pos_scores) else 0.0
        best = {
            "threshold": float(t),
            "specificity": 1.0,
            "sensitivity": 0.0,
            "tp": 0.0, "fp": 0.0,
            "tn": float(n_neg), "fn": float(n_pos),
        }
    return best


# --------------------------------------------------------------------- bootstrap
def bootstrap_sensitivity_ci(
    scores: np.ndarray,
    labels: np.ndarray,
    threshold: float,
    n_boot: int = N_BOOT,
    seed: int = SEED,
) -> tuple[float, float]:
    """Bootstrap 95% CI for sensitivity = P(score >= threshold | label==1).

    Resamples the 77 tracks with replacement and recomputes sensitivity with the
    FIXED full-sample threshold (threshold uncertainty is not included). Tracks with
    no hallucinated sample in a resample are skipped."""
    rng = np.random.default_rng(seed)
    n = len(scores)
    pos_mask = labels == 1
    sens: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        s = scores[idx]
        lab = labels[idx]
        n_pos = int(lab.sum())
        if n_pos <= 0:
            continue
        tp = int(((s >= threshold - EPS) & (lab == 1)).sum())
        sens.append(tp / n_pos)
    if not sens:
        return 0.0, 0.0
    return float(np.percentile(sens, 2.5)), float(np.percentile(sens, 97.5))


# ----------------------------------------------------------- logistic regression
def fit_logistic_regression(
    X: np.ndarray, y: np.ndarray, lr: float = 0.1, n_iter: int = 4000, l2: float = 0.01
) -> tuple[np.ndarray, float]:
    """L2-regularised logistic regression via gradient descent (numpy only).

    X is assumed standardised. Returns weights w and bias b."""
    n, d = X.shape
    w = np.zeros(d)
    b = 0.0
    for _ in range(n_iter):
        z = X @ w + b
        # numerically stable sigmoid
        p = np.where(z >= 0, 1.0 / (1.0 + np.exp(-z)), np.exp(z) / (1.0 + np.exp(z)))
        err = p - y
        grad_w = X.T @ err / n + l2 * w
        grad_b = float(err.mean())
        w -= lr * grad_w
        b -= lr * grad_b
    return w, b


def logistic_proba(X: np.ndarray, w: np.ndarray, b: float) -> np.ndarray:
    z = X @ w + b
    return np.where(z >= 0, 1.0 / (1.0 + np.exp(-z)), np.exp(z) / (1.0 + np.exp(z)))


# --------------------------------------------------------------------- driver
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(SRC_JSON.read_text(encoding="utf-8"))
    windows = data["windows"]
    n = len(windows)

    # Per-window scores (max across speakers) + hallucination label.
    rows: list[dict[str, Any]] = []
    for w in windows:
        sep_cpwer = float(w["always_separated_cpwer"])
        cr = max_across_speakers(w, compression_ratio)
        ent = max_across_speakers(w, language_id_entropy)
        ttr = max_across_speakers(w, token_type_diversity)
        csd = max_across_speakers(w, char_set_diversity)
        halluc = sep_cpwer > CATASTROPHIC_CPWER
        rows.append({
            "window_id": w["window_id"],
            "overlap_label": w["overlap_label"],
            "num_speakers": w["num_speakers"],
            "always_separated_cpwer": round(sep_cpwer, 6),
            "always_mixed_cpwer": round(float(w["always_mixed_cpwer"]), 6),
            "router_v2_cpwer": round(float(w["router_v2_cpwer"]), 6),
            "oracle_best_cpwer": round(float(w["oracle_best_cpwer"]), 6),
            "hallucinated": bool(halluc),
            "cr": cr,
            "lang_id_entropy": ent,
            "token_type_diversity": ttr,
            "char_set_diversity": csd,
        })

    n_halluc = sum(1 for r in rows if r["hallucinated"])
    n_nonhalluc = n - n_halluc

    labels = np.array([1.0 if r["hallucinated"] else 0.0 for r in rows], dtype=float)

    # --- Individual detectors: calibrate each at >= 90% specificity, then sensitivity.
    detector_specs = [
        ("compression_ratio", "cr", "H13_baseline", "CR > 2.4 baseline (RQ12: 2.7% sensitivity)"),
        ("language_id_entropy", "lang_id_entropy", "H13a", "language-id entropy > 50% sensitivity"),
        ("token_type_diversity", "token_type_diversity", "H13b", "token-type diversity > 50% sensitivity"),
        ("char_set_diversity", "char_set_diversity", None, "character-set diversity (secondary signal)"),
    ]
    detector_results: list[dict[str, Any]] = []
    # fixed-threshold sensitivity CIs use the full-sample threshold.
    for name, key, hypo, note in detector_specs:
        scores = np.array([r[key] for r in rows], dtype=float)
        neg = [float(s) for s, l in zip(scores, labels) if l == 0]
        pos = [float(s) for s, l in zip(scores, labels) if l == 1]
        op = roc_operating_point(neg, pos, TARGET_SPECIFICITY)
        ci_lo, ci_hi = bootstrap_sensitivity_ci(scores, labels, op["threshold"])
        detector_results.append({
            "detector": name,
            "hypothesis": hypo,
            "note": note,
            "threshold": round(op["threshold"], 6),
            "specificity": round(op["specificity"], 6),
            "sensitivity": round(op["sensitivity"], 6),
            "sensitivity_ci_95": [round(ci_lo, 6), round(ci_hi, 6)],
            "tp": int(op["tp"]),
            "fp": int(op["fp"]),
            "tn": int(op["tn"]),
            "fn": int(op["fn"]),
            "n_pos": n_halluc,
            "n_neg": n_nonhalluc,
        })

    # --- Ensemble: logistic regression over the 4 standardised scores.
    feat_keys = ["cr", "lang_id_entropy", "token_type_diversity", "char_set_diversity"]
    X = np.array([[r[k] for k in feat_keys] for r in rows], dtype=float)
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd_safe = np.where(sd > EPS, sd, 1.0)
    Xz = (X - mu) / sd_safe
    w, b = fit_logistic_regression(Xz, labels)
    ens_scores = logistic_proba(Xz, w, b)
    neg_e = [float(s) for s, l in zip(ens_scores, labels) if l == 0]
    pos_e = [float(s) for s, l in zip(ens_scores, labels) if l == 1]
    ens_op = roc_operating_point(neg_e, pos_e, TARGET_SPECIFICITY)
    ens_lo, ens_hi = bootstrap_sensitivity_ci(ens_scores, labels, ens_op["threshold"])
    ensemble_result = {
        "detector": "ensemble_logistic_regression",
        "hypothesis": "H13c",
        "note": "LR over 4 standardised scores (in-sample fit); > 80% sensitivity at >= 90% specificity",
        "features": feat_keys,
        "lr_weights": {k: round(float(wi), 6) for k, wi in zip(feat_keys, w)},
        "lr_bias": round(float(b), 6),
        "threshold": round(ens_op["threshold"], 6),
        "specificity": round(ens_op["specificity"], 6),
        "sensitivity": round(ens_op["sensitivity"], 6),
        "sensitivity_ci_95": [round(ens_lo, 6), round(ens_hi, 6)],
        "tp": int(ens_op["tp"]),
        "fp": int(ens_op["fp"]),
        "tn": int(ens_op["tn"]),
        "fn": int(ens_op["fn"]),
        "n_pos": n_halluc,
        "n_neg": n_nonhalluc,
    }

    # --- OR combiner (reference): flag if ANY of the 4 individually-calibrated
    #     detectors flags. Reports the resulting specificity (will be < 90%) and
    #     sensitivity, illustrating why a calibrated ensemble is needed.
    ind_thresholds = {d["detector"]: d["threshold"] for d in detector_results}
    or_flags = []
    for r in rows:
        flagged = any(r[k] >= ind_thresholds[name] - EPS
                      for name, k, _, _ in detector_specs)
        or_flags.append(flagged)
    tp_or = sum(1 for r, f in zip(rows, or_flags) if r["hallucinated"] and f)
    fp_or = sum(1 for r, f in zip(rows, or_flags) if not r["hallucinated"] and f)
    tn_or = sum(1 for r, f in zip(rows, or_flags) if not r["hallucinated"] and not f)
    fn_or = sum(1 for r, f in zip(rows, or_flags) if r["hallucinated"] and not f)
    or_result = {
        "detector": "or_combiner_reference",
        "note": "flag if ANY individually-calibrated detector flags (specificity drops below target)",
        "specificity": round(tn_or / n_nonhalluc, 6) if n_nonhalluc else 0.0,
        "sensitivity": round(tp_or / n_halluc, 6) if n_halluc else 0.0,
        "tp": tp_or, "fp": fp_or, "tn": tn_or, "fn": fn_or,
    }

    # --- Hypothesis verdicts.
    def find(name: str) -> dict[str, Any]:
        for d in detector_results:
            if d["detector"] == name:
                return d
        return ensemble_result

    h13a = find("language_id_entropy")
    h13b = find("token_type_diversity")
    h13c = ensemble_result
    cr_res = find("compression_ratio")

    h13a_supported = h13a["sensitivity"] > 0.5
    h13b_supported = h13b["sensitivity"] > 0.5
    h13c_supported = h13c["sensitivity"] > 0.8 and h13c["specificity"] >= 0.9 - EPS

    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ13: Diverse hallucination detector for AISHELL-4",
        "closes_issue": 903,
        "source_data": str(SRC_JSON.relative_to(PROJECT_ROOT)),
        "source_label": "external/sanity-check",
        "method": (
            "reanalysis only (no Whisper / no ASR run); reference-free scores computed "
            "from stored per-speaker separated text, aggregated by max across speakers"
        ),
        "meeting_id": data["meeting_id"],
        "n_windows": n,
        "n_hallucinated_tracks": n_halluc,
        "n_nonhallucinated_tracks": n_nonhalluc,
        "hallucination_label": "always_separated_cpwer > 1.0 (matches RQ12's 37/40 split)",
        "target_specificity": TARGET_SPECIFICITY,
        "aggregation": "max across per-speaker separated transcripts (worst-case track)",
        "detectors": detector_results,
        "ensemble": ensemble_result,
        "or_combiner_reference": or_result,
        "rq12_cr_baseline_context": {
            "rq12_cr_sensitivity": cr_res["sensitivity"],
            "rq12_cr_threshold_fixed_2_4": 2.4,
            "note": (
                "RQ12 used Whisper's fixed CR>2.4 threshold and found 2.7% sensitivity. "
                "Here we RECALIBRATE CR to >=90% specificity on AISHELL-4 non-hallucinated "
                "tracks for a fair detector comparison (the 2.4 threshold was calibrated on "
                "the gold benchmark, not AISHELL-4)."
            ),
        },
        "hypothesis_verdicts": {
            "H13a": {
                "statement": "language-id entropy sensitivity > 50% at >=90% specificity",
                "sensitivity": h13a["sensitivity"],
                "specificity": h13a["specificity"],
                "bootstrap_ci_95": h13a["sensitivity_ci_95"],
                "supported": bool(h13a_supported),
            },
            "H13b": {
                "statement": "token-type diversity sensitivity > 50% at >=90% specificity",
                "sensitivity": h13b["sensitivity"],
                "specificity": h13b["specificity"],
                "bootstrap_ci_95": h13b["sensitivity_ci_95"],
                "supported": bool(h13b_supported),
            },
            "H13c": {
                "statement": "ensemble sensitivity > 80% at >=90% specificity",
                "sensitivity": h13c["sensitivity"],
                "specificity": h13c["specificity"],
                "bootstrap_ci_95": h13c["sensitivity_ci_95"],
                "supported": bool(h13c_supported),
            },
        },
    }

    # --- Write CSV (detector comparison table).
    csv_fields = [
        "detector", "hypothesis", "threshold", "specificity", "sensitivity",
        "sensitivity_ci_lo", "sensitivity_ci_hi",
        "tp", "fp", "tn", "fn", "n_pos", "n_neg",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=csv_fields)
        wr.writeheader()
        for d in detector_results + [ensemble_result]:
            wr.writerow({
                "detector": d["detector"],
                "hypothesis": d.get("hypothesis", ""),
                "threshold": d["threshold"],
                "specificity": d["specificity"],
                "sensitivity": d["sensitivity"],
                "sensitivity_ci_lo": d["sensitivity_ci_95"][0],
                "sensitivity_ci_hi": d["sensitivity_ci_95"][1],
                "tp": d["tp"], "fp": d["fp"], "tn": d["tn"], "fn": d["fn"],
                "n_pos": d["n_pos"], "n_neg": d["n_neg"],
            })

    # --- Write JSON (summary + per-window scores).
    summary_with_rows = dict(summary)
    summary_with_rows["per_window_scores"] = rows
    OUT_JSON.write_text(
        json.dumps(summary_with_rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # --- Console summary.
    print(f"=== RQ13: Diverse hallucination detector (AISHELL-4, {n} tracks) ===")
    print(f"Label: experimental/frontier  |  Source: {SRC_JSON.relative_to(PROJECT_ROOT)}")
    print(f"Hallucinated tracks (sep cpWER > 1.0): {n_halluc}  |  non-hallucinated: {n_nonhalluc}")
    print(f"Target specificity: {TARGET_SPECIFICITY:.0%}  |  aggregation: max across speakers")
    print()
    print(f"{'detector':34s} {'thresh':>9s} {'spec':>6s} {'sens':>6s} {'CI95':>16s}  hyp")
    for d in detector_results + [ensemble_result]:
        ci = d["sensitivity_ci_95"]
        print(f"{d['detector']:34s} {d['threshold']:9.4f} {d['specificity']:6.1%} "
              f"{d['sensitivity']:6.1%} [{ci[0]:5.1%},{ci[1]:5.1%}]  {d.get('hypothesis','')}")
    print()
    print(f"OR combiner (reference): spec={or_result['specificity']:.1%} "
          f"sens={or_result['sensitivity']:.1%} (specificity drops below target)")
    print()
    print("Hypothesis verdicts:")
    print(f"  H13a (lang-id entropy sens > 50%): "
          f"{'SUPPORTED' if h13a_supported else 'NOT SUPPORTED'} "
          f"(sens={h13a['sensitivity']:.1%}, CI=[{h13a['sensitivity_ci_95'][0]:.1%},"
          f"{h13a['sensitivity_ci_95'][1]:.1%}])")
    print(f"  H13b (token diversity sens > 50%): "
          f"{'SUPPORTED' if h13b_supported else 'NOT SUPPORTED'} "
          f"(sens={h13b['sensitivity']:.1%}, CI=[{h13b['sensitivity_ci_95'][0]:.1%},"
          f"{h13b['sensitivity_ci_95'][1]:.1%}])")
    print(f"  H13c (ensemble sens > 80% at >=90% spec): "
          f"{'SUPPORTED' if h13c_supported else 'NOT SUPPORTED'} "
          f"(sens={h13c['sensitivity']:.1%}, spec={h13c['specificity']:.1%}, "
          f"CI=[{h13c['sensitivity_ci_95'][0]:.1%},{h13c['sensitivity_ci_95'][1]:.1%}])")
    print()
    print(f"RQ12 CR baseline (recalibrated to >=90% spec here): sens={cr_res['sensitivity']:.1%} "
          f"(RQ12 fixed CR>2.4 gave 2.7%)")
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
