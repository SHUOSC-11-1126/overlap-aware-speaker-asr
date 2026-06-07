from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT


CHECKLIST_COLUMNS = [
    "checklist_order",
    "step_id",
    "focus",
    "artifact_anchor",
    "checklist_goal",
    "expected_evidence",
    "preflight_step",
    "next_gate",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "storyboard_scope",
    "expected_inputs",
    "expected_outputs",
    "writeback_note",
]

RECEIPT_CHECKLIST_COLUMNS = [
    "checklist_order",
    "storyboard_scope",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "preflight_step",
    "next_gate",
]

RECEIPT_BOARD_COLUMNS = [
    "board_order",
    "storyboard_scope",
    "receipt_state",
    "prerequisite_artifact",
    "receipt_target",
    "board_note",
    "next_gate",
]

BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "step_id",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]

STORYBOARD_BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "story_card",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]

STORYBOARD_RECEIPT_BRIDGE_COLUMNS = [
    "checklist_order",
    "story_card",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def build_demo_walkthrough_receipt_rows(steps: list[dict[str, str]]) -> list[dict[str, str]]:
    if not steps:
        return []

    head = steps[0]
    step_id = str(head.get("step_id", ""))
    focus = str(head.get("focus", "")).strip().lower().replace(" ", "_")
    return [
        {
            "execution_status": "template_only",
            "walkthrough_scope": f"step_{step_id}_{focus}",
            "expected_inputs": "Demo walkthrough head plus one narration note stub.",
            "expected_outputs": "Diagnostic walkthrough note and a narrow presentation writeback.",
            "writeback_note": "No demo walkthrough pass has been executed yet; fill this receipt only after the first run.",
        }
    ]


def build_demo_walkthrough_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Demo Walkthrough Receipt",
        "",
        "This generated receipt is a template-only writeback target for the first demo walkthrough pass. It does not claim a completed live demo or recording.",
        "",
        "| execution_status | walkthrough_scope | expected_inputs | expected_outputs | writeback_note |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution_status']} | {row['walkthrough_scope']} | {row['expected_inputs']} | {row['expected_outputs']} | {row['writeback_note']} |"
        )
    return lines


def build_demo_storyboard_receipt_rows(cards: list[dict[str, str]]) -> list[dict[str, str]]:
    if not cards:
        return []

    head = cards[0]
    return [
        {
            "execution_status": "template_only",
            "storyboard_scope": str(head.get("title", "one_page_demo_storyboard")).strip().lower().replace(" ", "_"),
            "expected_inputs": "Demo storyboard cards plus one review note stub.",
            "expected_outputs": "Narrow storyboard review note and a demo narrative writeback.",
            "writeback_note": "No storyboard review pass has been executed yet; fill this receipt only after the first review.",
        }
    ]


def build_demo_storyboard_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Demo Storyboard Receipt",
        "",
        "This generated receipt is a template-only writeback target for the first demo storyboard review pass. It does not claim a completed live demo or recording.",
        "",
        "| execution_status | storyboard_scope | expected_inputs | expected_outputs | writeback_note |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution_status']} | {row['storyboard_scope']} | {row['expected_inputs']} | {row['expected_outputs']} | {row['writeback_note']} |"
        )
    return lines


def build_demo_storyboard_receipt_checklist_rows(receipt_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not receipt_rows:
        return []

    receipt = receipt_rows[0]
    storyboard_scope = str(receipt.get("storyboard_scope", ""))
    return [
        {
            "checklist_order": "1",
            "storyboard_scope": storyboard_scope,
            "prerequisite_artifact": "results/figures/demo_storyboard.md",
            "receipt_target": "results/figures/demo_storyboard_receipt.md",
            "checklist_goal": f"Verify the storyboard receipt path for {storyboard_scope} before any review writeback is advanced.",
            "preflight_step": "Open the storyboard cards and confirm the first review note stub before filling the receipt.",
            "next_gate": "Fill the storyboard receipt before promoting any demo-review claim.",
        }
    ]


def build_demo_storyboard_receipt_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Demo Storyboard Receipt Checklist",
        "",
        "This generated checklist turns the storyboard receipt into an ordered verification path. It remains demo support only and does not claim that any live demo or recording has been completed.",
        "",
        "| checklist_order | storyboard_scope | prerequisite_artifact | receipt_target | checklist_goal | preflight_step | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['storyboard_scope']} | {row['prerequisite_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | {row['preflight_step']} | {row['next_gate']} |"
        )
    return lines


