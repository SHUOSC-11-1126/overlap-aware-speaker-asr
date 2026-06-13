from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config
from .io_helpers import to_float
from .router_boundary_alignment import pick_oracle_method, prefers_separation_route
from .separation_phase_diagram import compute_delta_cer

ALIGNMENT_COLUMNS = [
    "sample_id",
    "split",
    "tier",
    "overlap_ratio",
    "selected_method",
    "oracle_method",
    "mixed_cer",
    "separated_cer",
    "separated_cleaned_cer",
    "selected_cer",
    "oracle_cer",
    "delta_cer_separated",
    "separation_helps",
    "prefers_separation_route",
    "router_matches_oracle",
    "router_aligns_with_phase",
    "router_regret_cer",
    "decision_rule",
]

SUMMARY_COLUMNS = [
    "scope",
    "metric",
    "value",
    "label",
]


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))



def load_manifest_by_sample() -> dict[str, dict[str, str]]:
    return {
        str(row.get("sample_id", "")): {key: str(value) for key, value in row.items()}
        for row in read_csv_rows(PROJECT_ROOT / "results" / "tables" / "synthetic_split_manifest.csv")
    }


def load_v2_decisions() -> list[dict[str, Any]]:
    rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "synthetic_split_routing_decisions.csv")
    return [row for row in rows if str(row.get("strategy", "")) == "v2_full_features"]


def build_alignment_rows(
    cer_rows: list[dict[str, Any]],
    decision_rows: list[dict[str, Any]],
    manifest_by_sample: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    cer_by_sample: dict[str, dict[str, float]] = defaultdict(dict)
    meta_by_sample: dict[str, dict[str, str]] = {}
    for row in cer_rows:
        sample_id = str(row.get("sample_id", ""))
        method = str(row.get("method", ""))
        cer = to_float(row.get("cer"))
        if sample_id and method and cer is not None:
            cer_by_sample[sample_id][method] = cer
            meta_by_sample[sample_id] = {
                "split": str(row.get("split", "")),
                "tier": str(row.get("tier", "")),
            }

    decision_by_sample = {str(row.get("sample_id", "")): row for row in decision_rows}
    alignment_rows: list[dict[str, Any]] = []

    for sample_id in sorted(cer_by_sample.keys()):
        methods = cer_by_sample[sample_id]
        mixed = methods.get("mixed_whisper")
        separated = methods.get("separated_whisper")
        cleaned = methods.get("separated_whisper_cleaned")
        if mixed is None or separated is None:
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
        decision = decision_by_sample.get(sample_id, {})
        selected_method = str(decision.get("selected_method", ""))
        selected_cer = available.get(selected_method, oracle_cer)
        delta_sep = compute_delta_cer(mixed, separated)
        separation_helps = delta_sep < 0
        prefers_sep = prefers_separation_route(selected_method)
        manifest = manifest_by_sample.get(sample_id, {})
        overlap_ratio = to_float(manifest.get("overlap_ratio"))
        meta = meta_by_sample.get(sample_id, {})

        alignment_rows.append(
            {
                "sample_id": sample_id,
                "split": meta.get("split", manifest.get("split", "")),
                "tier": meta.get("tier", manifest.get("tier", "")),
                "overlap_ratio": overlap_ratio if overlap_ratio is not None else "",
                "selected_method": selected_method,
                "oracle_method": oracle_method,
                "mixed_cer": mixed,
                "separated_cer": separated,
                "separated_cleaned_cer": cleaned if cleaned is not None else "",
                "selected_cer": selected_cer,
                "oracle_cer": oracle_cer,
                "delta_cer_separated": delta_sep,
                "separation_helps": separation_helps,
                "prefers_separation_route": prefers_sep,
                "router_matches_oracle": selected_method == oracle_method,
                "router_aligns_with_phase": prefers_sep == separation_helps,
                "router_regret_cer": round(selected_cer - oracle_cer, 6),
                "decision_rule": str(decision.get("decision_rule", "")),
            }
        )
    return alignment_rows


def build_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    scopes = ["ALL"] + sorted({str(row["split"]) for row in rows if row.get("split")})
    summary: list[dict[str, str]] = []
    for scope in scopes:
        subset = rows if scope == "ALL" else [row for row in rows if str(row.get("split")) == scope]
        if not subset:
            continue
        count = len(subset)
        oracle_matches = sum(1 for row in subset if row["router_matches_oracle"])
        phase_aligned = sum(1 for row in subset if row["router_aligns_with_phase"])
        avg_regret = round(sum(float(row["router_regret_cer"]) for row in subset) / count, 6)
        label = "synthetic/silver" if scope == "ALL" else "synthetic/silver_held_out" if scope == "test" else "synthetic/silver"
        for metric, value in [
            ("sample_count", str(count)),
            ("router_oracle_match_rate", str(round(oracle_matches / count, 4))),
            ("router_phase_alignment_rate", str(round(phase_aligned / count, 4))),
            ("average_router_regret_cer", str(avg_regret)),
        ]:
            summary.append({"scope": scope, "metric": metric, "value": value, "label": label})
    return summary


def build_summary_lines(
    alignment_rows: list[dict[str, Any]],
    summary_rows: list[dict[str, str]],
) -> list[str]:
    lines = [
        "# Synthetic Router Boundary Alignment (synthetic/silver)",
        "",
        "Label: `synthetic/silver` — audits router v2 (`v2_full_features`) on synthetic_overlap_v2",
        "against per-sample separation phase signals. Does not modify gold references.",
        "",
        "## Summary by Scope",
        "",
        "| scope | metric | value | label |",
        "| --- | --- | ---: | --- |",
    ]
    for row in summary_rows:
        lines.append(f"| {row['scope']} | {row['metric']} | {row['value']} | {row['label']} |")
    test_rows = [row for row in alignment_rows if str(row.get("split")) == "test"]
    lines.extend(
        [
            "",
            f"## Held-out Test Samples ({len(test_rows)} rows)",
            "",
            "| sample_id | overlap_ratio | selected | oracle | phase_aligned | regret_cer |",
            "| --- | ---: | --- | --- | --- | ---: |",
        ]
    )
    for row in test_rows[:15]:
        lines.append(
            f"| {row['sample_id']} | {row['overlap_ratio']} | {row['selected_method']} | "
            f"{row['oracle_method']} | {row['router_aligns_with_phase']} | {row['router_regret_cer']} |"
        )
    if len(test_rows) > 15:
        lines.append(f"| ... | | | | | ({len(test_rows) - 15} more in CSV) |")
    return lines


def build_synthetic_alignment_report() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    cer_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "synthetic_split_cer_results.csv")
    decision_rows = load_v2_decisions()
    manifest_by_sample = load_manifest_by_sample()
    alignment_rows = build_alignment_rows(cer_rows, decision_rows, manifest_by_sample)
    return alignment_rows, build_summary_rows(alignment_rows)


