from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


READINESS_COLUMNS = [
    "scope",
    "text_proxy_queue_status",
    "handoff_status",
    "trial_case_target",
    "method_direction",
    "readiness_status",
    "readiness_note",
]


def load_json_dict(path_rel: str) -> dict[str, str]:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_readiness_row(
    text_proxy_completion: dict[str, str],
    handoff: dict[str, str],
) -> dict[str, str]:
    text_proxy_queue = str(text_proxy_completion.get("queue_status", "queue_in_progress"))
    handoff_status = str(handoff.get("handoff_status", "handoff_not_ready"))
    trial_case = str(handoff.get("trial_case_target", "NoOverlap"))
    method_direction = str(handoff.get("method_direction", "embedding_or_voiceprint_baseline"))
    ready = text_proxy_queue == "queue_complete" and handoff_status == "embedding_trial_handoff_ready"
    return {
        "scope": "speaker_profile_embedding_trial_handoff",
        "text_proxy_queue_status": text_proxy_queue,
        "handoff_status": handoff_status,
        "trial_case_target": trial_case,
        "method_direction": method_direction,
        "readiness_status": "handoff_ready" if ready else "handoff_not_ready",
        "readiness_note": (
            "experimental/frontier embedding trial handoff readiness; "
            "voiceprint or embedding execution is not claimed."
        ),
    }


def build_readiness_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Speaker Profile Embedding Trial Handoff Readiness",
        "",
        "This generated note records embedding trial handoff readiness after the text-proxy diagnostic stack. "
        "It does not claim voiceprint success or improved speaker attribution.",
        "",
        "| scope | text_proxy_queue_status | handoff_status | trial_case_target | method_direction | readiness_status | readiness_note |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        (
            f"| {row['scope']} | {row['text_proxy_queue_status']} | {row['handoff_status']} | "
            f"{row['trial_case_target']} | {row['method_direction']} | {row['readiness_status']} | "
            f"{row['readiness_note']} |"
        ),
    ]


def write_outputs(readiness_row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "speaker_profile_embedding_trial_handoff_readiness.csv"
    json_path = tables_dir / "speaker_profile_embedding_trial_handoff_readiness.json"
    md_path = figures_dir / "speaker_profile_embedding_trial_handoff_readiness.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=READINESS_COLUMNS)
        writer.writeheader()
        writer.writerow(readiness_row)
    json_path.write_text(json.dumps(readiness_row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_readiness_lines(readiness_row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    text_proxy_completion = load_json_dict(
        "results/tables/speaker_profile_text_proxy_trial_diagnostic_completion_summary.json"
    )
    handoff = load_json_dict("results/tables/speaker_profile_embedding_trial_handoff.json")
    if not text_proxy_completion or not handoff:
        print("Text-proxy completion or embedding trial handoff not found; readiness not written.")
        return
    readiness_row = build_readiness_row(text_proxy_completion, handoff)
    csv_path, json_path, md_path = write_outputs(readiness_row)
    print(f"Wrote speaker profile embedding trial handoff readiness CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile embedding trial handoff readiness JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile embedding trial handoff readiness note: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Readiness status: {readiness_row['readiness_status']}")


if __name__ == "__main__":
    main()