def build_demo_storyboard_receipt_board_rows(
    receipt_rows: list[dict[str, str]],
    receipt_checklist_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    if not receipt_rows:
        return []

    receipt = receipt_rows[0]
    checklist = receipt_checklist_rows[0] if receipt_checklist_rows else {}
    storyboard_scope = str(receipt.get("storyboard_scope", ""))
    return [
        {
            "board_order": "1",
            "storyboard_scope": storyboard_scope,
            "receipt_state": str(receipt.get("execution_status", "template_only")),
            "prerequisite_artifact": str(checklist.get("prerequisite_artifact", "results/figures/demo_storyboard.md")),
            "receipt_target": str(checklist.get("receipt_target", "results/figures/demo_storyboard_receipt.md")),
            "board_note": f"Keep the storyboard receipt path visible for {storyboard_scope} while the receipt remains template-only.",
            "next_gate": "Open the receipt checklist before filling the receipt writeback.",
        }
    ]


def build_demo_storyboard_receipt_board_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Demo Storyboard Receipt Board",
        "",
        "This generated board condenses the storyboard receipt path into a single coordination snapshot. It remains demo support only and does not claim that any live demo or recording has been completed.",
        "",
        "| board_order | storyboard_scope | receipt_state | prerequisite_artifact | receipt_target | board_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['board_order']} | {row['storyboard_scope']} | {row['receipt_state']} | {row['prerequisite_artifact']} | {row['receipt_target']} | {row['board_note']} | {row['next_gate']} |"
        )
    return lines


def build_demo_storyboard_receipt_bridge_rows(
    cards: list[dict[str, str]],
    receipt_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    if not cards or not receipt_rows:
        return []

    head = cards[0]
    receipt = receipt_rows[0]
    return [
        {
            "checklist_order": "1",
            "story_card": str(head.get("title", "")),
            "prerequisite_artifact": "results/figures/demo_storyboard.md",
            "receipt_target": "results/figures/demo_storyboard_receipt.md",
            "checklist_goal": f"Verify the storyboard-to-receipt bridge for the {str(head.get('title', 'story'))} card before any review writeback is advanced.",
            "bridge_note": f"Open the storyboard first, then write back through the receipt target for {str(receipt.get('storyboard_scope', 'storyboard_review')).lower()}.",
            "next_gate": "Confirm this bridge before opening the storyboard receipt target.",
        }
    ]


def build_demo_storyboard_receipt_bridge_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Demo Storyboard Receipt Bridge",
        "",
        "This generated bridge links the storyboard cards to the storyboard receipt. It remains demo support only and does not claim that any live demo or recording has been completed.",
        "",
        "| checklist_order | story_card | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['story_card']} | {row['prerequisite_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | {row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def build_demo_walkthrough_bridge_checklist_rows(
    steps: list[dict[str, str]],
    receipt_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    if not steps or not receipt_rows:
        return []

    head = steps[0]
    receipt = receipt_rows[0]
    step_id = str(head.get("step_id", ""))
    focus = str(head.get("focus", ""))
    walkthrough_scope = str(receipt.get("walkthrough_scope", ""))
    return [
        {
            "checklist_order": "1",
            "step_id": step_id,
            "prerequisite_artifact": "results/figures/demo_walkthrough.md",
            "receipt_target": "results/figures/demo_walkthrough_receipt.md",
            "checklist_goal": f"Verify the demo walkthrough bridge for step {step_id} before any presentation claim is advanced.",
            "bridge_note": f"Open the walkthrough first, then write back through the receipt target for {walkthrough_scope} and the {focus} focus.",
            "next_gate": "Confirm this bridge before opening the walkthrough receipt target.",
        }
    ]


def build_demo_walkthrough_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Demo Walkthrough Bridge Checklist",
        "",
        "This generated checklist turns the walkthrough into a row-by-row bridge verification path. It remains presentation support only and does not claim a completed live demo or recording.",
        "",
        "| checklist_order | step_id | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['step_id']} | {row['prerequisite_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | {row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def build_demo_storyboard_cards(summary: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "title": "Problem",
            "body": "Overlap-aware ASR should separate selectively instead of assuming separation always helps.",
        },
        {
            "title": "Pipeline",
            "body": "Mixed ASR, separated ASR, duplicate suppression, adaptive routing, and speaker-aware evaluation form the main decision loop.",
        },
        {
            "title": "Findings",
            "body": f"{summary.get('baseline', '')} {summary.get('cascade', '')}".strip(),
        },
        {
            "title": "Frontier",
            "body": summary.get("frontier", ""),
        },
    ]


