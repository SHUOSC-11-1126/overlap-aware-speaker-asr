"""RQ53: Emotion-aware routing simulation (experimental/frontier).

REANALYSIS ONLY — no Whisper, no ASR, no new LLM calls. This script reads three
cached artefacts and simulates four routing policies that combine a text-based
corrected router (RQ16) with an emotion-based reliability signal (RQ36).

Research question
-----------------
RQ36 (PR #956) found that the LLM reads Mode S hallucinated transcripts as
"reliable" (within 1 SD of clean). RQ16 (PR #912) found that the corrected router
(lang-id entropy detector) recovers AISHELL-4 cpWER to 1.043. The stable baseline
found that "the emotion separation tax is opposite of the ASR tax" — separation
HELPS emotion but HURTS ASR.

RQ53 asks: **when the text-based corrected router and an emotion-based signal
disagree, which signal should win? Can a decoupled text+emotion router improve
cpWER over the text-only corrected router?**

This is a SIMULATION using cached data — no new LLM calls. We use RQ36's cached
emotion readings (the LLM's `reliable` field on the concatenated separated
transcript) and RQ16's corrected router decisions to simulate four routing
policies:

1. Text-only  — RQ16's corrected router decision (baseline, cpWER 1.043).
2. Emotion-only — route MIXED if the emotion signal says "unreliable".
3. AND (conservative) — route MIXED if EITHER text OR emotion says unreliable.
4. OR (aggressive)  — route MIXED only if BOTH text AND emotion say unreliable.

Signals
-------
- Text signal:   ``text_unreliable = (RQ16 corrected_decision == "mixed")``.
  The corrected router routes to MIXED when it detects the separated track as
  unreliable (lang-id entropy > 0.409, length-ratio > 2.0, or mode guards).
- Emotion signal: ``emotion_unreliable = (RQ36 reliable == False)``. The LLM's
  own ``reliable`` field on the concatenated separated transcript. For the 10
  silent windows with no transcript (and therefore no cache entry), we use
  RQ36's documented fail-open default (``reliable = True``), so the emotion
  signal says "reliable" — consistent with RQ36's ``_defaults()`` policy.

cpWER for a policy is the mean over the 77 AISHELL-4 windows of the chosen
route's stored cpWER (``always_mixed_cpwer`` if MIXED, else
``always_separated_cpwer``). This reproduces RQ16's 1.04329 for the text-only
policy exactly.

Hypotheses (pre-registered)
---------------------------
- H53a: AND policy (conservative) cpWER <= text-only (1.043). KILLED if > 1.043.
- H53b: OR policy (aggressive) cpWER < text-only (1.043). KILLED if >= 1.043.
- H53c: text and emotion disagree on > 20% of windows. KILLED if <= 20%.

This module is the testable helper layer (pure data loading, signal extraction,
policy simulation, statistics). The driver / orchestration (writing the results
JSON) is the ``run`` / ``main`` pair at the bottom. Unit tests:
``tests/test_emotion_aware_routing.py``.

Label: experimental/frontier. Closes #957.
"""
from __future__ import annotations

import hashlib
import json
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
EMOTION_CACHE_JSON = (
    PROJECT_ROOT
    / "results"
    / "frontier"
    / "llm_emotion_hallucination"
    / "llm_responses_cache.json"
)
RQ16_SIM_JSON = (
    PROJECT_ROOT
    / "results"
    / "frontier"
    / "corrected_router_simulation"
    / "simulation_results.json"
)
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "emotion_aware_routing"
OUT_JSON = OUT_DIR / "emotion_aware_routing_results.json"

# ----------------------------------------------------------------- constants
# RQ16's corrected-router cpWER on the 77 AISHELL-4 windows (the text-only baseline).
TEXT_BASELINE_CPWER = 1.04329
# Disagreement threshold for H53c (fraction of windows where signals differ).
DISAGREEMENT_THRESHOLD = 0.20
# Fail-open default for windows with no emotion reading (RQ36's _defaults() policy).
EMOTION_FAILOPEN_RELIABLE = True
N_BOOT = 10000
SEED = 42
ROUTE_MIXED = "mixed"
ROUTE_SEPARATED = "separated"


# ----------------------------------------------------------------- transcript / hashing
def concat_separated(window: dict[str, Any]) -> str:
    """Concatenate per-speaker separated transcripts (RQ36's emotion source track).

    Empty speakers are skipped. If the concatenation is empty, fall back to the
    mixed transcript (RQ36's documented fallback for silent windows). Returns ""
    only when both are empty (truly silent windows).
    """
    parts = [
        str(t)
        for t in window.get("separated_text_per_speaker", {}).values()
        if t is not None and str(t).strip()
    ]
    joined = "".join(parts)
    if not joined.strip():
        joined = str(window.get("mixed_text", ""))
    return joined


