from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def to_int(value: Any) -> int:
    try:
        return int(float(str(value).strip()))
    except Exception:
        return 0


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def read_csv_rows(path: Path, project_root: Path | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        ref = path.relative_to(project_root) if project_root else path
        raise FileNotFoundError(f"Missing table: {ref}")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        try:
            rows = list(csv.DictReader(f))
        except csv.Error as exc:
            ref = path.relative_to(project_root) if project_root else path
            raise ValueError(f"Failed to parse CSV {ref}: {exc}") from exc
    return [row for row in rows if isinstance(row, dict)]


def write_csv_json(
    rows: list[dict[str, Any]],
    csv_path: Path,
    json_path: Path,
    fieldnames: list[str],
) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def build_card_lines(rows: list[dict[str, str]], title: str) -> list[str]:
    lines = [
        f"# Speaker Profile {title} Diagnostic Coordination Card (experimental/frontier)",
        "",
        "Diagnostic scope coordination — not overlap-case embedding execution.",
        "",
        "| section_id | headline | artifact_anchor | result_label |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['section_id']} | {row['headline']} | {row['artifact_anchor']} | {row['result_label']} |"
        )
    lines.append("")
    for row in rows:
        lines.append(f"- **{row['section_id']}**: {row['coordination_note']}")
    return lines


def build_fill_lines(row: dict[str, str], title: str) -> list[str]:
    return [
        f"# Speaker Profile {title} Diagnostic Coordination Writeback",
        "",
        "| fill_status | diagnostic_case_scope | candidate_case_scope | execution_receipt_status | blocker |",
        "| --- | --- | --- | --- | --- |",
        (
            f"| {row['fill_status']} | {row['diagnostic_case_scope']} | {row['candidate_case_scope']} | "
            f"{row['execution_receipt_status']} | {row['blocker']} |"
        ),
    ]


def read_json(path: Path, project_root: Path | None = None) -> Any:
    if not path.exists():
        ref = path.relative_to(project_root) if project_root else path
        raise FileNotFoundError(f"Missing file: {ref}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_json_dict(path_rel: str, project_root: Path | None = None) -> dict[str, Any]:
    base = project_root or Path(__file__).resolve().parent.parent
    path = base / path_rel
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_case_map(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["id"]: case for case in config.get("audio_cases", [])}
