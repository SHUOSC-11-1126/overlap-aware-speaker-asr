# External Validation Candidates Plan

## Goal

Add a minimal `external_validation` frontier artifact that turns external mini validation from a future-work bullet into a concrete candidate card.

## Why This Next

This direction broadens the project again without downloading or evaluating a new dataset yet. The repository already names candidate datasets and the metadata that future agents should record:

- data source
- license
- preprocessing steps

That is enough to produce a first structured candidate table and note so the next contributor can choose an external sanity-check target quickly.

## Proposed Outputs

- `results/tables/external_validation_candidates.csv`
- `results/tables/external_validation_candidates.json`
- `results/figures/external_validation_candidates.md`

## Scope

- include AISHELL-4, AliMeeting, AMI, and LibriCSS
- record source, likely license note, fit for this project, and first preprocessing step
- label the output as `external/sanity-check`
- do not claim any external benchmark has already been run

## Verification

- add unit tests for candidate row construction
- add unit tests for markdown rendering
- run `python3 -m src.external_validation_candidates`
- run `python3 -m unittest tests.test_external_validation_candidates tests.test_demo_storyboard tests.test_llm_critic_qualitative tests.test_speaker_profile_similarity tests.test_export_meeteval_compatibility tests.test_project_harness tests.test_compute_aware_cascade -v`
