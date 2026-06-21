# Overlap-Aware Speaker ASR

## Project in One Sentence

This repository studies when speech separation helps or hurts multi-speaker ASR, and provides a documented research pipeline for adaptive routing, speaker-aware evaluation, and carefully labeled frontier experiments.

## What This Project Does

- Maintains a five-case gold benchmark for overlap-aware ASR evaluation.
- Compares mixed Whisper, separated speaker-track Whisper, and cleaned separated transcripts.
- Reports CER, error-type analysis, speaker CER, and cpCER-lite style speaker attribution checks.
- Provides adaptive router v1/v2 and a risk-aware selector for reference-free transcript choice.
- Includes compute-aware cascade analysis and Mode B cascade tiers as mainline experimental work.
- Keeps synthetic silver validation separate from gold benchmark claims.
- Provides optional scaffolding for MeetEval, LLM critic/repair, speaker-profile work, and demo support.
- Uses CI, tests, ADRs, and a harness workflow to protect the stable baseline.

## What This Project Does Not Claim

- It does not claim to train a new ASR foundation model.
- It does not claim to train a new speech separation model.
- It does not treat synthetic silver validation as gold benchmark evidence.
- It does not use ground-truth CER as a routing input.
- It does not treat frontier scaffolding, coordination records, receipts, or writebacks as stable mainline claims.
- It does not claim that `frontier/audio-depth-router` is ready to merge directly into `main`.

## Research Methodology

This project follows a **pre-registered hypothesis** research methodology for all frontier experiments:

1. **Research Question (RQ)** — stated before any code is written.
2. **Falsifiable hypotheses** with explicit success/kill criteria — what would make us abandon the direction.
3. **Implementation** — TDD-first, paired tests, reproducible `python -m src.<module>` commands.
4. **Honest reporting** — negative results are documented with the same rigor as positives. 8 of 15+ frontier studies produced clean negatives; each narrows the solution space.
5. **Literature grounding** — novelty claims are assessed against a 6-agent literature sweep (see [causal hallucination lit review](docs/frontier/causal_hallucination_probe_litreview.md)). We cite established work and scope our contributions honestly.
6. **Evidence labeling** — every result is tagged as `stable/gold`, `synthetic/silver`, `experimental/frontier`, `qualitative/demo`, or `external/sanity-check`.

## Current Status

See [docs/implementation-status.md](docs/implementation-status.md) for the detailed status matrix.
For the integrated research narrative, evidence levels, limitations, and figure
set, start with the [team research report](REPORT.md).

