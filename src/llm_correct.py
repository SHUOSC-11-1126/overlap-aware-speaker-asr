from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT


CSV_COLUMNS = [
    "case_id",
    "label",
    "risk_explanation",
    "candidate_repair",
    "uncertainty_note",
]

QUEUE_COLUMNS = [
    "queue_order",
    "case_id",
    "label",
    "review_priority",
    "why_now",
    "candidate_repair",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "review_scope",
    "expected_inputs",
    "expected_outputs",
    "writeback_note",
]

BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "case_id",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]

CHECKLIST_COLUMNS = [
    "checklist_order",
    "case_id",
    "review_priority",
    "checklist_goal",
    "expected_evidence",
    "preflight_step",
    "next_gate",
]


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return [row for row in csv.DictReader(f) if isinstance(row, dict)]


def build_critic_rows(
    risk_rows: list[dict[str, Any]],
    profile_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    profile_by_case = {str(row.get("case_id", "")): row for row in profile_rows}
    rows: list[dict[str, Any]] = []
    for risk_row in risk_rows:
        case_id = str(risk_row.get("case_id", ""))
        profile_row = profile_by_case.get(case_id, {})
        risk_flags = str(risk_row.get("risk_flags", ""))
        risk_level = str(risk_row.get("risk_level", ""))
        recommended_action = str(risk_row.get("recommended_action", ""))
        best_alignment = str(profile_row.get("best_profile_alignment", ""))
        uncertainty_note = (
            f"Profile alignment still prefers {best_alignment}, so attribution remains uncertain."
            if best_alignment
            else "No profile alignment signal is available, so attribution remains uncertain."
        )
        if risk_flags.strip():
            risk_explanation = f"{risk_flags} suggest unstable separated output and should be treated as a qualitative warning."
        else:
            risk_descriptor = risk_level if risk_level.strip() else "unknown"
            risk_explanation = (
                f"The selector reports a {risk_descriptor} risk state even without explicit flags, so the current transcript still deserves critic review."
            )
        rows.append(
            {
                "case_id": case_id,
                "label": "qualitative/demo",
                "risk_explanation": risk_explanation,
                "candidate_repair": f"Try {recommended_action} before treating the current transcript as final.",
                "uncertainty_note": uncertainty_note,
            }
        )
    return rows


def build_critic_note_lines(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "# LLM Critic Qualitative Note",
        "",
        "This generated note is qualitative only. It uses structured heuristics to imitate a transcript critic and does not claim verified transcript repair.",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## {row['case_id']}",
                "",
                f"- Label: `{row['label']}`",
                f"- Risk explanation: {row['risk_explanation']}",
                f"- Candidate repair: {row['candidate_repair']}",
                f"- Uncertainty note: {row['uncertainty_note']}",
                "",
            ]
        )
    return lines


def build_critic_review_queue_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prioritized: list[dict[str, Any]] = []
    for row in rows:
        risk_explanation = str(row.get("risk_explanation", ""))
        uncertainty_note = str(row.get("uncertainty_note", ""))
        has_swapped_signal = "swapped" in uncertainty_note.lower()
        has_explicit_flags = "risk" in risk_explanation.lower()
        if has_swapped_signal and has_explicit_flags:
            review_priority = "high"
            priority_rank = 0
            why_now = "Risk flags plus swapped-profile uncertainty make this the strongest first review target."
        elif has_explicit_flags:
            review_priority = "medium"
            priority_rank = 1
            why_now = "Explicit risk flags suggest the critic should review this soon even without a strong swap signal."
        else:
            review_priority = "medium"
            priority_rank = 2
            why_now = "The selector still reports review-worthy uncertainty, so this stays in the queue after the strongest flagged case."
        prioritized.append(
            {
                "case_id": str(row.get("case_id", "")),
                "label": str(row.get("label", "qualitative/demo")),
                "review_priority": review_priority,
                "why_now": why_now,
                "candidate_repair": str(row.get("candidate_repair", "")),
                "_priority_rank": priority_rank,
            }
        )
    prioritized.sort(key=lambda row: (int(row["_priority_rank"]), str(row["case_id"])))
    queue_rows: list[dict[str, Any]] = []
    for index, row in enumerate(prioritized, start=1):
        queue_rows.append(
            {
                "queue_order": str(index),
                "case_id": str(row["case_id"]),
                "label": str(row["label"]),
                "review_priority": str(row["review_priority"]),
                "why_now": str(row["why_now"]),
                "candidate_repair": str(row["candidate_repair"]),
            }
        )
    return queue_rows


