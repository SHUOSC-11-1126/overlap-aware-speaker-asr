"""RQ16: End-to-end corrected-router simulation on AISHELL-4.

REANALYSIS ONLY — no Whisper / no ASR model is run. This script reads the existing
AISHELL-4 external-validation results (``results/external_sanity_check/aishell4/
rq1_aishell4_validation_results.json``, label ``external/sanity-check``, PR #890) and
simulates an end-to-end *corrected router* that replaces router v2's compression-ratio
(CR) guard with three reference-free detectors computed from the stored per-speaker
separated transcripts:

  1. Language-id entropy detector (RQ13, PR #904): Shannon entropy over Unicode
     script categories, aggregated by MAX across per-speaker separated tracks.
     Threshold 0.409 bits (RQ13's >=90%-specificity operating point, 94.6% sensitivity).
  2. Silence-aware gate proxy (RQ8, PR #893): the RQ8 gate truncates interior silence
     gaps > 0.5 s on separated tracks. The AISHELL-4 audio is not available, so we use
     RQ14's text-proxy: ``length_ratio = separated_total_length / mixed_text_length``.
     A ratio > 2.0 captures the insertion_dominated mode where the separated track is
     far longer than the mixed track (silence-driven insertions). Flag => route mixed.
  3. Mode-specific guards (RQ14): multilingual_mixing (>= 3 distinct content scripts
     on the worst-case speaker track) OR repetition (max Whisper CR > 2.4).

Decision rule: if ANY guard flags the separated track => route to MIXED; else route to
SEPARATED. The corrected router's per-window cpWER is the chosen route's cpWER. We
average over the 77 windows and run seven ablations (each guard alone, each pair, all
three). Bootstrap 95% CIs use 10,000 resamples (seed=42).

Hypotheses
----------
- H16a: corrected router cpWER < always-mixed cpWER (1.17316).
- H16b: corrected router cpWER < router v2 cpWER (1.205628).
- H16c: language-id entropy alone recovers > 50% of router v2's regret gap to oracle.

This script is pure reanalysis (numpy + stdlib only; scipy / sklearn / Whisper are NOT
required). The detector primitives (``script_category``, ``language_id_entropy``,
``compression_ratio``) are lifted verbatim from RQ13/RQ12 so the thresholds are
directly comparable.

Label: experimental/frontier. Closes #908.
"""
from __future__ import annotations

import csv
import json
import math
import unicodedata
import zlib
from pathlib import Path
from typing import Any, Callable

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
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "corrected_router_simulation"
OUT_CSV = OUT_DIR / "simulation_results.csv"
OUT_JSON = OUT_DIR / "simulation_results.json"

# ------------------------------------------------------------------ thresholds
# RQ13 calibrated operating point (>= 90% specificity on AISHELL-4 non-hallucinated
# tracks): threshold 0.409073, specificity 0.925, sensitivity 0.946. We use 0.409.
LANG_ID_ENTROPY_THRESHOLD = 0.409
# RQ8/RQ14 silence-gap text proxy: separated track much longer than mixed track.
LENGTH_RATIO_THRESHOLD = 2.0
# RQ14 multilingual_mixing mode: >= 3 distinct linguistic-content scripts.
N_SCRIPTS_MULTILINGUAL = 3
# Whisper default compression-ratio threshold (RQ12/RQ14 repetition guard).
CR_THRESHOLD = 2.4

CATASTROPHIC_CPWER = 1.0  # cpWER > 1.0 => insertions dominate (hallucination)
N_BOOT = 10000
SEED = 42
EPS = 1e-9

# Linguistic-content script categories (exclude Space / Punct / Other noise).
CONTENT_SCRIPTS = {
    "Han", "Latin", "Hiragana", "Katakana", "Hangul",
    "Cyrillic", "Arabic", "Greek", "Digit",
}


