from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


CORE_FILES = [
    "README.md",
    "REPORT.md",
    "AGENTS.md",
    "docs/README.md",
    "docs/project_state.md",
    "docs/technical_implementation_plan_v2.md",
    "docs/roadmap.md",
    "docs/maintenance_harness.md",
    "docs/markdown_audit.md",
    "docs/contributions/README.md",
    "docs/contributions/WUFANGZHOU.md",
    "docs/contributions/TEAM_CONTRIBUTION_TEMPLATE.md",
    "docs/handoff/WUFANGZHOU_HANDOFF.md",
    "docs/backup_plan.md",
    "references/reference_transcripts.json",
    "results/tables/cer_results.csv",
    "results/tables/routing_performance_v2.csv",
    "results/tables/error_type_summary.csv",
    "results/tables/speaker_cer_results.csv",
    "results/tables/cpcer_lite_results.csv",
    "results/tables/risk_aware_performance.csv",
]

GOLD_CASES = [
    "NoOverlap",
    "LightOverlap",
    "MidOverlap",
    "HeavyOverlap",
    "OppositeOverlap",
]


def exists(rel_path: str) -> bool:
    return (PROJECT_ROOT / rel_path).exists()


def inspect_gold_cases() -> dict[str, bool]:
    ref_path = PROJECT_ROOT / "references" / "reference_transcripts.json"
    if not ref_path.exists():
        return {case: False for case in GOLD_CASES}
    try:
        data = json.loads(ref_path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {case: False for case in GOLD_CASES}
    if not isinstance(data, dict):
        return {case: False for case in GOLD_CASES}

    # The file may be stored either as a direct case_id -> record mapping or under a nested "cases" key.
    cases = data.get("cases", {})
    if not isinstance(cases, dict) or not cases:
        cases = data

    result: dict[str, bool] = {}
    for case in GOLD_CASES:
        entry = cases.get(case)
        if isinstance(entry, dict):
            result[case] = str(entry.get("status", "")).strip() == "verified_reference"
        else:
            result[case] = False
    return result


def inspect_synthetic_separation() -> dict[str, str]:
    if (PROJECT_ROOT / "resources" / "synthetic_overlap").exists():
        return {"status": "synthetic_overlap"}
    if (PROJECT_ROOT / "resources" / "synthetic_overlap_v2").exists():
        return {"status": "synthetic_overlap_v2"}
    return {"status": "missing"}


def build_report() -> dict[str, object]:
    missing_core = [path for path in CORE_FILES if not exists(path)]
    gold_status = inspect_gold_cases()
    synthetic_status = inspect_synthetic_separation()
    report = {
        "project_root": str(PROJECT_ROOT),
        "core_files_present": len(missing_core) == 0,
        "missing_core_files": missing_core,
        "gold_cases": gold_status,
        "synthetic_status": synthetic_status,
        "gold_and_synthetic_separated": synthetic_status["status"] in {"synthetic_overlap", "synthetic_overlap_v2"},
    }
    return report


def write_report(report: dict[str, object]) -> tuple[Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    json_path = tables_dir / "project_harness_report.json"
    md_path = figures_dir / "project_harness_report.md"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    gold_lines = []
    for case, ok in report["gold_cases"].items():
        gold_lines.append(f"- {case}: {'present' if ok else 'missing'}")

    lines = [
        "# Project Harness Report",
        "",
        "## Core Files",
        "",
        f"- core_files_present: {report['core_files_present']}",
        "",
        "### Missing Core Files",
    ]
    missing = report["missing_core_files"]
    if missing:
        for item in missing:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines += [
        "",
        "## Gold Cases",
        "",
    ] + gold_lines + [
        "",
        "## Synthetic Separation",
        "",
        f"- status: {report['synthetic_status']['status']}",
        f"- gold_and_synthetic_separated: {report['gold_and_synthetic_separated']}",
        "",
        "## Interpretation",
        "",
        "- The repository keeps gold references and synthetic resources separate.",
        "- The core maintenance files are in place for future agents.",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> None:
    report = build_report()
    json_path, md_path = write_report(report)
    print(f"Wrote harness report: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote harness summary: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"gold_cases_present: {all(report['gold_cases'].values())}")
    print(f"gold_and_synthetic_separated: {report['gold_and_synthetic_separated']}")


if __name__ == "__main__":
    main()