def build_critic_review_queue_lines(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "# LLM Critic Review Queue",
        "",
        "This generated queue is qualitative only. It suggests which cases should receive the next critic-style review pass first.",
        "",
        "| queue_order | case_id | label | review_priority | why_now | candidate_repair |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['queue_order']} | {row['case_id']} | {row['label']} | {row['review_priority']} | {row['why_now']} | {row['candidate_repair']} |"
        )
    return lines


def build_critic_review_receipt_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []

    head = rows[0]
    return [
        {
            "execution_status": "template_only",
            "review_scope": str(head.get("case_id", "")),
            "expected_inputs": "Critic review queue head plus one qualitative review note stub.",
            "expected_outputs": "Diagnostic critic-pass note and a narrow review writeback.",
            "writeback_note": "No critic-style review pass has been executed yet; fill this receipt only after the first review.",
        }
    ]


def build_critic_review_receipt_lines(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "# LLM Critic Review Receipt",
        "",
        "This generated receipt is a template-only writeback target for the first critic-style review pass. It does not claim verified transcript repair.",
        "",
        "| execution_status | review_scope | expected_inputs | expected_outputs | writeback_note |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution_status']} | {row['review_scope']} | {row['expected_inputs']} | {row['expected_outputs']} | {row['writeback_note']} |"
        )
    return lines


def build_critic_review_bridge_checklist_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []

    head = rows[0]
    case_id = str(head.get("case_id", ""))
    review_priority = str(head.get("review_priority", "medium"))
    return [
        {
            "checklist_order": "1",
            "case_id": case_id,
            "prerequisite_artifact": "results/figures/llm_critic_review_queue.md",
            "receipt_target": "results/figures/llm_critic_review_receipt.md",
            "checklist_goal": f"Verify the critic review bridge for {case_id} before any repair claim is advanced.",
            "bridge_note": f"Open the review queue first, then write back through the receipt target for the {review_priority} review pass.",
            "next_gate": "Confirm this bridge before opening the review receipt target.",
        }
    ]


