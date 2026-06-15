# TDD — Test-Driven Development

Adapted from code-tape's red → green → refactor discipline paired with the
Karpathy Guidelines. In this repo TDD is not just a convention — the
[knowledge-base contract](knowledge_base_contract.md) **mechanically enforces**
it for critical code.

## The loop

1. **Red** — write a failing test that pins the behaviour you want. The repo's
   convention is one or more `tests/test_<module>_<aspect>.py` files per
   `src/<module>.py` (e.g. `src/adaptive_router_v2.py` →
   `tests/test_adaptive_router_v2_helpers.py`).
2. **Green** — write the minimum code to pass.
3. **Refactor** — clean up with the test as a safety net.

Run the suite (fast — ~2s for 3000+ tests):

```bash
make test                # python -m unittest discover -s tests -p 'test_*.py'
```

## Mechanical enforcement

When a diff touches a critical **code** module, the contract requires a paired
test *in the same change*:

- `router-core` and `evaluation-core`: each touched `src/<name>.py` needs a
  changed `tests/test_<name>*.py`. Touching the router without touching a
  router test fails the gate — locally (pre-push) and in CI.
- `harness`: changes under `scripts/harness/**`, `.githooks/**`,
  `.github/workflows/**` need a changed `tests/test_harness*` or
  `scripts/harness/tests/**`.

This is the `paired-test` / `category-test` enforcement in
[`scripts/harness/contract_rules.py`](../../scripts/harness/contract_rules.py),
covered by [`tests/test_harness_contract_rules.py`](../../tests/test_harness_contract_rules.py).

## Karpathy Guidelines

Pair the loop with the `karpathy-guidelines` skill: make surgical changes,
avoid overcomplication, surface assumptions, and define verifiable success
criteria before coding. The paired-test gate turns "I verified it" into
"there is a committed test that verifies it."

## What is *not* gated by a test

Data and spec surfaces (`references`, `gold-results`, `authority-docs`) are not
unit-testable in the same way; they are gated by the structured impact summary
(and, for results/references, a result label) instead. That is intentional:
the gate matches the kind of change.