# ----------------------------------------------------------------- CR primitive
def compression_ratio(text: str) -> float:
    """Whisper-style compression ratio: len(utf8 bytes) / len(zlib-compressed bytes).

    Matches ``whisper.audio.compression_ratio`` and RQ12/RQ13's ``compression_ratio``.
    Returns 0.0 for empty/whitespace text. High CR (>~2.4) = repetitive loop."""
    if not text or not text.strip():
        return 0.0
    b = text.encode("utf-8")
    c = zlib.compress(b)
    return len(b) / len(c) if len(c) > 0 else 0.0


# ------------------------------------------------------------- script detection
def script_category(ch: str) -> str:
    """Map a character to a coarse Unicode script category (RQ13 verbatim).

    Uses ``unicodedata.name``. Whitespace -> "Space"; punctuation/symbols -> "Punct";
    control/unknown -> "Other". Sufficient to separate Han / Latin / Hiragana /
    Katakana / Hangul / Cyrillic / Arabic / Greek / Digit, which are exactly the
    scripts RQ12/RQ13 observed in AISHELL-4 hallucination."""
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


# --------------------------------------------------------------- the detectors
def language_id_entropy(text: str) -> float:
    """Shannon entropy (bits) over the script-category distribution of the text (RQ13).

    Clean Chinese (near-monoscript Han) -> entropy ~ 0. Diverse multilingual gibberish
    mixing Han+Latin+Katakana+Hangul -> high entropy."""
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


def distinct_content_scripts(text: str) -> int:
    """Number of distinct linguistic-content script categories in the text.

    Counts categories in ``CONTENT_SCRIPTS`` (Han, Latin, Hiragana, Katakana, Hangul,
    Cyrillic, Arabic, Greek, Digit). Space / Punct / Other are excluded as
    non-linguistic noise so that punctuation-heavy clean Chinese does not trip the
    multilingual_mixing guard. Returns 0 for empty/whitespace text."""
    if not text:
        return 0
    found: set[str] = set()
    for ch in text:
        sc = script_category(ch)
        if sc in CONTENT_SCRIPTS:
            found.add(sc)
    return len(found)


# ------------------------------------------------------------- per-track aggregate
def max_across_speakers(window: dict[str, Any], fn: Callable[[str], float]) -> float:
    """Max of fn(text) over the per-speaker separated transcripts (worst-case track).

    Same convention as RQ12's ``max_cr_separated`` and RQ13's ``max_across_speakers``:
    a window is flagged if ANY speaker track trips the detector. Empty/whitespace
    speaker texts contribute nothing and are effectively skipped."""
    vals = [
        fn(str(t))
        for t in window.get("separated_text_per_speaker", {}).values()
        if t is not None and str(t).strip()
    ]
    return max(vals) if vals else 0.0


def length_ratio(window: dict[str, Any]) -> float:
    """RQ8/RQ14 silence-gap text proxy: separated_total_length / mixed_text_length.

    Oracle-TextGrid separation leaves each speaker's speech at its original positions
    with the rest of the 30 s window silent; Whisper's confident-attractor then
    inserts tokens into the silence, inflating the separated transcript length far
    beyond the mixed transcript. A ratio > 2.0 captures the insertion_dominated mode
    (RQ14). ``mixed_text_length`` is floored at 1 to avoid division by zero."""
    sep = float(window.get("separated_total_length", 0) or 0)
    mix = float(window.get("mixed_text_length", 0) or 0)
    return sep / max(1.0, mix)


# ------------------------------------------------------------- guard computation
def compute_guards(window: dict[str, Any]) -> dict[str, Any]:
    """Compute all detector signals and boolean guard flags for one window."""
    ent = max_across_speakers(window, language_id_entropy)
    mcr = max_across_speakers(window, compression_ratio)
    nscr = int(max_across_speakers(window, lambda t: float(distinct_content_scripts(t))))
    lr = length_ratio(window)

    lang_flag = ent > LANG_ID_ENTROPY_THRESHOLD
    silence_flag = lr > LENGTH_RATIO_THRESHOLD
    multilingual_flag = nscr >= N_SCRIPTS_MULTILINGUAL
    repetition_flag = mcr > CR_THRESHOLD
    mode_flag = multilingual_flag or repetition_flag

    return {
        "lang_id_entropy": ent,
        "length_ratio": lr,
        "max_cr": mcr,
        "n_scripts": nscr,
        "lang_flag": bool(lang_flag),
        "silence_flag": bool(silence_flag),
        "multilingual_flag": bool(multilingual_flag),
        "repetition_flag": bool(repetition_flag),
        "mode_flag": bool(mode_flag),
    }