def write_outputs(
    alignment_rows: list[dict[str, Any]],
    summary_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    table_dir = PROJECT_ROOT / "results" / "tables"
    figure_dir = PROJECT_ROOT / "results" / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    csv_path = table_dir / "synthetic_router_boundary_alignment.csv"
    json_path = table_dir / "synthetic_router_boundary_alignment.json"
    summary_csv_path = table_dir / "synthetic_router_boundary_alignment_summary.csv"
    summary_json_path = table_dir / "synthetic_router_boundary_alignment_summary.json"
    md_path = figure_dir / "synthetic_router_boundary_alignment.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=ALIGNMENT_COLUMNS)
        writer.writeheader()
        writer.writerows(alignment_rows)
    json_path.write_text(json.dumps(alignment_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    with summary_csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(summary_rows)
    summary_json_path.write_text(
        json.dumps(summary_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_path.write_text(
        "\n".join(build_summary_lines(alignment_rows, summary_rows)) + "\n",
        encoding="utf-8",
    )
    return csv_path, json_path, summary_csv_path, summary_json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit router v2 boundary alignment on synthetic_overlap_v2 silver split."
    )
    return parser.parse_args()


def main() -> None:
    _ = parse_args()
    _ = load_config()
    alignment_rows, summary_rows = build_synthetic_alignment_report()
    paths = write_outputs(alignment_rows, summary_rows)
    for path in paths:
        print(f"Wrote: {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
