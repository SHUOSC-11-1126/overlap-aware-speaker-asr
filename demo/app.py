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


def load_json_list(path_rel: str) -> list[dict[str, str]]:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def load_json_dict(path_rel: str) -> dict[str, str]:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def render_storyboard() -> None:
    cards = load_json_list("results/tables/demo_storyboard_cards.json")
    if not cards:
        st.warning("Storyboard cards not found.")
        return
    cols = st.columns(min(len(cards), 4))
    for idx, card in enumerate(cards):
        with cols[idx % len(cols)]:
            st.markdown(f"**{card.get('title', 'Card')}**")
            st.write(card.get("body", ""))


def render_walkthrough() -> None:
    steps = load_json_list("results/tables/demo_walkthrough_steps.json")
    if not steps:
        st.warning("Walkthrough steps not found.")
        return
    for step in steps:
        st.markdown(f"**Step {step.get('step_id', '?')}: {step.get('focus', 'Focus')}**")
        st.write(step.get("talk_track", ""))
        st.caption(f"Artifact: `{step.get('artifact_anchor', '')}`")


def render_gold_table() -> None:
    st.table(
        {
            "strategy": [row[0] for row in GOLD_AVERAGES],
            "average CER": [f"{row[1]:.6f}" for row in GOLD_AVERAGES],
        }
    )


def render_frontier_fill_status() -> None:
    summary = load_json_dict("results/tables/frontier_execution_receipt_fill_queue_summary.json")
    execution = load_json_dict("results/tables/frontier_execution_receipt_fill_execution_status.json")
    completion = load_json_dict("results/tables/frontier_execution_receipt_fill_execution_completion_summary.json")
    rows = load_json_list("results/tables/frontier_execution_receipt_fill_queue_status.json")
    handoff_rows = load_json_list("results/tables/frontier_execution_receipt_fill_execution_handoff.json")
    operator_brief = load_json_dict("results/tables/frontier_execution_receipt_fill_execution_operator_brief.json")
    runbook = load_json_dict("results/tables/frontier_execution_receipt_fill_execution_runbook_card.json")
    dashboard = load_json_dict("results/tables/frontier_execution_receipt_fill_execution_completion_dashboard.json")
    preflight_batch = load_json_list("results/tables/meeteval_cpwer_execution_preflight_batch.json")
    if not summary:
        st.warning("Frontier fill queue summary not found.")
        return
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Fill queue status", summary.get("combined_fill_status", "unknown"))
        st.metric(
            "Awaiting fill",
            f"{summary.get('awaiting_fill_count', '0')}/{summary.get('total_frontier_count', '0')}",
        )
    with col_b:
        if execution:
            st.metric(
                "Fill execution status",
                execution.get("combined_fill_execution_status", "unknown"),
            )
        if completion:
            st.metric(
                "Awaiting fill execution",
                (
                    f"{completion.get('awaiting_fill_execution_count', '0')}/"
                    f"{completion.get('total_frontier_count', '0')}"
                ),
            )
    if rows:
        st.table(
            {
                "frontier": [row.get("frontier_name", "") for row in rows],
                "fill_status": [row.get("fill_status", "") for row in rows],
                "execution_status": [row.get("execution_status", "") for row in rows],
            }
        )
    if dashboard:
        st.markdown("**Fill execution dashboard**")
        st.write(dashboard.get("dashboard_note", ""))
    if runbook:
        st.markdown("**Fill execution runbook card**")
        st.write(runbook.get("runbook_note", ""))
        st.caption(f"Action: `{runbook.get('recommended_action', '')}`")
    if operator_brief:
        st.markdown("**Fill execution operator brief**")
        st.write(operator_brief.get("operator_note", ""))
        st.caption(
            f"First target: `{operator_brief.get('operator_frontier', '')}` → "
            f"`{operator_brief.get('operator_receipt', '')}`"
        )
    if handoff_rows:
        st.markdown("**Fill execution handoff actions**")
        st.table(
            {
                "frontier": [row.get("frontier_name", "") for row in handoff_rows],
                "fill execution status": [row.get("fill_execution_status", "") for row in handoff_rows],
                "recommended action": [row.get("recommended_action", "") for row in handoff_rows],
            }
        )


def main() -> None:
    st.set_page_config(page_title="Overlap-aware ASR Demo", layout="wide")
    st.title("When Should We Separate?")
    st.caption("Qualitative/demo viewer — not a live ASR runtime.")

    tab_story, tab_walk, tab_gold, tab_frontier = st.tabs(
        ["Storyboard", "Walkthrough", "Gold CER", "Frontier fill queue"]
    )
    with tab_story:
        render_storyboard()
    with tab_walk:
        render_walkthrough()
    with tab_gold:
        render_gold_table()
    with tab_frontier:
        render_frontier_fill_status()

    st.info(
        "This demo surfaces existing stable/gold and qualitative/demo artifacts. "
        "It does not run Whisper, separation, or routing live."
    )


if __name__ == "__main__":
    main()
