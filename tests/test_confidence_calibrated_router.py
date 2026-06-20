"""Tests for Confidence-Calibrated Router (CCR) -- experimental/frontier."""
from __future__ import annotations

import math

from src.confidence_calibrated_router import (
    SCORING_METHODS,
    extract_signals,
    get_cer,
    hard_regime_analysis,
    route_by_confidence,
    evaluate_routing_policies,
    score_cr_log,
    score_cr_nsp,
    score_cr_nsp_rep,
    score_cr_only,
    score_threshold_gate,
    signal_contribution_analysis,
)


# ---- extract_signals tests -------------------------------------------------------

def test_extract_signals_mixed():
    row = {"cr_mixed": 1.5, "rep_mixed": 3, "nsp_sep1": 0.5}
    signals = extract_signals(row, "mixed")
    assert signals["compression_ratio"] == 1.5
    assert signals["no_speech_prob"] == 0.0  # not available for mixed
    assert signals["repetition_count"] == 3.0


def test_extract_signals_sep():
    row = {"cr_sep1": 1.0, "cr_sep2": 2.0, "nsp_sep1": 0.3, "nsp_sep2": 0.7, "rep_sep1": 1, "rep_sep2": 2}
    signals = extract_signals(row, "sep")
    assert signals["compression_ratio"] == 2.0  # max of sep1, sep2
    assert signals["no_speech_prob"] == 0.7  # max of sep1, sep2
    assert signals["repetition_count"] == 3.0  # sum


def test_extract_signals_sep_trim():
    row = {"cr_sep1": 1.0, "cr_sep2": 2.0, "nsp_sep1": 0.3, "nsp_sep2": 0.7}
    signals = extract_signals(row, "sep_trim")
    # sep_trim uses sep signals as proxy
    assert signals["compression_ratio"] == 2.0


def test_extract_signals_missing_values():
    row = {}
    signals = extract_signals(row, "mixed")
    assert signals["compression_ratio"] == 0.0
    assert signals["repetition_count"] == 0.0


def test_extract_signals_unknown_arm():
    try:
        extract_signals({}, "unknown")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


# ---- get_cer tests ---------------------------------------------------------------

def test_get_cer_normal():
    row = {"cer_mixed": 0.5, "cer_sep": 0.3}
    assert get_cer(row, "mixed") == 0.5
    assert get_cer(row, "sep") == 0.3


def test_get_cer_missing():
    row = {}
    result = get_cer(row, "mixed")
    assert math.isnan(result) or result == 0.0


# ---- Scoring function tests ------------------------------------------------------

def test_score_cr_only_basic():
    # Higher CR => lower confidence
    assert score_cr_only({"compression_ratio": 0.0}) > score_cr_only({"compression_ratio": 5.0})


def test_score_cr_only_monotone():
    s1 = score_cr_only({"compression_ratio": 1.0})
    s2 = score_cr_only({"compression_ratio": 2.0})
    s3 = score_cr_only({"compression_ratio": 3.0})
    assert s1 > s2 > s3


def test_score_cr_nsp_basic():
    # Both signals contribute to lower confidence
    low = score_cr_nsp({"compression_ratio": 0.5, "no_speech_prob": 0.0})
    high_cr = score_cr_nsp({"compression_ratio": 5.0, "no_speech_prob": 0.0})
    high_nsp = score_cr_nsp({"compression_ratio": 0.5, "no_speech_prob": 0.9})
    assert low > high_cr
    assert low > high_nsp


def test_score_cr_nsp_rep_basic():
    high_rep = score_cr_nsp_rep({
        "compression_ratio": 1.0, "no_speech_prob": 0.1, "repetition_count": 10
    })
    low_rep = score_cr_nsp_rep({
        "compression_ratio": 1.0, "no_speech_prob": 0.1, "repetition_count": 0
    })
    assert low_rep > high_rep


def test_score_cr_log_lower_at_high_cr():
    # Log scaling should still decrease with CR, but less aggressively
    s1 = score_cr_log({"compression_ratio": 1.0})
    s2 = score_cr_log({"compression_ratio": 5.0})
    assert s1 > s2


def test_score_cr_log_milder_than_linear():
    # At high CR, log scaling should give higher score than linear
    cr = 10.0
    linear = score_cr_only({"compression_ratio": cr})
    log = score_cr_log({"compression_ratio": cr})
    assert log > linear  # log is more lenient at high CR


def test_score_threshold_gate_below_threshold():
    # Below thresholds: normal CR confidence
    signals = {"compression_ratio": 1.0, "no_speech_prob": 0.3}
    score = score_threshold_gate(signals)
    expected = 1.0 / (1.0 + 1.0)
    assert abs(score - expected) < 1e-6


def test_score_threshold_gate_above_cr_threshold():
    # Above CR threshold: degenerate => 0
    signals = {"compression_ratio": 3.0, "no_speech_prob": 0.3}
    score = score_threshold_gate(signals)
    assert score == 0.0


def test_score_threshold_gate_above_nsp_threshold():
    # Above NSP threshold: degenerate => 0
    signals = {"compression_ratio": 1.0, "no_speech_prob": 0.7}
    score = score_threshold_gate(signals)
    assert score == 0.0


# ---- Routing logic tests --------------------------------------------------------

def test_route_by_confidence_picks_highest():
    scores = {"mixed": 0.8, "sep": 0.3, "sep_trim": 0.5}
    assert route_by_confidence(scores) == "mixed"


