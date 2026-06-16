"""Project harness smoke check.

A lightweight, deterministic smoke that confirms the repository's stable
baseline is present and coherent: the authority docs and gold result tables
exist, the five verified gold cases are marked ``verified_reference`` in the
reference bundle, and synthetic-separation resources are available. It writes a
small JSON+Markdown report and always exits 0 (it reports, it does not gate).

History: this module previously also carried a ~4,400-line ``WAVE_FRONTIER_MODULES``
catalogue and dozens of ``build_frontier_*`` / ``write_frontier_*`` generators
that emitted frontier status/handoff/receipt/coordination documents. That
machinery was self-referential ceremony (see
``docs/frontier/agentic_research_entropy.md``) and regenerated thousands of
status files on every run, so it was removed during the ceremony purge. What
remains is the genuine baseline smoke.
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Authority docs, verified references, and the stable gold result tables. These
# are the load-bearing baseline artifacts the smoke confirms are present.
CORE_FILES = [
    "README.md",
    "REPORT.md",
    "AGENTS.md",
    "CLAUDE.md",
    "docs/README.md",
    "docs/project_state.md",
    "docs/roadmap.md",
    "docs/maintenance_harness.md",
    "docs/ambitious_research_agenda.md",
    "docs/agent_challenge_board.md",
    "docs/frontier/agentic_research_entropy.md",
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

    # The file may be a direct case_id -> record mapping or nested under "cases".
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


def build_report() -> dict:
    return {
        "project_root": str(PROJECT_ROOT),
        "core_files_present": {f: exists(f) for f in CORE_FILES},
        "gold_cases": inspect_gold_cases(),
        "synthetic_separation": inspect_synthetic_separation(),
    }


def build_report_lines(report: dict) -> list[str]:
    present = sum(1 for v in report["core_files_present"].values() if v)
    verified = sum(1 for v in report["gold_cases"].values() if v)
    lines = [
        "# Project Harness Smoke Report",
        "",
        f"Core files present: {present}/{len(report['core_files_present'])}",
        f"Verified gold cases: {verified}/{len(report['gold_cases'])}",
        f"Synthetic separation: {report['synthetic_separation']['status']}",
        "",
        "| gold case | verified_reference |",
        "| --- | --- |",
    ]
    for case, ok in report["gold_cases"].items():
        lines.append(f"| {case} | {'yes' if ok else 'no'} |")
    return lines


def write_report(report: dict, out_dir: Path | None = None) -> tuple[Path, Path]:
    tables_dir = Path(out_dir) if out_dir is not None else PROJECT_ROOT / "results" / "tables"
    figures_dir = (
        Path(out_dir) if out_dir is not None else PROJECT_ROOT / "results" / "figures"
    )
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    json_path = tables_dir / "project_harness_report.json"
    md_path = figures_dir / "project_harness_report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_report_lines(report)) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> None:
    report = build_report()
    json_path, md_path = write_report(report)
    present = sum(1 for v in report["core_files_present"].values() if v)
    verified = sum(1 for v in report["gold_cases"].values() if v)
    print(f"Core files present: {present}/{len(report['core_files_present'])}")
    print(f"Verified gold cases: {verified}/{len(report['gold_cases'])}")
    print(f"Synthetic separation: {report['synthetic_separation']['status']}")
    try:
        print(f"Wrote harness report: {json_path.relative_to(PROJECT_ROOT)}")
        print(f"Wrote harness summary: {md_path.relative_to(PROJECT_ROOT)}")
    except ValueError:
        print(f"Wrote harness report: {json_path}")
        print(f"Wrote harness summary: {md_path}")


if __name__ == "__main__":
    main()
