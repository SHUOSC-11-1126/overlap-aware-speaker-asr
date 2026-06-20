"""Tests for Contrastive Decoding -- experimental/frontier."""
from __future__ import annotations

from src.contrastive_decode import (
    contrastive_confidence,
    is_divergent,
    segment_hybrid,
    text_divergence,
)


# ---- text_divergence tests --------------------------------------------------------

def test_divergence_identical():
    assert text_divergence("hello world", "hello world") == 0.0


def test_divergence_different():
    assert text_divergence("hello", "world") > 0.5


def test_divergence_both_empty():
    assert text_divergence("", "") == 0.0


def test_divergence_one_empty():
    assert text_divergence("", "hello") == 1.0


def test_divergence_partial():
    # Partially similar texts should have moderate divergence
    d = text_divergence("the quick brown fox", "the quick brown dog")
    assert 0.0 < d < 0.5


# ---- is_divergent tests -----------------------------------------------------------

def test_is_divergent_identical():
    assert not is_divergent("hello", "hello", threshold=0.1)


def test_is_divergent_different():
    assert is_divergent("hello", "completely different text", threshold=0.1)


def test_is_divergent_custom_threshold():
    # "abc" vs "xyz" has CER=1.0, so threshold=0.9 still classifies as divergent
    assert is_divergent("abc", "xyz", threshold=0.9)
    # But threshold=1.1 (above max CER) means not divergent
    assert not is_divergent("abc", "xyz", threshold=1.1)


# ---- segment_hybrid tests ---------------------------------------------------------

def test_hybrid_uses_greedy_when_agree():
    result = segment_hybrid("hello world", "hello world")
    assert result == "hello world"


def test_hybrid_uses_fallback_when_divergent():
    greedy = "short"
    fallback = "a much longer and different transcript"
    result = segment_hybrid(greedy, fallback, divergence_threshold=0.1)
    assert result == fallback


def test_hybrid_custom_threshold():
    # "abc" vs "xyz" has CER=1.0, threshold=0.99 still triggers fallback
    greedy = "abc"
    fallback = "xyz"
    result = segment_hybrid(greedy, fallback, divergence_threshold=0.99)
    assert result == fallback
    # But threshold=1.1 (above max CER) keeps greedy
    result2 = segment_hybrid(greedy, fallback, divergence_threshold=1.1)
    assert result2 == greedy


def test_hybrid_both_empty():
    result = segment_hybrid("", "")
    assert result == ""


# ---- contrastive_confidence tests -------------------------------------------------

def test_confidence_identical():
    conf = contrastive_confidence("hello", "hello", 1.0, 1.0)
    assert conf["divergence"] == 0.0
    assert conf["is_divergent"] == 0.0
    assert conf["cr_delta"] == 0.0


def test_confidence_divergent():
    conf = contrastive_confidence("abc", "xyz", 3.0, 1.0)
    assert conf["divergence"] > 0.0
    assert conf["cr_delta"] == 2.0  # greedy CR - fallback CR


def test_confidence_fallback_better_cr():
    conf = contrastive_confidence("hello", "hello", 3.0, 1.0)
    assert conf["cr_delta"] == 2.0  # positive = fallback has lower CR


def test_confidence_contrastive_signal():
    # Higher divergence + larger CR delta → stronger signal
    low = contrastive_confidence("a", "b", 1.0, 0.9)
    high = contrastive_confidence("hello world", "completely different", 3.0, 1.0)
    assert high["contrastive_signal"] > low["contrastive_signal"]
