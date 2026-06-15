from __future__ import annotations

import re
import unicodedata


def normalize_asr_text(text: str) -> str:
    """Conservative CER normalization for Chinese ASR text."""
    text = unicodedata.normalize("NFKC", text or "").lower()
    text = re.sub(r"\[speaker_[12]\]", "", text)
    chars = []
    for char in text:
        if "\u4e00" <= char <= "\u9fff" or char.isalnum():
            chars.append(char)
    return "".join(chars)


def cer(reference: str, hypothesis: str) -> float:
    ref = normalize_asr_text(reference)
    hyp = normalize_asr_text(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    prev = list(range(len(hyp) + 1))
    for i, rc in enumerate(ref, start=1):
        curr = [i]
        for j, hc in enumerate(hyp, start=1):
            cost = 0 if rc == hc else 1
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost))
        prev = curr
    return round(prev[-1] / len(ref), 6)


def length_ratio(reference: str, hypothesis: str) -> float:
    ref_len = len(normalize_asr_text(reference))
    hyp_len = len(normalize_asr_text(hypothesis))
    if ref_len == 0:
        return 0.0 if hyp_len == 0 else 999.0
    return round(hyp_len / ref_len, 6)
