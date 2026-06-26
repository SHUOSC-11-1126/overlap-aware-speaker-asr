"""Tests for RQ40: Mode S corpus specificity (experimental/frontier).

Pins the pure helpers: compression ratio (Whisper-faithful), script category,
language-id entropy, script-aware tokeniser, char n-gram counts, token
containment, KL divergence in bits (add-1 smoothing on Q), reference-count
aggregation, KL detector score, specificity calibration, and the empirical
90%-specificity threshold calibration. Also pins the Mode S labeling logic
(full 5-criterion vs 3-criterion candidate vs Other) and the per-corpus
track loaders' structural invariants. The full driver ``main()`` is
exercised via a smoke test on the real AISHELL-4 + gold + silver source
data, verifying the CSV/JSON outputs and hypothesis verdicts.

No Whisper / no audio needed. numpy + stdlib only.
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

# The RQ40 analysis script lives in results/frontier/ as a standalone module
# (no src. package). Import it via sys.path manipulation, mirroring the
# harness entropy_guard / test_metadata_mode_s_detector pattern.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_DIR = _PROJECT_ROOT / "results" / "frontier" / "mode_s_corpus_specificity"
sys.path.insert(0, str(_SCRIPT_DIR))

import mode_s_corpus_specificity_analysis as rq40  # noqa: E402  (path-injected import)


# ----------------------------------------------------------------- CR primitive
class TestCompressionRatio(unittest.TestCase):
    def test_empty_is_zero(self) -> None:
        self.assertEqual(rq40.compression_ratio(""), 0.0)

    def test_whitespace_only_is_zero(self) -> None:
        self.assertEqual(rq40.compression_ratio("   \n\t  "), 0.0)

    def test_repetitive_text_has_high_ratio(self) -> None:
        repetitive = "小小小小小小小小小小小小"
        normal = "今天天气真好我们去公园散步吧"
        self.assertGreater(rq40.compression_ratio(repetitive),
                           rq40.compression_ratio(normal))

    def test_returns_positive_for_normal_text(self) -> None:
        # CR is len(raw bytes) / len(compressed bytes); for short text the zlib
        # overhead can dominate and CR can be < 1.0. We only assert > 0.
        self.assertGreater(rq40.compression_ratio("hello world"), 0.0)


# -------------------------------------------------------------- script detection
class TestScriptCategory(unittest.TestCase):
    def test_space_is_space(self) -> None:
        self.assertEqual(rq40.script_category(" "), "Space")

    def test_han(self) -> None:
        self.assertEqual(rq40.script_category("你"), "Han")

    def test_latin(self) -> None:
        self.assertEqual(rq40.script_category("A"), "Latin")

    def test_digit(self) -> None:
        self.assertEqual(rq40.script_category("3"), "Digit")

    def test_punct(self) -> None:
        self.assertEqual(rq40.script_category(","), "Punct")


class TestLanguageIdEntropy(unittest.TestCase):
    def test_empty_is_zero(self) -> None:
        self.assertEqual(rq40.language_id_entropy(""), 0.0)

    def test_monoscript_chinese_is_zero(self) -> None:
        # Pure Han has zero entropy (one script category dominates)
        self.assertEqual(rq40.language_id_entropy("你好世界"), 0.0)

    def test_mixed_script_has_positive_entropy(self) -> None:
        # Half Han, half Latin => entropy near 1.0 bit
        ent = rq40.language_id_entropy("你好AB")
        self.assertGreater(ent, 0.5)
        self.assertLess(ent, 1.5)

    def test_balanced_three_scripts_higher_entropy(self) -> None:
        # Three equally-weighted categories => entropy = log2(3) ~ 1.585
        ent = rq40.language_id_entropy("你好A")  # Han Han Latin => 2/3 vs 1/3
        expected = -(2 / 3) * np.log2(2 / 3) - (1 / 3) * np.log2(1 / 3)
        self.assertAlmostEqual(ent, expected, places=6)


# ----------------------------------------------------------------- tokeniser
class TestTokenize(unittest.TestCase):
    def test_empty_returns_empty(self) -> None:
        self.assertEqual(rq40.tokenize(""), [])

    def test_cjk_chars_become_individual_tokens(self) -> None:
        # Each CJK char is its own token.
        self.assertEqual(rq40.tokenize("你好"), ["你", "好"])

    def test_latin_runs_split_on_whitespace(self) -> None:
        self.assertEqual(rq40.tokenize("hello world"), ["hello", "world"])

    def test_mixed_cjk_and_latin(self) -> None:
        # 你好hello世界 => 你, 好, hello, 世, 界
        self.assertEqual(rq40.tokenize("你好hello世界"),
                         ["你", "好", "hello", "世", "界"])

    def test_whitespace_only_returns_empty(self) -> None:
        self.assertEqual(rq40.tokenize("   \n\t  "), [])


# ------------------------------------------------------------- n-gram utilities
class TestCharNgrams(unittest.TestCase):
    def test_short_text_returns_single_token(self) -> None:
        # "ab" has fewer than n=3 chars; returns the stripped string as the
        # only "n-gram" so frequency counts are still computable.
        self.assertEqual(rq40.char_ngrams("ab", 3), ["ab"])

    def test_empty_returns_empty(self) -> None:
        self.assertEqual(rq40.char_ngrams("", 3), [])

    def test_whitespace_is_stripped(self) -> None:
        # "a b c" => stripped "abc" => 3-grams ["abc"]
        self.assertEqual(rq40.char_ngrams("a b c", 3), ["abc"])

    def test_standard_3grams(self) -> None:
        # "abcde" => ["abc", "bcd", "cde"]
        self.assertEqual(rq40.char_ngrams("abcde", 3), ["abc", "bcd", "cde"])


class TestNgramCounts(unittest.TestCase):
    def test_counts_are_frequencies(self) -> None:
        # "ababa" stripped => 3-grams: aba, bab, aba => {aba: 2, bab: 1}
        counts = rq40.ngram_counts("ababa", 3)
        self.assertEqual(counts, {"aba": 2, "bab": 1})

    def test_empty_returns_empty_dict(self) -> None:
        self.assertEqual(rq40.ngram_counts("", 3), {})


# ------------------------------------------------------------- content similarity
class TestTokenContainment(unittest.TestCase):
    def test_identical_texts_returns_one(self) -> None:
        self.assertEqual(rq40.token_containment("你好世界", "你好世界"), 1.0)

    def test_disjoint_texts_returns_zero(self) -> None:
        # No shared tokens
        self.assertEqual(rq40.token_containment("你好", "hello world"), 0.0)

    def test_partial_overlap(self) -> None:
        # sep = "你好AB" (tokens: 你, 好, AB — "AB" is one Latin run)
        # mix = "你好C" (tokens: 你, 好, C)
        # containment = |{你,好} ∩ {你,好,C}| / |{你,好,AB}| = 2/3
        self.assertAlmostEqual(
            rq40.token_containment("你好AB", "你好C"), 2 / 3, places=6
        )

    def test_empty_sep_returns_zero(self) -> None:
        self.assertEqual(rq40.token_containment("", "你好"), 0.0)

    def test_empty_mix_returns_zero(self) -> None:
        # sep has tokens but mix has none => intersection empty
        self.assertEqual(rq40.token_containment("你好", ""), 0.0)

    def test_mode_s_near_duplicate_is_high(self) -> None:
        # Mode S = near-duplicate of mixed. sep tokens are a subset of mix
        # tokens => containment = 1.0.
        sep = "今天天气真好"
        mix = "今天天气真好我们去公园散步吧"
        self.assertGreater(rq40.token_containment(sep, mix), 0.8)


# ------------------------------------------------------------- KL divergence (RQ34)
class TestKLDivergenceBits(unittest.TestCase):
    def test_identical_distributions_returns_near_zero(self) -> None:
        # P == Q but with add-1 smoothing on Q, Q is slightly different from P,
        # so KL is small but not exactly 0. (Smoothing shrinks Q toward uniform.)
        counts = {"abc": 2, "bcd": 1}
        kl = rq40.kl_divergence_bits(counts, dict(counts))
        self.assertGreaterEqual(kl, 0.0)
        self.assertLess(kl, 0.1)

    def test_empty_returns_zero(self) -> None:
        self.assertEqual(rq40.kl_divergence_bits({}, {"abc": 1}), 0.0)
        self.assertEqual(rq40.kl_divergence_bits({"abc": 1}, {}), 0.0)

    def test_disjoint_support_is_finite_with_smoothing(self) -> None:
        # P has "aaa", Q has "bbb" — without smoothing KL would be infinite.
        # With add-1 smoothing on Q, Q(aaa) > 0 so KL is finite.
        kl = rq40.kl_divergence_bits({"aaa": 1}, {"bbb": 1}, smoothing=1.0)
        self.assertTrue(np.isfinite(kl))
        self.assertGreater(kl, 0.0)

    def test_value_is_in_bits(self) -> None:
        # For a known small case: P = {a:1}, Q = {a:1, b:1}, smoothing=1.
        # P(a) = 1.0. Q(a) = (1 + 1) / (2 + 1*2) = 2/4 = 0.5.
        # KL = 1.0 * log2(1.0 / 0.5) = 1.0 bit.
        kl = rq40.kl_divergence_bits({"a": 1}, {"a": 1, "b": 1}, smoothing=1.0)
        self.assertAlmostEqual(kl, 1.0, places=6)

    def test_smoothing_makes_q_positive_for_unseen_grams(self) -> None:
        # Q has no "zzz" but with smoothing Q(zzz) = 1 / (ref_total + |V_ref|)
        # > 0, so KL contribution from "zzz" is finite.
        ref = {"abc": 5, "bcd": 3}
        track = {"zzz": 2}
        kl = rq40.kl_divergence_bits(track, ref, smoothing=1.0)
        self.assertTrue(np.isfinite(kl))
        self.assertGreater(kl, 0.0)


class TestBuildReferenceCounts(unittest.TestCase):
    def test_aggregates_across_texts(self) -> None:
        # "abc" => {abc:1}; "bcd" => {bcd:1}; aggregated => {abc:1, bcd:1}
        ref = rq40.build_reference_counts(["abc", "bcd"], n=3)
        self.assertEqual(ref, {"abc": 1, "bcd": 1})

    def test_sums_repeated_grams(self) -> None:
        # "ababa" => {aba:2, bab:1}; "abaaba" => {aba:2, baa:1, aab:1}
        # aggregated: {aba:4, bab:1, baa:1, aab:1}
        ref = rq40.build_reference_counts(["ababa", "abaaba"], n=3)
        self.assertEqual(ref.get("aba"), 4)
        self.assertEqual(ref.get("bab"), 1)

    def test_empty_list_returns_empty(self) -> None:
        self.assertEqual(rq40.build_reference_counts([], n=3), {})


class TestKLDetectorScore(unittest.TestCase):
    def test_returns_kl_of_track_against_reference(self) -> None:
        ref = rq40.build_reference_counts(["你好世界今天"], n=3)
        # Same text => KL ~ 0 (track == reference distribution)
        score = rq40.kl_detector_score("你好世界今天", ref, n=3)
        self.assertAlmostEqual(score, 0.0, places=4)

    def test_different_text_has_positive_score(self) -> None:
        ref = rq40.build_reference_counts(["你好世界今天"], n=3)
        # Completely different characters => positive KL
        score = rq40.kl_detector_score("xyzuvw", ref, n=3)
        self.assertGreater(score, 0.0)


# ------------------------------------------------------- threshold calibration
class TestCalibrateKLSpecificity(unittest.TestCase):
    def test_empty_returns_one(self) -> None:
        self.assertEqual(rq40.calibrate_kl_specificity([], 3.30), 1.0)

    def test_all_below_threshold_is_one(self) -> None:
        # All neg scores < threshold => no FPs => specificity = 1.0
        self.assertEqual(
            rq40.calibrate_kl_specificity([0.0, 1.0, 2.0], 3.30), 1.0
        )

    def test_all_above_threshold_is_zero(self) -> None:
        # All neg scores >= threshold => all FPs => specificity = 0.0
        self.assertEqual(
            rq40.calibrate_kl_specificity([4.0, 5.0, 6.0], 3.30), 0.0
        )

    def test_partial_above_threshold(self) -> None:
        # 2 of 4 scores >= 3.30 => 2 FPs => specificity = 1 - 2/4 = 0.5
        self.assertAlmostEqual(
            rq40.calibrate_kl_specificity([1.0, 2.0, 4.0, 5.0], 3.30), 0.5,
            places=6
        )


class TestCalibrateThresholdForTargetSpecificity(unittest.TestCase):
    def test_separable_case_finds_threshold(self) -> None:
        # Negs in [0..9], positives in [10, 11]. Threshold 10 gives spec=1.0,
        # sens=1.0. With target 0.90, the calibrated threshold should be ~10.
        neg = [float(i) for i in range(10)]
        pos = [10.0, 11.0]
        out = rq40.calibrate_threshold_for_target_specificity(
            neg, pos, target_spec=0.90
        )
        self.assertGreaterEqual(out["specificity"], 0.90)
        self.assertEqual(out["tp"], 2)
        self.assertEqual(out["sensitivity"], 1.0)

    def test_no_threshold_meets_target_returns_high_threshold(self) -> None:
        # Negs and positives fully interleaved; no threshold gives 0.90 spec
        # with any sensitivity. The fallback returns the highest threshold
        # (flag nothing) with spec=1.0, sens=0.0.
        neg = [0.0, 1.0, 2.0, 3.0]
        pos = [1.5, 2.5]
        out = rq40.calibrate_threshold_for_target_specificity(
            neg, pos, target_spec=0.99
        )
        self.assertEqual(out["sensitivity"], 0.0)
        self.assertEqual(out["tp"], 0)
        self.assertEqual(out["fn"], 2)

    def test_empty_negs_returns_inf_threshold(self) -> None:
        out = rq40.calibrate_threshold_for_target_specificity(
            [], [1.0, 2.0], target_spec=0.90
        )
        self.assertEqual(out["sensitivity"], 0.0)
        self.assertEqual(out["fn"], 2)

    def test_empty_pos_is_safe(self) -> None:
        # No positives; calibration still returns a finite threshold with
        # sens=0 (no positives to catch).
        out = rq40.calibrate_threshold_for_target_specificity(
            [1.0, 2.0, 3.0], [], target_spec=0.90
        )
        self.assertEqual(out["sensitivity"], 0.0)
        self.assertGreaterEqual(out["specificity"], 0.90)


# ------------------------------------------------------------- Mode S labeling
class TestIsModeSFull(unittest.TestCase):
    def _track(
        self,
        halluc: bool = True,
        ent: float = 0.1,
        lr: float = 1.0,
        cr: float = 1.5,
        cs: float = 0.9,
        has_mix: bool = True,
    ) -> dict:
        return {
            "hallucinated": halluc,
            "lang_id_entropy": ent,
            "length_ratio": lr,
            "cr": cr,
            "content_similarity": cs,
            "has_mixed_text": has_mix,
        }

    def test_non_hallucinated_returns_false(self) -> None:
        self.assertFalse(rq40.is_mode_s_full(self._track(halluc=False)))

    def test_no_mixed_text_returns_false(self) -> None:
        self.assertFalse(rq40.is_mode_s_full(self._track(has_mix=False)))

    def test_nan_length_ratio_returns_false(self) -> None:
        t = self._track()
        t["length_ratio"] = float("nan")
        self.assertFalse(rq40.is_mode_s_full(t))

    def test_nan_content_similarity_returns_false(self) -> None:
        t = self._track()
        t["content_similarity"] = float("nan")
        self.assertFalse(rq40.is_mode_s_full(t))

    def test_full_criteria_met_returns_true(self) -> None:
        # ent < 0.409, lr < 2.0, cr < 2.4, cs > 0.8
        self.assertTrue(rq40.is_mode_s_full(self._track()))

    def test_high_lang_id_returns_false(self) -> None:
        self.assertFalse(rq40.is_mode_s_full(self._track(ent=0.5)))

    def test_high_cr_returns_false(self) -> None:
        self.assertFalse(rq40.is_mode_s_full(self._track(cr=3.0)))

    def test_low_content_similarity_returns_false(self) -> None:
        self.assertFalse(rq40.is_mode_s_full(self._track(cs=0.5)))


class TestIsModeSCandidate3Criterion(unittest.TestCase):
    def test_non_hallucinated_returns_false(self) -> None:
        t = {"hallucinated": False, "lang_id_entropy": 0.1, "cr": 1.5}
        self.assertFalse(rq40.is_mode_s_candidate_3criterion(t))

    def test_low_ent_low_cr_returns_true(self) -> None:
        t = {"hallucinated": True, "lang_id_entropy": 0.1, "cr": 1.5}
        self.assertTrue(rq40.is_mode_s_candidate_3criterion(t))

    def test_high_ent_returns_false(self) -> None:
        t = {"hallucinated": True, "lang_id_entropy": 0.5, "cr": 1.5}
        self.assertFalse(rq40.is_mode_s_candidate_3criterion(t))

    def test_high_cr_returns_false(self) -> None:
        t = {"hallucinated": True, "lang_id_entropy": 0.1, "cr": 3.0}
        self.assertFalse(rq40.is_mode_s_candidate_3criterion(t))


class TestAssignModeSLabel(unittest.TestCase):
    def test_full_mode_s_returns_mode_s(self) -> None:
        t = {
            "hallucinated": True,
            "lang_id_entropy": 0.1,
            "length_ratio": 1.0,
            "cr": 1.5,
            "content_similarity": 0.9,
            "has_mixed_text": True,
        }
        self.assertEqual(rq40.assign_mode_s_label(t), "Mode_S")

    def test_candidate_without_mixed_text_returns_candidate(self) -> None:
        t = {
            "hallucinated": True,
            "lang_id_entropy": 0.1,
            "length_ratio": float("nan"),
            "cr": 1.5,
            "content_similarity": float("nan"),
            "has_mixed_text": False,
        }
        self.assertEqual(rq40.assign_mode_s_label(t), "Mode_S_candidate")

    def test_non_hallucinated_returns_other(self) -> None:
        t = {
            "hallucinated": False,
            "lang_id_entropy": 0.1,
            "length_ratio": 1.0,
            "cr": 1.5,
            "content_similarity": 0.9,
            "has_mixed_text": True,
        }
        self.assertEqual(rq40.assign_mode_s_label(t), "Other")

    def test_high_lang_id_returns_other(self) -> None:
        t = {
            "hallucinated": True,
            "lang_id_entropy": 0.5,
            "length_ratio": 1.0,
            "cr": 1.5,
            "content_similarity": 0.9,
            "has_mixed_text": True,
        }
        self.assertEqual(rq40.assign_mode_s_label(t), "Other")


# ------------------------------------------------------------- data loaders
class TestLoadAishell4Tracks(unittest.TestCase):
    def setUp(self) -> None:
        self.tracks = rq40.load_aishell4_tracks()

    def test_returns_77_tracks(self) -> None:
        self.assertEqual(len(self.tracks), 77)

    def test_all_tracks_have_required_fields(self) -> None:
        required = {
            "corpus", "track_id", "sep_text", "mix_text", "hallucinated",
            "cer", "lang_id_entropy", "cr", "length_ratio", "content_similarity",
            "has_mixed_text", "num_speakers",
        }
        for t in self.tracks:
            self.assertTrue(required.issubset(t.keys()), f"missing keys in {t['track_id']}")

    def test_corpus_is_aishell4(self) -> None:
        for t in self.tracks:
            self.assertEqual(t["corpus"], "aishell4")

    def test_known_mode_s_windows_have_mixed_text(self) -> None:
        # Windows 22 and 30 are the known Mode S cases; both must have
        # mixed_text cached (the full 5-criterion definition requires it).
        # Note: 35 of 77 AISHELL-4 windows have empty mixed_text, so we only
        # assert on the Mode S windows here.
        ids = {t["track_id"]: t for t in self.tracks}
        for wid in ("22", "30"):
            self.assertIn(wid, ids)
            self.assertTrue(ids[wid]["has_mixed_text"],
                            f"window {wid} should have mixed_text")

    def test_known_mode_s_windows_are_hallucinated(self) -> None:
        # Windows 22 and 30 are the known Mode S cases; both must be hallucinated.
        ids = {t["track_id"]: t for t in self.tracks}
        for wid in ("22", "30"):
            self.assertIn(wid, ids, f"window {wid} missing")
            self.assertTrue(ids[wid]["hallucinated"],
                            f"window {wid} should be hallucinated")


class TestLoadGoldTracks(unittest.TestCase):
    def setUp(self) -> None:
        self.tracks = rq40.load_gold_tracks()

    def test_returns_600_tracks(self) -> None:
        # 300 conditions x sep1/sep2 = 600 tracks
        self.assertEqual(len(self.tracks), 600)

    def test_corpus_is_gold(self) -> None:
        for t in self.tracks:
            self.assertEqual(t["corpus"], "gold")

    def test_has_mixed_text_is_false(self) -> None:
        # Gold tracks have no cached mixed_text.
        for t in self.tracks:
            self.assertFalse(t["has_mixed_text"])

    def test_length_ratio_and_content_similarity_are_nan(self) -> None:
        # Without mixed_text, length_ratio and content_similarity are NaN.
        for t in self.tracks:
            self.assertTrue(math.isnan(t["length_ratio"]))
            self.assertTrue(math.isnan(t["content_similarity"]))

    def test_num_speakers_is_two(self) -> None:
        for t in self.tracks:
            self.assertEqual(t["num_speakers"], 2)


class TestLoadSilverTracks(unittest.TestCase):
    def setUp(self) -> None:
        self.tracks = rq40.load_silver_tracks()

    def test_returns_25_tracks(self) -> None:
        # 25 synthetic silver samples
        self.assertEqual(len(self.tracks), 25)

    def test_corpus_is_silver(self) -> None:
        for t in self.tracks:
            self.assertEqual(t["corpus"], "silver")

    def test_has_mixed_text_is_true(self) -> None:
        # Silver samples have mixed_text cached.
        for t in self.tracks:
            self.assertTrue(t["has_mixed_text"])

    def test_length_ratio_and_content_similarity_are_finite(self) -> None:
        for t in self.tracks:
            self.assertFalse(math.isnan(t["length_ratio"]))
            self.assertFalse(math.isnan(t["content_similarity"]))


# ------------------------------------------------------------- module constants
class TestModuleConstants(unittest.TestCase):
    def test_mode_s_thresholds_match_rq19(self) -> None:
        self.assertEqual(rq40.LANG_ID_ENTROPY_THRESHOLD, 0.409)
        self.assertEqual(rq40.LENGTH_RATIO_THRESHOLD, 2.0)
        self.assertEqual(rq40.CR_THRESHOLD, 2.4)

    def test_rq40_content_similarity_threshold(self) -> None:
        self.assertEqual(rq40.CONTENT_SIMILARITY_THRESHOLD, 0.8)

    def test_kl_threshold_is_3_30_bits(self) -> None:
        self.assertEqual(rq40.KL_THRESHOLD, 3.30)

    def test_aishell4_reference_counts(self) -> None:
        self.assertEqual(rq40.AISHELL4_MODE_S_COUNT, 2)
        self.assertEqual(rq40.AISHELL4_HALLUC_COUNT, 37)
        self.assertAlmostEqual(
            rq40.AISHELL4_MODE_S_PREVALENCE, 2 / 37, places=6
        )

    def test_hallucination_thresholds(self) -> None:
        self.assertEqual(rq40.AISHELL4_CPWER_HALLUC, 1.0)
        self.assertEqual(rq40.GOLD_CER_HALLUC, 0.5)
        self.assertEqual(rq40.SILVER_CER_HALLUC, 0.5)


# ------------------------------------------------------------- smoke test (driver)
class TestMainSmoke(unittest.TestCase):
    """Smoke test: run the full driver on the real source data and verify
    the CSV/JSON outputs and hypothesis verdicts are well-formed."""

    @classmethod
    def setUpClass(cls) -> None:
        # Run main() once; redirect OUT_CSV / OUT_JSON to a temp dir so we
        # don't clobber the committed outputs (and so the test is hermetic).
        cls._tmpdir = tempfile.mkdtemp(prefix="rq40_smoke_")
        cls._orig_out_csv = rq40.OUT_CSV
        cls._orig_out_json = rq40.OUT_JSON
        cls._orig_out_dir = rq40.OUT_DIR
        out_dir = Path(cls._tmpdir) / "out"
        out_dir.mkdir(parents=True, exist_ok=True)
        rq40.OUT_DIR = out_dir
        rq40.OUT_CSV = out_dir / "mode_s_corpus_specificity_results.csv"
        rq40.OUT_JSON = out_dir / "mode_s_corpus_specificity_results.json"
        # Capture stdout (the script prints a summary)
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            rq40.main()
        cls.stdout = buf.getvalue()
        cls.json_path = rq40.OUT_JSON
        cls.csv_path = rq40.OUT_CSV

    @classmethod
    def tearDownClass(cls) -> None:
        # Restore original paths
        rq40.OUT_CSV = cls._orig_out_csv
        rq40.OUT_JSON = cls._orig_out_json
        rq40.OUT_DIR = cls._orig_out_dir

    def test_csv_exists_and_has_rows(self) -> None:
        self.assertTrue(self.csv_path.exists())
        with self.csv_path.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        # 77 AISHELL-4 + 600 gold + 25 silver = 702
        self.assertEqual(len(rows), 702)

    def test_csv_has_expected_columns(self) -> None:
        with self.csv_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            cols = reader.fieldnames
        expected = {
            "corpus", "track_id", "hallucinated", "mode_s_label",
            "lang_id_entropy", "length_ratio", "cr", "content_similarity",
            "kl_score", "kl_flag_fixed", "kl_flag_calibrated",
            "cer", "has_mixed_text", "num_speakers",
        }
        self.assertTrue(expected.issubset(set(cols)))

    def test_json_exists_and_is_valid(self) -> None:
        self.assertTrue(self.json_path.exists())
        data = json.loads(self.json_path.read_text(encoding="utf-8"))
        self.assertIn("hypothesis_verdicts", data)
        self.assertIn("per_track", data)
        self.assertEqual(len(data["per_track"]), 702)

    def test_hypothesis_verdicts_present(self) -> None:
        data = json.loads(self.json_path.read_text(encoding="utf-8"))
        hv = data["hypothesis_verdicts"]
        for key in ("H40a", "H40b", "H40c"):
            self.assertIn(key, hv)
            self.assertIn("supported", hv[key])
            self.assertIn("reason", hv[key])
            self.assertIsInstance(hv[key]["supported"], bool)

    def test_aishell4_has_two_mode_s(self) -> None:
        # The known AISHELL-4 Mode S cases (windows 22, 30) must be detected.
        data = json.loads(self.json_path.read_text(encoding="utf-8"))
        a4 = data["mode_s_counts_per_corpus"]["aishell4"]
        self.assertEqual(a4["n_mode_s_full"], 2)
        self.assertIn("22", a4["mode_s_track_ids"])
        self.assertIn("30", a4["mode_s_track_ids"])

    def test_gold_has_zero_full_mode_s(self) -> None:
        # Gold has no cached mixed_text, so the full 5-criterion definition
        # cannot apply; n_mode_s_full must be 0.
        data = json.loads(self.json_path.read_text(encoding="utf-8"))
        gold = data["mode_s_counts_per_corpus"]["gold"]
        self.assertEqual(gold["n_mode_s_full"], 0)

    def test_kl_results_have_dual_thresholds(self) -> None:
        # Both fixed and calibrated thresholds are reported per corpus.
        data = json.loads(self.json_path.read_text(encoding="utf-8"))
        for corpus in ("aishell4", "gold", "silver"):
            kl = data["kl_detector_results_per_corpus"][corpus]
            self.assertIn("fixed_threshold", kl)
            self.assertIn("calibrated_threshold", kl)
            self.assertIn("fixed_specificity_on_non_hallucinated", kl)
            self.assertIn("calibrated_specificity_on_non_hallucinated", kl)

    def test_calibrated_threshold_meets_90pct_specificity_on_aishell4(self) -> None:
        # The empirically-calibrated threshold must achieve >= 90% specificity
        # on AISHELL-4 non-hallucinated (by construction).
        data = json.loads(self.json_path.read_text(encoding="utf-8"))
        a4 = data["kl_detector_results_per_corpus"]["aishell4"]
        self.assertGreaterEqual(
            a4["calibrated_specificity_on_non_hallucinated"], 0.90 - 1e-6
        )

    def test_per_track_has_dual_kl_flags(self) -> None:
        data = json.loads(self.json_path.read_text(encoding="utf-8"))
        for t in data["per_track"]:
            self.assertIn("kl_flag_fixed", t)
            self.assertIn("kl_flag_calibrated", t)
            self.assertIsInstance(t["kl_flag_fixed"], bool)
            self.assertIsInstance(t["kl_flag_calibrated"], bool)


if __name__ == "__main__":
    unittest.main()
