# When Should We Separate?

Boundary-aware, compute-aware, speaker-aware, and frontier-assisted ASR for
overlapping speech.

## Abstract

This project studies a practical question in multi-speaker speech recognition:
when should an ASR system keep the mixed audio, when should it run separated
speaker tracks, and when should it escalate to a safer route? The answer is not
"always separate." On the five-case gold benchmark, separated ASR is strongest
for NoOverlap, HeavyOverlap, and OppositeOverlap, while mixed ASR is safer for
LightOverlap and MidOverlap. The feature-based router v2 matches the post-hoc
oracle average CER on the gold cases (`0.120042`) without using CER as an input
feature. Synthetic silver and held-out split results show that the same story
must remain evidence-labeled: route selection is promising, but robustness,
external validation, and official meeting-style metrics still need care.

The team extended the baseline in several directions: boundary analysis for
where separation helps or hurts, risk-aware final selection, compute-aware and
Mode B tiered cascades, speaker-aware and cpCER-lite evaluation, MeetEval/cpWER
compatibility, speaker-profile diagnostics, LLM critic scaffolding, AudioDepth
frontier research, and OpenClaw-style agentic engineering support. The report
keeps stable mainline findings separate from exploratory and demo claims.

## 1. Research Question

Overlapping speech creates a routing problem. A single mixed ASR pass can
preserve content but lose speakers. Separation can recover masked speech, but
it can also introduce repeated fragments, insertions, and over-cleaned
transcripts. This project therefore asks:

> When should we separate, when should we keep mixed ASR, and when should the
> system escalate to a risk-aware or compute-aware route?

The current system compares and routes among:

- `mixed_whisper`;
- `separated_whisper`;
- `separated_whisper_cleaned`;
- adaptive router v1/v2;
- risk-aware final selection;
- compute-aware and Mode B cascade variants;
- optional frontier paths such as MeetEval, speaker-profile risk signals, LLM
  critic, and AudioDepth acoustic triage.

![Overlap-aware ASR route map](results/figures/report/fig1_system_route_map.png)

## 2. Benchmark and Evidence Levels

The gold benchmark contains five manually verified cases:

| case | overlap level | role in analysis |
|---|---:|---|
| NoOverlap | 0 | clean comparison case |
| LightOverlap | 1 | light cross-talk, separation can hurt |
| MidOverlap | 2 | moderate overlap, instability remains visible |
| HeavyOverlap | 3 | stronger overlap, separation tends to help |
| OppositeOverlap | 4 | competitive overlap, separated route is strongest |

The repository also contains synthetic silver and held-out synthetic split
evaluations. These are valuable for stress-testing route rules, but they are
not gold evidence. Optional frontier outputs such as MeetEval/cpWER bridges,
speaker-profile diagnostics, LLM critic notes, OpenClaw screenshots, and
AudioDepth visualizations are labeled as exploratory, compatibility, or demo
support unless directly tied to verified benchmark numbers.

| evidence level | used for | claim boundary |
|---|---|---|
| Gold benchmark | core CER, speaker CER, cpCER-lite, router comparison | primary project result |
| Synthetic silver | robustness and overfitting checks | not a gold benchmark |
| Held-out synthetic split | route stability under larger synthetic variation | silver/synthetic only |
| Optional frontier | compatibility, diagnostic, demo, and research extensions | not stable ASR claims |
| AudioDepth frontier | pre-ASR acoustic triage research | exploratory, not mainline stable |

## 3. Mainline ASR Pipeline

The mainline pipeline starts from existing mixed audio and separated speaker
tracks. It runs mixed Whisper, separated speaker-track Whisper, and a
duplicate-suppressed cleaned separated transcript. The outputs are evaluated
with CER, error-type summaries, speaker-aware CER, and cpCER-lite permutation
checks. Router decisions use observable features only; CER is reserved for
post-decision evaluation.

The most important engineering discipline is that route selection and
evaluation are separate. Router v1 uses overlap-level rules. Router v2 adds
instability features such as length inflation, duplicate-removal count,
repetition proxies, speaker length imbalance, and method disagreement. The
risk-aware selector adds a conservative deployment layer that can choose a
slightly worse CER route if the transcript looks safer and more explainable.

## 4. Core Results

On the five gold cases, the best method changes by overlap regime:

| case | best method | best CER |
|---|---|---:|
| NoOverlap | separated_whisper | 0.053957 |
| LightOverlap | mixed_whisper | 0.210714 |
| MidOverlap | mixed_whisper | 0.178947 |
| HeavyOverlap | separated_whisper | 0.109489 |
| OppositeOverlap | separated_whisper | 0.047101 |

Average CER by strategy:

| strategy | average CER |
|---|---:|
| fixed_mixed_whisper | 0.302093 |
| fixed_separated_whisper | 0.191846 |
| fixed_separated_whisper_cleaned | 0.181681 |
| risk_aware_selector | 0.134587 |
| router_v2 | 0.120042 |
| oracle_best | 0.120042 |