| Area | Status |
|---|---|
| Gold benchmark, Whisper baselines, CER/error/speaker-aware evaluation | Stable Mainline |
| Router v1/v2, risk-aware selector, compute-aware cascade | Mainline Experimental |
| Mode B / cascade tiers | Mainline Experimental |
| Synthetic validation | Mainline Experimental; silver evidence only |
| MeetEval, LLM, speaker-profile, demo support | Optional Integration / Frontier Scaffold |
| AudioDepth router | Frontier Branch Only |
| **Model scale & correction frontier (PR #860–#871)** | **experimental/frontier; base eliminates separation tax** |

## Key Visual Evidence

<p align="center">
  <img src="results/frontier/asr_llm_frontier_capstone.png" width="80%" alt="ASR×LLM+Emotion frontier capstone — five results on one canvas" />
</p>
<p align="center"><em>Figure 1: The ASR×LLM+Emotion frontier capstone — five experimental results on one canvas. <a href="docs/frontier/asr_llm_emotion_capstone.md">Full synthesis</a>.</em></p>

<p align="center">
  <img src="results/frontier/model_scale/model_scale_analysis.png" width="45%" alt="Model scale analysis — base eliminates separation tax" />
  <img src="results/frontier/separation_tax/separation_tax.png" width="45%" alt="Separation tax phase diagram" />
</p>
<p align="center"><em>Left: Whisper-base eliminates the separation tax (CER 0.200 constant across all overlaps). Right: The separation-tax phase diagram showing the heavy hallucination tail at low overlap.</em></p>

<p align="center">
  <img src="results/frontier/noise_robust_router/noise_robust_router.png" width="45%" alt="Noise-robust router — recovers 92% of oracle gap" />
  <img src="results/frontier/causal_hallucination_probe/FINDINGS.md" width="0%" alt="" />
  <img src="results/frontier/emotion_separation_tax/emotion_asr_divergence.png" width="45%" alt="Emotion-ASR divergence — separation helps emotion but hurts ASR" />
</p>
<p align="center"><em>Left: The reference-free noise-robust router recovers ~92% of the oracle gap. Right: The Emotional Separation Tax — separation helps emotion but hurts ASR at low/mid overlap (objective-dependent).</em></p>

27 experimental figures are available in `results/frontier/*/`. Each FINDINGS.md contains the full analysis with reproducible data.

### Complete Figure Gallery

<details>
<summary><strong>Click to expand all 27 frontier figures</strong></summary>

**Separation Tax & Hallucination:**
- [Separation tax phase diagram](results/frontier/separation_tax/separation_tax.png) — CER vs overlap with heavy hallucination tail
- [Hallucination router validation](results/frontier/hallucination_router/routing_curve.csv) — held-out split routing comparison
- [Hallucination cure comparison](results/frontier/hallucination_cure/cure_curve.csv) — 5-cure head-to-head
- [Noise robustness map](results/frontier/noise_robustness/noise_curve.csv) — overlap × SNR grid

**Noise-Robust Gates & Router:**
- [Spectral flatness gate](results/frontier/noise_robust_gate/noise_robust_gate.png) — broadband noise cure
- [Speaker-conditioned gate](results/frontier/speaker_conditioned_gate/speaker_gate.png) — babble cure (AUC 0.95)
- [Gate selector](results/frontier/gate_selector/gate_selector.png) — reference-free gate selection
- [Noise-robust router](results/frontier/noise_robust_router/noise_robust_router.png) — recovers ~92% of oracle gap

**Causal Hallucination Probe:**
- [Causal probe findings](results/frontier/causal_hallucination_probe/FINDINGS.md) — confident attractor mechanism

**Model Scale & Correction:**
- [Model scale analysis](results/frontier/model_scale/model_scale_analysis.png) — base eliminates separation tax
- [Error profile decomposition](results/frontier/error_profile_decomposition/error_profile_by_model.png) — both models substitution-dominated
- [Contrastive decoding](results/frontier/contrastive_decode/contrastive_analysis.png) — divergence detects but can't cure
- [Runtime cascade](results/frontier/runtime_cascade/cascade_analysis.png) — binary cliff, not smooth Pareto
- [Multi-decode voting](results/frontier/multi_decode_voter/multi_decode_analysis.png) — CR wins over agreement
- [Confidence-calibrated router](results/frontier/confidence_calibrated_router/ccr_regret_by_ratio.png) — multi-signal hurts

**Emotion Frontier:**
- [Emotion separation tax](results/frontier/emotion_separation_tax/emotion_separation_tax.png) — separation helps emotion
- [Emotion-ASR divergence](results/frontier/emotion_separation_tax/emotion_asr_divergence.png) — objective-dependent decision
- [Arousal-ASR probe](results/frontier/arousal_asr_probe/arousal_asr_probe.png) — arousal doesn't predict difficulty
- [Lexical emotion tax](results/frontier/lexical_emotion_tax/lexical_emotion_tax.png) — tri-modal comparison
- [LLM ASR critic](results/frontier/llm_asr_critic/llm_asr_critic.png) — simple beats fancy
- [Emotion-anchored repair](results/frontier/emotion_anchored_repair/emotion_anchored_repair.png) — anchoring worsens it
- [Tri-modal fusion](results/frontier/emotion_modality_fusion/emotion_modality_fusion.png) — orthogonality ≠ complementarity
- [Emotion fidelity meter](results/frontier/emotion_fidelity_meter/emotion_fidelity_meter.png) — coarse gate only
- [Gate emotion cost](results/frontier/gate_emotion_cost/gate_emotion_cost.png) — objective-blind cures
- [Objective-aware routing](results/frontier/objective_aware_routing/objective_aware_routing.png) — decoupled routing
- [Semantic emotion tax](results/frontier/semantic_emotion_tax/semantic_emotion_tax.png) — LLM reads implicit emotion
- [LLM speaker attribution](results/frontier/llm_speaker_attribution/llm_speaker_attribution.png) — sign isn't free

**Capstone:**
- [ASR×LLM+Emotion hero figure](results/frontier/asr_llm_frontier_capstone.png) — all five results on one canvas

</details>

## Frontier Highlights — ASR × LLM + Emotion + Speaker (experimental/frontier)

A 2026 frontier session explored where a *local, offline* LLM (`deepseek-r1` via ollama) and cheap
reference-free signals help overlap-aware speaker ASR. Full synthesis + deployable recipe:
[docs/frontier/asr_llm_emotion_capstone.md](docs/frontier/asr_llm_emotion_capstone.md) · hero figure:
`results/frontier/asr_llm_frontier_capstone.png`.

| Result | Outcome |
|---|---|
| [Noise-robust router](results/frontier/noise_robust_router/FINDINGS.md) (#814) | ✅ a reference-free decoder-degeneracy router beats both fixed strategies and recovers ~92% of the per-utterance oracle gap |
| [Objective-aware decoupled routing](results/frontier/objective_aware_routing/FINDINGS.md) (#823) | ✅ the separate-vs-mixed decision is *objective-dependent* — routing text by the ASR signal while always reading emotion from the separated track halves emotion distortion and cuts joint regret ~14× at equal CER |
| [Semantic Emotion Tax](results/frontier/semantic_emotion_tax/FINDINGS.md) (#831) | ✅ a local LLM reads implicit emotion ~7× more than the lexicon — an orthogonal 3rd emotion modality |
| [Tri-modal emotion fusion](results/frontier/emotion_modality_fusion/FINDINGS.md) (#835) | ◐ fusion helps the semantic target only; acoustic-arousal is the dominant reference-free emotion-damage signal |
| [Emotion-anchored repair](results/frontier/emotion_anchored_repair/FINDINGS.md) (#833) | ❌ anchoring does not cure LLM over-correction — don't blind-repair in this setting |
| [LLM speaker-attribution](results/frontier/llm_speaker_attribution/FINDINGS.md) (#838) | ◐ affect encodes who-said-what, but the sign isn't knowable reference-free |

These are `experimental/frontier` (Whisper-tiny + silver references + local `deepseek-r1`); they are not
gold-benchmark claims. The unifying thread: the cheap Whisper decoder signal is the deployable routing
lever, acoustic prosody owns acoustic emotion, and the LLM's gift is *coverage* of implicit semantics —
not free-lunch repair or attribution rules.

## Frontier Highlights — Model Scale & Correction Frontier (experimental/frontier)

A 2026 frontier session asked: **is the "when to separate?" problem real, or a tiny-model artifact?**
The answer changes the project's research direction.

| Result | Outcome |
|---|---|
| [Confidence-Calibrated Router](results/frontier/confidence_calibrated_router/FINDINGS.md) | ❌ multi-signal composites hurt; compression-ratio alone is near-optimal |
| [Multi-Decode Voting](results/frontier/multi_decode_voter/FINDINGS.md) (#858) | ❌ temperature perturbation doesn't help; CR wins (Spearman 0.781) |
| [Contrastive Decoding](results/frontier/contrastive_decode/FINDINGS.md) (#857) | ◐ divergence detects hallucination (AUC 0.765) but fallback can't cure it |
| **[Model Scale Analysis](results/frontier/model_scale/FINDINGS.md) (#859)** | **🏆 base eliminates the separation tax entirely (CER 0.200 at ALL overlaps)** |
| [Runtime Cascade](results/frontier/runtime_cascade/FINDINGS.md) (#863) | ❌ CR signal too coarse for segment selection (binary cliff, not smooth Pareto) |
| [Reference Validity](results/frontier/reference_validity/FINDINGS.md) | ✅ base's 0.200 CER is real (base and small differ 37.2% on clean audio) |
| [Error Pattern Analysis](results/frontier/base_error_correction/FINDINGS.md) (#867) | ❌ 64 unique patterns, only 9.4% recurring — 0.200 is a hard floor for correction |
| [LLM Rescoring](results/frontier/llm_base_rescore/FINDINGS.md) (#869) | ❌ catastrophic (0/26 helped, CER 0.316→0.798) — LLM rewrites instead of correcting |
| [Error Profile Decomposition](results/frontier/error_profile_decomposition/FINDINGS.md) (#865) | ◐ both models ~70% substitution-dominated; CER difference = total count, not error types |

**The key finding: the "overlap-aware speaker ASR" problem is a tiny-model artifact.** Whisper-base
(1.93× compute) produces CER=0.200 at all overlap ratios — the separation tax vanishes. The 29 frontier
routing/gating studies were compensating for a problem that disappears with marginally more compute.
The 0.200 remaining CER is a hard floor: pattern-based correction, T/S normalization, and LLM rescoring
all fail to improve it. Future frontier should focus on base+ model capabilities and external validation.

## Negative Results — Bounded Failures as Research Progress

The teacher's feedback notes: "Negative results are completely acceptable. What matters is the depth of the investigation." This project documents 8+ clean negative results, each narrowing the solution space:

| Negative Result | What it tells us | Evidence |
|---|---|---|
| LLM rescoring is catastrophic (0/26 helped, CER 0.316→0.798) | Small LLMs *rewrite* rather than *correct* — the 0.200 CER floor is not fixable by contextual understanding | [FINDINGS](results/frontier/llm_base_rescore/FINDINGS.md) |
| Runtime cascade has binary cliff, not smooth Pareto | CR signal is too coarse for segment-level escalation — just use base (1.93×) | [FINDINGS](results/frontier/runtime_cascade/FINDINGS.md) |
| Beam search raises CER under every noise type | The noise-robust cure is NOT in the decoder — it must act on the audio | [FINDINGS](results/frontier/decoder_cure_noise/FINDINGS.md) |
| Emotion-anchored repair worsens over-correction | Giving the LLM "more latitude to rewrite" causes more hallucination — #822's tax is robust | [FINDINGS](results/frontier/emotion_anchored_repair/FINDINGS.md) |
| Arousal does NOT predict ASR difficulty (r=0.002) | Emotion↔ASR is asymmetric — separation affects emotion, but emotion can't route ASR | [FINDINGS](results/frontier/arousal_asr_probe/FINDINGS.md) |
| Speaker similarity does not predict separation benefit (Pearson +0.49 → +0.08 under robust stats) | Use tail-robust statistics for ΔCER correlations | [FINDINGS](results/frontier/speaker_similarity_probe/FINDINGS.md) |
| Hallucination router loses to trivial always-trim | Once you silence-trim, knowing overlap barely matters | [FINDINGS](results/frontier/hallucination_router/FINDINGS.md) |
| Multi-decode voting doesn't beat single CR | Whisper-tiny is stably bad — temperature perturbation doesn't help | [FINDINGS](results/frontier/multi_decode_voter/FINDINGS.md) |

Each negative result is documented with pre-registered hypotheses, kill criteria, honest reporting of what failed and why, and deployable implications.

## Frontier Highlights — Causal & Internal-State Hallucination (experimental/frontier)

A 2026 frontier line looks *inside* Whisper at the separation-tax hallucination (`separation_tax` showed
a reference-free compression-ratio guard catches the catastrophic tail — but only at ~20% of the decoded
stream, *after* the repetition is emitted). Plan + cited 2025–26 literature:
[docs/frontier/causal_hallucination_probe.md](docs/frontier/causal_hallucination_probe.md).

| Result | Outcome |
|---|---|
| [Causal & internal-state hallucination probe](results/frontier/causal_hallucination_probe/FINDINGS.md) (#855) | ✅ the separation-tax loop is a *confident* attractor (catastrophic routes decode at higher avg_logprob / lower token entropy than clean), and a token-id **repetition lock-in trip-wire** fires at ~2% of the stream vs ~20% for compression-ratio (~10× earlier); at tight streaming-realistic causal caps the internal-state detector beats output-CR, at loose caps CR's broader coverage wins — neither alone dominates |

The honest deployable sharpening: gate a streaming overlap-aware ASR system on the lock-in trip-wire for
the Mode-R repetition tail, keep compression-ratio for the Mode-N non-repetition minority. The
confident-loop mechanism extends (not discovers) the 2025–26 attractor line; the token-id lock-in
trip-wire and the offline-router gain-decay-under-prefix-forcing analysis are the novel slots.

## Frontier Highlights — AudioDepth Router (frontier branch only)

AudioDepth is a second frontier branch. It treats overlapping speech as a
time-frequency occlusion problem, inspired by depth-style representations in
visual recognition, and asks whether pre-ASR acoustic maps can help decide when
to use mixed ASR, separated ASR, cleaned routes, or review/fallback paths.

See [AudioDepth Router Exploratory Study](docs/frontier/audio-depth-router.md)
for the research motivation, visualization design, experiment stages,
controlled results, limitations, and merge boundaries. See also the
[team research report](REPORT.md) for how AudioDepth relates to the stable ASR
router, compute-aware cascade, LLM/emotion frontier, and team-level evidence
hierarchy.

AudioDepth is not currently a stable mainline claim and should not be merged
from `frontier/audio-depth-router` without separating code, documentation,
lightweight examples, tests, and large artifacts.

## Literature & Related Work

This project builds on and relates to the following research lines:

**Speech separation and ASR:**
- Sato et al. (Interspeech 2021, "Should We Always Separate?") — established that separators inject artifacts below an SIR/SNR crossover. Our Phase 1 reproduces and extends this to a continuous phase diagram with mechanistic analysis.
- Kolbaek et al. (2017) — oracle separation methodology. We follow their approach of studying oracle bounds before realistic separators.

**Whisper hallucination:**
- Koenecke et al. (ACM FAccT 2024, "Careless Whisper") — hallucinations concentrate in silent regions as phrase repetition. Our separation tax is the separation-induced variant.
- Baranski et al. (ICASSP 2025) — a recurring finite "bag of hallucinations" covers most cases.
- Aparin et al. (2026, arXiv:2606.07473) — Whisper's filter fails on confident hallucinations; encoder/SAE latents separable pre-loop.
- Waldendorf et al. (ACL 2026 Findings, arXiv:2604.19565) — uncertainty metrics fail in the clean/confident regime.
- Wang et al., Calm-Whisper (Interspeech 2025, arXiv:2505.12969) — 3/20 decoder heads cause >75% of non-speech hallucinations.
- Viakhirev et al. (2026, arXiv:2604.08591) — Compression-Seeking Attractor with self-attention rank collapse.
- Corpataux et al. (OpenReview 2026) — per-token Local Confidence Drop for trajectory detection.
- Ahn et al., Whisper-CD (Interspeech 2026, arXiv:2603.06193) — training-free token-level contrastive decoding.

**ASR × LLM:**
- GenSEC-LLM challenge (arXiv:2409.09785, 2024) — post-ASR emotion recognition as an LLM task.
- R3 (arXiv:2409.15551, 2024) — couples ASR error-correction with emotion recognition.
- VoxEmo (arXiv:2603.08936, 2026) — benchmarks speech emotion recognition with speech LLMs.

**Emotion in speech:**
- Russell (1980), Scherer (2005) — dimensional emotion tradition (arousal/valence). Our gain-invariant prosody approach follows this line.

Full literature review with per-hypothesis novelty assessment:
[docs/frontier/causal_hallucination_probe_litreview.md](docs/frontier/causal_hallucination_probe_litreview.md).
Emotion frontier reading list: [docs/emotion_frontier.md](docs/emotion_frontier.md) (References section).

## Quickstart

Use a Python version aligned with CI, preferably Python 3.12. The core install is:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m src.project_harness
```

If you see `ModuleNotFoundError: No module named 'yaml'`, install the core requirements first; it is usually an environment setup issue, not evidence that the project code is broken.

Full setup, optional dependencies, smoke tests, demo setup, and troubleshooting are in [docs/quickstart.md](docs/quickstart.md).

## Results

Start with [docs/results-index.md](docs/results-index.md) and [results/README.md](results/README.md).

Recommended result entry points:

- [Team research report](REPORT.md)
- [Current results summary](results/figures/curated/current_results_summary.md)
- [Adaptive routing summary](results/figures/curated/best_method_by_case.md)
- [Risk-aware selector summary](results/figures/curated/risk_aware_selection_summary.md)
- [Compute-aware cascade summary](results/figures/curated/compute_aware_cascade_summary.md)
- [Mode B cascade tiers summary](results/figures/curated/cascade_tiers_summary.md)

Historical wave, receipt, writeback, checklist, and demo presentation records have been moved under `results/figures/archive/`. They are useful for traceability, but they are not final benchmark claims.

## Repository Map

| Path | Purpose |
|---|---|
| `src/` | Research scripts, evaluation modules, routing logic, and generated frontier helpers |
| `tests/` | Unit tests and harness coverage |
| `docs/` | Curated setup, status, result, branch, governance, and archive documentation |
| `docs/harness/` | Development harness: hooks, knowledge-base contract, SDD, and TDD workflow |
| `docs/adr/` | Architecture and approach decision records |
| `resources/` | Small audio inputs, snippets, synthetic assets, and references |
| `results/` | Curated result summaries plus archived generated records |
| `scripts/` | Harness and maintenance support scripts |

## Mainline vs Frontier

- `main` is the stable review baseline.
- `frontier/audio-depth-router` is a high-risk experimental branch with many artifacts and model-like outputs; it needs separate review and should be split before any merge.
- `wave*`, `frontier/wave*`, and `demo-wave*` branches are mostly historical coordination/writeback trails.
- `improve/*` and `cursor/*` branches with no diff against `main` are cleanup candidates, but this pass does not delete remote branches.

See [docs/branch-audit.md](docs/branch-audit.md) for the branch cleanup policy.

## Documentation

| Need | Read |
|---|---|
| Run locally | [docs/quickstart.md](docs/quickstart.md) |
| Read the full team report | [REPORT.md](REPORT.md) |
| Understand what is implemented | [docs/implementation-status.md](docs/implementation-status.md) |
| Find core results | [docs/results-index.md](docs/results-index.md) |
| Understand result storage | [results/README.md](results/README.md) |
| Understand branch status | [docs/branch-audit.md](docs/branch-audit.md) |
| Understand archive policy | [docs/archive-plan.md](docs/archive-plan.md) |
| Review course contribution records | [CONTRIBUTIONS.md](CONTRIBUTIONS.md) |
| Review AudioDepth frontier strategy | [docs/frontier/audio-depth-router.md](docs/frontier/audio-depth-router.md) |
| Review governance | [docs/harness/](docs/harness/) and [docs/adr/](docs/adr/) |

Historical planning and generated coordination records are indexed from [docs/archive/README.md](docs/archive/README.md).

## Harness Engineering Loop

> Developed with reference to [code-tape](https://github.com/ceilf6/code-tape).

An always-on development harness keeps the stable baseline safe while frontier work continues. It has four pillars (full docs in [`docs/harness/`](docs/harness/README.md)):

- **Git hooks** — `pre-commit` runs the fast test gate and `pre-push` runs the contract + full test gate, installed via `core.hooksPath`. Bootstrap once with `make agent-bootstrap`.
- **Knowledge base** — GitNexus indexes the code graph so a change's cascade is visible before editing critical modules ([contract](docs/harness/knowledge_base_contract.md)).
- **SDD** — an authority-document hierarchy plus [ADRs](docs/adr/README.md) anchor what agents treat as ground truth ([spec](docs/harness/sdd.md)).
- **TDD** — the contract mechanically requires a paired test for every critical code change, red → green → refactor ([spec](docs/harness/tdd.md)).

The full loop is `issue → PR → repo-guard CR → respond` ([workflow](docs/harness/workflow_spec.md)). code-tape's engineering-camp scoring and auto-merge automation is intentionally out of scope.

### Implementation Details (943 lines across 5 Python modules)

| Module | Lines | Purpose |
|---|---|---|
| `scripts/harness/contract_rules.py` | 424 | Classifies files into 6 critical-skeleton categories (router-core / evaluation-core / harness / references / gold-results / authority-docs). Changes to critical code trigger the paired-test gate. |
| `scripts/harness/contract_check.py` | 238 | Runs on every `git push`; compares staged diff against contract rules; integrates with CI as `Contract Guard`. |
| `scripts/harness/quality.py` | 123 | Unified command surface: `quality.py {predev,precommit,prepush,ci,local}`. Makefile: `make quality-{predev,precommit,prepush}`. |
| `scripts/harness/entropy_guard.py` | 128 | Advisory pre-dev check that warns when changes add ceremony without substance. |
| `scripts/harness/install_hooks.py` | 30 | Sets `core.hooksPath=.githooks` automatically. |

The harness enabled the entire frontier research workflow: every one of the 40+ frontier PRs passed through this gate, and the contract prevented any critical-skeleton change from landing without paired tests.

## Emotion Frontier (experimental)

> Label: `experimental/frontier`. Full plan, findings, and cited 2025–2026 reading in
> [`docs/emotion_frontier.md`](docs/emotion_frontier.md).

Extends the project's "when should we separate?" question from ASR-CER into **emotion**. Offline,
label-free (clean-source prosody / reference text are the ground truth, mirroring CER):

### The Seven Emotion Findings (#14–#20)

| # | Finding | RQ | Outcome | Evidence |
|---|---|---|---|---|
| 14 | **Emotional Separation Tax** | Does separation preserve or distort per-speaker emotion? | ✅ Separation *helps* emotion at all overlaps (opposite of ASR tax). Decision is **objective-dependent**. | [FINDINGS](results/frontier/emotion_separation_tax/FINDINGS.md) · [figure](results/frontier/emotion_separation_tax/emotion_asr_divergence.png) |
| 15 | **Arousal ≠ ASR-difficulty** | Does acoustic arousal predict ASR difficulty? | ❌ Pearson(arousal, CER) = 0.002. Emotion is a consequence to *preserve*, not a routing feature. | [FINDINGS](results/frontier/arousal_asr_probe/FINDINGS.md) · [figure](results/frontier/arousal_asr_probe/arousal_asr_probe.png) |
| 16 | **Lexical emotion + tri-modal tax** | Can regex/lexicon valence + acoustic arousal jointly characterize the tax? | ◐ Lexical arm underpowered (fires on 2/16 snippets). Motivates the LLM reader. | [FINDINGS](results/frontier/lexical_emotion_tax/FINDINGS.md) · [figure](results/frontier/lexical_emotion_tax/lexical_emotion_tax.png) |
| 17 | **LLM × ASR critic** | Can a local LLM serve as reference-free QE and repair? | ❌ LLM judge dominated by free compression-ratio signal. GER repair net-harms. Simple beats fancy. | [FINDINGS](results/frontier/llm_asr_critic/FINDINGS.md) · [figure](results/frontier/llm_asr_critic/llm_asr_critic.png) |
| 18 | **Objective-aware decoupled routing** | Can decoupling text-route and emotion-route recover both? | ✅ Decoupled keeps same CER but halves emotion distortion, cutting joint regret ~14×. | [FINDINGS](results/frontier/objective_aware_routing/FINDINGS.md) · [figure](results/frontier/objective_aware_routing/objective_aware_routing.png) |
| 19 | **Emotion fidelity meter** | Can we estimate emotion fidelity with NO clean reference? | ◐ Usable coarse gate (r=−0.51) but weak graded predictor (r=−0.20) that saturates. | [FINDINGS](results/frontier/emotion_fidelity_meter/FINDINGS.md) · [figure](results/frontier/emotion_fidelity_meter/emotion_fidelity_meter.png) |
| 20 | **Gate emotion cost** | Do CER-tuned hallucination-cure gates damage emotion? | ◐ Both gates cure CER AND damage emotion. Speaker gate dominates on both axes. | [FINDINGS](results/frontier/gate_emotion_cost/FINDINGS.md) · [figure](results/frontier/gate_emotion_cost/gate_emotion_cost.png) |

### Design Choices

- **Why gain-invariant prosody?** Standard SER models require labeled training data, which doesn't exist for our overlap-controlled debate corpus. We operationalize emotion as gain-invariant acoustic prosody (arousal-side), using the clean source's own prosody as reference — following the dimensional emotion tradition (Russell, 1980; Scherer, 2005).
- **Why deepseek-r1:7b via ollama?** Required: (a) fully offline (no API calls, privacy); (b) reasoning capability for emotion interpretation; (c) small enough (7B) for reproducible local experimentation. Alternatives considered: GPT-4/Claude (online, not reproducible), Llama-3-8B (no reasoning traces).
- **Why Whisper-tiny for emotion experiments?** Same ASR outputs as the separation-tax baseline for cross-study comparability. Since the separation tax is tiny-specific, using tiny means emotion findings are *conservative* — they study emotion under worst-case ASR errors.

## Research Entropy Audit (meta-research)

> Label: `experimental/frontier`. Full analysis in [`docs/frontier/agentic_research_entropy.md`](docs/frontier/agentic_research_entropy.md).

When an autonomous agentic loop ran unsupervised on this repo, ~89% of `src/*.py` files drifted into
self-referential ceremony (handoff/receipt/coordination/completion-summary) with **zero computation**.
This is a *research integrity* issue — ceremony creates an illusion of progress.

**Metrics:** Entropy saturation 0.894 → 0.035 after cleanup; degeneration index 0.46 → 0.00; tests 3,304 → 825 all green.

**Preventive guard:** `scripts/harness/entropy_guard.py` — advisory check that warns when changes add ceremony without substance. Integrated into `make quality-predev`.

**Module:** `src/research_entropy_audit.py` — two-signal classifier (filename + content) + git timeline visualization + bounded degeneration index.

## OpenClaw: Agentic Engineering Assistant

> Illustrative tooling shown for context, not a benchmark result. Label: `qualitative/demo`.

OpenClaw ("ceilf6's claw") is the agentic engineering assistant that drives
the kind of workflow described in the Harness Engineering Loop above. Instead
of living only in a terminal, it runs as chat 智能体 (agents) inside the IM tools
a team already uses — 飞书 (Feishu) and 大象 — so issue triage, code review, and
progress reporting happen in the conversation rather than in a separate
dashboard.

It exposes named agents driven by slash commands:

- **`FrontAgent`** — reference-free code review that returns a risk summary
  (Blocker / Critical counts plus concrete fixes, e.g. flagging a
  dynamic-`RegExp` ReDoS in a test file) and `/progress-reporter` group updates
  that track each member's current issue, unclaimed work, recently merged PRs,
  and milestones.
- **坤坤** — a conversational agent for handover notes, material organization, and message polishing.

Agents call LLM backends (e.g. `gpt-5.5`) through a provider abstraction and
follow the same `issue → PR → repo-guard CR → respond` loop documented above.
OpenClaw is developed alongside [code-tape](https://github.com/ceilf6/code-tape).

<p align="center">
  <img src="assets/飞书中的OpenClaw-1.jpg" width="40%" alt="OpenClaw code review with risk scoring in Feishu" />
  <img src="assets/大象中的OpenClaw.jpg" width="40%" alt="OpenClaw conversational agent 坤坤 in 大象" />
</p>

## Contributors

Contributor details live in [CONTRIBUTIONS.md](CONTRIBUTIONS.md). The README
intentionally keeps contributor history short so the project entry point remains
readable.

- [Contributions](CONTRIBUTIONS.md): team contribution statements and course submission evidence.

## License / Citation / Acknowledgements

**License:** This project is developed for academic coursework. All code is provided as-is for educational purposes.

**Citation:** If you use this work, please cite:
```
@software{overlap_aware_speaker_asr,
  title={Overlap-Aware Speaker ASR: When Does Separation Help?},
  author={王景宏, 吴方舟, 谢宇轩, 邵俊霖, 梁跃川, 张浩豪},
  year={2026},
  url={https://github.com/ceilf6/overlap-aware-speaker-asr}
}
```

**Acknowledgements:** Developed with reference to [code-tape](https://github.com/ceilf6/code-tape) for the engineering harness. ASR powered by [Whisper](https://github.com/openai/whisper). Local LLM via [ollama](https://ollama.ai/) + [deepseek-r1](https://github.com/deepseek-ai/DeepSeek-R1). Speaker embedding via [Resemblyzer](https://github.com/resemble-ai/Resemblyzer).
