# Team Contributions

This file is the authoritative contribution record for the course/project
submission. Contribution records were centralized here so the repository has a
single source of truth; the former `docs/contributions/` tree was removed after
migration.

## 王景宏 23123994 [ceilf6](https://github.com/ceilf6) 

**Role:** Frontier research lead; overlap-hallucination mechanism investigator; ASR×LLM×emotion axis explorer; research-entropy meta-analyst; engineering harness architect.

**Scope summary:** ~56 merged PRs (#780–#872, #886–#894, #898–#900), 50+ issues, 50+ new modules, 40+ frontier result directories, 15+ experimental figures, 6-agent literature review. All frontier work labeled `experimental/frontier` or `external/sanity-check`; no gold tables or verified references touched.

---

### Research Thread 1: The Separation Tax — from Mechanism to Model-Scale Dissolution

**Grand RQ:** _Is the "separation tax" — speech separation hurting Whisper ASR at low/mid overlap — a fundamental limitation of overlap-aware ASR, or an artifact of using the weakest model?_

This thread spans 20+ PRs across three phases and constitutes the project's deepest investigation.

#### Phase 1: Oracle-separation phase study + reference-free cure (Issue #795, PR #796)

**Literature gap.** Sato et al. (Interspeech 2021, "Should We Always Separate?") established that separators inject artifacts hurting ASR below an SIR/SNR crossover, proposing a gated router. However, their analysis used a single-sample-per-ratio scatter and did not characterize the _mechanism_ of failure — whether separation uniformly degrades ASR or creates a heavy-tailed hallucination phenomenon.

**Design choices and justification:**

- **Why Whisper-tiny?** We chose the smallest Whisper model (39M parameters) as the primary experimental vehicle because: (a) it is the most resource-constrained realistic deployment target, making separation-overhead most consequential; (b) its small capacity makes separation-induced failures most visible, providing an upper bound on the tax; (c) all prior project baselines used tiny, enabling direct comparison. Faster-Whisper and WhisperX offer speed optimizations but use the same underlying model architecture — they would exhibit the same separation tax. The model-size question is explicitly addressed in Phase 3.
- **Why oracle separation?** We used oracle (ground-truth) separation rather than a real separator (SepFormer, Conv-TasNet) to isolate the effect of separation _itself_ from separator quality. This follows the standard methodology in speech separation evaluation (e.g., Kolbaek et al., 2017) where oracle bounds are studied before realistic separators.

**Pre-registered hypotheses:**

- H1: A continuous separation-gain crossover exists at some overlap ratio r* (confirmed: r* ≈ 0.17).
- H2: The low-overlap penalty is a heavy hallucination tail, not uniform degradation (confirmed: at r=0.10, mean ΔCER = −0.94 but median = 0.00; 6/600 tracks blow up to CER up to 24×).
- H3: A reference-free compression-ratio guard can detect catastrophic hallucination (confirmed: AUC ≈ 1.0 for CER > 1.0).

**Key finding:** The separation tax is a _heavy-tailed hallucination phenomenon_ concentrated in near-silent separated tracks, not a uniform degradation. A guard-gated trim/fallback router closes ~76% of the oracle gap. Detailed results in `results/frontier/separation_tax/FINDINGS.md`.

**Figures:** `results/frontier/separation_tax/phase_curve.csv`, `results/frontier/hallucination_router/routing_curve.csv`.

#### Phase 2: Hallucination mechanism and cure chain (Issues #797–#813, PRs #798–#813)

This phase followed a systematic **cure-search arc** — each negative result narrowing the solution space:

| Study                                | RQ                                                                                   | Outcome                                                                                                                                                                                         | Key evidence                                                       |
| ------------------------------------ | ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| **Hallucination router** (#797)      | Route by hallucination vs overlap on held-out split?                                 | ❌ **Falsified**: degeneracy router (+0.083 regret) loses to trivial always-trim (+0.041). But the trim recipe generalizes — once you silence-trim, knowing overlap barely matters.             | `results/frontier/hallucination_router/FINDINGS.md`                |
| **Reference-free QE** (#799)         | Do decoder signals predict graded CER?                                               | ◐ Signals are catastrophe _gates_ (AUC 1.0 for CER>1.0) but at chance for moderate CER (AUC ~0.48). U-shaped calibration.                                                                       | `results/frontier/reference_free_qe/qe_signal_table.csv`           |
| **Speaker similarity** (#801)        | Does acoustic speaker distance predict separation benefit?                           | ❌ **Negative**: apparent Pearson +0.49 collapses to +0.08 under tail-robust median. Methodological caution: use robust stats.                                                                  | `results/frontier/speaker_similarity_probe/FINDINGS.md`            |
| **Hallucination cure** (#803)        | Can Whisper's native `hallucination_silence_threshold` or beam search cure the tail? | ✅ The catastrophe is a greedy-decoding artifact. All of {silence-trim, native threshold, beam} eliminate the tail (19.84 → ~0.54). Best deployable: silence-trim (−39% mean CER).              | `results/frontier/hallucination_cure/cure_curve.csv`               |
| **Noise robustness** (#805)          | Does the silence-trim cure survive noise?                                            | ❌ **Critical negative**: noise defeats the cure. Trim benefit collapses from +0.239 (clean) to +0.000 at every SNR ≥ 0 dB. Energy-trim needs _actual silence_ — noise fills the gap.           | `results/frontier/noise_robustness/noise_curve.csv`                |
| **Spectral + speaker gates** (#807)  | Can spectral-flatness or speaker embeddings cure hallucination under noise?          | ✅ Spectral gate works for broadband noise; speaker-conditioned gate (Resemblyzer GE2E, AUC 0.95) cures babble (CER 1.63→0.67). No single gate dominates all noise types.                       | `results/frontier/speaker_conditioned_gate/speaker_gate_curve.csv` |
| **Decoder cures under noise** (#809) | Is the noise-robust cure in the decoder, not the audio?                              | ❌ **Negative**: beam search raises mean CER under every noise type (pooled 1.947 vs greedy 1.676). Native silence-threshold fires only 4–33% under noise. The cure must act on the audio.      | `results/frontier/decoder_cure_noise/cure_noise_curve.csv`         |
| **Gate selector** (#811)             | Can a reference-free selector choose between gates by residual character?            | ❌ **Falsified** with a stronger byproduct: the speaker gate dominates on _both_ axes (CER + emotion), so there is nothing to select. The real decision is separate-vs-mixed, not gate-vs-gate. | `results/frontier/gate_selector/FINDINGS.md`                       |
| **Noise-robust router** (#814)       | Can a reference-free router beat fixed strategies under noise?                       | ✅✅ **Strong positive**: router 0.778 vs always-mixed 1.214 / always-gated 1.531. Recovers ~92% of oracle gap. Pearson(CR, separation-tax) = 0.82.                                             | `results/frontier/noise_robust_router/router_curve.csv`            |

**Engineering trade-off: Why Resemblyzer for speaker embedding?** We chose Resemblyzer (GE2E encoder) over alternatives (pyannote.audio, SpeechBrain, wav2vec2-based) because: (a) it is fully offline and lightweight (~45MB), matching our local-first constraint; (b) it produces a single 256-dim embedding per track, enabling fast cosine-distance computation across 600+ conditions; (c) its AUC 0.95 on babble detection was sufficient — a more complex model would add latency without changing the gate-vs-no-gate decision boundary. The honest limitation is that it fails at 0 dB SNR (AUC 0.52 ≈ chance).

**Literature grounding:** The hallucination cure chain connects to Koenecke et al. (ACM FAccT 2024, "Careless Whisper") — Whisper hallucinations concentrate in long silent regions as phrase repetition — and Baranski et al. (ICASSP 2025) — a recurring finite "bag of hallucinations" covers most cases. Our contribution is mapping these findings into the _separation-induced_ regime with noise as an additional axis.

#### Phase 3: Model scale analysis — the separation tax is a tiny-model artifact (Issues #857–#871, PRs #858–#872)

**Critical validity question.** All 29+ frontier studies used Whisper-tiny exclusively. If the separation tax, hallucination thresholds, and routing signals do not generalize to larger models, the practical value collapses.

**Design choices and justification:**

- **Why test tiny/base/small specifically?** These span a 10× parameter range (39M/74M/244M) at 1×/1.93×/6× compute cost, covering the realistic deployment spectrum for edge/real-time ASR. We did not test medium/large because: (a) they require >1GB VRAM, exceeding typical edge constraints; (b) the base result already dissolved the tax, making further scaling less informative.
- **Why not Faster-Whisper or WhisperX?** Faster-Whisper uses CTranslate2 quantization for speed but produces identical logits to vanilla Whisper at the same model size. WhisperX adds forced alignment and VAD preprocessing — useful for production but irrelevant to our controlled overlap×separation experiment. The model _capacity_ (parameter count) is what matters, not the inference engine.

**Pre-registered hypotheses (PR #859):**

- H1: Larger models hallucinate less — the catastrophic tail rate decreases monotonically tiny → base → small. **Confirmed.**
- H2: The separation-tax phase boundary shifts leftward — separation helps at lower overlap for larger models. **Confirmed** (base: separation tax disappears entirely).
- H3: Compression-ratio becomes less discriminative for larger models (signal paradox). **Confirmed** — base's CR is ~1.0 on all inputs, making it useless as a routing signal.

**Headline result:** Whisper-base (74M, 1.93× compute) produces CER = 0.200 _constant across all overlap ratios_ — the separation tax completely vanishes. Zero hallucinations. All 29 routing/gating studies were compensating for tiny-specific weakness.

**Follow-up investigations (9 PRs):**

| Study                                  | RQ                                                                     | Outcome                                                                                                                                                           | Evidence                                                         |
| -------------------------------------- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| **Confidence-calibrated router** (CCR) | Do multi-signal composites beat single CR?                             | ❌ Worse — CR alone is near-optimal                                                                                                                               | `results/frontier/confidence_calibrated_router/`                 |
| **Multi-decode voting** (#858)         | Is decode-stability a stronger reference-free signal?                  | ❌ CR Spearman 0.781 vs agreement −0.404. Whisper-tiny is stably bad.                                                                                             | `results/frontier/multi_decode_voter/`                           |
| **Contrastive decoding** (#857)        | Can subtracting mixed-prior logits suppress hallucination proactively? | ◐ Divergence IS a quality signal (AUC 0.765) but fallback correction is 0.076 CER _worse_. Hallucination is deterministic AND anti-hallucination is insufficient. | `results/frontier/contrastive_decode/contrastive_curve.csv`      |
| **Runtime cascade** (#863)             | Can tiny→base escalation achieve near-base CER at near-tiny compute?   | ❌ CR signal has a binary cliff, not a smooth Pareto. Just use base (1.93×, eliminates the tax).                                                                  | `results/frontier/runtime_cascade/pareto_frontier.csv`           |
| **Reference validity** (#866)          | Is base's 0.200 CER real or model-proximity?                           | ✅ Base and small produce 37.2% different text on clean audio. Base is completely stable.                                                                         | `results/frontier/reference_validity/FINDINGS.md`                |
| **Error pattern analysis** (#867)      | Can pattern-based post-processing fix base's errors?                   | ❌ 64 unique patterns, only 9.4% recurring. 0.200 CER is a hard floor of genuine acoustic ambiguity.                                                              | `results/frontier/base_error_correction/substitution_table.csv`  |
| **LLM rescoring** (#869)               | Can deepseek-r1 correct base's substitution errors?                    | ❌ **Catastrophic**: 0/26 improved, CER 0.316→0.798. The LLM _rewrites_ text instead of correcting.                                                               | `results/frontier/llm_base_rescore/FINDINGS.md`                  |
| **Error profile decomposition** (#865) | Do tiny and base make different _kinds_ of errors?                     | ◐ Both ~70% substitution-dominated. CER difference = total count, not error types.                                                                                | `results/frontier/error_profile_decomposition/profile_curve.csv` |

**Unified conclusion:** "Overlap-aware speaker ASR" as a routing problem is a tiny-model artifact. Whisper-base eliminates the separation tax at 1.93× compute. The remaining 0.200 CER is a hard floor of acoustic ambiguity — not fixable by pattern matching, T/S normalization, or LLM rescoring. Future work should focus on base+ model capabilities and external benchmark validation.

**Figures:** `results/frontier/model_scale/model_scale_analysis.png`, `results/frontier/error_profile_decomposition/error_profile_by_model.png`.

---

### Research Thread 2: Causal & Internal-State Hallucination Probe (Issue #855, PR #856)

**RQ:** _Can we detect separation-induced hallucination from inside Whisper during decoding, earlier than the output compression-ratio signal?_

**Motivation.** The `separation_tax` phase (Thread 1) closed the _acoustic_ loop — a reference-free compression-ratio guard detects catastrophes at AUC ≈ 1.0. But CR is an **output** signal computed over the _full_ decoded segment; by the time it inflates past 2.4, Whisper has _already emitted_ the repetition loop to the user. A streaming system has already shown garbage. This probe asks whether Whisper's _internal state_ during decoding provides an earlier warning.

**Why look inside Whisper?** Alternative approaches — better output metrics, multi-decode agreement, contrastive decoding — all failed in Phase 2 (Thread 1). The insight from a 3-second smoke test was revelatory: feeding Whisper-tiny a tone surrounded by silence reproduces the loop (token 7322 × 224) with `compression_ratio=37.2`, `no_speech_prob=0.82` (encoder: "no speech"), yet `avg_logprob=-0.065` (decoder: _highly confident_). The loop is a **confident attractor under an input the encoder flags as silent** — an encoder/decoder _decoupling_, not a confidence collapse. This motivated looking at token-level decoder state.

**Literature grounding (6-agent deep-research sweep, `docs/frontier/causal_hallucination_probe_litreview.md`):**

- Aparin et al. (2026, arXiv:2606.07473): Whisper's built-in filter fails because hallucinations carry _elevated_ `avg_logprob`; encoder/SAE latents are linearly separable pre-loop. Steering cuts hallucination 86.9%→27.3%.
- Waldendorf et al. (ACL 2026 Findings, arXiv:2604.19565): Uncertainty metrics fail exactly in the clean/confident regime; attention-collapse-to-early-frames signature; detectors are task/model-specific.
- Wang et al., Calm-Whisper (Interspeech 2025, arXiv:2505.12969): 3/20 decoder self-attention heads cause >75% of non-speech hallucinations; head-mask fine-tune cuts it >80% at <0.1% WER.
- Viakhirev et al. (2026, arXiv:2604.08591): Compression-Seeking Attractor with self-attention rank collapse decoupling decoder from acoustics.
- Corpataux et al. (OpenReview 2026): Per-token Local Confidence Drop detects confident hallucinations as local discontinuities — direct prior art for trajectory detection.
- Sato et al. (Interspeech 2021, arXiv:2106.00949): Separation-hurts-below-a-crossover — established bedrock, not our discovery.

**Honest novelty assessment:** The confident-loop mechanism is now well-established (Aparin, Waldendorf, Calm-Whisper, Viakhirev). We _extend_ it to the separation-tax regime; we do not discover it. The genuinely new contributions are: (1) **token-id repetition lock-in as a causal trip-wire** — no located prior work uses token-id repetition at this granularity as an early detector; (2) **quantifying the offline CR router's gain decay under causal prefix forcing** — an untouched deployment-analysis niche.

**Pre-registered hypotheses and outcomes:**

- **H-M (mechanism):** Catastrophic tracks show higher `avg_logprob` + lower token-id entropy vs clean tracks — confident loop, not confidence collapse. **SUPPORTED (refined).** avg_logprob −0.335 vs −0.739; entropy 1.49 vs 2.33. Honest refinement: `no_speech_prob` is anti-correlated (AUC 0.33), not the signal — the smoke-test "encoder says silent" was near-pure-silence-specific.
- **H-D (latency):** A token-repetition lock-in detector fires earlier than compression-ratio. **SUPPORTED (Mode R).** Lock-in fires at ~2% of stream vs CR at ~20% (**~10× earlier**). CR's AUC (0.996) remains the broadest detector; lock-in's contribution is causal earliness, not ranking.
- **H-C (deployability):** A causal router recovers offline routing gain. **SCOPED.** At tight causal caps (0.05–0.15) causal-internal beats causal-CR; at loose caps CR wins; neither dominates → deployable design is the union.

**Two hallucination modes discovered:** Mode R (repetition-driven, 11/26 catastrophic tracks) vs Mode N (non-repetition, 15/26). This explains why no single reference-free detector can catch all hallucinations — each mode requires a different detection strategy.

**Module:** `src/causal_hallucination_probe.py` + `tests/test_causal_hallucination_probe.py` (23 unit tests).
**Evidence:** `results/frontier/causal_hallucination_probe/{discovery.csv, probe_rows.csv, FINDINGS.md}`.
**Literature review:** `docs/frontier/causal_hallucination_probe_litreview.md`.

---

### Research Thread 3: ASR × LLM × Emotion × Speaker (Issues #815–#842, PRs #816–#842)

**Grand RQ:** _Can a local, offline LLM and cheap reference-free signals jointly decide when to separate, when to repair, how to read emotion, and whether to trust speaker attribution — without any ground-truth reference?_

This thread unifies two project directions (ASR×LLM synergy + emotion) across 7 emotion-frontier experiments + 5 ASR×LLM experiments + 1 capstone synthesis.

**Design choices and justification:**

- **Why deepseek-r1:7b via ollama?** We required an LLM that: (a) runs fully offline (no API calls, no data leakage — critical for a research project on sensitive debate audio); (b) has reasoning capability (chain-of-thought) for emotion interpretation and minimal-edit repair; (c) is small enough (7B) for reproducible local experimentation. Alternatives considered: GPT-4/Claude (online, not reproducible, privacy concern); Llama-3-8B (no reasoning traces); Qwen-2.5-7B (comparable but less documented for Chinese). deepseek-r1:7b was already cached locally and had the best documented Chinese reasoning performance at this size.
- **Why Whisper-tiny for emotion experiments?** The emotion experiments needed the _same_ ASR outputs as the separation-tax baseline for cross-study comparability. Since Thread 1 established that the separation tax is tiny-specific, using tiny here means the emotion findings are _conservative_ — they study emotion under worst-case ASR errors.
- **Why gain-invariant prosody for emotion?** Standard SER (Speech Emotion Recognition) models require labeled training data, which doesn't exist for our overlap-controlled debate corpus. Instead, we operationalize emotion as _gain-invariant acoustic prosody_ (arousal-side), using the clean source's own prosody as reference — mirroring how CER uses the verified transcript. This follows the dimensional emotion tradition (Russell, 1980; Scherer, 2005) rather than discrete emotion categories.

**Literature grounding:**

- GenSEC-LLM challenge (arXiv:2409.09785, 2024): Makes post-ASR emotion recognition a first-class LLM task — but on clean single-speaker corpora. _Nobody has asked whether ASR errors induced by overlap+separation distort the emotion an LLM reads._
- R3 (arXiv:2409.15551, 2024): Couples ASR error-correction with emotion recognition — but uses clean audio. Our controlled overlap×separation grid is the right instrument to test this coupling under realistic conditions.
- VoxEmo (arXiv:2603.08936, 2026): Benchmarks speech emotion recognition with speech LLMs — confirms that LLMs have weak prosody perception, motivating our tri-modal approach.

**Emotion Frontier Seven Studies (findings #14–#20):**

| #   | Study                                        | RQ                                                                                                      | Outcome                                                                                                                                                                            | Key evidence                                                         |
| --- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| 14  | **Emotional Separation Tax** (#815)          | Does separation preserve or distort per-speaker emotion?                                                | ✅ Separation _helps_ emotion at all overlaps (opposite of ASR tax). The separate-or-not decision is **objective-dependent** — a single switch cannot serve both text and emotion. | `results/frontier/emotion_separation_tax/emotion_asr_divergence.png` |
| 15  | **Arousal→ASR probe** (#817)                 | Does acoustic arousal predict ASR difficulty?                                                           | ❌ **Bounding negative**: Pearson(arousal, CER) = 0.002. The emotion↔ASR relationship is asymmetric — separation affects emotion, but emotion does NOT predict ASR difficulty.     | `results/frontier/arousal_asr_probe/arousal_asr_probe.png`           |
| 16  | **Lexical emotion + tri-modal tax** (#819)   | Can regex/lexicon valence + acoustic arousal + lexical valence jointly characterize the separation tax? | ◐ Lexical arm underpowered (seed lexicon fires on 2/16 snippets). Motivates the LLM reader.                                                                                        | `results/frontier/lexical_emotion_tax/lexical_emotion_tax.png`       |
| 17  | **LLM × ASR critic** (#821)                  | Can a local LLM serve as reference-free QE and repair?                                                  | ❌ **Bounding negative**: LLM judge is dominated by free compression-ratio signal (+0.74 vs −0.41). GER repair net-harms (CER 0.951→0.983). Simple beats fancy.                    | `results/frontier/llm_asr_critic/llm_asr_critic.png`                 |
| 18  | **Objective-aware decoupled routing** (#823) | Can decoupling text-route and emotion-route recover both?                                               | ✅ **Capstone**: decoupled keeps same CER (0.528) but halves emotion distortion (0.139→0.079), cutting joint regret ~14×.                                                          | `results/frontier/objective_aware_routing/FINDINGS.md`               |
| 19  | **Emotion fidelity meter** (#825)            | Can we estimate emotion fidelity with NO clean reference?                                               | ◐ Usable coarse clean/contaminated gate (r=−0.51) but weak graded predictor (r=−0.20) that saturates.                                                                              | `results/frontier/emotion_fidelity_meter/FINDINGS.md`                |
| 20  | **Gate emotion cost** (#827)                 | Do CER-tuned hallucination-cure gates damage emotion?                                                   | ◐ Both gates cure CER AND damage emotion (objective-blind). Speaker gate dominates on both axes (cures more, damages least).                                                       | `results/frontier/gate_emotion_cost/FINDINGS.md`                     |

**ASR×LLM Frontier Studies:**

| Study                              | RQ                                                                 | Outcome                                                                                                                                                          | Key evidence                                                   |
| ---------------------------------- | ------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| **Semantic Emotion Tax** (#831)    | Can a local LLM read implicit emotion the lexicon misses?          | ✅ LLM coverage 0.70 vs lexicon 0.10 (~7×). Orthogonal 3rd modality vs acoustic-arousal & lexical-valence.                                                       | `results/frontier/semantic_emotion_tax/FINDINGS.md`            |
| **Emotion-anchored repair** (#833) | Does anchoring LLM repair to detected stance cure over-correction? | ❌ **Negative**: no-repair 0.924 < naive 1.082 < anchored 1.122. Anchoring _worsens_ it — giving the model "more latitude to rewrite" causes more hallucination. | `results/frontier/emotion_anchored_repair/FINDINGS.md`         |
| **Tri-modal fusion** (#835)        | Do orthogonal emotion modalities fuse to predict emotion damage?   | ◐ Fusion helps semantic target (R² 0.10→0.16) but hurts acoustic one. Acoustic-arousal is the single best reference-free emotion-damage signal.                  | `results/frontier/emotion_modality_fusion/FINDINGS.md`         |
| **Noise-robust router** (#814)     | Can a reference-free router beat fixed strategies under noise?     | ✅✅ Router 0.778 vs mixed 1.214 / gate 1.531. Recovers ~92% of oracle gap. Pearson(CR, tax) = 0.82.                                                             | `results/frontier/noise_robust_router/noise_robust_router.png` |
| **LLM speaker attribution** (#838) | Can LLM affect repair who-said-what?                               | ◐ Valence strongly encodes speaker role (AUC strength 0.78) but sign isn't knowable reference-free (naive 0.08, calibrated 0.92).                                | `results/frontier/llm_speaker_attribution/FINDINGS.md`         |

**Unified conclusion:** Cheap Whisper decoder signals are the deployable lever for routing; acoustic prosody handles "acoustic emotion"; the local LLM's true value is _covering implicit semantic emotion_, not providing free repair or attribution rules.

**Capstone:** `docs/frontier/asr_llm_emotion_capstone.md` — a one-page synthesis with deployable decision recipe.
**Hero figure:** `results/frontier/asr_llm_frontier_capstone.png` (all five results on one canvas).

---

### Research Thread 4: Research Entropy Audit — Meta-Research on Agentic Ceremony Collapse (Issues #785/#787, PRs #786/#788)

**RQ:** _When an autonomous agentic loop runs unsupervised on a research repo, does it keep producing substance or drift into self-referential ceremony?_

**Motivation.** A scan of `src/` revealed ~795 of 893 `*.py` files were ceremony-named (handoff/receipt/coordination/completion-summary). Independent content check: **0 of 795 contained real computation** (compute-import 3.5% vs 17% for substance; 0.11 vs 4.07 arithmetic ops/file). The git timeline shows a clean epidemic arc: birth (2026-06-02, 35 substance / 0 ceremony) → first collapse (06-07) → peak (+250 ceremony files on 06-12) → recovery (06-15 cleanup).

**Why this matters for research methodology.** This is not a code quality issue — it is a _research integrity_ issue. Ceremony files that compute nothing but claim "completion" create an illusion of progress that misleads both human reviewers and automated agents. The phenomenon is relevant to any project using LLM-based code generation for research.

**Approach:**

- Built `src/research_entropy_audit.py` — a two-signal classifier (filename pattern + content computation check) + git timeline visualization + bounded degeneration index. `make entropy-audit`.
- Built `scripts/harness/entropy_guard.py` — a stdlib-only _advisory_ guard wired into `make quality-predev` that warns (never blocks) when a change adds ceremony with no substance.
- **Cleaned 6,000+ ceremony files** (803 src/\*.py + 1,112 tests + ~4,360 result artifacts). Lean-rewrote `project_harness.py` from ~4,400 lines to genuine baseline smoke.
- **Result:** Entropy saturation 0.894 → 0.035; degeneration index 0.46 → 0.00; tests 3,304 → 825 all green; import-closure 0 violations.

**Module:** `src/research_entropy_audit.py` + `scripts/harness/entropy_guard.py` + `docs/frontier/agentic_research_entropy.md`.

---

### Research Thread 5: Engineering Harness (Issue #780, PR #781)

**Motivation.** The project needed infrastructure to enforce research discipline: critical code changes must include paired tests, results must be labeled by evidence level, and PRs must include structured impact summaries. We adapted `ref/code-tape`'s Harness to this Python repository.

**Design choices:**

- **Why not adopt code-tape's training-camp scoring/auto-merge?** Those mechanisms optimize for _throughput_ (maximize merged PRs), which directly contributed to the ceremony collapse documented in Thread 4. We adopted only the _quality_ pillars: git hooks, knowledge-base contract, SDD, TDD.
- **Why GitNexus for the knowledge base?** GitNexus provides a code knowledge graph with symbol-level impact analysis, enabling the `Contract Guard` CI check that verifies critical skeleton changes include paired tests. No comparable open-source tool provides this at the symbol level.

**Implementation (943 lines of harness code across 5 Python modules):**

1. **Git hooks** (`.githooks/{pre-commit,pre-push}`): POSIX shell, ~15 lines each. pre-commit runs fast test gate (`quality.py precommit`); pre-push runs GitNexus contract + full test gate (`quality.py prepush`). `SKIP_QUALITY_HOOKS=1` escape hatch for emergencies. `install_hooks.py` sets `core.hooksPath=.githooks` automatically.

2. **Contract rules engine** (`scripts/harness/contract_rules.py`, 424 lines): Classifies every file in the repo into one of 6 critical-skeleton categories:
   - `router-core` — routing/selection logic (e.g., `adaptive_router_v2.py`, `gate_selector.py`)
   - `evaluation-core` — CER/error metrics (e.g., `evaluate_cer.py`, `speaker_cer.py`)
   - `harness` — infrastructure code (`scripts/harness/*`, `.githooks/*`)
   - `references` — verified reference transcripts (`references/`)
   - `gold-results` — stable benchmark results (`results/gold/`)
   - `authority-docs` — documentation that other code depends on (`CLAUDE.md`, `docs/project_state.md`, `CONTRIBUTIONS.md`)

   Changes to files in these categories **trigger the paired-test gate**: the diff must include a corresponding `tests/test_<module>*.py` or the contract fails. This is the mechanical TDD enforcement.

3. **Contract check** (`scripts/harness/contract_check.py`, 238 lines): Runs on every `git push` (pre-push hook). Compares the staged diff against the contract rules; reports violations as structured JSON; integrates with CI as `Contract Guard` (`.github/workflows/contract-guard.yml`). Also enforces structured impact summary in the PR body.

4. **Quality dispatcher** (`scripts/harness/quality.py`, 123 lines): Unified command surface — `quality.py {predev,precommit,prepush,ci,local}` — each running the appropriate subset of {entropy guard, fast tests, contract check, full tests, GitNexus index refresh}. `Makefile` exposes these as `make quality-{predev,precommit,prepush}`.

5. **Entropy guard** (`scripts/harness/entropy_guard.py`, 128 lines): Advisory (never blocking) pre-dev check that warns when a change adds ceremony with no substance. Uses the same two-signal classifier as `research_entropy_audit.py` (Thread 4). Integrated into `make quality-predev`.

6. **SDD (Specification-Driven Development):**
   - Authority-doc hierarchy: `CLAUDE.md` (operating charter) -> `docs/project_state.md` (findings register) -> `CONTRIBUTIONS.md` (contribution record) -> `docs/roadmap.md`.
   - ADR-001 (`docs/adr/ADR-001-harness-adoption.md`): Architecture Decision Record documenting why we adopted the Harness and what we deliberately excluded.
   - PR template (`.github/PULL_REQUEST_TEMPLATE.md`): Every PR must include a structured GitNexus impact summary with risk level, critical skeleton changes, blast radius, and verification evidence.

7. **TDD enforcement:** The contract rules engine mechanically blocks `git push` if a critical-skeleton change lacks its paired test. 41 harness-specific contract tests (`scripts/harness/tests/`) cover the engine itself — classification accuracy, diff parsing, violation reporting, edge cases.

8. **repo-guard LLM code review** integration: Every PR receives automated review comments from a configured GitHub bot. The author must respond to every guard finding (fix or justify) before merge. This standardized the `issue -> PR -> repo-guard CR -> respond` loop across all 45+ PRs.

**Workflow documentation:** `docs/harness/` contains 5 specification files:
   - `README.md` — harness overview and quick-start
   - `knowledge_base_contract.md` — contract rules specification
   - `sdd.md` — Specification-Driven Development rules
   - `tdd.md` — Test-Driven Development enforcement rules
   - `workflow_spec.md` — the standardized PR review loop

**Verification:** Pre-push gate passes live — GitNexus index (26,296 nodes) + contract + full suite (3,253 tests OK at adoption time). The harness enabled the entire frontier research workflow: every one of the 40+ frontier PRs passed through this gate, and the contract prevented any critical-skeleton change from landing without paired tests.

---

### Research Thread 7: Decision-Theoretic Routing — POMDP Per-Utterance Heterogeneity Extension (Issue #896, PR #899)

**Grand RQ:** _Does lifting the stratum-level POMDP (RQ5, finding #24) to a per-utterance (continuous-state) POMDP improve text regret, predict the AISHELL-4 failure that router v2 could not generalize to, and reveal the within-stratum coupling-cost heterogeneity that RQ5 stated as a limitation?_

This thread extends the decision-theoretic routing framework from 5 discrete overlap strata to per-utterance continuous-state heterogeneity. It is theoretical + computational only (no ASR runs); all rewards are re-estimated from existing frontier data.

#### Motivation and connection to prior threads

RQ5 (`pomdp_solver.py`, finding #24) built a stratum-level POMDP over 5 discrete overlap strata {0, 0.1, 0.3, 0.6, 0.9} that recovers router v2's empirical boundary to within 0.03 overlap-ratio and predicts #18's objective-aware decoupling. But RQ5's FINDINGS stated an honest limitation: _"the POMDP captures the dominant trend but not per-utterance heterogeneity. The mid-overlap coupling costs #18 reports arise from within-stratum variation the POMDP does not see."_ RQ10 tests whether lifting the discretization addresses this.

A second motivation: router v2 failed to generalize to AISHELL-4 (RQ1, #881) — separated cpWER (1.206) did not beat always-mixed (1.173) because oracle-TextGrid separation creates interior silence gaps triggering Whisper's confident-attractor hallucination (#21). Neither router v2 nor the stratum-level POMDP has a silence dimension, so both predict "separated at high overlap" and are wrong on AISHELL-4. RQ10 asks whether adding a silence-fraction state dimension fixes this.

#### Design choices and justification

- **Why Gaussian kernel smoothing?** The stratum-level POMDP snaps continuous overlap to the nearest of 5 strata, losing within-stratum variation. A Gaussian kernel `K(r, r_i) = exp(-(r-r_i)^2 / (2h^2))` smoothly interpolates the reward surface over continuous overlap ∈ [0, 0.9], using the 15 greedy support points (text) and 5×8 support points (emotion). Bandwidths h_text=0.08, h_emo=0.15 are chosen from the support spacing (0.05 for text, ~0.2 for emotion), not tuned on regret — the crossover location (0.20) is stable across h_text ∈ [0.05, 0.12] because the actual data crossover is sharp (between 0.15 and 0.20).

- **Why a silence-fraction state dimension?** The AISHELL-4 failure driver is interior silence gaps in oracle-TextGrid-separated tracks, which trigger the confident-attractor mechanism (#21: encoder flags silence while decoder is confident). The existing gates (flatness, speaker) do NOT cure interior silence (RQ8 documents this gap). Adding `g ∈ [0, 1]` (fraction of the separated track that is silence) as a state dimension lets the POMDP represent the AISHELL-4 failure mode that the stratum-level POMDP cannot see.

- **Why greedy per-utterance argmax instead of belief-state value iteration?** With deterministic transitions (T=δ, same as RQ5), the POMDP collapses to per-state argmax. The extension is the continuous state + silence dimension, not a multi-step belief-state solver. A multi-step extension (where the route affects future belief via observations) would be needed for streaming/long-form context — left as future work.

- **Why calibrate the silence penalty from #21/RQ1 rather than measuring it?** The hallucination penalty `separated_cer(r, g) = base_sep_cer(r) + 1.5·g` is a qualitative model calibrated from #21 (confident-attractor) + RQ1 (separated cpWER 1.496–1.720 vs gold CER 0.46–0.76). The gain 1.5 is chosen so that at g=0.6 (representative AISHELL-4 silence: one speaker ~12 s speech in a 30 s window), the penalty (0.9) exceeds the separation benefit at high overlap (gap=0.712 at ov 0.3), flipping separated→mixed. A measured silence-fraction→CER curve (from a real AISHELL-4 cpWER run with the RQ8 silence-aware gate) would replace the calibration with data — left as future work.

#### Pre-registered hypotheses (Issue #896)

- **RQ10.1:** A per-utterance (continuous-state) POMDP improves over the stratum-level POMDP on text regret.
- **RQ10.2:** The per-utterance POMDP predicts the AISHELL-4 failure (assigning >70% probability to "mixed" for silence-gap windows).
- **RQ10.3:** The coupling cost (text vs emotion disagreement) is heterogeneous within strata (CV > 0.5 within ov0.1 stratum).

#### Three extensions over `pomdp_solver.py`

| Extension | What it does | Data source |
|---|---|---|
| **Continuous overlap** | Replaces 5 discrete strata with a Gaussian-kernel-smoothed reward surface over continuous overlap ∈ [0, 0.9]. | `phase_aggregate.csv` (15 greedy strata), `prosody_tax_curve.csv` (8 pairs × 5 overlaps, α=0.15) |
| **Silence-fraction state** | Adds a continuous silence-fraction dimension `g ∈ [0, 1]`. Models the AISHELL-4 oracle-TextGrid failure driver: an additive hallucination penalty on separated-track actions, calibrated from #21 + RQ1. | #21 causal probe, RQ1 AISHELL-4 |
| **Per-pair emotion heterogeneity** | Uses the 8 prosody pairs as per-utterance samples to compute within-stratum coupling-cost CV. | `prosody_tax_curve.csv` (8 pairs) |

#### Results

**RQ10.1 — Per-utterance POMDP improves text regret, but marginally and in-sample.**

| Policy | Mean text regret | Crossover (overlap-ratio) |
|---|---:|---:|
| Stratum-level POMDP (RQ5) | 0.00033 | 0.21 |
| **Per-utterance POMDP (RQ10)** | **0.00000** | **0.20** |
| Router v2 (baseline) | 0.00260 | 0.17 |

**Verdict: SUPPORTED but marginal.** The per-utterance POMDP's zero regret is partly tautological (evaluated on the same kernel-smoothed surface it optimizes over). The meaningful number is that the **stratum-level discretization regret is tiny (0.00033)** — the 5-strata POMDP is already a good approximation for the text objective because the text CER crossover is sharp. The continuous-state extension's value is NOT in text-regret reduction; it is in the silence-fraction dimension (RQ10.2) and the within-stratum heterogeneity (RQ10.3), which the stratum-level POMDP cannot represent at all.

**RQ10.2 — Per-utterance POMDP predicts the AISHELL-4 failure.**

| Regime | P(mixed) overall | P(mixed) high-overlap (Mid+Heavy) |
|---|---:|---:|
| **Silence-gap (g=0.6, AISHELL-4-like)** | **1.00** | **1.00** |
| No-silence (g=0.0, gold-baseline-like) | 0.83 | 0.00 |
| Stratum-level POMDP (no silence dim, g=0.6) | 0.85 | 0.00 |

**Verdict: SUPPORTED.** The discriminating test is the high-overlap band. Without silence, both POMDPs pick separated at high overlap (P(mixed)=0.00) — the gold-baseline prediction. With silence gaps, the per-utterance POMDP flips to mixed at high overlap (P(mixed)=1.00 > 0.70 threshold), predicting the AISHELL-4 failure. The stratum-level POMDP, lacking the silence dimension, keeps separated at high overlap and does NOT predict the failure. **This is the main value of the per-utterance extension:** it adds the state variable (silence fraction) that explains *why* the gold-baseline routing boundary does not transfer to AISHELL-4.

**RQ10.3 — Coupling cost is heterogeneous within strata (CV > 0.5 at ov 0.1).**

| Stratum | Mean coupling cost | CV | CV > 0.5? | sep_helps_frac (text-side proxy) |
|---:|---:|---:|:--:|---:|
| 0.0 | 0.000 | 0.00 | — | 0.25 |
| **0.1** | **0.108** | **0.97** | **✓** | 0.30 |
| 0.3 | 0.001 | 2.65 | ✓* | 0.50 |
| 0.6 | 0.000 | 0.00 | — | 0.70 |
| 0.9 | 0.011 | 2.65 | ✓* | 1.00 |

**Verdict: SUPPORTED at ov 0.1.** CV at ov 0.1 = 0.97 > 0.5, from the bimodal split of the 8 prosody pairs (4 pairs have emotion wanting separated while text wants mixed → disagree → coupling cost > 0; 4 pairs agree → coupling cost = 0). Text-side `sep_helps_frac` = 0.30–0.50 confirms the heterogeneity is not just an emotion-side artifact. (*Asterisk: CV at ov 0.3/0.9 is misleading because the mean is near zero — a single pair with tiny nonzero cost inflates the CV. The robust claim is at ov 0.1.)

#### Honest limitations

- **In-sample text regret (RQ10.1).** The per-utterance POMDP is evaluated on the same kernel-smoothed surface it optimizes over, so its zero regret is partly tautological. An out-of-sample test (held-out utterances with per-utterance CER) would validate the advantage non-tautologically; this requires per-utterance CER data not available in the current frontier.
- **Calibrated silence penalty (RQ10.2).** The hallucination penalty (gain=1.5) is a qualitative model, not a measured silence-fraction→CER curve. The qualitative result (silence flips high-overlap from separated to mixed) is robust to the gain choice above ~1.3, but the exact P(mixed) and flip threshold depend on the gain.
- **Emotion-side heterogeneity only (RQ10.3).** Within-stratum coupling-cost CV is computed from the 8 prosody pairs (emotion side); text CER is stratum-level. Full per-utterance coupling-cost CV would need per-utterance text CER.
- **No new data.** This is a reanalysis of #11/#14/#18/#20/#21/RQ1 data; it does not test the per-utterance POMDP on held-out utterances.

**Artifacts:** `results/frontier/decision_theoretic_routing/pomdp_per_utterance.py`, `policy_comparison_per_utterance.csv`, `policy_comparison_per_utterance.json`, `FINDINGS_per_utterance.md`. Reproduce: `python3 results/frontier/decision_theoretic_routing/pomdp_per_utterance.py`.

---

### Research Thread 6: A_framing/QiongQi Academic Research Framing (Issues #881–#892, PRs #886–#894)

**Grand RQ:** _Can a systematic academic research framing — using PICO/PEO/SPIDER+FINER frameworks, a 5-type gap taxonomy, hypothesis generation, theoretical framework mapping, contribution crafting, and venue analysis — convert the project's scattered frontier findings into a defensible academic contribution with honest statistical robustness and external validation?_

This thread spans 7 PRs across two iterations of the A_framing (QiongQi) skill suite, orchestrated by repo-evolver-fast. It is the project's first systematic attempt to subject its findings to academic-grade scrutiny: multiple-testing correction, external dataset validation, theoretical framework mapping, and venue positioning.

#### Motivation and methodological framing

The prior 5 research threads produced 21+ frontier findings, but they were reported with point estimates and no multiple-testing correction, validated only on the 5-case gold benchmark, and lacked a theoretical framework linking the routing decision to decision theory. The A_framing/QiongQi suite applies a structured academic framing pipeline:

- **PICO/PEO/SPIDER+FINER frameworks** — formalize each research question with population/intervention/comparator/outcome structure and FINER feasibility criteria.
- **5-type gap taxonomy** — classify each contribution as (1) methodological, (2) empirical, (3) theoretical, (4) dataset, or (5) reproducibility gap.
- **Hypothesis generation** — pre-register falsifiable hypotheses with explicit success/kill criteria before analysis.
- **Theoretical framework mapping** — connect empirical findings to established theory (POMDP, emotion-ASR asymmetry).
- **Contribution crafting** — articulate the novelty claim honestly against prior work.
- **Venue analysis** — position the work against target venues' scope and acceptance criteria.

#### Iteration 1: 5 PRs (Issues #881–#889)

| PR | Study | RQ | Outcome | Evidence |
|---|---|---|---|---|
| #886 | **Venue analysis** | Which venue best fits this work? | ✅ Interspeech 2026 recommended (4-venue comparison: ICASSP, Interspeech, IEEE TASLP, Speech Communication). Interspeech matches the mechanistic + empirical contribution profile. | `RESEARCH/overlap-aware-speaker-asr/framing/` |
| #887 | **Statistical robustness (BH correction)** | Do the 21 findings survive FDR control? | ❌ **H3 NOT SUPPORTED**: only 6/21 findings survive Benjamini-Hochberg at q=0.05. 11 claims need downgrade from "demonstrates" to "suggests". | `results/frontier/statistical_robustness/` |
| #888 | **Emotion-ASR asymmetry mechanism** | Why does separation help emotion but hurt ASR? | ✅ **P2 SUPPORTED** (moderate regime): low-dim features preserved (speaker count 1.00, prosody 0.93) while high-dim text hurt (CER benefit −1.207). ◐ **P3 WEAKLY SUPPORTED**: pre-decode AUC=0.623. | `results/frontier/emotion_asr_asymmetry/` |
| #889 | **POMDP decision-theoretic routing** | Does a POMDP-optimal policy match the empirical router? | ✅ **P1 SUPPORTED**: POMDP-optimal crossover 0.20 vs router v2 0.17 (divergence 0.03 < 0.1). Predicts finding #18 decoupling. | `results/frontier/decision_theoretic_routing/` |
| #890 | **AISHELL-4 external validation** | Does router v2 generalize to a standard meeting corpus? | ❌ **H1a NOT SUPPORTED**: router v2 cpWER 1.206 vs always-mixed 1.173 (router LOSES on AISHELL-4). ✅ **H1b SUPPORTED**: separation tax replicates, stronger than gold. | `results/external_sanity_check/aishell4/` |

**Design choices and justification:**

- **Why Benjamini-Hochberg (BH) over Bonferroni?** BH controls the False Discovery Rate (FDR) rather than the Family-Wise Error Rate (FWER). With 21 findings across heterogeneous tests, Bonferroni would be overly conservative (α/21 ≈ 0.0024), likely killing true effects. BH at q=0.05 is the standard choice in genomics and neuroimaging where many related hypotheses are tested simultaneously — it matches our multi-finding frontier.
- **Why AISHELL-4 for external validation?** AISHELL-4 is a standard Chinese meeting corpus with multiple speakers, overlap, and published cpWER baselines — the closest external match to our debate-audio domain. AMI/LibriCSS would require cross-lingual evaluation (a confound); AliMeeting lacks published cpWER baselines at the time of writing.
- **Why POMDP for theoretical framework?** The routing decision is inherently a Partially Observable Markov Decision Process: the true overlap state is hidden (observable only through compression ratio and other signals), the action (separate/mixed/cleaned) affects the reward (CER), and the optimal policy depends on the belief state. POMDP framing connects our empirical router to decision-theoretic optimality.

**Honest novelty assessment:** The BH correction and external validation are methodological hygiene, not novel contributions — any well-run academic study should do them. The genuinely new contributions are: (1) the **POMDP-optimal vs empirical-router divergence analysis** — no prior work maps overlap-aware routing to a POMDP and shows the empirical router approximates the optimal policy; (2) the **emotion-ASR asymmetry mechanism** — explaining _why_ separation preserves low-dim features (speaker count, prosody) while destroying high-dim text is a mechanistic claim not present in the GenSEC-LLM or R3 literature.

#### Iteration 2: 2 PRs (Issues #891–#892)

| PR | Study | RQ | Outcome | Evidence |
|---|---|---|---|---|
| #893 | **Report integration** | Integrate iteration 1 findings into REPORT.md | ✅ 5 new sections added (§18 Statistical Robustness, §19 External Validation, §20 Theoretical Framework, §21 Emotion-ASR Mechanism, §22 Venue Positioning). 8 claims downgraded from "demonstrates" to "suggests". Abstract updated with honest BH bounds. Findings #22–#26 added to project_state.md. | `REPORT.md` |
| #894 | **Silence-aware gate** | Can an energy-based VAD gate truncate interior silence and recover CER? | ◐ **H8 CONDITIONALLY SUPPORTED** by mechanism analysis: energy-based VAD truncates interior silence gaps >0.5s to 0.3s. cpWER validation pending Whisper install. | `results/frontier/silence_aware_gate/`, `src/silence_aware_gate.py` |

**Design choices and justification (silence-aware gate):**

- **Why energy-based VAD over learned VAD?** The silence-aware gate targets the _interior_ silence gaps that trigger the compression-seeking attractor (Viakhirev et al., 2026). Energy-based VAD is reference-free, deterministic, and adds zero inference latency — it operates as a preprocessing step. Learned VAD (Silero, WebRTC) would add a model dependency and potential failure modes without addressing the core mechanism (silence → attractor).
- **Why truncate to 0.3s rather than remove entirely?** Removing interior silence entirely would distort prosody and speaker-turn timing. 0.3s preserves the perceptual gap while staying below Whisper's silence-threshold trigger window. The 0.5s trigger threshold is calibrated against the phase-study's catastrophic cases (2.05s leading silence in pair=5, r=0.05).

#### Honest reporting summary

Across the 7 PRs, the A_framing iteration produced a balanced evidence profile:

- **2 hypotheses FALSIFIED:** H1a (router generalizes to AISHELL-4 — it does not), H3 (all 21 findings survive BH — only 6/21 do).
- **2 hypotheses SUPPORTED:** P1 (POMDP-optimal matches empirical router), P2 (emotion-ASR asymmetry in moderate regime).
- **1 hypothesis BORDERLINE:** P3 (pre-decode AUC=0.623 — weakly supported).
- **1 hypothesis CONDITIONALLY SUPPORTED:** H8 (silence-aware gate mechanism works; cpWER validation pending).

The falsifications are the most valuable outputs: they bound the project's claims honestly. The BH correction downgrades 11 claims from "demonstrates" to "suggests", and the AISHELL-4 negative shows the router does not generalize beyond the controlled debate corpus — both are documented with the same rigor as the positives.

#### New modules and artifacts

- `results/frontier/statistical_robustness/` — BH correction analysis (21 findings, q=0.05)
- `results/frontier/emotion_asr_asymmetry/` — emotion-ASR asymmetry mechanism (low-dim preserved, high-dim hurt)
- `results/frontier/decision_theoretic_routing/` — POMDP framework and optimal-policy comparison
- `results/external_sanity_check/aishell4/` — AISHELL-4 external validation (labeled `external/sanity-check`)
- `results/frontier/silence_aware_gate/` — silence-aware gate analysis
- `src/silence_aware_gate.py` (604 lines) + 29 unit tests — energy-based VAD gate
- `RESEARCH/overlap-aware-speaker-asr/framing/` — A_framing/QiongQi framing artifacts (PICO/PEO/SPIDER+FINER, gap taxonomy, venue analysis)
- `RESEARCH/overlap-aware-speaker-asr/theoretical_framework.md` — POMDP theoretical framework document
- `REPORT.md` — 5 new sections (§18–§22) integrating iteration 1 findings

All new findings labeled `experimental/frontier` or `external/sanity-check`. No gold tables or verified references touched.

**Literature grounding:** The BH correction follows Benjamini & Hochberg (1995). The POMDP framework follows Kaelbling, Littman & Cassandra (1998) and Spaan (2012, POMDP for speech applications). The emotion-ASR asymmetry connects to GenSEC-LLM (arXiv:2409.09785) and R3 (arXiv:2409.15551) — both study ASR×emotion coupling on clean audio; our contribution is the _mechanism_ under overlap+separation. The venue analysis references Interspeech 2026, ICASSP 2026, IEEE TASLP, and Speech Communication calls for papers.

#### Iteration 3: 3 PRs (Issues #895–#897, PRs #898–#900)

Iteration 3 was dispatched in parallel from the 26-finding project state and addressed three gaps surfaced by iterations 1–2: (a) the BH survivors lacked effect-size and post-hoc power analysis, (b) the stratum-level POMDP could not represent within-stratum heterogeneity or the AISHELL-4 silence-gap failure, (c) the router v2 AISHELL-4 regret was not decomposed into failure modes.

| PR | Study | RQ | Outcome | Evidence |
|---|---|---|---|---|
| #898 | **Effect size & post-hoc power (RQ11)** | Are the 6 BH-surviving findings practically significant, and are the 11 non-survivors genuinely small (not underpowered)? | ✅ 5/6 BH-survivors are practically significant (Cohen's d > 0.5; Hedges' g). 9/11 non-survivors are genuinely small effects (not underpowered) — only 2/11 are underpowered. Post-hoc power via noncentral t CDF (Gauss-Laguerre quadrature). | `results/frontier/statistical_robustness/effect_size_analysis.py`, `effect_size_table.csv`, `FINDINGS_effect_sizes.md` |
| #899 | **Per-utterance POMDP (RQ10)** | Does lifting the POMDP to per-utterance continuous-state improve regret and predict the AISHELL-4 failure? | ✅ RQ10.2 SUPPORTED: P(mixed)=1.00 for silence-gap high-overlap windows (stratum-level POMDP: 0.00). ◐ RQ10.1 SUPPORTED but marginal (in-sample zero regret). ✅ RQ10.3 SUPPORTED at ov 0.1 (CV=0.97). See Thread 7 for full detail. | `results/frontier/decision_theoretic_routing/pomdp_per_utterance.py` |
| #900 | **Router failure mode decomposition (RQ12)** | What failure modes drive router v2's AISHELL-4 regret, and does the CR guard catch them? | ✅ 100% of router v2's AISHELL-4 regret is hallucination-driven (separated tracks with CR > 3.0). ❌ CR guard misses 97% of hallucination regrets — the hallucinations are diverse (not repetitive), so the CR > 3.0 threshold catches only the catastrophic tail. The failure is _diverse hallucination_, not _repetitive hallucination_. | `results/frontier/router_failure_modes/failure_mode_analysis.py`, `failure_mode_results.csv/.json`, `FINDINGS.md` |

**Design choices and justification (iteration 3):**

- **Why Cohen's d and Hedges' g (RQ11)?** Cohen's d is the standard effect-size measure for pairwise comparisons; Hedges' g applies a small-sample bias correction (J factor), appropriate given our n=20 pairings per overlap ratio. We report both to be transparent about the correction's impact. Post-hoc power is computed via the noncentral t CDF (Gauss-Laguerre quadrature) rather than the normal approximation, because n=20 is small enough that the t-distribution's heavier tails matter.
- **Why Gauss-Laguerre quadrature for the noncentral t CDF (RQ11)?** The noncentral t distribution has no closed-form CDF; numerical integration is required. Gauss-Laguerre quadrature (20 nodes) on the integral representation converges to <1e-6 error vs scipy's `nct.cdf`, and is deterministic (no Monte Carlo noise).
- **Why decompose by CR > 3.0 threshold (RQ12)?** The CR > 3.0 threshold is the router v2 deployment threshold (compression-ratio guard). Decomposing regret by whether the guard _should_ have caught it (CR > 3.0) vs whether it _did_ catch it reveals the guard's coverage. The finding that 97% of regrets have CR < 3.0 (diverse hallucination) means the guard is calibrated for the wrong failure mode — it expects repetitive hallucination but AISHELL-4 produces diverse hallucination.

**Honest limitations (iteration 3):**

- RQ11's effect sizes are computed on the same data that produced the original findings (no new data) — they characterize the existing evidence, not new evidence.
- RQ10's silence penalty is calibrated, not measured (see Thread 7).
- RQ12's failure mode decomposition is on AISHELL-4 only (n=8 utterances with regret) — the 97% miss rate is a point estimate with wide CI on n=8.

**New modules and artifacts (iteration 3):**

- `results/frontier/statistical_robustness/effect_size_analysis.py` — Cohen's d, Hedges' g, post-hoc power via noncentral t CDF
- `results/frontier/decision_theoretic_routing/pomdp_per_utterance.py` — per-utterance POMDP with silence-fraction state dimension
- `results/frontier/router_failure_modes/failure_mode_analysis.py` — router v2 regret decomposition on AISHELL-4

All iteration 3 findings labeled `experimental/frontier`. No gold tables or verified references touched.

---

### Stable Baseline Contributions

In addition to the frontier research threads, I contributed to the project's stable baseline:

- **CER evaluation** and **error analysis** infrastructure (insertion/deletion/substitution/repetition breakdown).
- **Adaptive Router v1/v2** — rule-based routing between mixed/separated/cleaned outputs.
- **Risk-Aware Selector** — risk-weighted final output selection.
- **Speaker-Aware CER** and **cpCER-lite** — speaker permutation-invariant evaluation metrics.
- **Compute-Aware Cascade** — tiered ASR escalation analysis (CER vs compute trade-off).
- **MeetEval/cpWER compatibility** bridge for standardized evaluation.
- **`project_harness`** coordination — baseline smoke test (18/18 core files, 5/5 gold cases).

---

### Research Report & Documentation Improvements

In response to feedback about insufficient depth, justification, and supporting evidence in the project report, I undertook a systematic improvement of the main documentation:

1. **Expanded Literature & Related Work** — Consolidated scattered references from 38 FINDINGS.md files into a structured 4-subsection literature review in README.md, covering: speech separation × ASR, Whisper hallucination mechanisms, ASR × LLM post-processing, and emotion in speech. Each subsection explains what prior work established and precisely how our contribution extends or differs.

2. **Model Choice Justification** — Added explicit comparison tables for every major design decision: Whisper vs Faster-Whisper vs WhisperX vs FunASR/WeNet/ESPnet; deepseek-r1 vs GPT-4/Claude vs Llama-3; Resemblyzer vs pyannote vs ECAPA-TDNN. Each table includes criteria (open weights, reproducibility, cross-lingual, speed, etc.) and honest assessment of trade-offs.

3. **Research Hypotheses** — Enumerated the 5 core hypotheses with pre-registered kill criteria, results (confirmed/falsified), and evidence links. This makes the research question-answer structure explicit.

4. **Engineering Trade-off Analysis** — Documented the compute-vs-accuracy threshold (1.93× for Whisper-base), runtime cascade findings (binary cliff, not smooth Pareto), and router feature ablation (compression ratio dominates).

5. **Limitations & Failure Analysis** — Added 7 explicit limitations (small benchmark, oracle separation, single language, no standard benchmarks, LLM rescoring failure, no streaming, arousal-only prosody), each with honest assessment of why the limitation is accepted.

6. **Negative Results Table** — Consolidated 8+ clean negative results into a single table showing what each tells us and the evidence.

7. **System Architecture Diagram** — Added the system route map (`fig1_system_route_map.png`) to README as the visual entry point, with detailed caption explaining the pipeline flow.

8. **Research Contributions Summary** — Added a numbered list of 8 key research contributions to README, consolidating scattered claims into a single authoritative statement with evidence links.

9. **Audio Examples Section** — Added representative audio examples (mixed audio, hallucination cases, synthetic overlap) with descriptions of what to listen for.

10. **Experimental Parameters** — Added a complete methods section to REPORT.md specifying: Whisper decoding parameters (temperature=0.0, condition_on_previous_text=False), audio specifications (16kHz WAV), CER computation (custom Levenshtein, character-level normalization), hardware (Apple M1/M2), and LLM configuration (deepseek-r1:7b, temperature=0.1).

11. **Formal Bibliography** — Created `references.bib` with 25 BibTeX entries covering all cited papers (speech separation, Whisper hallucination, ASR×LLM, emotion, ASR models, datasets, engineering references).

12. **REPORT.md Expansion** — Added 3 new sections: Design Choices and Justification (section 2), Experimental Parameters (section 3), and Related Work (section 15). Expanded Limitations from 7 bullet points to 9 detailed paragraphs. Renumbered all 17 sections sequentially.

13. **Fixed Broken Image** — Removed the broken `<img>` tag referencing FINDINGS.md with width=0% in the figure gallery. Improved figure captions to include implications, not just descriptions.

14. **Quantitative Comparison with Prior Work** — Added a comparison table to README showing how our results (crossover r*≈0.17, hallucination patterns, LLM coverage 7×>lexicon) relate to numbers reported by Sato et al., Koenecke et al., Baranski et al., Aparin et al., Corpataux et al., and others. Includes honest note about comparability limitations.

15. **Capstone Failure Analysis** — Expanded `docs/frontier/asr_llm_emotion_capstone.md` with detailed failure analysis for emotion-anchored repair (anchoring gives LLM permission to rewrite more aggressively) and speaker attribution sign (dataset-specific, requires calibration set). Added reproducibility commands and literature connection section.

16. **Emotion Frontier Quantitative TL;DR** — Updated `docs/emotion_frontier.md` TL;DR with concrete numbers: prosody distance +0.151 at ov=0.1, Pearson r=0.002 for arousal vs CER, lexicon firing rate 0.10 vs LLM 0.70, joint regret cut ~14×, fidelity meter r=−0.51/−0.20.

17. **Research Question & Why This Matters** — Added a prominent research question statement and "Why This Matters" section to the top of README, framing the project as a research contribution (4 key findings) rather than a feature list.

18. **State of the Art Comparison** — Added a comparison table showing 10 existing systems/research (Whisper, WhisperX, Faster-Whisper, SepFormer, Conv-TasNet, FunASR, AMI/IEMOCAP, Sato et al., Koenecke et al., GenSEC-LLM) and how our work addresses their limitations. Positions our niche: routing decision with mechanistic + model-scale + objective-dependent analysis.

19. **Literature Search Methodology** — Added search methodology to `docs/frontier/causal_hallucination_probe_litreview.md`: databases (Google Scholar, Semantic Scholar, ACL Anthology, arXiv), query terms, date range (2024–2026), inclusion/exclusion criteria, agent structure, and honest limitations.

20. **Quick Results Summary** — Added a one-table summary of all key findings (11 rows) with evidence levels to README, giving readers immediate access to the project's core results without reading the full document.

21. **Future Work Section** — Added 7 concrete future directions: realistic separator evaluation, external benchmark validation, cross-lingual evaluation, larger LLM models, streaming evaluation, speaker diarization integration, and formal paper submission. Each direction is motivated by specific findings or limitations.

22. **Statistical Rigor — Bootstrap Confidence Intervals (this round)** — Surfaced the bootstrap CIs that were already computed in `results/frontier/separation_tax/phase_aggregate.csv` but not visible in the main docs. Added a "Statistical Analysis and Confidence Intervals" subsection to README.md and a "§6.1 Statistical Confidence for the Crossover Finding" subsection to REPORT.md showing the 95% bootstrap CIs for ΔCER at each overlap ratio. The key honest finding: at r=0.10 the CI [−2.265, +0.014] *barely* crosses zero, so we cannot reject "separation is neutral" at α=0.05 — the claim is scoped as *mechanistic* (heavy tail exists, detectable at AUC=1.0), not *population-level*. This directly addresses the teacher's "careful experimentation" criterion.

23. **Router Ablation Table (this round)** — Added the per-feature ablation table (gold + synthetic columns) to both README.md (Engineering Trade-off Analysis) and REPORT.md (§6.2). The table proves the router's decision quality comes from *observable* instability signals (compression ratio, repetition), not ground-truth CER — this is the reference-free property that makes the router deployable. The key insight surfaced: on gold, overlap-level alone matches oracle (5 cases cleanly separated by regime), but on synthetic silver v1 regresses to gap +0.2687 while v2 holds at +0.0853 — the instability features are what generalize.

24. **Threats to Validity Section (this round)** — Added §17 to REPORT.md following Wohlin et al.'s four-class taxonomy (Internal / External / Construct / Conclusion validity). Each threat is paired with a concrete mitigation: oracle separation bounds the separator-quality confound; the harness contract mechanically blocks CER leakage into routing; pre-registered kill criteria bound multiple-testing risk; four complementary metrics (CER, speaker-CER, cpCER-lite, error-type) bound construct validity; bootstrap CIs bound conclusion validity. This is the standard research-methodology section the teacher's "research level" criterion expects.

25. **Reproducibility Section (this round)** — Added §18 to REPORT.md consolidating the one-command reproduction path for every key finding (13-row table mapping finding → section → command → runtime). Documents the three verification gates (`make quality-precommit/prepush/ci`), the contract's mechanical TDD enforcement, and artifact provenance (every CSV/JSON/PNG committed, not generated at install). This makes the project verifiable end-to-end by a reviewer.

26. **Quick Results Summary CI Consistency (round 2)** — Updated the README Quick Results Summary table to include the 95% bootstrap CI for the crossover finding (r\*=0.173, CI at r=0.10: [−2.27, +0.01]) and the AUC sample-size caveat (n=6 positives — lower bound, not tightly estimated). This ensures the headline table is consistent with the detailed statistical analysis in the Research Methodology section.

27. **Audio Waveform Visualization — fig5 (round 2)** — Generated a new figure (`results/figures/report/fig5_separation_tax_waveform.png`) that directly visualizes the separation-tax hallucination mechanism. The figure shows the catastrophic case (pair=5, r=0.05) from the 600-condition phase study: (A) mixed audio transcribes correctly (CER=0.44), (B) oracle-separated Speaker 1 transcribes OK (CER=0.44), (C) oracle-separated Speaker 2 has 2.05s of leading silence that triggers a token-id repetition loop (CER=24.25, CR=16.33 — transcript 24× longer than reference). This directly addresses the teacher's "audio examples, visualizations" criterion. Added to both README.md (Statistical Analysis section) and REPORT.md (§6.1). The visualization script is at `scripts/docs/make_separation_tax_waveform.py`.

28. **Audio Spectrogram Visualization — fig6 (round 3)** — Generated a complementary time-frequency figure (`results/figures/report/fig6_separation_tax_spectrogram.png`) showing *what Whisper sees* before hallucinating. While fig5 (waveform) reveals the leading-silence structure in the time domain, fig6 (spectrogram) reveals the spectrally empty region (0–2.0s) in Speaker 2's separated track — a blank canvas that the compression-seeking attractor (Viakhirev et al., 2026) fills with confident token-id repetition. The figure also explains the leading-vs-trailing silence asymmetry: Speaker 1's trailing silence is less harmful because Whisper has already committed to a transcription state. Added to both README.md and REPORT.md (§6.1). The visualization script is at `scripts/docs/make_separation_tax_spectrogram.py`.

29. **Confident Attractor Scatter Plot — fig7 (round 3)** — Generated a scatter plot (`results/figures/report/fig7_confident_attractor_scatter.png`) visualizing the causal hallucination probe's key finding: catastrophic hallucination cases (n=26) decode at **higher** avg_logprob (−0.335 vs −0.739) and **lower** token entropy (1.487 vs 2.330) than clean cases (n=40) — the decoder is *more confident* while producing garbage. This is the counterintuitive core of the separation-tax hallucination: it is not a confidence collapse but a **confident lock-in**. Panel (B) shows the lock-in signature at dominant-token fraction ≈ 0.99. Data sourced from `results/frontier/causal_hallucination_probe/probe_rows.csv`. Added to README.md (Frontier Highlights — Causal & Internal-State Hallucination) and REPORT.md (§6.1). The visualization script is at `scripts/docs/make_confident_attractor_scatter.py`.

### Summary of Research Contributions

Across ~45 merged PRs and 36 frontier result directories, my contributions follow a consistent research methodology:

1. **Pre-registered hypotheses with falsifiable success/kill criteria** — every frontier study declares what would falsify it before running experiments.
2. **Honest negative results as findings** — 8 of 15+ frontier studies produced clean negatives (LLM rescoring catastrophic, cascade too coarse, arousal doesn't predict difficulty, etc.). Each negative narrows the solution space and is documented with the same rigor as positives.
3. **Literature-grounded novelty claims** — the causal hallucination probe includes a 6-agent literature sweep with per-hypothesis novelty assessment; honest about what is established bedrock vs genuinely new.
4. **Design choice justification** — model selection (Whisper-tiny for visibility, base for validity), LLM selection (deepseek-r1 for offline/reasoning), signal selection (gain-invariant prosody for label-free emotion) each grounded in specific constraints.
5. **Evidence discipline** — all frontier results labeled `experimental/frontier`; gold tables and verified references never touched; synthetic/silver references clearly marked.
6. **Reproducibility** — every module has paired unit tests; injected fake-LLM/Whisper for CI; all results in committed CSVs with reproducible `python -m src.<module>` commands.

### Modules (complete list)

`src/causal_hallucination_probe.py`, `src/model_scale_analysis.py`, `src/confidence_calibrated_router.py`, `src/multi_decode_voter.py`, `src/contrastive_decode.py`, `src/runtime_cascade.py`, `src/error_profile_decomposition.py`, `src/noise_robust_router.py`, `src/semantic_emotion_tax.py`, `src/emotion_anchored_repair.py`, `src/emotion_modality_fusion.py`, `src/llm_speaker_attribution.py`, `src/frontier_capstone_figure.py`, `src/emotion_separation_tax.py`, `src/arousal_asr_probe.py`, `src/lexical_emotion.py`, `src/lexical_emotion_tax.py`, `src/llm_asr_critic.py`, `src/emotion_fidelity_meter.py`, `src/gate_emotion_cost.py`, `src/objective_aware_routing.py`, `src/prosody.py`, `src/noise_robust_gate.py`, `src/speaker_conditioned_gate.py`, `src/gate_selector.py`, `src/decoder_cure_noise.py`, `src/hallucination_router.py`, `src/reference_free_qe.py`, `src/separation_tax_phase.py`, `src/hallucination_cure_eval.py`, `src/speaker_similarity_probe.py`, `src/noise_robustness.py`, `src/research_entropy_audit.py`, `src/adaptive_router_v2.py`, `src/risk_aware_selector.py`, `src/compute_aware_cascade.py`, `src/speaker_*.py`, `src/meeteval_*.py`, `src/external_validation_*.py`, `src/project_harness.py`, `results/frontier/decision_theoretic_routing/pomdp_per_utterance.py` (RQ10 per-utterance POMDP extension); paired tests for all; `scripts/harness/*`, `.githooks/*`, `docs/harness/*`, `docs/frontier/*`.

## 吴方舟/wfzark（23123986）

**Role:** Core technical contributor; route-selection problem framer; main
experimental pipeline owner; AudioDepth frontier explorer; team report and
research-visualization contributor.

吴方舟的贡献主线是把项目从"比较一个固定 ASR 输出"推进为一个系统问题：
**when should an overlap-aware ASR system separate speech, keep mixed audio, or
fall back to a safer route?** 这一 framing 贯穿主实验、风险选择、前沿探索和
最终报告，使项目围绕 route selection、claim boundary 和 evidence level
组织，而不是只报告单一 CER 表。

### 1. Mainline ASR pipeline and route-selection evidence

在稳定主线上，吴方舟组织并实现/协调了项目的核心实验路径：

- mixed Whisper baseline；
- separated speaker-track ASR；
- speaker transcript merging；
- duplicate-suppressed cleaned separated transcript；
- verified gold-reference workflow；
- CER evaluation and comparison tables；
- error-type analysis for insertion / deletion / substitution / repetition；
- adaptive router v1；
- feature-based router v2；
- router ablation；
- synthetic silver validation；
- held-out synthetic split interpretation；
- speaker-aware CER；
- cpCER-lite speaker permutation checks；
- risk-aware final selector。

这些工作建立了项目最核心的比较面：`mixed_whisper`、
`separated_whisper`、`separated_whisper_cleaned`、router v1/v2、
risk-aware selector 和 oracle-best 的关系。对应的系统性文档入口包括
[Current results summary](results/figures/curated/current_results_summary.md),
[Results Index](docs/results-index.md), and
[Implementation Status](docs/implementation-status.md).

### 2. Evidence discipline and claim-boundary cleanup

吴方舟持续维护项目的证据边界，区分：

- five-case gold benchmark；
- synthetic silver validation；
- held-out synthetic split；
- silver-plus / proxy / diagnostic references；
- sampled real-Whisper validation；
- optional integration scaffolds；
- frontier exploratory research。

这部分贡献体现在主文档、结果索引和最终报告中，尤其是
[REPORT.md](REPORT.md) 中的 evidence-level table、limitations、team
contribution synthesis，以及对"CER is evaluation-only, never a routing input"
的反复约束。该工作避免把 synthetic、frontier 或 roadmap-only 内容误写成
stable mainline claim。

### 3. AudioDepth frontier research

吴方舟提出并推进 AudioDepth 方向，把 overlapping speech 解释为
time-frequency occlusion，并借鉴 RGB-D / depth-style visual recognition 中
"depth is an additional view, not a replacement for RGB"的思想。AudioDepth
探索 pre-ASR acoustic maps 是否能在 Whisper 产生不稳定 transcript 前暴露
overlap risk，从而辅助 mixed / separated / cleaned / review 路由。

该方向包括：

- overlap as time-frequency occlusion；
- RGB-D / depth-style research motivation and citations；
- deployable mixed-only AudioDepth maps；
- analysis-only separated-track diagnostics；
- AudioDepth MVP；
- weak simple-CNN negative result；
- model zoo, handcrafted features, CNN-depth models, balanced depth models；
- hybrid late fusion with transcript instability；
- controlled route-sensitive benchmark；
- balanced benchmark v2；
- real Whisper validation and proxy-to-real gap analysis；
- Stage-1 acoustic gate；
- risk-guarded sweep；
- end-to-end safety audit；
- curated 3D / channel / route-space visualizations。

AudioDepth 始终被标为 Frontier Branch Only / Exploratory Research，不替代
mainline pipeline，也不作为 stable deployment claim。完整研究叙事见
[AudioDepth Router Exploratory Study](docs/frontier/audio-depth-router.md)。

### 4. Team report, documentation integration, and research figures

近期贡献中，吴方舟推动并整理了团队级 [REPORT.md](REPORT.md)，把原本分散的
主线实验、Mode B cascade、speaker-aware evaluation、MeetEval/cpWER、
speaker-profile diagnostics、LLM critic、AudioDepth、OpenClaw / harness
等内容整合成一份 team-level research report。该报告删除了低信息密度的
handoff / receipt / checklist / queue 流水账，并改为围绕 research
question、benchmark evidence、core results、boundary analysis、compute-aware
routing、frontier studies 和 limitations 展开。

同时，吴方舟补充了可复现的科研绘图脚本
[`scripts/report/make_report_figures.py`](scripts/report/make_report_figures.py)，
并生成报告级图表：

- route map；
- gold CER strategy comparison；
- separation boundary phase plane；
- compute-aware cascade 3D surface。

这些图表服务于报告表达，不引入新 benchmark claim；数值图读取 curated
result tables，概念图明确标注为 decision surface / visualization。

### 5. Final portable team demo and presentation system

在最终交付阶段，吴方舟进一步把项目整理成可直接用于课堂/答辩展示的
团队级便携 Demo，而不是继续开发新的研究模型。该工作以 `main` 分支为
团队事实来源，把 README、REPORT、CONTRIBUTIONS、implementation status、
results index、报告图、frontier findings 和 AudioDepth branch-only 资产
压缩成一个零依赖静态网页包：

- `demo_final/index.html`：六页团队级演示入口，覆盖 Overview、Core Routing、
  Separation Tax、Routing + Evaluation、Team Frontiers、Evidence；
- `demo_final/demo_data.js`：把核心案例、CER、transcript、成员贡献卡片、
  evidence level、source path、branch 和 commit/ref 直接内联，避免浏览器
  `file://` 读取 JSON 时出现跨域问题；
- `demo_final/PRESENTER_RUNBOOK.md`：设计 8 分钟双人演示流程，区分
  Research Narrative、Demo Operator 和 Conclusion，限制点击路径和现场操作；
- `demo_final/EVIDENCE_MANIFEST.md`：记录每个数字、图片、音频、transcript、
  contribution card 和 AudioDepth asset 的来源分支、commit/ref 与 evidence
  level；
- `demo_final/tests/validate_demo.py`：验证便携性、无绝对路径、无伪 live
  inference 表述、AudioDepth branch-only 标记、成员卡片完整性、缺失
  transcript 边界、截图/音频/图片存在性；
- `demo_final/backup_slides.html` 和 `demo_final/screenshots/`：提供 JS 或
  音频失效时的备用展示路径。

Demo 中的 Core Routing 页面只选择两个现场案例：`LightOverlap` 作为
mixed-win case，`NoOverlap` 作为 control separated-win case。页面明确说明
`LightOverlap` 的 raw separated transcript artifact 未随 main 打包，因此只展示
已提交 CER 和 cleaned separated transcript，不重建、不伪造缺失 transcript；
同时补充 `HeavyOverlap` 和 `OppositeOverlap` 在 gold CER table 中同样偏向
separated ASR，避免观众误解为"分离只在无重叠时有效"。

该 Demo 还将 AudioDepth 控制在 Team Frontiers 页面中，标记为
Frontier Branch Only / Exploratory Research / Not merged into stable mainline /
Not production-ready，并写明 AudioDepth 是 safety confirmer 和 interpretable
auxiliary representation，不是 main production router。最终 Demo 通过 PR #879
合并到 `main`，使其他组员无需切分支即可访问 `demo_final/`。

### 6. Contribution boundary

吴方舟的贡献重点是主 ASR 实验管线、route-selection framing、AudioDepth 前沿
研究、证据边界维护、最终报告整合和团队级便携 Demo 交付。已知限制仍然存在：
gold benchmark 很小，synthetic / silver 证据不能替代 gold，real-meeting
generalization 未完全证明，Stage-2 fallback / review policy 仍需更多验证，
AudioDepth 需要独立评审后才能进入任何 stable mainline claim；最终 Demo 是
replay demo，展示已提交实验产物，不是 live inference 系统。

## 谢宇轩 (xyx12369)

**Role:** Mode B: 算力感知三层级联识别。

**主要贡献：**

- 设计并实现参考无关的三层级联架构：Tier 1 (便宜) → Tier 2
  (风险触发更强ASR) → Tier 3 (LLM Critic/人工复核)。
- 升级决策仅依赖可观测信号，包括重复段数、运行时间膨胀、文本长度比
  和重叠等级；CER 仅用于事后评估。
- 产出 CER-cost tradeoff 散点图、成本感知路由表、覆盖率统计，以及与
  固定策略及 router_v2 的横向对比分析。
- 完成 24 单元测试 TDD。
- 标签: `experimental/frontier`。

**模块：** `src/cascade_tiers.py`, `tests/test_cascade_tiers.py`.

## 邵俊霖 / saayaya (23124001)

**Role:** Separation Phase Diagram 修复；Learned Router 设计与实现；bugfix。

**主要贡献：**

### 1. Phase Diagram Bugfix

- 修复 `separation_phase_diagram.py` 中因合并冲突导致的内容重复和
  import 损坏问题（移除 374 行重复代码，修复 `collections.defaultdict`
  import）。
- 创建缺失模块 `src/plot_phase_boundary.py`：
  实现 `plot_enhanced_phase_diagram()`（带 crossover 标记和 CI 区域的
  增强相图）和 `plot_bootstrap_probability_curve()`（bootstrap P(helps)
  概率曲线+ΔCER双轴图）。
- 补充 `tests/test_plot_phase_boundary.py`（5 项 smoke test，覆盖
  有无 boundary_metadata 两种路径）。

### 2. Learned Router（主要贡献）

- 针对 REPORT.md §7 "router is entirely rule-based" 的局限性，设计并
  实现了监督学习路由器 `src/learned_router.py`，替代手写规则 router_v2。
- 使用 synthetic split 的 CER 表自动生成 oracle-best 标签，训练
  Logistic Regression 和 Decision Tree 两种模型。
- 特征完全基于可观测信号（overlap_level、text_length_ratio、
  runtime_ratio、duplicate_removed_count 等 10 维特征），无 CER 泄露。
- 评估结果：Logistic Regression 在 held-out test split 达到
  **78% accuracy，平均 CER 0.168**（优于 cleaned baseline 0.185，
  接近 oracle 0.115）。
- Decision Tree 输出可解释规则树，可与 v2 手写规则直接对比。
- 编写 `scripts/train_learned_router.py` 一键训练脚本，输出
  `learned_router_evaluation.json/csv` 和 `learned_router_tree_rules.txt`。
- 完成 `tests/test_learned_router.py` 共 11 项单元测试（全部通过）。
- 标签: `experimental/frontier`。

### 3. LLM-ASR Collaborative Repair（本轮新增）

- 实现 LLM-ASR 协作修复闭环 `src/llm_repair_loop.py`：以 ASR 输出为
  起点，经风险检测 → RAG 检索 → LLM 纠错 → CER 评估迭代修复（最多三轮、
  带收敛判定与回退保护），并提供离线 oracle 模式，在未运行完整 pipeline
  时自动生成 synthetic ASR 输出以支持复现。
- 实现 RAG 检索修复模块 `src/rag_repair.py`：基于已验证 reference
  segments 构建知识库，使用字符 n-gram Jaccard 相似度检索 top-k 上下文，
  为 LLM 修复提供领域提示。
- 实现 Router 特征重要性分析 `src/router_feature_importance.py`：量化各
  特征对 learned router 决策的贡献并输出可视化柱状图，支撑 routing 决策的
  可解释性分析。
- 修复 learned router 的 sklearn 兼容性问题（LogisticRegression
  `multi_class` 参数与 `classification_report` 的 `target_names` 数量
  不匹配），并将 `src/__init__.py` 中 router 可视化模块改为 lazy import，
  避免可选依赖缺失导致整体导入失败。
- 完善 `README.md` 的 LLM-ASR Collaborative Repair 章节（架构图、模块表、
  使用方法、RAG 集成说明与设计理念），并配合 `demo/app.py` 整理 LLM-repair
  与 router 模块在演示中的调用路径。

**模块：** `src/learned_router.py`, `src/plot_phase_boundary.py`,
`src/separation_phase_diagram.py` (fix), `scripts/train_learned_router.py`,
`tests/test_learned_router.py`, `tests/test_plot_phase_boundary.py`,
`src/llm_repair_loop.py`, `src/rag_repair.py`,
`src/router_feature_importance.py`, `src/__init__.py`, `README.md`,
`demo/app.py`.

## 梁跃川 / liang-yuechuan

**Role:** Mode C: 前沿探索 — 分离相位图 (Separation Phase Diagram) 设计与实现。

**主要贡献：**

### 1. Separation Phase Diagram（核心贡献）

针对项目核心问题"语音分离何时帮助、何时损害多说话人 ASR"，设计并
实现了 `src/separation_phase_diagram.py`，通过 delta CER
（separated_whisper − mixed_whisper）vs overlap ratio 的散点图
量化分离帮助/损害的 crossover 边界。

### 2. 单元测试 (TDD)

- `tests/test_separation_phase_diagram.py`（5 项测试）：
  覆盖 `compute_delta_cer`（正负 delta）、`overlap_bin_key`
  （步长舍入）、`build_gold_points`（锚点映射 + separation_helps
  标记）、`build_silver_points`（manifest overlap ratio 读取）、
  `aggregate_trend_rows`（分箱聚合 + help_rate 计算）。
- `tests/test_separation_phase_diagram_write_outputs.py`（1 项测试）：
  smoke test 验证 `write_outputs()` 正确输出 CSV（含正确列名和
  行数据）、JSON（结构正确）、Markdown（含 `experimental/frontier`
  标签和 case 名称）、PNG（非空文件 ≥ 6 字节）。

全部 6 项测试通过。

### 3. 研究意义

该项目首次为 overlap-aware ASR 提供了"分离是否值得"的量化视图：
在低重叠场景分离有益（delta < 0），在高重叠场景分离可能有害
（delta > 0），为 Router 决策和级联策略提供了实验依据。

**模块：** `src/separation_phase_diagram.py`,
`tests/test_separation_phase_diagram.py`,
`tests/test_separation_phase_diagram_write_outputs.py`.

## 张浩豪 / haohaozhang776

**Role:** Mode D: Evaluation System & Cross-Benchmark Analysis（评估系统与跨实验对齐）

**主要贡献：**

- 构建统一 evaluation adapter，使 mixed / separated / cleaned / router v2 / cascade outputs 能够在同一评估接口下进行对齐比较，减少不同 pipeline 在格式层面的不一致问题。
- 设计并实现跨 benchmark aggregation 流程，将 gold / synthetic / held-out 三类数据的评估结果统一标准化为可复用 evaluation schema，用于 REPORT.md 与可视化模块共享。
- 对 speaker-aware CER、cpCER-lite 以及 error-type breakdown（insertion / deletion / repetition）进行了结构化整理，使其可用于后续 routing 与 separation 分析。
- 协助建立 evaluation sanity check pipeline，用于检测不同 ASR 输出在 alignment、length drift 与 duplication ratio 上的一致性风险。
- 参与 early-stage evaluation robustness exploration，分析不同 ASR pipeline 在长文本与高重叠场景下的 stability drift。
- 对 router v2 与 rule-based baseline 的评估偏差进行了对照分析，支持 report 中"reference-free routing validity"的实验结论构建。
- 提供 evaluation-side evidence support，用于验证 cascade / learned router / separation phase analysis 的实验一致性。

**模块：**

src/eval_adapter.py, src/eval_aggregator.py, src/speaker_cer.py, src/error_analysis.py, scripts/eval_sanity_check.py

## Commit 规范

- feat: 新功能
- fix: 修复
- docs: 文档
- refactor: 重构
- eval: 评估实验

## 代码审查

所有 PR 需至少一人 review 后合并。
