# GitNexus Knowledge-Base Contract

Adapted from code-tape's `docs/知识库契约.md`. This repo's knowledge base is a
GitNexus code graph: the local agent builds the graph and reasons about a
change's cascade before editing critical code; CI re-checks as a backstop.
There is **no external knowledge-base service** — the authoritative context is
the in-repo documents listed under [SDD](sdd.md).

## Local agent workflow

Before editing code:

```bash
make agent-bootstrap     # installs git hooks (core.hooksPath=.githooks)
make quality-predev      # GitNexus index refresh + contract (advisory)
```

Commit and push run the gates automatically through the hooks:

```bash
git commit               # pre-commit -> fast test gate
git push                 # pre-push -> contract (local) + full test gate
```

Do not pre-run `quality-precommit` / `quality-local` by hand in the normal
flow — those belong to the `pre-commit` and `pre-push` hooks. Run them manually
only when diagnosing a hook failure, doing a pre-flight check, deliberately
bypassing with `SKIP_QUALITY_HOOKS=1`, or working where hooks are not installed.

`contract-local` runs `npx gitnexus@<version> analyze --force --index-only`,
which only refreshes the `.gitnexus/` index — it does not rewrite `AGENTS.md` /
`CLAUDE.md`. Default timeout is 120s local / 300s CI; raise it with
`GITNEXUS_ANALYZE_TIMEOUT_MS` if this large repo needs longer. Locally a failed
or slow index build is advisory (warn + continue); in CI it is a hard failure
unless `GITNEXUS_OPTIONAL=1`.

## Critical skeleton surfaces

When a diff touches any of these, the contract activates. The list mirrors this
repo's stable baseline and the charter's Hard Safety Rules:

| Category | Surface | Requirement when touched |
| --- | --- | --- |
| `router-core` | `src/adaptive_router*.py`, `src/router_*.py` | paired test `tests/test_<module>*.py` in the same change |
| `evaluation-core` | `src/evaluate_cer.py`, `evaluate_error_types`, `evaluate_speaker_cer`, `evaluate_cpcer_lite`, `risk_aware_selector`, `analyze_cer_errors` | paired test in the same change |
| `harness` | `scripts/harness/**`, `.githooks/**`, `.github/workflows/**`, `Makefile` | a changed `tests/test_harness*` or `scripts/harness/tests/**` |
| `references` | `references/**` (verified transcripts) | structured summary **+ result label** |
| `gold-results` | the six gold tables in `results/tables/` | structured summary **+ result label** |
| `authority-docs` | charter, project_state, roadmap, technical plans, `docs/harness/**`, `docs/adr/**` | structured summary |

Touching any critical surface also requires reading the GitNexus suggestions
the script prints, and (for a PR) filling the structured impact summary.

## Structured GitNexus impact summary

In a PR, fill the impact-summary block (see the
[PR template](../../.github/PULL_REQUEST_TEMPLATE.md)). Field names accept
English or Chinese; placeholders like `-`, `无`, `todo`, `n/a` are rejected:

```md
- Risk level: LOW | MEDIUM | HIGH | CRITICAL
- Critical skeleton change: which critical directories / files were touched
- GitNexus impact: must mention detect_changes plus one of query / context / impact
- Verification: which test commands ran, and their result (or why they could not run)
- Result label: gold | silver | frontier | demo | oracle | external  (required only when references / gold tables change)
```

## CI contract

On a PR, CI runs:

```bash
make contract-gitnexus   # contract_check.py gitnexus
```

This refreshes the index and evaluates the contract against the PR base diff
with the impact summary **enforced**. A critical change must satisfy both the
paired-test / category-test gate and the structured summary. The Result label
becomes mandatory when verified references or gold tables move — directly
encoding "do not silently overwrite results" and "do not claim silver as gold".
