# Archive Plan

This file explains what was moved out of the primary reading path and what
should be considered for future cleanup. It is a plan and record, not a deletion
policy.

## Archive Categories

| Category | Current Location | New Location | Why Archive | Risk | Approval Needed |
|---|---|---|---|---|---|
| Historical superpowers plans/specs | `docs/superpowers/` | `docs/archive/superpowers/` | Useful history, but too dense for primary docs | Low; moved with `git mv` | Already moved in this branch; review paths |
| Old implementation plan v1 | `docs/technical_implementation_plan.md` | `docs/archive/old-plans/` | Superseded by current status and docs map | Low | Review only |
| Historical video script | `docs/video_script.md` | `docs/archive/old-plans/` | Presentation history, not setup/status | Low | Review only |
| Historical markdown audit | `docs/markdown_audit.md` | `docs/archive/old-status-ledgers/` | Superseded by this cleanup manifest | Low | Review only |
| Wave records | `results/figures/*wave*.md` | `results/figures/archive/waves/` | Generated historical coordination | Low; links may need index-based access | Review sampled files |
| Receipts | `results/figures/*receipt*.md` | `results/figures/archive/receipts/` | Execution trace, not final claim | Low | Review sampled files |
| Writebacks | `results/figures/*writeback*.md` | `results/figures/archive/writebacks/` | Agent writeback trace, not final claim | Low | Review sampled files |
| Bridge/checklists | `*bridge*checklist*.md`, `*checklist*.md` | `results/figures/archive/bridge-checklists/` | Automation/checklist trace | Medium; review active relevance | Maintainer review |
| Demo presentation writebacks | `results/figures/*demo*presentation*.md`, `*presentation*writeback*.md` | `results/figures/archive/demo-presentations/` | Demo history, not benchmark evidence | Low | Review sampled files |
| Repeated result summaries | `results/figures/*.md` | `results/figures/curated/` or archive | Separate curated summaries from generated records | Medium | Maintainer should review curated list |
| Branch cleanup candidates | Remote branches | Not moved | Branch list is noisy | High | Explicit maintainer approval required |

## Code and Test Follow-Up

The cleanup found 1317 `src/` / `tests/` paths matching wave, writeback, or
receipt naming patterns. This pass does not move Python files or change test
logic.

## Contribution Record Source

Contribution records are now centralized in the root `CONTRIBUTIONS.md` file.
The former `docs/contributions/` tree has been removed to avoid duplicate
contribution sources.

Recommended future work:

| Area | Recommendation |
|---|---|
| Wave-specific Python modules | Consider replacing repeated generated modules with a parameterized generator |
| Wave-specific tests | Keep behavior coverage, but consider table-driven tests where possible |
| Writeback/receipt helpers | Extract reusable builders before deleting any generated modules |

Any code movement needs a separate PR and full test review.
