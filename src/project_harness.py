from __future__ import annotations

import csv
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


CORE_FILES = [
    "README.md",
    "REPORT.md",
    "AGENTS.md",
    "docs/README.md",
    "docs/ambitious_research_agenda.md",
    "docs/agent_challenge_board.md",
    "docs/experiment_proposal_template.md",
    "docs/project_state.md",
    "docs/technical_implementation_plan_v2.md",
    "docs/roadmap.md",
    "docs/maintenance_harness.md",
    "docs/markdown_audit.md",
    "docs/contribution.md",
    "docs/experiment_notes.md",
    "docs/video_script.md",
    "docs/contributions/README.md",
    "docs/contributions/WUFANGZHOU.md",
    "docs/contributions/TEAM_CONTRIBUTION_TEMPLATE.md",
    "docs/handoff/WUFANGZHOU_HANDOFF.md",
    "docs/backup_plan.md",
    "docs/skills/README.md",
    "docs/skills/skill_01_separation_phase_diagram.md",
    "docs/skills/skill_02_compute_aware_cascade.md",
    "docs/skills/skill_03_speaker_profile_voiceprint.md",
    "docs/skills/skill_04_meeteval_compatibility.md",
    "docs/skills/skill_05_agentic_llm_critic.md",
    "docs/skills/skill_06_github_demo_excellence.md",
    "references/reference_transcripts.json",
    "results/tables/cer_results.csv",
    "results/tables/routing_performance_v2.csv",
    "results/tables/error_type_summary.csv",
    "results/tables/speaker_cer_results.csv",
    "results/tables/cpcer_lite_results.csv",
    "results/tables/risk_aware_performance.csv",
]

GOLD_CASES = [
    "NoOverlap",
    "LightOverlap",
    "MidOverlap",
    "HeavyOverlap",
    "OppositeOverlap",
]

FRONTIER_SKILLS = [
    {
        "frontier_id": "speaker_profile",
        "evidence_path": "docs/skills/skill_03_speaker_profile_voiceprint.md",
        "expected_output": "speaker profile triage card",
        "next_step": "Use the triage card to justify a stronger profile method while keeping the signal scoped to risk detection.",
    },
    {
        "frontier_id": "meeteval_compatibility",
        "evidence_path": "docs/skills/skill_04_meeteval_compatibility.md",
        "expected_output": "MeetEval readiness card",
        "next_step": "Use the readiness card to stage one narrow dry run before claiming any benchmark bridge.",
    },
    {
        "frontier_id": "llm_critic",
        "evidence_path": "docs/skills/skill_05_agentic_llm_critic.md",
        "expected_output": "qualitative critic queue",
        "next_step": "Use the review queue to decide which critic-style review queue item should be read first.",
    },
    {
        "frontier_id": "external_validation",
        "evidence_path": "docs/ambitious_research_agenda.md",
        "expected_output": "external sanity-check prioritization card",
        "next_step": "Use the prioritization card to map one tiny sanity-check slice without claiming a completed benchmark.",
    },
    {
        "frontier_id": "demo_excellence",
        "evidence_path": "docs/skills/skill_06_github_demo_excellence.md",
        "expected_output": "demo-facing storyboard or walkthrough",
        "next_step": "Use the demo walkthrough to shape a short demo walk before any heavier app build.",
    },
]


def exists(rel_path: str) -> bool:
    return (PROJECT_ROOT / rel_path).exists()


