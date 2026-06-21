# Generative AudioDepth Reliability Input Audit

Stage 33 reuses the real Stage 32 artifacts in the current branch.

## Files

- `results/tables/generative_audiodepth_dataset.csv`: present
- `results/tables/generative_audiodepth_train.csv`: present
- `results/tables/generative_audiodepth_validation.csv`: present
- `results/tables/generative_audiodepth_test.csv`: present
- `results/tables/generative_route_regret_predictions.csv`: present
- `results/tables/generative_audiodepth_distillation.csv`: present
- `results/tables/controlled_v2_real_whisper_cer.csv`: present
- `results/tables/audiodepth_v2_metadata.csv`: present

## Counts

- unique samples: 60
- task rows: 300
- task distribution: DOMINANCE_MAP:60; OVERLAP_MAP:60; REVIEW_RISK:60; ROUTE_REGRET:60; UNCERTAINTY_MAP:60
- oracle-route distribution: mixed:34; separated:26
- target-family distribution: cleaned_win_anchor:15; mixed_win_anchor:15; review_needed_anchor:15; separated_win_anchor:15

## Leakage Risk

- Teacher map targets may use source tracks and remain analysis-only.
- Student/probe inputs are restricted to mixed-only metadata, generated-map summaries, or held-out teacher-map upper bounds.
- Split checks group by source utterance tokens, source pairs, counterfactual family IDs, and mixed wav paths.

## Data Sufficiency

- 60 samples are enough for deterministic reliability probes and failure discovery.
- 60 samples are not enough for a large neural generator or broad deployment claims.

## Stage 33 Notes

Information-value probe completed with shared nearest-neighbor capacity.
