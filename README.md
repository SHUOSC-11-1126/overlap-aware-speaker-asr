# Overlap-Aware Speaker-Attributed ASR with Adaptive Routing

This repository studies when speech separation helps multi-speaker ASR, when it hurts, and how a simple rule-based router can choose the best transcript type for a given overlap level.

## Project Overview

The project evaluates five benchmark cases:

- `NoOverlap`
- `LightOverlap`
- `MidOverlap`
- `HeavyOverlap`
- `OppositeOverlap`

We compare three transcript families:

1. `mixed_whisper`
2. `separated_whisper`
3. `separated_whisper_cleaned`

The main findings are:

- Speech separation is useful, but not universally beneficial.
- LightOverlap and MidOverlap degradation is mainly caused by insertion and repetition hallucination.
- A rule-based adaptive router reaches an average CER of `0.120042`, matching the oracle best average on this benchmark.
- Speaker-aware CER shows that the cleaned transcript helps LightOverlap and MidOverlap, while the raw separated transcript remains better for NoOverlap, HeavyOverlap, and OppositeOverlap.

## Main Results

### Global CER

| Strategy | Average CER |
| --- | ---: |
| fixed_mixed_whisper | 0.302093 |
| fixed_separated_whisper | 0.191846 |
| fixed_separated_whisper_cleaned | 0.181681 |
| oracle_best | 0.120042 |
| rule_router | 0.120042 |

### Speaker-aware CER

| Strategy | Average speaker macro CER |
| --- | ---: |
| separated_whisper | 0.116538 |
| separated_whisper_cleaned | 0.124558 |

## Figures and Summary

- [Current results summary](results/figures/current_results_summary.md)
- [CER by case](results/figures/cer_by_case.png)
- [CER by method average](results/figures/cer_by_method_average.png)
- [Adaptive routing summary](results/figures/best_method_by_case.md)
- [Error type summary](results/figures/error_type_summary.md)
- [Speaker-aware summary](results/figures/speaker_cer_summary.md)

## Quick Start

Run the full evaluation pipeline:

```powershell
python -m src.transcribe_whisper --case all --mode mixed
python -m src.transcribe_whisper --case all --mode separated
python -m src.merge_speaker_tracks --case all
python -m src.postprocess_transcript --case all --method duplicate_suppression
python -m src.evaluate_cer --case all
python -m src.adaptive_router
python -m src.evaluate_error_types --case all
python -m src.evaluate_speaker_cer --case all
python -m src.summarize_results
```

For the minimal adaptive routing path:

```powershell
python -m src.run_experiment --stage separated
python -m src.run_experiment --stage compare
python -m src.adaptive_router
```

## Repository Structure

- `configs/`: project configuration
- `resources/`: migrated audio inputs and glossary resources
- `references/`: verified reference transcripts
- `src/`: experiment scripts and analysis utilities
- `results/`: generated transcripts, tables, figures, and summaries
- `docs/`: implementation notes and stage plans
- `chat_upload/`: local-only upload bundles for draft preparation

## How to Reproduce

1. Install dependencies from `requirements.txt`.
2. Ensure the audio and reference files are present under `resources/` and `references/`.
3. Run the mixed and separated ASR stages.
4. Merge speaker tracks and apply duplicate suppression.
5. Run CER, error-type, speaker-aware, and adaptive routing analyses.
6. Open the summary markdown files in `results/figures/` and the CSV tables in `results/tables/`.

## Notes

- The repository keeps verified references for all five benchmark cases.
- `LLM` and `RAG` are treated as future extensions rather than the core experimental path.
- The current research focus is adaptive routing, error analysis, and speaker-aware evaluation.

## Project Maintenance and Future Skills

Future contributors should read these files before making changes:

- [AGENTS.md](AGENTS.md)
- [docs/project_state.md](docs/project_state.md)
- [docs/roadmap.md](docs/roadmap.md)
- [docs/maintenance_harness.md](docs/maintenance_harness.md)
- [docs/skills/README.md](docs/skills/README.md)

The skill cards are not model-training prompts. They are small research and maintenance guides for future work:

- [Skill 01: Separation Phase Diagram](docs/skills/skill_01_separation_phase_diagram.md)
- [Skill 02: Compute-aware Cascade](docs/skills/skill_02_compute_aware_cascade.md)
- [Skill 03: Speaker Profile / Voiceprint-assisted Risk Detection](docs/skills/skill_03_speaker_profile_voiceprint.md)
- [Skill 04: MeetEval / cpWER Compatibility Plan](docs/skills/skill_04_meeteval_compatibility.md)

If you are continuing the project, read those files first, then inspect the current results and only then decide whether a new experiment is justified.
