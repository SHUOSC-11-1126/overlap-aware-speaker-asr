# Current Roadmap

This is the short, reviewer-facing roadmap. The long historical queue remains in `docs/roadmap.md` for provenance and generated frontier bookkeeping.

## Now

1. Keep the stable five-case gold benchmark and `router_v2` claim boundary unchanged.
2. Treat AudioDepth as a frontier Stage-1 triage signal, not a replacement for text-instability routing.
3. Treat Generative AudioDepth as a safety/interpretable confirmer, not the main router.
4. Keep controlled_v2 and source-disjoint v2 evidence labeled `silver_plus_unverified` until manual annotation is done.

## Next Highest-value Work

1. Annotate the `11` prepared micro-gold candidates in `results/tables/micro_gold_annotation_sheet.csv`.
2. Re-run unified router evaluation with gold/silver metrics separated after annotation.
3. Construct targeted cleaned-win cases because current controlled_v2 and source-disjoint v2 evidence still has `0` cleaned oracle wins.
4. Add a verified review/abstention outcome path rather than scoring review as an oracle handoff.
5. Run a tiny external sanity slice only after source/license status is confirmed.

## Near-term Engineering Cleanup

1. Keep `python -m scripts.check_environment` as the first clone-and-run command.
2. Keep new frontier outputs under explicit prefixes and claim ledgers.
3. Maintain `docs/module_lifecycle.md` and `results/tables/results_manifest.csv` with `python -m scripts.generate_repo_indexes`.
4. Avoid committing generated queue expansions unless they are intentionally refreshed with `python -m src.project_harness`.
5. Prefer small documents that point to detailed ledgers over adding more long-form content to `README.md`.

## Current Decision

The project is complete as a research baseline plus frontier evidence package. The remaining work is evidence strengthening: manual micro-gold, external validation, and cleaner route-specific benchmark design.