def build_demo_storyboard_lines(cards: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Demo Storyboard",
        "",
        "This generated storyboard is a demo-facing summary of the repository's core story and current frontier extensions.",
        "",
        "```mermaid",
        'flowchart LR',
        '    A["Mixed / Separated Audio"] --> B["ASR Paths"]',
        '    B --> C["Router + Risk Selector"]',
        '    C --> D["Speaker-aware / cpCER-lite Evaluation"]',
        '    D --> E["Frontier Extensions"]',
        "```",
        "",
    ]
    for card in cards:
        lines.extend(
            [
                f"## {card['title']}",
                "",
                card["body"],
                "",
            ]
        )
    return lines


def build_demo_storyboard_bridge_checklist_rows(
    cards: list[dict[str, str]],
    steps: list[dict[str, str]],
) -> list[dict[str, str]]:
    if not cards or not steps:
        return []

    head_card = cards[0]
    head_step = steps[0]
    return [
        {
            "checklist_order": "1",
            "story_card": str(head_card.get("title", "")),
            "prerequisite_artifact": "results/figures/demo_storyboard.md",
            "receipt_target": "results/figures/demo_walkthrough.md",
            "checklist_goal": f"Verify the storyboard bridge before the {str(head_step.get('step_id', ''))} walkthrough step is advanced.",
            "bridge_note": f"Use the {str(head_card.get('title', 'story'))} card to justify opening the {str(head_step.get('focus', '')).lower()} walkthrough step.",
            "next_gate": "Confirm this bridge before opening the walkthrough artifact.",
        }
    ]


def build_demo_storyboard_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Demo Storyboard Bridge Checklist",
        "",
        "This generated checklist turns the storyboard into a row-by-row bridge verification path. It remains demo support only and does not claim a completed live demo or recording.",
        "",
        "| checklist_order | story_card | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['story_card']} | {row['prerequisite_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | {row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def build_demo_walkthrough_steps(summary: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "step_id": "1",
            "focus": "Problem framing",
            "talk_track": "Start with the core question: overlap exists, but separation should be selective rather than automatic.",
            "artifact_anchor": "README.md",
        },
        {
            "step_id": "2",
            "focus": "Baseline evidence",
            "talk_track": summary.get("baseline", ""),
            "artifact_anchor": "REPORT.md",
        },
        {
            "step_id": "3",
            "focus": "Routing takeaway",
            "talk_track": summary.get("router", ""),
            "artifact_anchor": "results/figures/compute_aware_cascade_summary.md",
        },
        {
            "step_id": "4",
            "focus": "Frontier breadth",
            "talk_track": summary.get("frontier", ""),
            "artifact_anchor": "results/figures/project_harness_report.md",
        },
        {
            "step_id": "5",
            "focus": "Next-step framing",
            "talk_track": "Close by showing that the next work is structured: benchmark handoff, external prioritization, and qualitative repair paths are already staged.",
            "artifact_anchor": "docs/roadmap.md",
        },
    ]


def build_demo_walkthrough_lines(steps: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Demo Walkthrough",
        "",
        "This generated walkthrough suggests a short demo sequence for explaining the repository to a new viewer.",
        "",
        "| step_id | focus | talk_track | artifact_anchor |",
        "| --- | --- | --- | --- |",
    ]
    for step in steps:
        lines.append(
            f"| {step['step_id']} | {step['focus']} | {step['talk_track']} | {step['artifact_anchor']} |"
        )
    return lines