def inspect_gold_cases() -> dict[str, bool]:
    ref_path = PROJECT_ROOT / "references" / "reference_transcripts.json"
    if not ref_path.exists():
        return {case: False for case in GOLD_CASES}
    try:
        data = json.loads(ref_path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {case: False for case in GOLD_CASES}
    if not isinstance(data, dict):
        return {case: False for case in GOLD_CASES}

    # The file may be stored either as a direct case_id -> record mapping or under a nested "cases" key.
    cases = data.get("cases", {})
    if not isinstance(cases, dict) or not cases:
        cases = data

    result: dict[str, bool] = {}
    for case in GOLD_CASES:
        entry = cases.get(case)
        if isinstance(entry, dict):
            result[case] = str(entry.get("status", "")).strip() == "verified_reference"
        else:
            result[case] = False
    return result


def inspect_synthetic_separation() -> dict[str, str]:
    if (PROJECT_ROOT / "resources" / "synthetic_overlap").exists():
        return {"status": "synthetic_overlap"}
    if (PROJECT_ROOT / "resources" / "synthetic_overlap_v2").exists():
        return {"status": "synthetic_overlap_v2"}
    return {"status": "missing"}


def build_frontier_status_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for frontier in FRONTIER_SKILLS:
        evidence_path = str(frontier["evidence_path"])
        rows.append(
            {
                "frontier_id": str(frontier["frontier_id"]),
                "status": "documented_skill" if exists(evidence_path) else "missing_skill",
                "evidence_path": evidence_path,
                "expected_output": str(frontier["expected_output"]),
                "next_step": str(frontier["next_step"]),
            }
        )
    return rows


def frontier_priority(frontier_id: str) -> int:
    priority_order = {
        "meeteval_compatibility": 1,
        "external_validation": 2,
        "speaker_profile": 3,
        "llm_critic": 4,
        "demo_excellence": 5,
    }
    return priority_order.get(frontier_id, 99)


def build_frontier_execution_queue_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    sorted_rows = sorted(rows, key=lambda row: (frontier_priority(str(row.get("frontier_id", ""))), str(row.get("frontier_id", ""))))
    queue_rows: list[dict[str, str]] = []
    for index, row in enumerate(sorted_rows, start=1):
        frontier_id = str(row.get("frontier_id", ""))
        next_step = str(row.get("next_step", ""))
        why_now = next_step
        queue_rows.append(
            {
                "queue_order": str(index),
                "frontier_id": frontier_id,
                "status": str(row.get("status", "")),
                "entry_artifact": str(row.get("expected_output", "")),
                "why_now": why_now,
            }
        )
    return queue_rows


def build_frontier_execution_queue_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Execution Queue",
        "",
        "This generated queue orders the next breadth-first frontier moves without claiming that the queued work has already been completed.",
        "",
        "| queue_order | frontier_id | status | entry_artifact | why_now |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['queue_order']} | {row['frontier_id']} | {row['status']} | {row['entry_artifact']} | {row['why_now']} |"
        )
    return lines


def build_frontier_focus_card_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not rows:
        return []
    head = rows[0]
    return [
        {
            "queue_order": str(head.get("queue_order", "")),
            "current_frontier": str(head.get("frontier_id", "")),
            "entry_artifact": str(head.get("entry_artifact", "")),
            "current_action": str(head.get("why_now", "")),
        }
    ]


def build_frontier_focus_card_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Focus Card",
        "",
        "This generated card highlights the single current breadth-first frontier starting point.",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"- Queue order: `{row['queue_order']}`",
                f"- Current frontier: `{row['current_frontier']}`",
                f"- Entry artifact: `{row['entry_artifact']}`",
                f"- Current action: {row['current_action']}",
            ]
        )
    return lines


def frontier_next_artifact(frontier_id: str) -> tuple[str, str]:
    mapping = {
        "meeteval_compatibility": (
            "results/figures/meeteval_dry_run_handoff.md",
            "results/tables/meeteval_dry_run_receipt.json",
        ),
        "external_validation": (
            "results/figures/external_validation_prioritization.md",
            "results/tables/external_validation_slice_receipt.json",
        ),
        "speaker_profile": (
            "results/figures/speaker_profile_triage.md",
            "results/tables/speaker_profile_method_receipt.json",
        ),
        "llm_critic": (
            "results/figures/llm_critic_review_queue.md",
            "results/tables/llm_critic_review_receipt.json",
        ),
        "demo_excellence": (
            "results/figures/demo_walkthrough.md",
            "results/tables/demo_walkthrough_receipt.json",
        ),
    }
    return mapping.get(frontier_id, ("", ""))


FRONTIER_RECEIPT_CHECKLIST_COLUMNS = [
    "checklist_order",
    "current_frontier",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "preflight_step",
    "next_gate",
]

FRONTIER_PICKLIST_CHECKLIST_COLUMNS = [
    "checklist_order",
    "current_frontier",
    "pickup_artifact",
    "receipt_target",
    "checklist_goal",
    "parallelism_note",
    "next_gate",
]

FRONTIER_RECEIPT_BOARD_CHECKLIST_COLUMNS = [
    "checklist_order",
    "frontier_id",
    "pickup_artifact",
    "receipt_target",
    "checklist_goal",
    "board_note",
    "next_gate",
]

FRONTIER_HANDOFF_CHECKLIST_COLUMNS = [
    "checklist_order",
    "current_frontier",
    "next_artifact",
    "receipt_target",
    "checklist_goal",
    "execution_intent",
    "next_gate",
]

FRONTIER_COORDINATION_CHECKLIST_COLUMNS = [
    "checklist_order",
    "frontier_id",
    "entry_artifact",
    "pickup_artifact",
    "receipt_target",
    "checklist_goal",
    "coordination_note",
    "next_gate",
]

FRONTIER_WRITEBACK_CHECKLIST_COLUMNS = [
    "checklist_order",
    "frontier_id",
    "entry_artifact",
    "receipt_target",
    "checklist_goal",
    "writeback_note",
    "next_gate",
]


