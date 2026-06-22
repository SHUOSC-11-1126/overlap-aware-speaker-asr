from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
RESULTS_DIR = ROOT / "results"
DOCS_DIR = ROOT / "docs"
TABLES_DIR = RESULTS_DIR / "tables"
FIGURES_DIR = RESULTS_DIR / "figures"


def classify_module(path: Path) -> str:
    name = path.stem
    if name == "__init__":
        return "stable-mainline"
    if name in {
        "run_experiment",
        "evaluate_cer",
        "evaluate_speaker_cer",
        "postprocess_transcript",
        "adaptive_router",
        "audio_manifest",
        "project_harness",
    }:
        return "stable-mainline"
    if any(token in name for token in ["audio_depth", "audiodepth", "controlled", "generative", "source_disjoint", "unified_router", "micro_gold"]):
        return "frontier-audiodepth"
    if any(token in name for token in ["cascade", "compute_aware", "risk_aware"]):
        return "mainline-experimental"
    if any(token in name for token in ["meeteval", "cpwer", "speaker_profile", "external_validation", "llm", "rag", "emotion"]):
        return "optional-integration"
    if name.startswith(("wave", "demo_", "frontier_")) or "writeback" in name or "bridge_checklist" in name:
        return "frontier-scaffold"
    return "archive-candidate"


def evidence_for_module(path: Path) -> str:
    stem = path.stem
    candidates = [
        FIGURES_DIR / f"{stem}.md",
        TABLES_DIR / f"{stem}.csv",
        TABLES_DIR / f"{stem}.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.relative_to(ROOT).as_posix()
    if "audiodepth" in stem or "audio_depth" in stem:
        return "docs/frontier/audio-depth-router.md"
    if "generative" in stem:
        return "docs/frontier/generative_audiodepth.md"
    return ""


def reviewer_priority(lifecycle: str) -> str:
    return {
        "stable-mainline": "high",
        "mainline-experimental": "medium",
        "frontier-audiodepth": "medium",
        "optional-integration": "low",
        "frontier-scaffold": "low",
        "archive-candidate": "low",
    }.get(lifecycle, "low")


def generated_by_for_result(path: Path) -> str:
    stem = path.stem
    if stem.endswith("_summary"):
        stem = stem.removesuffix("_summary")
    script = SRC_DIR / f"{stem}.py"
    if script.exists():
        return f"python -m src.{script.stem}"
    for module in SRC_DIR.glob("*.py"):
        if module.stem in stem:
            return f"python -m src.{module.stem}"
    return "unknown_or_historical"


def evidence_label_for_result(path: Path) -> str:
    text = path.name.lower()
    if "gold" in text or "global_cer" in text or "final_" in text:
        return "gold_or_final_summary"
    if "source_disjoint" in text or "micro_gold" in text or "unified_router" in text:
        return "controlled_silver_plus_stage34"
    if "audio_depth" in text or "audiodepth" in text or "generative" in text:
        return "frontier_audiodepth"
    if "synthetic" in text:
        return "synthetic_silver"
    if "frontier_" in text or "wave" in text or "demo" in text:
        return "coordination_or_demo"
    return "project_result"


def can_regenerate(path: Path) -> str:
    return "maybe" if generated_by_for_result(path) == "unknown_or_historical" else "yes"


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_module_lifecycle() -> list[dict[str, str]]:
    rows = []
    for path in sorted(SRC_DIR.glob("*.py")):
        lifecycle = classify_module(path)
        rows.append(
            {
                "module": path.name,
                "lifecycle": lifecycle,
                "owner": "project",
                "evidence_path": evidence_for_module(path),
                "reviewer_priority": reviewer_priority(lifecycle),
                "safe_to_change": "only_with_tests" if lifecycle in {"stable-mainline", "mainline-experimental"} else "yes_with_claim_boundary",
                "tests_hint": f"rg {path.stem} tests",
            }
        )
    counts = Counter(row["lifecycle"] for row in rows)
    lines = [
        "# Module Lifecycle Index",
        "",
        "This index classifies top-level `src/*.py` modules without moving files. It is a reviewer and maintainer aid, not an import-path contract.",
        "",
        "| lifecycle | count |",
        "| --- | ---: |",
        *[f"| {name} | {counts[name]} |" for name in sorted(counts)],
        "",
        "| module | lifecycle | evidence path | reviewer priority | safe to change | tests hint |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['module']}` | {row['lifecycle']} | {row['evidence_path']} | {row['reviewer_priority']} | {row['safe_to_change']} | `{row['tests_hint']}` |"
        )
    out = DOCS_DIR / "module_lifecycle.md"
    out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return rows


def write_results_manifest() -> list[dict[str, str]]:
    rows = []
    for path in sorted([*TABLES_DIR.glob("*"), *FIGURES_DIR.glob("*")]):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        label = evidence_label_for_result(path)
        priority = "high" if label in {"gold_or_final_summary", "controlled_silver_plus_stage34"} else "medium" if "audiodepth" in label else "low"
        rows.append(
            {
                "path": rel,
                "evidence_label": label,
                "generated_by": generated_by_for_result(path),
                "source_inputs": "see generator or adjacent docs",
                "reviewer_priority": priority,
                "can_regenerate": can_regenerate(path),
                "keep_action": "keep" if priority in {"high", "medium"} else "keep_or_archive_later",
            }
        )
    write_csv(
        TABLES_DIR / "results_manifest.csv",
        rows,
        ["path", "evidence_label", "generated_by", "source_inputs", "reviewer_priority", "can_regenerate", "keep_action"],
    )
    counts = Counter(row["evidence_label"] for row in rows)
    lines = [
        "# Results Manifest Summary",
        "",
        "Generated by `python -m scripts.generate_repo_indexes`.",
        "",
        f"- indexed result artifacts: `{len(rows)}`",
        "",
        "| evidence label | count |",
        "| --- | ---: |",
        *[f"| {name} | {counts[name]} |" for name in sorted(counts)],
        "",
        "Full manifest: `results/tables/results_manifest.csv`.",
    ]
    (FIGURES_DIR / "results_manifest_summary.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return rows


def main() -> int:
    module_rows = write_module_lifecycle()
    result_rows = write_results_manifest()
    print(f"Wrote docs/module_lifecycle.md with {len(module_rows)} modules")
    print(f"Wrote results/tables/results_manifest.csv with {len(result_rows)} artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
