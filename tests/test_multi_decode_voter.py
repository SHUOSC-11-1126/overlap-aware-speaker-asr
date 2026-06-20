"""Tests for Multi-Decode Self-Consistency Voter -- experimental/frontier."""
from __future__ import annotations

from src.multi_decode_voter import (
    character_majority_vote,
    decode_agreement,
    route_by_stability,
)


# ---- character_majority_vote tests ------------------------------------------------

def test_vote_identical():
    assert character_majority_vote(["hello", "hello", "hello"]) == "hello"


def test_vote_majority_wins():
    # 2 out of 3 agree on 'a', 1 has 'b'
    texts = ["abc", "abc", "xbc"]
    result = character_majority_vote(texts)
    assert result == "abc"


def test_vote_tie_break_by_first():
    # All different at pos 0: 'a', 'b', 'c' — each appears once
    # Tie-break: max(chars, key=lambda c: (counts[c], -chars.index(c)))
    # counts all 1, so -chars.index(c) decides: 'a' has index 0 → -0 = 0 (largest)
    texts = ["ax", "bx", "cx"]
    result = character_majority_vote(texts)
    assert result[0] == "a"  # first occurrence wins tie


def test_vote_truncates_to_shortest():
    texts = ["abcde", "ab", "abc"]
    result = character_majority_vote(texts)
    assert len(result) == 2  # shortest is "ab" (len 2)


def test_vote_single_text():
    assert character_majority_vote(["hello"]) == "hello"


def test_vote_empty():
    assert character_majority_vote([]) == ""


def test_vote_empty_texts():
    # All empty → returns longest (empty)
    assert character_majority_vote(["", ""]) == ""


def test_vote_one_empty():
    # One empty → min_len = 0 → returns longest
    result = character_majority_vote(["", "hello"])
    assert result == "hello"


# ---- decode_agreement tests -------------------------------------------------------

def test_agreement_identical():
    texts = ["hello world"] * 5
    agr = decode_agreement(texts)
    assert agr["mean_pairwise_cer"] == 0.0
    assert agr["agreement_score"] == 1.0


def test_agreement_different():
    texts = ["hello", "world", "xyz"]
    agr = decode_agreement(texts)
    assert agr["mean_pairwise_cer"] > 0.0
    assert agr["agreement_score"] < 1.0


def test_agreement_single():
    agr = decode_agreement(["hello"])
    assert agr["agreement_score"] == 1.0
    assert agr["mean_pairwise_cer"] == 0.0


def test_agreement_two_texts():
    agr = decode_agreement(["hello", "hello"])
    assert agr["mean_pairwise_cer"] == 0.0


def test_agreement_returns_all_metrics():
    agr = decode_agreement(["abc", "def", "ghi"])
    expected_keys = {"mean_pairwise_cer", "min_pairwise_cer", "max_pairwise_cer",
                     "agreement_score", "length_cv"}
    assert expected_keys.issubset(set(agr.keys()))


def test_agreement_min_leq_mean_leq_max():
    agr = decode_agreement(["hello world", "hello there", "goodbye world"])
    assert agr["min_pairwise_cer"] <= agr["mean_pairwise_cer"]
    assert agr["mean_pairwise_cer"] <= agr["max_pairwise_cer"]


def test_agreement_length_cv_zero_for_same_length():
    agr = decode_agreement(["abc", "def"])
    assert agr["length_cv"] == 0.0


def test_agreement_length_cv_positive_for_different_lengths():
    agr = decode_agreement(["a", "hello world"])
    assert agr["length_cv"] > 0.0


# ---- route_by_stability tests ----------------------------------------------------

def test_route_picks_highest_agreement():
    agr = {"mixed": 0.9, "sep": 0.3}
    assert route_by_stability(agr) == "mixed"


def test_route_with_allowed():
    agr = {"mixed": 0.9, "sep": 0.3, "sep_trim": 0.7}
    assert route_by_stability(agr, ["sep", "sep_trim"]) == "sep_trim"


def test_route_empty():
    assert route_by_stability({}) == ""
