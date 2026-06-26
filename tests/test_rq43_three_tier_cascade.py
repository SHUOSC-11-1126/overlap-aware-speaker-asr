"""Tests for RQ43: 3-tier cascade (tiny -> KL gate -> base) Pareto analysis.

 experimental/frontier. Closes #955.

Pins the pure helpers used by
``results/frontier/three_tier_cascade/three_tier_cascade_analysis.py``:

  * character n-gram extraction and frequency distributions
  * background (corpus-pooled) n-gram distribution
  * n-gram KL divergence with ASYMMETRIC Laplace smoothing (P empirical, Q
    add-1 smoothed over Q's own support, sum over P's support), including
    empty / identical / disjoint edge cases
  * base-cpWER estimation via the model_scale base/tiny CER ratio
  * nearest-bucket overlap-ratio lookup into the model_scale per-ratio table
  * cascade aggregation (weighted cpWER + compute from an escalation mask)
  * Pareto dominance classification
  * oracle escalation ordering (worst-tiny-cpWER-first) and deterministic
    random escalation (seeded)
  * threshold sweep (monotone escalation fraction vs threshold)

The full driver ``main()`` is exercised via a smoke test on the real AISHELL-4
source JSON + model_scale CSV (no Whisper / no audio; pure reanalysis).
"""
from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

# The RQ43 analysis script lives in results/frontier/ as a standalone module
# (mirrors RQ19/RQ33 layout). Import via sys.path manipulation.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_DIR = _PROJECT_ROOT / "results" / "frontier" / "three_tier_cascade"
sys.path.insert(0, str(_SCRIPT_DIR))

import three_tier_cascade_analysis as tt  # noqa: E402  (path-injected import)


# ------------------------------------------------------------- n-gram extraction
class TestCharNgrams(unittest.TestCase):
    def test_bigrams_basic(self) -> None:
        self.assertEqual(
            sorted(tt.char_ngrams("abcd", 2)), ["ab", "bc", "cd"]
        )

    def test_whitespace_stripped(self) -> None:
        # internal whitespace is removed before windowing
        self.assertEqual(
            sorted(tt.char_ngrams("a b c", 2)), ["ab", "bc"]
        )

    def test_too_short_returns_single_or_empty(self) -> None:
        # length < n: the whole stripped string is the only "n-gram"
        self.assertEqual(tt.char_ngrams("ab", 3), {"ab"})
        self.assertEqual(tt.char_ngrams("", 2), set())

    def test_trigrams(self) -> None:
        self.assertEqual(
            sorted(tt.char_ngrams("abcde", 3)), ["abc", "bcd", "cde"]
        )

    def test_cjk_chars_are_individual_codepoints(self) -> None:
        # CJK characters are normal Unicode codepoints; bigrams are pairs.
        # Sort both sides: CJK codepoint order differs from positional order
        # (世 U+4E16 < 你 U+4F60 < 好 U+597D < 界 U+754C), so sorted() reorders
        # the actual into ["世界", "你好", "好世"] while the positional list is
        # ["你好", "好世", "世界"]. Comparing sorted-to-sorted isolates the
        # membership check from this codepoint-vs-positional ordering artifact.
        self.assertEqual(
            sorted(tt.char_ngrams("你好世界", 2)),
            sorted(["你好", "好世", "世界"]),
        )


class TestNgramDistribution(unittest.TestCase):
    def test_counts_are_frequencies(self) -> None:
        dist = tt.ngram_distribution("abab", 2)
        self.assertEqual(dist, {"ab": 2, "ba": 1})

    def test_empty_text_empty_dist(self) -> None:
        self.assertEqual(tt.ngram_distribution("", 2), {})

    def test_total_equals_n_minus_1(self) -> None:
        text = "abcdefgh"  # 8 chars -> 7 bigrams
        dist = tt.ngram_distribution(text, 2)
        self.assertEqual(sum(dist.values()), 7)


# ------------------------------------------------------- background distribution
class TestBackgroundDistribution(unittest.TestCase):
    def test_pools_across_texts(self) -> None:
        bg = tt.build_background_distribution(["abab", "abc"], 2)
        # abab -> {ab:2, ba:1}; abc -> {ab:1, bc:1}; pooled {ab:3, ba:1, bc:1}
        self.assertEqual(bg, {"ab": 3, "ba": 1, "bc": 1})

    def test_empty_corpus_empty_dist(self) -> None:
        self.assertEqual(tt.build_background_distribution([], 2), {})

    def test_strips_whitespace_per_text(self) -> None:
        bg = tt.build_background_distribution(["a b", "a c"], 2)
        # "a b" -> "ab" -> {ab:1}; "a c" -> "ac" -> {ac:1}
        self.assertEqual(bg, {"ab": 1, "ac": 1})


