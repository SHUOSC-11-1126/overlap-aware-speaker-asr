# Ceremony Purge — Manifest & Audit Trail

This is the auditable record of the ceremony purge (issue #787, PR #788). It
documents what was removed, the deterministic criteria, the safety method, and
how to reproduce or roll back. It complements the diagnosis in
`docs/frontier/agentic_research_entropy.md`.

## What "ceremony" means here

Self-referential scaffolding that computes nothing — handoff / receipt /
coordination / completion-summary / writeback / wave / bridge-checklist /
operator-brief / runbook / dashboard files that only assemble hardcoded status
strings and write status documents, mostly referencing other such files. The
audit (`src/research_entropy_audit.py`) measured ~89% of `src/*.py` as this, with
**zero** ceremony-named files containing real computation.

## Deletion criteria (deterministic)

A `src/*.py` file was deleted iff its name matched the ceremony vocabulary AND it
computed nothing (no research/numeric import, < 3 arithmetic ops) — the same
two-signal classifier the audit uses, which had **0 name/content disagreements**.
A small hand-audited set of name-clean pure status-emitter chains (the
`llm_critic_review_pass_*` chain, `meeteval_cpwer_execution_status/preflight`,
`external_validation_slice_staging_*`, `speaker_profile_embedding_trial_execution_*`)
was added after confirming by inspection that each only builds strings and writes
status docs (loads no audio/CER/model data).

Result tables/figures were deleted by the same name vocabulary, plus the
`results/figures/archive/` historical trace and the `cascade_benchmark_*`
coordination artifacts. Gold result tables, verified references, curated
summaries, and `results/entropy_audit/` were explicitly protected.

## Counts

| Surface | Removed | Kept |
|---|---:|---:|
| `src/*.py` | 803 | 90 |
| `tests/test_*.py` | 1,112 | ~225 |
| `results/` artifacts | ~4,360 | ~625 |
| `project_harness.py` | ~4,290 lines (`WAVE_FRONTIER_MODULES` + frontier generators) | lean smoke |
| `compute_aware_cascade.py` | 73 `cascade_benchmark` fns + 23 column constants (~2,090 lines) | cascade analysis |

Audit delta: ceremony saturation **0.894 → 0.035**, degeneration index **0.46 → 0.00**;
full test suite **3,304 → 778 tests, all green**; smoke 18/18 core files, 5/5 gold cases.

## Safety method — import closure

Before deletion, a static import scan (`from .x` / `from src.x` / `import src.x`)
over every kept `src/*.py` and `tests/test_*.py` confirmed the kept set is
import-closed against the delete set: **0 violations**. Any ceremony module
imported by a kept module/test was promoted back to "keep". No `router-core`,
`evaluation-core`, gold table, or verified reference was touched.

### Retained ceremony helpers (load-bearing)

Three ceremony-named helpers were deliberately kept because kept code imports
them; `tests/test_ceremony_purge_residuals.py` enforces this rationale:

| Retained helper | Imported by |
|---|---|
| `external_validation_go_no_go_board` | `external_validation_narrow_audio_eval` |
| `external_validation_slice_scaffold` | `external_validation_license_confirmation`, `external_validation_audio_excerpt_staging_plan` |
| `meeteval_cpwer_official_execution_completion_summary` | `tests/test_meeteval_cpwer_official_execution` |

## project_harness.py — before/after functional map

| Kept (genuine baseline smoke) | Removed (ceremony engine) |
|---|---|
| `exists`, `inspect_gold_cases`, `inspect_synthetic_separation`, `build_report`, `write_report`, `main`; `CORE_FILES`, `GOLD_CASES` | `WAVE_FRONTIER_MODULES` (wave1–wave100+ catalogue); `build_frontier_*` / `write_frontier_*` generators (status checklist, queue, focus card, handoff packet, receipt packet/map/board, parallel picklist, coordination matrix, writeback index, + checklists); `FRONTIER_SKILLS` |

The smoke still confirms the authority docs, verified references, gold tables,
gold cases, and synthetic resources are present, and exits 0.

## Reproduce / roll back

- Re-measure: `make entropy-audit` (or `python -m src.research_entropy_audit`) —
  recomputes saturation from the working tree.
- Everything removed is recoverable from git history (the pre-purge commit on
  `main` is `f9050d02`; this purge is on `cleanup/purge-ceremony`).
- The advisory `make quality-predev` guard (`scripts/harness/entropy_guard.py`)
  warns if a future change re-introduces ceremony faster than substance.

## Known residual

`compute_aware_cascade.py` retained its real cost/accuracy cascade analysis; its
`cascade_benchmark` generation appendage was removed in this PR (the prior note
deferring it is superseded). No further ceremony generators remain in kept
modules at the time of writing.
