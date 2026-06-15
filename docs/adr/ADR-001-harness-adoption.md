# ADR-001: Adopt the code-tape Harness (hooks / knowledge base / SDD / TDD)

- Status: Accepted
- Date: 2026-06-15
- Deciders: repository maintainer (goal: adapt `ref/code-tape`'s Harness to this repo)
- Related: [`ref/code-tape`](../../ref/code-tape), [`docs/harness/`](../harness/README.md), [`docs/maintenance_harness.md`](../maintenance_harness.md)

## Context

This repository protects a stable ASR baseline while encouraging frontier
experimentation (see the Agent Operating Charter). Until now the only automated
guardrails were CI (`unittest` + `project_harness` smoke) and the LLM
`repo-guard` reviewer. There was no local quality gate, no mechanical link
between critical code changes and their tests, and no structured way to reason
about a change's blast radius before editing.

`ref/code-tape` ships a mature Harness. Four of its pillars are directly useful
here; its "engineering camp" automation (issue auto-claim, score keeping, PR
auto-merge, progress bots) is not.

## Decision

Adopt and adapt the four useful pillars, translated from code-tape's
npm/TypeScript stack to this repo's Python stack:

1. **Git hooks** via `core.hooksPath=.githooks` — `pre-commit` runs the fast
   test gate, `pre-push` runs the contract + full test gate.
2. **Knowledge base** — GitNexus indexes the code graph; `scripts/harness/
   contract_check.py` refreshes it and evaluates a contract over the diff.
3. **SDD** — an authority-document hierarchy plus this ADR series replace
   code-tape's single PRD.
4. **TDD** — the contract mechanically requires a paired test for every
   critical code change.

The npm-script composition becomes `scripts/harness/quality.py` plus a
`Makefile`. The "engineering camp" scoring/auto-merge machinery is **not**
ported.

## Alternatives considered

- **Copy code-tape verbatim** — rejected: it is npm/TypeScript and carries the
  out-of-scope camp automation.
- **CI-only enforcement (no local hooks)** — rejected: loses the fast local
  feedback loop and the pre-edit knowledge-base step.
- **A third-party pre-commit framework (e.g. `pre-commit`)** — rejected for now:
  adds a dependency and config surface; the charter favours carefully chosen,
  minimal tooling, and a small stdlib orchestrator is enough.

## Consequences

- Positive: fast deterministic local gate; critical code can't merge without a
  paired test; references/gold tables can't be silently overwritten; agents get
  a code-graph view before editing.
- Negative / risks: the first `npx gitnexus analyze` is slow on this large repo
  — mitigated by making it best-effort locally (warn + continue), hard only in
  CI, with `GITNEXUS_SKIP=1` / `GITNEXUS_ANALYZE_TIMEOUT_MS` escape hatches.
- Result label for outputs this produces: not applicable (tooling, not research output).

## Verification

- `tests/test_harness_contract_rules.py` covers the contract engine (33 cases).
- The `harness` contract category requires those tests to change alongside the
  scripts.
- CI `Contract Guard` (`scripts/harness/contract_check.py gitnexus`) is the
  final enforced gate.