def test_route_by_confidence_with_allowed_subset():
    scores = {"mixed": 0.8, "sep": 0.3, "sep_trim": 0.5}
    assert route_by_confidence(scores, ["sep", "sep_trim"]) == "sep_trim"


def test_route_by_confidence_tie_break():
    scores = {"a": 0.5, "b": 0.5}
    # Stable tie-break: first in allowed order
    assert route_by_confidence(scores, ["a", "b"]) == "a"
    assert route_by_confidence(scores, ["b", "a"]) == "b"


def test_route_by_confidence_empty():
    # Should handle gracefully: returns empty string for empty input
    result = route_by_confidence({})
    assert result == ""


# ---- Integration: evaluate_routing_policies tests --------------------------------

def _make_row(
    pair_id: int,
    overlap_ratio: float,
    cer_mixed: float,
    cer_sep: float,
    cer_sep_trim: float,
    cr_mixed: float = 1.0,
    cr_sep1: float = 1.0,
    cr_sep2: float = 1.0,
    nsp_sep1: float = 0.1,
    nsp_sep2: float = 0.1,
    rep_mixed: float = 0.0,
    rep_sep1: float = 0.0,
    rep_sep2: float = 0.0,
) -> dict:
    return {
        "pair_id": str(pair_id),
        "overlap_ratio": str(overlap_ratio),
        "config": "greedy",
        "cer_mixed": str(cer_mixed),
        "cer_sep": str(cer_sep),
        "cer_sep_trim": str(cer_sep_trim),
        "cr_mixed": str(cr_mixed),
        "cr_sep1": str(cr_sep1),
        "cr_sep2": str(cr_sep2),
        "nsp_sep1": str(nsp_sep1),
        "nsp_sep2": str(nsp_sep2),
        "rep_mixed": str(rep_mixed),
        "rep_sep1": str(rep_sep1),
        "rep_sep2": str(rep_sep2),
    }


def test_evaluate_routing_oracle_perfect():
    """Oracle should have zero regret."""
    rows = [
        _make_row(0, 0.5, cer_mixed=0.3, cer_sep=0.5, cer_sep_trim=0.4),
        _make_row(1, 0.8, cer_mixed=0.6, cer_sep=0.2, cer_sep_trim=0.25),
    ]
    result = evaluate_routing_policies(rows, ["mixed", "sep", "sep_trim"])
    assert result["n"] == 2
    assert result["regret_vs_oracle"]["oracle"] == 0.0


def test_evaluate_routing_all_methods_present():
    rows = [
        _make_row(0, 0.5, cer_mixed=0.3, cer_sep=0.5, cer_sep_trim=0.4),
    ]
    result = evaluate_routing_policies(rows, ["mixed", "sep", "sep_trim"])
    for method in SCORING_METHODS:
        assert method in result["mean_cer"]
        assert method in result["regret_vs_oracle"]


def test_evaluate_routing_best_policy():
    """When mixed always wins, best_policy should be fixed_mixed or a method that picks mixed."""
    rows = [
        _make_row(i, ratio, cer_mixed=0.1, cer_sep=0.9, cer_sep_trim=0.8)
        for i, ratio in enumerate([0.1, 0.3, 0.5, 0.7])
    ]
    result = evaluate_routing_policies(rows, ["mixed", "sep", "sep_trim"])
    # All methods should pick mixed (it's always much better)
    for policy, regret in result["regret_vs_oracle"].items():
        if policy == "oracle":
            assert regret == 0.0
        elif policy == "fixed_mixed":
            assert regret == 0.0  # mixed is always best


# ---- Signal contribution tests ---------------------------------------------------

def test_signal_contribution_returns_all_methods():
    rows = [
        _make_row(0, 0.5, cer_mixed=0.3, cer_sep=0.5, cer_sep_trim=0.4),
        _make_row(1, 0.8, cer_mixed=0.6, cer_sep=0.2, cer_sep_trim=0.25),
    ]
    result = signal_contribution_analysis(rows, ["mixed", "sep", "sep_trim"])
    assert "baseline_cr_only_regret" in result
    assert "contributions" in result
    assert "best_method" in result
    for method in SCORING_METHODS:
        if method != "cr_only":
            assert method in result["contributions"]


# ---- Hard regime tests -----------------------------------------------------------

def test_hard_regime_identifies_narrow_margin():
    """Samples with |CER_mixed - CER_sep| < 0.1 should be classified as hard."""
    rows = [
        _make_row(0, 0.5, cer_mixed=0.45, cer_sep=0.50, cer_sep_trim=0.48),  # hard: diff=0.05
        _make_row(1, 0.8, cer_mixed=0.1, cer_sep=0.9, cer_sep_trim=0.8),     # easy: diff=0.7
    ]
    result = hard_regime_analysis(rows, ["mixed", "sep_trim"], margin=0.1)
    assert result["n_hard"] == 1
    assert result["n_easy"] == 1


def test_hard_regime_empty_handling():
    """When no samples are hard, should handle gracefully."""
    rows = [
        _make_row(0, 0.5, cer_mixed=0.1, cer_sep=0.9, cer_sep_trim=0.8),
    ]
    result = hard_regime_analysis(rows, ["mixed", "sep_trim"], margin=0.1)
    assert result["n_hard"] == 0
    assert result["n_easy"] == 1
