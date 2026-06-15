# Architecture / Approach Decision Records (ADRs)

ADRs capture decisions that are hard to reverse or that shape future work:
evaluation-metric definitions, routing-signal policy, dependencies and external
datasets, and changes to the Harness itself. They are the "why" layer of
[SDD](../harness/sdd.md).

## Conventions

- One decision per file, numbered: `ADR-NNN-short-title.md`.
- Status is one of: `Proposed`, `Accepted`, `Superseded by ADR-NNN`, `Deprecated`.
- ADRs are immutable once `Accepted` — to change a decision, write a new ADR that supersedes it rather than editing history.
- Start from [`ADR-000-template.md`](ADR-000-template.md).

## Index

| ADR | Title | Status |
| --- | --- | --- |
| [ADR-001](ADR-001-harness-adoption.md) | Adopt the code-tape Harness (hooks / knowledge base / SDD / TDD) | Accepted |
