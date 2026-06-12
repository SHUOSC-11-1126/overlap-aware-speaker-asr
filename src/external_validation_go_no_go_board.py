from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BOARD_COLUMNS = [
    "checkpoint_name",
    "dataset_name",
    "current_status",
    "blocker",
    "go_no_go_state",
    "next_action",
    "evidence_artifact",
]

SUMMARY_COLUMNS = [
    "scope",
    "dataset_name",
    "checkpoint_count",
    "go_count",
    "no_go_count",
    "overall_state",
    "primary_blocker",
    "recommended_next_action",
    "observation",
]


def load_json_payload(path_rel: str) -> dict | list:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, (dict, list)) else {}


def classify_go_no_go_state(current_status: str) -> str:
    lowered = current_status.strip().lower()
    no_go_tokens = ("pending", "blocked", "not_ready", "template_only", "missing", "scaffold_only")
    if not lowered:
        return "no_go"
    if any(token in lowered for token in no_go_tokens):
        return "no_go"
    return "go"


def license_is_confirmed(license_status: str, confirmation_status: str) -> bool:
    lowered = f"{license_status} {confirmation_status}".lower()
    return "confirmed" in lowered and "pending" not in lowered


def mini_check_audio_ready(mini_check: dict | list | None) -> bool:
    if not isinstance(mini_check, dict):
        return False
    return (
        str(mini_check.get("audio_staged", "")).strip().lower() == "true"
        and str(mini_check.get("reference_staged", "")).strip().lower() == "true"
    )


def mini_check_validation_status(mini_check: dict | list | None) -> str:
    if not isinstance(mini_check, dict):
        return ""
    return str(mini_check.get("validation_status", "")).strip()


def normalize_first_status(payload: dict | list, preferred_keys: list[str]) -> str:
    if isinstance(payload, dict):
        for key in preferred_keys:
            value = str(payload.get(key, "")).strip()
            if value:
                return value
        return ""
    if isinstance(payload, list) and payload:
        first = payload[0]
        if isinstance(first, dict):
            for key in preferred_keys:
                value = str(first.get(key, "")).strip()
                if value:
                    return value
    return ""