# ----------------------------------------------------------- KL divergence (nats)
class TestKLDivergence(unittest.TestCase):
    def test_identical_distributions_near_zero(self) -> None:
        # P == Q under the ASYMMETRIC formulation: P is empirical, Q is
        # add-1 smoothed over its own support, so q(x) = (c+1)/(N+V) < c/N = p(x)
        # for high-count tokens and the KL is a small positive value (bias
        # O(V/N), shrinks as the corpus grows). It is NOT exactly zero.
        p = {"a": 2, "b": 3, "c": 5}
        kl = tt.kl_divergence(p, p)
        self.assertGreaterEqual(kl, 0.0)
        self.assertLess(kl, 0.01)  # small positive bias from Q smoothing

    def test_non_negative(self) -> None:
        p = {"a": 10, "b": 1}
        q = {"a": 1, "b": 10, "c": 5}
        self.assertGreaterEqual(tt.kl_divergence(p, q), 0.0)

    def test_disjoint_vocab_positive(self) -> None:
        # disjoint support => high KL (Q smoothing gives q(x) = 1/(N_q + V_q),
        # P concentrated on a token Q lacks => high p(x)/q(x) ratio)
        p = {"a": 10}
        q = {"b": 10}
        kl = tt.kl_divergence(p, q)
        self.assertGreater(kl, 0.0)

    def test_concentrated_vs_diverse_is_high(self) -> None:
        # A concentrated distribution (one bigram dominates) diverges more
        # from a diverse background than a balanced distribution does.
        concentrated = {"aa": 100}                      # Mode-S-like: repetitive
        diverse = {"ab": 10, "bc": 10, "cd": 10, "da": 10}
        background = {"ab": 25, "bc": 25, "cd": 25, "da": 25}
        self.assertGreater(
            tt.kl_divergence(concentrated, background),
            tt.kl_divergence(diverse, background),
        )

    def test_empty_both_is_zero(self) -> None:
        self.assertEqual(tt.kl_divergence({}, {}), 0.0)

    def test_empty_p_against_q_is_zero(self) -> None:
        # Empty P has no support; KL = sum over P's support of p(x)*log(p(x)/q(x))
        # is the empty sum = 0 by convention. (The asymmetric formulation does
        # not invent a uniform P over Q's vocab; P stays empty.)
        kl = tt.kl_divergence({}, {"a": 5, "b": 5})
        self.assertEqual(kl, 0.0)

    def test_q_smoothing_handles_missing_tokens(self) -> None:
        # P has a token Q lacks; Q's add-1 smoothing over its own support keeps
        # q(x) > 0 (avoiding log(0)). P's missing-from-Q token gets q(x) = 1/denom_q.
        p = {"x": 4, "y": 1}
        q = {"y": 4, "z": 1}
        kl = tt.kl_divergence(p, q)
        # finite and positive (P leans toward "x" which is rare in Q)
        self.assertTrue(math.isfinite(kl))
        self.assertGreater(kl, 0.0)

    def test_p_empirical_q_smoothed_scales_correctly(self) -> None:
        # Sanity: doubling P's counts (same distribution) should not change KL,
        # because P is empirical (scale-invariant) and Q is fixed.
        q = {"a": 5, "b": 5}
        kl1 = tt.kl_divergence({"a": 1, "b": 1}, q)
        kl2 = tt.kl_divergence({"a": 100, "b": 100}, q)
        # identical distributions => identical KL (P is normalised)
        self.assertAlmostEqual(kl1, kl2, places=9)