def transcript_hash(text: str) -> str:
    """Stable short hash of a transcript for cache keys (sha1, first 16 hex).

    Identical to ``src.llm_emotion_hallucination.transcript_hash`` so cache keys
    match RQ36's exactly.
    """
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


# ----------------------------------------------------------------- signal extraction
def extract_emotion_signal(
    window: dict[str, Any], cache: dict[str, Any]
) -> tuple[bool | None, bool]:
    """Return ``(reliable, has_reading)`` for one window.

    ``reliable`` is the LLM's ``reliable`` field from RQ36's cache (True/False).
    If the window's transcript has no cache entry (silent window), returns
    ``(EMOTION_FAILOPEN_RELIABLE, False)`` — fail-open, matching RQ36's
    ``_defaults()``. ``has_reading`` distinguishes a true True from a fail-open
    True so the analysis can report coverage.
    """
    transcript = concat_separated(window)
    if not transcript.strip():
        return EMOTION_FAILOPEN_RELIABLE, False
    key = transcript_hash(transcript)
    if key in cache:
        entry = cache[key]
        if isinstance(entry, dict) and "reliable" in entry:
            return bool(entry["reliable"]), True
    return EMOTION_FAILOPEN_RELIABLE, False


def extract_text_signal(rq16_row: dict[str, Any]) -> bool:
    """Return True iff the text-based corrected router says "unreliable".

    RQ16 routes to MIXED when it detects the separated track as unreliable, so
    ``text_unreliable = (corrected_decision == "mixed")``.
    """
    return rq16_row.get("corrected_decision") == ROUTE_MIXED


# ----------------------------------------------------------------- policies
def policy_text_only(text_unreliable: bool) -> str:
    """Text-only baseline: route MIXED iff the text signal says unreliable."""
    return ROUTE_MIXED if text_unreliable else ROUTE_SEPARATED


def policy_emotion_only(emotion_unreliable: bool) -> str:
    """Emotion-only: route MIXED iff the emotion signal says unreliable."""
    return ROUTE_MIXED if emotion_unreliable else ROUTE_SEPARATED


def policy_and(text_unreliable: bool, emotion_unreliable: bool) -> str:
    """AND (conservative): route MIXED if EITHER signal says unreliable."""
    return ROUTE_MIXED if (text_unreliable or emotion_unreliable) else ROUTE_SEPARATED


def policy_or(text_unreliable: bool, emotion_unreliable: bool) -> str:
    """OR (aggressive): route MIXED only if BOTH signals say unreliable."""
    return ROUTE_MIXED if (text_unreliable and emotion_unreliable) else ROUTE_SEPARATED


# ----------------------------------------------------------------- cpWER
def route_cpwer(decision: str, mixed_cpwer: float, separated_cpwer: float) -> float:
    """Return the per-window cpWER for the chosen route."""
    if decision == ROUTE_MIXED:
        return float(mixed_cpwer)
    return float(separated_cpwer)


def compute_policy_cpwer(decisions: list[str], windows: list[dict[str, Any]]) -> float:
    """Mean cpWER over windows for a list of per-window route decisions.

    Each window must have ``always_mixed_cpwer`` and ``always_separated_cpwer``.
    Returns NaN if the window list is empty.
    """
    if not decisions or not windows:
        return float("nan")
    total = 0.0
    for dec, w in zip(decisions, windows):
        total += route_cpwer(
            dec,
            float(w["always_mixed_cpwer"]),
            float(w["always_separated_cpwer"]),
        )
    return total / len(windows)


