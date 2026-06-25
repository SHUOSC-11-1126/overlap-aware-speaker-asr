"""RQ37: Per-speaker cpWER decomposition -- experimental/frontier (Issue #944).

Research question (pre-registered)
----------------------------------
cpWER aggregates errors across all speakers into a single number.  In a
6-speaker meeting the total cpWER may be dominated by 1-2 speakers whose
channel failed (separator collapse, whisper-tiny hallucination, etc.).
This module decomposes cpWER by speaker to answer:

  H37a: Does one speaker contribute > 50% of total cpWER in the worst windows?
  H37b: Is the worst speaker consistent across windows (same speaker worst
        in > 50% of the top-10 worst windows)?
  H37c: Do Mode S windows (separator-collapse) have uniform per-speaker error
        (Gini < 0.3), or is the error concentrated on one speaker?

Method
------
For each window we run MeetEval 0.4.3's ``cpwer`` with character-level
tokenisation (``' '.join(list(text))`` -- the standard Chinese cpCER
convention, matching RQ30's char-level arm).  ``cpwer`` returns the optimal
ref<->hyp speaker assignment and the aggregate error count.  We then use
``CPErrorRate.apply_assignment`` to align the per-speaker texts and compute
a per-speaker Levenshtein distance on the character lists.  The per-speaker
errors sum to the cpWER aggregate errors (including unmatched-hypothesis
insertions attributed to a dedicated ``__unmatched_hyp__`` bucket).

Labels: experimental/frontier.  Source data is external/sanity-check
(AISHELL-4 meeting M_R003S02C01, 77 windows).  Stable tables untouched;
outputs go to results/frontier/per_speaker_cpwer_decomposition/.
"""
from __future__ import annotations

import warnings
from typing import Any

# MeetEval prints "Assuming sort=False" spam on every call; silence it at import.
warnings.filterwarnings("ignore")

# --------------------------------------------------------------------- pure helpers

def to_char_level(text: str) -> str:
    """Space-separate each character so MeetEval treats each character as one "word".

    This is the standard Chinese cpCER convention (Chinese has no word
    delimiter, so each character IS a token).  Matches RQ30's char-level arm.
    """
    return " ".join(list(text))


def _strip_whitespace(text: str) -> str:
    """Remove ALL whitespace characters from a string.

    MeetEval tokenises the ``words`` field with ``str.split()``, which
    collapses runs of whitespace and drops empty tokens.  For char-level
    inputs (``' '.join(list(text))``) this means any whitespace present in
    the RAW text is removed from the token sequence seen by MeetEval.  To
    make per-speaker edit distances sum exactly to MeetEval's aggregate
    ``cpwer.errors``, we replicate that behaviour by stripping whitespace
    before computing Levenshtein and lengths.
    """
    return "".join(ch for ch in text if not ch.isspace())


def char_edit_distance(ref: str, hyp: str) -> int:
    """Levenshtein edit distance between two strings at the character level.

    Pure Python (no MeetEval dependency).  Used to decompose the cpWER
    aggregate error count into per-speaker contributions after the optimal
    ref<->hyp assignment is fixed by ``cpwer``.

    ``ref`` and ``hyp`` are raw strings; the distance is computed over their
    character sequences (NOT over whitespace-split tokens).  This matches
    MeetEval's per-pair WER when each character is one token.
    """
    r = list(ref)
    h = list(hyp)
    n, m = len(r), len(h)
    if n == 0:
        return m
    if m == 0:
        return n
    # Two-row DP for memory efficiency.
    prev = list(range(m + 1))
    cur = [0] * (m + 1)
    for i in range(1, n + 1):
        cur[0] = i
        ri = r[i - 1]
        for j in range(1, m + 1):
            cost = 0 if ri == h[j - 1] else 1
            cur[j] = min(
                prev[j] + 1,        # deletion
                cur[j - 1] + 1,     # insertion
                prev[j - 1] + cost,  # substitution / match
            )
        prev, cur = cur, prev
    return prev[m]


def gini_coefficient(values: list[float]) -> float:
    """Gini coefficient of a list of non-negative values.

    0 = perfect equality, 1 = perfect inequality (one value holds everything).

    Edge cases:
      - empty list or all zeros -> 0.0 (no inequality to measure)
      - single value -> 0.0 (trivially equal with itself)

    Uses the mean-normalised absolute-difference form:
        G = sum_i sum_j |x_i - x_j| / (2 * n * sum(x))
    which is algebraically equivalent to the sorted-rank form and stable for
    small n (Mode S windows have 1-2 speakers).
    """
    n = len(values)
    if n == 0:
        return 0.0
    total = sum(values)
    if total <= 0:
        return 0.0
    abs_diff_sum = 0.0
    for i in range(n):
        for j in range(n):
            abs_diff_sum += abs(values[i] - values[j])
    return abs_diff_sum / (2.0 * n * total)


# ----------------------------------------------------------------- MeetEval bridge

SESSION_ID = "s1"
UNMATCHED_HYP_KEY = "__unmatched_hyp__"