# Ablation -> (flag it if any of these guards fire). "corrected" = all three.
ABLATIONS: list[tuple[str, list[str]]] = [
    ("lang_only", ["lang_flag"]),
    ("silence_only", ["silence_flag"]),
    ("mode_only", ["mode_flag"]),
    ("lang_silence", ["lang_flag", "silence_flag"]),
    ("lang_mode", ["lang_flag", "mode_flag"]),
    ("silence_mode", ["silence_flag", "mode_flag"]),
    ("corrected", ["lang_flag", "silence_flag", "mode_flag"]),
]


def decision(flags: dict[str, Any], guard_keys: list[str]) -> str:
    """Route to MIXED if any of the guard keys is True; else SEPARATED."""
    return "mixed" if any(flags[k] for k in guard_keys) else "separated"


def cpwer_for(window: dict[str, Any], choice: str) -> float:
    return float(window["always_mixed_cpwer"] if choice == "mixed"
                 else window["always_separated_cpwer"])


# --------------------------------------------------------------------- bootstrap
def bootstrap_mean_ci(values: np.ndarray, n_boot: int = N_BOOT, seed: int = SEED) -> tuple[float, float]:
    """Bootstrap 95% CI for the mean of ``values`` (resample with replacement)."""
    rng = np.random.default_rng(seed)
    n = len(values)
    means: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        means.append(float(values[idx].mean()))
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def bootstrap_diff_ci(
    a: np.ndarray, b: np.ndarray, n_boot: int = N_BOOT, seed: int = SEED
) -> tuple[float, float]:
    """Bootstrap 95% CI for mean(a) - mean(b) (paired, per-window resample)."""
    rng = np.random.default_rng(seed)
    n = len(a)
    diffs: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        diffs.append(float(a[idx].mean() - b[idx].mean()))
    return float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


