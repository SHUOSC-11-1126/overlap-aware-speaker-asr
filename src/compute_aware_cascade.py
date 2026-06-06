from __future__ import annotations

import argparse
import csv
import json
import struct
import zlib
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config


METHODS = ["mixed_whisper", "separated_whisper", "separated_whisper_cleaned"]

DEFAULT_COST_PROXY = {
    "mixed_whisper": 1.0,
    "separated_whisper": 2.0,
    "separated_whisper_cleaned": 2.1,
    "manual_review": 3.0,
}

STRATEGIES = [
    "fixed_mixed_whisper",
    "fixed_separated_whisper",
    "fixed_separated_whisper_cleaned",
    "router_v2_costed",
    "risk_aware_costed",
    "budget_cascade",
]

SYNTHETIC_STRATEGIES = [
    "fixed_mixed_whisper",
    "fixed_separated_whisper",
    "fixed_separated_whisper_cleaned",
    "router_v2_synthetic_costed",
    "budget_cascade",
    "cleaned_preferred_cascade",
]

PERFORMANCE_COLUMNS = [
    "strategy",
    "label",
    "average_cer",
    "average_compute_cost",
    "relative_cost_vs_fixed_separated",
    "automatic_coverage",
    "manual_review_count",
    "sample_count",
    "case_count",
    "selected_method_mix",
    "notes",
]

SYNTHETIC_PERFORMANCE_COLUMNS = [
    "scope",
    "strategy",
    "label",
    "average_cer",
    "average_compute_cost",
    "relative_cost_vs_fixed_separated",
    "automatic_coverage",
    "manual_review_count",
    "sample_count",
    "case_count",
    "selected_method_mix",
    "notes",
]

RUNTIME_AUDIT_COLUMNS = [
    "dataset",
    "scope",
    "strategy",
    "observed_runtime_count",
    "proxy_runtime_count",
    "manual_review_count",
    "case_count",
    "observed_runtime_ratio",
    "notes",
]

RUNTIME_NORMALIZATION_COLUMNS = [
    "dataset",
    "scope",
    "strategy",
    "average_runtime_sec",
    "average_selected_audio_duration_sec",
    "average_rtf",
    "sample_count",
    "duration_source",
    "notes",
]

PARETO_COLUMNS = [
    "dataset",
    "scope",
    "strategy",
    "average_cer",
    "average_compute_cost",
    "average_rtf",
    "pareto_status",
    "dominated_by",
    "notes",
]

RECOMMENDATION_COLUMNS = [
    "dataset",
    "scope",
    "profile",
    "recommended_strategy",
    "average_cer",
    "average_compute_cost",
    "average_rtf",
    "reason",
]

ROBUSTNESS_GAP_COLUMNS = [
    "strategy",
    "gold_average_cer",
    "synthetic_average_cer",
    "cer_gap_vs_gold",
    "gold_average_compute_cost",
    "synthetic_average_compute_cost",
    "cost_gap_vs_gold",
    "gold_average_rtf",
    "synthetic_average_rtf",
    "rtf_gap_vs_gold",
    "robustness_rank",
    "notes",
]

RECOMMENDATION_STABILITY_COLUMNS = [
    "profile",
    "distinct_strategy_count",
    "most_common_strategy",
    "consensus_ratio",
    "scope_count",
    "strategy_set",
    "notes",
]

RECOMMENDATION_FAMILY_STABILITY_COLUMNS = [
    "profile",
    "distinct_strategy_count",
    "most_common_strategy",
    "consensus_ratio",
    "scope_count",
    "strategy_set",
    "notes",
]

DECISION_MATRIX_COLUMNS = [
    "profile",
    "gold_recommended_strategy",
    "synthetic_all_recommended_strategy",
    "family_most_common_strategy",
    "family_consensus_ratio",
    "synthetic_all_average_cer",
    "synthetic_all_average_compute_cost",
    "synthetic_all_average_rtf",
    "robustness_rank",
    "shared_cer_gap_vs_gold",
    "notes",
]

ARTIFACT_INDEX_COLUMNS = [
    "artifact_id",
    "dataset",
    "label",
    "artifact_group",
    "artifact_path",
    "generator_command",
    "intended_use",
]

BENCHMARK_READINESS_COLUMNS = [
    "artifact_id",
    "dataset",
    "label",
    "artifact_group",
    "artifact_path",
    "benchmark_priority",
    "benchmark_priority_rank",
    "benchmark_status",
    "readiness_tier",
    "next_evidence_step",
]

BENCHMARK_PLAN_COLUMNS = [
    "plan_step_id",
    "step_order",
    "phase",
    "dataset_scope",
    "command",
    "prerequisite_artifacts",
    "refreshed_artifacts",
    "success_signal",
]

PROFILE_PLAYBOOK_COLUMNS = [
    "profile",
    "default_role",
    "family_strategy",
    "gold_strategy",
    "synthetic_strategy",
    "when_to_use",
    "avoid_when",
    "tradeoff_summary",
]

BENCHMARK_CHECKLIST_COLUMNS = [
    "plan_step_id",
    "step_order",
    "phase",
    "dataset_scope",
    "command",
    "session_type",
    "required_metadata",
    "acceptance_check",
]

BENCHMARK_MANIFEST_TEMPLATE_COLUMNS = [
    "plan_step_id",
    "step_order",
    "phase",
    "dataset_scope",
    "session_type",
    "command",
    "acceptance_check",
    "hardware_label",
    "device",
    "repeat_count",
    "warmup_count",
    "batch_shape",
    "timing_notes",
    "source_timing_manifest",
    "refresh_command",
    "diff_review_notes",
    "cross_dataset_scope",
    "consistency_notes",
]

BENCHMARK_STATUS_COLUMNS = [
    "plan_step_id",
    "step_order",
    "phase",
    "dataset_scope",
    "execution_status",
    "readiness_signal",
    "pending_field_count",
    "blocking_category",
    "next_action",
    "missing_fields",
    "acceptance_check",
]

BENCHMARK_EXECUTION_SUMMARY_COLUMNS = [
    "phase",
    "step_count",
    "filled_step_count",
    "template_only_step_count",
    "total_pending_field_count",
    "readiness_label",
    "primary_blocking_category",
    "recommended_next_action",
    "covered_datasets",
]

BENCHMARK_EXECUTION_QUEUE_COLUMNS = [
    "queue_rank",
    "plan_step_id",
    "phase",
    "dataset_scope",
    "priority_bucket",
    "blocking_category",
    "next_action",
    "pending_field_count",
    "queue_reason",
]


def build_benchmark_packet_lines(
    readiness_rows: list[dict[str, Any]],
    plan_rows: list[dict[str, Any]],
    checklist_rows: list[dict[str, Any]],
    manifest_rows: list[dict[str, Any]],
    status_rows: list[dict[str, Any]],
    execution_summary_rows: list[dict[str, Any]],
    execution_queue_rows: list[dict[str, Any]],
) -> list[str]:
    lines = [
        "# Cascade Benchmark Handoff Packet",
        "",
        "This generated packet consolidates the benchmark readiness scaffold, staged plan, execution checklist, session manifest template, and execution-status board.",
        "",
        "## Readiness Snapshot",
        "",
        "| artifact_id | benchmark_priority | benchmark_status | next_evidence_step |",
        "| --- | --- | --- | --- |",
    ]
    for row in readiness_rows[:5]:
        lines.append(
            f"| {row.get('artifact_id', '')} | {row.get('benchmark_priority', '')} | {row.get('benchmark_status', '')} | {row.get('next_evidence_step', '')} |"
        )
    lines.extend(["", "## Phase Order", ""])
    for row in plan_rows:
        lines.append(
            f"- step {row.get('step_order', '')}: `{row.get('plan_step_id', '')}` / `{row.get('phase', '')}` / `{row.get('dataset_scope', '')}` / `{row.get('command', '')}`"
        )
    lines.extend(["", "## Metadata Capture", ""])
    for row in checklist_rows:
        lines.append(
            f"- `{row.get('plan_step_id', '')}`: session `{row.get('session_type', '')}`, metadata `{row.get('required_metadata', '')}`, acceptance `{row.get('acceptance_check', '')}`"
        )
    lines.extend(["", "## Execution Summary", ""])
    for row in execution_summary_rows:
        lines.append(
            f"- `{row.get('phase', '')}`: `{row.get('readiness_label', '')}` with "
            f"`{row.get('template_only_step_count', '')}/{row.get('step_count', '')}` template-only steps, "
            f"`{row.get('total_pending_field_count', '')}` pending fields, blocker `{row.get('primary_blocking_category', '')}`, "
            f"next `{row.get('recommended_next_action', '')}`, datasets `{row.get('covered_datasets', '')}`"
        )
    lines.extend(["", "## Execution Queue", ""])
    for row in execution_queue_rows:
        lines.append(
            f"- rank {row.get('queue_rank', '')}: `{row.get('plan_step_id', '')}` / `{row.get('priority_bucket', '')}` / "
            f"blocker `{row.get('blocking_category', '')}` / next `{row.get('next_action', '')}` / reason `{row.get('queue_reason', '')}`"
        )
    lines.extend(["", "## Execution Status", ""])
    for row in status_rows:
        lines.append(
            f"- step {row.get('step_order', '')}: `{row.get('plan_step_id', '')}` is `{row.get('execution_status', '')}` / "
            f"`{row.get('readiness_signal', '')}` with missing `{row.get('missing_fields', '')}`"
        )
    lines.extend(["", "## Manifest Template", ""])
    if manifest_rows:
        sample = manifest_rows[0]
        fields = [key for key, value in sample.items() if str(value).strip() == "TODO"]
        lines.append(f"Manifest template fields: {', '.join(fields)}")
    return lines