# --------------------------------------------------- base-cpWER estimation (ratio)
class TestEstimateBaseCpwer(unittest.TestCase):
    def test_applies_ratio(self) -> None:
        self.assertAlmostEqual(tt.estimate_base_cpwer(1.0, 0.4283), 0.4283, places=6)
        self.assertAlmostEqual(tt.estimate_base_cpwer(2.5, 0.5), 1.25, places=6)

    def test_zero_tiny_zero_base(self) -> None:
        self.assertEqual(tt.estimate_base_cpwer(0.0, 0.4283), 0.0)

    def test_ratio_above_one_keeps_base_worse(self) -> None:
        # if ratio > 1 (base worse than tiny at this bucket), base > tiny
        self.assertAlmostEqual(tt.estimate_base_cpwer(0.8, 1.2), 0.96, places=6)


# --------------------------------------- overlap-ratio bucket lookup (model_scale)
class TestRatioLookup(unittest.TestCase):
    def setUp(self) -> None:
        # mirror the model_scale per-ratio summary shape
        self.per_ratio = [
            {"overlap_ratio": 0.0,  "cer_tiny": 0.50, "cer_base": 0.26},
            {"overlap_ratio": 0.15, "cer_tiny": 0.55, "cer_base": 0.26},
            {"overlap_ratio": 0.35, "cer_tiny": 1.67, "cer_base": 0.38},
            {"overlap_ratio": 0.6,  "cer_tiny": 0.67, "cer_base": 0.51},
            {"overlap_ratio": 0.9,  "cer_tiny": 0.82, "cer_base": 0.77},
        ]

    def test_nearest_bucket(self) -> None:
        self.assertEqual(tt.nearest_ratio(self.per_ratio, 0.0)["overlap_ratio"], 0.0)
        self.assertEqual(tt.nearest_ratio(self.per_ratio, 0.4)["overlap_ratio"], 0.35)
        self.assertEqual(tt.nearest_ratio(self.per_ratio, 0.8)["overlap_ratio"], 0.9)
        self.assertEqual(tt.nearest_ratio(self.per_ratio, 0.12)["overlap_ratio"], 0.15)

    def test_ratio_value(self) -> None:
        row = tt.nearest_ratio(self.per_ratio, 0.4)
        ratio = row["cer_base"] / row["cer_tiny"]
        self.assertAlmostEqual(ratio, 0.38 / 1.67, places=6)

    def test_out_of_range_clamps_to_nearest(self) -> None:
        # below min -> min; above max -> max
        self.assertEqual(tt.nearest_ratio(self.per_ratio, -0.5)["overlap_ratio"], 0.0)
        self.assertEqual(tt.nearest_ratio(self.per_ratio, 5.0)["overlap_ratio"], 0.9)


# ----------------------------------------------------------- cascade aggregation
class TestCascadeAggregate(unittest.TestCase):
    def test_all_tiny_equals_always_tiny(self) -> None:
        tiny = [0.5, 0.6, 0.4, 0.7]
        base = [0.2, 0.3, 0.2, 0.3]
        mask = [False, False, False, False]
        cpwer, compute, frac = tt.cascade_aggregate(tiny, base, mask, 1.0, 1.93)
        self.assertAlmostEqual(cpwer, 0.55, places=9)
        self.assertAlmostEqual(compute, 1.0, places=9)
        self.assertEqual(frac, 0.0)

    def test_all_base_equals_always_base(self) -> None:
        tiny = [0.5, 0.6, 0.4, 0.7]
        base = [0.2, 0.3, 0.2, 0.3]
        mask = [True, True, True, True]
        cpwer, compute, frac = tt.cascade_aggregate(tiny, base, mask, 1.0, 1.93)
        self.assertAlmostEqual(cpwer, 0.25, places=9)
        self.assertAlmostEqual(compute, 1.93, places=9)
        self.assertEqual(frac, 1.0)

    def test_partial_escalation(self) -> None:
        tiny = [0.5, 0.6, 0.4, 0.7]
        base = [0.2, 0.3, 0.2, 0.3]
        mask = [False, True, False, True]
        cpwer, compute, frac = tt.cascade_aggregate(tiny, base, mask, 1.0, 1.93)
        # cpwer = mean(0.5, 0.3, 0.4, 0.3) = 0.375
        self.assertAlmostEqual(cpwer, 0.375, places=9)
        # compute = 1.0*0.5 + 1.93*0.5 = 1.465
        self.assertAlmostEqual(compute, 1.465, places=9)
        self.assertAlmostEqual(frac, 0.5, places=9)

    def test_compute_uses_fraction(self) -> None:
        tiny = [1.0] * 10
        base = [0.5] * 10
        mask = [True] * 3 + [False] * 7
        _, compute, frac = tt.cascade_aggregate(tiny, base, mask, 1.0, 1.93)
        self.assertAlmostEqual(frac, 0.3, places=9)
        self.assertAlmostEqual(compute, 1.0 * 0.7 + 1.93 * 0.3, places=9)


