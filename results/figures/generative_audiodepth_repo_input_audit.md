# Generative AudioDepth Repo Input Audit

Stage 32 starts from the actual `frontier/audio-depth-router` branch state, not from assumed paths.

## Available Data Sources

- controlled_v2 manifest rows: 120
- controlled_v2 real Whisper CER rows: 60
- analysis-only AudioDepth teacher map rows: 60
- deployable mixed-only AudioDepth v2 rows: 120
- usable paired samples for this first promptable dataset: 60

## Teacher Labels

- OVERLAP_MAP and DOMINANCE_MAP use source-track-derived analysis maps.
- UNCERTAINTY_MAP is a weak map derived from teacher overlap structure and boundary gradients.
- ROUTE_REGRET uses sample-level real-Whisper CER regret vectors.
- REVIEW_RISK uses Stage-2-style review heuristics: small route gap, high minimum CER, or review-needed family.

## Mixed-only Features

- Deployable AudioDepth v2 metadata provides mixed-logmel, overlap proxy, uncertainty proxy, and summary statistics.
- Student/deployable paths are restricted to mixed audio or mixed-logmel-derived maps.

## Missing or Limited Fields

- No reliable window-level CER exists, so route regret remains sample-level.
- Speaker IDs are not separately available beyond source utterance IDs.
- Teacher maps are controlled/silver-plus analysis targets, not production labels.

## Leakage Risks

- Source tracks are allowed only for teacher-target construction.
- Student inference must not accept source-track paths.
- Splits must group rows by source utterance and counterfactual family, not by target-task rows.

## Adopted Tables

- `results/tables/controlled_v2_manifest.csv`
- `results/tables/controlled_v2_real_whisper_cer.csv`
- `results/tables/audio_depth_v2_map_metadata.csv`
- `results/tables/audiodepth_v2_metadata.csv`
- `results/tables/controlled_v2_route_gap_filtered.csv`

## Counts

- dataset rows: 300
- target quality distribution: {'oracle_source_activity': 120, 'weak_uncertainty_target': 60, 'real_whisper_sample_level_regret': 60, 'stage2_review_guard_heuristic': 60}
- target families: {'mixed_win_anchor': 15, 'separated_win_anchor': 15, 'cleaned_win_anchor': 15, 'review_needed_anchor': 15}
