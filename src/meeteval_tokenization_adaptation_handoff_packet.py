from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


PACKET_COLUMNS = [
    "packet_order",
    "section_name",
    "artifact_path",
    "section_role",
    "packet_note",
]


PACKET_SECTIONS = [
    (
        "1",
        "tokenization_diagnostic",
        "results/figures/meeteval_cpwer_official_execution_tokenization_diagnostic.md",
        "Root-cause diagnostic for raw official cpWER drift under CJK text tokenization.",
    ),
    (
        "2",
        "character_level_official_execution",
        "results/figures/meeteval_cpwer_character_level_official_execution.md",
        "Character-spaced official cpWER execution used for bridge-lite comparable evidence.",
    ),
    (
        "3",
        "reconciliation_audit",
        "results/figures/meeteval_cpwer_official_execution_reconciliation_audit.md",
        "Reconciliation audit comparing character-spaced official cpWER against bridge-lite.",
    ),
    (
        "4",
        "tokenization_gain_scorecard",
        "results/figures/meeteval_cpwer_tokenization_gain_scorecard.md",
        "Per-case raw-to-character cpWER gain and preferred tokenization recommendation.",
    ),
    (
        "5",
        "tokenization_adaptation_completion_summary",
        "results/figures/meeteval_cpwer_tokenization_adaptation_completion_summary.md",
        "Queue-level completion summary for reconciled tokenization adaptation evidence.",
    ),
    (
        "6",
        "tokenization_adaptation_handoff",
        "results/figures/meeteval_tokenization_adaptation_handoff.md",
        "Handoff from reconciled tokenization adaptation evidence to frontier fill execution.",
    ),
    (
        "7",
        "tokenization_adaptation_handoff_bridge_checklist",
        "results/figures/meeteval_tokenization_adaptation_handoff_bridge_checklist.md",
        "Verify the tokenization handoff before opening the frontier fill evidence receipt.",
    ),
    (
        "8",
        "tokenization_adaptation_handoff_completion_summary",
        "results/figures/meeteval_tokenization_adaptation_handoff_completion_summary.md",
        "Completion rollup for the tokenization adaptation handoff path.",
    ),
]


def load_handoff_completion_summary() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "meeteval_tokenization_adaptation_handoff_completion_summary.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_packet_rows(summary: dict[str, str]) -> list[dict[str, str]]:
    handoff_status = str(summary.get("handoff_status", "tokenization_adaptation_handoff_pending"))
    aligned_count = str(summary.get("aligned_count", "0"))
    total_count = str(summary.get("total_count", "0"))
    queue_status = str(summary.get("queue_status", "queue_in_progress"))
    rows: list[dict[str, str]] = []
    for order, section_name, artifact_path, section_role in PACKET_SECTIONS:
        rows.append(
            {
                "packet_order": order,
                "section_name": section_name,
                "artifact_path": artifact_path,
                "section_role": section_role,
                "packet_note": (
                    f"MeetEval tokenization adaptation packet section while handoff_status={handoff_status}, "
                    f"aligned_count={aligned_count}, total_count={total_count}, queue_status={queue_status}; "
                    "this remains experimental/frontier coordination and does not claim full benchmark completion."
                ),
            }
        )
    return rows


def build_packet_lines(rows: list[dict[str, str]], summary: dict[str, str]) -> list[str]:
    handoff_status = str(summary.get("handoff_status", "tokenization_adaptation_handoff_pending"))
    queue_status = str(summary.get("queue_status", "queue_in_progress"))
    return [
        "# MeetEval Tokenization Adaptation Handoff Packet",
        "",
        "This generated packet provides a compact entrypoint for the MeetEval tokenization adaptation handoff stack. "
        "It remains experimental/frontier coordination only and does not claim full benchmark completion.",
        "",
        f"Current handoff status: `{handoff_status}`.",
        f"Current queue status: `{queue_status}`.",
        "",
        "| packet_order | section_name | artifact_path | section_role | packet_note |",
        "| --- | --- | --- | --- | --- |",
        *[
            f"| {row['packet_order']} | {row['section_name']} | {row['artifact_path']} | "
            f"{row['section_role']} | {row['packet_note']} |"
            for row in rows
        ],
    ]


def write_outputs(rows: list[dict[str, str]], summary: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_tokenization_adaptation_handoff_packet.csv"
    json_path = tables_dir / "meeteval_tokenization_adaptation_handoff_packet.json"
    md_path = figures_dir / "meeteval_tokenization_adaptation_handoff_packet.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=PACKET_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_packet_lines(rows, summary)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    summary = load_handoff_completion_summary()
    if not summary:
        print("Tokenization adaptation handoff completion summary not found; handoff packet not written.")
        return
    rows = build_packet_rows(summary)
    csv_path, json_path, md_path = write_outputs(rows, summary)
    print(f"Wrote MeetEval tokenization adaptation handoff packet CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval tokenization adaptation handoff packet JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval tokenization adaptation handoff packet note: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