# ------------------------------------------------------------- Pareto dominance
class TestParetoClassify(unittest.TestCase):
    def test_frontier_when_undominated(self) -> None:
        policies = [
            {"name": "tiny", "cpwer": 0.50, "compute": 1.0},
            {"name": "base", "cpwer": 0.20, "compute": 1.93},
            {"name": "cascade", "cpwer": 0.35, "compute": 1.40},
        ]
        out = tt.classify_pareto(policies)
        by_name = {p["name"]: p for p in out}
        # none of these strictly dominates another (tiny: high cpwer low compute;
        # base: low cpwer high compute; cascade: middle on both)
        self.assertEqual(by_name["tiny"]["pareto_status"], "frontier")
        self.assertEqual(by_name["base"]["pareto_status"], "frontier")
        self.assertEqual(by_name["cascade"]["pareto_status"], "frontier")

    def test_dominated_marked(self) -> None:
        policies = [
            {"name": "tiny", "cpwer": 0.50, "compute": 1.0},
            {"name": "base", "cpwer": 0.20, "compute": 1.93},
            {"name": "dominated", "cpwer": 0.55, "compute": 1.10},  # worse than tiny on both
        ]
        out = tt.classify_pareto(policies)
        by_name = {p["name"]: p for p in out}
        self.assertEqual(by_name["dominated"]["pareto_status"], "dominated")
        self.assertEqual(by_name["dominated"]["dominated_by"], "tiny")

    def test_tie_is_not_domination(self) -> None:
        # equal on both axes is not strict domination
        policies = [
            {"name": "a", "cpwer": 0.3, "compute": 1.0},
            {"name": "b", "cpwer": 0.3, "compute": 1.0},
        ]
        out = tt.classify_pareto(policies)
        self.assertTrue(all(p["pareto_status"] == "frontier" for p in out))


# ----------------------------------------------------- oracle / random escalation
class TestOracleOrdering(unittest.TestCase):
    def test_worst_first(self) -> None:
        tiny = [0.5, 0.8, 0.3, 0.6]
        base = [0.2, 0.4, 0.2, 0.3]
        # improvement = tiny - base = [0.3, 0.4, 0.1, 0.3]
        # order by improvement desc: idx1 (0.4), idx0 (0.3), idx3 (0.3), idx2 (0.1)
        order = tt.oracle_escalation_order(tiny, base)
        self.assertEqual(order[0], 1)
        self.assertEqual(order[-1], 2)
        # ties (idx0, idx3 both 0.3) broken by original index order
        self.assertEqual(sorted(order[:3]), [0, 1, 3])

    def test_order_length(self) -> None:
        tiny = [0.1, 0.2, 0.3]
        base = [0.05, 0.1, 0.15]
        order = tt.oracle_escalation_order(tiny, base)
        self.assertEqual(len(order), 3)
        self.assertEqual(sorted(order), [0, 1, 2])


class TestRandomEscalation(unittest.TestCase):
    def test_deterministic_with_seed(self) -> None:
        order1 = tt.random_escalation_order(10, seed=42)
        order2 = tt.random_escalation_order(10, seed=42)
        self.assertEqual(order1, order2)

    def test_different_seeds_differ(self) -> None:
        order1 = tt.random_escalation_order(20, seed=1)
        order2 = tt.random_escalation_order(20, seed=2)
        self.assertNotEqual(order1, order2)

    def test_is_permutation(self) -> None:
        order = tt.random_escalation_order(8, seed=7)
        self.assertEqual(sorted(order), list(range(8)))


# --------------------------------------------------------------- threshold sweep
class TestThresholdSweep(unittest.TestCase):
    def test_higher_threshold_lower_fraction(self) -> None:
        # KL scores with a spread; as threshold rises, fewer escalate
        kl_scores = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
        thresholds = [0.0, 1.5, 2.5, 5.0]
        fracs = []
        for t in thresholds:
            mask = [s > t for s in kl_scores]
            fracs.append(sum(mask) / len(mask))
        self.assertGreater(fracs[0], fracs[1])
        self.assertGreater(fracs[1], fracs[2])
        self.assertGreater(fracs[2], fracs[3])

    def test_threshold_above_all_escalates_none(self) -> None:
        kl_scores = [1.0, 2.0, 3.0]
        mask = tt.escalation_mask(kl_scores, threshold=10.0)
        self.assertFalse(any(mask))

    def test_threshold_below_all_escalates_all(self) -> None:
        kl_scores = [1.0, 2.0, 3.0]
        mask = tt.escalation_mask(kl_scores, threshold=0.0)
        self.assertTrue(all(mask))