def build_checkpoint_rows() -> list[dict[str, str]]:
    license_gate = load_json_payload("results/tables/external_validation_license_gate.json")
    license_confirmation = load_json_payload("results/tables/external_validation_license_confirmation.json")
    if not license_confirmation:
        license_confirmation = load_json_payload(
            "results/tables/external_validation_license_confirmation_scaffold.json"
        )
    manifest = load_json_payload("results/tables/external_validation_slice_manifest.json")
    readiness = load_json_payload("results/tables/external_validation_slice_staging_readiness.json")
    execution_status = load_json_payload("results/tables/external_validation_slice_staging_execution_status.json")
    mini_check = load_json_payload("results/tables/external_validation_mini_sanity_check.json")

    dataset_name = str(
        (manifest if isinstance(manifest, dict) else {}).get(
            "dataset_name",
            (readiness if isinstance(readiness, dict) else {}).get("dataset_name", "AISHELL-4"),
        )
    )
    license_status = str(
        (manifest if isinstance(manifest, dict) else {}).get(
            "license_status",
            normalize_first_status(license_confirmation, ["license_status"]),
        )
    )
    confirmation_status = normalize_first_status(license_confirmation, ["confirmation_status"])
    confirmed = license_is_confirmed(license_status, confirmation_status)

    rows = [
        {
            "checkpoint_name": "license_gate",
            "dataset_name": dataset_name,
            "current_status": license_status or normalize_first_status(license_gate, ["license_status"]),
            "blocker": "none_documented" if confirmed else "license_confirmation_pending",
            "next_action": (
                "License documented under external/sanity-check; optional audio staging may proceed."
                if confirmed
                else "Record a concrete license confirmation decision before any audio staging."
            ),
            "evidence_artifact": (
                "results/figures/external_validation_license_confirmation.md"
                if confirmed
                else "results/figures/external_validation_license_gate.md"
            ),
        },
        {
            "checkpoint_name": "license_confirmation",
            "dataset_name": dataset_name,
            "current_status": confirmation_status or normalize_first_status(license_confirmation, ["confirmation_status"]),
            "blocker": "none_documented" if confirmed else "license_confirmation_pending",
            "next_action": (
                "License confirmation recorded; keep attribution visible in external artifacts."
                if confirmed
                else "Fill the confirmation scaffold with the recorded license decision."
            ),
            "evidence_artifact": (
                "results/figures/external_validation_license_confirmation.md"
                if confirmed
                else "results/figures/external_validation_license_confirmation_scaffold.md"
            ),
        },
        {
            "checkpoint_name": "slice_manifest",
            "dataset_name": dataset_name,
            "current_status": normalize_first_status(manifest, ["staging_status", "license_status"]),
            "blocker": (
                "none_documented"
                if confirmed
                and str((manifest if isinstance(manifest, dict) else {}).get("staging_status", ""))
                in {"ready_for_staging", "audio_excerpt_staged", "audio_and_reference_staged"}
                else str((manifest if isinstance(manifest, dict) else {}).get("staging_status", "blocked_by_license_gate"))
            ),
            "next_action": (
                "Manifest ready for optional AISHELL-4 excerpt staging."
                if confirmed
                else "Keep the manifest narrow and blocked until license confirmation is recorded."
            ),
            "evidence_artifact": "results/figures/external_validation_slice_manifest.md",
        },
        {
            "checkpoint_name": "staging_readiness",
            "dataset_name": dataset_name,
            "current_status": normalize_first_status(readiness, ["readiness_status"]),
            "blocker": str((readiness if isinstance(readiness, dict) else {}).get("blocker", "")),
            "next_action": (
                "Readiness review may proceed; audio download remains optional."
                if confirmed
                else "Resolve the readiness blocker before any staging review."
            ),
            "evidence_artifact": "results/figures/external_validation_slice_staging_readiness.md",
        },
        {
            "checkpoint_name": "mini_sanity_check",
            "dataset_name": dataset_name,
            "current_status": normalize_first_status(mini_check, ["validation_status"]),
            "blocker": (
                "audio_staging_pending"
                if mini_check_validation_status(mini_check) == "metadata_only_pass"
                else (
                    "none_documented"
                    if mini_check_validation_status(mini_check) == "ready_for_narrow_audio_eval"
                    else mini_check_validation_status(mini_check) or "missing"
                )
            ),
            "next_action": (
                "Metadata-only pass recorded; stage one excerpt before claiming audio eval."
                if mini_check_validation_status(mini_check) == "metadata_only_pass"
                else (
                    "Narrow external audio eval may proceed under external/sanity-check labeling."
                    if mini_check_validation_status(mini_check) == "ready_for_narrow_audio_eval"
                    else "Run python -m src.external_validation_mini_sanity_check after license confirmation."
                )
            ),
            "evidence_artifact": "results/figures/external_validation_mini_sanity_check.md",
        },
        {
            "checkpoint_name": "execution_chain",
            "dataset_name": dataset_name,
            "current_status": normalize_first_status(execution_status, ["execution_receipt_status", "execution_chain_status"]),
            "blocker": (
                str((execution_status if isinstance(execution_status, dict) else {}).get("blocker", "license_confirmation_pending"))
                if not confirmed
                else (
                    "execution_receipt_pending"
                    if mini_check_audio_ready(mini_check)
                    else "audio_staging_pending"
                )
            ),
            "next_action": (
                "Do not fill the execution receipt until the license blocker is cleared."
                if not confirmed
                else (
                    "Fill execution receipt before claiming any external benchmark run."
                    if mini_check_audio_ready(mini_check)
                    else "Fill execution receipt only after optional audio excerpt is staged."
                )
            ),
            "evidence_artifact": "results/figures/external_validation_slice_staging_execution_status.md",
        },
    ]

    for row in rows:
        row["go_no_go_state"] = classify_go_no_go_state(str(row.get("current_status", "")))
    return rows


