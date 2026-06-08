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
    receipt_batch_scaffold = load_json_list("results/tables/meeteval_cpwer_execution_receipt_batch_scaffold.json")
    execution_status_batch = load_json_list("results/tables/meeteval_cpwer_execution_status_batch.json")
    completion_summary = load_json_dict(
        "results/tables/meeteval_cpwer_execution_status_batch_completion_summary.json"
    )
    batch_handoff = load_json_list("results/tables/meeteval_cpwer_execution_status_batch_handoff.json")
    official_execution = load_json_list("results/tables/meeteval_cpwer_official_execution.json")
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
    if preflight_batch:
        pass_count = sum(1 for row in preflight_batch if str(row.get("preflight_pass", "")).lower() == "true")
        st.metric("MeetEval preflight batch", f"{pass_count}/{len(preflight_batch)} cases passed")
        st.markdown("**MeetEval preflight batch cases**")
        st.table(
            {
                "case_id": [row.get("case_id", "") for row in preflight_batch],
                "preflight_pass": [row.get("preflight_pass", "") for row in preflight_batch],
                "hypothesis_source": [row.get("hypothesis_source", "") for row in preflight_batch],
            }
        )
    if receipt_batch_scaffold:
        st.metric(
            "MeetEval receipt scaffolds",
            f"{len(receipt_batch_scaffold)}/5 cases scaffolded",
        )
    if execution_status_batch:
        ready_count = sum(
            1 for row in execution_status_batch if row.get("execution_chain_status") == "execution_chain_ready"
        )
        st.metric("MeetEval execution chain", f"{ready_count}/{len(execution_status_batch)} cases ready")
    if completion_summary:
        st.metric(
            "Batch chain queue",
            completion_summary.get("queue_status", "unknown"),
        )
    if batch_handoff:
        first_ready = next(
            (row for row in batch_handoff if row.get("handoff_status") == "execution_handoff_ready"),
            None,
        )
        if first_ready:
            st.caption(
                f"Next official cpWER target: `{first_ready.get('case_id', '')}` "
                f"({first_ready.get('hypothesis_source', '')})"
            )
    if official_execution:
        st.markdown("**Official MeetEval cpWER narrow dry run**")
        st.table(
            {
                "case_id": [row.get("case_id", "") for row in official_execution],
                "status": [row.get("execution_status", "") for row in official_execution],
                "official_cpwer": [row.get("official_cpwer", "—") or "—" for row in official_execution],
            }
        )
    char_execution = load_json_list("results/tables/meeteval_cpwer_character_level_official_execution.json")
    reconciliation = load_json_list("results/tables/meeteval_cpwer_official_execution_reconciliation_audit.json")
    if char_execution:
        st.markdown("**Character-spaced MeetEval cpWER (reconciled)**")
        st.table(
            {
                "case_id": [row.get("case_id", "") for row in char_execution],
                "char_cpwer": [row.get("official_cpwer", "—") or "—" for row in char_execution],
                "raw_cpwer": [row.get("official_cpwer_raw", "—") or "—" for row in char_execution],
            }
        )
    if reconciliation:
        aligned = sum(1 for row in reconciliation if row.get("reconciliation_status") == "aligned")
        st.metric("Bridge-lite reconciliation", f"{aligned}/{len(reconciliation)} aligned")
        st.table(
            {
                "case_id": [row.get("case_id", "") for row in reconciliation],
                "char_cpwer": [row.get("character_level_cpwer", "—") for row in reconciliation],
                "bridge_lite": [row.get("cpwer_bridge_lite", "—") for row in reconciliation],
                "status": [row.get("reconciliation_status", "") for row in reconciliation],
            }
        )
    tokenization_handoff = load_json_dict("results/tables/meeteval_tokenization_adaptation_handoff.json")
    if tokenization_handoff:
        st.markdown("**Tokenization adaptation handoff**")
        st.metric("Handoff status", tokenization_handoff.get("handoff_status", "unknown"))
        st.caption(f"Target: `{tokenization_handoff.get('handoff_target', '')}`")
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


