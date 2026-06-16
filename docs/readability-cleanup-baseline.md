# Readability Cleanup Baseline

This file records the repository state before the readability cleanup on
`docs/project-audit-readability-cleanup`. It exists so the cleanup can be
reviewed and rolled back with clear before/after evidence.

## File Count Baseline

| Metric | Count |
|---|---:|
| All Markdown files | 1817 |
| Markdown files under `results/figures/` | 1603 |
| Markdown files under `docs/` | 206 |
| All Python files | 2234 |
| Python files under `tests/` | 1335 |

## Low-Information-Density Result Records

These counts use top-level `results/figures/*.md` patterns before any archive
move. Categories can overlap, so the values are diagnostic rather than a sum.

| Pattern | Count |
|---|---:|
| `*wave*.md` | 1030 |
| `*receipt*.md` | 489 |
| `*writeback*.md` | 481 |
| `*bridge*checklist*.md` | 152 |
| `*checklist*.md` | 167 |
| `*demo*presentation*.md` / `*presentation*writeback*.md` | 161 |

## Reading Entry Diagnosis

| Entry | Current Role Before Cleanup | Problem |
|---|---|---|
| `README.md` | Project description, result tables, reproduction command list, documentation map, LLM usage, contributor notes | Too many jobs for a first screen; important setup and status boundaries are hard to scan quickly |
| `docs/README.md` | Documentation index plus long result-link list | Overlaps with the root README and sends readers into many generated result files |
| `docs/project_state.md` | Long-running state ledger for future agents | Useful for continuity, but too long for new readers or reviewers |
| `results/figures/` | Curated summaries mixed with generated wave, receipt, writeback, checklist, and demo records | Looks like an uncurated artifact bucket; final result summaries are hard to find |

## Recommended Main Reading Path

New readers should eventually start with:

1. `README.md`
2. `docs/quickstart.md`
3. `docs/implementation-status.md`
4. `docs/results-index.md`
5. `results/README.md`
6. `docs/branch-audit.md`

Historical wave, receipt, writeback, bridge-checklist, and old planning records
should be kept for traceability but moved out of the primary reading path.
