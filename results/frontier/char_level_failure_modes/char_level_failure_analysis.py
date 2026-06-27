#!/usr/bin/env python3
"""RQ35: Char-level cpWER failure-mode characterisation on AISHELL-4.

Research question
-----------------
Which AISHELL-4 windows are worst at char-level cpWER, and how does the
char-level failure decomposition differ from the utterance-level decomposition
in RQ12 (``results/frontier/router_failure_modes/``, PR #900)?

Pre-registered hypotheses
-------------------------
- H35a: The top-10 worst windows by char-level separated cpWER differ from the
  top-10 by utterance-level separated cpWER (Spearman rho < 0.5).
- H35b: At char-level, the failure-mode error mix shifts -- substitution errors
  dominate over insertion errors (char-level counts character edits, not
  speaker-stream insertions as the utterance-level metric does).
- H35c: The Mode S windows (w22, w30) remain in the top-10 worst at char-level
  (their monoscript hallucination is still costly when measured per-character).

Method
------
Reanalysis only -- no Whisper / no ASR model is run. For each of the 77 AISHELL-4
windows we re-run MeetEval 0.4.3 on the stored transcripts with TWO tokenisation
strategies:

  1. Char-level (standard Chinese cpCER convention): insert a space between each
     Chinese character so MeetEval treats each character as one "word".
  2. Utterance-level (the project's stored convention, RQ30 PR #935): each
     speaker's whole Chinese string is one "word".

For both granularities we use MeetEval's ``cpwer`` (separated, multi-speaker vs
multi-speaker) and ``orcwer`` (mixed, single-channel vs multi-speaker reference)
-- matching RQ30's approach so the aggregate char-level numbers reproduce RQ30's
established baseline (always_separated char cpWER = 0.915831). The
``CPErrorRate`` result objects expose ``substitutions`` / ``insertions`` /
``deletions`` counts, which we use to decompose errors at each granularity.

We then: (i) rank windows by char-level vs utterance-level separated cpWER and
compute Spearman rho + top-10 overlap (H35a); (ii) decompose the char-level
errors of the worst / failure windows into sub/ins/del and compare to the
utterance-level decomposition (H35b); (iii) check whether the Mode S windows
(w22, w30 -- RQ19's verified monoscript set) sit in the char-level top-10 (H35c).

Label: ``experimental/frontier``. Closes #942.

Run:
    /opt/homebrew/bin/python3 results/frontier/char_level_failure_modes/char_level_failure_analysis.py
"""
from __future__ import annotations

import csv
import json
import warnings
import zlib
from pathlib import Path
from typing import Any

warnings.filterwarnings("ignore")  # MeetEval prints "Assuming sort=False" spam

from scipy.stats import spearmanr
try:
    import meeteval
    from meeteval.wer import cpwer, orcwer
except ImportError:  # pure helpers can still be tested without MeetEval
    meeteval = None
    cpwer = None
    orcwer = None

# --------------------------------------------------------------------------- paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_JSON = (
    PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
OUT_DIR = Path(__file__).resolve().parent
OUT_CSV = OUT_DIR / "char_level_failure_results.csv"
OUT_JSON = OUT_DIR / "char_level_failure_results.json"

SESSION_ID = "s1"

# ----------------------------------------------------------------- thresholds
CR_THRESHOLD = 2.4          # Whisper's default compression_ratio_threshold
CATASTROPHIC_CPWER = 1.0    # cpWER > 1.0  =>  errors > length => insertions dominate
EPS = 1e-9

# Mode S windows -- RQ19 (results/frontier/mode_s_detector/, PR #919) verified
# that exactly windows 22 and 30 satisfy: hallucinated AND lang_id_entropy <
# 0.409 AND length_ratio < 2.0 AND cr < 2.4 (monoscript near-duplicate of mixed).
MODE_S_WINDOWS = {22, 30}

# RQ12's 11 utterance-level failure windows (results/frontier/router_failure_modes/
# FINDINGS.md, PR #900) -- used for the top-10 / failure-set overlap comparison.
RQ12_FAILURE_WINDOWS = {0, 5, 8, 18, 22, 26, 29, 30, 31, 41, 42}