def build_segments(speaker_text: dict[str, str], char_level: bool = True) -> list[dict]:
    """Build MeetEval segment dicts from {speaker: text}.

    Skips empty/whitespace-only strings (matches the project's compute_cpwer
    convention and RQ30's build_segments).
    """
    segs: list[dict] = []
    for spk, txt in speaker_text.items():
        if not txt or not txt.strip():
            continue
        words = to_char_level(txt) if char_level else txt
        segs.append({"session_id": SESSION_ID, "speaker": spk, "words": words})
    return segs


def decompose_cpwer_per_speaker(
    ref_text_per_speaker: dict[str, str],
    hyp_text_per_speaker: dict[str, str],
) -> dict[str, Any]:
    """Decompose a window's cpWER into per-speaker contributions.

    Returns a dict with:
      - ``assignment``: the optimal ref->hyp speaker mapping from MeetEval.
      - ``per_speaker``: list of {speaker, ref_length, hyp_length, errors,
        cpwer, share_of_total_errors} for each REF speaker (speakers with
        non-empty reference text).  ``speaker`` is the ref speaker ID.
      - ``unmatched_hyp``: {errors, hyp_length} for hypothesis speakers that
        had no reference match (pure insertions).  Counted in total_errors.
      - ``total_errors``: equals MeetEval cpwer.errors (verified by caller).
      - ``total_length``: equals MeetEval cpwer.length.
      - ``cpwer``: total_errors / total_length (char-level cpWER).
      - ``meetval_errors`` / ``meetval_length``: MeetEval's aggregate values
        (returned for cross-check; per_speaker errors should sum to
        ``meetval_errors`` including unmatched_hyp.errors).

    The decomposition is deterministic given MeetEval's optimal assignment:
    after the assignment is fixed, each ref speaker's error count is the
    Levenshtein distance between their aligned reference and the matched
    hypothesis.  Unmatched hypothesis speakers contribute their full length
    as insertions.
    """
    # Imported lazily so the module's pure helpers remain importable in
    # environments without MeetEval (e.g. CI test gate without meeteval).
    from meeteval.wer import cpwer as _cpwer

    ref_segs = build_segments(ref_text_per_speaker, char_level=True)
    hyp_segs = build_segments(hyp_text_per_speaker, char_level=True)

    if not ref_segs or not hyp_segs:
        return {
            "assignment": (),
            "per_speaker": [],
            "unmatched_hyp": {"errors": 0, "hyp_length": 0},
            "total_errors": 0,
            "total_length": 0,
            "cpwer": 0.0,
            "meetval_errors": 0,
            "meetval_length": 0,
            "skipped": True,
        }

    result = _cpwer(ref_segs, hyp_segs)[SESSION_ID]
    assignment = tuple(result.assignment)
    meetval_errors = int(result.errors)
    meetval_length = int(result.length)

    # apply_assignment aligns the per-speaker texts under the ref speaker keys
    # (style="ref").  Unmatched hypothesis speakers get a fallback key ('a',
    # 'b', ...) with empty reference text.  We pass the RAW text (not the
    # space-joined char-level form) because char_edit_distance already
    # operates at the character level on raw strings; the char-level
    # tokenisation above was only to obtain MeetEval's optimal assignment and
    # aggregate error count.
    ref_dict = {spk: txt for spk, txt in ref_text_per_speaker.items() if txt and txt.strip()}
    hyp_dict = {spk: txt for spk, txt in hyp_text_per_speaker.items() if txt and txt.strip()}
    aligned_ref, aligned_hyp = result.apply_assignment(ref_dict, hyp_dict, style="ref")

    per_speaker: list[dict[str, Any]] = []
    unmatched_hyp_errors = 0
    unmatched_hyp_length = 0

    # Separate the real ref speakers from the fallback keys (lowercase letters
    # introduced by apply_assignment for unmatched hyp speakers).
    fallback_keys = {k for k in aligned_ref if k not in ref_dict}

    # MeetEval tokenises the ``words`` field with str.split(), which collapses
    # all whitespace and drops empty tokens.  For char-level inputs
    # (' '.join(list(text))) this means internal whitespace in the RAW text is
    # removed from the token sequence.  To make per-speaker edit distances sum
    # exactly to MeetEval's aggregate cpwer.errors, we strip whitespace from
    # the aligned texts before computing Levenshtein and lengths.
    for spk in ref_dict:
        ref_text = _strip_whitespace(aligned_ref.get(spk, ""))
        hyp_text = _strip_whitespace(aligned_hyp.get(spk, ""))
        errors = char_edit_distance(ref_text, hyp_text)
        ref_len = len(ref_text)
        hyp_len = len(hyp_text)
        cpwer = errors / ref_len if ref_len > 0 else 0.0
        per_speaker.append({
            "speaker": spk,
            "ref_length": ref_len,
            "hyp_length": hyp_len,
            "errors": errors,
            "cpwer": cpwer,
        })

    for fk in fallback_keys:
        hyp_text = _strip_whitespace(aligned_hyp.get(fk, ""))
        # ref is empty for fallback keys -> all hyp chars are insertions.
        errors = len(hyp_text)
        unmatched_hyp_errors += errors
        unmatched_hyp_length += len(hyp_text)

    total_errors = sum(p["errors"] for p in per_speaker) + unmatched_hyp_errors
    total_length = sum(p["ref_length"] for p in per_speaker)

    # Compute share of total errors (over real speakers + unmatched bucket).
    denom = total_errors if total_errors > 0 else 1
    for p in per_speaker:
        p["share_of_total_errors"] = p["errors"] / denom
    unmatched_share = unmatched_hyp_errors / denom

    cpwer = total_errors / total_length if total_length > 0 else 0.0

    return {
        "assignment": assignment,
        "per_speaker": per_speaker,
        "unmatched_hyp": {
            "errors": unmatched_hyp_errors,
            "hyp_length": unmatched_hyp_length,
            "share_of_total_errors": unmatched_share,
        },
        "total_errors": total_errors,
        "total_length": total_length,
        "cpwer": cpwer,
        "meetval_errors": meetval_errors,
        "meetval_length": meetval_length,
        "skipped": False,
    }