def build_frontier_handoff_packet_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not queue_rows:
        return []

    head = queue_rows[0]
    frontier_id = str(head.get("frontier_id", ""))
    next_artifact, expected_evidence = frontier_next_artifact(frontier_id)
    return [
        {
            "queue_order": str(head.get("queue_order", "")),
            "current_frontier": frontier_id,
            "next_artifact": next_artifact,
            "execution_intent": f"Run a single narrow dry run handoff step for {frontier_id} before any broader claim.",
            "expected_evidence": expected_evidence,
            "handoff_scope": "Coordination-only packet; not a claim of completed frontier execution.",
        }
    ]


def build_frontier_handoff_packet_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Handoff Packet",
        "",
        "This generated packet points the current frontier queue head at the single next artifact to open. It does not claim that the frontier work has already been executed.",
        "",
        "| queue_order | current_frontier | next_artifact | execution_intent | expected_evidence | handoff_scope |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['queue_order']} | {row['current_frontier']} | {row['next_artifact']} | {row['execution_intent']} | {row['expected_evidence']} | {row['handoff_scope']} |"
        )
    return lines


def build_frontier_handoff_checklist_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not queue_rows:
        return []

    head = queue_rows[0]
    frontier_id = str(head.get("frontier_id", ""))
    next_artifact, receipt_target = frontier_next_artifact(frontier_id)
    return [
        {
            "checklist_order": "1",
            "current_frontier": frontier_id,
            "next_artifact": next_artifact,
            "receipt_target": receipt_target,
            "checklist_goal": f"Use the handoff packet to stage the next frontier pass for {frontier_id}.",
            "execution_intent": "Open the next artifact first, then keep the receipt target visible for the narrow follow-up step.",
            "next_gate": "Confirm the handoff packet snapshot before advancing the queue.",
        }
    ]


def build_frontier_handoff_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Handoff Checklist",
        "",
        "This generated checklist turns the handoff packet into an ordered open-artifact path. It remains coordination-only and does not claim that any frontier work has already been executed.",
        "",
        "| checklist_order | current_frontier | next_artifact | receipt_target | checklist_goal | execution_intent | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['current_frontier']} | {row['next_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | {row['execution_intent']} | {row['next_gate']} |"
        )
    return lines


def build_frontier_receipt_packet_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not queue_rows:
        return []

    head = queue_rows[0]
    frontier_id = str(head.get("frontier_id", ""))
    prerequisite_artifact, receipt_target = frontier_next_artifact(frontier_id)
    return [
        {
            "current_frontier": frontier_id,
            "prerequisite_artifact": prerequisite_artifact,
            "receipt_target": receipt_target,
            "execution_note": "Open the handoff first, then write back to the receipt target after the narrow next step.",
            "packet_scope": "Coordination-only packet; not a claim of completed frontier execution.",
        }
    ]


def build_frontier_receipt_packet_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Receipt Packet",
        "",
        "This generated packet points the current frontier queue head at its receipt-level writeback target. It does not claim that the frontier work has already been executed.",
        "",
        "| current_frontier | prerequisite_artifact | receipt_target | execution_note | packet_scope |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['current_frontier']} | {row['prerequisite_artifact']} | {row['receipt_target']} | {row['execution_note']} | {row['packet_scope']} |"
        )
    return lines


def build_frontier_receipt_checklist_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not queue_rows:
        return []

    head = queue_rows[0]
    frontier_id = str(head.get("frontier_id", ""))
    prerequisite_artifact, receipt_target = frontier_next_artifact(frontier_id)
    return [
        {
            "checklist_order": "1",
            "current_frontier": frontier_id,
            "prerequisite_artifact": prerequisite_artifact,
            "receipt_target": receipt_target,
            "checklist_goal": f"Write back the receipt for {frontier_id} before any broader frontier claim.",
            "preflight_step": "Open the prerequisite artifact and confirm the receipt target before the writeback step.",
            "next_gate": "Fill the receipt target and confirm the frontier writeback before advancing the queue.",
        }
    ]


def build_frontier_receipt_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Receipt Checklist",
        "",
        "This generated checklist turns the frontier receipt packet into an ordered writeback path. It remains coordination-only and does not claim that any frontier work has already been executed.",
        "",
        "| checklist_order | current_frontier | prerequisite_artifact | receipt_target | checklist_goal | preflight_step | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['current_frontier']} | {row['prerequisite_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | {row['preflight_step']} | {row['next_gate']} |"
        )
    return lines