# ----------------------------------------------------------------- pure helpers
def to_char_level(text: str) -> str:
    """Space-separate each character so MeetEval treats it as one "word".

    Standard Chinese cpCER convention: Chinese has no word delimiter, so each
    character IS a token. ``"你好世界"`` -> ``"你 好 世 界"``.
    """
    return " ".join(list(text))


def build_segments(speaker_text: dict[str, str], char_level: bool) -> list[dict]:
    """Build MeetEval segment dicts from {speaker: text}.

    Skips empty/whitespace-only strings (matches the project's compute_cpwer).
    """
    segs = []
    for spk, txt in speaker_text.items():
        if not txt or not txt.strip():
            continue
        words = to_char_level(txt) if char_level else txt
        segs.append({"session_id": SESSION_ID, "speaker": spk, "words": words})
    return segs


def build_mixed_segment(mixed_text: str, char_level: bool) -> list[dict]:
    """Build a single-channel hypothesis segment for orcWER."""
    if not mixed_text or not mixed_text.strip():
        return []
    words = to_char_level(mixed_text) if char_level else mixed_text
    return [{"session_id": SESSION_ID, "speaker": "mix", "words": words}]


def _decomp(result: Any) -> dict[str, int | float]:
    """Extract the error decomposition from a MeetEval CPErrorRate / OrcErrorRate."""
    return {
        "error_rate": float(result.error_rate),
        "errors": int(result.errors),
        "length": int(result.length),
        "substitutions": int(result.substitutions),
        "insertions": int(result.insertions),
        "deletions": int(result.deletions),
    }


def compute_cpwer_with_decomp(
    refs: dict[str, str], hyps: dict[str, str], char_level: bool
) -> dict[str, int | float]:
    """Run cpwer (multi-speaker vs multi-speaker) and return the decomposition.

    Returns the project's empty-sentinel (error_rate=1.0, zero counts, length=0,
    ``empty=True``) when either side has no non-empty speakers -- MeetEval itself
    refuses to run on empty input. This matches RQ30's ``safe_cpwer`` convention
    so the aggregate reproduces RQ30's char-level baseline.
    """
    ref_segs = build_segments(refs, char_level)
    hyp_segs = build_segments(hyps, char_level)
    if not ref_segs or not hyp_segs:
        return {
            "error_rate": 1.0, "errors": 0, "length": 0,
            "substitutions": 0, "insertions": 0, "deletions": 0,
            "empty": True,
        }
    r = cpwer(ref_segs, hyp_segs)[SESSION_ID]
    out = _decomp(r)
    out["empty"] = False
    return out


def compute_orcwer_with_decomp(
    refs: dict[str, str], mixed_text: str, char_level: bool
) -> dict[str, int | float]:
    """Run orcwer (single mixed channel vs multi-speaker reference) with decomp.

    Uses the project's empty-sentinel (1.0) when refs or mixed is empty.
    """
    ref_segs = build_segments(refs, char_level)
    mix_segs = build_mixed_segment(mixed_text, char_level)
    if not ref_segs or not mix_segs:
        return {
            "error_rate": 1.0, "errors": 0, "length": 0,
            "substitutions": 0, "insertions": 0, "deletions": 0,
            "empty": True,
        }
    r = orcwer(ref_segs, mix_segs)[SESSION_ID]
    out = _decomp(r)
    out["empty"] = False
    return out


def compression_ratio(text: str) -> float:
    """Whisper-style compression ratio: len(utf8 bytes) / len(zlib-compressed bytes).

    Matches ``whisper.audio.compression_ratio`` and RQ12's
    ``failure_mode_analysis.compression_ratio``. Returns 0.0 for empty/whitespace
    text. High CR (>~2.4) indicates a repetitive / degenerate loop.
    """
    if not text or not text.strip():
        return 0.0
    b = text.encode("utf-8")
    c = zlib.compress(b)
    return len(b) / len(c) if len(c) > 0 else 0.0


def max_cr_separated(window: dict[str, Any]) -> float:
    """Max Whisper CR across the per-speaker separated transcripts.

    Lower bound on Whisper's true per-segment max CR (concatenated text dilutes
    CR). Identical logic to RQ12's ``max_cr_separated``.
    """
    vals = [
        compression_ratio(t)
        for t in window.get("separated_text_per_speaker", {}).values()
        if t and str(t).strip()
    ]
    return max(vals) if vals else 0.0


