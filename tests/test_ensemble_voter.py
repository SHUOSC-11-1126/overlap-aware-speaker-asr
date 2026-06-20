"""Tests for Multi-Model Ensemble Voter -- experimental/frontier."""
from __future__ import annotations

from src.ensemble_voter import (
    agreement_score,
    ensemble_confidence,
    length_ratio,
    route_by_agreement,
    symmetric_cer,
    text_cer,
)


# ---- text_cer tests ---------------------------------------------------------------

def test_text_cer_identical():
    assert text_cer("hello world", "hello world") == 0.0


def test_text_cer_different():
    assert text_cer("hello", "world") > 0.0


def test_text_cer_empty_ref():
    # Empty reference, non-empty hypothesis: 1.0
    assert text_cer("", "hello") == 1.0


def test_text_cer_both_empty():
    assert text_cer("", "") == 0.0


# ---- symmetric_cer tests ----------------------------------------------------------

def test_symmetric_cer_identical():
    assert symmetric_cer("hello", "hello") == 0.0


def test_symmetric_cer_symmetric():
    # Should be symmetric (average of both directions)
    a = symmetric_cer("hello world", "hello there world")
    b = symmetric_cer("hello there world", "hello world")
    assert abs(a - b) < 1e-6


# ---- length_ratio tests -----------------------------------------------------------

def test_length_ratio_identical():
    assert length_ratio("hello", "world") == 1.0


def test_length_ratio_different():
    assert length_ratio("hi", "hello world") < 1.0
    assert length_ratio("hi", "hello world") > 0.0


def test_length_ratio_both_empty():
    assert length_ratio("", "") == 1.0


def test_length_ratio_one_empty():
    assert length_ratio("", "hello") == 0.0


def test_length_ratio_order_independent():
    # min/max ensures order doesn't matter
    assert length_ratio("hi", "hello world") == length_ratio("hello world", "hi")


# ---- agreement_score tests --------------------------------------------------------

def test_agreement_score_identical():
    texts = {"tiny": "hello world", "base": "hello world", "small": "hello world"}
    score = agreement_score(texts)
    assert score == 1.0


def test_agreement_score_different():
    texts = {"tiny": "completely different text", "base": "hello world", "small": "goodbye"}
    score = agreement_score(texts)
    assert 0.0 <= score < 1.0


def test_agreement_score_two_models():
    texts = {"tiny": "hello", "base": "hello"}
    score = agreement_score(texts)
    assert score == 1.0


def test_agreement_score_single_model():
    texts = {"tiny": "hello"}
    score = agreement_score(texts)
    assert score == 1.0  # single model = perfect agreement


def test_agreement_score_empty():
    texts = {}
    score = agreement_score(texts)
    assert score == 1.0  # degenerate case


def test_agreement_score_partial_agreement():
    # Two models agree, one disagrees
    texts = {
        "tiny": "the quick brown fox",
        "base": "the quick brown fox",
        "small": "a completely different sentence here",
    }
    score = agreement_score(texts)
    assert 0.0 < score < 1.0


# ---- ensemble_confidence tests ----------------------------------------------------

def test_ensemble_confidence_returns_agreement():
    texts = {"tiny": "hello", "base": "hello"}
    conf = ensemble_confidence(texts)
    assert "agreement" in conf
    assert conf["agreement"] == 1.0


def test_ensemble_confidence_returns_metrics():
    texts = {"tiny": "the quick brown fox jumps", "base": "the quick brown fox"}
    conf = ensemble_confidence(texts)
    assert "min_pairwise_cer" in conf
    assert "max_pairwise_cer" in conf
    assert "mean_pairwise_cer" in conf
    assert "length_cv" in conf


def test_ensemble_confidence_with_cr_signals():
    texts = {"tiny": "hello", "base": "hello"}
    cr = {"tiny": 1.0, "base": 1.5}
    conf = ensemble_confidence(texts, cr_signals=cr)
    assert "combined_agreement_cr" in conf
    assert 0.0 <= conf["combined_agreement_cr"] <= 1.0


def test_ensemble_confidence_repetition_metrics():
    texts = {"tiny": "hello world", "base": "hello world"}
    conf = ensemble_confidence(texts)
    assert "max_repetition" in conf
    assert "repetition_spread" in conf


# ---- route_by_agreement tests ----------------------------------------------------

def test_route_by_agreement_picks_highest():
    scores = {"mixed": 0.9, "sep": 0.5}
    assert route_by_agreement(scores) == "mixed"


def test_route_by_agreement_with_allowed():
    scores = {"mixed": 0.9, "sep": 0.5, "sep_trim": 0.7}
    assert route_by_agreement(scores, ["sep", "sep_trim"]) == "sep_trim"


def test_route_by_agreement_tie_break():
    scores = {"a": 0.5, "b": 0.5}
    assert route_by_agreement(scores, ["a", "b"]) == "a"
    assert route_by_agreement(scores, ["b", "a"]) == "b"


def test_route_by_agreement_empty():
    assert route_by_agreement({}) == ""
