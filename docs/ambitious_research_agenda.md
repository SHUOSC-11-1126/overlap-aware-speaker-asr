# Ambitious Research Agenda: Beyond the Stable Baseline

## 1. Why We Should Go Beyond the Baseline

The stable baseline has already answered an important question: speech separation is not always beneficial. That is a real result, but it is also a starting point. The next stage should encourage agents to explore the boundary conditions, failure modes, and higher-risk systems that reveal where the baseline breaks.

This repository should now be treated as an open-ended agentic research workspace rather than a project that only needs maintenance.

## 2. Grand Research Question

Can an AI-agentic ASR system decide when to separate, when to spend more compute, when to trust speaker identity, and when to ask for repair or human review?

## 3. Direction 1: Separation Phase Diagram

- Sweep overlap ratio from 0% to 90%
- Generate a separation gain curve
- Locate the boundary where separation helps or hurts
- Output:
  - `results/tables/separation_phase_diagram.csv`
  - `results/figures/separation_phase_diagram.png`
- Research value:
  - move from isolated cases to a boundary-aware phase exploration

## 4. Direction 2: Compute-aware Cascaded Recognition

- Different routes have different cost/accuracy trade-offs
- Tier 1: cheap ASR
- Tier 2: stronger ASR only for risky cases
- Tier 3: LLM critic or manual review
- Output:
  - `results/tables/cascade_performance.csv`
  - `results/figures/cer_runtime_tradeoff.png`
- Research value:
  - shift from pure CER chasing to accuracy-cost reasoning

## 5. Direction 3: Speaker Profile / Voiceprint-assisted Risk Detection

- Use `con/pro` snippets to build light speaker profiles
- Explore known-speaker enrollment
- Detect speaker swap risk, track contamination, and attribution uncertainty
- Keep the scope bounded:
  - this is not general speaker identification
  - this is profile-assisted risk detection

## 6. Direction 4: Agentic ASR Critic and Repair Loop

- Use LLMs or local models as transcript critics
- Input:
  - transcript
  - risk report
  - glossary
- Output:
  - risk explanation
  - correction candidates
  - summary of failure mode
- Important:
  - outputs must be labeled as qualitative unless fully evaluated

## 7. Direction 5: External Mini Validation

- Use a small subset from one external dataset:
  - AISHELL-4
  - AliMeeting
  - AMI
  - LibriCSS
- Goal:
  - sanity check and domain alignment
- Record:
  - data source
  - license
  - preprocessing steps

## 8. Direction 6: GitHub / Demo / Visualization Excellence

- README hero polish
- architecture diagram
- phase diagram visualization
- demo GIF
- Streamlit dashboard
- social preview image
- presentation script

## 9. How to Evaluate Ambitious Experiments

Every ambitious experiment should explicitly state:

- research question
- hypothesis
- input
- output
- metrics
- expected failure mode
- whether it is gold / silver / demo / oracle / external
- what would still be useful even if it fails

## 10. Guiding Principle

The baseline is stable. The frontier should be bold, explicit, and well-labeled.

## 11. AudioDepth Model Zoo and Hybrid Routing

- Question: can richer audio-depth architectures or hybrid audio-text signals improve route selection?
- Why now: the first AudioDepth MVP was informative but weak.
- Outputs:
  - `results/tables/audio_depth_zoo_hybrid_features.csv`
  - `results/tables/audio_depth_zoo_training_log.csv`
  - `results/tables/audio_depth_zoo_model_status.csv`
  - `results/tables/audio_depth_zoo_performance.csv`
  - `results/figures/audio_depth_zoo_summary.md`
- Interpretation rule:
  - if the zoo still does not beat router_v2, treat that as a boundary finding rather than a failure
  - if a hybrid or cascade helps, treat it as frontier improvement, not a stable-baseline rewrite

## 12. Systematic AudioDepth-Hybrid Router

- Question: can audio-depth, transcript-instability, confidence, and cost signals form a practical routing system?
- Current evidence:
  - generated `audio_depth_stress_v1`
  - trained systematic hybrid routers
  - added bootstrap CI, cost cascade, LLM/review selector, external blocked report, and case studies
- Limitation:
  - current stress route CER is proxy evidence because real Whisper inference is unavailable in this runtime
  - simulated cost is not hardware timing evidence
