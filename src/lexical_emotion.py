"""Offline regex/lexicon lexical-emotion extractor (experimental/frontier).

The acoustic prosody library (`src/prosody.py`) captures the AROUSAL side of emotion but is blind to
VALENCE (positive vs negative) — which in debate speech lives in the WORDS, i.e. in the ASR transcript.
This module is the complementary "text track": a deterministic, fully-offline Chinese emotion reader
built from a curated keyword lexicon plus regex rules for negation and intensification (the "用正则辅助
情感分析" direction). No model, no network, no labels.

It exists for three jobs:
  1. give VALENCE that acoustic arousal cannot (a fuller emotion picture: valence + arousal);
  2. measure whether ASR errors corrupt a speaker's lexical emotion (the lexical separation-tax),
     tying emotion to the ASR OUTPUT rather than the audio;
  3. provide a cheap, structured emotion signal to feed the prosody-grounded LLM critic
     (`src/llm_asr_critic.py`) — the 2025/26 SER frontier (EmotionThinker, VoxEmo, ProsodyLM) finds
     speech-LLMs have weak prosody/affect perception, so injecting explicit lexical + prosodic cues is
     the complementary fusion direction.

The lexicon is a documented SEED (debate-oriented), not exhaustive; it is meant to be extended.

Labels: experimental/frontier. Pure deterministic text logic; unit-tested.
"""
from __future__ import annotations

import re
from typing import Any

# --- Seed Chinese emotion lexicon (debate-oriented; extend freely) -----------------------------
POSITIVE = [
    "支持", "赞成", "赞同", "认同", "同意", "好", "优秀", "正确", "重要", "有利", "进步",
    "希望", "成功", "喜欢", "积极", "合理", "受益", "优势", "改善", "可行", "肯定", "值得",
]
NEGATIVE = [
    "反对", "错误", "危险", "失败", "问题", "担心", "糟糕", "严重", "威胁", "损害", "不利",
    "质疑", "批评", "痛苦", "愤怒", "反感", "否定", "缺陷", "风险", "灾难", "恶化", "无法",
]
INTENSIFIERS = ["非常", "极其", "十分", "特别", "相当", "格外", "尤其", "很", "太", "最", "极", "更"]
# Note: standalone "非" is intentionally excluded — it collides with the intensifier "非常"
# (非常好 must not read as negated). Explicit "并非" is kept. Modern negation is covered by 不/没/无.
NEGATORS = ["不", "没有", "没", "无", "别", "未", "毫不", "并非"]
HIGH_AROUSAL = ["绝对", "强烈", "必须", "震惊", "愤怒", "激烈", "拼命", "崩溃", "疯狂", "极力", "坚决"]

NEGATION_WINDOW = 4   # chars before a sentiment word to scan for a negator
INTENSIFIER_FACTOR = 1.8


def _find_all(text: str, word: str) -> list[int]:
    return [m.start() for m in re.finditer(re.escape(word), text)]


def _has_in_window(text: str, idx: int, vocab: list[str], window: int) -> bool:
    pre = text[max(0, idx - window): idx]
    return any(v in pre for v in vocab)


def lexical_emotion(text: str) -> dict[str, Any]:
    """Deterministic valence + arousal from Chinese text via keyword + regex rules.

    valence  signed (positive=approval, negative=opposition), negation-aware, intensifier-scaled,
             length-normalized by sqrt(chars) so intensified short phrases score higher.
    arousal  non-negative: high-arousal markers + intensifiers + exclamation/question density.
    """
    if not text:
        return {"valence": 0.0, "arousal": 0.0, "n_pos": 0, "n_neg": 0, "n_neg_flips": 0,
                "n_high_arousal": 0, "n_intensifier": 0, "length": 0}

    n_chars = len(text)
    valence_raw = 0.0
    n_pos = n_neg = n_flips = 0

    def score(words: list[str], polarity: float) -> None:
        nonlocal valence_raw, n_pos, n_neg, n_flips
        for w in words:
            for idx in _find_all(text, w):
                p = polarity
                if _has_in_window(text, idx, NEGATORS, NEGATION_WINDOW):
                    p = -p
                    n_flips += 1
                weight = 1.0
                if _has_in_window(text, idx, INTENSIFIERS, NEGATION_WINDOW):
                    weight = INTENSIFIER_FACTOR
                valence_raw += p * weight
                if p > 0:
                    n_pos += 1
                else:
                    n_neg += 1

    score(POSITIVE, +1.0)
    score(NEGATIVE, -1.0)

    n_high = sum(len(_find_all(text, w)) for w in HIGH_AROUSAL)
    n_int = sum(len(_find_all(text, w)) for w in INTENSIFIERS)
    n_excl = text.count("！") + text.count("!") + text.count("？") + text.count("?")
    arousal_raw = float(n_high + n_int + n_excl)

    norm = (n_chars ** 0.5) or 1.0
    return {
        "valence": round(valence_raw / norm, 6),
        "arousal": round(arousal_raw / norm, 6),
        "n_pos": n_pos, "n_neg": n_neg, "n_neg_flips": n_flips,
        "n_high_arousal": n_high, "n_intensifier": n_int, "length": n_chars,
    }


def emotion_vector(text: str) -> tuple[float, float]:
    """(valence, arousal) — the 2-D affect point used for distances."""
    e = lexical_emotion(text)
    return e["valence"], e["arousal"]


def lexical_distance(ref_text: str, hyp_text: str) -> dict[str, float]:
    """Lexical-emotion distortion between a reference transcript and a hypothesis. Used by the
    lexical separation-tax: how much does an ASR error move the speaker's textual emotion?"""
    vr, ar = emotion_vector(ref_text)
    vh, ah = emotion_vector(hyp_text)
    vd, ad = abs(vr - vh), abs(ar - ah)
    return {"valence_dist": round(vd, 6), "arousal_dist": round(ad, 6),
            "combined": round((vd ** 2 + ad ** 2) ** 0.5, 6)}
