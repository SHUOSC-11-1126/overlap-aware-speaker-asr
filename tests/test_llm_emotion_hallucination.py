"""Tests for RQ36: LLM emotion reading from hallucinated transcripts.

Label: experimental/frontier (statistical layer) / qualitative/demo (LLM emotion readings).

Pin the PURE helpers in ``src/llm_emotion_hallucination.py``: prompt construction,
deepseek-r1 response parsing (JSON-after-think, code-fenced JSON, malformed-JSON regex
fallback, garbage -> graceful default), transcript hashing, the F-test of confidence
variance, the Mann-Whitney AUC, the Mode-S-within-1-SD check, AISHELL-4 / gold-track
data loading, the cache-and-call mechanism (cache hit, cache miss with mock, call
failure), and the end-to-end hypothesis verdicts.

No ollama / no network is required: ``call_ollama`` is never invoked by the tests
(the cache-miss path injects a fake ``call_fn``).
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

import numpy as np

from src.llm_emotion_hallucination import (
    CATASTROPHIC_CPWER,
    MODE_S_WINDOW_IDS,
    build_prompt,
    compute_auc,
    compute_f_test,
    evaluate_hypotheses,
    get_llm_emotion,
    lexicon_emotion_metrics,
    load_aishell4_windows,
    load_gold_tracks,
    load_cache,
    mode_s_comparison,
    parse_llm_response,
    save_cache,
    transcript_hash,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AISHELL4_JSON = (
    PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
GOLD_TEXT_JSON = (
    PROJECT_ROOT
    / "results"
    / "frontier"
    / "gold_detector_comparison"
    / "gold_track_texts.json"
)
GOLD_CURVE_CSV = (
    PROJECT_ROOT / "results" / "frontier" / "separation_tax" / "phase_curve.csv"
)


# --------------------------------------------------------------------------- prompt
class TestBuildPrompt(unittest.TestCase):
    def test_prompt_contains_transcript(self) -> None:
        p = build_prompt("你好世界")
        self.assertIn("你好世界", p)
        self.assertIn("emotion", p)
        self.assertIn("reliable", p)
        self.assertIn("confidence", p)

    def test_prompt_contains_json_schema(self) -> None:
        p = build_prompt("test")
        self.assertIn('"emotion"', p)
        self.assertIn('"arousal"', p)
        self.assertIn('"valence"', p)
        self.assertIn('"confidence"', p)
        self.assertIn('"reliable"', p)


# -------------------------------------------------------------------- response parsing
class TestParseLLMResponse(unittest.TestCase):
    def test_clean_json_after_think(self) -> None:
        raw = (
            "<think>\nLet me reason about this.\n</think>\n\n"
            "```json\n"
            '{"emotion": "neutral", "arousal": 2, "valence": 4, '
            '"confidence": 0.6, "reliable": true}\n'
            "```\n"
        )
        r = parse_llm_response(raw)
        self.assertTrue(r["parsed_ok"])
        self.assertEqual(r["emotion"], "neutral")
        self.assertEqual(r["arousal"], 2)
        self.assertEqual(r["valence"], 4)
        self.assertAlmostEqual(r["confidence"], 0.6)
        self.assertTrue(r["reliable"])

    def test_bare_json_no_think_no_fence(self) -> None:
        raw = '{"emotion": "happy", "arousal": 4, "valence": 5, "confidence": 0.8, "reliable": true}'
        r = parse_llm_response(raw)
        self.assertTrue(r["parsed_ok"])
        self.assertEqual(r["emotion"], "happy")
        self.assertAlmostEqual(r["confidence"], 0.8)

    def test_malformed_json_regex_fallback(self) -> None:
        # No valid JSON object, but fields present as key: value text.
        raw = (
            "<think>reasoning</think>\n"
            "emotion: sad\narousal: 3\nvalence: 2\nconfidence: 0.45\nreliable: false\n"
        )
        r = parse_llm_response(raw)
        # Regex fallback should recover the scalar fields.
        self.assertEqual(r["emotion"], "sad")
        self.assertEqual(r["arousal"], 3)
        self.assertEqual(r["valence"], 2)
        self.assertAlmostEqual(r["confidence"], 0.45)
        self.assertFalse(r["reliable"])
        # parsed_ok is False because strict JSON failed, but fields were recovered.
        self.assertFalse(r["parsed_ok"])

    def test_garbage_returns_safe_defaults(self) -> None:
        r = parse_llm_response("totally unrelated text with no fields")
        self.assertFalse(r["parsed_ok"])
        self.assertEqual(r["emotion"], "neutral")
        self.assertEqual(r["arousal"], 3)
        self.assertEqual(r["valence"], 3)
        self.assertAlmostEqual(r["confidence"], 0.5)
        self.assertTrue(r["reliable"])  # default: assume reliable (fail-open)

    def test_confidence_clamped_to_unit(self) -> None:
        raw = '{"emotion": "angry", "arousal": 5, "valence": 1, "confidence": 1.4, "reliable": false}'
        r = parse_llm_response(raw)
        self.assertAlmostEqual(r["confidence"], 1.0)
        raw2 = '{"emotion": "angry", "arousal": 5, "valence": 1, "confidence": -0.2, "reliable": false}'
        r2 = parse_llm_response(raw2)
        self.assertAlmostEqual(r2["confidence"], 0.0)

    def test_arousal_valence_bounded(self) -> None:
        raw = '{"emotion":"x","arousal":9,"valence":0,"confidence":0.5,"reliable":true}'
        r = parse_llm_response(raw)
        self.assertEqual(r["arousal"], 5)
        self.assertEqual(r["valence"], 1)


# ----------------------------------------------------------------------- hashing / cache
class TestHashAndCache(unittest.TestCase):
    def test_hash_deterministic(self) -> None:
        self.assertEqual(transcript_hash("abc"), transcript_hash("abc"))

    def test_hash_differs(self) -> None:
        self.assertNotEqual(transcript_hash("abc"), transcript_hash("abd"))

    def test_save_load_cache_roundtrip(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "cache.json"
            cache = {"abc": {"emotion": "neutral", "confidence": 0.5}}
            save_cache(p, cache)
            loaded = load_cache(p)
            self.assertEqual(loaded["abc"]["emotion"], "neutral")

    def test_load_cache_missing_returns_empty(self) -> None:
        self.assertEqual(load_cache(Path("/nonexistent/path/cache.json")), {})


# --------------------------------------------------------------------------- cache+call
class TestGetLLMEmotion(unittest.TestCase):
    def test_cache_hit_does_not_call(self) -> None:
        calls = []

        def fake_call(prompt: str) -> str:
            calls.append(prompt)
            return "should not be called"

        cache = {transcript_hash("hello"): {"emotion": "happy", "confidence": 0.9}}
        r = get_llm_emotion("hello", cache, call_fn=fake_call)
        self.assertEqual(r["emotion"], "happy")
        self.assertEqual(len(calls), 0)

    def test_cache_miss_calls_and_stores(self) -> None:
        raw = '{"emotion": "sad", "arousal": 3, "valence": 2, "confidence": 0.4, "reliable": false}'

        def fake_call(prompt: str) -> str:
            return raw

        cache: dict = {}
        r = get_llm_emotion("a fresh transcript", cache, call_fn=fake_call)
        self.assertEqual(r["emotion"], "sad")
        self.assertAlmostEqual(r["confidence"], 0.4)
        # Stored in cache under the hash.
        self.assertIn(transcript_hash("a fresh transcript"), cache)

    def test_call_failure_returns_unparsed(self) -> None:
        def fake_call(prompt: str) -> str:
            raise RuntimeError("ollama down")

        cache: dict = {}
        r = get_llm_emotion("broken", cache, call_fn=fake_call)
        self.assertFalse(r["parsed_ok"])
        self.assertEqual(r["emotion"], "neutral")
        # Failed call is still cached (negative cache) so we don't retry forever.
        self.assertIn(transcript_hash("broken"), cache)


# ------------------------------------------------------------------------------ F-test
class TestFTest(unittest.TestCase):
    def test_equal_variances_gives_f_near_one(self) -> None:
        rng = np.random.default_rng(0)
        a = rng.normal(0, 1, 200).tolist()
        b = rng.normal(0, 1, 200).tolist()
        r = compute_f_test(a, b)
        self.assertAlmostEqual(r["f_stat"], 1.0, delta=0.3)
        self.assertGreater(r["p_value"], 0.05)

    def test_unequal_variances_gives_large_f(self) -> None:
        rng = np.random.default_rng(1)
        wide = rng.normal(0, 3, 200).tolist()  # larger variance
        tight = rng.normal(0, 1, 200).tolist()
        r = compute_f_test(wide, tight)
        self.assertGreater(r["f_stat"], 4.0)
        self.assertLess(r["p_value"], 0.001)
        # var_halluc is the first arg, var_clean the second.
        self.assertGreater(r["var_halluc"], r["var_clean"])

    def test_empty_safe(self) -> None:
        r = compute_f_test([], [1.0, 2.0])
        self.assertIn("f_stat", r)
        self.assertTrue(np.isnan(r["f_stat"]) or r["f_stat"] == 0.0)


# -------------------------------------------------------------------------------- AUC
class TestAUC(unittest.TestCase):
    def test_perfect_classifier(self) -> None:
        # positives all score higher than negatives
        scores = [0.9, 0.8, 0.3, 0.2]
        labels = [1, 1, 0, 0]
        self.assertAlmostEqual(compute_auc(scores, labels), 1.0)

    def test_inverted_classifier(self) -> None:
        scores = [0.1, 0.2, 0.8, 0.9]
        labels = [1, 1, 0, 0]
        self.assertAlmostEqual(compute_auc(scores, labels), 0.0)

    def test_random_ties(self) -> None:
        scores = [0.5, 0.5, 0.5, 0.5]
        labels = [1, 1, 0, 0]
        self.assertAlmostEqual(compute_auc(scores, labels), 0.5)

    def test_partial(self) -> None:
        scores = [0.9, 0.4, 0.6, 0.2]
        labels = [1, 1, 0, 0]
        # pairs: (0.9>0.6)=1, (0.9>0.2)=1, (0.4<0.6)=0, (0.4>0.2)=1 -> 3/4
        self.assertAlmostEqual(compute_auc(scores, labels), 0.75)


# --------------------------------------------------------------------- Mode S comparison
class TestModeSComparison(unittest.TestCase):
    def test_within_one_sd(self) -> None:
        clean = [0.5, 0.6, 0.55, 0.45, 0.5, 0.6, 0.55, 0.45, 0.5, 0.6]
        mode_s = [0.5, 0.52]  # right at the mean -> within 1 SD
        r = mode_s_comparison(mode_s, clean)
        self.assertTrue(r["within_1sd"])

    def test_outside_one_sd(self) -> None:
        clean = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        # SD = 0 here; any deviation is "outside". Use a non-zero SD case:
        clean = [0.4, 0.6, 0.4, 0.6, 0.4, 0.6, 0.4, 0.6, 0.4, 0.6]
        mode_s = [0.05, 0.05]  # far below mean ~0.5, SD ~0.1 -> >1 SD away
        r = mode_s_comparison(mode_s, clean)
        self.assertFalse(r["within_1sd"])

    def test_empty_clean_safe(self) -> None:
        r = mode_s_comparison([0.5], [])
        self.assertIn("within_1sd", r)


# ---------------------------------------------------------------------- data loading
class TestLoadAishell4(unittest.TestCase):
    def test_loads_77_windows_with_labels(self) -> None:
        rows = load_aishell4_windows(AISHELL4_JSON)
        self.assertEqual(len(rows), 77)
        n_halluc = sum(1 for r in rows if r["hallucinated"])
        n_clean = sum(1 for r in rows if not r["hallucinated"])
        self.assertEqual(n_halluc, 37)
        self.assertEqual(n_clean, 40)
        # Mode S
        mode_s = [r for r in rows if r["mode_s"]]
        self.assertEqual(len(mode_s), len(MODE_S_WINDOW_IDS))
        self.assertEqual(sorted(r["window_id"] for r in mode_s), sorted(MODE_S_WINDOW_IDS))
        # diverse = hallucinated and not mode_s
        diverse = [r for r in rows if r["hallucinated"] and not r["mode_s"]]
        self.assertEqual(len(diverse), 37 - len(MODE_S_WINDOW_IDS))

    def test_transcripts_non_empty(self) -> None:
        rows = load_aishell4_windows(AISHELL4_JSON)
        # All HALLUCINATED windows must have non-empty transcripts (hallucination requires
        # decoded text; cpWER > 1.0 means insertions dominated, so text exists).
        for r in rows:
            if r["hallucinated"]:
                self.assertGreater(
                    len(r["transcript"]), 0, msg=f"empty hallucinated transcript {r['track_id']}"
                )
        # Empty transcripts (silent windows) are allowed only on the clean side.
        empty = [r for r in rows if len(r["transcript"]) == 0]
        for r in empty:
            self.assertFalse(r["hallucinated"], msg=f"empty but hallucinated {r['track_id']}")
        # Most windows have speech; silent windows are a small minority.
        self.assertLess(len(empty), 20)

    def test_hallucination_label_matches_cpwer(self) -> None:
        rows = load_aishell4_windows(AISHELL4_JSON)
        for r in rows:
            self.assertEqual(r["hallucinated"], r["always_separated_cpwer"] > CATASTROPHIC_CPWER)


class TestLoadGoldTracks(unittest.TestCase):
    def test_loads_catastrophic_and_clean(self) -> None:
        rows = load_gold_tracks(GOLD_TEXT_JSON, GOLD_CURVE_CSV, n_clean_control=40)
        n_cat = sum(1 for r in rows if r["hallucinated"])
        n_clean = sum(1 for r in rows if not r["hallucinated"])
        # ~13 catastrophic (cer_sep2 > 1.0) joinable with non-empty sep2_text.
        self.assertGreaterEqual(n_cat, 10)
        self.assertEqual(n_clean, 40)
        for r in rows:
            self.assertGreater(len(r["transcript"]), 0)

    def test_deterministic_clean_sample(self) -> None:
        r1 = load_gold_tracks(GOLD_TEXT_JSON, GOLD_CURVE_CSV, n_clean_control=10, seed=42)
        r2 = load_gold_tracks(GOLD_TEXT_JSON, GOLD_CURVE_CSV, n_clean_control=10, seed=42)
        clean1 = sorted(r["track_id"] for r in r1 if not r["hallucinated"])
        clean2 = sorted(r["track_id"] for r in r2 if not r["hallucinated"])
        self.assertEqual(clean1, clean2)


# ------------------------------------------------------------------------- lexicon fallback
class TestLexiconFallback(unittest.TestCase):
    def test_returns_density_and_diversity(self) -> None:
        m = lexicon_emotion_metrics("我非常支持这个观点，很好")
        self.assertIn("emotion_word_density", m)
        self.assertIn("emotion_diversity", m)
        self.assertGreaterEqual(m["emotion_word_density"], 0.0)
        self.assertGreaterEqual(m["emotion_diversity"], 0.0)
        self.assertLessEqual(m["emotion_diversity"], 1.0)

    def test_empty_text_safe(self) -> None:
        m = lexicon_emotion_metrics("")
        self.assertEqual(m["emotion_word_density"], 0.0)


# -------------------------------------------------------------------- hypothesis verdicts
class TestEvaluateHypotheses(unittest.TestCase):
    def _row(self, dataset, halluc, conf, reliable, mode_s=False):
        return {
            "dataset": dataset,
            "hallucinated": halluc,
            "mode_s": mode_s,
            "confidence": conf,
            "reliable": reliable,
            "parsed_ok": True,
        }

    def test_h36a_supported_when_halluc_variance_high(self) -> None:
        rows = []
        # hallucinated: wide confidence spread
        for c in [0.1, 0.2, 0.3, 0.9, 0.95, 0.05, 0.85, 0.15, 0.8, 0.1]:
            rows.append(self._row("aishell4", True, c, False))
        # clean: tight confidence
        for c in [0.7, 0.72, 0.71, 0.69, 0.7, 0.71, 0.7, 0.72, 0.69, 0.7]:
            rows.append(self._row("aishell4", False, c, True))
        v = evaluate_hypotheses(rows)
        self.assertGreater(v["h36a"]["f_stat"], 2.0)
        self.assertTrue(v["h36a"]["supported"])

    def test_h36b_supported_when_reliable_tracks_clean(self) -> None:
        rows = []
        # hallucinated -> reliable=False (LLM flags unreliable)
        for _ in range(20):
            rows.append(self._row("aishell4", True, 0.3, False))
        # clean -> reliable=True
        for _ in range(20):
            rows.append(self._row("aishell4", False, 0.8, True))
        v = evaluate_hypotheses(rows)
        self.assertGreater(v["h36b"]["auc_reliable"], 0.9)
        self.assertTrue(v["h36b"]["supported"])

    def test_h36c_within_1sd(self) -> None:
        rows = []
        # Mode S confidence near clean mean
        for c in [0.5, 0.52]:
            rows.append(self._row("aishell4", True, c, True, mode_s=True))
        # diverse hallucinated (won't affect H36c)
        for c in [0.2, 0.3, 0.1, 0.15]:
            rows.append(self._row("aishell4", True, c, False, mode_s=False))
        # clean
        for c in [0.5, 0.55, 0.48, 0.52, 0.5, 0.53, 0.49, 0.51, 0.5, 0.5]:
            rows.append(self._row("aishell4", False, c, True))
        v = evaluate_hypotheses(rows)
        self.assertTrue(v["h36c"]["within_1sd"])

    def test_verdicts_have_all_fields(self) -> None:
        rows = [self._row("aishell4", True, 0.3, False), self._row("aishell4", False, 0.7, True)]
        v = evaluate_hypotheses(rows)
        for h in ("h36a", "h36b", "h36c"):
            self.assertIn(h, v)
            self.assertIn("supported", v[h])
            self.assertIn("statement", v[h])


if __name__ == "__main__":
    unittest.main()
