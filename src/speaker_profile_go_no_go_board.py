from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BOARD_COLUMNS = [
    "checkpoint_name",
    "case_scope",
    "current_status",
    "claim_boundary",
    "go_no_go_state",
    "next_action",
    "evidence_artifact",
]

SUMMARY_COLUMNS = [
    "scope",
    "case_scope",
    "checkpoint_count",
    "go_count",
    "no_go_count",
    "overall_state",
    "primary_boundary",
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
    if lowered in {
        "preflight_ready",
        "execution_chain_ready",
        "receipt_ready_to_fill",
        "advance_to_narrow_embedding_baseline",
    }:
        return "go"
    return "no_go"


def build_checkpoint_rows() -> list[dict[str, str]]:
    multisignal = load_json_payload("results/tables/speaker_profile_multisignal_summary.json")
    preflight = load_json_payload("results/tables/speaker_profile_embedding_trial_execution_preflight_readiness.json")
    execution_status = load_json_payload("results/tables/speaker_profile_embedding_trial_execution_status.json")
    receipt_ready = load_json_payload("results/tables/speaker_profile_embedding_trial_execution_receipt_readiness.json")

    case_scope = str(
        (preflight if isinstance(preflight, dict) else {}).get(
            "case_id",
            (execution_status if isinstance(execution_status, dict) else {}).get("case_id", "NoOverlap"),
        )
    )

    rows = [
        {
            "checkpoint_name": "multisignal_frontier_decision",
            "case_scope": case_scope,
            "current_status": str((multisignal if isinstance(multisignal, dict) else {}).get("frontier_decision", "")),
            "claim_boundary": "narrow_embedding_only_not_attribution_claim",
            "next_action": "Use the multi-signal result only to justify a narrow embedding baseline, not attribution success.",
            "evidence_artifact": "results/figures/speaker_profile_multisignal_summary.md",
        },
        {
            "checkpoint_name": "execution_preflight",
            "case_scope": case_scope,
            "current_status": str((preflight if isinstance(preflight, dict) else {}).get("readiness_status", "")),
            "claim_boundary": "execution_preflight_only",
            "next_action": "Keep the scope on the existing verified-case preflight until a real embedding run exists.",
            "evidence_artifact": "results/figures/speaker_profile_embedding_trial_execution_preflight_readiness.md",
        },
        {
            "checkpoint_name": "execution_chain",
            "case_scope": case_scope,
            "current_status": str((execution_status if isinstance(execution_status, dict) else {}).get("execution_chain_status", "")),
            "claim_boundary": "execution_chain_ready_not_result_ready",
            "next_action": "Only fill the execution receipt after a real narrow embedding run.",
            "evidence_artifact": "results/figures/speaker_profile_embedding_trial_execution_status.md",
        },
        {
            "checkpoint_name": "execution_receipt",
            "case_scope": case_scope,
            "current_status": str((receipt_ready if isinstance(receipt_ready, dict) else {}).get("readiness_status", "")),
            "claim_boundary": "receipt_ready_to_fill_not_attribution_ready",
            "next_action": "Use the ready receipt only as a writeback slot for the first narrow embedding trial.",
            "evidence_artifact": "results/figures/speaker_profile_embedding_trial_execution_receipt_readiness.md",
        },
    ]

    for row in rows:
        row["go_no_go_state"] = classify_go_no_go_state(str(row.get("current_status", "")))
    return rows


def build_summary_row(rows: list[dict[str, str]]) -> dict[str, str]:
    go_count = sum(1 for row in rows if row.get("go_no_go_state") == "go")
    no_go_count = len(rows) - go_count
    case_scope = rows[0]["case_scope"] if rows else "NoOverlap"

    oppositeoverlap_receipt_path = (
        PROJECT_ROOT / "results/tables/speaker_profile_oppositeoverlap_diagnostic_coordination_receipt.json"
    )
    heavyoverlap_receipt_path = (
        PROJECT_ROOT / "results/tables/speaker_profile_heavyoverlap_diagnostic_coordination_receipt.json"
    )
    midoverlap_receipt_path = (
        PROJECT_ROOT / "results/tables/speaker_profile_midoverlap_diagnostic_coordination_receipt.json"
    )
    lightoverlap_receipt_path = (
        PROJECT_ROOT / "results/tables/speaker_profile_lightoverlap_diagnostic_coordination_receipt.json"
    )
    case_scope_receipt_path = PROJECT_ROOT / "results/tables/speaker_profile_case_scope_coordination_receipt.json"
    oppositeoverlap_complete = False
    heavyoverlap_complete = False
    midoverlap_complete = False
    lightoverlap_complete = False
    case_scope_complete = False
    if oppositeoverlap_receipt_path.exists():
        payload = json.loads(oppositeoverlap_receipt_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            oppositeoverlap_complete = (
                str(payload.get("execution_status", ""))
                == "speaker_profile_oppositeoverlap_diagnostic_coordination_complete"
            )
    if heavyoverlap_receipt_path.exists():
        payload = json.loads(heavyoverlap_receipt_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            heavyoverlap_complete = (
                str(payload.get("execution_status", ""))
                == "speaker_profile_heavyoverlap_diagnostic_coordination_complete"
            )
    if midoverlap_receipt_path.exists():
        payload = json.loads(midoverlap_receipt_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            midoverlap_complete = (
                str(payload.get("execution_status", ""))
                == "speaker_profile_midoverlap_diagnostic_coordination_complete"
            )
    if lightoverlap_receipt_path.exists():
        payload = json.loads(lightoverlap_receipt_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            lightoverlap_complete = (
                str(payload.get("execution_status", ""))
                == "speaker_profile_lightoverlap_diagnostic_coordination_complete"
            )
    if case_scope_receipt_path.exists():
        payload = json.loads(case_scope_receipt_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            case_scope_complete = (
                str(payload.get("execution_status", "")) == "speaker_profile_case_scope_coordination_complete"
            )

    if rows and go_count == len(rows) and oppositeoverlap_complete:
        overall_state = "speaker_profile_oppositeoverlap_diagnostic_coordination_complete"
        recommended_next_action = (
            "OppositeOverlap diagnostic scope coordinated; all gold-case diagnostic boundaries documented."
        )
    elif rows and go_count == len(rows) and heavyoverlap_complete:
        overall_state = "speaker_profile_heavyoverlap_diagnostic_coordination_complete"
        recommended_next_action = (
            "HeavyOverlap diagnostic scope coordinated; OppositeOverlap remains deferred diagnostic candidate only."
        )
    elif rows and go_count == len(rows) and midoverlap_complete:
        overall_state = "speaker_profile_midoverlap_diagnostic_coordination_complete"
        recommended_next_action = (
            "MidOverlap diagnostic scope coordinated; HeavyOverlap remains deferred diagnostic candidate only."
        )
    elif rows and go_count == len(rows) and lightoverlap_complete:
        overall_state = "speaker_profile_lightoverlap_diagnostic_coordination_complete"
        recommended_next_action = (
            "LightOverlap diagnostic scope coordinated; MidOverlap remains deferred diagnostic candidate only."
        )
    elif rows and go_count == len(rows) and case_scope_complete:
        overall_state = "speaker_profile_case_scope_coordination_complete"
        recommended_next_action = (
            "Case-scope coordination documented; LightOverlap/MidOverlap remain diagnostic candidates only."
        )
    elif rows and go_count == len(rows):
        overall_state = "narrow_execution_ready"
        recommended_next_action = (
            "Proceed only with one narrow embedding baseline writeback for the current verified case; "
            "do not upgrade this into a broader attribution claim."
        )
    else:
        overall_state = "execution_not_ready"
        recommended_next_action = (
            "Complete speaker profile checkpoints before any case-scope coordination writeback."
        )
    return {
        "scope": "speaker_profile_go_no_go_board",
        "case_scope": case_scope,
        "checkpoint_count": str(len(rows)),
        "go_count": str(go_count),
        "no_go_count": str(no_go_count),
        "overall_state": overall_state,
        "primary_boundary": "attribution_claims_still_blocked_by_weak_support",
        "recommended_next_action": recommended_next_action,
        "observation": (
            "experimental/frontier coordination board only; it separates narrow execution readiness "
            "from blocked speaker-attribution claims."
        ),
    }


def build_board_lines(rows: list[dict[str, str]]) -> list[str]:
    go_count = sum(1 for row in rows if row.get("go_no_go_state") == "go")
    lines = [
        "# Speaker Profile Go-No-Go Board",
        "",
        "This generated board compresses the current speaker-profile stronger-method chain into a go/no-go view. "
        "It remains experimental/frontier and does not claim speaker identification success.",
        "",
        f"Summary: `{go_count}/{len(rows)}` checkpoints are ready for a narrow embedding-baseline execution path, while attribution claims remain blocked.",
        "",
        "| checkpoint_name | case_scope | current_status | claim_boundary | go_no_go_state | next_action | evidence_artifact |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checkpoint_name']} | {row['case_scope']} | {row['current_status']} | {row['claim_boundary']} | "
            f"{row['go_no_go_state']} | {row['next_action']} | {row['evidence_artifact']} |"
        )
    return lines


def build_summary_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Speaker Profile Go-No-Go Summary",
        "",
        "This generated summary condenses the speaker-profile decision board into one frontier action line. "
        "It remains experimental/frontier and does not claim speaker attribution success.",
        "",
        "| scope | case_scope | checkpoint_count | go_count | no_go_count | overall_state | primary_boundary | recommended_next_action | observation |",
        "| --- | --- | ---: | ---: | ---: | --- | --- | --- | --- |",
        (
            f"| {row['scope']} | {row['case_scope']} | {row['checkpoint_count']} | {row['go_count']} | "
            f"{row['no_go_count']} | {row['overall_state']} | {row['primary_boundary']} | "
            f"{row['recommended_next_action']} | {row['observation']} |"
        ),
    ]


def write_outputs(
    rows: list[dict[str, str]],
    summary_row: dict[str, str],
) -> tuple[Path, Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    board_csv = tables_dir / "speaker_profile_go_no_go_board.csv"
    board_json = tables_dir / "speaker_profile_go_no_go_board.json"
    summary_csv = tables_dir / "speaker_profile_go_no_go_summary.csv"
    summary_json = tables_dir / "speaker_profile_go_no_go_summary.json"
    board_md = figures_dir / "speaker_profile_go_no_go_board.md"
    summary_md = figures_dir / "speaker_profile_go_no_go_summary.md"

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
    print(f"Wrote speaker profile go-no-go board CSV: {outputs[0].relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile go-no-go board JSON: {outputs[1].relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile go-no-go summary CSV: {outputs[2].relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile go-no-go summary JSON: {outputs[3].relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile go-no-go board note: {outputs[4].relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile go-no-go summary note: {outputs[5].relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