def build_summary_row(rows: list[dict[str, str]]) -> dict[str, str]:
    go_count = sum(1 for row in rows if row.get("go_no_go_state") == "go")
    no_go_count = len(rows) - go_count
    dataset_name = rows[0]["dataset_name"] if rows else "AISHELL-4"

    primary_blocker = "none_documented"
    for row in rows:
        blocker = str(row.get("blocker", "")).strip()
        if blocker and blocker not in {"none_documented", ""}:
            primary_blocker = blocker
            break

    if primary_blocker == "execution_receipt_pending":
        overall_state = "ready_for_narrow_audio_eval"
        recommended_next_action = (
            "Audio excerpt staged; fill execution receipt before any external benchmark claim."
        )
    elif primary_blocker in {"none_documented", "audio_staging_pending"}:
        overall_state = "ready_for_optional_audio_staging"
        recommended_next_action = "Optionally stage one AISHELL-4 excerpt; do not claim gold benchmark results."
    elif "license" in primary_blocker:
        overall_state = "blocked_by_license_confirmation"
        recommended_next_action = (
            "Record and write back the license confirmation decision before any external staging attempt."
        )
    else:
        overall_state = "not_ready_for_staging"
        recommended_next_action = "Resolve the primary blocker before any external audio staging attempt."
    return {
        "scope": "external_validation_go_no_go_board",
        "dataset_name": dataset_name,
        "checkpoint_count": str(len(rows)),
        "go_count": str(go_count),
        "no_go_count": str(no_go_count),
        "overall_state": overall_state,
        "primary_blocker": primary_blocker,
        "recommended_next_action": recommended_next_action,
        "observation": (
            "external/sanity-check coordination board only; it does not claim external audio download "
            "or benchmark execution."
        ),
    }


def build_board_lines(rows: list[dict[str, str]]) -> list[str]:
    no_go_count = sum(1 for row in rows if row.get("go_no_go_state") == "no_go")
    lines = [
        "# External Validation Go-No-Go Board",
        "",
        "This generated board compresses the first external validation slice chain into a go/no-go view. "
        "It remains external/sanity-check coordination only and does not claim any external download or benchmark run.",
        "",
        f"Summary: `{no_go_count}/{len(rows)}` checkpoints are still `no_go` for the first AISHELL-4 slice.",
        "",
        "| checkpoint_name | dataset_name | current_status | blocker | go_no_go_state | next_action | evidence_artifact |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checkpoint_name']} | {row['dataset_name']} | {row['current_status']} | {row['blocker']} | "
            f"{row['go_no_go_state']} | {row['next_action']} | {row['evidence_artifact']} |"
        )
    return lines


def build_summary_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# External Validation Go-No-Go Summary",
        "",
        "This generated summary condenses the external validation go/no-go board into one decision line. "
        "It remains external/sanity-check coordination only and does not claim any external benchmark execution.",
        "",
        "| scope | dataset_name | checkpoint_count | go_count | no_go_count | overall_state | primary_blocker | recommended_next_action | observation |",
        "| --- | --- | ---: | ---: | ---: | --- | --- | --- | --- |",
        (
            f"| {row['scope']} | {row['dataset_name']} | {row['checkpoint_count']} | {row['go_count']} | "
            f"{row['no_go_count']} | {row['overall_state']} | {row['primary_blocker']} | "
            f"{row['recommended_next_action']} | {row['observation']} |"
        ),
    ]
    return lines


def write_outputs(
    rows: list[dict[str, str]],
    summary_row: dict[str, str],
) -> tuple[Path, Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    board_csv = tables_dir / "external_validation_go_no_go_board.csv"
    board_json = tables_dir / "external_validation_go_no_go_board.json"
    summary_csv = tables_dir / "external_validation_go_no_go_summary.csv"
    summary_json = tables_dir / "external_validation_go_no_go_summary.json"
    board_md = figures_dir / "external_validation_go_no_go_board.md"
    summary_md = figures_dir / "external_validation_go_no_go_summary.md"

    with board_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BOARD_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    board_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    with summary_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerow(summary_row)
    summary_json.write_text(json.dumps(summary_row, ensure_ascii=False, indent=2), encoding="utf-8")

    board_md.write_text("\n".join(build_board_lines(rows)) + "\n", encoding="utf-8")
    summary_md.write_text("\n".join(build_summary_lines(summary_row)) + "\n", encoding="utf-8")
    return board_csv, board_json, summary_csv, summary_json, board_md, summary_md


def main() -> None:
    rows = build_checkpoint_rows()
    summary_row = build_summary_row(rows)
    outputs = write_outputs(rows, summary_row)
    print(f"Wrote external validation go-no-go board CSV: {outputs[0].relative_to(PROJECT_ROOT)}")
    print(f"Wrote external validation go-no-go board JSON: {outputs[1].relative_to(PROJECT_ROOT)}")
    print(f"Wrote external validation go-no-go summary CSV: {outputs[2].relative_to(PROJECT_ROOT)}")
    print(f"Wrote external validation go-no-go summary JSON: {outputs[3].relative_to(PROJECT_ROOT)}")
    print(f"Wrote external validation go-no-go board note: {outputs[4].relative_to(PROJECT_ROOT)}")
    print(f"Wrote external validation go-no-go summary note: {outputs[5].relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