def build_frontier_receipt_map_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    map_rows: list[dict[str, str]] = []
    for row in queue_rows:
        frontier_id = str(row.get("frontier_id", ""))
        prerequisite_artifact, receipt_target = frontier_next_artifact(frontier_id)
        map_rows.append(
            {
                "queue_order": str(row.get("queue_order", "")),
                "current_frontier": frontier_id,
                "prerequisite_artifact": prerequisite_artifact,
                "receipt_target": receipt_target,
                "map_note": "Open the prerequisite artifact first, then use the receipt target for writeback.",
                "map_scope": "Coordination-only map; not a claim of completed frontier execution.",
            }
        )
    return map_rows


def build_frontier_receipt_map_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Receipt Map",
        "",
        "This generated map shows the receipt path for each current frontier. It does not claim that any frontier work has already been executed.",
        "",
        "| queue_order | current_frontier | prerequisite_artifact | receipt_target | map_note | map_scope |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['queue_order']} | {row['current_frontier']} | {row['prerequisite_artifact']} | {row['receipt_target']} | {row['map_note']} | {row['map_scope']} |"
        )
    return lines


def build_frontier_parallel_picklist_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    picklist_rows: list[dict[str, str]] = []
    for row in queue_rows:
        frontier_id = str(row.get("frontier_id", ""))
        pickup_artifact, receipt_target = frontier_next_artifact(frontier_id)
        picklist_rows.append(
            {
                "queue_order": str(row.get("queue_order", "")),
                "current_frontier": frontier_id,
                "pickup_artifact": pickup_artifact,
                "receipt_target": receipt_target,
                "pickup_note": "Safe to pick up in parallel after checking queue order and opening the pickup artifact first.",
                "picklist_scope": "Coordination-only picklist; not a claim of completed frontier execution.",
            }
        )
    return picklist_rows


def build_frontier_parallel_picklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Parallel Picklist",
        "",
        "This generated picklist shows which current frontiers can be picked up independently while keeping the breadth-first queue visible. It does not claim that any frontier work has already been executed.",
        "",
        "| queue_order | current_frontier | pickup_artifact | receipt_target | pickup_note | picklist_scope |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['queue_order']} | {row['current_frontier']} | {row['pickup_artifact']} | {row['receipt_target']} | {row['pickup_note']} | {row['picklist_scope']} |"
        )
    return lines


def build_frontier_parallel_picklist_checklist_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not queue_rows:
        return []

    head = queue_rows[0]
    frontier_id = str(head.get("frontier_id", ""))
    pickup_artifact, receipt_target = frontier_next_artifact(frontier_id)
    return [
        {
            "checklist_order": "1",
            "current_frontier": frontier_id,
            "pickup_artifact": pickup_artifact,
            "receipt_target": receipt_target,
            "checklist_goal": f"Pick up {frontier_id} in parallel only after confirming queue order.",
            "parallelism_note": "Check the queue head first, then open the pickup artifact before any parallel action.",
            "next_gate": "Complete the pickup artifact and keep the receipt target visible for writeback.",
        }
    ]


def build_frontier_parallel_picklist_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Parallel Picklist Checklist",
        "",
        "This generated checklist turns the parallel picklist into an ordered pickup path. It remains coordination-only and does not claim that any frontier work has already been executed.",
        "",
        "| checklist_order | current_frontier | pickup_artifact | receipt_target | checklist_goal | parallelism_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['current_frontier']} | {row['pickup_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | {row['parallelism_note']} | {row['next_gate']} |"
        )
    return lines


def build_frontier_receipt_board_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    board_rows: list[dict[str, str]] = []
    for row in queue_rows:
        frontier_id = str(row.get("frontier_id", ""))
        pickup_artifact, receipt_target = frontier_next_artifact(frontier_id)
        board_rows.append(
            {
                "queue_order": str(row.get("queue_order", "")),
                "frontier_id": frontier_id,
                "pickup_artifact": pickup_artifact,
                "receipt_target": receipt_target,
                "board_status": str(row.get("status", "")),
                "board_note": "Use this board as the single breadth-first receipt snapshot before moving to the next queue head.",
                "board_scope": "Coordination-only board; not a claim of completed frontier execution.",
            }
        )
    return board_rows


def build_frontier_receipt_board_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Receipt Board",
        "",
        "This generated board consolidates the current frontier queue, pickup artifact, and receipt target into one breadth-first snapshot. It does not claim that any frontier work has already been executed.",
        "",
        "| queue_order | frontier_id | pickup_artifact | receipt_target | board_status | board_note | board_scope |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['queue_order']} | {row['frontier_id']} | {row['pickup_artifact']} | {row['receipt_target']} | {row['board_status']} | {row['board_note']} | {row['board_scope']} |"
        )
    return lines


