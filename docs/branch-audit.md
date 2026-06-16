# Branch Audit and Cleanup Plan

This file explains how to interpret the repository's many remote branches. It
does not delete or modify any remote branch.

## Mainline

- `main`

`main` is the stable review baseline and the source of truth for this cleanup.

## High-Risk Frontier Branch

- `frontier/audio-depth-router`

This branch does not represent mainline status. It is Frontier Branch Only /
Exploratory Research and needs separate review before merge. Prior audit
evidence showed it adds many files, including artifact-heavy outputs such as
`.npy`, `.png`, and model-like files. It should not be merged directly.

Recommended split before any merge:

| Slice | Handling |
|---|---|
| Code | Review separately with tests |
| Documentation | Keep claim boundaries explicit |
| Lightweight samples | Keep small and reproducible |
| Large artifacts / models | Move to release artifacts or external storage |

See [frontier/audio-depth-router.md](frontier/audio-depth-router.md) for the
lightweight mainline documentation entry and merge-boundary checklist.

## Diff-Zero / Already Absorbed Candidates

Branches matching these families often have no remaining file diff against
`main`:

- `improve/*`
- `cursor/*`
- `agent/*`

Cleanup policy: generate a full list, confirm with maintainers, back up the
branch names, and only then delete or archive remote branches. This pass does
not delete them.

## Wave / Demo / Coordination Branches

These families are mostly historical collaboration and writeback trails:

- `wave*`
- `frontier/wave*`
- `demo-wave*`
- `frontier/demo-wave*`

They should not be used as evidence of mainline feature completeness. Their
corresponding generated Markdown records have been moved under
`results/figures/archive/` where possible.

## Cleanup Policy

1. Generate an exact branch list with diff status.
2. Classify branches as mainline, high-risk frontier, already absorbed, or
   historical coordination.
3. Ask maintainers to confirm.
4. Back up the branch list or tag important refs.
5. Delete or archive only after explicit approval.

No remote branch is deleted by this readability cleanup.
