# Harness

This directory documents the development Harness adopted from
[`ref/code-tape`](../../ref/code-tape) and adapted to this Python research
repository. The Harness is the set of always-on guardrails that keep the
stable baseline safe while the project pursues ambitious frontier work (see
the [Agent Operating Charter](../../CLAUDE.md)).

The Harness has four pillars. The "engineering camp" automation in code-tape
(issue auto-claim, PR auto-merge, score keeping, progress bots) is **out of
scope** and was deliberately not ported.

| Pillar | What it does here | Where |
| --- | --- | --- |
| Git hooks | `pre-commit` runs the fast test gate; `pre-push` runs the contract + full test gate | [`.githooks/`](../../.githooks), `scripts/harness/install_hooks.py` |
| Knowledge base | GitNexus indexes the code graph so agents can see a change's cascade before editing critical code | [`knowledge_base_contract.md`](knowledge_base_contract.md), `scripts/harness/contract_*.py` |
| SDD | Spec-driven development: an authority-doc hierarchy + ADRs anchor what agents treat as ground truth | [`sdd.md`](sdd.md), [`../adr/`](../adr) |
| TDD | Red → green → refactor; the contract mechanically requires a paired test for every critical code change | [`tdd.md`](tdd.md) |

## Quick start (every agent / contributor)

```bash
make agent-bootstrap     # install git hooks via core.hooksPath, print the workflow
make quality-predev      # refresh the GitNexus index + contract (advisory) before editing
# ... edit code, write tests ...
git commit               # pre-commit hook runs the fast test gate automatically
git push                 # pre-push hook runs the contract + full test gate automatically
```

No npm here, so [`../../Makefile`](../../Makefile) is the ergonomic surface and
[`scripts/harness/quality.py`](../../scripts/harness/quality.py) is the single
source of truth that the hooks delegate to.

## Gate cadence

| Stage | Command | Contents | GitNexus | Impact summary |
| --- | --- | --- | --- | --- |
| pre-commit | `quality.py precommit` | full unittest suite (~2s) | — | — |
| pre-push | `quality.py local` | contract (local) + full suite | refresh, best-effort | advisory |
| CI | `contract_check.py gitnexus` + tests | contract (PR base) + tests + harness smoke | refresh, required | **enforced** |

Structural gates (a touched critical module needs its paired test) are hard
**everywhere**. The structured impact summary is advisory locally — there is
no PR body to read — and a hard gate in CI, where the PR body exists.

## Escape hatches

- `SKIP_QUALITY_HOOKS=1` — bypass a local hook in an emergency. CI never honours it.
- `GITNEXUS_SKIP=1` — skip only the GitNexus index refresh (keeps the deterministic contract check).
- `GITNEXUS_ANALYZE_TIMEOUT_MS` — override the index-build timeout (default 120s local / 300s CI).

See [`maintenance_harness.md`](../maintenance_harness.md) for the result-labeling
and reproducibility policy this Harness enforces.