![Gold benchmark CER by route strategy](results/figures/report/fig2_gold_cer_strategy_comparison.png)

The central result is selective separation. Separation is helpful in heavier
overlap regimes, but under LightOverlap and MidOverlap it can amplify
insertion-heavy and repetition-heavy hallucinations. Duplicate suppression
reduces some damage but does not make separated output universally best.

## 5. Boundary-aware Analysis

The project does not stop at a leaderboard. It also studies where separation
changes from helpful to harmful. The boundary line appears through several
modules:

- `src/separation_phase_diagram.py` maps overlap regimes and delta CER.
- `src/separation_phase_boundary.py` adds LOWESS-style smoothing and bootstrap
  confidence intervals for a separation-help boundary.
- `src/router_boundary_alignment.py` checks whether router decisions agree
  with the gold boundary.
- `src/error_type_boundary_report.py` explains boundary behavior through
  insertion, deletion, substitution, and repetition patterns.
- `src/risk_aware_boundary_audit.py` checks whether conservative selection
  blocks unsafe direct routes.

![Separation boundary phase plane](results/figures/report/fig3_separation_boundary_phase_plane.png)

This boundary framing is the scientific core of the project. The goal is not
only to find the lowest average CER on five examples, but to explain why route
choice should change when overlap intensity and transcript instability change.

## 6. Speaker-aware and Permutation-aware Evaluation

Global CER collapses all speaker text into one string. That can hide speaker
attribution failures, so the project includes speaker-aware CER and cpCER-lite.

Speaker-aware CER compares each speaker track separately and reports macro CER
and speaker gap. On the gold benchmark:

| method | average speaker macro CER |
|---|---:|
| separated_whisper | 0.116538 |
| separated_whisper_cleaned | 0.124558 |

cpCER-lite checks direct vs swapped speaker mapping. In the five gold cases,
the direct mapping is always better, so the main errors are content-level
insertions and repetitions rather than speaker-swap failures.

This does not mean speaker identity is solved. Speaker-profile and voiceprint
experiments remain frontier diagnostics. Their current value is to expose weak
or near-tie risk signals, not to claim robust open-set speaker identification.

## 7. Risk-aware and Compute-aware Routing

The risk-aware selector is a reference-free final selection layer. It uses
deployment-visible signals such as method disagreement, repetition risk, length
inflation, and instability features. Its average CER (`0.134587`) is slightly
worse than router v2, but it is more conservative and easier to explain.

The compute-aware cascade line asks a different question: when should the
system spend more compute? The current costed gold analysis shows:

| strategy | average CER | relative cost vs fixed separated |
|---|---:|---:|
| fixed_mixed_whisper | 0.302093 | 0.874104 |
| fixed_separated_whisper | 0.191846 | 1.000000 |
| fixed_separated_whisper_cleaned | 0.181681 | 1.000000 |
| router_v2_costed | 0.120042 | 0.929533 |
| risk_aware_costed | 0.134587 | 0.929533 |
| budget_cascade | 0.134587 | 0.929533 |

## 8. Mode B: Three-tier Compute-aware Cascade

谢宇轩 (xyx12369) contributed the Mode B three-tier cascade. This line treats
overlap-aware ASR as a staged compute allocation problem:

| tier | purpose | trigger style |
|---|---|---|
| Tier 1 | cheap default route | always available |
| Tier 2 | stronger route | instability signals |
| Tier 3 | critic or manual review | extreme instability |

The escalation rule is reference-free: it uses observable signals such as text
length ratio, duplicate count, runtime ratio, and overlap level. CER is used
only after the route is chosen. The Mode B result is intentionally labeled
`experimental/frontier`; it is a systems design contribution, not a deployment
recommendation.

| strategy | average CER | average compute cost | automatic coverage |
|---|---:|---:|---:|
| fixed_mixed_whisper | 0.302093 | 1.00 | 100% |
| fixed_separated_whisper | 0.191846 | 2.00 | 100% |
| fixed_separated_whisper_cleaned | 0.181681 | 2.10 | 100% |
| router_v2_baseline | 0.120042 | 1.60 | 100% |
| tiered_cascade_v1 | 0.181134 | 1.92 | 100% |

![Compute-aware cascade trade-off surface](results/figures/report/fig4_compute_cascade_3d_surface.png)

## 9. MeetEval, External Validation, and LLM Frontiers

Several frontier lines extend the evaluation surface without replacing the
stable gold benchmark.

MeetEval / cpWER compatibility exports verified reference and hypothesis
segments into a meeting-evaluation-friendly format. The current bridge is
export-complete and ready for narrow diagnostic follow-up, but it does not yet
claim official cpWER completion.

External validation is framed as a tiny sanity-check path, not a full external
benchmark. Candidate work includes documented source, license, preprocessing,
and a narrow slice before any broader claim.

