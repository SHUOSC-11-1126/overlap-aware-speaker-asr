from __future__ import annotations

import re


def normalize_for_character_wer(text: str) -> str:
    text = re.sub(r"\[SPEAKER_\d+\]", "", text)
    text = text.replace("\n", "").replace("\r", "").replace(" ", "")
    text = re.sub(r"[^\w\u4e00-\u9fff]", "", text)
    return text


def tokenize_chinese_for_meeteval(text: str) -> str:
    normalized = normalize_for_character_wer(text)
    if not normalized:
        return ""
    return " ".join(list(normalized))


def count_meeteval_tokens(text: str) -> int:
    tokenized = tokenize_chinese_for_meeteval(text)
    if not tokenized:
        return 0
    return len(tokenized.split())
