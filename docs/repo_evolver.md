# Repo Evolver — Local Overrides

Label: **experimental/frontier**

This repository uses the [repo-evolver](https://github.com/) skill with local overrides. There is **no repo-guard** bot; PRs are auto-merged after CI (or basic checks) pass.

## Differences from default repo-evolver

| Default | This repo |
|---------|-----------|
| Wait for repo-guard issue review | **Skip** — proceed immediately after issue creation |
| Wait for repo-guard PR review | **Skip** — merge when mergeable |
| Phase 4 meta-improve (repo-guard tuning) | **Disabled** — set `meta_improvement_exhausted: true` in state |
| `pnpm typecheck/test/lint` | Python: see scan commands below |
| Squash merge | **`gh pr merge --merge`** — preserve incremental commits |

## Safety (from AGENTS.md)

- Do not overwrite verified references or gold result tables.
- Do not use ground-truth CER as routing input.
- Do not mix gold and synthetic results without labeling.
- New experimental outputs go under versioned paths, not stable tables.

## Scan commands

```bash
# Correctness — run full suite; note optional-deps failures separately
python3 -m unittest discover -s tests -p 'test_*.py' -q

# Code hygiene
grep -rn "TODO\|FIXME\|HACK" --include="*.py" src/ tests/ | head -50

# Optional: project harness smoke
python3 -m src.project_harness
```

Score findings using the repo-evolver scan rubric (`references/scan-rubric.md` in the skill). Adapt TypeScript-specific signals to Python (import errors, unittest failures, missing deps).

## Workflow per issue

1. Create GitHub issue from scan backlog (Phase 1).
2. Branch `improve/<slug>` from `main`.
3. Implement with **one commit per logical change** (test fix, refactor, doc update — separate commits).
4. Push, open PR with `Closes #N`.
5. Wait for `gh pr checks` (if any); fix failures on the same branch.
6. When mergeable: `gh pr merge <n> --merge --delete-branch`
7. Update `.claude/repo-evolver.local.md` backlog entry to done.

## Completion

When scan produces empty backlog **three times in a row**, output:

```text
<promise>NO_MORE_IMPROVEMENTS</promise>
```

## State file

Runtime state: `.claude/repo-evolver.local.md` (gitignored). Agents read/write this between automation runs.

## Automation handoff

Cursor Automations should:

1. Read this file and `.claude/repo-evolver.local.md`.
2. Execute **one repo-evolver phase per run** if time-boxed, or **loop phases** until `NO_MORE_IMPROVEMENTS` if the session allows.
3. Never force-push `main`.
4. Cap open evolver PRs at 10; finish in-flight PRs before creating new ones.
