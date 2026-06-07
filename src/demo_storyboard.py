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

BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "step_id",
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
) -> tuple[Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    json_path = tables_dir / "demo_storyboard_cards.json"
    md_path = figures_dir / "demo_storyboard.md"
    walkthrough_json_path = tables_dir / "demo_walkthrough_steps.json"
    walkthrough_md_path = figures_dir / "demo_walkthrough.md"
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