def render_speaker_profile_status() -> None:
    diagnostic = load_json_list("results/tables/speaker_profile_text_proxy_trial_diagnostic.json")
    summary = load_json_dict("results/tables/speaker_profile_text_proxy_trial_diagnostic_summary.json")
    completion = load_json_dict("results/tables/speaker_profile_text_proxy_trial_diagnostic_completion_summary.json")
    bridge = load_json_list("results/tables/speaker_profile_text_proxy_trial_diagnostic_bridge_checklist.json")
    if not summary:
        st.warning("Speaker profile text-proxy diagnostic summary not found.")
        return
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric(
            "Swapped bias",
            f"{summary.get('swapped_count', '0')}/{summary.get('case_count', '0')} cases",
        )
        st.metric("Average confidence gap", summary.get("average_confidence_gap", "—"))
    with col_b:
        if completion:
            st.metric("Diagnostic queue", completion.get("queue_status", "unknown"))
        st.caption(f"Next method: `{summary.get('next_method_direction', '')}`")
    if diagnostic:
        st.markdown("**All-gold text-proxy diagnostic**")
        st.table(
            {
                "case_id": [row.get("case_id", "") for row in diagnostic],
                "alignment": [row.get("best_profile_alignment", "") for row in diagnostic],
                "gap": [row.get("profile_confidence_gap", "") for row in diagnostic],
            }
        )
    if bridge:
        st.markdown("**Diagnostic bridge checklist**")
        st.write(bridge[0].get("bridge_note", ""))
        st.caption(f"Next gate: {bridge[0].get('next_gate', '')}")
    handoff_readiness = load_json_dict("results/tables/speaker_profile_embedding_trial_handoff_readiness.json")
    handoff_completion = load_json_dict(
        "results/tables/speaker_profile_embedding_trial_handoff_completion_summary.json"
    )
    embedding_handoff = load_json_dict("results/tables/speaker_profile_embedding_trial_handoff.json")
    embedding_trial = load_json_dict("results/tables/speaker_profile_embedding_trial.json")
    if handoff_readiness:
        st.markdown("**Embedding trial handoff readiness**")
        col_c, col_d = st.columns(2)
        with col_c:
            st.metric("Handoff readiness", handoff_readiness.get("readiness_status", "unknown"))
        with col_d:
            st.metric("Trial target", handoff_readiness.get("trial_case_target", "—"))
    if handoff_completion:
        st.caption(f"Handoff queue: `{handoff_completion.get('queue_status', '')}`")
    if embedding_handoff:
        st.markdown("**Embedding trial handoff**")
        st.write(embedding_handoff.get("handoff_goal", ""))
    if embedding_trial:
        st.table(
            {
                "field": ["case_id", "trial_status", "profile_confidence_gap"],
                "value": [
                    embedding_trial.get("case_id", ""),
                    embedding_trial.get("trial_status", ""),
                    embedding_trial.get("profile_confidence_gap", ""),
                ],
            }
        )
    scaffold_readiness = load_json_dict(
        "results/tables/speaker_profile_embedding_trial_execution_scaffold_readiness.json"
    )
    if scaffold_readiness:
        st.markdown("**Execution scaffold readiness**")
        st.metric("Scaffold readiness", scaffold_readiness.get("readiness_status", "unknown"))
        st.caption(f"Case: `{scaffold_readiness.get('case_id', '')}`")
    st.info(
        "Text-profile proxy is a risk signal only — not deployment-ready speaker identification. "
        "All gold cases currently prefer swapped alignment."
    )


def main() -> None:
    st.set_page_config(page_title="Overlap-aware ASR Demo", layout="wide")
    st.title("When Should We Separate?")
    st.caption("Qualitative/demo viewer — not a live ASR runtime.")

    tab_story, tab_walk, tab_gold, tab_frontier, tab_speaker = st.tabs(
        ["Storyboard", "Walkthrough", "Gold CER", "Frontier fill queue", "Speaker profile"]
    )
    with tab_story:
        render_storyboard()
    with tab_walk:
        render_walkthrough()
    with tab_gold:
        render_gold_table()
    with tab_frontier:
        render_frontier_fill_status()
    with tab_speaker:
        render_speaker_profile_status()

    st.info(
        "This demo surfaces existing stable/gold and qualitative/demo artifacts. "
        "It does not run Whisper, separation, or routing live."
    )


if __name__ == "__main__":
    main()
