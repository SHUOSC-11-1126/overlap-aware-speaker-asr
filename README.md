# When Should We Separate? Boundary-aware, Compute-aware, and Speaker-aware Adaptive ASR for Overlapping Speech

We study when speech separation helps or hurts multi-speaker ASR, and we build adaptive routing and risk-aware evaluation tools for speaker-attributed transcription.

## What This Project Is

- ASR pipeline optimization
- adaptive routing
- error type analysis
- speaker-aware evaluation
- synthetic robustness validation
- risk-aware selection

## What This Project Is Not

- not training a new ASR model
- not training a new speech separation model
- not claiming synthetic silver results as gold
- not using ground-truth CER as router input

## Main Results

### Gold Benchmark Averages

| strategy | average CER |
| --- | ---: |
| fixed_mixed_whisper | 0.302093 |
| fixed_separated_whisper | 0.191846 |
| fixed_separated_whisper_cleaned | 0.181681 |
| router_v2 | 0.120042 |
| oracle_best | 0.120042 |

### Synthetic Validation

| setting | v1 | v2 | oracle |
| --- | ---: | ---: | ---: |
| original 25 | 0.350902 | 0.167553 | 0.082239 |
| held-out split test | 0.361350 | 0.335326 | 0.115181 |

### Risk-Aware Selector

| strategy | average CER |
| --- | ---: |
| risk_aware_selector | 0.134587 |
| router_v2 | 0.120042 |
| oracle_best | 0.120042 |

## Core Findings

- Speech separation is useful, but not universally beneficial.
- `NoOverlap`, `HeavyOverlap`, and `OppositeOverlap` benefit strongly from separated speaker-track ASR.
- `LightOverlap` and `MidOverlap` degradation is mainly caused by insertion and repetition hallucination.
- `cpCER-lite` did not find speaker swap as the dominant error source in the five gold cases.
- Feature-based router v2 is more stable than overlap-only v1 on synthetic validation.
- The risk-aware selector is an explainability and deployability layer, not the best-CER result.

## How to Reproduce

Run the main evaluation chain:

```powershell
python -m src.evaluate_cer --case all
python -m src.adaptive_router_v2
python -m src.evaluate_error_types --case all
python -m src.evaluate_speaker_cer --case all
python -m src.evaluate_cpcer_lite --case all
python -m src.risk_aware_selector --case all
python -m src.router_ablation
python -m src.router_ablation_split
python -m src.project_harness
```

## Figures and Summary Files

- [Current results summary](results/figures/current_results_summary.md)
- [CER by case](results/figures/cer_by_case.png)
- [CER by method average](results/figures/cer_by_method_average.png)
- [Adaptive routing summary](results/figures/best_method_by_case.md)
- [Error type summary](results/figures/error_type_summary.md)
- [Speaker-aware summary](results/figures/speaker_cer_summary.md)
- [cpCER-lite summary](results/figures/cpcer_lite_summary.md)
- [Risk-aware summary](results/figures/risk_aware_selection_summary.md)
- [Router ablation summary](results/figures/router_ablation_summary.md)
- [Synthetic routing summary](results/figures/synthetic_routing_summary.md)
- [Synthetic split summary](results/figures/synthetic_split_routing_summary.md)

## Repository Structure

- `configs/`: project configuration
- `references/`: verified reference transcripts
- `resources/`: migrated audio inputs, snippets, and synthetic assets
- `src/`: experiment scripts and analysis utilities
- `results/`: generated transcripts, tables, figures, and summaries
- `docs/`: project docs, stage notes, skills, and maintenance guidance
- `chat_upload/`: local-only upload bundles for draft preparation

## Documentation Map

New contributors should read these files before modifying code:

- [AGENTS.md](AGENTS.md)
- [docs/project_state.md](docs/project_state.md)
- [docs/roadmap.md](docs/roadmap.md)
- [docs/maintenance_harness.md](docs/maintenance_harness.md)
- [docs/markdown_audit.md](docs/markdown_audit.md)
- [docs/README.md](docs/README.md)
- [docs/skills/README.md](docs/skills/README.md)

## Project Maintenance and Future Skills

The skill cards are not model-training prompts. They are small research and maintenance guides for future work:

- [Skill 01: Separation Phase Diagram](docs/skills/skill_01_separation_phase_diagram.md)
- [Skill 02: Compute-aware Cascade](docs/skills/skill_02_compute_aware_cascade.md)
- [Skill 03: Speaker Profile / Voiceprint-assisted Risk Detection](docs/skills/skill_03_speaker_profile_voiceprint.md)
- [Skill 04: MeetEval / cpWER Compatibility Plan](docs/skills/skill_04_meeteval_compatibility.md)

If you are continuing the project, read the docs above first, then inspect the current results, and only then decide whether a new experiment is justified.

## Notes

- The repository keeps verified references for all five benchmark cases.
- `LLM` and `RAG` are future extensions rather than the core experimental path.
- The current research focus is adaptive routing, error analysis, speaker-aware evaluation, and stability checking.