# ----------------------------------------------------------- ranking + hypotheses

def rank_windows_by_cpwer(window_results: list[dict[str, Any]], top_k: int = 10) -> list[dict[str, Any]]:
    """Rank windows by total char-level cpWER (descending) and return the top-k.

    Each entry in ``window_results`` must contain ``window_id`` and ``cpwer``.
    """
    ranked = sorted(window_results, key=lambda w: w.get("cpwer", 0.0), reverse=True)
    return ranked[:top_k]


def worst_speaker(per_speaker: list[dict[str, Any]]) -> tuple[str, float, int]:
    """Identify the worst real ref speaker by error count.

    Returns (speaker_id, share_of_total_errors, error_count).  If there are
    no real speakers, returns ("", 0.0, 0).
    """
    if not per_speaker:
        return "", 0.0, 0
    worst = max(per_speaker, key=lambda p: p["errors"])
    return worst["speaker"], worst.get("share_of_total_errors", 0.0), worst["errors"]


def worst_speaker_consistency(top_windows: list[dict[str, Any]]) -> tuple[str, float]:
    """Compute the fraction of top windows sharing the same worst speaker.

    Returns (most_common_worst_speaker, fraction_of_top_windows).  Fraction
    is count(most_common) / len(top_windows).
    """
    if not top_windows:
        return "", 0.0
    worst_ids: list[str] = []
    for w in top_windows:
        ws_id, _, _ = worst_speaker(w.get("per_speaker", []))
        if ws_id:
            worst_ids.append(ws_id)
    if not worst_ids:
        return "", 0.0
    from collections import Counter
    counts = Counter(worst_ids)
    most_common_id, most_common_count = counts.most_common(1)[0]
    return most_common_id, most_common_count / len(top_windows)


def evaluate_hypotheses(
    top_windows: list[dict[str, Any]],
    mode_s_window_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate H37a / H37b / H37c against the decomposition.

    H37a SUPPORTED if max worst-speaker share > 0.50 in the top-10 worst windows.
    H37b SUPPORTED if the same speaker is worst in > 50% of the top-10 windows.
    H37c SUPPORTED if Mode S windows have Gini < 0.3 (uniform per-speaker error).
    """
    # H37a: max share > 50% in top-10
    top_shares = [
        worst_speaker(w.get("per_speaker", []))[1] for w in top_windows
    ]
    max_share = max(top_shares) if top_shares else 0.0
    h37a_supported = max_share > 0.50

    # H37b: same speaker worst in > 50% of top-10
    common_id, frac = worst_speaker_consistency(top_windows)
    h37b_supported = frac > 0.50

    # H37c: Mode S windows have Gini < 0.3
    mode_s_ginis: dict[int, float] = {}
    for w in mode_s_window_results:
        wid = w["window_id"]
        per_speaker = w.get("per_speaker", [])
        cpwer_values = [p["cpwer"] for p in per_speaker]
        mode_s_ginis[wid] = gini_coefficient(cpwer_values)
    h37c_supported = all(g < 0.3 for g in mode_s_ginis.values()) if mode_s_ginis else False

    return {
        "H37a": {
            "statement": "One speaker contributes > 50% of total cpWER in the worst windows.",
            "verdict": "SUPPORTED" if h37a_supported else "NOT SUPPORTED",
            "max_worst_speaker_share": max_share,
            "per_window_shares": top_shares,
            "threshold": 0.50,
        },
        "H37b": {
            "statement": "The worst speaker is consistent across windows.",
            "verdict": "SUPPORTED" if h37b_supported else "NOT SUPPORTED",
            "most_common_worst_speaker": common_id,
            "consistency_fraction": frac,
            "threshold": 0.50,
        },
        "H37c": {
            "statement": "Mode S windows have uniform per-speaker error (Gini < 0.3).",
            "verdict": "SUPPORTED" if h37c_supported else "NOT SUPPORTED",
            "mode_s_ginis": mode_s_ginis,
            "threshold": 0.30,
        },
    }