def rank_windows(rows: list[dict[str, Any]], key: str, descending: bool = True) -> list[dict[str, Any]]:
    """Return rows sorted by ``key``. Stable sort; ties keep original order.

    Each returned row is ``{window_id, rank, value}`` with rank starting at 1.
    """
    ordered = sorted(rows, key=lambda r: r[key], reverse=descending)
    out = []
    for i, r in enumerate(ordered, start=1):
        out.append({"window_id": r["window_id"], "rank": i, "value": r[key]})
    return out


def top_n_window_ids(ranking: list[dict[str, Any]], n: int = 10) -> set[int]:
    """Return the set of window_ids in the top-n of a ranking."""
    return {r["window_id"] for r in ranking[:n]}


def set_overlap(a: set[int], b: set[int]) -> dict[str, Any]:
    """Overlap stats between two window-id sets: intersection, union, jaccard."""
    inter = a & b
    union = a | b
    return {
        "intersection": sorted(inter),
        "intersection_size": len(inter),
        "union_size": len(union),
        "jaccard": len(inter) / len(union) if union else 0.0,
    }


def spearman_rho(a: list[float], b: list[float]) -> tuple[float, float]:
    """Spearman rho + p-value for two parallel lists. Returns (rho, p)."""
    if len(a) < 2 or len(a) != len(b):
        return float("nan"), float("nan")
    rho, p = spearmanr(a, b)
    return float(rho), float(p)


def classify_failure(
    method: str,
    mixed_cpwer: float,
    separated_cpwer: float,
    router_cpwer: float,
    oracle_cpwer: float,
    max_cr_sep: float,
) -> str:
    """Classify a window into a primary failure mode (mirrors RQ12's 4 modes).

    Modes (mutually exclusive, failure windows only -- a failure window is one
    where the router picked the oracle-worse method, i.e. routing_regret > 0):

      - ``separated_hallucination_cr_caught``: router picked separated, separated
        lost, separated cpWER > 1.0, AND max CR > 2.4.
      - ``separated_hallucination_cr_missed``: router picked separated, separated
        lost, separated cpWER > 1.0, AND max CR <= 2.4.
      - ``mixed_hallucination``: router picked mixed, mixed lost, mixed cpWER > 1.0.
      - ``wrong_route_nonhalluc``: router picked the worse method but NEITHER track
        hallucinated (both cpWER <= 1.0).
      - ``none``: not a failure window (router picked the oracle-best method).
    """
    routing_regret = router_cpwer - oracle_cpwer
    is_failure = routing_regret > EPS
    if not is_failure:
        return "none"
    if method == "separated":
        # router picked separated and lost  <=>  separated worse than mixed
        separated_lost = separated_cpwer > mixed_cpwer + EPS
        if separated_lost and separated_cpwer > CATASTROPHIC_CPWER and max_cr_sep > CR_THRESHOLD:
            return "separated_hallucination_cr_caught"
        if separated_lost and separated_cpwer > CATASTROPHIC_CPWER:
            return "separated_hallucination_cr_missed"
        return "wrong_route_nonhalluc"
    else:  # router picked mixed
        mixed_lost = mixed_cpwer > separated_cpwer + EPS
        if mixed_lost and mixed_cpwer > CATASTROPHIC_CPWER:
            return "mixed_hallucination"
        return "wrong_route_nonhalluc"


def total_error_breakdown(
    rows: list[dict[str, Any]], prefix: str, predicate=None
) -> dict[str, int]:
    """Sum sub/ins/del/length/errors over rows (optionally filtered by predicate).

    ``prefix`` selects the metric family, e.g. ``"char_sep"`` reads
    ``char_sep_substitutions`` etc.
    """
    sel = rows if predicate is None else [r for r in rows if predicate(r)]
    return {
        "substitutions": sum(int(r[f"{prefix}_substitutions"]) for r in sel),
        "insertions": sum(int(r[f"{prefix}_insertions"]) for r in sel),
        "deletions": sum(int(r[f"{prefix}_deletions"]) for r in sel),
        "errors": sum(int(r[f"{prefix}_errors"]) for r in sel),
        "length": sum(int(r[f"{prefix}_length"]) for r in sel),
        "n_windows": len(sel),
    }