def build_benchmark_status_rows(manifest_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tracked_fields = [
        "hardware_label",
        "device",
        "repeat_count",
        "warmup_count",
        "batch_shape",
        "timing_notes",
        "source_timing_manifest",
        "refresh_command",
        "diff_review_notes",
        "cross_dataset_scope",
        "consistency_notes",
    ]
    rows: list[dict[str, Any]] = []
    for row in manifest_rows:
        missing = [field for field in tracked_fields if str(row.get(field, "")).strip() == "TODO"]
        execution_status = "template_only" if missing else "filled"
        readiness_signal = "pending_execution" if missing else "ready_for_review"
        phase = str(row.get("phase", ""))
        pending_field_count = len(missing)
        if not missing:
            blocking_category = "ready_for_review"
            next_action = "review_completed_manifest"
        elif phase == "foundation":
            blocking_category = "runtime_capture_missing"
            next_action = "collect_controlled_runtime"
        elif phase == "surface":
            blocking_category = "artifact_refresh_missing"
            next_action = "refresh_timing_backed_artifacts"
        else:
            blocking_category = "derived_refresh_missing"
            next_action = "refresh_cross_dataset_stack"
        rows.append(
            {
                "plan_step_id": row.get("plan_step_id", ""),
                "step_order": row.get("step_order", ""),
                "phase": phase,
                "dataset_scope": row.get("dataset_scope", ""),
                "execution_status": execution_status,
                "readiness_signal": readiness_signal,
                "pending_field_count": pending_field_count,
                "blocking_category": blocking_category,
                "next_action": next_action,
                "missing_fields": ";".join(missing),
                "acceptance_check": row.get("acceptance_check", ""),
            }
        )
    return sorted(rows, key=lambda row: to_int(row.get("step_order")))


def build_benchmark_execution_summary_rows(status_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in status_rows:
        grouped.setdefault(str(row.get("phase", "")), []).append(row)

    rows: list[dict[str, Any]] = []
    for phase in sorted(grouped, key=lambda value: min(to_int(row.get("step_order")) for row in grouped[value])):
        entries = sorted(grouped[phase], key=lambda row: to_int(row.get("step_order")))
        step_count = len(entries)
        filled_step_count = sum(1 for row in entries if str(row.get("execution_status", "")) == "filled")
        template_only_step_count = sum(1 for row in entries if str(row.get("execution_status", "")) == "template_only")
        total_pending_field_count = sum(to_int(row.get("pending_field_count")) for row in entries)
        blocking_counts: dict[str, int] = {}
        action_counts: dict[str, int] = {}
        datasets = sorted({str(row.get("dataset_scope", "")) for row in entries if str(row.get("dataset_scope", "")).strip()})
        blocking_source_rows = [row for row in entries if to_int(row.get("pending_field_count")) > 0] or entries
        action_source_rows = [row for row in entries if to_int(row.get("pending_field_count")) > 0] or entries
        for row in blocking_source_rows:
            blocking = str(row.get("blocking_category", ""))
            blocking_counts[blocking] = blocking_counts.get(blocking, 0) + 1
        for row in action_source_rows:
            action = str(row.get("next_action", ""))
            action_counts[action] = action_counts.get(action, 0) + 1
        primary_blocking_category = min(blocking_counts, key=lambda key: (-blocking_counts[key], key))
        recommended_next_action = min(action_counts, key=lambda key: (-action_counts[key], key))
        readiness_label = "ready_for_review" if total_pending_field_count == 0 else "pending_execution"
        rows.append(
            {
                "phase": phase,
                "step_count": step_count,
                "filled_step_count": filled_step_count,
                "template_only_step_count": template_only_step_count,
                "total_pending_field_count": total_pending_field_count,
                "readiness_label": readiness_label,
                "primary_blocking_category": primary_blocking_category,
                "recommended_next_action": recommended_next_action,
                "covered_datasets": ";".join(datasets),
            }
        )
    return rows


def build_benchmark_execution_summary_lines(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "# Cascade Benchmark Execution Summary",
        "",
        "This generated summary condenses the phase-by-phase benchmark board into execution-ready blocker totals and next actions.",
        "",
        "| phase | step_count | filled_step_count | template_only_step_count | total_pending_field_count | readiness_label | primary_blocking_category | recommended_next_action | covered_datasets |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['phase']} | {row['step_count']} | {row['filled_step_count']} | {row['template_only_step_count']} | "
            f"{row['total_pending_field_count']} | {row['readiness_label']} | {row['primary_blocking_category']} | "
            f"{row['recommended_next_action']} | {row['covered_datasets']} |"
        )
    return lines


def build_benchmark_execution_queue_rows(status_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    priority_rank = {
        "do_now": 0,
        "next_after_runtime": 1,
        "ready_for_review": 2,
    }

    queue_rows: list[dict[str, Any]] = []
    for row in status_rows:
        blocking_category = str(row.get("blocking_category", ""))
        pending_field_count = to_int(row.get("pending_field_count"))
        execution_status = str(row.get("execution_status", ""))
        if execution_status == "filled":
            priority_bucket = "ready_for_review"
        elif blocking_category == "runtime_capture_missing":
            priority_bucket = "do_now"
        else:
            priority_bucket = "next_after_runtime"
        queue_rows.append(
            {
                "queue_rank": 0,
                "plan_step_id": row.get("plan_step_id", ""),
                "phase": row.get("phase", ""),
                "dataset_scope": row.get("dataset_scope", ""),
                "priority_bucket": priority_bucket,
                "blocking_category": blocking_category,
                "next_action": row.get("next_action", ""),
                "pending_field_count": pending_field_count,
                "queue_reason": f"{blocking_category} with {pending_field_count} pending fields",
                "step_order": to_int(row.get("step_order")),
            }
        )
    sorted_rows = sorted(
        queue_rows,
        key=lambda row: (
            priority_rank.get(str(row["priority_bucket"]), 99),
            to_int(row["step_order"]),
            -to_int(row["pending_field_count"]),
            str(row["plan_step_id"]),
        ),
    )
    for index, row in enumerate(sorted_rows, start=1):
        row["queue_rank"] = index
        row.pop("step_order", None)
    return sorted_rows


def build_benchmark_execution_queue_lines(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "# Cascade Benchmark Execution Queue",
        "",
        "This generated queue turns the benchmark status stack into an ordered next-run list.",
        "",
        "| queue_rank | plan_step_id | phase | dataset_scope | priority_bucket | blocking_category | next_action | pending_field_count | queue_reason |",
        "| ---: | --- | --- | --- | --- | --- | --- | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['queue_rank']} | {row['plan_step_id']} | {row['phase']} | {row['dataset_scope']} | {row['priority_bucket']} | "
            f"{row['blocking_category']} | {row['next_action']} | {row['pending_field_count']} | {row['queue_reason']} |"
        )
    return lines


def write_benchmark_execution_queue_outputs(
    rows: list[dict[str, Any]],
    csv_path: Path,
    json_path: Path,
    summary_path: Path,
) -> None:
    write_csv_json(rows, csv_path, json_path, BENCHMARK_EXECUTION_QUEUE_COLUMNS)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text("\n".join(build_benchmark_execution_queue_lines(rows)) + "\n", encoding="utf-8")


def write_benchmark_execution_summary_outputs(
    rows: list[dict[str, Any]],
    csv_path: Path,
    json_path: Path,
    summary_path: Path,
) -> None:
    write_csv_json(rows, csv_path, json_path, BENCHMARK_EXECUTION_SUMMARY_COLUMNS)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text("\n".join(build_benchmark_execution_summary_lines(rows)) + "\n", encoding="utf-8")


def write_benchmark_packet_output(
    readiness_rows: list[dict[str, Any]],
    plan_rows: list[dict[str, Any]],
    checklist_rows: list[dict[str, Any]],
    manifest_rows: list[dict[str, Any]],
    status_rows: list[dict[str, Any]],
    execution_summary_rows: list[dict[str, Any]],
    execution_queue_rows: list[dict[str, Any]],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(
            build_benchmark_packet_lines(
                readiness_rows,
                plan_rows,
                checklist_rows,
                manifest_rows,
                status_rows,
                execution_summary_rows,
                execution_queue_rows,
            )
        )
        + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute-aware cascade evaluation.")
    parser.add_argument(
        "--dataset",
        choices=["gold", "synthetic_split"],
        default="gold",
        help="Dataset scope to evaluate.",
    )
    return parser.parse_args()


def to_float(value: Any) -> float:
    try:
        return float(str(value).strip())
    except Exception:
        return 0.0


def to_int(value: Any) -> int:
    try:
        return int(float(str(value).strip()))
    except Exception:
        return 0


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing table: {path.relative_to(PROJECT_ROOT)}")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [row for row in csv.DictReader(f) if isinstance(row, dict)]


def write_csv_json(rows: list[dict[str, Any]], csv_path: Path, json_path: Path, fieldnames: list[str]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def compute_method_cost(method: str, runtime_row: dict[str, Any]) -> float:
    runtime_field = {
        "mixed_whisper": "mixed_runtime_sec",
        "separated_whisper": "separated_runtime_sec",
        "separated_whisper_cleaned": "cleaned_runtime_sec",
    }.get(method)
    if runtime_field:
        observed = to_float(runtime_row.get(runtime_field))
        if observed > 0:
            return observed
    return DEFAULT_COST_PROXY.get(method, DEFAULT_COST_PROXY["manual_review"])


def has_observed_runtime(method: str, runtime_row: dict[str, Any]) -> bool:
    runtime_field = {
        "mixed_whisper": "mixed_runtime_sec",
        "separated_whisper": "separated_runtime_sec",
        "separated_whisper_cleaned": "cleaned_runtime_sec",
    }.get(method)
    if not runtime_field:
        return False
    return to_float(runtime_row.get(runtime_field)) > 0


def choose_budget_cascade_method(overlap_level: int, risk_level: str) -> str:
    if overlap_level == 0:
        return "separated_whisper"
    if overlap_level in (1, 2):
        return "mixed_whisper"
    if risk_level in {"medium", "high"}:
        return "separated_whisper_cleaned"
    return "separated_whisper"


def choose_cleaned_preferred_method(overlap_level: int, duplicate_removed_count: int) -> str:
    if overlap_level >= 3 or duplicate_removed_count > 0:
        return "separated_whisper_cleaned"
    if overlap_level in (1, 2):
        return "mixed_whisper"
    return "separated_whisper"


def fixed_method_for_strategy(strategy: str) -> str | None:
    mapping = {
        "fixed_mixed_whisper": "mixed_whisper",
        "fixed_separated_whisper": "separated_whisper",
        "fixed_separated_whisper_cleaned": "separated_whisper_cleaned",
    }
    return mapping.get(strategy)


def select_strategy_method(
    strategy: str,
    case: dict[str, Any],
    decisions: dict[str, dict[str, str]],
) -> str:
    fixed = fixed_method_for_strategy(strategy)
    if fixed:
        return fixed
    case_id = str(case.get("case_id", "")).strip()
    if strategy == "budget_cascade":
        return choose_budget_cascade_method(to_int(case.get("overlap_level")), str(case.get("risk_level", "low")).strip())
    return decisions.get(strategy, {}).get(case_id, "manual_review")


def build_strategy_rows(
    cases: list[dict[str, Any]],
    decisions: dict[str, dict[str, str]],
    cer_lookup: dict[tuple[str, str], float],
    runtime_lookup: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    case_count = len(cases)
    for strategy in STRATEGIES:
        cer_values: list[float] = []
        costs: list[float] = []
        method_counts: dict[str, int] = {}
        manual_review_count = 0

        for case in cases:
            case_id = str(case.get("case_id", "")).strip()
            method = select_strategy_method(strategy, case, decisions)
            method_counts[method] = method_counts.get(method, 0) + 1
            costs.append(compute_method_cost(method, runtime_lookup.get(case_id, {})))

            if method == "manual_review":
                manual_review_count += 1
                continue
            cer = cer_lookup.get((case_id, method))
            if cer is not None:
                cer_values.append(cer)

        automatic_count = case_count - manual_review_count
        rows.append(
            {
                "strategy": strategy,
                "label": "experimental/frontier",
                "average_cer": round(sum(cer_values) / len(cer_values), 6) if cer_values else "",
                "average_compute_cost": round(sum(costs) / len(costs), 6) if costs else 0.0,
                "relative_cost_vs_fixed_separated": "",
                "automatic_coverage": round(automatic_count / case_count, 6) if case_count else 0.0,
                "manual_review_count": manual_review_count,
                "sample_count": len(cer_values),
                "case_count": case_count,
                "selected_method_mix": ";".join(
                    f"{method}:{method_counts[method]}" for method in sorted(method_counts)
                ),
                "notes": (
                    "Costed offline analysis; route selection uses existing reference-free decisions or overlap/risk signals. "
                    "CER is used only after decisions are fixed."
                ),
            }
        )

    separated_cost = next(
        (to_float(row["average_compute_cost"]) for row in rows if row["strategy"] == "fixed_separated_whisper"),
        0.0,
    )
    for row in rows:
        row["relative_cost_vs_fixed_separated"] = (
            round(to_float(row["average_compute_cost"]) / separated_cost, 6) if separated_cost else ""
        )
    return rows


def build_synthetic_scope_rows(
    cases: list[dict[str, Any]],
    decisions: dict[str, dict[str, str]],
    cer_lookup: dict[tuple[str, str], float],
    runtime_lookup: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    scopes: list[tuple[str, list[dict[str, Any]]]] = [("ALL", cases)]
    for split in sorted({str(case.get("split", "")).strip() for case in cases if str(case.get("split", "")).strip()}):
        scopes.append((split.upper(), [case for case in cases if str(case.get("split", "")).strip() == split]))
    for tier in sorted({str(case.get("tier", "")).strip() for case in cases if str(case.get("tier", "")).strip()}):
        scopes.append((tier, [case for case in cases if str(case.get("tier", "")).strip() == tier]))

    for scope, scoped_cases in scopes:
        case_count = len(scoped_cases)
        for strategy in SYNTHETIC_STRATEGIES:
            cer_values: list[float] = []
            costs: list[float] = []
            method_counts: dict[str, int] = {}
            manual_review_count = 0

            for case in scoped_cases:
                case_id = str(case.get("case_id", "")).strip()
                overlap_level = to_int(case.get("overlap_level"))
                duplicate_removed_count = to_int(case.get("duplicate_removed_count"))
                if strategy == "cleaned_preferred_cascade":
                    method = choose_cleaned_preferred_method(overlap_level, duplicate_removed_count)
                elif strategy == "budget_cascade":
                    risk_level = "high" if duplicate_removed_count > 0 or overlap_level >= 3 else "low"
                    method = choose_budget_cascade_method(overlap_level, risk_level)
                elif strategy == "router_v2_synthetic_costed":
                    method = decisions.get(strategy, {}).get(case_id, "manual_review")
                else:
                    method = select_strategy_method(strategy, case, {})

                method_counts[method] = method_counts.get(method, 0) + 1
                costs.append(compute_method_cost(method, runtime_lookup.get(case_id, {})))

                if method == "manual_review":
                    manual_review_count += 1
                    continue
                cer = cer_lookup.get((case_id, method))
                if cer is not None:
                    cer_values.append(cer)

            automatic_count = case_count - manual_review_count
            rows.append(
                {
                    "scope": scope,
                    "strategy": strategy,
                    "label": "synthetic/silver",
                    "average_cer": round(sum(cer_values) / len(cer_values), 6) if cer_values else "",
                    "average_compute_cost": round(sum(costs) / len(costs), 6) if costs else 0.0,
                    "relative_cost_vs_fixed_separated": "",
                    "automatic_coverage": round(automatic_count / case_count, 6) if case_count else 0.0,
                    "manual_review_count": manual_review_count,
                    "sample_count": len(cer_values),
                    "case_count": case_count,
                    "selected_method_mix": ";".join(
                        f"{method}:{method_counts[method]}" for method in sorted(method_counts)
                    ),
                    "notes": (
                        "Synthetic split cascade validation; route selection uses overlap, duplicate-removal, or existing "
                        "reference-free routing outputs. CER is evaluation-only."
                    ),
                }
            )

    separated_costs = {
        row["scope"]: to_float(row["average_compute_cost"])
        for row in rows
        if row["strategy"] == "fixed_separated_whisper"
    }
    for row in rows:
        separated_cost = separated_costs.get(str(row["scope"]))
        row["relative_cost_vs_fixed_separated"] = (
            round(to_float(row["average_compute_cost"]) / separated_cost, 6) if separated_cost else ""
        )
    return rows


def summarize_runtime_sources(
    cases: list[dict[str, Any]],
    strategies: list[str],
    decisions: dict[str, dict[str, str]],
    runtime_lookup: dict[str, dict[str, Any]],
    scope: str = "ALL",
    dataset_label: str = "gold",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    case_count = len(cases)
    for strategy in strategies:
        observed_runtime_count = 0
        proxy_runtime_count = 0
        manual_review_count = 0
        for case in cases:
            case_id = str(case.get("case_id", "")).strip()
            if strategy == "cleaned_preferred_cascade":
                method = choose_cleaned_preferred_method(
                    to_int(case.get("overlap_level")),
                    to_int(case.get("duplicate_removed_count")),
                )
            elif strategy == "budget_cascade":
                risk_level = str(case.get("risk_level", "")).strip()
                if not risk_level:
                    risk_level = "high" if to_int(case.get("duplicate_removed_count")) > 0 or to_int(case.get("overlap_level")) >= 3 else "low"
                method = choose_budget_cascade_method(to_int(case.get("overlap_level")), risk_level)
            elif strategy in decisions:
                method = decisions.get(strategy, {}).get(case_id, "manual_review")
            else:
                method = select_strategy_method(strategy, case, {})

            if method == "manual_review":
                manual_review_count += 1
                proxy_runtime_count += 1
            elif has_observed_runtime(method, runtime_lookup.get(case_id, {})):
                observed_runtime_count += 1
            else:
                proxy_runtime_count += 1

        rows.append(
            {
                "dataset": dataset_label,
                "scope": scope,
                "strategy": strategy,
                "observed_runtime_count": observed_runtime_count,
                "proxy_runtime_count": proxy_runtime_count,
                "manual_review_count": manual_review_count,
                "case_count": case_count,
                "observed_runtime_ratio": round(observed_runtime_count / case_count, 6) if case_count else 0.0,
                "notes": "Observed runtime count reflects selected methods with dataset runtime fields available; all other selected methods fall back to proxy cost.",
            }
        )
    return rows


def selected_duration_sec(method: str, duration_row: dict[str, Any]) -> float:
    if method == "mixed_whisper":
        return to_float(duration_row.get("mixed_duration_sec"))
    if method in {"separated_whisper", "separated_whisper_cleaned"}:
        return to_float(duration_row.get("separated_duration_sec"))
    return 0.0


def summarize_runtime_normalization(
    cases: list[dict[str, Any]],
    strategies: list[str],
    decisions: dict[str, dict[str, str]],
    runtime_lookup: dict[str, dict[str, Any]],
    duration_lookup: dict[str, dict[str, Any]],
    scope: str = "ALL",
    dataset_label: str = "gold",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for strategy in strategies:
        runtime_values: list[float] = []
        duration_values: list[float] = []
        rtf_values: list[float] = []
        for case in cases:
            case_id = str(case.get("case_id", "")).strip()
            if strategy == "cleaned_preferred_cascade":
                method = choose_cleaned_preferred_method(
                    to_int(case.get("overlap_level")),
                    to_int(case.get("duplicate_removed_count")),
                )
            elif strategy == "budget_cascade":
                risk_level = str(case.get("risk_level", "")).strip()
                if not risk_level:
                    risk_level = "high" if to_int(case.get("duplicate_removed_count")) > 0 or to_int(case.get("overlap_level")) >= 3 else "low"
                method = choose_budget_cascade_method(to_int(case.get("overlap_level")), risk_level)
            elif strategy in decisions:
                method = decisions.get(strategy, {}).get(case_id, "manual_review")
            else:
                method = select_strategy_method(strategy, case, {})

            if method == "manual_review":
                continue
            runtime_sec = compute_method_cost(method, runtime_lookup.get(case_id, {}))
            duration_sec = selected_duration_sec(method, duration_lookup.get(case_id, {}))
            if runtime_sec > 0 and duration_sec > 0:
                runtime_values.append(runtime_sec)
                duration_values.append(duration_sec)
                rtf_values.append(runtime_sec / duration_sec)

        rows.append(
            {
                "dataset": dataset_label,
                "scope": scope,
                "strategy": strategy,
                "average_runtime_sec": round(sum(runtime_values) / len(runtime_values), 6) if runtime_values else "",
                "average_selected_audio_duration_sec": round(sum(duration_values) / len(duration_values), 6) if duration_values else "",
                "average_rtf": round(sum(rtf_values) / len(rtf_values), 6) if rtf_values else "",
                "sample_count": len(rtf_values),
                "duration_source": "selected_audio",
                "notes": "RTF uses the selected route's processed audio duration: mixed uses one stream, separated/cleaned use the combined two-stream duration.",
            }
        )
    return rows


def classify_pareto_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    classified: list[dict[str, Any]] = []
    for row in rows:
        current_cer = to_float(row.get("average_cer"))
        current_cost = to_float(row.get("average_compute_cost"))
        dominated_by = ""
        for other in rows:
            if other is row:
                continue
            other_cer = to_float(other.get("average_cer"))
            other_cost = to_float(other.get("average_compute_cost"))
            not_worse = other_cer <= current_cer and other_cost <= current_cost
            strictly_better = other_cer < current_cer or other_cost < current_cost
            if not_worse and strictly_better:
                dominated_by = str(other.get("strategy", ""))
                break
        enriched = dict(row)
        enriched["pareto_status"] = "dominated" if dominated_by else "frontier"
        enriched["dominated_by"] = dominated_by
        enriched["notes"] = (
            "Pareto frontier minimizes average CER and average compute cost jointly."
            if not dominated_by
            else "Dominated by a strategy with no worse CER and no worse compute cost."
        )
        classified.append(enriched)
    return classified


def build_recommendation_rows(pareto_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in pareto_rows:
        key = (str(row.get("dataset", "")), str(row.get("scope", "")))
        grouped.setdefault(key, []).append(row)

    for (dataset, scope), rows in grouped.items():
        frontier_rows = [row for row in rows if str(row.get("pareto_status")) == "frontier"] or rows

        accuracy_pick = min(
            rows,
            key=lambda row: (to_float(row.get("average_cer")), to_float(row.get("average_compute_cost"))),
        )
        recommendations.append(
            {
                "dataset": dataset,
                "scope": scope,
                "profile": "accuracy_first",
                "recommended_strategy": str(accuracy_pick.get("strategy", "")),
                "average_cer": accuracy_pick.get("average_cer", ""),
                "average_compute_cost": accuracy_pick.get("average_compute_cost", ""),
                "average_rtf": accuracy_pick.get("average_rtf", ""),
                "reason": "Lowest average CER; ties break toward lower compute cost.",
            }
        )

        cost_pick = min(
            rows,
            key=lambda row: (to_float(row.get("average_compute_cost")), to_float(row.get("average_cer"))),
        )
        recommendations.append(
            {
                "dataset": dataset,
                "scope": scope,
                "profile": "cost_first",
                "recommended_strategy": str(cost_pick.get("strategy", "")),
                "average_cer": cost_pick.get("average_cer", ""),
                "average_compute_cost": cost_pick.get("average_compute_cost", ""),
                "average_rtf": cost_pick.get("average_rtf", ""),
                "reason": "Lowest average compute cost; ties break toward lower CER.",
            }
        )

        cer_values = [to_float(row.get("average_cer")) for row in frontier_rows]
        cost_values = [to_float(row.get("average_compute_cost")) for row in frontier_rows]
        cer_min, cer_max = min(cer_values or [0.0]), max(cer_values or [0.0])
        cost_min, cost_max = min(cost_values or [0.0]), max(cost_values or [0.0])

        def normalized_score(row: dict[str, Any]) -> tuple[float, float, float]:
            cer = to_float(row.get("average_cer"))
            cost = to_float(row.get("average_compute_cost"))
            cer_norm = 0.0 if cer_max == cer_min else (cer - cer_min) / (cer_max - cer_min)
            cost_norm = 0.0 if cost_max == cost_min else (cost - cost_min) / (cost_max - cost_min)
            return (cer_norm + cost_norm, cer_norm, cost_norm)

        balanced_pick = min(frontier_rows, key=normalized_score)
        recommendations.append(
            {
                "dataset": dataset,
                "scope": scope,
                "profile": "balanced",
                "recommended_strategy": str(balanced_pick.get("strategy", "")),
                "average_cer": balanced_pick.get("average_cer", ""),
                "average_compute_cost": balanced_pick.get("average_compute_cost", ""),
                "average_rtf": balanced_pick.get("average_rtf", ""),
                "reason": "Chosen from the Pareto frontier by the smallest normalized CER+compute distance to the ideal point.",
            }
        )

    return recommendations


def build_robustness_gap_rows(
    gold_rows: list[dict[str, Any]],
    synthetic_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    def canonical_strategy_name(strategy: str) -> str:
        if strategy in {"router_v2_costed", "router_v2_synthetic_costed"}:
            return "router_v2"
        return strategy

    gold_lookup = {
        canonical_strategy_name(str(row.get("strategy", ""))): row
        for row in gold_rows
        if str(row.get("scope", "ALL")) == "ALL"
    }
    synthetic_lookup = {
        canonical_strategy_name(str(row.get("strategy", ""))): row
        for row in synthetic_rows
        if str(row.get("scope", "ALL")) == "ALL"
    }
    shared = sorted(set(gold_lookup) & set(synthetic_lookup))
    rows: list[dict[str, Any]] = []
    for strategy in shared:
        gold = gold_lookup[strategy]
        synthetic = synthetic_lookup[strategy]
        cer_gap = round(to_float(synthetic.get("average_cer")) - to_float(gold.get("average_cer")), 6)
        cost_gap = round(to_float(synthetic.get("average_compute_cost")) - to_float(gold.get("average_compute_cost")), 6)
        rtf_gap = round(to_float(synthetic.get("average_rtf")) - to_float(gold.get("average_rtf")), 6)
        rows.append(
            {
                "strategy": strategy,
                "gold_average_cer": gold.get("average_cer", ""),
                "synthetic_average_cer": synthetic.get("average_cer", ""),
                "cer_gap_vs_gold": cer_gap,
                "gold_average_compute_cost": gold.get("average_compute_cost", ""),
                "synthetic_average_compute_cost": synthetic.get("average_compute_cost", ""),
                "cost_gap_vs_gold": cost_gap,
                "gold_average_rtf": gold.get("average_rtf", ""),
                "synthetic_average_rtf": synthetic.get("average_rtf", ""),
                "rtf_gap_vs_gold": rtf_gap,
                "robustness_rank": 0,
                "notes": "Gap is synthetic_split ALL minus gold ALL for the same strategy.",
            }
        )
    ranked = sorted(rows, key=lambda row: (to_float(row["cer_gap_vs_gold"]), abs(to_float(row["cost_gap_vs_gold"])), str(row["strategy"])))
    for index, row in enumerate(ranked, start=1):
        row["robustness_rank"] = index
    return ranked


def build_recommendation_stability_rows(recommendation_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in recommendation_rows:
        grouped.setdefault(str(row.get("profile", "")), []).append(row)

    rows: list[dict[str, Any]] = []
    for profile in sorted(grouped):
        entries = grouped[profile]
        counts: dict[str, int] = {}
        for entry in entries:
            strategy = str(entry.get("recommended_strategy", ""))
            counts[strategy] = counts.get(strategy, 0) + 1
        most_common_strategy = min(
            counts,
            key=lambda strategy: (-counts[strategy], strategy),
        )
        scope_count = len(entries)
        rows.append(
            {
                "profile": profile,
                "distinct_strategy_count": len(counts),
                "most_common_strategy": most_common_strategy,
                "consensus_ratio": round(counts[most_common_strategy] / scope_count, 6) if scope_count else 0.0,
                "scope_count": scope_count,
                "strategy_set": ";".join(sorted(counts)),
                "notes": "Consensus ratio is the share of audited scopes that recommend the most common strategy for this profile.",
            }
        )
    return rows


def canonical_strategy_family(strategy: str) -> str:
    if strategy in {"router_v2_costed", "router_v2_synthetic_costed"}:
        return "router_v2"
    return strategy


def build_recommendation_family_stability_rows(recommendation_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_rows = [
        dict(row, recommended_strategy=canonical_strategy_family(str(row.get("recommended_strategy", ""))))
        for row in recommendation_rows
    ]
    return build_recommendation_stability_rows(normalized_rows)


def build_decision_matrix_rows(
    gold_recommendations: list[dict[str, Any]],
    synthetic_recommendations: list[dict[str, Any]],
    family_stability_rows: list[dict[str, Any]],
    robustness_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    gold_lookup = {str(row.get("profile", "")): row for row in gold_recommendations if str(row.get("scope", "")) == "ALL"}
    synthetic_lookup = {str(row.get("profile", "")): row for row in synthetic_recommendations if str(row.get("scope", "")) == "ALL"}
    family_lookup = {str(row.get("profile", "")): row for row in family_stability_rows}
    robustness_lookup = {str(row.get("strategy", "")): row for row in robustness_rows}

    rows: list[dict[str, Any]] = []
    for profile in sorted(set(gold_lookup) | set(synthetic_lookup)):
        gold_row = gold_lookup.get(profile, {})
        synthetic_row = synthetic_lookup.get(profile, {})
        family_row = family_lookup.get(profile, {})
        synthetic_strategy = str(synthetic_row.get("recommended_strategy", ""))
        family_strategy = canonical_strategy_family(synthetic_strategy)
        robustness_row = robustness_lookup.get(family_strategy, {})
        rows.append(
            {
                "profile": profile,
                "gold_recommended_strategy": gold_row.get("recommended_strategy", ""),
                "synthetic_all_recommended_strategy": synthetic_strategy,
                "family_most_common_strategy": family_row.get("most_common_strategy", ""),
                "family_consensus_ratio": family_row.get("consensus_ratio", ""),
                "synthetic_all_average_cer": synthetic_row.get("average_cer", ""),
                "synthetic_all_average_compute_cost": synthetic_row.get("average_compute_cost", ""),
                "synthetic_all_average_rtf": synthetic_row.get("average_rtf", ""),
                "robustness_rank": robustness_row.get("robustness_rank", ""),
                "shared_cer_gap_vs_gold": robustness_row.get("cer_gap_vs_gold", ""),
                "notes": "Decision matrix merges gold recommendation, synthetic ALL recommendation, family-level stability, and shared robustness gap.",
            }
        )
    return rows


def load_gold_cases() -> list[dict[str, Any]]:
    config = load_config()
    risk_rows = {str(row["case_id"]): row for row in read_csv_rows(PROJECT_ROOT / "results" / "tables" / "risk_aware_selection.csv")}
    cases: list[dict[str, Any]] = []
    for case in config.get("audio_cases", []):
        case_id = str(case.get("id", "")).strip()
        risk_row = risk_rows.get(case_id, {})
        cases.append(
            {
                "case_id": case_id,
                "overlap_level": to_int(case.get("overlap_level")),
                "risk_level": str(risk_row.get("risk_level", "low")).strip() or "low",
            }
        )
    return [case for case in cases if case["case_id"]]


def load_decisions() -> dict[str, dict[str, str]]:
    router_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "routing_decisions_v2.csv")
    risk_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "risk_aware_selection.csv")
    return {
        "router_v2_costed": {
            str(row.get("case_id", "")).strip(): str(row.get("selected_method", "")).strip()
            for row in router_rows
            if str(row.get("case_id", "")).strip()
        },
        "risk_aware_costed": {
            str(row.get("case_id", "")).strip(): str(row.get("final_selected_method", "")).strip()
            for row in risk_rows
            if str(row.get("case_id", "")).strip()
        },
    }


def load_cer_lookup() -> dict[tuple[str, str], float]:
    lookup: dict[tuple[str, str], float] = {}
    for row in read_csv_rows(PROJECT_ROOT / "results" / "tables" / "cer_results.csv"):
        case_id = str(row.get("case_id", "")).strip()
        method = str(row.get("method", "")).strip()
        if case_id and method:
            lookup[(case_id, method)] = to_float(row.get("cer"))
    return lookup


def load_runtime_lookup() -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for row in read_csv_rows(PROJECT_ROOT / "results" / "tables" / "routing_decisions_v2.csv"):
        case_id = str(row.get("case_id", "")).strip()
        if not case_id:
            continue
        separated_runtime = to_float(row.get("separated_runtime_sec"))
        cleaned_runtime = to_float(row.get("cleaned_runtime_sec")) or separated_runtime
        lookup[case_id] = {
            "mixed_runtime_sec": to_float(row.get("mixed_runtime_sec")),
            "separated_runtime_sec": separated_runtime,
            "cleaned_runtime_sec": cleaned_runtime,
        }
    return lookup


def load_synthetic_split_cases() -> list[dict[str, Any]]:
    manifest_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "synthetic_split_manifest.csv")
    decision_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "synthetic_split_routing_decisions.csv")
    duplicate_lookup: dict[str, int] = {}
    for row in decision_rows:
        sample_id = str(row.get("sample_id", "")).strip()
        if sample_id and sample_id not in duplicate_lookup:
            duplicate_lookup[sample_id] = to_int(row.get("duplicate_removed_count"))
    return [
        {
            "case_id": str(row.get("sample_id", "")).strip(),
            "split": str(row.get("split", "")).strip(),
            "tier": str(row.get("tier", "")).strip(),
            "overlap_level": to_int(row.get("overlap_level_numeric")),
            "duplicate_removed_count": duplicate_lookup.get(str(row.get("sample_id", "")).strip(), 0),
        }
        for row in manifest_rows
        if str(row.get("sample_id", "")).strip()
    ]


def load_synthetic_split_decisions() -> dict[str, dict[str, str]]:
    rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "synthetic_split_routing_decisions.csv")
    return {
        "router_v2_synthetic_costed": {
            str(row.get("sample_id", "")).strip(): str(row.get("selected_method", "")).strip()
            for row in rows
            if str(row.get("sample_id", "")).strip() and str(row.get("strategy", "")).strip() == "v2_full_features"
        }
    }


def load_synthetic_split_cer_lookup() -> dict[tuple[str, str], float]:
    lookup: dict[tuple[str, str], float] = {}
    for row in read_csv_rows(PROJECT_ROOT / "results" / "tables" / "synthetic_split_cer_results.csv"):
        case_id = str(row.get("sample_id", "")).strip()
        method = str(row.get("method", "")).strip()
        if case_id and method:
            lookup[(case_id, method)] = to_float(row.get("cer"))
    return lookup


def load_synthetic_split_runtime_lookup() -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for row in read_csv_rows(PROJECT_ROOT / "results" / "tables" / "synthetic_split_routing_decisions.csv"):
        if str(row.get("strategy", "")).strip() != "v2_full_features":
            continue
        case_id = str(row.get("sample_id", "")).strip()
        if not case_id:
            continue
        lookup[case_id] = {
            "mixed_runtime_sec": to_float(row.get("mixed_runtime_sec")),
            "separated_runtime_sec": to_float(row.get("separated_runtime_sec")),
            "cleaned_runtime_sec": to_float(row.get("cleaned_runtime_sec")) or to_float(row.get("separated_runtime_sec")),
        }
    return lookup


def load_gold_duration_lookup() -> dict[str, dict[str, Any]]:
    rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "audio_manifest.csv")
    grouped: dict[str, dict[str, float]] = {}
    for row in rows:
        case_id = str(row.get("case_id", "")).strip()
        audio_type = str(row.get("audio_type", "")).strip()
        duration_sec = to_float(row.get("duration_sec"))
        if not case_id:
            continue
        payload = grouped.setdefault(case_id, {"mixed_duration_sec": 0.0, "separated_duration_sec": 0.0})
        if audio_type == "mixed":
            payload["mixed_duration_sec"] = duration_sec
        elif audio_type in {"separated_spk1", "separated_spk2"}:
            payload["separated_duration_sec"] += duration_sec
    return grouped


def load_synthetic_split_duration_lookup() -> dict[str, dict[str, Any]]:
    rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "synthetic_split_manifest.csv")
    lookup: dict[str, dict[str, Any]] = {}
    for row in rows:
        case_id = str(row.get("sample_id", "")).strip()
        mixed_duration_sec = to_float(row.get("mixed_duration_sec"))
        if case_id:
            lookup[case_id] = {
                "mixed_duration_sec": mixed_duration_sec,
                "separated_duration_sec": round(mixed_duration_sec * 2, 6) if mixed_duration_sec else 0.0,
            }
    return lookup


def render_summary(rows: list[dict[str, Any]], output_path: Path, figure_path: Path) -> None:
    lines = [
        "# Compute-aware Cascade Summary",
        "",
        "## Label",
        "",
        "- experimental/frontier",
        "",
        "## Interpretation",
        "",
        "- This is an offline costed analysis of existing gold benchmark outputs.",
        "- Route selection uses overlap, risk, and existing reference-free router decisions.",
        "- CER is used only after each strategy has fixed its selected method.",
        "- Compute cost uses observed runtime fields when available and deterministic proxy costs otherwise.",
        "",
        "## Performance",
        "",
        "| strategy | average_cer | average_compute_cost | relative_cost_vs_fixed_separated | coverage | method_mix |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| {strategy} | {average_cer} | {average_compute_cost} | {relative_cost_vs_fixed_separated} | "
            "{automatic_coverage} | {selected_method_mix} |".format(**row)
        )
    lines += [
        "",
        "## Outputs",
        "",
        "- Table: `results/tables/cascade_performance.csv`",
        f"- Figure: `{figure_path.relative_to(PROJECT_ROOT).as_posix()}`",
        "",
        "## Caution",
        "",
        "The runtime values are useful for comparing routes inside this repository, but they are not a universal hardware benchmark.",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_synthetic_summary(rows: list[dict[str, Any]], output_path: Path, figure_path: Path) -> None:
    perf_map = {(str(row["scope"]), str(row["strategy"])): row for row in rows}
    lines = [
        "# Synthetic Split Compute-aware Cascade Summary",
        "",
        "## Label",
        "",
        "- synthetic/silver",
        "- experimental/frontier",
        "",
        "## Interpretation",
        "",
        "- This is a held-out synthetic split cascade validation using silver references.",
        "- Route selection uses overlap, duplicate-removal signals, or existing reference-free router v2 decisions.",
        "- CER is used only after each strategy has fixed its selected method.",
        "- Runtime values come from existing synthetic routing tables and are repository-local cost signals only.",
        "",
    ]
    for scope in ["ALL", "DEV", "TEST"]:
        lines.extend([f"## {scope}", "", "| strategy | average_cer | average_compute_cost | relative_cost_vs_fixed_separated | method_mix |", "| --- | ---: | ---: | ---: | --- |"])
        for strategy in SYNTHETIC_STRATEGIES:
            row = perf_map.get((scope, strategy))
            if row:
                lines.append(
                    f"| {strategy} | {row['average_cer']} | {row['average_compute_cost']} | {row['relative_cost_vs_fixed_separated']} | {row['selected_method_mix']} |"
                )
        lines.append("")
    tier_scopes = sorted({str(row["scope"]) for row in rows if str(row["scope"]) not in {"ALL", "DEV", "TEST"}})
    if tier_scopes:
        lines.extend(["## Tier Breakdown", ""])
        for scope in tier_scopes:
            lines.extend([f"### {scope}", "", "| strategy | average_cer | average_compute_cost | sample_count |", "| --- | ---: | ---: | ---: |"])
            for strategy in SYNTHETIC_STRATEGIES:
                row = perf_map.get((scope, strategy))
                if row:
                    lines.append(
                        f"| {strategy} | {row['average_cer']} | {row['average_compute_cost']} | {row['sample_count']} |"
                    )
            lines.append("")
    lines.extend(
        [
            "## Outputs",
            "",
            "- Table: `results/tables/synthetic_split_cascade_performance.csv`",
            f"- Figure: `{figure_path.relative_to(PROJECT_ROOT).as_posix()}`",
            "",
            "## Caution",
            "",
            "These results are silver validation evidence and must not be promoted to gold benchmark claims.",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_runtime_audit_summary(rows: list[dict[str, Any]], output_path: Path) -> None:
    lines = [
        "# Cascade Runtime Provenance Audit",
        "",
        "This audit shows whether each selected route used observed runtime fields or fell back to proxy cost.",
        "",
    ]
    grouped_scopes = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (str(row["dataset"]), str(row["scope"]))
        if key not in seen:
            seen.add(key)
            grouped_scopes.append(key)
    for dataset, scope in grouped_scopes:
        lines.extend([f"## {dataset} / {scope}", "", "| strategy | observed_runtime_count | proxy_runtime_count | manual_review_count | observed_runtime_ratio |", "| --- | ---: | ---: | ---: | ---: |"])
        for row in rows:
            if str(row["dataset"]) == dataset and str(row["scope"]) == scope:
                lines.append(
                    f"| {row['strategy']} | {row['observed_runtime_count']} | {row['proxy_runtime_count']} | {row['manual_review_count']} | {row['observed_runtime_ratio']} |"
                )
        lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_runtime_normalization_summary(rows: list[dict[str, Any]], output_path: Path) -> None:
    lines = [
        "# Cascade Runtime Normalization Audit",
        "",
        "This audit normalizes selected-route runtime by the selected audio duration to estimate route-specific RTF.",
        "",
    ]
    grouped_scopes = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (str(row["dataset"]), str(row["scope"]))
        if key not in seen:
            seen.add(key)
            grouped_scopes.append(key)
    for dataset, scope in grouped_scopes:
        lines.extend([f"## {dataset} / {scope}", "", "| strategy | average_runtime_sec | average_selected_audio_duration_sec | average_rtf | sample_count |", "| --- | ---: | ---: | ---: | ---: |"])
        for row in rows:
            if str(row["dataset"]) == dataset and str(row["scope"]) == scope:
                lines.append(
                    f"| {row['strategy']} | {row['average_runtime_sec']} | {row['average_selected_audio_duration_sec']} | {row['average_rtf']} | {row['sample_count']} |"
                )
        lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_pareto_rows(
    performance_rows: list[dict[str, Any]],
    runtime_normalization_rows: list[dict[str, Any]],
    dataset_label: str,
) -> list[dict[str, Any]]:
    rtf_lookup = {
        (str(row.get("scope", "ALL")), str(row.get("strategy", ""))): row
        for row in runtime_normalization_rows
    }
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in performance_rows:
        scope = str(row.get("scope", "ALL"))
        runtime_row = rtf_lookup.get((scope, str(row.get("strategy", ""))), {})
        grouped.setdefault(scope, []).append(
            {
                "dataset": dataset_label,
                "scope": scope,
                "strategy": str(row.get("strategy", "")),
                "average_cer": row.get("average_cer", ""),
                "average_compute_cost": row.get("average_compute_cost", ""),
                "average_rtf": runtime_row.get("average_rtf", ""),
            }
        )

    pareto_rows: list[dict[str, Any]] = []
    for scope in sorted(grouped):
        pareto_rows.extend(classify_pareto_rows(grouped[scope]))
    return pareto_rows


def render_pareto_summary(rows: list[dict[str, Any]], output_path: Path) -> None:
    lines = [
        "# Cascade Pareto Frontier Audit",
        "",
        "This audit marks which strategies are on the CER/compute Pareto frontier and which are dominated.",
        "",
    ]
    grouped_scopes = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (str(row["dataset"]), str(row["scope"]))
        if key not in seen:
            seen.add(key)
            grouped_scopes.append(key)
    for dataset, scope in grouped_scopes:
        lines.extend([f"## {dataset} / {scope}", "", "| strategy | average_cer | average_compute_cost | average_rtf | pareto_status | dominated_by |", "| --- | ---: | ---: | ---: | --- | --- |"])
        for row in rows:
            if str(row["dataset"]) == dataset and str(row["scope"]) == scope:
                lines.append(
                    f"| {row['strategy']} | {row['average_cer']} | {row['average_compute_cost']} | {row['average_rtf']} | {row['pareto_status']} | {row['dominated_by']} |"
                )
        lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_pareto_outputs(
    rows: list[dict[str, Any]],
    csv_path: Path,
    json_path: Path,
    summary_path: Path,
) -> None:
    write_csv_json(rows, csv_path, json_path, PARETO_COLUMNS)
    render_pareto_summary(rows, summary_path)


def render_recommendation_summary(rows: list[dict[str, Any]], output_path: Path) -> None:
    lines = [
        "# Cascade Recommendation Card",
        "",
        "This card recommends strategies for different deployment preferences using the current cascade audits.",
        "",
    ]
    grouped = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (str(row["dataset"]), str(row["scope"]))
        if key not in seen:
            seen.add(key)
            grouped.append(key)
    for dataset, scope in grouped:
        lines.extend([f"## {dataset} / {scope}", "", "| profile | recommended_strategy | average_cer | average_compute_cost | average_rtf | reason |", "| --- | --- | ---: | ---: | ---: | --- |"])
        for row in rows:
            if str(row["dataset"]) == dataset and str(row["scope"]) == scope:
                lines.append(
                    f"| {row['profile']} | {row['recommended_strategy']} | {row['average_cer']} | {row['average_compute_cost']} | {row['average_rtf']} | {row['reason']} |"
                )
        lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_recommendation_outputs(
    rows: list[dict[str, Any]],
    csv_path: Path,
    json_path: Path,
    summary_path: Path,
) -> None:
    write_csv_json(rows, csv_path, json_path, RECOMMENDATION_COLUMNS)
    render_recommendation_summary(rows, summary_path)


def render_robustness_gap_summary(rows: list[dict[str, Any]], output_path: Path) -> None:
    lines = [
        "# Cascade Robustness Gap Audit",
        "",
        "This audit compares gold ALL against synthetic split ALL for shared strategy names.",
        "",
        "| strategy | gold_average_cer | synthetic_average_cer | cer_gap_vs_gold | gold_average_compute_cost | synthetic_average_compute_cost | cost_gap_vs_gold | gold_average_rtf | synthetic_average_rtf | rtf_gap_vs_gold | robustness_rank |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['strategy']} | {row['gold_average_cer']} | {row['synthetic_average_cer']} | {row['cer_gap_vs_gold']} | "
            f"{row['gold_average_compute_cost']} | {row['synthetic_average_compute_cost']} | {row['cost_gap_vs_gold']} | "
            f"{row['gold_average_rtf']} | {row['synthetic_average_rtf']} | {row['rtf_gap_vs_gold']} | {row['robustness_rank']} |"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_robustness_gap_outputs(
    rows: list[dict[str, Any]],
    csv_path: Path,
    json_path: Path,
    summary_path: Path,
) -> None:
    write_csv_json(rows, csv_path, json_path, ROBUSTNESS_GAP_COLUMNS)
    render_robustness_gap_summary(rows, summary_path)


def render_recommendation_stability_summary(rows: list[dict[str, Any]], output_path: Path) -> None:
    lines = [
        "# Cascade Recommendation Stability Audit",
        "",
        "This audit checks how often each recommendation profile keeps the same strategy across audited scopes.",
        "",
        "| profile | distinct_strategy_count | most_common_strategy | consensus_ratio | scope_count | strategy_set |",
        "| --- | ---: | --- | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['profile']} | {row['distinct_strategy_count']} | {row['most_common_strategy']} | {row['consensus_ratio']} | {row['scope_count']} | {row['strategy_set']} |"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_recommendation_stability_outputs(
    rows: list[dict[str, Any]],
    csv_path: Path,
    json_path: Path,
    summary_path: Path,
) -> None:
    write_csv_json(rows, csv_path, json_path, RECOMMENDATION_STABILITY_COLUMNS)
    render_recommendation_stability_summary(rows, summary_path)


def write_recommendation_family_stability_outputs(
    rows: list[dict[str, Any]],
    csv_path: Path,
    json_path: Path,
    summary_path: Path,
) -> None:
    write_csv_json(rows, csv_path, json_path, RECOMMENDATION_FAMILY_STABILITY_COLUMNS)
    render_recommendation_stability_summary(rows, summary_path)


def render_decision_matrix_summary(rows: list[dict[str, Any]], output_path: Path) -> None:
    lines = [
        "# Cascade Decision Matrix",
        "",
        "This matrix consolidates recommendation, family-level stability, and shared robustness into one deployment-facing table.",
        "",
        "| profile | gold_recommended_strategy | synthetic_all_recommended_strategy | family_most_common_strategy | family_consensus_ratio | synthetic_all_average_cer | synthetic_all_average_compute_cost | synthetic_all_average_rtf | robustness_rank | shared_cer_gap_vs_gold |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['profile']} | {row['gold_recommended_strategy']} | {row['synthetic_all_recommended_strategy']} | "
            f"{row['family_most_common_strategy']} | {row['family_consensus_ratio']} | {row['synthetic_all_average_cer']} | "
            f"{row['synthetic_all_average_compute_cost']} | {row['synthetic_all_average_rtf']} | {row['robustness_rank']} | {row['shared_cer_gap_vs_gold']} |"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_decision_matrix_outputs(
    rows: list[dict[str, Any]],
    csv_path: Path,
    json_path: Path,
    summary_path: Path,
) -> None:
    write_csv_json(rows, csv_path, json_path, DECISION_MATRIX_COLUMNS)
    render_decision_matrix_summary(rows, summary_path)


def build_frontier_report_lines(
    decision_matrix_rows: list[dict[str, Any]],
    family_stability_rows: list[dict[str, Any]],
    robustness_rows: list[dict[str, Any]],
) -> list[str]:
    lines = [
        "# Compute-aware Cascade Frontier Report",
        "",
        "This report consolidates the current compute-aware cascade decision evidence into one generated note.",
        "",
        "## Decision Matrix",
        "",
        "| profile | gold_recommended_strategy | synthetic_all_recommended_strategy | family_most_common_strategy | family_consensus_ratio | synthetic_all_average_cer | robustness_rank |",
        "| --- | --- | --- | --- | ---: | ---: | ---: |",
    ]
    for row in decision_matrix_rows:
        lines.append(
            f"| {row['profile']} | {row['gold_recommended_strategy']} | {row['synthetic_all_recommended_strategy']} | "
            f"{row['family_most_common_strategy']} | {row['family_consensus_ratio']} | {row['synthetic_all_average_cer']} | {row['robustness_rank']} |"
        )
    lines.extend(["", "## Stability Highlights", ""])
    for row in family_stability_rows:
        lines.append(
            f"- `{row['profile']}`: most common family `{row['most_common_strategy']}`, consensus `{row['consensus_ratio']}`"
        )
    lines.extend(["", "## Robustness Highlights", ""])
    for row in robustness_rows[:3]:
        lines.append(
            f"- rank {row['robustness_rank']}: `{row['strategy']}` with `cer_gap_vs_gold {row['cer_gap_vs_gold']}`"
        )
    return lines


def write_frontier_report(
    decision_matrix_rows: list[dict[str, Any]],
    family_stability_rows: list[dict[str, Any]],
    robustness_rows: list[dict[str, Any]],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(build_frontier_report_lines(decision_matrix_rows, family_stability_rows, robustness_rows)) + "\n", encoding="utf-8")


def build_artifact_index_rows() -> list[dict[str, Any]]:
    registry = [
        ("gold_cascade_performance", "gold", "experimental/frontier", "performance", "results/tables/cascade_performance.csv", "python -m src.compute_aware_cascade", "Primary gold compute-aware performance table."),
        ("gold_cascade_summary", "gold", "experimental/frontier", "summary", "results/figures/compute_aware_cascade_summary.md", "python -m src.compute_aware_cascade", "Narrative summary of the gold cascade trade-off table."),
        ("gold_tradeoff_figure", "gold", "experimental/frontier", "figure", "results/figures/cer_runtime_tradeoff.png", "python -m src.compute_aware_cascade", "CER versus compute scatter plot for gold strategies."),
        ("gold_runtime_audit", "gold", "experimental/frontier", "audit", "results/tables/cascade_runtime_audit.csv", "python -m src.compute_aware_cascade", "Observed-runtime versus proxy-runtime provenance audit for gold selections."),
        ("gold_runtime_normalization", "gold", "experimental/frontier", "audit", "results/tables/cascade_runtime_normalization.csv", "python -m src.compute_aware_cascade", "Selected-route runtime normalization and RTF audit for gold strategies."),
        ("gold_pareto", "gold", "experimental/frontier", "audit", "results/tables/cascade_pareto.csv", "python -m src.compute_aware_cascade", "CER/compute Pareto frontier audit for gold strategies."),
        ("gold_recommendations", "gold", "experimental/frontier", "recommendation", "results/tables/cascade_recommendations.csv", "python -m src.compute_aware_cascade", "Deployment-profile recommendation card for gold strategies."),
        ("gold_frontier_report", "gold", "experimental/frontier", "report", "results/figures/cascade_frontier_report.md", "python -m src.compute_aware_cascade --dataset synthetic_split", "Single-entry frontier report that consolidates the current cascade evidence stack."),
        ("synthetic_split_cascade_performance", "synthetic_split", "synthetic/silver", "performance", "results/tables/synthetic_split_cascade_performance.csv", "python -m src.compute_aware_cascade --dataset synthetic_split", "Held-out synthetic split cascade performance table."),
        ("synthetic_split_cascade_summary", "synthetic_split", "synthetic/silver", "summary", "results/figures/synthetic_split_cascade_summary.md", "python -m src.compute_aware_cascade --dataset synthetic_split", "Narrative summary of synthetic split cascade trade-offs."),
        ("synthetic_split_tradeoff_figure", "synthetic_split", "synthetic/silver", "figure", "results/figures/synthetic_split_cer_runtime_tradeoff.png", "python -m src.compute_aware_cascade --dataset synthetic_split", "CER versus compute scatter plot for synthetic split strategies."),
        ("synthetic_split_runtime_audit", "synthetic_split", "synthetic/silver", "audit", "results/tables/synthetic_split_cascade_runtime_audit.csv", "python -m src.compute_aware_cascade --dataset synthetic_split", "Observed-runtime versus proxy-runtime provenance audit for synthetic split selections."),
        ("synthetic_split_runtime_normalization", "synthetic_split", "synthetic/silver", "audit", "results/tables/synthetic_split_cascade_runtime_normalization.csv", "python -m src.compute_aware_cascade --dataset synthetic_split", "Selected-route runtime normalization and RTF audit for synthetic split strategies."),
        ("synthetic_split_pareto", "synthetic_split", "synthetic/silver", "audit", "results/tables/synthetic_split_cascade_pareto.csv", "python -m src.compute_aware_cascade --dataset synthetic_split", "CER/compute Pareto frontier audit for synthetic split strategies."),
        ("synthetic_split_recommendations", "synthetic_split", "synthetic/silver", "recommendation", "results/tables/synthetic_split_cascade_recommendations.csv", "python -m src.compute_aware_cascade --dataset synthetic_split", "Deployment-profile recommendation card for synthetic split strategies."),
        ("cross_dataset_robustness_gap", "cross_dataset", "experimental/frontier", "audit", "results/tables/cascade_robustness_gap.csv", "python -m src.compute_aware_cascade --dataset synthetic_split", "Gold versus synthetic split robustness gap table for shared strategy families."),
        ("cross_dataset_recommendation_stability", "cross_dataset", "experimental/frontier", "audit", "results/tables/cascade_recommendation_stability.csv", "python -m src.compute_aware_cascade --dataset synthetic_split", "Raw strategy recommendation stability across gold and synthetic scopes."),
        ("cross_dataset_family_stability", "cross_dataset", "experimental/frontier", "audit", "results/tables/cascade_recommendation_family_stability.csv", "python -m src.compute_aware_cascade --dataset synthetic_split", "Family-level recommendation stability across gold and synthetic scopes."),
        ("cross_dataset_decision_matrix", "cross_dataset", "experimental/frontier", "report", "results/tables/cascade_decision_matrix.csv", "python -m src.compute_aware_cascade --dataset synthetic_split", "Deployment-facing matrix that merges recommendation and robustness evidence."),
        ("cross_dataset_profile_playbook", "cross_dataset", "experimental/frontier", "report", "results/figures/cascade_profile_playbook.md", "python -m src.compute_aware_cascade --dataset synthetic_split", "Profile-by-profile deployment playbook derived from the cascade decision matrix."),
        ("cross_dataset_benchmark_readiness", "cross_dataset", "experimental/frontier", "report", "results/figures/cascade_benchmark_readiness.md", "python -m src.compute_aware_cascade --dataset synthetic_split", "Priority-ordered readiness scaffold for replacing repository-local timing with controlled benchmark evidence."),
        ("cross_dataset_benchmark_plan", "cross_dataset", "experimental/frontier", "report", "results/figures/cascade_benchmark_plan.md", "python -m src.compute_aware_cascade --dataset synthetic_split", "Staged benchmark handoff plan derived from the readiness scaffold."),
        ("cross_dataset_benchmark_checklist", "cross_dataset", "experimental/frontier", "report", "results/figures/cascade_benchmark_checklist.md", "python -m src.compute_aware_cascade --dataset synthetic_split", "Execution checklist for recording benchmark session metadata and acceptance checks."),
        ("cross_dataset_benchmark_manifest_template", "cross_dataset", "experimental/frontier", "report", "results/tables/cascade_benchmark_manifest_template.csv", "python -m src.compute_aware_cascade --dataset synthetic_split", "Fill-in template for benchmark session metadata captured during controlled timing runs."),
        ("cross_dataset_benchmark_status", "cross_dataset", "experimental/frontier", "report", "results/figures/cascade_benchmark_status.md", "python -m src.compute_aware_cascade --dataset synthetic_split", "Phase-by-phase benchmark status board showing template completeness and pending execution gaps."),
        ("cross_dataset_benchmark_execution_summary", "cross_dataset", "experimental/frontier", "report", "results/figures/cascade_benchmark_execution_summary.md", "python -m src.compute_aware_cascade --dataset synthetic_split", "Execution-summary rollup showing blocker totals, readiness by phase, and recommended next actions."),
        ("cross_dataset_benchmark_execution_queue", "cross_dataset", "experimental/frontier", "report", "results/figures/cascade_benchmark_execution_queue.md", "python -m src.compute_aware_cascade --dataset synthetic_split", "Ordered benchmark execution queue showing which pending step should run or review next."),
        ("cross_dataset_benchmark_handoff_packet", "cross_dataset", "experimental/frontier", "report", "results/figures/cascade_benchmark_handoff_packet.md", "python -m src.compute_aware_cascade --dataset synthetic_split", "Single-entry benchmark handoff packet consolidating readiness, plan, checklist, manifest template, and status board."),
    ]
    rows = [
        {
            "artifact_id": artifact_id,
            "dataset": dataset,
            "label": label,
            "artifact_group": artifact_group,
            "artifact_path": artifact_path,
            "generator_command": generator_command,
            "intended_use": intended_use,
        }
        for artifact_id, dataset, label, artifact_group, artifact_path, generator_command, intended_use in registry
    ]
    return sorted(rows, key=lambda row: (str(row["dataset"]), str(row["artifact_group"]), str(row["artifact_id"])))


def build_artifact_index_lines(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "# Cascade Artifact Index",
        "",
        "This generated index lists the current compute-aware cascade artifacts, labels, and intended entrypoints.",
        "",
    ]
    datasets = sorted({str(row.get("dataset", "")) for row in rows})
    for dataset in datasets:
        lines.extend(
            [
                f"## {dataset}",
                "",
                "| artifact_id | label | artifact_group | artifact_path | generator_command | intended_use |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in rows:
            if str(row.get("dataset", "")) == dataset:
                lines.append(
                    f"| {row['artifact_id']} | {row['label']} | {row['artifact_group']} | {row['artifact_path']} | {row['generator_command']} | {row['intended_use']} |"
                )
        lines.append("")
    return lines


def write_artifact_index_outputs(
    rows: list[dict[str, Any]],
    csv_path: Path,
    json_path: Path,
    summary_path: Path,
) -> None:
    write_csv_json(rows, csv_path, json_path, ARTIFACT_INDEX_COLUMNS)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text("\n".join(build_artifact_index_lines(rows)) + "\n", encoding="utf-8")


def benchmark_priority_rank(priority: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(priority, 9)


def build_benchmark_readiness_rows(artifact_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for artifact in artifact_rows:
        artifact_id = str(artifact.get("artifact_id", ""))
        dataset = str(artifact.get("dataset", ""))
        artifact_group = str(artifact.get("artifact_group", ""))

        if "runtime" in artifact_id:
            priority = "high"
            status = "repo_local_runtime_only"
            readiness_tier = "benchmark_foundation"
            next_step = "Run a controlled same-hardware timing sweep for the selected routes."
        elif artifact_group in {"performance", "figure"}:
            priority = "high"
            status = "repo_local_runtime_only"
            readiness_tier = "benchmark_surface"
            next_step = "Rebuild this artifact after controlled route timing is collected."
        elif dataset == "cross_dataset":
            priority = "medium"
            status = "inherits_repo_local_runtime"
            readiness_tier = "downstream_summary"
            next_step = "Refresh after gold and synthetic controlled benchmark evidence lands."
        elif artifact_group in {"recommendation", "report", "summary"}:
            priority = "medium"
            status = "inherits_repo_local_runtime"
            readiness_tier = "downstream_summary"
            next_step = "Refresh after controlled benchmark evidence replaces repository-local timing."
        else:
            priority = "low"
            status = "reference_only"
            readiness_tier = "registry_support"
            next_step = "Keep as lookup support unless benchmark scope expands."

        rows.append(
            {
                "artifact_id": artifact_id,
                "dataset": dataset,
                "label": artifact.get("label", ""),
                "artifact_group": artifact_group,
                "artifact_path": artifact.get("artifact_path", ""),
                "benchmark_priority": priority,
                "benchmark_priority_rank": benchmark_priority_rank(priority),
                "benchmark_status": status,
                "readiness_tier": readiness_tier,
                "next_evidence_step": next_step,
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            to_int(row.get("benchmark_priority_rank")),
            str(row.get("dataset", "")),
            str(row.get("artifact_id", "")),
        ),
    )


def build_benchmark_readiness_lines(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "# Cascade Benchmark Readiness",
        "",
        "This generated note identifies which cascade artifacts most need controlled hardware/runtime evidence next.",
        "",
    ]
    priorities = ["high", "medium", "low"]
    for priority in priorities:
        scoped_rows = [row for row in rows if str(row.get("benchmark_priority", "")) == priority]
        if not scoped_rows:
            continue
        lines.extend(
            [
                f"## {priority} priority",
                "",
                "| artifact_id | dataset | benchmark_status | readiness_tier | artifact_path | next_evidence_step |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in scoped_rows:
            lines.append(
                f"| {row['artifact_id']} | {row['dataset']} | {row['benchmark_status']} | {row['readiness_tier']} | {row['artifact_path']} | {row['next_evidence_step']} |"
            )
        lines.append("")
    return lines


def write_benchmark_readiness_outputs(
    rows: list[dict[str, Any]],
    csv_path: Path,
    json_path: Path,
    summary_path: Path,
) -> None:
    write_csv_json(rows, csv_path, json_path, BENCHMARK_READINESS_COLUMNS)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text("\n".join(build_benchmark_readiness_lines(rows)) + "\n", encoding="utf-8")


def build_benchmark_plan_rows(readiness_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        {
            "plan_step_id": "phase1_gold_runtime_foundation",
            "step_order": 1,
            "phase": "foundation",
            "dataset_scope": "gold",
            "command": "python -m src.compute_aware_cascade",
            "prerequisite_artifacts": "gold_runtime_audit;gold_runtime_normalization",
            "refreshed_artifacts": "gold_runtime_audit;gold_runtime_normalization",
            "success_signal": "Gold runtime foundation artifacts are rebuilt from controlled timing.",
        },
        {
            "plan_step_id": "phase2_synthetic_runtime_foundation",
            "step_order": 2,
            "phase": "foundation",
            "dataset_scope": "synthetic_split",
            "command": "python -m src.compute_aware_cascade --dataset synthetic_split",
            "prerequisite_artifacts": "synthetic_split_runtime_audit;synthetic_split_runtime_normalization",
            "refreshed_artifacts": "synthetic_split_runtime_audit;synthetic_split_runtime_normalization",
            "success_signal": "Synthetic split runtime foundation artifacts are rebuilt from controlled timing.",
        },
        {
            "plan_step_id": "phase3_gold_surface_refresh",
            "step_order": 3,
            "phase": "surface",
            "dataset_scope": "gold",
            "command": "python -m src.compute_aware_cascade",
            "prerequisite_artifacts": "gold_cascade_performance;gold_tradeoff_figure;gold_cascade_summary;gold_recommendations;gold_frontier_report",
            "refreshed_artifacts": "gold_cascade_performance;gold_tradeoff_figure;gold_cascade_summary;gold_recommendations;gold_frontier_report",
            "success_signal": "Gold surface artifacts are rebuilt from controlled timing-backed inputs.",
        },
        {
            "plan_step_id": "phase4_synthetic_surface_refresh",
            "step_order": 4,
            "phase": "surface",
            "dataset_scope": "synthetic_split",
            "command": "python -m src.compute_aware_cascade --dataset synthetic_split",
            "prerequisite_artifacts": "synthetic_split_cascade_performance;synthetic_split_tradeoff_figure;synthetic_split_cascade_summary;synthetic_split_recommendations",
            "refreshed_artifacts": "synthetic_split_cascade_performance;synthetic_split_tradeoff_figure;synthetic_split_cascade_summary;synthetic_split_recommendations",
            "success_signal": "Synthetic split surface artifacts are rebuilt from controlled timing-backed inputs.",
        },
        {
            "plan_step_id": "phase5_cross_dataset_refresh",
            "step_order": 5,
            "phase": "cross_dataset",
            "dataset_scope": "cross_dataset",
            "command": "python -m src.compute_aware_cascade --dataset synthetic_split",
            "prerequisite_artifacts": "cross_dataset_robustness_gap;cross_dataset_recommendation_stability;cross_dataset_family_stability;cross_dataset_decision_matrix",
            "refreshed_artifacts": "cross_dataset_robustness_gap;cross_dataset_recommendation_stability;cross_dataset_family_stability;cross_dataset_decision_matrix",
            "success_signal": "Cross-dataset decision-support artifacts are rebuilt from controlled timing-backed inputs.",
        },
    ]
    available = {str(row.get("artifact_id", "")) for row in readiness_rows}
    filtered_rows: list[dict[str, Any]] = []
    for row in rows:
        needed = {
            artifact
            for field in ["prerequisite_artifacts", "refreshed_artifacts"]
            for artifact in str(row.get(field, "")).split(";")
            if artifact
        }
        if needed.issubset(available):
            filtered_rows.append(row)
    return sorted(filtered_rows, key=lambda row: to_int(row.get("step_order")))


def build_benchmark_plan_lines(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "# Cascade Benchmark Plan",
        "",
        "This generated handoff plan turns benchmark readiness priorities into a staged execution order.",
        "",
        "| step_order | plan_step_id | phase | dataset_scope | command | prerequisite_artifacts | refreshed_artifacts | success_signal |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['step_order']} | {row['plan_step_id']} | {row['phase']} | {row['dataset_scope']} | {row['command']} | "
            f"{row['prerequisite_artifacts']} | {row['refreshed_artifacts']} | {row['success_signal']} |"
        )
    return lines


def write_benchmark_plan_outputs(
    rows: list[dict[str, Any]],
    csv_path: Path,
    json_path: Path,
    summary_path: Path,
) -> None:
    write_csv_json(rows, csv_path, json_path, BENCHMARK_PLAN_COLUMNS)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text("\n".join(build_benchmark_plan_lines(rows)) + "\n", encoding="utf-8")


def build_profile_playbook_rows(decision_matrix_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in decision_matrix_rows:
        profile = str(row.get("profile", ""))
        family_strategy = str(row.get("family_most_common_strategy", ""))
        gold_strategy = str(row.get("gold_recommended_strategy", ""))
        synthetic_strategy = str(row.get("synthetic_all_recommended_strategy", ""))
        robustness_rank = to_int(row.get("robustness_rank"))
        consensus_ratio = to_float(row.get("family_consensus_ratio"))
        synthetic_cost = to_float(row.get("synthetic_all_average_compute_cost"))

        if profile == "balanced":
            default_role = "default"
            when_to_use = "Use when you want the cleanest default operating point across scopes and a stable router-family recommendation around router_v2."
            avoid_when = "Avoid when your main requirement is either the absolute lowest held-out CER or the lowest compute floor."
            tradeoff_summary = (
                f"Stable family-level default around `{family_strategy}` with consensus {consensus_ratio} and lower synthetic cost "
                "than accuracy_first."
            )
        elif profile == "accuracy_first":
            default_role = "robust_accuracy"
            when_to_use = "Use when held-out robustness and stronger accuracy-biased recovery matter more than compute simplicity."
            avoid_when = "Avoid when you need the cheapest operating mode or a perfectly stable family recommendation across scopes."
            tradeoff_summary = (
                f"Best accuracy-biased option with lowest shared robustness rank {robustness_rank}, but it shifts from `{gold_strategy}` "
                f"on gold to `{synthetic_strategy}` on held-out synthetic split."
            )
        else:
            default_role = "budget_floor"
            when_to_use = "Use when compute cost is the primary constraint and you want the most stable cost-first recommendation."
            avoid_when = "Avoid when moderate or heavy overlap accuracy matters more than cost floor."
            tradeoff_summary = (
                f"Cheapest stable profile built around `{family_strategy}` with synthetic compute cost {synthetic_cost}, but it carries the weakest CER."
            )

        rows.append(
            {
                "profile": profile,
                "default_role": default_role,
                "family_strategy": family_strategy,
                "gold_strategy": gold_strategy,
                "synthetic_strategy": synthetic_strategy,
                "when_to_use": when_to_use,
                "avoid_when": avoid_when,
                "tradeoff_summary": tradeoff_summary,
            }
        )
    return sorted(rows, key=lambda row: str(row.get("profile", "")))


def build_profile_playbook_lines(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "# Cascade Profile Playbook",
        "",
        "This generated playbook turns the cascade profile recommendations into deployment-facing guidance.",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## {row['profile']}",
                "",
                f"- role: `{row['default_role']}`",
                f"- family_strategy: `{row['family_strategy']}`",
                f"- gold_strategy: `{row['gold_strategy']}`",
                f"- synthetic_strategy: `{row['synthetic_strategy']}`",
                f"- when_to_use: {row['when_to_use']}",
                f"- avoid_when: {row['avoid_when']}",
                f"- tradeoff_summary: {row['tradeoff_summary']}",
                "",
            ]
        )
    return lines


def write_profile_playbook_outputs(
    rows: list[dict[str, Any]],
    csv_path: Path,
    json_path: Path,
    summary_path: Path,
) -> None:
    write_csv_json(rows, csv_path, json_path, PROFILE_PLAYBOOK_COLUMNS)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text("\n".join(build_profile_playbook_lines(rows)) + "\n", encoding="utf-8")


def build_benchmark_checklist_rows(plan_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in plan_rows:
        phase = str(row.get("phase", ""))
        if phase == "foundation":
            session_type = "timing_capture"
            required_metadata = "hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes"
        elif phase == "surface":
            session_type = "artifact_refresh"
            required_metadata = "source_timing_manifest;refresh_command;diff_review_notes"
        else:
            session_type = "derived_refresh"
            required_metadata = "source_timing_manifest;cross_dataset_scope;refresh_command;consistency_notes"

        rows.append(
            {
                "plan_step_id": row.get("plan_step_id", ""),
                "step_order": row.get("step_order", ""),
                "phase": phase,
                "dataset_scope": row.get("dataset_scope", ""),
                "command": row.get("command", ""),
                "session_type": session_type,
                "required_metadata": required_metadata,
                "acceptance_check": row.get("success_signal", ""),
            }
        )
    return sorted(rows, key=lambda row: to_int(row.get("step_order")))


def build_benchmark_checklist_lines(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "# Cascade Benchmark Checklist",
        "",
        "This generated checklist records the metadata and acceptance checks required for each benchmark handoff step.",
        "",
        "| step_order | plan_step_id | phase | dataset_scope | command | session_type | required_metadata | acceptance_check |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['step_order']} | {row['plan_step_id']} | {row['phase']} | {row['dataset_scope']} | {row['command']} | "
            f"{row['session_type']} | {row['required_metadata']} | {row['acceptance_check']} |"
        )
    return lines


def write_benchmark_checklist_outputs(
    rows: list[dict[str, Any]],
    csv_path: Path,
    json_path: Path,
    summary_path: Path,
) -> None:
    write_csv_json(rows, csv_path, json_path, BENCHMARK_CHECKLIST_COLUMNS)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text("\n".join(build_benchmark_checklist_lines(rows)) + "\n", encoding="utf-8")


def build_benchmark_manifest_template_rows(checklist_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    template_fields = [
        "hardware_label",
        "device",
        "repeat_count",
        "warmup_count",
        "batch_shape",
        "timing_notes",
        "source_timing_manifest",
        "refresh_command",
        "diff_review_notes",
        "cross_dataset_scope",
        "consistency_notes",
    ]
    rows: list[dict[str, Any]] = []
    for row in checklist_rows:
        template = {field: "" for field in template_fields}
        for field in str(row.get("required_metadata", "")).split(";"):
            key = field.strip()
            if key in template:
                template[key] = "TODO"
        rows.append(
            {
                "plan_step_id": row.get("plan_step_id", ""),
                "step_order": row.get("step_order", ""),
                "phase": row.get("phase", ""),
                "dataset_scope": row.get("dataset_scope", ""),
                "session_type": row.get("session_type", ""),
                "command": row.get("command", ""),
                "acceptance_check": row.get("acceptance_check", ""),
                **template,
            }
        )
    return sorted(rows, key=lambda row: to_int(row.get("step_order")))


def write_benchmark_manifest_template_outputs(
    rows: list[dict[str, Any]],
    csv_path: Path,
    json_path: Path,
) -> None:
    write_csv_json(rows, csv_path, json_path, BENCHMARK_MANIFEST_TEMPLATE_COLUMNS)


def build_benchmark_status_lines(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "# Cascade Benchmark Status Board",
        "",
        "This generated status board tracks which benchmark handoff phases are still template-only and what evidence is missing next.",
        "",
        "| step_order | plan_step_id | phase | dataset_scope | execution_status | readiness_signal | pending_field_count | blocking_category | next_action | missing_fields | acceptance_check |",
        "| ---: | --- | --- | --- | --- | --- | ---: | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['step_order']} | {row['plan_step_id']} | {row['phase']} | {row['dataset_scope']} | "
            f"{row['execution_status']} | {row['readiness_signal']} | {row['pending_field_count']} | {row['blocking_category']} | "
            f"{row['next_action']} | {row['missing_fields']} | {row['acceptance_check']} |"
        )
    return lines


def write_benchmark_status_outputs(
    rows: list[dict[str, Any]],
    csv_path: Path,
    json_path: Path,
    summary_path: Path,
) -> None:
    write_csv_json(rows, csv_path, json_path, BENCHMARK_STATUS_COLUMNS)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text("\n".join(build_benchmark_status_lines(rows)) + "\n", encoding="utf-8")


def set_pixel(pixels: bytearray, width: int, height: int, x: int, y: int, color: tuple[int, int, int]) -> None:
    if 0 <= x < width and 0 <= y < height:
        idx = (y * width + x) * 3
        pixels[idx : idx + 3] = bytes(color)


def draw_line(
    pixels: bytearray,
    width: int,
    height: int,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    color: tuple[int, int, int],
) -> None:
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        set_pixel(pixels, width, height, x0, y0, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def draw_circle(
    pixels: bytearray,
    width: int,
    height: int,
    cx: int,
    cy: int,
    radius: int,
    color: tuple[int, int, int],
) -> None:
    for y in range(cy - radius, cy + radius + 1):
        for x in range(cx - radius, cx + radius + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= radius**2:
                set_pixel(pixels, width, height, x, y, color)


def write_fallback_png(path: Path, rows: list[dict[str, Any]]) -> None:
    width, height = 900, 550
    pixels = bytearray(b"\xff\xff\xff" * width * height)
    left, right, top, bottom = 90, 40, 40, 80
    plot_w = width - left - right
    plot_h = height - top - bottom
    axis_color = (45, 45, 45)
    grid_color = (225, 225, 225)
    point_color = (47, 111, 143)

    x_values = [to_float(row["average_compute_cost"]) for row in rows]
    y_values = [to_float(row["average_cer"]) for row in rows]
    x_min, x_max = min(x_values or [0.0]), max(x_values or [1.0])
    y_min, y_max = min(y_values or [0.0]), max(y_values or [1.0])
    if x_min == x_max:
        x_min -= 1.0
        x_max += 1.0
    if y_min == y_max:
        y_min -= 0.1
        y_max += 0.1
    x_pad = (x_max - x_min) * 0.08
    y_pad = (y_max - y_min) * 0.08
    x_min -= x_pad
    x_max += x_pad
    y_min -= y_pad
    y_max += y_pad

    for tick in range(6):
        x = left + round(plot_w * tick / 5)
        y = top + round(plot_h * tick / 5)
        draw_line(pixels, width, height, x, top, x, top + plot_h, grid_color)
        draw_line(pixels, width, height, left, y, left + plot_w, y, grid_color)
    draw_line(pixels, width, height, left, top, left, top + plot_h, axis_color)
    draw_line(pixels, width, height, left, top + plot_h, left + plot_w, top + plot_h, axis_color)

    for row in rows:
        x_value = to_float(row["average_compute_cost"])
        y_value = to_float(row["average_cer"])
        x = left + round((x_value - x_min) / (x_max - x_min) * plot_w)
        y = top + plot_h - round((y_value - y_min) / (y_max - y_min) * plot_h)
        draw_circle(pixels, width, height, x, y, 7, point_color)
        draw_circle(pixels, width, height, x, y, 3, (255, 255, 255))

    raw_rows = []
    for y in range(height):
        start = y * width * 3
        raw_rows.append(b"\x00" + bytes(pixels[start : start + width * 3]))
    compressed = zlib.compress(b"".join(raw_rows))

    def chunk(kind: bytes, data: bytes) -> bytes:
        payload = kind + data
        return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", compressed)
        + chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def render_tradeoff_figure(rows: list[dict[str, Any]], output_path: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        write_fallback_png(output_path, rows)
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    x_values = [to_float(row["average_compute_cost"]) for row in rows]
    y_values = [to_float(row["average_cer"]) for row in rows]
    ax.scatter(x_values, y_values, color="#2f6f8f", s=80)
    for row, x_value, y_value in zip(rows, x_values, y_values):
        ax.annotate(str(row["strategy"]), (x_value, y_value), textcoords="offset points", xytext=(6, 5), fontsize=8)
    ax.set_xlabel("Average compute cost (observed runtime or proxy)")
    ax.set_ylabel("Average CER")
    ax.set_title("Compute-aware cascade trade-off")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def write_runtime_audit_outputs(
    rows: list[dict[str, Any]],
    csv_path: Path,
    json_path: Path,
    summary_path: Path,
) -> None:
    write_csv_json(rows, csv_path, json_path, RUNTIME_AUDIT_COLUMNS)
    render_runtime_audit_summary(rows, summary_path)


def write_runtime_normalization_outputs(
    rows: list[dict[str, Any]],
    csv_path: Path,
    json_path: Path,
    summary_path: Path,
) -> None:
    write_csv_json(rows, csv_path, json_path, RUNTIME_NORMALIZATION_COLUMNS)
    render_runtime_normalization_summary(rows, summary_path)


def main() -> None:
    args = parse_args()
    wrote_profile_playbook = False
    artifact_index_rows = build_artifact_index_rows()
    benchmark_readiness_rows = build_benchmark_readiness_rows(artifact_index_rows)
    benchmark_plan_rows = build_benchmark_plan_rows(benchmark_readiness_rows)
    artifact_index_csv = PROJECT_ROOT / "results" / "tables" / "cascade_artifact_index.csv"
    artifact_index_json = PROJECT_ROOT / "results" / "tables" / "cascade_artifact_index.json"
    artifact_index_md = PROJECT_ROOT / "results" / "figures" / "cascade_artifact_index.md"
    benchmark_readiness_csv = PROJECT_ROOT / "results" / "tables" / "cascade_benchmark_readiness.csv"
    benchmark_readiness_json = PROJECT_ROOT / "results" / "tables" / "cascade_benchmark_readiness.json"
    benchmark_readiness_md = PROJECT_ROOT / "results" / "figures" / "cascade_benchmark_readiness.md"
    benchmark_plan_csv = PROJECT_ROOT / "results" / "tables" / "cascade_benchmark_plan.csv"
    benchmark_plan_json = PROJECT_ROOT / "results" / "tables" / "cascade_benchmark_plan.json"
    benchmark_plan_md = PROJECT_ROOT / "results" / "figures" / "cascade_benchmark_plan.md"
    benchmark_checklist_rows = build_benchmark_checklist_rows(benchmark_plan_rows)
    benchmark_checklist_csv = PROJECT_ROOT / "results" / "tables" / "cascade_benchmark_checklist.csv"
    benchmark_checklist_json = PROJECT_ROOT / "results" / "tables" / "cascade_benchmark_checklist.json"
    benchmark_checklist_md = PROJECT_ROOT / "results" / "figures" / "cascade_benchmark_checklist.md"
    benchmark_manifest_template_rows = build_benchmark_manifest_template_rows(benchmark_checklist_rows)
    benchmark_manifest_template_csv = PROJECT_ROOT / "results" / "tables" / "cascade_benchmark_manifest_template.csv"
    benchmark_manifest_template_json = PROJECT_ROOT / "results" / "tables" / "cascade_benchmark_manifest_template.json"
    benchmark_status_rows = build_benchmark_status_rows(benchmark_manifest_template_rows)
    benchmark_status_csv = PROJECT_ROOT / "results" / "tables" / "cascade_benchmark_status.csv"
    benchmark_status_json = PROJECT_ROOT / "results" / "tables" / "cascade_benchmark_status.json"
    benchmark_status_md = PROJECT_ROOT / "results" / "figures" / "cascade_benchmark_status.md"
    benchmark_execution_summary_rows = build_benchmark_execution_summary_rows(benchmark_status_rows)
    benchmark_execution_summary_csv = PROJECT_ROOT / "results" / "tables" / "cascade_benchmark_execution_summary.csv"
    benchmark_execution_summary_json = PROJECT_ROOT / "results" / "tables" / "cascade_benchmark_execution_summary.json"
    benchmark_execution_summary_md = PROJECT_ROOT / "results" / "figures" / "cascade_benchmark_execution_summary.md"
    benchmark_execution_queue_rows = build_benchmark_execution_queue_rows(benchmark_status_rows)
    benchmark_execution_queue_csv = PROJECT_ROOT / "results" / "tables" / "cascade_benchmark_execution_queue.csv"
    benchmark_execution_queue_json = PROJECT_ROOT / "results" / "tables" / "cascade_benchmark_execution_queue.json"
    benchmark_execution_queue_md = PROJECT_ROOT / "results" / "figures" / "cascade_benchmark_execution_queue.md"
    benchmark_packet_md = PROJECT_ROOT / "results" / "figures" / "cascade_benchmark_handoff_packet.md"
    profile_playbook_csv = PROJECT_ROOT / "results" / "tables" / "cascade_profile_playbook.csv"
    profile_playbook_json = PROJECT_ROOT / "results" / "tables" / "cascade_profile_playbook.json"
    profile_playbook_md = PROJECT_ROOT / "results" / "figures" / "cascade_profile_playbook.md"
    if args.dataset == "synthetic_split":
        cases = load_synthetic_split_cases()
        decisions = load_synthetic_split_decisions()
        runtime_lookup = load_synthetic_split_runtime_lookup()
        rows = build_synthetic_scope_rows(
            cases,
            decisions,
            load_synthetic_split_cer_lookup(),
            runtime_lookup,
        )
        table_csv = PROJECT_ROOT / "results" / "tables" / "synthetic_split_cascade_performance.csv"
        table_json = PROJECT_ROOT / "results" / "tables" / "synthetic_split_cascade_performance.json"
        figure_path = PROJECT_ROOT / "results" / "figures" / "synthetic_split_cer_runtime_tradeoff.png"
        summary_path = PROJECT_ROOT / "results" / "figures" / "synthetic_split_cascade_summary.md"
        runtime_audit_csv = PROJECT_ROOT / "results" / "tables" / "synthetic_split_cascade_runtime_audit.csv"
        runtime_audit_json = PROJECT_ROOT / "results" / "tables" / "synthetic_split_cascade_runtime_audit.json"
        runtime_audit_md = PROJECT_ROOT / "results" / "figures" / "synthetic_split_cascade_runtime_audit.md"
        runtime_norm_csv = PROJECT_ROOT / "results" / "tables" / "synthetic_split_cascade_runtime_normalization.csv"
        runtime_norm_json = PROJECT_ROOT / "results" / "tables" / "synthetic_split_cascade_runtime_normalization.json"
        runtime_norm_md = PROJECT_ROOT / "results" / "figures" / "synthetic_split_cascade_runtime_normalization.md"
        pareto_csv = PROJECT_ROOT / "results" / "tables" / "synthetic_split_cascade_pareto.csv"
        pareto_json = PROJECT_ROOT / "results" / "tables" / "synthetic_split_cascade_pareto.json"
        pareto_md = PROJECT_ROOT / "results" / "figures" / "synthetic_split_cascade_pareto.md"
        recommendation_csv = PROJECT_ROOT / "results" / "tables" / "synthetic_split_cascade_recommendations.csv"
        recommendation_json = PROJECT_ROOT / "results" / "tables" / "synthetic_split_cascade_recommendations.json"
        recommendation_md = PROJECT_ROOT / "results" / "figures" / "synthetic_split_cascade_recommendations.md"

        write_csv_json(rows, table_csv, table_json, SYNTHETIC_PERFORMANCE_COLUMNS)
        render_tradeoff_figure([row for row in rows if str(row["scope"]) == "ALL"], figure_path)
        render_synthetic_summary(rows, summary_path, figure_path)
        runtime_rows: list[dict[str, Any]] = []
        runtime_rows.extend(
            summarize_runtime_sources(
                cases,
                SYNTHETIC_STRATEGIES,
                decisions,
                runtime_lookup,
                scope="ALL",
                dataset_label="synthetic_split",
            )
        )
        for split in sorted({str(case.get("split", "")).strip() for case in cases if str(case.get("split", "")).strip()}):
            runtime_rows.extend(
                summarize_runtime_sources(
                    [case for case in cases if str(case.get("split", "")).strip() == split],
                    SYNTHETIC_STRATEGIES,
                    decisions,
                    runtime_lookup,
                    scope=split.upper(),
                    dataset_label="synthetic_split",
                )
            )
        write_runtime_audit_outputs(runtime_rows, runtime_audit_csv, runtime_audit_json, runtime_audit_md)
        duration_lookup = load_synthetic_split_duration_lookup()
        runtime_norm_rows: list[dict[str, Any]] = []
        runtime_norm_rows.extend(
            summarize_runtime_normalization(
                cases,
                SYNTHETIC_STRATEGIES,
                decisions,
                runtime_lookup,
                duration_lookup,
                scope="ALL",
                dataset_label="synthetic_split",
            )
        )
        for split in sorted({str(case.get("split", "")).strip() for case in cases if str(case.get("split", "")).strip()}):
            runtime_norm_rows.extend(
                summarize_runtime_normalization(
                    [case for case in cases if str(case.get("split", "")).strip() == split],
                    SYNTHETIC_STRATEGIES,
                    decisions,
                    runtime_lookup,
                    duration_lookup,
                    scope=split.upper(),
                    dataset_label="synthetic_split",
                )
            )
        write_runtime_normalization_outputs(runtime_norm_rows, runtime_norm_csv, runtime_norm_json, runtime_norm_md)
        pareto_rows = build_pareto_rows(
            [row for row in rows if str(row.get("scope", "")) in {"ALL", "DEV", "TEST"}],
            runtime_norm_rows,
            dataset_label="synthetic_split",
        )
        write_pareto_outputs(pareto_rows, pareto_csv, pareto_json, pareto_md)
        recommendation_rows = build_recommendation_rows(pareto_rows)
        write_recommendation_outputs(recommendation_rows, recommendation_csv, recommendation_json, recommendation_md)

        gold_rows = build_strategy_rows(load_gold_cases(), load_decisions(), load_cer_lookup(), load_runtime_lookup())
        gold_runtime_norm_rows = summarize_runtime_normalization(
            load_gold_cases(),
            STRATEGIES,
            load_decisions(),
            load_runtime_lookup(),
            load_gold_duration_lookup(),
            scope="ALL",
            dataset_label="gold",
        )
        gold_performance_rows = [dict(row, scope="ALL") for row in gold_rows]
        gold_pareto_rows = build_pareto_rows(gold_performance_rows, gold_runtime_norm_rows, dataset_label="gold")
        robustness_rows = build_robustness_gap_rows(gold_pareto_rows, pareto_rows)
        write_robustness_gap_outputs(
            robustness_rows,
            PROJECT_ROOT / "results" / "tables" / "cascade_robustness_gap.csv",
            PROJECT_ROOT / "results" / "tables" / "cascade_robustness_gap.json",
            PROJECT_ROOT / "results" / "figures" / "cascade_robustness_gap.md",
        )
        gold_recommendation_rows = build_recommendation_rows(gold_pareto_rows)
        stability_rows = build_recommendation_stability_rows(gold_recommendation_rows + recommendation_rows)
        write_recommendation_stability_outputs(
            stability_rows,
            PROJECT_ROOT / "results" / "tables" / "cascade_recommendation_stability.csv",
            PROJECT_ROOT / "results" / "tables" / "cascade_recommendation_stability.json",
            PROJECT_ROOT / "results" / "figures" / "cascade_recommendation_stability.md",
        )
        family_stability_rows = build_recommendation_family_stability_rows(gold_recommendation_rows + recommendation_rows)
        write_recommendation_family_stability_outputs(
            family_stability_rows,
            PROJECT_ROOT / "results" / "tables" / "cascade_recommendation_family_stability.csv",
            PROJECT_ROOT / "results" / "tables" / "cascade_recommendation_family_stability.json",
            PROJECT_ROOT / "results" / "figures" / "cascade_recommendation_family_stability.md",
        )
        decision_matrix_rows = build_decision_matrix_rows(
            gold_recommendation_rows,
            recommendation_rows,
            family_stability_rows,
            robustness_rows,
        )
        write_decision_matrix_outputs(
            decision_matrix_rows,
            PROJECT_ROOT / "results" / "tables" / "cascade_decision_matrix.csv",
            PROJECT_ROOT / "results" / "tables" / "cascade_decision_matrix.json",
            PROJECT_ROOT / "results" / "figures" / "cascade_decision_matrix.md",
        )
        write_frontier_report(
            decision_matrix_rows,
            family_stability_rows,
            robustness_rows,
            PROJECT_ROOT / "results" / "figures" / "cascade_frontier_report.md",
        )
        write_artifact_index_outputs(artifact_index_rows, artifact_index_csv, artifact_index_json, artifact_index_md)
        write_benchmark_readiness_outputs(
            benchmark_readiness_rows,
            benchmark_readiness_csv,
            benchmark_readiness_json,
            benchmark_readiness_md,
        )
        write_benchmark_plan_outputs(
            benchmark_plan_rows,
            benchmark_plan_csv,
            benchmark_plan_json,
            benchmark_plan_md,
        )
        write_benchmark_checklist_outputs(
            benchmark_checklist_rows,
            benchmark_checklist_csv,
            benchmark_checklist_json,
            benchmark_checklist_md,
        )
        write_benchmark_manifest_template_outputs(
            benchmark_manifest_template_rows,
            benchmark_manifest_template_csv,
            benchmark_manifest_template_json,
        )
        write_benchmark_status_outputs(
            benchmark_status_rows,
            benchmark_status_csv,
            benchmark_status_json,
            benchmark_status_md,
        )
        write_benchmark_execution_summary_outputs(
            benchmark_execution_summary_rows,
            benchmark_execution_summary_csv,
            benchmark_execution_summary_json,
            benchmark_execution_summary_md,
        )
        write_benchmark_execution_queue_outputs(
            benchmark_execution_queue_rows,
            benchmark_execution_queue_csv,
            benchmark_execution_queue_json,
            benchmark_execution_queue_md,
        )
        write_benchmark_packet_output(
            benchmark_readiness_rows,
            benchmark_plan_rows,
            benchmark_checklist_rows,
            benchmark_manifest_template_rows,
            benchmark_status_rows,
            benchmark_execution_summary_rows,
            benchmark_execution_queue_rows,
            benchmark_packet_md,
        )
        profile_playbook_rows = build_profile_playbook_rows(decision_matrix_rows)
        write_profile_playbook_outputs(
            profile_playbook_rows,
            profile_playbook_csv,
            profile_playbook_json,
            profile_playbook_md,
        )
        wrote_profile_playbook = True
    else:
        cases = load_gold_cases()
        decisions = load_decisions()
        runtime_lookup = load_runtime_lookup()
        rows = build_strategy_rows(cases, decisions, load_cer_lookup(), runtime_lookup)
        table_csv = PROJECT_ROOT / "results" / "tables" / "cascade_performance.csv"
        table_json = PROJECT_ROOT / "results" / "tables" / "cascade_performance.json"
        figure_path = PROJECT_ROOT / "results" / "figures" / "cer_runtime_tradeoff.png"
        summary_path = PROJECT_ROOT / "results" / "figures" / "compute_aware_cascade_summary.md"
        runtime_audit_csv = PROJECT_ROOT / "results" / "tables" / "cascade_runtime_audit.csv"
        runtime_audit_json = PROJECT_ROOT / "results" / "tables" / "cascade_runtime_audit.json"
        runtime_audit_md = PROJECT_ROOT / "results" / "figures" / "cascade_runtime_audit.md"
        runtime_norm_csv = PROJECT_ROOT / "results" / "tables" / "cascade_runtime_normalization.csv"
        runtime_norm_json = PROJECT_ROOT / "results" / "tables" / "cascade_runtime_normalization.json"
        runtime_norm_md = PROJECT_ROOT / "results" / "figures" / "cascade_runtime_normalization.md"
        pareto_csv = PROJECT_ROOT / "results" / "tables" / "cascade_pareto.csv"
        pareto_json = PROJECT_ROOT / "results" / "tables" / "cascade_pareto.json"
        pareto_md = PROJECT_ROOT / "results" / "figures" / "cascade_pareto.md"
        recommendation_csv = PROJECT_ROOT / "results" / "tables" / "cascade_recommendations.csv"
        recommendation_json = PROJECT_ROOT / "results" / "tables" / "cascade_recommendations.json"
        recommendation_md = PROJECT_ROOT / "results" / "figures" / "cascade_recommendations.md"

        write_csv_json(rows, table_csv, table_json, PERFORMANCE_COLUMNS)
        render_tradeoff_figure(rows, figure_path)
        render_summary(rows, summary_path, figure_path)
        runtime_rows = summarize_runtime_sources(
            cases,
            STRATEGIES,
            decisions,
            runtime_lookup,
            scope="ALL",
            dataset_label="gold",
        )
        write_runtime_audit_outputs(runtime_rows, runtime_audit_csv, runtime_audit_json, runtime_audit_md)
        runtime_norm_rows = summarize_runtime_normalization(
            cases,
            STRATEGIES,
            decisions,
            runtime_lookup,
            load_gold_duration_lookup(),
            scope="ALL",
            dataset_label="gold",
        )
        write_runtime_normalization_outputs(runtime_norm_rows, runtime_norm_csv, runtime_norm_json, runtime_norm_md)
        gold_performance_rows = [dict(row, scope="ALL") for row in rows]
        pareto_rows = build_pareto_rows(gold_performance_rows, runtime_norm_rows, dataset_label="gold")
        write_pareto_outputs(pareto_rows, pareto_csv, pareto_json, pareto_md)
        recommendation_rows = build_recommendation_rows(pareto_rows)
        write_recommendation_outputs(recommendation_rows, recommendation_csv, recommendation_json, recommendation_md)
        write_artifact_index_outputs(artifact_index_rows, artifact_index_csv, artifact_index_json, artifact_index_md)
        write_benchmark_readiness_outputs(
            benchmark_readiness_rows,
            benchmark_readiness_csv,
            benchmark_readiness_json,
            benchmark_readiness_md,
        )
        write_benchmark_plan_outputs(
            benchmark_plan_rows,
            benchmark_plan_csv,
            benchmark_plan_json,
            benchmark_plan_md,
        )

    print(f"Wrote cascade performance: {table_csv.relative_to(PROJECT_ROOT)}")
    print(f"Wrote cascade JSON: {table_json.relative_to(PROJECT_ROOT)}")
    print(f"Wrote cascade figure: {figure_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote cascade summary: {summary_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote cascade artifact index: {artifact_index_csv.relative_to(PROJECT_ROOT)}")
    print(f"Wrote cascade benchmark readiness: {benchmark_readiness_csv.relative_to(PROJECT_ROOT)}")
    print(f"Wrote cascade benchmark plan: {benchmark_plan_csv.relative_to(PROJECT_ROOT)}")
    print(f"Wrote cascade benchmark checklist: {benchmark_checklist_csv.relative_to(PROJECT_ROOT)}")
    print(f"Wrote cascade benchmark manifest template: {benchmark_manifest_template_csv.relative_to(PROJECT_ROOT)}")
    print(f"Wrote cascade benchmark status: {benchmark_status_csv.relative_to(PROJECT_ROOT)}")
    print(f"Wrote cascade benchmark execution summary: {benchmark_execution_summary_csv.relative_to(PROJECT_ROOT)}")
    print(f"Wrote cascade benchmark execution queue: {benchmark_execution_queue_csv.relative_to(PROJECT_ROOT)}")
    print(f"Wrote cascade benchmark handoff packet: {benchmark_packet_md.relative_to(PROJECT_ROOT)}")
    if wrote_profile_playbook:
        print(f"Wrote cascade profile playbook: {profile_playbook_csv.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