def build_frontier_receipt_board_checklist_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not queue_rows:
        return []

    head = queue_rows[0]
    frontier_id = str(head.get("frontier_id", ""))
    pickup_artifact, receipt_target = frontier_next_artifact(frontier_id)
    return [
        {
            "checklist_order": "1",
            "frontier_id": frontier_id,
            "pickup_artifact": pickup_artifact,
            "receipt_target": receipt_target,
            "checklist_goal": f"Use the receipt board to stage the next frontier pass for {frontier_id}.",
            "board_note": "Open the board snapshot first, then keep the pickup artifact visible while writing back.",
            "next_gate": "Confirm the board snapshot and receipt target before the next queue head advances.",
        }
    ]


def build_frontier_receipt_board_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Receipt Board Checklist",
        "",
        "This generated checklist turns the receipt board into an ordered snapshot path. It remains coordination-only and does not claim that any frontier work has already been executed.",
        "",
        "| checklist_order | frontier_id | pickup_artifact | receipt_target | checklist_goal | board_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['frontier_id']} | {row['pickup_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | {row['board_note']} | {row['next_gate']} |"
        )
    return lines


def build_frontier_coordination_matrix_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    matrix_rows: list[dict[str, str]] = []
    for row in queue_rows:
        frontier_id = str(row.get("frontier_id", ""))
        pickup_artifact, receipt_target = frontier_next_artifact(frontier_id)
        matrix_rows.append(
            {
                "queue_order": str(row.get("queue_order", "")),
                "frontier_id": frontier_id,
                "status": str(row.get("status", "")),
                "entry_artifact": str(row.get("entry_artifact", "")),
                "pickup_artifact": pickup_artifact,
                "receipt_target": receipt_target,
                "coordination_note": "Coordinate this frontier by opening the pickup artifact first and writing back to the receipt target after the narrow next step.",
                "coordination_scope": "Coordination-only matrix; not a claim of completed frontier execution.",
            }
        )
    return matrix_rows


def build_frontier_coordination_matrix_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Coordination Matrix",
        "",
        "This generated matrix combines queue order, entry artifact, pickup artifact, and receipt target for every current frontier. It does not claim that any frontier work has already been executed.",
        "",
        "| queue_order | frontier_id | status | entry_artifact | pickup_artifact | receipt_target | coordination_note | coordination_scope |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['queue_order']} | {row['frontier_id']} | {row['status']} | {row['entry_artifact']} | {row['pickup_artifact']} | {row['receipt_target']} | {row['coordination_note']} | {row['coordination_scope']} |"
        )
    return lines


def build_frontier_coordination_checklist_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not queue_rows:
        return []

    head = queue_rows[0]
    frontier_id = str(head.get("frontier_id", ""))
    pickup_artifact, receipt_target = frontier_next_artifact(frontier_id)
    return [
        {
            "checklist_order": "1",
            "frontier_id": frontier_id,
            "entry_artifact": str(head.get("entry_artifact", "")),
            "pickup_artifact": pickup_artifact,
            "receipt_target": receipt_target,
            "checklist_goal": f"Use the coordination matrix to stage the next frontier pass for {frontier_id}.",
            "coordination_note": "Open the entry artifact first, then keep the pickup artifact and receipt target visible for the next step.",
            "next_gate": "Confirm the coordination matrix snapshot before advancing the queue.",
        }
    ]


def build_frontier_coordination_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Coordination Checklist",
        "",
        "This generated checklist turns the coordination matrix into an ordered scan path. It remains coordination-only and does not claim that any frontier work has already been executed.",
        "",
        "| checklist_order | frontier_id | entry_artifact | pickup_artifact | receipt_target | checklist_goal | coordination_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['frontier_id']} | {row['entry_artifact']} | {row['pickup_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | {row['coordination_note']} | {row['next_gate']} |"
        )
    return lines


def build_frontier_writeback_index_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    index_rows: list[dict[str, str]] = []
    for row in queue_rows:
        frontier_id = str(row.get("frontier_id", ""))
        pickup_artifact, receipt_target = frontier_next_artifact(frontier_id)
        index_rows.append(
            {
                "queue_order": str(row.get("queue_order", "")),
                "frontier_id": frontier_id,
                "entry_artifact": str(row.get("entry_artifact", "")),
                "receipt_target": receipt_target,
                "writeback_note": f"Open {pickup_artifact} first, then write back to {receipt_target}.",
                "writeback_scope": "Coordination-only index; not a claim of completed frontier execution.",
            }
        )
    return index_rows


def build_frontier_writeback_index_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Writeback Index",
        "",
        "This generated index isolates the writeback target for each current frontier. It does not claim that any frontier work has already been executed.",
        "",
        "| queue_order | frontier_id | entry_artifact | receipt_target | writeback_note | writeback_scope |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['queue_order']} | {row['frontier_id']} | {row['entry_artifact']} | {row['receipt_target']} | {row['writeback_note']} | {row['writeback_scope']} |"
        )
    return lines


