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

## 13. Controlled Route-Sensitive Benchmark

- Question: can a hybrid router prove value when the benchmark intentionally creates real route contrast?
- Current evidence:
  - 26 source snippet utterances inventoried
  - 80 controlled samples generated
  - 40 controlled samples evaluated with real faster-whisper base
  - controlled hybrid/fusion router beats router_v2 and approaches oracle
- Limitation:
  - references are currently `silver_plus_unverified`
  - the first controlled slice is separation-dominant, so future samples should add more mixed-favored and cleaned-favored cases

## 14. Balanced Route-Sensitive Benchmark v2

- Question: can a route-balanced benchmark prove that a frontier router is not simply selecting separated?
- Current evidence:
  - 240 candidate v2 samples generated
  - 120 final v2 samples generated with equal anchor families
  - 60 stratified samples evaluated with real faster-whisper base
  - balanced router CER `0.502854` versus router_v2 `0.643520`
- Limitation:
  - references remain `silver_plus_unverified`
  - cleaned oracle wins are `0`, so cleaned routing is a negative finding rather than a demonstrated win
  - AudioDepth v2 maps are `analysis_only_irm_proxy`, not deployable features

## 15. AudioDepth-Centric Routing Frontier

- Question: can AudioDepth represent overlapping speech as a depth/occlusion-like acoustic structure and provide a deployable pre-ASR gate?
- Current evidence:
  - 200 deployable mixed-only maps generated
  - feature audit shows modest route and route-gap signal
  - resnet embedding probe reaches oracle-route accuracy `0.655172`
  - Stage-1 gate reaches held-out accuracy `0.758621`
- Limitation:
  - current gate is conservative and mostly detects ambiguous/review risk
  - easy_mixed and separation_helpful recall are not yet useful
  - two-stage cascade matches router_v2 rather than improving CER
  - stronger learned overlap detection is likely needed

Update: the calibrated gate follow-up recovers some of that missing action signal. By separating route-action labels from risk flags, AudioDepth reaches easy_mixed recall `0.400000`, separation_helpful recall `0.800000`, and controlled_v2 threshold-sweep CER `0.533160` with text-probe reduction `0.716667`. The remaining risk is false-safe routing, currently `0.183333` in the sweep.

Update: the risk-guarded gate follow-up turns AudioDepth into a more safety-aware triage module. The balanced policy reaches controlled_v2 CER `0.529082`, direct-bypass false-safe `0.000000`, and text-probe reduction `0.416667`; the aggressive policy reaches CER `0.537082` with text-probe reduction `0.650000`. The Stage 31 safety audit shows the remaining high-error mixed selections come from Stage-2/review fallback rather than AudioDepth direct bypass.

Update: the generative follow-up reframes AudioDepth as a promptable acoustic-map problem rather than only a route classifier. The first-pass dataset has `60` controlled_v2 samples and `300` task rows across overlap, dominance, uncertainty, route-regret, and review-risk targets. It is worth keeping as an auxiliary interpretability frontier: promptable map MAE improves slightly over an unconditioned baseline (`0.241263` vs `0.246685`), and route-regret selection improves fixed mixed CER on the source-disjoint test split (`0.671608` vs `0.739509`). It is not yet a replacement path because false-safe mixed selections remain (`4`) and counterfactual evidence is proxy-only.

## 16. Highest-Value Next Directions

1. Manual micro-gold verification for 30-50 controlled_v2 samples.
2. Stage-2 review guard / abstention policy with verified review outcomes.
3. Cleaned-win benchmark construction.
4. Exact same-source AudioDepth counterfactual scenes for overlap and dominance.
5. MeetEval / cpWER compatibility execution.
6. External mini sanity check.
7. AST / WavLM AudioDepth probe.
8. Repository cleanup / artifact archiving.
