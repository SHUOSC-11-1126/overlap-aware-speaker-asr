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


def to_float(value: Any) -> float:
    try:
        return float(str(value).strip())
    except Exception:
        return 0.0


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


def load_case_map(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["id"]: case for case in config.get("audio_cases", [])}
