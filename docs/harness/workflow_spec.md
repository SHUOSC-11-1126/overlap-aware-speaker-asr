# Development Workflow

Adapted from code-tape's `docs/规范工作流程.md`, **trimmed to the development
guardrails**. The training-camp mechanics (issue auto-claim, score keeping, PR
auto-merge, 24-hour timeout, progress bots) are intentionally omitted — they are
not part of this repo's Harness.

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

1. `make agent-bootstrap` — install hooks (`core.hooksPath=.githooks`) and print the workflow.
2. `make quality-predev` — refresh the GitNexus index and run the contract (advisory) before editing.
3. Read the relevant [authority docs](sdd.md) and write a spec/proposal or ADR for non-trivial work.
4. Write code **test-first** ([TDD](tdd.md)). A critical code change needs its paired test in the same change.
5. `git commit` — the `pre-commit` hook runs the fast test gate. Do not hand-run it first.
6. `git push` — the `pre-push` hook runs the contract (local) + full test gate.
7. Open a PR and fill the [structured impact summary](../../.github/PULL_REQUEST_TEMPLATE.md) for any critical change.
8. CI (`Tests` + `Contract Guard`) is the final gate; address its findings.

## Do / don't

- Do label every result `gold` / `silver` / `frontier` / `demo` / `oracle` / `external`.
- Do keep synthetic/silver outputs separate from gold, in versioned paths.
- Don't overwrite verified references or gold tables silently — declare it via the Result label.
- Don't carry unrelated changes in a PR.
- Don't use `SKIP_QUALITY_HOOKS=1` outside a genuine emergency; CI ignores it anyway.

## Minimal checklist

```text
bootstrap:  make agent-bootstrap && make quality-predev
commit:     git commit         (pre-commit -> fast test gate)
push:       git push           (pre-push  -> contract + full test gate)
PR:         fill the GitNexus impact summary for critical changes
```
