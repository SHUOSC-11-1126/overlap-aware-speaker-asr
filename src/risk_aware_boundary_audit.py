from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config
from .router_boundary_alignment import pick_oracle_method, prefers_separation_route
from .separation_phase_diagram import GOLD_CASE_TIER_ANCHOR, compute_delta_cer

AUDIT_COLUMNS = [
    "case_id",
    "overlap_ratio_anchor",
    "base_router_method",
    "final_selected_method",
    "risk_level",
    "oracle_method",
    "mixed_cer",
    "separated_cer",
    "separated_cleaned_cer",
    "selected_cer",
    "oracle_cer",
    "delta_cer_separated",
    "separation_helps",
    "prefers_separation_route",
    "selector_matches_oracle",
    "selector_aligns_with_phase",
    "selector_regret_cer",
    "risk_layer_changed_method",
    "recommended_action",
]

SUMMARY_COLUMNS = [
    "metric",
    "value",
    "label",
]


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


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


def build_cer_by_case() -> dict[str, dict[str, float]]:
    grouped: dict[str, dict[str, float]] = {}
    for row in read_csv_rows(PROJECT_ROOT / "results" / "tables" / "cer_results.csv"):
        case_id = str(row.get("case_id", ""))
        method = str(row.get("method", ""))
        cer = to_float(row.get("cer"))
        if case_id and method and cer is not None:
            grouped.setdefault(case_id, {})[method] = cer
    return grouped


def build_audit_rows(
    risk_rows: list[dict[str, Any]],
    cer_by_case: dict[str, dict[str, float]],
) -> list[dict[str, Any]]:
    audit_rows: list[dict[str, Any]] = []
    for risk in risk_rows:
        case_id = str(risk.get("case_id", ""))
        methods = cer_by_case.get(case_id, {})
        mixed = methods.get("mixed_whisper")
        separated = methods.get("separated_whisper")
        cleaned = methods.get("separated_whisper_cleaned")
        if not case_id or mixed is None or separated is None:
            continue

        available = {
            name: value
            for name, value in [
                ("mixed_whisper", mixed),
                ("separated_whisper", separated),
                ("separated_whisper_cleaned", cleaned),
            ]
            if value is not None
        }
        oracle_method, oracle_cer = pick_oracle_method(available)
        base_method = str(risk.get("base_router_method", ""))
        final_method = str(risk.get("final_selected_method", ""))
        selected_cer = available.get(final_method, oracle_cer)
        delta_sep = compute_delta_cer(mixed, separated)
        separation_helps = delta_sep < 0
        prefers_sep = prefers_separation_route(final_method)
        _, anchor_ratio = GOLD_CASE_TIER_ANCHOR.get(case_id, ("", 0.0))

        audit_rows.append(
            {
                "case_id": case_id,
                "overlap_ratio_anchor": anchor_ratio,
                "base_router_method": base_method,
                "final_selected_method": final_method,
                "risk_level": str(risk.get("risk_level", "")),
                "oracle_method": oracle_method,
                "mixed_cer": mixed,
                "separated_cer": separated,
                "separated_cleaned_cer": cleaned if cleaned is not None else "",
                "selected_cer": selected_cer,
                "oracle_cer": oracle_cer,
                "delta_cer_separated": delta_sep,
                "separation_helps": separation_helps,
                "prefers_separation_route": prefers_sep,
                "selector_matches_oracle": final_method == oracle_method,
                "selector_aligns_with_phase": prefers_sep == separation_helps,
                "selector_regret_cer": round(selected_cer - oracle_cer, 6),
                "risk_layer_changed_method": base_method != final_method,
                "recommended_action": str(risk.get("recommended_action", "")),
            }
        )
    return sorted(audit_rows, key=lambda row: str(row["case_id"]))


def build_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    if not rows:
        return []
    count = len(rows)
    oracle_matches = sum(1 for row in rows if row["selector_matches_oracle"])
    phase_aligned = sum(1 for row in rows if row["selector_aligns_with_phase"])
    risk_changed = sum(1 for row in rows if row["risk_layer_changed_method"])
    avg_regret = round(sum(float(row["selector_regret_cer"]) for row in rows) / count, 6)
    return [
        {"metric": "gold_case_count", "value": str(count), "label": "stable/gold"},
        {
            "metric": "selector_oracle_match_rate",
            "value": str(round(oracle_matches / count, 4)),
            "label": "experimental/frontier",
        },
        {
            "metric": "selector_phase_alignment_rate",
            "value": str(round(phase_aligned / count, 4)),
            "label": "experimental/frontier",
        },
        {
            "metric": "risk_layer_override_rate",
            "value": str(round(risk_changed / count, 4)),
            "label": "experimental/frontier",
        },
        {"metric": "average_selector_regret_cer", "value": str(avg_regret), "label": "experimental/frontier"},
    ]


def build_summary_lines(
    audit_rows: list[dict[str, Any]],
    summary_rows: list[dict[str, str]],
) -> list[str]:
    lines = [
        "# Risk-aware Boundary Audit (experimental/frontier)",
        "",
        "Label: `experimental/frontier` — audits the reference-free risk-aware selector",
        "against gold separation phase boundaries. Does not modify verified references.",
        "",
        "## Summary",
        "",
        "| metric | value | label |",
        "| --- | ---: | --- |",
    ]
    for row in summary_rows:
        lines.append(f"| {row['metric']} | {row['value']} | {row['label']} |")
    lines.extend(
        [
            "",
            "## Per-case Audit",
            "",
            "| case_id | final_method | oracle | risk_level | phase_aligned | regret_cer | risk_changed |",
            "| --- | --- | --- | --- | --- | ---: | --- |",
        ]
    )
    for row in audit_rows:
        lines.append(
            f"| {row['case_id']} | {row['final_selected_method']} | {row['oracle_method']} | "
            f"{row['risk_level']} | {row['selector_aligns_with_phase']} | {row['selector_regret_cer']} | "
            f"{row['risk_layer_changed_method']} |"
        )
    return lines


def build_audit_report() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    risk_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "risk_aware_selection.csv")
    audit_rows = build_audit_rows(risk_rows, build_cer_by_case())
    return audit_rows, build_summary_rows(audit_rows)


def write_outputs(
    audit_rows: list[dict[str, Any]],
    summary_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    table_dir = PROJECT_ROOT / "results" / "tables"
    figure_dir = PROJECT_ROOT / "results" / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    csv_path = table_dir / "risk_aware_boundary_audit.csv"
    json_path = table_dir / "risk_aware_boundary_audit.json"
    summary_csv_path = table_dir / "risk_aware_boundary_audit_summary.csv"
    summary_json_path = table_dir / "risk_aware_boundary_audit_summary.json"
    md_path = figure_dir / "risk_aware_boundary_audit.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_COLUMNS)
        writer.writeheader()
        writer.writerows(audit_rows)
    json_path.write_text(json.dumps(audit_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    with summary_csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(summary_rows)
    summary_json_path.write_text(
        json.dumps(summary_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_path.write_text("\n".join(build_summary_lines(audit_rows, summary_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, summary_csv_path, summary_json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit risk-aware selector choices against separation phase boundaries on gold."
    )
    return parser.parse_args()


def main() -> None:
    _ = parse_args()
    _ = load_config()
    audit_rows, summary_rows = build_audit_report()
    paths = write_outputs(audit_rows, summary_rows)
    for path in paths:
        print(f"Wrote: {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
