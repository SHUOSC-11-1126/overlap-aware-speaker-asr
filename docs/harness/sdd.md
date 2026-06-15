# SDD — Spec-Driven Development

Adapted from code-tape, where `docs/PRD.md` has the highest authority and code
must not deviate from `docs/技术方案.md`. This repo has no single PRD; instead a
**hierarchy of authority documents** plays that role, and **ADRs** capture
decisions. Spec precedes code: agents read the spec, propose against it, then
implement.

## Authority hierarchy

When two documents disagree, the higher one wins:

1. [`CLAUDE.md`](../../CLAUDE.md) / [`AGENTS.md`](../../AGENTS.md) — the Agent Operating Charter (mission, hard safety rules, result labels, challenge modes).
2. [`docs/project_state.md`](../project_state.md) — the current verified state of the baseline and frontier.
3. [`docs/roadmap.md`](../roadmap.md) and [`docs/technical_implementation_plan_v2.md`](../technical_implementation_plan_v2.md) — the planned direction and technical approach.
4. [`docs/adr/`](../adr) — Architecture/approach Decision Records: the "why" behind structural choices.
5. [`README.md`](../../README.md) / [`REPORT.md`](../../REPORT.md) — the public-facing narrative and results.

These are the `authority-docs` critical category in the
[knowledge-base contract](knowledge_base_contract.md): changing them requires a
structured impact summary, because they redefine what every future agent treats
as ground truth.

## Spec-first loop

1. **Read** the relevant authority docs and the matching `docs/skills/` note.
2. **Propose** using [`docs/experiment_proposal_template.md`](../experiment_proposal_template.md)
   (Question / Hypothesis / Method / Inputs / Outputs / Metrics / Compute cost /
   Failure modes / Owner). For a structural or cross-cutting decision, write an
   [ADR](../adr/README.md) instead.
3. **Implement** against the spec, test-first (see [TDD](tdd.md)).
4. **Label** every output `gold` / `silver` / `frontier` / `demo` / `oracle` /
   `external` per [`maintenance_harness.md`](../maintenance_harness.md).
5. **Record** state changes back into `docs/project_state.md`.

## When to write an ADR

Write an ADR when a choice is hard to reverse or shapes future work: a new
evaluation metric's definition, a routing-signal policy, a dependency or
external dataset, or a change to the Harness itself. ADRs are short, numbered,
and immutable once accepted — supersede rather than edit. See
[`docs/adr/ADR-000-template.md`](../adr/ADR-000-template.md).

## Charter guardrails the spec must respect

- Do not overwrite verified references unless explicitly requested.
- Do not use ground-truth CER / references as deployable routing input.
- Do not mix gold and synthetic/silver results without labeling.
- Do not silently overwrite result tables or claim silver as gold.
- Do not add heavyweight modules without a stated research question, owner, and output path.