# --------------------------------------------------------------------- driver
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(SRC_JSON.read_text(encoding="utf-8"))
    windows = data["windows"]
    n = len(windows)

    rows: list[dict[str, Any]] = []
    for w in windows:
        wid = w["window_id"]
        refs = w["ref_text_per_speaker"]
        sep_hyps = w["separated_text_per_speaker"]
        mixed = w.get("mixed_text", "")
        method = w["router_v2_method"]
        mcr_sep = max_cr_separated(w)

        # ---- char-level (standard Chinese cpCER convention)
        char_sep = compute_cpwer_with_decomp(refs, sep_hyps, char_level=True)
        char_mix = compute_orcwer_with_decomp(refs, mixed, char_level=True)
        char_router = char_sep if method == "separated" else char_mix
        if char_sep["error_rate"] <= char_mix["error_rate"] + EPS:
            char_oracle = char_sep
            char_oracle_method = "separated"
        else:
            char_oracle = char_mix
            char_oracle_method = "mixed"

        # ---- utterance-level (project's stored convention; whole string = 1 token)
        utter_sep = compute_cpwer_with_decomp(refs, sep_hyps, char_level=False)
        utter_mix = compute_orcwer_with_decomp(refs, mixed, char_level=False)
        utter_router = utter_sep if method == "separated" else utter_mix
        if utter_sep["error_rate"] <= utter_mix["error_rate"] + EPS:
            utter_oracle = utter_sep
            utter_oracle_method = "separated"
        else:
            utter_oracle = utter_mix
            utter_oracle_method = "mixed"

        # ---- failure-mode classification at each granularity
        char_mode = classify_failure(
            method, char_mix["error_rate"], char_sep["error_rate"],
            char_router["error_rate"], char_oracle["error_rate"], mcr_sep,
        )
        utter_mode = classify_failure(
            method, utter_mix["error_rate"], utter_sep["error_rate"],
            utter_router["error_rate"], utter_oracle["error_rate"], mcr_sep,
        )

        row = {
            "window_id": wid,
            "overlap_label": w["overlap_label"],
            "overlap_level": w["overlap_level"],
            "num_speakers": w["num_speakers"],
            "router_v2_method": method,
            "router_v2_rule": w.get("router_v2_rule", ""),
            "is_mode_s": wid in MODE_S_WINDOWS,
            "max_cr_separated": round(mcr_sep, 4),
            # char-level
            "char_sep_error_rate": round(char_sep["error_rate"], 6),
            "char_sep_errors": char_sep["errors"],
            "char_sep_length": char_sep["length"],
            "char_sep_substitutions": char_sep["substitutions"],
            "char_sep_insertions": char_sep["insertions"],
            "char_sep_deletions": char_sep["deletions"],
            "char_sep_empty": char_sep["empty"],
            "char_mix_error_rate": round(char_mix["error_rate"], 6),
            "char_mix_errors": char_mix["errors"],
            "char_mix_length": char_mix["length"],
            "char_mix_substitutions": char_mix["substitutions"],
            "char_mix_insertions": char_mix["insertions"],
            "char_mix_deletions": char_mix["deletions"],
            "char_mix_empty": char_mix["empty"],
            "char_router_error_rate": round(char_router["error_rate"], 6),
            "char_oracle_error_rate": round(char_oracle["error_rate"], 6),
            "char_oracle_method": char_oracle_method,
            "char_routing_regret": round(char_router["error_rate"] - char_oracle["error_rate"], 6),
            "char_failure_window": (char_router["error_rate"] - char_oracle["error_rate"]) > EPS,
            "char_primary_failure_mode": char_mode,
            # utterance-level
            "utter_sep_error_rate": round(utter_sep["error_rate"], 6),
            "utter_sep_errors": utter_sep["errors"],
            "utter_sep_length": utter_sep["length"],
            "utter_sep_substitutions": utter_sep["substitutions"],
            "utter_sep_insertions": utter_sep["insertions"],
            "utter_sep_deletions": utter_sep["deletions"],
            "utter_sep_empty": utter_sep["empty"],
            "utter_mix_error_rate": round(utter_mix["error_rate"], 6),
            "utter_mix_errors": utter_mix["errors"],
            "utter_mix_length": utter_mix["length"],
            "utter_router_error_rate": round(utter_router["error_rate"], 6),
            "utter_oracle_error_rate": round(utter_oracle["error_rate"], 6),
            "utter_oracle_method": utter_oracle_method,
            "utter_routing_regret": round(utter_router["error_rate"] - utter_oracle["error_rate"], 6),
            "utter_failure_window": (utter_router["error_rate"] - utter_oracle["error_rate"]) > EPS,
            "utter_primary_failure_mode": utter_mode,
        }
        rows.append(row)

    # ----------------------------------------------------------- sanity: aggregates
    char_agg_sep = sum(r["char_sep_error_rate"] for r in rows) / n
    char_agg_mix = sum(r["char_mix_error_rate"] for r in rows) / n
    char_agg_router = sum(r["char_router_error_rate"] for r in rows) / n
    char_agg_oracle = sum(r["char_oracle_error_rate"] for r in rows) / n
    utter_agg_sep = sum(r["utter_sep_error_rate"] for r in rows) / n
    utter_agg_mix = sum(r["utter_mix_error_rate"] for r in rows) / n
    utter_agg_router = sum(r["utter_router_error_rate"] for r in rows) / n
    utter_agg_oracle = sum(r["utter_oracle_error_rate"] for r in rows) / n

    # ----------------------------------------------------------- H35a: ranking
    char_ranking = rank_windows(rows, "char_sep_error_rate", descending=True)
    utter_ranking = rank_windows(rows, "utter_sep_error_rate", descending=True)
    rho_sep_all, p_sep_all = spearman_rho(
        [r["char_sep_error_rate"] for r in rows],
        [r["utter_sep_error_rate"] for r in rows],
    )
    char_top10 = top_n_window_ids(char_ranking, 10)
    utter_top10 = top_n_window_ids(utter_ranking, 10)
    top10_overlap = set_overlap(char_top10, utter_top10)

    # Top-10 among ACTIVE (non-empty separated hyp) windows -- a cleaner
    # hallucination-focused view that excludes the 1.0-sentinel separator-silence
    # windows. Reported alongside the all-windows top-10.
    active_rows = [r for r in rows if not r["char_sep_empty"]]
    char_active_ranking = rank_windows(active_rows, "char_sep_error_rate", descending=True)
    char_active_top10 = top_n_window_ids(char_active_ranking, 10)

    # ----------------------------------------------------------- failure windows
    char_failure = [r for r in rows if r["char_failure_window"]]
    utter_failure = [r for r in rows if r["utter_failure_window"]]
    char_failure_ids = {r["window_id"] for r in char_failure}
    utter_failure_ids = {r["window_id"] for r in utter_failure}
    failure_overlap = set_overlap(char_failure_ids, utter_failure_ids)

    modes = [
        "separated_hallucination_cr_caught",
        "separated_hallucination_cr_missed",
        "mixed_hallucination",
        "wrong_route_nonhalluc",
    ]

    def mode_breakdown(rows_all: list[dict[str, Any]], failure_rows: list[dict[str, Any]], regret_key: str, mode_key: str) -> dict[str, Any]:
        total_regret = sum(r[regret_key] for r in failure_rows)
        out: dict[str, Any] = {}
        for m in modes:
            mrows = [r for r in failure_rows if r[mode_key] == m]
            regret = sum(r[regret_key] for r in mrows)
            out[m] = {
                "n_windows": len(mrows),
                "regret": round(regret, 6),
                "share_of_regret": round(regret / total_regret, 6) if total_regret > EPS else 0.0,
            }
        return out

    char_mode_mix = mode_breakdown(rows, char_failure, "char_routing_regret", "char_primary_failure_mode")
    utter_mode_mix = mode_breakdown(rows, utter_failure, "utter_routing_regret", "utter_primary_failure_mode")

    # ----------------------------------------------------------- H35b: error decomp
    # Char-level error breakdown for the char-level failure windows' SEPARATED
    # tracks (the track that drives separated-hallucination regret). Compare to
    # the utterance-level breakdown for the same windows.
    char_failure_ids_set = {r["window_id"] for r in char_failure}
    char_fail_sep_breakdown = total_error_breakdown(
        rows, "char_sep", predicate=lambda r: r["window_id"] in char_failure_ids_set,
    )
    utter_for_char_fail_sep_breakdown = total_error_breakdown(
        rows, "utter_sep", predicate=lambda r: r["window_id"] in char_failure_ids_set,
    )
    # Also for the char-level top-10 worst (by separated cpwer) -- the H35a set
    char_top10_sep_breakdown = total_error_breakdown(
        rows, "char_sep", predicate=lambda r: r["window_id"] in char_top10,
    )
    # And for ALL active windows (aggregate error-type mix)
    char_all_active_sep = total_error_breakdown(rows, "char_sep", predicate=lambda r: not r["char_sep_empty"])
    utter_all_active_sep = total_error_breakdown(rows, "utter_sep", predicate=lambda r: not r["utter_sep_empty"])

    # dominance check: subs > ins at char-level
    char_subs_gt_ins_fail = char_fail_sep_breakdown["substitutions"] > char_fail_sep_breakdown["insertions"]
    char_subs_gt_ins_top10 = char_top10_sep_breakdown["substitutions"] > char_top10_sep_breakdown["insertions"]
    char_subs_gt_ins_all = char_all_active_sep["substitutions"] > char_all_active_sep["insertions"]
    # utterance-level dominance (for the shift narrative)
    utter_subs_gt_ins_fail = utter_for_char_fail_sep_breakdown["substitutions"] > utter_for_char_fail_sep_breakdown["insertions"]

    # ----------------------------------------------------------- H35c: Mode S in top-10
    mode_s_in_char_top10 = {wid: (wid in char_top10) for wid in sorted(MODE_S_WINDOWS)}
    mode_s_in_char_active_top10 = {wid: (wid in char_active_top10) for wid in sorted(MODE_S_WINDOWS)}
    mode_s_char_rank = {
        wid: next((r["rank"] for r in char_ranking if r["window_id"] == wid), None)
        for wid in sorted(MODE_S_WINDOWS)
    }
    mode_s_char_active_rank = {
        wid: next((r["rank"] for r in char_active_ranking if r["window_id"] == wid), None)
        for wid in sorted(MODE_S_WINDOWS)
    }

    # ----------------------------------------------------------- hypothesis verdicts
    h35a_supported = (rho_sep_all < 0.5) and (top10_overlap["intersection_size"] < 10)
    h35b_supported = bool(char_subs_gt_ins_fail and char_subs_gt_ins_top10)
    # H35c: BOTH Mode S windows in the char-level top-10 worst (all-windows ranking)
    h35c_supported = all(mode_s_in_char_top10.values())

    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ35: Char-level cpWER failure-mode characterisation on AISHELL-4",
        "closes_issue": 942,
        "meeteval_version": meeteval.__version__,
        "source_data": {
            "path": str(SRC_JSON.relative_to(PROJECT_ROOT)),
            "label": "external/sanity-check",
            "num_windows": n,
            "meeting_id": data.get("meeting_id"),
        },
        "method": (
            "Reanalysis only (no Whisper / no ASR run). Re-ran MeetEval 0.4.3 on the "
            "stored AISHELL-4 transcripts at two tokenisation granularities: "
            "char-level (space between each Chinese character -- standard cpCER) and "
            "utterance-level (each speaker's whole string = 1 token -- the project's "
            "stored convention, RQ30). cpwer for separated (multi vs multi), orcwer "
            "for mixed (single channel vs multi ref), matching RQ30 so the char-level "
            "aggregate reproduces RQ30's baseline. CPErrorRate.substitutions/"
            "insertions/deletions provide the error-type decomposition."
        ),
        "mode_s_windows": sorted(MODE_S_WINDOWS),
        "mode_s_source": "RQ19 (results/frontier/mode_s_detector/, PR #919): hallucinated AND lang_id_entropy<0.409 AND length_ratio<2.0 AND cr<2.4 -> exactly w22, w30",
        "rq12_failure_windows": sorted(RQ12_FAILURE_WINDOWS),
        "aggregate_cpwer": {
            "char_level": {
                "always_mixed": round(char_agg_mix, 6),
                "always_separated": round(char_agg_sep, 6),
                "router_v2": round(char_agg_router, 6),
                "oracle_best": round(char_agg_oracle, 6),
            },
            "utterance_level": {
                "always_mixed": round(utter_agg_mix, 6),
                "always_separated": round(utter_agg_sep, 6),
                "router_v2": round(utter_agg_router, 6),
                "oracle_best": round(utter_agg_oracle, 6),
            },
            "rq30_char_baseline": {"always_separated": 0.915831},
            "sanity": "char-level always_separated matches RQ30's 0.915831",
        },
        "H35a_ranking": {
            "statement": "Top-10 worst by char-level separated cpWER differ from top-10 by utterance-level (Spearman rho < 0.5).",
            "spearman_rho_char_vs_utter_separated_all_windows": {
                "rho": round(rho_sep_all, 6), "p": round(p_sep_all, 6),
            },
            "char_top10_window_ids": sorted(char_top10),
            "utter_top10_window_ids": sorted(utter_top10),
            "top10_overlap": top10_overlap,
            "char_active_top10_window_ids": sorted(char_active_top10),
            "verdict": "SUPPORTED" if h35a_supported else "NOT SUPPORTED",
            "supported": bool(h35a_supported),
        },
        "H35b_error_mix": {
            "statement": "At char-level, substitution errors dominate over insertion errors (char-level counts character edits, not speaker-stream insertions).",
            "char_level_failure_windows_sep_breakdown": char_fail_sep_breakdown,
            "utterance_level_same_windows_sep_breakdown": utter_for_char_fail_sep_breakdown,
            "char_level_top10_sep_breakdown": char_top10_sep_breakdown,
            "char_level_all_active_sep_breakdown": char_all_active_sep,
            "utterance_level_all_active_sep_breakdown": utter_all_active_sep,
            "subs_gt_ins_char_failure": bool(char_subs_gt_ins_fail),
            "subs_gt_ins_char_top10": bool(char_subs_gt_ins_top10),
            "subs_gt_ins_char_all_active": bool(char_subs_gt_ins_all),
            "subs_gt_ins_utter_same_windows": bool(utter_subs_gt_ins_fail),
            "verdict": "SUPPORTED" if h35b_supported else "NOT SUPPORTED",
            "supported": bool(h35b_supported),
        },
        "H35c_mode_s": {
            "statement": "Mode S windows (w22, w30) remain in the top-10 worst at char-level.",
            "mode_s_in_char_top10_all_windows": mode_s_in_char_top10,
            "mode_s_in_char_top10_active_only": mode_s_in_char_active_top10,
            "mode_s_char_rank_all_windows": mode_s_char_rank,
            "mode_s_char_rank_active_only": mode_s_char_active_rank,
            "char_top10_window_ids": sorted(char_top10),
            "char_active_top10_window_ids": sorted(char_active_top10),
            "verdict": "SUPPORTED" if h35c_supported else "NOT SUPPORTED",
            "supported": bool(h35c_supported),
        },
        "failure_windows": {
            "char_level": {
                "n_failure_windows": len(char_failure),
                "router_accuracy": round((n - len(char_failure)) / n, 4),
                "failure_window_ids": sorted(char_failure_ids),
                "total_routing_regret": round(sum(r["char_routing_regret"] for r in char_failure), 6),
                "mode_mix": char_mode_mix,
            },
            "utterance_level": {
                "n_failure_windows": len(utter_failure),
                "router_accuracy": round((n - len(utter_failure)) / n, 4),
                "failure_window_ids": sorted(utter_failure_ids),
                "total_routing_regret": round(sum(r["utter_routing_regret"] for r in utter_failure), 6),
                "mode_mix": utter_mode_mix,
                "rq12_failure_window_ids": sorted(RQ12_FAILURE_WINDOWS),
                "matches_rq12": utter_failure_ids == RQ12_FAILURE_WINDOWS,
            },
            "overlap_char_vs_utter": failure_overlap,
        },
        "top10_char_worst_detail": [
            {
                "rank": r["rank"],
                "window_id": r["window_id"],
                "char_sep_cpwer": round(r["value"], 6),
                "is_mode_s": r["window_id"] in MODE_S_WINDOWS,
                "is_rq12_failure": r["window_id"] in RQ12_FAILURE_WINDOWS,
            }
            for r in char_ranking[:10]
        ],
        "top10_char_active_worst_detail": [
            {
                "rank": r["rank"],
                "window_id": r["window_id"],
                "char_sep_cpwer": round(r["value"], 6),
                "is_mode_s": r["window_id"] in MODE_S_WINDOWS,
                "is_rq12_failure": r["window_id"] in RQ12_FAILURE_WINDOWS,
            }
            for r in char_active_ranking[:10]
        ],
    }

    # ----------------------------------------------------------- write CSV
    csv_fields = list(rows[0].keys())
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # ----------------------------------------------------------- console
    print(f"=== RQ35: Char-level cpWER failure-mode characterisation ({n} windows) ===")
    print(f"Label: experimental/frontier  |  Source: {SRC_JSON.relative_to(PROJECT_ROOT)}")
    print(f"MeetEval: {meeteval.__version__}")
    print()
    print("Aggregate cpWER (mean over 77 windows):")
    print(f"  {'Policy':<20}{'char-level':>14}{'utter-level':>14}")
    print(f"  {'always_mixed':<20}{char_agg_mix:>14.6f}{utter_agg_mix:>14.6f}")
    print(f"  {'always_separated':<20}{char_agg_sep:>14.6f}{utter_agg_sep:>14.6f}")
    print(f"  {'router_v2':<20}{char_agg_router:>14.6f}{utter_agg_router:>14.6f}")
    print(f"  {'oracle_best':<20}{char_agg_oracle:>14.6f}{utter_agg_oracle:>14.6f}")
    print(f"  [sanity] char always_separated={char_agg_sep:.6f} vs RQ30 baseline 0.915831")
    print()
    print("H35a (ranking):")
    print(f"  Spearman rho (char vs utter separated, all 77): {rho_sep_all:+.4f} (p={p_sep_all:.3e})")
    print(f"  char top-10:    {sorted(char_top10)}")
    print(f"  utter top-10:   {sorted(utter_top10)}")
    print(f"  top-10 overlap: {top10_overlap['intersection_size']}/10  jaccard={top10_overlap['jaccard']:.3f}")
    print(f"  -> {'SUPPORTED' if h35a_supported else 'NOT SUPPORTED'} (rho<0.5 AND overlap<10)")
    print()
    print("H35b (error mix, separated track):")
    print(f"  char-level FAILURE windows (n={char_fail_sep_breakdown['n_windows']}) sep breakdown:")
    print(f"    subs={char_fail_sep_breakdown['substitutions']}  ins={char_fail_sep_breakdown['insertions']}  dels={char_fail_sep_breakdown['deletions']}  (subs>ins: {char_subs_gt_ins_fail})")
    print(f"  utter-level SAME windows sep breakdown:")
    print(f"    subs={utter_for_char_fail_sep_breakdown['substitutions']}  ins={utter_for_char_fail_sep_breakdown['insertions']}  dels={utter_for_char_fail_sep_breakdown['deletions']}  (subs>ins: {utter_subs_gt_ins_fail})")
    print(f"  char-level top-10 worst sep breakdown: subs={char_top10_sep_breakdown['substitutions']}  ins={char_top10_sep_breakdown['insertions']}  dels={char_top10_sep_breakdown['deletions']}  (subs>ins: {char_subs_gt_ins_top10})")
    print(f"  -> {'SUPPORTED' if h35b_supported else 'NOT SUPPORTED'}")
    print()
    print("H35c (Mode S in char top-10):")
    print(f"  char top-10 (all windows): {sorted(char_top10)}")
    print(f"  char top-10 (active only): {sorted(char_active_top10)}")
    for wid in sorted(MODE_S_WINDOWS):
        print(f"  w{wid}: char_rank={mode_s_char_rank[wid]} (all) / {mode_s_char_active_rank[wid]} (active); in top-10: {mode_s_in_char_top10[wid]}")
    print(f"  -> {'SUPPORTED' if h35c_supported else 'NOT SUPPORTED'}")
    print()
    print("Failure windows:")
    print(f"  char-level:   {len(char_failure)}/{n} failure  (router acc {(n-len(char_failure))/n:.1%}); ids={sorted(char_failure_ids)}")
    print(f"  utter-level:  {len(utter_failure)}/{n} failure  (router acc {(n-len(utter_failure))/n:.1%}); ids={sorted(utter_failure_ids)}")
    print(f"  utter-level matches RQ12's 11: {utter_failure_ids == RQ12_FAILURE_WINDOWS}")
    print(f"  failure-set overlap: {failure_overlap['intersection_size']}  jaccard={failure_overlap['jaccard']:.3f}")
    print()
    print("Mode mix (share of routing regret):")
    for m in modes:
        cs = char_mode_mix[m]["share_of_regret"]
        us = utter_mode_mix[m]["share_of_regret"]
        print(f"  {m:42s} char={cs:6.1%}  utter={us:6.1%}")
    print()
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