def build_demo_walkthrough_checklist_rows(steps: list[dict[str, str]]) -> list[dict[str, str]]:
    checklist_rows: list[dict[str, str]] = []
    for index, step in enumerate(steps, start=1):
        focus = str(step.get("focus", ""))
        artifact_anchor = str(step.get("artifact_anchor", ""))
        checklist_rows.append(
            {
                "checklist_order": str(index),
                "step_id": str(step.get("step_id", "")),
                "focus": focus,
                "artifact_anchor": artifact_anchor,
                "checklist_goal": str(step.get("talk_track", "")),
                "expected_evidence": "results/tables/demo_walkthrough_receipt.json",
                "preflight_step": f"Open {artifact_anchor} before presenting the {focus.lower()} step.",
                "next_gate": "Fill the walkthrough receipt after the first presentation run.",
            }
        )
    return checklist_rows


def build_demo_walkthrough_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Demo Walkthrough Checklist",
        "",
        "This generated checklist orders the demo walkthrough into a presentation-ready execution path. It remains a coordination artifact and does not claim a completed live demo or recording.",
        "",
        "| checklist_order | step_id | focus | artifact_anchor | checklist_goal | expected_evidence | preflight_step | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['step_id']} | {row['focus']} | {row['artifact_anchor']} | {row['checklist_goal']} | {row['expected_evidence']} | {row['preflight_step']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(
    cards: list[dict[str, str]],
    steps: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    json_path = tables_dir / "demo_storyboard_cards.json"
    md_path = figures_dir / "demo_storyboard.md"
    storyboard_receipt_rows = build_demo_storyboard_receipt_rows(cards)
    storyboard_receipt_json_path = tables_dir / "demo_storyboard_receipt.json"
    storyboard_receipt_md_path = figures_dir / "demo_storyboard_receipt.md"
    storyboard_receipt_bridge_rows = build_demo_storyboard_receipt_bridge_rows(cards, storyboard_receipt_rows)
    storyboard_receipt_bridge_csv_path = tables_dir / "demo_storyboard_receipt_bridge.csv"
    storyboard_receipt_bridge_json_path = tables_dir / "demo_storyboard_receipt_bridge.json"
    storyboard_receipt_bridge_md_path = figures_dir / "demo_storyboard_receipt_bridge.md"
    storyboard_receipt_checklist_rows = build_demo_storyboard_receipt_checklist_rows(storyboard_receipt_rows)
    storyboard_receipt_checklist_csv_path = tables_dir / "demo_storyboard_receipt_checklist.csv"
    storyboard_receipt_checklist_json_path = tables_dir / "demo_storyboard_receipt_checklist.json"
    storyboard_receipt_checklist_md_path = figures_dir / "demo_storyboard_receipt_checklist.md"
    storyboard_receipt_board_rows = build_demo_storyboard_receipt_board_rows(
        storyboard_receipt_rows,
        storyboard_receipt_checklist_rows,
    )
    storyboard_receipt_board_csv_path = tables_dir / "demo_storyboard_receipt_board.csv"
    storyboard_receipt_board_json_path = tables_dir / "demo_storyboard_receipt_board.json"
    storyboard_receipt_board_md_path = figures_dir / "demo_storyboard_receipt_board.md"
    walkthrough_json_path = tables_dir / "demo_walkthrough_steps.json"
    walkthrough_md_path = figures_dir / "demo_walkthrough.md"
    storyboard_bridge_checklist_rows = build_demo_storyboard_bridge_checklist_rows(cards, steps)
    storyboard_bridge_checklist_csv_path = tables_dir / "demo_storyboard_bridge_checklist.csv"
    storyboard_bridge_checklist_json_path = tables_dir / "demo_storyboard_bridge_checklist.json"
    storyboard_bridge_checklist_md_path = figures_dir / "demo_storyboard_bridge_checklist.md"
    walkthrough_receipt_json_path = tables_dir / "demo_walkthrough_receipt.json"
    walkthrough_receipt_md_path = figures_dir / "demo_walkthrough_receipt.md"
    walkthrough_checklist_rows = build_demo_walkthrough_checklist_rows(steps)
    walkthrough_checklist_csv_path = tables_dir / "demo_walkthrough_checklist.csv"
    walkthrough_checklist_json_path = tables_dir / "demo_walkthrough_checklist.json"
    walkthrough_checklist_md_path = figures_dir / "demo_walkthrough_checklist.md"
    walkthrough_bridge_checklist_rows = build_demo_walkthrough_bridge_checklist_rows(
        steps,
        build_demo_walkthrough_receipt_rows(steps),
    )
    walkthrough_bridge_checklist_csv_path = tables_dir / "demo_walkthrough_bridge_checklist.csv"
    walkthrough_bridge_checklist_json_path = tables_dir / "demo_walkthrough_bridge_checklist.json"
    walkthrough_bridge_checklist_md_path = figures_dir / "demo_walkthrough_bridge_checklist.md"
    json_path.write_text(json.dumps(cards, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_demo_storyboard_lines(cards)) + "\n", encoding="utf-8")
    storyboard_receipt_json_path.write_text(json.dumps(storyboard_receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    storyboard_receipt_md_path.write_text(
        "\n".join(build_demo_storyboard_receipt_lines(storyboard_receipt_rows)) + "\n",
        encoding="utf-8",
    )
    with storyboard_receipt_bridge_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=STORYBOARD_RECEIPT_BRIDGE_COLUMNS)
        writer.writeheader()
        writer.writerows(storyboard_receipt_bridge_rows)
    storyboard_receipt_bridge_json_path.write_text(
        json.dumps(storyboard_receipt_bridge_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    storyboard_receipt_bridge_md_path.write_text(
        "\n".join(build_demo_storyboard_receipt_bridge_lines(storyboard_receipt_bridge_rows)) + "\n",
        encoding="utf-8",
    )
    with storyboard_receipt_checklist_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=RECEIPT_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(storyboard_receipt_checklist_rows)
    storyboard_receipt_checklist_json_path.write_text(
        json.dumps(storyboard_receipt_checklist_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    storyboard_receipt_checklist_md_path.write_text(
        "\n".join(build_demo_storyboard_receipt_checklist_lines(storyboard_receipt_checklist_rows)) + "\n",
        encoding="utf-8",
    )
    with storyboard_receipt_board_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=RECEIPT_BOARD_COLUMNS)
        writer.writeheader()
        writer.writerows(storyboard_receipt_board_rows)
    storyboard_receipt_board_json_path.write_text(
        json.dumps(storyboard_receipt_board_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    storyboard_receipt_board_md_path.write_text(
        "\n".join(build_demo_storyboard_receipt_board_lines(storyboard_receipt_board_rows)) + "\n",
        encoding="utf-8",
    )
    with storyboard_bridge_checklist_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=STORYBOARD_BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(storyboard_bridge_checklist_rows)
    storyboard_bridge_checklist_json_path.write_text(
        json.dumps(storyboard_bridge_checklist_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    storyboard_bridge_checklist_md_path.write_text(
        "\n".join(build_demo_storyboard_bridge_checklist_lines(storyboard_bridge_checklist_rows)) + "\n",
        encoding="utf-8",
    )
    walkthrough_json_path.write_text(json.dumps(steps, ensure_ascii=False, indent=2), encoding="utf-8")
    walkthrough_md_path.write_text("\n".join(build_demo_walkthrough_lines(steps)) + "\n", encoding="utf-8")
    walkthrough_receipt_rows = build_demo_walkthrough_receipt_rows(steps)
    walkthrough_receipt_json_path.write_text(json.dumps(walkthrough_receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    walkthrough_receipt_md_path.write_text(
        "\n".join(build_demo_walkthrough_receipt_lines(walkthrough_receipt_rows)) + "\n",
        encoding="utf-8",
    )
    with walkthrough_checklist_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(walkthrough_checklist_rows)
    walkthrough_checklist_json_path.write_text(json.dumps(walkthrough_checklist_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    walkthrough_checklist_md_path.write_text(
        "\n".join(build_demo_walkthrough_checklist_lines(walkthrough_checklist_rows)) + "\n",
        encoding="utf-8",
    )
    with walkthrough_bridge_checklist_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(walkthrough_bridge_checklist_rows)
    walkthrough_bridge_checklist_json_path.write_text(
        json.dumps(walkthrough_bridge_checklist_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    walkthrough_bridge_checklist_md_path.write_text(
        "\n".join(build_demo_walkthrough_bridge_checklist_lines(walkthrough_bridge_checklist_rows)) + "\n",
        encoding="utf-8",
    )
    return (
        json_path,
        md_path,
        storyboard_receipt_json_path,
        storyboard_receipt_md_path,
        storyboard_receipt_bridge_csv_path,
        storyboard_receipt_bridge_json_path,
        storyboard_receipt_bridge_md_path,
        storyboard_receipt_checklist_csv_path,
        storyboard_receipt_checklist_json_path,
        storyboard_receipt_checklist_md_path,
        storyboard_receipt_board_csv_path,
        storyboard_receipt_board_json_path,
        storyboard_receipt_board_md_path,
        storyboard_bridge_checklist_csv_path,
        storyboard_bridge_checklist_json_path,
        storyboard_bridge_checklist_md_path,
        walkthrough_json_path,
        walkthrough_md_path,
        walkthrough_receipt_json_path,
        walkthrough_receipt_md_path,
        walkthrough_checklist_csv_path,
        walkthrough_checklist_json_path,
        walkthrough_checklist_md_path,
        walkthrough_bridge_checklist_csv_path,
        walkthrough_bridge_checklist_json_path,
        walkthrough_bridge_checklist_md_path,
    )


def main() -> None:
    summary = {
        "baseline": "Selective separation beats blind separation in the current gold benchmark.",
        "cascade": "router_v2 is the balanced default, while cleaned separated output is the robust fallback.",
        "router": "router_v2 matches oracle-best average CER, and the compute-aware frontier turns that into deployment-facing tradeoff guidance.",
        "frontier": "Breadth-first artifacts now cover compute-aware cascade, MeetEval compatibility, speaker profile risk signaling, qualitative critics, and external prioritization.",
    }
    cards = build_demo_storyboard_cards(summary)
    steps = build_demo_walkthrough_steps(summary)
    (
        json_path,
        md_path,
        storyboard_receipt_json_path,
        storyboard_receipt_md_path,
        storyboard_receipt_bridge_csv_path,
        storyboard_receipt_bridge_json_path,
        storyboard_receipt_bridge_md_path,
        storyboard_receipt_checklist_csv_path,
        storyboard_receipt_checklist_json_path,
        storyboard_receipt_checklist_md_path,
        storyboard_receipt_board_csv_path,
        storyboard_receipt_board_json_path,
        storyboard_receipt_board_md_path,
        storyboard_bridge_checklist_csv_path,
        storyboard_bridge_checklist_json_path,
        storyboard_bridge_checklist_md_path,
        walkthrough_json_path,
        walkthrough_md_path,
        walkthrough_receipt_json_path,
        walkthrough_receipt_md_path,
        walkthrough_checklist_csv_path,
        walkthrough_checklist_json_path,
        walkthrough_checklist_md_path,
        walkthrough_bridge_checklist_csv_path,
        walkthrough_bridge_checklist_json_path,
        walkthrough_bridge_checklist_md_path,
    ) = write_outputs(cards, steps)
    print(f"Wrote demo storyboard cards: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo storyboard note: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo storyboard receipt JSON: {storyboard_receipt_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo storyboard receipt note: {storyboard_receipt_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo storyboard receipt bridge CSV: {storyboard_receipt_bridge_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo storyboard receipt bridge JSON: {storyboard_receipt_bridge_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo storyboard receipt bridge note: {storyboard_receipt_bridge_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo storyboard receipt checklist CSV: {storyboard_receipt_checklist_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo storyboard receipt checklist JSON: {storyboard_receipt_checklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo storyboard receipt checklist note: {storyboard_receipt_checklist_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo storyboard receipt board CSV: {storyboard_receipt_board_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo storyboard receipt board JSON: {storyboard_receipt_board_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo storyboard receipt board note: {storyboard_receipt_board_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo storyboard bridge checklist CSV: {storyboard_bridge_checklist_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo storyboard bridge checklist JSON: {storyboard_bridge_checklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo storyboard bridge checklist note: {storyboard_bridge_checklist_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo walkthrough steps: {walkthrough_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo walkthrough note: {walkthrough_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo walkthrough receipt JSON: {walkthrough_receipt_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo walkthrough receipt note: {walkthrough_receipt_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo walkthrough checklist CSV: {walkthrough_checklist_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo walkthrough checklist JSON: {walkthrough_checklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo walkthrough checklist note: {walkthrough_checklist_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo walkthrough bridge checklist CSV: {walkthrough_bridge_checklist_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo walkthrough bridge checklist JSON: {walkthrough_bridge_checklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo walkthrough bridge checklist note: {walkthrough_bridge_checklist_md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
