"""Qualitative/demo Streamlit viewer for project storyboard and gold benchmark summary."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]

GOLD_AVERAGES = [
    ("fixed_mixed_whisper", 0.302093),
    ("fixed_separated_whisper", 0.191846),
    ("fixed_separated_whisper_cleaned", 0.181681),
    ("router_v2", 0.120042),
    ("oracle_best", 0.120042),
]


def load_storyboard_cards() -> list[dict[str, str]]:
    path = PROJECT_ROOT / "results" / "tables" / "demo_storyboard_cards.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [card for card in payload if isinstance(card, dict)]


def main() -> None:
    st.set_page_config(page_title="Overlap-aware ASR Demo", layout="wide")
    st.title("When Should We Separate?")
    st.caption("Qualitative/demo viewer — not a live ASR runtime.")

    cards = load_storyboard_cards()
    if cards:
        st.subheader("Storyboard")
        cols = st.columns(min(len(cards), 4))
        for idx, card in enumerate(cards):
            with cols[idx % len(cols)]:
                st.markdown(f"**{card.get('title', 'Card')}**")
                st.write(card.get("body", ""))

    st.subheader("Gold Benchmark Averages")
    st.table(
        {
            "strategy": [row[0] for row in GOLD_AVERAGES],
            "average CER": [f"{row[1]:.6f}" for row in GOLD_AVERAGES],
        }
    )

    st.info(
        "This demo surfaces existing stable/gold and qualitative/demo artifacts. "
        "It does not run Whisper, separation, or routing live."
    )


if __name__ == "__main__":
    main()
