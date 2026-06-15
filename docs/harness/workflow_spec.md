# Development Workflow

Adapted from code-tape's `docs/规范工作流程.md` and AGENTS.md item 8. The
**review loop is kept** — issue → PR → repo-guard CR → respond. Only the
*training-camp automation* (issue auto-claim, score keeping, PR auto-merge,
24-hour timeout, progress bots) is intentionally omitted; that scoring
machinery is not part of this repo's Harness, but quality review is.

## Branch naming

Match the repo convention (and code-tape's): branch from `main` with a typed
prefix.

```text
feature/<short-topic>     # new module / capability
fix/<short-topic>         # bug fix
chore/<short-topic>       # tooling, docs, harness, cleanup
research/<short-topic>    # frontier / experimental exploration
```

## The loop

0. **Issue first.** Work starts from an issue that links the relevant
   [authority doc](sdd.md) / spec section and states acceptance criteria. (No
   auto-claim / scoring — just the issue as the unit of work and the PR anchor.)
1. `make agent-bootstrap` — install hooks (`core.hooksPath=.githooks`) and print the workflow.
2. `make quality-predev` — refresh the GitNexus index and run the contract (advisory) before editing.
3. Read the linked authority docs and write a spec/proposal or ADR for non-trivial work.
4. Write code **test-first** ([TDD](tdd.md)). A critical code change needs its paired test in the same change.
5. `git commit` — the `pre-commit` hook runs the fast test gate. Do not hand-run it first.
6. `git push` — the `pre-push` hook runs the contract (local) + full test gate.
7. **Open a PR**, reference the issue (`Closes #N`), and fill the
   [structured impact summary](../../.github/PULL_REQUEST_TEMPLATE.md) for any critical change.
8. **Wait for the review loop** (below), then **respond to every comment**.
9. CI (`Tests` + `Contract Guard`) plus a clean repo-guard review are the gates to merge.

## Review loop (repo-guard CR)

This mirrors code-tape AGENTS.md item 8: *open a PR, then wait for the automated
reviews and act on them.* After opening (or pushing to) a PR:

- **GitHub Actions** runs `Tests` and `Contract Guard` (the knowledge-base contract).
- **repo-guard** ([`.github/workflows/repo-guard.yml`](../../.github/workflows/repo-guard.yml),
  `ceilf6/repo-guard`) reviews the issue/PR with an LLM and posts CR comments.
  Any other configured PR reviewer (e.g. Copilot) comments here too.
- An ignorable "needs CR to pass" style status can appear before review lands — that is normal; wait for the comments.

Then the development agent **must read and respond to every repo-guard / reviewer
comment** — fix the issue or justify why not, and push a follow-up commit (which
re-runs the gates and re-triggers review). Do not merge with unaddressed guard
findings. This keeps **generation and evaluation separate**: the author does not
self-approve; an independent reviewer signs off.

## Do / don't

- Do start from an issue and reference it from the PR (`Closes #N`).
- Do respond to every repo-guard / reviewer comment before merge.
- Do label every result `gold` / `silver` / `frontier` / `demo` / `oracle` / `external`.
- Do keep synthetic/silver outputs separate from gold, in versioned paths.
- Don't overwrite verified references or gold tables silently — declare it via the Result label.
- Don't carry unrelated changes in a PR, and don't self-merge past unresolved guard findings.
- Don't use `SKIP_QUALITY_HOOKS=1` outside a genuine emergency; CI ignores it anyway.

## Minimal checklist

```text
issue:      open/pick an issue linked to a spec section + acceptance criteria
bootstrap:  make agent-bootstrap && make quality-predev
commit:     git commit         (pre-commit -> fast test gate)
push:       git push           (pre-push  -> contract + full test gate)
PR:         Closes #N + fill the GitNexus impact summary for critical changes
review:     wait for repo-guard CR + CI, then respond to every comment
```
