# Readability Cleanup Manifest

This file records the structural readability cleanup performed on
`docs/project-audit-readability-cleanup`. The full moved-file mapping is in
`readability-cleanup-moved-files.tsv`.

## Summary

| Metric | Before | After |
|---|---:|---:|
| All Markdown files | 1817 | 1827 |
| Top-level Markdown files in `results/figures/` | 1603 | 1 |
| Markdown files in `results/figures/curated/` | 0 | 20 |
| Markdown files in `results/figures/archive/` | 0 | 1583 |
| Markdown files in `docs/archive/` | 0 | 172 |
| Moved paths recorded in TSV | 0 | 1607 |

The total Markdown count increased because this cleanup adds curated entry
documents and archive indexes while preserving historical content.

## Moved Files

The moved-file list is too large for a readable Markdown table. See the machine
readable manifest:

```text
docs/readability-cleanup-moved-files.tsv
```

Category summary:

| Category | Count | New Location |
|---|---:|---|
| Curated reviewer-facing result summary | 20 | `results/figures/curated/` |
| Historical receipt artifact | 429 | `results/figures/archive/receipts/` |
| Historical writeback artifact | 316 | `results/figures/archive/writebacks/` |
| Historical wave record | 290 | `results/figures/archive/waves/` |
| Historical bridge/checklist artifact | 167 | `results/figures/archive/bridge-checklists/` |
| Historical demo presentation writeback | 161 | `results/figures/archive/demo-presentations/` |
| Generated coordination or status artifact | 117 | `results/figures/archive/miscellaneous/` |
| Remaining non-curated result summary | 103 | `results/figures/archive/miscellaneous/` |
| Historical superpowers planning tree | 1 directory | `docs/archive/superpowers/` |
| Historical implementation plan v1 | 1 | `docs/archive/old-plans/` |
| Historical video script | 1 | `docs/archive/old-plans/` |
| Historical markdown audit | 1 | `docs/archive/old-status-ledgers/` |

## Files Kept In Place

| Path | Reason |
|---|---|
| `docs/project_state.md` | Long status ledger still useful for continuity |
| `REPORT.md` | Review-facing narrative report remains at repository root |
| `CONTRIBUTIONS.md` | Contributor details remain outside the slim README |
| `docs/contributions/` | Protected active documentation for course final submission contribution records |
| `docs/harness/` | Current governance documentation |
| `docs/adr/` | Current decision record documentation |
| `results/figures/*.png` | Figure assets were not part of this Markdown cleanup |
| `src/` and `tests/` | Core code and tests were intentionally not moved |

Protected active documentation: `docs/contributions/`.

## Needs Maintainer Confirmation

| Path / Topic | Reason |
|---|---|
| `results/figures/archive/bridge-checklists/` | Some checklists might still be useful as active maintenance references |
| `results/figures/curated/` | Maintainers should confirm the curated result list |
| `docs/archive/superpowers/` | Historical planning tree moved out of primary docs; confirm no current governance file was expected there |
| Remote branch cleanup | This cleanup documents policy only and does not delete branches |
| `frontier/audio-depth-router` | Needs separate PR split and artifact policy |
| License / Citation | Maintainer decision still required |

## Link Update Notes

- `README.md` now links to curated result summaries and curated documentation
  entry points.
- `docs/README.md` is now a documentation map rather than a long result index.
- `docs/results-index.md` is the primary result-navigation document.
- `results/README.md` and `results/figures/README.md` explain curated versus
  historical result locations.
- Historical documents may still mention pre-cleanup paths for context. Use
  `readability-cleanup-moved-files.tsv` as the authoritative path mapping.