# ----------------------------------------------------------- driver smoke test
class TestDriverSmoke(unittest.TestCase):
    """Smoke-test main() on the real AISHELL-4 + model_scale sources.

    Verifies the script runs end-to-end, writes the expected outputs, and
    produces sane aggregate numbers (cpWER within [base, tiny], compute within
    [1.0, 1.93], Pareto frontier non-empty).
    """
    @classmethod
    def setUpClass(cls) -> None:
        cls.out_dir = _SCRIPT_DIR
        # run main() once; outputs are deterministic and cached on disk.
        tt.main()

    def test_writes_outputs(self) -> None:
        self.assertTrue((self.out_dir / "three_tier_cascade_results.csv").exists())
        self.assertTrue((self.out_dir / "three_tier_cascade_results.json").exists())
        self.assertTrue((self.out_dir / "pareto_frontier.csv").exists())

    def test_summary_fields_present(self) -> None:
        summary = json.loads(
            (self.out_dir / "three_tier_cascade_results.json").read_text(encoding="utf-8")
        )
        for key in ("label", "rq", "closes_issue", "n_windows",
                    "policies", "pareto_frontier", "hypothesis_verdicts",
                    "threshold_sweep", "kl_threshold"):
            self.assertIn(key, summary, msg=f"missing {key}")
        self.assertEqual(summary["label"], "experimental/frontier")
        self.assertEqual(summary["closes_issue"], 955)

    def test_cascade_between_tiny_and_base(self) -> None:
        summary = json.loads(
            (self.out_dir / "three_tier_cascade_results.json").read_text(encoding="utf-8")
        )
        pol = {p["name"]: p for p in summary["policies"]}
        # cascade cpWER must lie between always-base and always-tiny (separated)
        cascade = pol["cascade_kl@3.30_separated"]["cpwer"]
        tiny = pol["always_tiny_separated"]["cpwer"]
        base = pol["always_base_separated"]["cpwer"]
        self.assertLessEqual(cascade, tiny + 1e-9)
        self.assertGreaterEqual(cascade, base - 1e-9)
        # compute within [1.0, 1.93]
        c_compute = pol["cascade_kl@3.30_separated"]["compute"]
        self.assertGreaterEqual(c_compute, 1.0 - 1e-9)
        self.assertLessEqual(c_compute, 1.93 + 1e-9)

    def test_hypothesis_verdicts_have_all_three(self) -> None:
        summary = json.loads(
            (self.out_dir / "three_tier_cascade_results.json").read_text(encoding="utf-8")
        )
        for h in ("H43a", "H43b", "H43c"):
            self.assertIn(h, summary["hypothesis_verdicts"])
            self.assertIn("supported", summary["hypothesis_verdicts"][h])
            self.assertIn("reason", summary["hypothesis_verdicts"][h])

    def test_pareto_frontier_nonempty(self) -> None:
        summary = json.loads(
            (self.out_dir / "three_tier_cascade_results.json").read_text(encoding="utf-8")
        )
        frontier = summary["pareto_frontier"]
        self.assertGreater(len(frontier), 0)
        # every frontier point must be undominated
        for p in frontier:
            self.assertEqual(p["pareto_status"], "frontier")

    def test_threshold_sweep_monotone_fraction(self) -> None:
        summary = json.loads(
            (self.out_dir / "three_tier_cascade_results.json").read_text(encoding="utf-8")
        )
        sweep = summary["threshold_sweep"]
        # sort by threshold ascending; escalation fraction must be non-increasing
        sweep_sorted = sorted(sweep, key=lambda x: x["threshold"])
        fracs = [s["escalation_fraction"] for s in sweep_sorted]
        for a, b in zip(fracs, fracs[1:]):
            self.assertGreaterEqual(a, b - 1e-9)


if __name__ == "__main__":
    unittest.main()