# ----------------------------------------------------------------- disagreement
def compute_disagreement(
    text_signals: list[bool], emotion_signals: list[bool]
) -> dict[str, Any]:
    """Compute the disagreement fraction between text and emotion signals.

    Returns ``{n, disagree_count, disagree_fraction, both_unreliable,
    both_reliable, text_only_unreliable, emotion_only_unreliable}``. Disagreement
    is counted where the two boolean signals differ. Fraction = disagree_count / n.
    """
    n = len(text_signals)
    if n == 0:
        return {
            "n": 0,
            "disagree_count": 0,
            "disagree_fraction": 0.0,
            "both_unreliable": 0,
            "both_reliable": 0,
            "text_only_unreliable": 0,
            "emotion_only_unreliable": 0,
        }
    disagree = 0
    both_unr = 0
    both_rel = 0
    text_only = 0
    emo_only = 0
    for t, e in zip(text_signals, emotion_signals):
        if t and e:
            both_unr += 1
        elif (not t) and (not e):
            both_rel += 1
        elif t and (not e):
            text_only += 1
            disagree += 1
        else:  # (not t) and e
            emo_only += 1
            disagree += 1
    return {
        "n": n,
        "disagree_count": disagree,
        "disagree_fraction": round(disagree / n, 6),
        "both_unreliable": both_unr,
        "both_reliable": both_rel,
        "text_only_unreliable": text_only,
        "emotion_only_unreliable": emo_only,
    }


# ----------------------------------------------------------------- bootstrap
def bootstrap_cpwer_ci(
    per_window_cpwers: list[float], n_boot: int = N_BOOT, seed: int = SEED
) -> dict[str, float]:
    """Bootstrap 95% CI for the mean of ``per_window_cpwers``.

    Resamples with replacement, computes the mean per resample, and reports the
    2.5 / 97.5 percentiles. Returns ``{mean, ci_low, ci_high, n_boot}``. On
    degenerate input (empty list), returns NaNs.
    """
    arr = np.asarray(per_window_cpwers, dtype=float)
    if arr.size == 0:
        return {"mean": float("nan"), "ci_low": float("nan"),
                "ci_high": float("nan"), "n_boot": n_boot}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, arr.size, size=(n_boot, arr.size))
    means = arr[idx].mean(axis=1)
    return {
        "mean": round(float(arr.mean()), 6),
        "ci_low": round(float(np.percentile(means, 2.5)), 6),
        "ci_high": round(float(np.percentile(means, 97.5)), 6),
        "n_boot": n_boot,
    }


# ----------------------------------------------------------------- hypotheses
def evaluate_hypotheses(
    text_cpwer: float,
    emotion_cpwer: float,
    and_cpwer: float,
    or_cpwer: float,
    disagree_fraction: float,
    baseline: float = TEXT_BASELINE_CPWER,
) -> dict[str, Any]:
    """Evaluate H53a / H53b / H53c.

    - H53a: AND policy cpWER <= baseline (matches text-only). KILLED if > baseline.
    - H53b: OR policy cpWER < baseline (beats text-only). KILLED if >= baseline.
    - H53c: disagreement fraction > 0.20. KILLED if <= 0.20.
    """
    h53a_supported = and_cpwer <= baseline
    h53b_supported = or_cpwer < baseline
    h53c_supported = disagree_fraction > DISAGREEMENT_THRESHOLD
    return {
        "h53a": {
            "statement": f"AND policy cpWER <= text-only baseline ({baseline})",
            "and_cpwer": round(and_cpwer, 6),
            "baseline_cpwer": baseline,
            "delta_and_minus_baseline": round(and_cpwer - baseline, 6),
            "kill_criterion": "AND cpWER > baseline",
            "supported": bool(h53a_supported),
        },
        "h53b": {
            "statement": f"OR policy cpWER < text-only baseline ({baseline})",
            "or_cpwer": round(or_cpwer, 6),
            "baseline_cpwer": baseline,
            "delta_or_minus_baseline": round(or_cpwer - baseline, 6),
            "kill_criterion": "OR cpWER >= baseline",
            "supported": bool(h53b_supported),
        },
        "h53c": {
            "statement": f"text and emotion disagree on > {DISAGREEMENT_THRESHOLD:.0%} of windows",
            "disagree_fraction": round(disagree_fraction, 6),
            "threshold": DISAGREEMENT_THRESHOLD,
            "kill_criterion": f"disagreement <= {DISAGREEMENT_THRESHOLD:.0%}",
            "supported": bool(h53c_supported),
        },
    }