LLM critic and repair-loop modules are qualitative diagnostics. They can
explain risky transcripts and propose candidate repairs, but they must not
silently become the gold truth. Any repair claim needs after-the-fact
evaluation against references.

## 10. AudioDepth Frontier Study

AudioDepth, led as a frontier research direction by WU FANGZHOU, reframes
overlapping speech as time-frequency occlusion. The analogy comes from RGB-D
and depth-style visual recognition: depth is not a replacement for RGB, but an
additional view that helps reason about occlusion, distance, and boundaries.
AudioDepth asks whether a pre-ASR acoustic map can expose overlap risk before
Whisper or another ASR model has already produced an unstable transcript.

![AudioDepth 3D occlusion landscape](docs/assets/audio-depth/audio_depth_3d_occlusion_landscape.png)

The frontier work includes an AudioDepth MVP, model zoo, handcrafted features,
CNN-depth models, balanced depth models, hybrid late fusion, transcript
instability fusion, route-sensitive controlled benchmarks, real Whisper
validation, proxy-to-real gap analysis, deployable mixed-only maps, Stage-1
acoustic gating, risk-guarded sweeps, and end-to-end safety audits.

The important negative finding is that a simple CNN over AudioDepth maps did
not beat router v2. That failure is useful: it suggests that pre-ASR acoustic
maps may need handcrafted or hybrid late-fusion features rather than a small
pure CNN. AudioDepth remains Frontier Branch Only / Exploratory Research and
should not be presented as a stable mainline feature.

![AudioDepth route decision space](docs/assets/audio-depth/audio_depth_route_decision_space.png)

## 11. Agentic Engineering and OpenClaw

The repository also includes an engineering governance layer. Git hooks,
contract guards, SDD/TDD documentation, ADRs, and GitNexus-style code graph
checks protect the stable baseline while frontier work continues. OpenClaw is
the agentic engineering assistant associated with this workflow. It is shown as
qualitative/demo support, not as a benchmark result.

The most important meta-lesson is evidence discipline. The project previously
accumulated many status, handoff, receipt, and queue artifacts. The
agentic-research-entropy audit measured that drift, and the cleanup pass
demoted or archived low-value coordination records. Those artifacts are useful
for traceability, but they are not research findings.

## 12. Team Contributions in the Research Story

The report is a team artifact, not a single-line personal writeup.

| contributor | research emphasis |
|---|---|
| WU FANGZHOU / 吴方舟 | main ASR pipeline, route framing, router v1/v2, evaluation discipline, AudioDepth frontier |
| 王景宏 (ceilf6) | team lead across stable baseline and frontiers; compute-aware cascade, MeetEval/cpWER, speaker-profile diagnostics, external validation, LLM critic, demo, harness and repo guard |
| 谢宇轩 (xyx12369) | Mode B three-tier compute-aware cascade, CER-cost tradeoff, reference-free escalation, TDD coverage |

The shared contribution is the claim boundary: stable gold results, synthetic
silver checks, optional frontier scaffolds, and exploratory research are labeled
separately so the project can be ambitious without overstating evidence.

## 13. Limitations

- The gold benchmark has only five verified cases.
- Synthetic and held-out synthetic references are silver evidence, not gold.
- Router v2 matches the oracle on the gold cases, but that does not prove
  universal generalization.
- Runtime and compute measurements are repository-local and not universal
  hardware benchmarks.
- Mode B, MeetEval, speaker-profile, external validation, LLM critic, and
  AudioDepth outputs are experimental or frontier-labeled unless explicitly
  connected to verified benchmark evidence.
- AudioDepth has strong explanatory visuals and useful negative findings, but
  it is not a stable mainline router.
- OpenClaw and the harness improve engineering workflow, not ASR accuracy by
  themselves.

## 14. Conclusion

The project establishes a stable overlap-aware ASR baseline and extends it into
a broader research system. The main result is selective separation: mixed ASR is
safer under some light and moderate overlap conditions, separated ASR is
stronger under heavier overlap, and duplicate suppression can reduce but not
eliminate separated-track hallucination. Router v2 reaches the post-hoc oracle
average CER on the gold benchmark while preserving reference-free decision
making.

The broader team contribution is a research map around that result. Boundary
analysis asks where separation flips from helpful to harmful. Risk-aware and
compute-aware routes ask when a safer or more expensive path is justified. Mode
B turns that into a tiered cascade. Speaker-aware and MeetEval-compatible
metrics broaden evaluation. AudioDepth explores a pre-ASR acoustic view of
overlap risk. OpenClaw and the harness make the workflow easier to review
without confusing process with evidence.

The answer to "When should we separate?" is therefore a controlled decision,
not a fixed rule: separate when overlap and instability evidence support it,
keep mixed ASR when separation introduces hallucination risk, and escalate only
when the observable signals justify the extra cost or review.
