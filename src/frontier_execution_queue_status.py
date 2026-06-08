from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


STATUS_COLUMNS = [
    "scope",
    "meeteval_chain_status",
    "speaker_profile_chain_status",
    "external_staging_chain_status",
    "llm_critic_chain_status",
    "demo_excellence_chain_status",
    "combined_chain_status",
    "status_note",
]


def load_summary(path_rel: str) -> dict[str, str]:
    summary_path = PROJECT_ROOT / path_rel
    if not summary_path.exists():
        return {}
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def current_state_to_chain_status(current_state: str) -> str:
    ready_states = {
        "receipt_ready_to_fill",
        "narrow_execution_ready",
        "qualitative_writeback_ready",
        "presentation_writeback_ready",
    }
    return "execution_chain_ready" if current_state in ready_states else "execution_chain_in_progress"


def build_status_row(
    meeteval_status: dict[str, str],
    speaker_profile_status: dict[str, str],
    external_staging_status: dict[str, str],
    llm_critic_status: dict[str, str],
    demo_status: dict[str, str],
) -> dict[str, str]:
    meeteval_chain = str(meeteval_status.get("execution_chain_status", "execution_chain_in_progress"))
    speaker_chain = str(speaker_profile_status.get("execution_chain_status", "execution_chain_in_progress"))
    external_chain = str(external_staging_status.get("execution_chain_status", "execution_chain_in_progress"))
    llm_chain = current_state_to_chain_status(str(llm_critic_status.get("overall_state", "")))
    demo_chain = current_state_to_chain_status(str(demo_status.get("overall_state", "")))
    all_ready = (
        meeteval_chain == "execution_chain_ready"
        and speaker_chain == "execution_chain_ready"
        and external_chain == "execution_chain_ready"
        and llm_chain == "execution_chain_ready"
        and demo_chain == "execution_chain_ready"
    )
    combined_status = "execution_chain_ready" if all_ready else "execution_chain_in_progress"
    return {
        "scope": "frontier_execution_queues",
        "meeteval_chain_status": meeteval_chain,
        "speaker_profile_chain_status": speaker_chain,
        "external_staging_chain_status": external_chain,
        "llm_critic_chain_status": llm_chain,
        "demo_excellence_chain_status": demo_chain,
        "combined_chain_status": combined_status,
        "status_note": (
            "Unified experimental/frontier execution-chain rollup across MeetEval, speaker profile, external staging, "
            "LLM critic, and demo excellence; no official benchmark execution, verified transcript repair, live demo, "
            "or external audio staging is claimed."
        ),
    }


def build_status_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# Frontier Execution Queue Status",
        "",
        "This generated note records the unified frontier execution-chain rollup. "
        "It remains coordination support only and does not claim benchmark completion.",
        "",
        "| scope | meeteval_chain_status | speaker_profile_chain_status | external_staging_chain_status | llm_critic_chain_status | demo_excellence_chain_status | combined_chain_status | status_note |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
        (
            f"| {row['scope']} | {row['meeteval_chain_status']} | {row['speaker_profile_chain_status']} | "
            f"{row['external_staging_chain_status']} | {row['llm_critic_chain_status']} | "
            f"{row['demo_excellence_chain_status']} | {row['combined_chain_status']} | {row['status_note']} |"
        ),
    ]
    return lines


def write_outputs(status_row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_queue_status.csv"
    json_path = tables_dir / "frontier_execution_queue_status.json"
    md_path = figures_dir / "frontier_execution_queue_status.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=STATUS_COLUMNS)
        writer.writeheader()
        writer.writerow(status_row)
    json_path.write_text(json.dumps(status_row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_status_lines(status_row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    meeteval_status = load_summary("results/tables/meeteval_cpwer_execution_status.json")
    speaker_profile_status = load_summary("results/tables/speaker_profile_embedding_trial_execution_status.json")
    external_staging_status = load_summary("results/tables/external_validation_slice_staging_execution_status.json")
    llm_critic_status = load_summary("results/tables/llm_critic_go_no_go_summary.json")
    demo_status = load_summary("results/tables/demo_go_no_go_summary.json")
    status_row = build_status_row(
        meeteval_status,
        speaker_profile_status,
        external_staging_status,
        llm_critic_status,
        demo_status,
    )
    csv_path, json_path, md_path = write_outputs(status_row)
    print(f"Wrote frontier execution queue status CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution queue status JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution queue status note: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Combined chain status: {status_row['combined_chain_status']}")


if __name__ == "__main__":
    main()