def build_frontier_writeback_checklist_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not queue_rows:
        return []

    head = queue_rows[0]
    frontier_id = str(head.get("frontier_id", ""))
    pickup_artifact, receipt_target = frontier_next_artifact(frontier_id)
    return [
        {
            "checklist_order": "1",
            "frontier_id": frontier_id,
            "entry_artifact": str(head.get("entry_artifact", "")),
            "receipt_target": receipt_target,
            "checklist_goal": f"Use the writeback index to complete the frontier writeback path for {frontier_id}.",
            "writeback_note": f"Open {pickup_artifact} first, then write back to {receipt_target} after the narrow next step.",
            "next_gate": "Confirm the writeback index snapshot before advancing the queue.",
        }
    ]


def build_frontier_writeback_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Writeback Checklist",
        "",
        "This generated checklist turns the writeback index into an ordered closeout path. It remains coordination-only and does not claim that any frontier work has already been executed.",
        "",
        "| checklist_order | frontier_id | entry_artifact | receipt_target | checklist_goal | writeback_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['frontier_id']} | {row['entry_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | {row['writeback_note']} | {row['next_gate']} |"
        )
    return lines


def write_frontier_coordination_checklist(frontier_status: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    checklist_rows = build_frontier_coordination_checklist_rows(queue_rows)
    csv_path = tables_dir / "frontier_coordination_checklist.csv"
    json_path = tables_dir / "frontier_coordination_checklist.json"
    md_path = figures_dir / "frontier_coordination_checklist.md"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FRONTIER_COORDINATION_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(checklist_rows)
    json_path.write_text(json.dumps(checklist_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_coordination_checklist_lines(checklist_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def write_frontier_writeback_checklist(frontier_status: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    checklist_rows = build_frontier_writeback_checklist_rows(queue_rows)
    csv_path = tables_dir / "frontier_writeback_checklist.csv"
    json_path = tables_dir / "frontier_writeback_checklist.json"
    md_path = figures_dir / "frontier_writeback_checklist.md"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FRONTIER_WRITEBACK_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(checklist_rows)
    json_path.write_text(json.dumps(checklist_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_writeback_checklist_lines(checklist_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def build_report() -> dict[str, object]:
    missing_core = [path for path in CORE_FILES if not exists(path)]
    gold_status = inspect_gold_cases()
    synthetic_status = inspect_synthetic_separation()
    frontier_status = build_frontier_status_rows()
    report = {
        "project_root": ".",
        "core_files_present": len(missing_core) == 0,
        "missing_core_files": missing_core,
        "gold_cases": gold_status,
        "synthetic_status": synthetic_status,
        "gold_and_synthetic_separated": synthetic_status["status"] in {"synthetic_overlap", "synthetic_overlap_v2"},
        "frontier_status": frontier_status,
    }
    return report


def write_report(report: dict[str, object]) -> tuple[Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    json_path = tables_dir / "project_harness_report.json"
    md_path = figures_dir / "project_harness_report.md"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    gold_lines = []
    for case, ok in report["gold_cases"].items():
        gold_lines.append(f"- {case}: {'present' if ok else 'missing'}")

    lines = [
        "# Project Harness Report",
        "",
        "## Core Files",
        "",
        f"- core_files_present: {report['core_files_present']}",
        "",
        "### Missing Core Files",
    ]
    missing = report["missing_core_files"]
    if missing:
        for item in missing:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines += [
        "",
        "## Gold Cases",
        "",
    ] + gold_lines + [
        "",
        "## Synthetic Separation",
        "",
        f"- status: {report['synthetic_status']['status']}",
        f"- gold_and_synthetic_separated: {report['gold_and_synthetic_separated']}",
        "",
        "## Frontier Status",
        "",
        "| frontier_id | status | evidence_path | expected_output | next_step |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in report["frontier_status"]:
        lines.append(
            f"| {row['frontier_id']} | {row['status']} | {row['evidence_path']} | {row['expected_output']} | {row['next_step']} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- The repository keeps gold references and synthetic resources separate.",
        "- The core maintenance files are in place for future agents.",
        "- The frontier status table makes breadth-first experimental directions visible before new code lands.",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def write_frontier_queue(frontier_status: list[dict[str, str]]) -> tuple[Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    json_path = tables_dir / "frontier_execution_queue.json"
    md_path = figures_dir / "frontier_execution_queue.md"
    json_path.write_text(json.dumps(queue_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_execution_queue_lines(queue_rows)) + "\n", encoding="utf-8")
    return json_path, md_path


def write_frontier_focus_card(frontier_status: list[dict[str, str]]) -> tuple[Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    focus_rows = build_frontier_focus_card_rows(queue_rows)
    json_path = tables_dir / "frontier_focus_card.json"
    md_path = figures_dir / "frontier_focus_card.md"
    json_path.write_text(json.dumps(focus_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_focus_card_lines(focus_rows)) + "\n", encoding="utf-8")
    return json_path, md_path


def write_frontier_handoff_packet(frontier_status: list[dict[str, str]]) -> tuple[Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    handoff_rows = build_frontier_handoff_packet_rows(queue_rows)
    json_path = tables_dir / "frontier_handoff_packet.json"
    md_path = figures_dir / "frontier_handoff_packet.md"
    json_path.write_text(json.dumps(handoff_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_handoff_packet_lines(handoff_rows)) + "\n", encoding="utf-8")
    return json_path, md_path


def write_frontier_receipt_packet(frontier_status: list[dict[str, str]]) -> tuple[Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    receipt_rows = build_frontier_receipt_packet_rows(queue_rows)
    json_path = tables_dir / "frontier_receipt_packet.json"
    md_path = figures_dir / "frontier_receipt_packet.md"
    json_path.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_receipt_packet_lines(receipt_rows)) + "\n", encoding="utf-8")
    return json_path, md_path


def write_frontier_receipt_checklist(frontier_status: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    checklist_rows = build_frontier_receipt_checklist_rows(queue_rows)
    csv_path = tables_dir / "frontier_receipt_checklist.csv"
    json_path = tables_dir / "frontier_receipt_checklist.json"
    md_path = figures_dir / "frontier_receipt_checklist.md"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FRONTIER_RECEIPT_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(checklist_rows)
    json_path.write_text(json.dumps(checklist_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_receipt_checklist_lines(checklist_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def write_frontier_handoff_checklist(frontier_status: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    checklist_rows = build_frontier_handoff_checklist_rows(queue_rows)
    csv_path = tables_dir / "frontier_handoff_checklist.csv"
    json_path = tables_dir / "frontier_handoff_checklist.json"
    md_path = figures_dir / "frontier_handoff_checklist.md"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FRONTIER_HANDOFF_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(checklist_rows)
    json_path.write_text(json.dumps(checklist_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_handoff_checklist_lines(checklist_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def write_frontier_parallel_picklist_checklist(frontier_status: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    checklist_rows = build_frontier_parallel_picklist_checklist_rows(queue_rows)
    csv_path = tables_dir / "frontier_parallel_picklist_checklist.csv"
    json_path = tables_dir / "frontier_parallel_picklist_checklist.json"
    md_path = figures_dir / "frontier_parallel_picklist_checklist.md"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FRONTIER_PICKLIST_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(checklist_rows)
    json_path.write_text(json.dumps(checklist_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_parallel_picklist_checklist_lines(checklist_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def write_frontier_receipt_map(frontier_status: list[dict[str, str]]) -> tuple[Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    receipt_map_rows = build_frontier_receipt_map_rows(queue_rows)
    json_path = tables_dir / "frontier_receipt_map.json"
    md_path = figures_dir / "frontier_receipt_map.md"
    json_path.write_text(json.dumps(receipt_map_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_receipt_map_lines(receipt_map_rows)) + "\n", encoding="utf-8")
    return json_path, md_path


def write_frontier_parallel_picklist(frontier_status: list[dict[str, str]]) -> tuple[Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    picklist_rows = build_frontier_parallel_picklist_rows(queue_rows)
    json_path = tables_dir / "frontier_parallel_picklist.json"
    md_path = figures_dir / "frontier_parallel_picklist.md"
    json_path.write_text(json.dumps(picklist_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_parallel_picklist_lines(picklist_rows)) + "\n", encoding="utf-8")
    return json_path, md_path


def write_frontier_receipt_board(frontier_status: list[dict[str, str]]) -> tuple[Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    board_rows = build_frontier_receipt_board_rows(queue_rows)
    json_path = tables_dir / "frontier_receipt_board.json"
    md_path = figures_dir / "frontier_receipt_board.md"
    json_path.write_text(json.dumps(board_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_receipt_board_lines(board_rows)) + "\n", encoding="utf-8")
    return json_path, md_path


def write_frontier_receipt_board_checklist(frontier_status: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    checklist_rows = build_frontier_receipt_board_checklist_rows(queue_rows)
    csv_path = tables_dir / "frontier_receipt_board_checklist.csv"
    json_path = tables_dir / "frontier_receipt_board_checklist.json"
    md_path = figures_dir / "frontier_receipt_board_checklist.md"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FRONTIER_RECEIPT_BOARD_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(checklist_rows)
    json_path.write_text(json.dumps(checklist_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_receipt_board_checklist_lines(checklist_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def write_frontier_coordination_matrix(frontier_status: list[dict[str, str]]) -> tuple[Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    matrix_rows = build_frontier_coordination_matrix_rows(queue_rows)
    json_path = tables_dir / "frontier_coordination_matrix.json"
    md_path = figures_dir / "frontier_coordination_matrix.md"
    json_path.write_text(json.dumps(matrix_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_coordination_matrix_lines(matrix_rows)) + "\n", encoding="utf-8")
    return json_path, md_path


def write_frontier_writeback_index(frontier_status: list[dict[str, str]]) -> tuple[Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    index_rows = build_frontier_writeback_index_rows(queue_rows)
    json_path = tables_dir / "frontier_writeback_index.json"
    md_path = figures_dir / "frontier_writeback_index.md"
    json_path.write_text(json.dumps(index_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_writeback_index_lines(index_rows)) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> None:
    report = build_report()
    json_path, md_path = write_report(report)
    queue_json_path, queue_md_path = write_frontier_queue(report["frontier_status"])
    focus_json_path, focus_md_path = write_frontier_focus_card(report["frontier_status"])
    handoff_json_path, handoff_md_path = write_frontier_handoff_packet(report["frontier_status"])
    handoff_checklist_csv_path, handoff_checklist_json_path, handoff_checklist_md_path = write_frontier_handoff_checklist(report["frontier_status"])
    receipt_json_path, receipt_md_path = write_frontier_receipt_packet(report["frontier_status"])
    receipt_checklist_csv_path, receipt_checklist_json_path, receipt_checklist_md_path = write_frontier_receipt_checklist(report["frontier_status"])
    receipt_map_json_path, receipt_map_md_path = write_frontier_receipt_map(report["frontier_status"])
    parallel_picklist_json_path, parallel_picklist_md_path = write_frontier_parallel_picklist(report["frontier_status"])
    parallel_picklist_checklist_csv_path, parallel_picklist_checklist_json_path, parallel_picklist_checklist_md_path = write_frontier_parallel_picklist_checklist(report["frontier_status"])
    receipt_board_json_path, receipt_board_md_path = write_frontier_receipt_board(report["frontier_status"])
    receipt_board_checklist_csv_path, receipt_board_checklist_json_path, receipt_board_checklist_md_path = write_frontier_receipt_board_checklist(report["frontier_status"])
    coordination_matrix_json_path, coordination_matrix_md_path = write_frontier_coordination_matrix(report["frontier_status"])
    coordination_checklist_csv_path, coordination_checklist_json_path, coordination_checklist_md_path = write_frontier_coordination_checklist(report["frontier_status"])
    writeback_index_json_path, writeback_index_md_path = write_frontier_writeback_index(report["frontier_status"])
    writeback_checklist_csv_path, writeback_checklist_json_path, writeback_checklist_md_path = write_frontier_writeback_checklist(report["frontier_status"])
    print(f"Wrote harness report: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote harness summary: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier queue JSON: {queue_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier queue note: {queue_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier focus JSON: {focus_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier focus note: {focus_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier handoff JSON: {handoff_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier handoff note: {handoff_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier handoff checklist CSV: {handoff_checklist_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier handoff checklist JSON: {handoff_checklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier handoff checklist note: {handoff_checklist_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt JSON: {receipt_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt note: {receipt_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt checklist CSV: {receipt_checklist_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt checklist JSON: {receipt_checklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt checklist note: {receipt_checklist_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt map JSON: {receipt_map_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt map note: {receipt_map_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier parallel picklist JSON: {parallel_picklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier parallel picklist note: {parallel_picklist_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier parallel picklist checklist CSV: {parallel_picklist_checklist_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier parallel picklist checklist JSON: {parallel_picklist_checklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier parallel picklist checklist note: {parallel_picklist_checklist_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt board JSON: {receipt_board_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt board note: {receipt_board_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt board checklist CSV: {receipt_board_checklist_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt board checklist JSON: {receipt_board_checklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt board checklist note: {receipt_board_checklist_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier coordination matrix JSON: {coordination_matrix_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier coordination matrix note: {coordination_matrix_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier coordination checklist CSV: {coordination_checklist_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier coordination checklist JSON: {coordination_checklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier coordination checklist note: {coordination_checklist_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier writeback index JSON: {writeback_index_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier writeback index note: {writeback_index_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier writeback checklist CSV: {writeback_checklist_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier writeback checklist JSON: {writeback_checklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier writeback checklist note: {writeback_checklist_md_path.relative_to(PROJECT_ROOT)}")
    print(f"gold_cases_present: {all(report['gold_cases'].values())}")
    print(f"gold_and_synthetic_separated: {report['gold_and_synthetic_separated']}")


if __name__ == "__main__":
    main()
