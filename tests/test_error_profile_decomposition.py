"""Tests for Error Profile Decomposition -- experimental/frontier."""
from __future__ import annotations

from src.error_profile_decomposition import (
    compare_error_profiles,
    decompose_errors,
)


# ---- decompose_errors tests -------------------------------------------------------

def test_decompose_identical():
    result = decompose_errors("hello world", "hello world")
    assert result["cer"] == 0.0
    assert result["n_substitutions"] == 0
    assert result["n_deletions"] == 0
    assert result["n_insertions"] == 0
    assert result["is_hallucination_dominated"] is False


def test_decompose_substitution():
    # "abc" → "axc": 1 substitution
    result = decompose_errors("abc", "axc")
    assert result["n_substitutions"] == 1
    assert result["n_deletions"] == 0
    assert result["n_insertions"] == 0
    assert result["substitution_frac"] == 1.0


def test_decompose_insertion():
    # "abc" → "abXc": 1 insertion
    result = decompose_errors("abc", "abXc")
    assert result["n_insertions"] == 1
    assert result["insertion_frac"] == 1.0


def test_decompose_deletion():
    # "abc" → "ac": 1 deletion
    result = decompose_errors("abc", "ac")
    assert result["n_deletions"] == 1
    assert result["deletion_frac"] == 1.0


def test_decompose_hallucination_dominated():
    # Many insertions = hallucination
    result = decompose_errors("abc", "aXXXbXXXcXXX")
    assert result["is_hallucination_dominated"] is True


def test_decompose_not_hallucination():
    # Pure substitution = not hallucination
    result = decompose_errors("abc", "xyz")
    assert result["is_hallucination_dominated"] is False


def test_decompose_fractions_sum_to_one():
    result = decompose_errors("hello world", "goodbye earth")
    total = result["substitution_frac"] + result["deletion_frac"] + result["insertion_frac"]
    assert abs(total - 1.0) < 0.01 or result["n_total_errors"] == 0


def test_decompose_cer():
    # "abc" (3 chars) → "xyz" (3 chars): 3/3 = 1.0
    result = decompose_errors("abc", "xyz")
    assert result["cer"] == 1.0


def test_decompose_empty():
    result = decompose_errors("", "")
    assert result["cer"] == 0.0
    assert result["n_total_errors"] == 0


# ---- compare_error_profiles tests -------------------------------------------------

def test_compare_identical():
    profile = decompose_errors("abc", "abc")
    comp = compare_error_profiles(profile, profile)
    assert comp["cer_delta"] == 0.0
    assert comp["insertion_frac_delta"] == 0.0


def test_compare_different():
    a = decompose_errors("abc", "abc")  # perfect
    b = decompose_errors("abc", "xyz")  # all wrong
    comp = compare_error_profiles(a, b)
    assert comp["cer_delta"] > 0