# ----------------------------------------------------------------- data loading
def load_aishell4_windows(path: Path = AISHELL4_JSON) -> list[dict[str, Any]]:
    """Load the 77 AISHELL-4 windows from the RQ1 validation results."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return list(data.get("windows", []))


def load_emotion_cache(path: Path = EMOTION_CACHE_JSON) -> dict[str, Any]:
    """Load RQ36's LLM emotion response cache (keyed by transcript hash)."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_rq16_per_window(path: Path = RQ16_SIM_JSON) -> dict[int, dict[str, Any]]:
    """Load RQ16's per-window corrected-router rows, indexed by window_id."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {int(r["window_id"]): r for r in data.get("per_window", [])}


# ----------------------------------------------------------------- simulation
def simulate(
    windows: list[dict[str, Any]],
    rq16_by_id: dict[int, dict[str, Any]],
    cache: dict[str, Any],
) -> dict[str, Any]:
    """Run the four-policy simulation over the AISHELL-4 windows.

    Returns the full results dict (per-window rows + aggregate cpWERs +
    disagreement + hypothesis verdicts).
    """
    per_window_rows: list[dict[str, Any]] = []
    text_signals: list[bool] = []
    emotion_signals: list[bool] = []
    text_decisions: list[str] = []
    emotion_decisions: list[str] = []
    and_decisions: list[str] = []
    or_decisions: list[str] = []
    n_with_reading = 0

    for w in windows:
        wid = int(w["window_id"])
        rq16 = rq16_by_id[wid]
        reliable, has_reading = extract_emotion_signal(w, cache)
        text_unr = extract_text_signal(rq16)
        emo_unr = reliable is False  # fail-open True -> not unreliable

        if has_reading:
            n_with_reading += 1

        t_dec = policy_text_only(text_unr)
        e_dec = policy_emotion_only(emo_unr)
        a_dec = policy_and(text_unr, emo_unr)
        o_dec = policy_or(text_unr, emo_unr)

        mixed_cpw = float(w["always_mixed_cpwer"])
        sep_cpw = float(w["always_separated_cpwer"])

        text_signals.append(text_unr)
        emotion_signals.append(emo_unr)
        text_decisions.append(t_dec)
        emotion_decisions.append(e_dec)
        and_decisions.append(a_dec)
        or_decisions.append(o_dec)

        per_window_rows.append({
            "window_id": wid,
            "overlap_label": w.get("overlap_label", ""),
            "always_mixed_cpwer": mixed_cpw,
            "always_separated_cpwer": sep_cpw,
            "rq16_corrected_decision": rq16.get("corrected_decision"),
            "emotion_reliable": reliable,
            "emotion_has_reading": has_reading,
            "text_unreliable": text_unr,
            "emotion_unreliable": emo_unr,
            "text_only_decision": t_dec,
            "emotion_only_decision": e_dec,
            "and_decision": a_dec,
            "or_decision": o_dec,
            "text_only_cpwer": route_cpwer(t_dec, mixed_cpw, sep_cpw),
            "emotion_only_cpwer": route_cpwer(e_dec, mixed_cpw, sep_cpw),
            "and_cpwer": route_cpwer(a_dec, mixed_cpw, sep_cpw),
            "or_cpwer": route_cpwer(o_dec, mixed_cpw, sep_cpw),
        })

    n = len(windows)
    text_cpwer = compute_policy_cpwer(text_decisions, windows)
    emotion_cpwer = compute_policy_cpwer(emotion_decisions, windows)
    and_cpwer = compute_policy_cpwer(and_decisions, windows)
    or_cpwer = compute_policy_cpwer(or_decisions, windows)

    disagreement = compute_disagreement(text_signals, emotion_signals)
    # Secondary disagreement restricted to windows with an actual emotion reading.
    reading_mask = [r["emotion_has_reading"] for r in per_window_rows]
    text_signals_read = [t for t, m in zip(text_signals, reading_mask) if m]
    emotion_signals_read = [e for e, m in zip(emotion_signals, reading_mask) if m]
    disagreement_with_readings = compute_disagreement(text_signals_read, emotion_signals_read)

    verdicts = evaluate_hypotheses(
        text_cpwer, emotion_cpwer, and_cpwer, or_cpwer,
        disagreement["disagree_fraction"],
    )

    # Bootstrap CIs for each policy.
    def ci_for(field: str) -> dict[str, float]:
        return bootstrap_cpwer_ci([r[field] for r in per_window_rows])

    policy_cpwers = {
        "text_only": {
            "cpwer": round(text_cpwer, 6),
            "ci_95": ci_for("text_only_cpwer"),
            "decision_counts": _decision_counts(text_decisions),
        },
        "emotion_only": {
            "cpwer": round(emotion_cpwer, 6),
            "ci_95": ci_for("emotion_only_cpwer"),
            "decision_counts": _decision_counts(emotion_decisions),
        },
        "and_conservative": {
            "cpwer": round(and_cpwer, 6),
            "ci_95": ci_for("and_cpwer"),
            "decision_counts": _decision_counts(and_decisions),
        },
        "or_aggressive": {
            "cpwer": round(or_cpwer, 6),
            "ci_95": ci_for("or_cpwer"),
            "decision_counts": _decision_counts(or_decisions),
        },
    }

    return {
        "label": "experimental/frontier",
        "rq": "RQ53: Emotion-aware routing simulation",
        "closes_issue": 957,
        "mode": "B (Focused Extension)",
        "method": (
            "SIMULATION using cached data (no new LLM calls). Combines RQ36's "
            "cached emotion `reliable` field with RQ16's corrected-router "
            "decisions to simulate four routing policies on the 77 AISHELL-4 "
            "windows. cpWER per policy = mean of the chosen route's stored cpWER."
        ),
        "data_sources": {
            "aishell4": {
                "path": str(AISHELL4_JSON.relative_to(PROJECT_ROOT)),
                "label": "external/sanity-check",
                "n_windows": n,
            },
            "emotion_cache": {
                "path": str(EMOTION_CACHE_JSON.relative_to(PROJECT_ROOT)),
                "label": "qualitative/demo",
                "source_rq": "RQ36 (PR #956)",
                "n_cache_entries": len(cache),
                "n_windows_with_reading": n_with_reading,
                "n_windows_missing": n - n_with_reading,
                "failopen_policy": "reliable=True for silent windows (RQ36 _defaults)",
            },
            "rq16_corrected_router": {
                "path": str(RQ16_SIM_JSON.relative_to(PROJECT_ROOT)),
                "label": "experimental/frontier",
                "source_rq": "RQ16 (PR #912)",
                "corrected_router_cpwer": TEXT_BASELINE_CPWER,
            },
        },
        "signals": {
            "text_unreliable": "RQ16 corrected_decision == 'mixed'",
            "emotion_unreliable": "RQ36 reliable == False (fail-open True if no reading)",
        },
        "policies": {
            "text_only": "RQ16's corrected router (baseline)",
            "emotion_only": "route MIXED if emotion says unreliable",
            "and_conservative": "route MIXED if EITHER text OR emotion says unreliable",
            "or_aggressive": "route MIXED only if BOTH text AND emotion say unreliable",
        },
        "baseline_cpwer": TEXT_BASELINE_CPWER,
        "policy_cpwers": policy_cpwers,
        "disagreement": disagreement,
        "disagreement_windows_with_readings": disagreement_with_readings,
        "hypothesis_verdicts": verdicts,
        "per_window": per_window_rows,
    }


def _decision_counts(decisions: list[str]) -> dict[str, int]:
    """Tally mixed/separated decisions."""
    out: dict[str, int] = {ROUTE_MIXED: 0, ROUTE_SEPARATED: 0}
    for d in decisions:
        out[d] = out.get(d, 0) + 1
    return out


# ----------------------------------------------------------------- driver
def run(out_path: Path = OUT_JSON) -> dict[str, Any]:
    """Load data, run the simulation, write the results JSON, return the results."""
    windows = load_aishell4_windows()
    cache = load_emotion_cache()
    rq16_by_id = load_rq16_per_window()
    results = simulate(windows, rq16_by_id, cache)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return results


def main() -> None:
    print("=== RQ53: Emotion-aware routing simulation ===")
    print("Label: experimental/frontier. Mode B (Focused Extension). Closes #957.")
    print()
    results = run()
    print(f"Windows: {len(results['per_window'])}")
    print(f"Windows with emotion reading: "
          f"{results['data_sources']['emotion_cache']['n_windows_with_reading']}")
    print()
    print("Policy cpWERs:")
    for name, info in results["policy_cpwers"].items():
        ci = info["ci_95"]
        print(f"  {name:20s} cpWER={info['cpwer']:.5f} "
              f"CI=[{ci['ci_low']:.5f}, {ci['ci_high']:.5f}] "
              f"decisions={info['decision_counts']}")
    print()
    d = results["disagreement"]
    dr = results["disagreement_windows_with_readings"]
    print(f"Disagreement: {d['disagree_count']}/{d['n']} = {d['disagree_fraction']:.3f} "
          f"(all windows); {dr['disagree_count']}/{dr['n']} = {dr['disagree_fraction']:.3f} "
          f"(windows with readings)")
    print()
    print("Hypothesis verdicts:")
    for h in ("h53a", "h53b", "h53c"):
        v = results["hypothesis_verdicts"][h]
        verdict = "SUPPORTED" if v["supported"] else "KILLED"
        print(f"  {h}: {verdict} — {v['statement']}")
    print()
    print(f"Results written to: {OUT_JSON.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