# --------------------------------------------------------------------- driver
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(SRC_JSON.read_text(encoding="utf-8"))
    windows = data["windows"]
    n = len(windows)

    # Per-window guard computation + decisions.
    rows: list[dict[str, Any]] = []
    for w in windows:
        g = compute_guards(w)
        row: dict[str, Any] = {
            "window_id": w["window_id"],
            "overlap_ratio": w["overlap_ratio"],
            "overlap_label": w["overlap_label"],
            "always_mixed_cpwer": float(w["always_mixed_cpwer"]),
            "always_separated_cpwer": float(w["always_separated_cpwer"]),
            "router_v2_cpwer": float(w["router_v2_cpwer"]),
            "router_v2_method": w["router_v2_method"],
            "oracle_best_cpwer": float(w["oracle_best_cpwer"]),
            "lang_id_entropy": round(g["lang_id_entropy"], 6),
            "length_ratio": round(g["length_ratio"], 6),
            "max_cr": round(g["max_cr"], 6),
            "n_scripts": g["n_scripts"],
            "lang_flag": g["lang_flag"],
            "silence_flag": g["silence_flag"],
            "multilingual_flag": g["multilingual_flag"],
            "repetition_flag": g["repetition_flag"],
            "mode_flag": g["mode_flag"],
        }
        # Each ablation's decision + cpwer.
        for name, keys in ABLATIONS:
            ch = decision(g, keys)
            row[f"{name}_decision"] = ch
            row[f"{name}_cpwer"] = round(cpwer_for(w, ch), 6)
        rows.append(row)

    # Aggregate cpWER per policy (mean over 77 windows).
    def policy_mean(key: str) -> float:
        return float(np.mean([r[key] for r in rows]))

    always_mixed_cpwer = policy_mean("always_mixed_cpwer")
    always_separated_cpwer = policy_mean("always_separated_cpwer")
    router_v2_cpwer = policy_mean("router_v2_cpwer")
    oracle_best_cpwer = policy_mean("oracle_best_cpwer")

    ablation_cpwers: dict[str, float] = {}
    ablation_cis: dict[str, list[float]] = {}
    for name, _ in ABLATIONS:
        vals = np.array([r[f"{name}_cpwer"] for r in rows], dtype=float)
        ablation_cpwers[name] = float(vals.mean())
        lo, hi = bootstrap_mean_ci(vals)
        ablation_cis[name] = [round(lo, 6), round(hi, 6)]

    corrected_cpwer = ablation_cpwers["corrected"]

    # Decision-count breakdown for the corrected router.
    def decision_counts(key: str) -> dict[str, int]:
        counts = {"mixed": 0, "separated": 0}
        for r in rows:
            counts[r[key]] += 1
        return counts

    corrected_counts = decision_counts("corrected_decision")

    # How often each guard fires.
    guard_fire_counts = {
        "lang_flag": sum(1 for r in rows if r["lang_flag"]),
        "silence_flag": sum(1 for r in rows if r["silence_flag"]),
        "multilingual_flag": sum(1 for r in rows if r["multilingual_flag"]),
        "repetition_flag": sum(1 for r in rows if r["repetition_flag"]),
        "mode_flag": sum(1 for r in rows if r["mode_flag"]),
    }

    # Regret reductions (positive = corrected router is better).
    regret_vs_oracle_corrected = corrected_cpwer - oracle_best_cpwer
    regret_vs_oracle_router_v2 = router_v2_cpwer - oracle_best_cpwer
    regret_reduction_vs_router_v2 = router_v2_cpwer - corrected_cpwer
    regret_reduction_vs_mixed = always_mixed_cpwer - corrected_cpwer

    # H16c: fraction of router v2's regret gap to oracle recovered by lang-id alone.
    lang_only_cpwer = ablation_cpwers["lang_only"]
    regret_gap_router_v2 = router_v2_cpwer - oracle_best_cpwer
    regret_gap_lang_only = lang_only_cpwer - oracle_best_cpwer
    lang_only_recovery = (
        (regret_gap_router_v2 - regret_gap_lang_only) / regret_gap_router_v2
        if regret_gap_router_v2 > EPS else 0.0
    )

    # Bootstrap CIs for the hypothesis-test differences (paired per window).
    corrected_arr = np.array([r["corrected_cpwer"] for r in rows], dtype=float)
    mixed_arr = np.array([r["always_mixed_cpwer"] for r in rows], dtype=float)
    rv2_arr = np.array([r["router_v2_cpwer"] for r in rows], dtype=float)
    oracle_arr = np.array([r["oracle_best_cpwer"] for r in rows], dtype=float)
    lang_only_arr = np.array([r["lang_only_cpwer"] for r in rows], dtype=float)

    ci_corrected_minus_mixed = bootstrap_diff_ci(corrected_arr, mixed_arr)
    ci_corrected_minus_rv2 = bootstrap_diff_ci(corrected_arr, rv2_arr)
    # H16c recovery fraction bootstrap: per-resample recovery = (rv2_gap - lang_gap)/rv2_gap.
    rng = np.random.default_rng(SEED)
    recoveries: list[float] = []
    for _ in range(N_BOOT):
        idx = rng.integers(0, n, size=n)
        rv2_gap = float(rv2_arr[idx].mean() - oracle_arr[idx].mean())
        lang_gap = float(lang_only_arr[idx].mean() - oracle_arr[idx].mean())
        if rv2_gap > EPS:
            recoveries.append((rv2_gap - lang_gap) / rv2_gap)
    if recoveries:
        ci_lang_recovery = [
            round(float(np.percentile(recoveries, 2.5)), 6),
            round(float(np.percentile(recoveries, 97.5)), 6),
        ]
    else:
        ci_lang_recovery = [0.0, 0.0]

    # Hypothesis verdicts.
    h16a_supported = corrected_cpwer < always_mixed_cpwer
    h16b_supported = corrected_cpwer < router_v2_cpwer
    h16c_supported = lang_only_recovery > 0.5

    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ16: End-to-end corrected-router simulation on AISHELL-4",
        "closes_issue": 908,
        "source_data": str(SRC_JSON.relative_to(PROJECT_ROOT)),
        "source_label": "external/sanity-check",
        "method": (
            "reanalysis only (no Whisper / no ASR run); reference-free detectors "
            "computed from stored per-speaker separated text. Corrected router routes "
            "to MIXED if any guard flags the separated track, else SEPARATED."
        ),
        "meeting_id": data["meeting_id"],
        "n_windows": n,
        "thresholds": {
            "lang_id_entropy": LANG_ID_ENTROPY_THRESHOLD,
            "length_ratio": LENGTH_RATIO_THRESHOLD,
            "n_scripts_multilingual": N_SCRIPTS_MULTILINGUAL,
            "cr_repetition": CR_THRESHOLD,
            "note": (
                "lang_id_entropy threshold 0.409 from RQ13 (>=90% specificity, 94.6% "
                "sensitivity); length_ratio 2.0 from RQ14 insertion_dominated proxy; "
                "n_scripts >= 3 and max_cr > 2.4 from RQ14 mode guards."
            ),
        },
        "baselines": {
            "always_mixed_cpwer": round(always_mixed_cpwer, 6),
            "always_separated_cpwer": round(always_separated_cpwer, 6),
            "router_v2_cpwer": round(router_v2_cpwer, 6),
            "oracle_best_cpwer": round(oracle_best_cpwer, 6),
        },
        "corrected_router_cpwer": round(corrected_cpwer, 6),
        "corrected_router_ci_95": ablation_cis["corrected"],
        "corrected_router_decision_counts": corrected_counts,
        "guard_fire_counts": guard_fire_counts,
        "ablation_cpwers": {k: round(v, 6) for k, v in ablation_cpwers.items()},
        "ablation_ci_95": ablation_cis,
        "regret_analysis": {
            "router_v2_regret_vs_oracle": round(regret_vs_oracle_router_v2, 6),
            "corrected_regret_vs_oracle": round(regret_vs_oracle_corrected, 6),
            "regret_reduction_vs_router_v2": round(regret_reduction_vs_router_v2, 6),
            "regret_reduction_vs_always_mixed": round(regret_reduction_vs_mixed, 6),
            "router_v2_regret_gap_to_oracle": round(regret_gap_router_v2, 6),
            "lang_only_regret_gap_to_oracle": round(regret_gap_lang_only, 6),
            "lang_only_recovery_fraction": round(lang_only_recovery, 6),
            "lang_only_recovery_ci_95": ci_lang_recovery,
        },
        "hypothesis_verdicts": {
            "H16a": {
                "statement": "corrected router cpWER < always-mixed cpWER (1.17316)",
                "corrected_cpwer": round(corrected_cpwer, 6),
                "always_mixed_cpwer": round(always_mixed_cpwer, 6),
                "delta_corrected_minus_mixed": round(corrected_cpwer - always_mixed_cpwer, 6),
                "bootstrap_ci_95": [round(ci_corrected_minus_mixed[0], 6),
                                    round(ci_corrected_minus_mixed[1], 6)],
                "supported": bool(h16a_supported),
            },
            "H16b": {
                "statement": "corrected router cpWER < router v2 cpWER (1.205628)",
                "corrected_cpwer": round(corrected_cpwer, 6),
                "router_v2_cpwer": round(router_v2_cpwer, 6),
                "delta_corrected_minus_router_v2": round(corrected_cpwer - router_v2_cpwer, 6),
                "bootstrap_ci_95": [round(ci_corrected_minus_rv2[0], 6),
                                    round(ci_corrected_minus_rv2[1], 6)],
                "supported": bool(h16b_supported),
            },
            "H16c": {
                "statement": "language-id entropy alone recovers > 50% of router v2's regret gap to oracle",
                "lang_only_cpwer": round(lang_only_cpwer, 6),
                "router_v2_regret_gap_to_oracle": round(regret_gap_router_v2, 6),
                "lang_only_recovery_fraction": round(lang_only_recovery, 6),
                "bootstrap_ci_95": ci_lang_recovery,
                "supported": bool(h16c_supported),
            },
        },
    }

    # ----------------------------------------------------------- write CSV
    csv_fields = [
        "window_id", "overlap_ratio", "overlap_label",
        "always_mixed_cpwer", "always_separated_cpwer", "router_v2_cpwer",
        "router_v2_method", "oracle_best_cpwer",
        "lang_id_entropy", "length_ratio", "max_cr", "n_scripts",
        "lang_flag", "silence_flag", "multilingual_flag", "repetition_flag", "mode_flag",
        "corrected_decision", "corrected_cpwer",
        "lang_only_decision", "lang_only_cpwer",
        "silence_only_decision", "silence_only_cpwer",
        "mode_only_decision", "mode_only_cpwer",
        "lang_silence_decision", "lang_silence_cpwer",
        "lang_mode_decision", "lang_mode_cpwer",
        "silence_mode_decision", "silence_mode_cpwer",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=csv_fields)
        wr.writeheader()
        for r in rows:
            wr.writerow({k: r.get(k, "") for k in csv_fields})

    # ----------------------------------------------------------- write JSON
    summary_with_rows = dict(summary)
    summary_with_rows["per_window"] = rows
    OUT_JSON.write_text(
        json.dumps(summary_with_rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # ----------------------------------------------------------- console
    print(f"=== RQ16: Corrected-router simulation (AISHELL-4, {n} windows) ===")
    print(f"Label: experimental/frontier  |  Source: {SRC_JSON.relative_to(PROJECT_ROOT)}")
    print()
    print("Baselines:")
    print(f"  always_mixed     : {always_mixed_cpwer:.6f}")
    print(f"  always_separated : {always_separated_cpwer:.6f}")
    print(f"  router_v2        : {router_v2_cpwer:.6f}")
    print(f"  oracle_best      : {oracle_best_cpwer:.6f}")
    print()
    print("Guard fire counts (of 77 windows):")
    for k, v in guard_fire_counts.items():
        print(f"  {k:20s}: {v:2d}")
    print()
    print("Ablation cpWERs (mean over 77 windows, 95% bootstrap CI):")
    for name, _ in ABLATIONS:
        print(f"  {name:16s}: {ablation_cpwers[name]:.6f}  "
              f"CI=[{ablation_cis[name][0]:.4f}, {ablation_cis[name][1]:.4f}]")
    print()
    print(f"Corrected router decisions: mixed={corrected_counts['mixed']}, "
          f"separated={corrected_counts['separated']}")
    print()
    print("Hypothesis verdicts:")
    print(f"  H16a (corrected < always-mixed 1.173): "
          f"{'SUPPORTED' if h16a_supported else 'NOT SUPPORTED'}  "
          f"(corrected={corrected_cpwer:.4f}, delta={corrected_cpwer-always_mixed_cpwer:+.4f}, "
          f"CI=[{ci_corrected_minus_mixed[0]:+.4f}, {ci_corrected_minus_mixed[1]:+.4f}])")
    print(f"  H16b (corrected < router v2 1.206):   "
          f"{'SUPPORTED' if h16b_supported else 'NOT SUPPORTED'}  "
          f"(delta={corrected_cpwer-router_v2_cpwer:+.4f}, "
          f"CI=[{ci_corrected_minus_rv2[0]:+.4f}, {ci_corrected_minus_rv2[1]:+.4f}])")
    print(f"  H16c (lang-id alone recovers >50% of rv2 regret gap): "
          f"{'SUPPORTED' if h16c_supported else 'NOT SUPPORTED'}  "
          f"(recovery={lang_only_recovery:.1%}, CI=[{ci_lang_recovery[0]:.1%}, {ci_lang_recovery[1]:.1%}])")
    print()
    print(f"Regret reduction vs router v2: {regret_reduction_vs_router_v2:+.4f} per window")
    print(f"Regret reduction vs always-mixed: {regret_reduction_vs_mixed:+.4f} per window")
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
