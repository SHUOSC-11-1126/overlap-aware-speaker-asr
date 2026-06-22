# Stage 34: Source-disjoint Evidence Expansion

Stage 34 expands the AudioDepth evidence path with a stricter source-token audit, a unified router evaluation table, a micro-gold annotation pack, and a runtime/compute utility audit.

## Data Boundary

- controlled_v2 manifest rows: `120`
- rows with existing real Whisper route CER: `60`
- strict source-disjoint rows retained: `47`
- strict route-CER split: train `20`, validation `9`, test `7`
- source-utterance leakage: `0`
- source-pair leakage: `0`
- newly launched ASR jobs: `0`

The remaining controlled_v2 rows are useful for annotation and bookkeeping, but they are not used for unified CER claims unless route-level CER exists.

## Reference Quality

All audited controlled_v2 rows remain `silver_plus_unverified`; Stage 34 does not promote any row to manual gold. The reference audit writes every row with `claimed_as_gold=False` and prepares the micro-gold pack as `prepared_not_annotated`.

## Unified Router Evaluation

The strict test set has `7` route-CER samples. Oracle distribution is mixed `4`, separated `3`, cleaned `0`.

| policy | mean selected CER | false-safe | high-error mixed | review rate | coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| fixed_mixed | `0.875111` | `3` | `6` | `0.000000` | `1.000000` |
| fixed_separated | `0.672207` | `0` | `0` | `0.000000` | `1.000000` |
| router_v2_refit | `0.572829` | `0` | `3` | `0.000000` | `1.000000` |
| stage30_risk_guarded_gate_refit | `0.572829` | `0` | `1` | `0.285714` | `0.714286` |
| stage31_stage2_review_guard_refit | `0.572829` | `0` | `1` | `0.571429` | `0.428571` |
| stage33_safe_regret_fusion_refit | `0.572829` | `0` | `1` | `0.571429` | `0.428571` |

The abstention policies are scored under an explicit `oracle_for_abstained_rows` handoff assumption, so their CER should be read together with review rate and coverage.

## Runtime and Utility

Runtime provenance is split into three levels:

- head-only router: metadata policy evaluation, about `0.000100` sec;
- feature-ready router: deterministic wav-header scan proxy, about `0.000105` sec on the strict test pack;
- end-to-end ASR reuse: existing faster-whisper/base route runtimes.

Mean route runtimes on the strict test pack are mixed `0.993471` sec, separated `1.098543` sec, cleaned `1.098543` sec, and all-routes-per-sample `2.092400` sec.

## Decision

The main deployable direction remains a conservative AudioDepth/text router with explicit review/abstention. Generative AudioDepth should remain a safety and interpretability confirmer. Stage 34 strengthens the audit trail and prepares micro-gold annotation, but the test set is still too small and non-gold for a strong external generalization claim.

## Reproducibility

```bash
python -m src.build_source_disjoint_benchmark_v2
python -m src.audit_source_disjoint_v2_references
python -m src.run_source_disjoint_v2_routes
python -m src.evaluate_unified_router_benchmark
python -m src.audit_unified_router_safety
python -m src.bootstrap_unified_router_results
python -m src.select_micro_gold_candidates
python -m src.benchmark_end_to_end_runtime
python -m src.evaluate_compute_aware_router_utility
```