def build_critic_review_bridge_checklist_lines(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "# LLM Critic Review Bridge Checklist",
        "",
        "This generated checklist turns the review queue into a row-by-row bridge verification path. It remains qualitative only and does not claim repaired transcripts.",
        "",
        "| checklist_order | case_id | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['case_id']} | {row['prerequisite_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | {row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def build_critic_review_checklist_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []

    head = rows[0]
    review_priority = str(head.get("review_priority", "medium"))
    case_id = str(head.get("case_id", ""))
    checklist_goal = str(head.get("candidate_repair", ""))
    preflight_step = (
        "Confirm the strongest risk flags before drafting the first critic-style repair note."
        if review_priority == "high"
        else "Confirm the current qualitative warning before drafting the first critic-style repair note."
    )
    next_gate = (
        "Fill one critic review receipt before promoting any repair claim."
        if case_id
        else "Keep the queue ordered before promoting any repair claim."
    )
    return [
        {
            "checklist_order": "1",
            "case_id": case_id,
            "review_priority": review_priority,
            "checklist_goal": checklist_goal,
            "expected_evidence": "results/tables/llm_critic_review_receipt.json",
            "preflight_step": preflight_step,
            "next_gate": next_gate,
        }
    ]


def build_critic_review_checklist_lines(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "# LLM Critic Review Checklist",
        "",
        "This generated checklist turns the critic queue into an ordered execution path. It remains qualitative only and does not claim repaired transcripts.",
        "",
        "| checklist_order | case_id | review_priority | checklist_goal | expected_evidence | preflight_step | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['case_id']} | {row['review_priority']} | {row['checklist_goal']} | {row['expected_evidence']} | {row['preflight_step']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, Any]]) -> tuple[Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    csv_path = tables_dir / "llm_critic_qualitative_summary.csv"
    json_path = tables_dir / "llm_critic_qualitative_summary.json"
    md_path = figures_dir / "llm_critic_qualitative_note.md"
    queue_rows = build_critic_review_queue_rows(rows)
    queue_csv_path = tables_dir / "llm_critic_review_queue.csv"
    queue_json_path = tables_dir / "llm_critic_review_queue.json"
    queue_md_path = figures_dir / "llm_critic_review_queue.md"
    receipt_rows = build_critic_review_receipt_rows(queue_rows)
    receipt_json_path = tables_dir / "llm_critic_review_receipt.json"
    receipt_md_path = figures_dir / "llm_critic_review_receipt.md"
    bridge_checklist_rows = build_critic_review_bridge_checklist_rows(queue_rows)
    bridge_checklist_csv_path = tables_dir / "llm_critic_review_bridge_checklist.csv"
    bridge_checklist_json_path = tables_dir / "llm_critic_review_bridge_checklist.json"
    bridge_checklist_md_path = figures_dir / "llm_critic_review_bridge_checklist.md"
    checklist_rows = build_critic_review_checklist_rows(queue_rows)
    checklist_csv_path = tables_dir / "llm_critic_review_checklist.csv"
    checklist_json_path = tables_dir / "llm_critic_review_checklist.json"
    checklist_md_path = figures_dir / "llm_critic_review_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_critic_note_lines(rows)) + "\n", encoding="utf-8")
    with queue_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=QUEUE_COLUMNS)
        writer.writeheader()
        writer.writerows(queue_rows)
    queue_json_path.write_text(json.dumps(queue_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    queue_md_path.write_text("\n".join(build_critic_review_queue_lines(queue_rows)) + "\n", encoding="utf-8")
    receipt_json_path.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_md_path.write_text("\n".join(build_critic_review_receipt_lines(receipt_rows)) + "\n", encoding="utf-8")
    with bridge_checklist_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(bridge_checklist_rows)
    bridge_checklist_json_path.write_text(json.dumps(bridge_checklist_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    bridge_checklist_md_path.write_text(
        "\n".join(build_critic_review_bridge_checklist_lines(bridge_checklist_rows)) + "\n",
        encoding="utf-8",
    )
    with checklist_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(checklist_rows)
    checklist_json_path.write_text(json.dumps(checklist_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    checklist_md_path.write_text("\n".join(build_critic_review_checklist_lines(checklist_rows)) + "\n", encoding="utf-8")
    return (
        csv_path,
        json_path,
        md_path,
        queue_csv_path,
        queue_json_path,
        queue_md_path,
        receipt_json_path,
        receipt_md_path,
        bridge_checklist_csv_path,
        bridge_checklist_json_path,
        bridge_checklist_md_path,
        checklist_csv_path,
        checklist_json_path,
        checklist_md_path,
    )


def main() -> None:
    risk_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "risk_aware_selection.csv")
    profile_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "speaker_profile_similarity.csv")
    rows = build_critic_rows(risk_rows, profile_rows)
    (
        csv_path,
        json_path,
        md_path,
        queue_csv_path,
        queue_json_path,
        queue_md_path,
        receipt_json_path,
        receipt_md_path,
        bridge_checklist_csv_path,
        bridge_checklist_json_path,
        bridge_checklist_md_path,
        checklist_csv_path,
        checklist_json_path,
        checklist_md_path,
    ) = write_outputs(rows)
    print(f"Wrote LLM critic summary: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic note: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic queue: {queue_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic queue JSON: {queue_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic queue note: {queue_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic receipt JSON: {receipt_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic receipt note: {receipt_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic bridge checklist CSV: {bridge_checklist_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic bridge checklist JSON: {bridge_checklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic bridge checklist note: {bridge_checklist_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic checklist CSV: {checklist_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic checklist JSON: {checklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic checklist note: {checklist_md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
