# Team Contributions

This file is the authoritative contribution record for the course/project
submission. Contribution records were centralized here so the repository has a
single source of truth; the former `docs/contributions/` tree was removed after
migration.

## 王景宏 (ceilf6)

**Role:** Frontier research lead; overlap-hallucination mechanism investigator; ASR×LLM×emotion axis explorer; research-entropy meta-analyst; engineering harness architect.

**Scope summary:** ~45 merged PRs (#780–#872), 40+ issues, 40+ new modules, 36 frontier result directories, 15+ experimental figures, 6-agent literature review. All frontier work labeled `experimental/frontier`; no gold tables or verified references touched.

---

### Research Thread 1: The Separation Tax — from Mechanism to Model-Scale Dissolution

**Grand RQ:** *Is the "separation tax" — speech separation hurting Whisper ASR at low/mid overlap — a fundamental limitation of overlap-aware ASR, or an artifact of using the weakest model?*

This thread spans 20+ PRs across three phases and constitutes the project's deepest investigation.

#### Phase 1: Oracle-separation phase study + reference-free cure (Issue #795, PR #796)

**Literature gap.** Sato et al. (Interspeech 2021, "Should We Always Separate?") established that separators inject artifacts hurting ASR below an SIR/SNR crossover, proposing a gated router. However, their analysis used a single-sample-per-ratio scatter and did not characterize the *mechanism* of failure — whether separation uniformly degrades ASR or creates a heavy-tailed hallucination phenomenon.

**Design choices and justification:**
- **Why Whisper-tiny?** We chose the smallest Whisper model (39M parameters) as the primary experimental vehicle because: (a) it is the most resource-constrained realistic deployment target, making separation-overhead most consequential; (b) its small capacity makes separation-induced failures most visible, providing an upper bound on the tax; (c) all prior project baselines used tiny, enabling direct comparison. Faster-Whisper and WhisperX offer speed optimizations but use the same underlying model architecture — they would exhibit the same separation tax. The model-size question is explicitly addressed in Phase 3.
- **Why oracle separation?** We used oracle (ground-truth) separation rather than a real separator (SepFormer, Conv-TasNet) to isolate the effect of separation *itself* from separator quality. This follows the standard methodology in speech separation evaluation (e.g., Kolbaek et al., 2017) where oracle bounds are studied before realistic separators.

**Pre-registered hypotheses:**
- H1: A continuous separation-gain crossover exists at some overlap ratio r* (confirmed: r* ≈ 0.17).
- H2: The low-overlap penalty is a heavy hallucination tail, not uniform degradation (confirmed: at r=0.10, mean ΔCER = −0.94 but median = 0.00; 6/600 tracks blow up to CER up to 24×).
- H3: A reference-free compression-ratio guard can detect catastrophic hallucination (confirmed: AUC ≈ 1.0 for CER > 1.0).

**Key finding:** The separation tax is a *heavy-tailed hallucination phenomenon* concentrated in near-silent separated tracks, not a uniform degradation. A guard-gated trim/fallback router closes ~76% of the oracle gap. Detailed results in `results/frontier/separation_tax/FINDINGS.md`.

**Figures:** `results/frontier/separation_tax/phase_curve.csv`, `results/frontier/hallucination_router/routing_curve.csv`.

#### Phase 2: Hallucination mechanism and cure chain (Issues #797–#813, PRs #798–#813)

This phase followed a systematic **cure-search arc** — each negative result narrowing the solution space:

| Study | RQ | Outcome | Key evidence |
|---|---|---|---|
| **Hallucination router** (#797) | Route by hallucination vs overlap on held-out split? | ❌ **Falsified**: degeneracy router (+0.083 regret) loses to trivial always-trim (+0.041). But the trim recipe generalizes — once you silence-trim, knowing overlap barely matters. | `results/frontier/hallucination_router/FINDINGS.md` |
| **Reference-free QE** (#799) | Do decoder signals predict graded CER? | ◐ Signals are catastrophe *gates* (AUC 1.0 for CER>1.0) but at chance for moderate CER (AUC ~0.48). U-shaped calibration. | `results/frontier/reference_free_qe/qe_signal_table.csv` |
| **Speaker similarity** (#801) | Does acoustic speaker distance predict separation benefit? | ❌ **Negative**: apparent Pearson +0.49 collapses to +0.08 under tail-robust median. Methodological caution: use robust stats. | `results/frontier/speaker_similarity_probe/FINDINGS.md` |
| **Hallucination cure** (#803) | Can Whisper's native `hallucination_silence_threshold` or beam search cure the tail? | ✅ The catastrophe is a greedy-decoding artifact. All of {silence-trim, native threshold, beam} eliminate the tail (19.84 → ~0.54). Best deployable: silence-trim (−39% mean CER). | `results/frontier/hallucination_cure/cure_curve.csv` |
| **Noise robustness** (#805) | Does the silence-trim cure survive noise? | ❌ **Critical negative**: noise defeats the cure. Trim benefit collapses from +0.239 (clean) to +0.000 at every SNR ≥ 0 dB. Energy-trim needs *actual silence* — noise fills the gap. | `results/frontier/noise_robustness/noise_curve.csv` |
| **Spectral + speaker gates** (#807) | Can spectral-flatness or speaker embeddings cure hallucination under noise? | ✅ Spectral gate works for broadband noise; speaker-conditioned gate (Resemblyzer GE2E, AUC 0.95) cures babble (CER 1.63→0.67). No single gate dominates all noise types. | `results/frontier/speaker_conditioned_gate/speaker_gate_curve.csv` |
| **Decoder cures under noise** (#809) | Is the noise-robust cure in the decoder, not the audio? | ❌ **Negative**: beam search raises mean CER under every noise type (pooled 1.947 vs greedy 1.676). Native silence-threshold fires only 4–33% under noise. The cure must act on the audio. | `results/frontier/decoder_cure_noise/cure_noise_curve.csv` |
| **Gate selector** (#811) | Can a reference-free selector choose between gates by residual character? | ❌ **Falsified** with a stronger byproduct: the speaker gate dominates on *both* axes (CER + emotion), so there is nothing to select. The real decision is separate-vs-mixed, not gate-vs-gate. | `results/frontier/gate_selector/FINDINGS.md` |
| **Noise-robust router** (#814) | Can a reference-free router beat fixed strategies under noise? | ✅✅ **Strong positive**: router 0.778 vs always-mixed 1.214 / always-gated 1.531. Recovers ~92% of oracle gap. Pearson(CR, separation-tax) = 0.82. | `results/frontier/noise_robust_router/router_curve.csv` |

**Engineering trade-off: Why Resemblyzer for speaker embedding?** We chose Resemblyzer (GE2E encoder) over alternatives (pyannote.audio, SpeechBrain, wav2vec2-based) because: (a) it is fully offline and lightweight (~45MB), matching our local-first constraint; (b) it produces a single 256-dim embedding per track, enabling fast cosine-distance computation across 600+ conditions; (c) its AUC 0.95 on babble detection was sufficient — a more complex model would add latency without changing the gate-vs-no-gate decision boundary. The honest limitation is that it fails at 0 dB SNR (AUC 0.52 ≈ chance).

**Literature grounding:** The hallucination cure chain connects to Koenecke et al. (ACM FAccT 2024, "Careless Whisper") — Whisper hallucinations concentrate in long silent regions as phrase repetition — and Baranski et al. (ICASSP 2025) — a recurring finite "bag of hallucinations" covers most cases. Our contribution is mapping these findings into the *separation-induced* regime with noise as an additional axis.

#### Phase 3: Model scale analysis — the separation tax is a tiny-model artifact (Issues #857–#871, PRs #858–#872)

**Critical validity question.** All 29+ frontier studies used Whisper-tiny exclusively. If the separation tax, hallucination thresholds, and routing signals do not generalize to larger models, the practical value collapses.

**Design choices and justification:**
- **Why test tiny/base/small specifically?** These span a 10× parameter range (39M/74M/244M) at 1×/1.93×/6× compute cost, covering the realistic deployment spectrum for edge/real-time ASR. We did not test medium/large because: (a) they require >1GB VRAM, exceeding typical edge constraints; (b) the base result already dissolved the tax, making further scaling less informative.
- **Why not Faster-Whisper or WhisperX?** Faster-Whisper uses CTranslate2 quantization for speed but produces identical logits to vanilla Whisper at the same model size. WhisperX adds forced alignment and VAD preprocessing — useful for production but irrelevant to our controlled overlap×separation experiment. The model *capacity* (parameter count) is what matters, not the inference engine.

**Pre-registered hypotheses (PR #859):**
- H1: Larger models hallucinate less — the catastrophic tail rate decreases monotonically tiny → base → small. **Confirmed.**
- H2: The separation-tax phase boundary shifts leftward — separation helps at lower overlap for larger models. **Confirmed** (base: separation tax disappears entirely).
- H3: Compression-ratio becomes less discriminative for larger models (signal paradox). **Confirmed** — base's CR is ~1.0 on all inputs, making it useless as a routing signal.

**Headline result:** Whisper-base (74M, 1.93× compute) produces CER = 0.200 *constant across all overlap ratios* — the separation tax completely vanishes. Zero hallucinations. All 29 routing/gating studies were compensating for tiny-specific weakness.

**Follow-up investigations (9 PRs):**

| Study | RQ | Outcome | Evidence |
|---|---|---|---|
| **Confidence-calibrated router** (CCR) | Do multi-signal composites beat single CR? | ❌ Worse — CR alone is near-optimal | `results/frontier/confidence_calibrated_router/` |
| **Multi-decode voting** (#858) | Is decode-stability a stronger reference-free signal? | ❌ CR Spearman 0.781 vs agreement −0.404. Whisper-tiny is stably bad. | `results/frontier/multi_decode_voter/` |
| **Contrastive decoding** (#857) | Can subtracting mixed-prior logits suppress hallucination proactively? | ◐ Divergence IS a quality signal (AUC 0.765) but fallback correction is 0.076 CER *worse*. Hallucination is deterministic AND anti-hallucination is insufficient. | `results/frontier/contrastive_decode/contrastive_curve.csv` |
| **Runtime cascade** (#863) | Can tiny→base escalation achieve near-base CER at near-tiny compute? | ❌ CR signal has a binary cliff, not a smooth Pareto. Just use base (1.93×, eliminates the tax). | `results/frontier/runtime_cascade/pareto_frontier.csv` |
| **Reference validity** (#866) | Is base's 0.200 CER real or model-proximity? | ✅ Base and small produce 37.2% different text on clean audio. Base is completely stable. | `results/frontier/reference_validity/FINDINGS.md` |
| **Error pattern analysis** (#867) | Can pattern-based post-processing fix base's errors? | ❌ 64 unique patterns, only 9.4% recurring. 0.200 CER is a hard floor of genuine acoustic ambiguity. | `results/frontier/base_error_correction/substitution_table.csv` |
| **LLM rescoring** (#869) | Can deepseek-r1 correct base's substitution errors? | ❌ **Catastrophic**: 0/26 improved, CER 0.316→0.798. The LLM *rewrites* text instead of correcting. | `results/frontier/llm_base_rescore/FINDINGS.md` |
| **Error profile decomposition** (#865) | Do tiny and base make different *kinds* of errors? | ◐ Both ~70% substitution-dominated. CER difference = total count, not error types. | `results/frontier/error_profile_decomposition/profile_curve.csv` |

**Unified conclusion:** "Overlap-aware speaker ASR" as a routing problem is a tiny-model artifact. Whisper-base eliminates the separation tax at 1.93× compute. The remaining 0.200 CER is a hard floor of acoustic ambiguity — not fixable by pattern matching, T/S normalization, or LLM rescoring. Future work should focus on base+ model capabilities and external benchmark validation.

**Figures:** `results/frontier/model_scale/model_scale_analysis.png`, `results/frontier/error_profile_decomposition/error_profile_by_model.png`.

---

### Research Thread 2: Causal & Internal-State Hallucination Probe (Issue #855, PR #856)

**RQ:** *Can we detect separation-induced hallucination from inside Whisper during decoding, earlier than the output compression-ratio signal?*

**Motivation.** The `separation_tax` phase (Thread 1) closed the *acoustic* loop — a reference-free compression-ratio guard detects catastrophes at AUC ≈ 1.0. But CR is an **output** signal computed over the *full* decoded segment; by the time it inflates past 2.4, Whisper has *already emitted* the repetition loop to the user. A streaming system has already shown garbage. This probe asks whether Whisper's *internal state* during decoding provides an earlier warning.

**Why look inside Whisper?** Alternative approaches — better output metrics, multi-decode agreement, contrastive decoding — all failed in Phase 2 (Thread 1). The insight from a 3-second smoke test was revelatory: feeding Whisper-tiny a tone surrounded by silence reproduces the loop (token 7322 × 224) with `compression_ratio=37.2`, `no_speech_prob=0.82` (encoder: "no speech"), yet `avg_logprob=-0.065` (decoder: *highly confident*). The loop is a **confident attractor under an input the encoder flags as silent** — an encoder/decoder *decoupling*, not a confidence collapse. This motivated looking at token-level decoder state.

**Literature grounding (6-agent deep-research sweep, `docs/frontier/causal_hallucination_probe_litreview.md`):**
- Aparin et al. (2026, arXiv:2606.07473): Whisper's built-in filter fails because hallucinations carry *elevated* `avg_logprob`; encoder/SAE latents are linearly separable pre-loop. Steering cuts hallucination 86.9%→27.3%.
- Waldendorf et al. (ACL 2026 Findings, arXiv:2604.19565): Uncertainty metrics fail exactly in the clean/confident regime; attention-collapse-to-early-frames signature; detectors are task/model-specific.
- Wang et al., Calm-Whisper (Interspeech 2025, arXiv:2505.12969): 3/20 decoder self-attention heads cause >75% of non-speech hallucinations; head-mask fine-tune cuts it >80% at <0.1% WER.
- Viakhirev et al. (2026, arXiv:2604.08591): Compression-Seeking Attractor with self-attention rank collapse decoupling decoder from acoustics.
- Corpataux et al. (OpenReview 2026): Per-token Local Confidence Drop detects confident hallucinations as local discontinuities — direct prior art for trajectory detection.
- Sato et al. (Interspeech 2021, arXiv:2106.00949): Separation-hurts-below-a-crossover — established bedrock, not our discovery.

**Honest novelty assessment:** The confident-loop mechanism is now well-established (Aparin, Waldendorf, Calm-Whisper, Viakhirev). We *extend* it to the separation-tax regime; we do not discover it. The genuinely new contributions are: (1) **token-id repetition lock-in as a causal trip-wire** — no located prior work uses token-id repetition at this granularity as an early detector; (2) **quantifying the offline CR router's gain decay under causal prefix forcing** — an untouched deployment-analysis niche.

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

**Grand RQ:** *Can a local, offline LLM and cheap reference-free signals jointly decide when to separate, when to repair, how to read emotion, and whether to trust speaker attribution — without any ground-truth reference?*

This thread unifies two project directions (ASR×LLM synergy + emotion) across 7 emotion-frontier experiments + 5 ASR×LLM experiments + 1 capstone synthesis.

**Design choices and justification:**
- **Why deepseek-r1:7b via ollama?** We required an LLM that: (a) runs fully offline (no API calls, no data leakage — critical for a research project on sensitive debate audio); (b) has reasoning capability (chain-of-thought) for emotion interpretation and minimal-edit repair; (c) is small enough (7B) for reproducible local experimentation. Alternatives considered: GPT-4/Claude (online, not reproducible, privacy concern); Llama-3-8B (no reasoning traces); Qwen-2.5-7B (comparable but less documented for Chinese). deepseek-r1:7b was already cached locally and had the best documented Chinese reasoning performance at this size.
- **Why Whisper-tiny for emotion experiments?** The emotion experiments needed the *same* ASR outputs as the separation-tax baseline for cross-study comparability. Since Thread 1 established that the separation tax is tiny-specific, using tiny here means the emotion findings are *conservative* — they study emotion under worst-case ASR errors.
- **Why gain-invariant prosody for emotion?** Standard SER (Speech Emotion Recognition) models require labeled training data, which doesn't exist for our overlap-controlled debate corpus. Instead, we operationalize emotion as *gain-invariant acoustic prosody* (arousal-side), using the clean source's own prosody as reference — mirroring how CER uses the verified transcript. This follows the dimensional emotion tradition (Russell, 1980; Scherer, 2005) rather than discrete emotion categories.

**Literature grounding:**
- GenSEC-LLM challenge (arXiv:2409.09785, 2024): Makes post-ASR emotion recognition a first-class LLM task — but on clean single-speaker corpora. *Nobody has asked whether ASR errors induced by overlap+separation distort the emotion an LLM reads.*
- R3 (arXiv:2409.15551, 2024): Couples ASR error-correction with emotion recognition — but uses clean audio. Our controlled overlap×separation grid is the right instrument to test this coupling under realistic conditions.
- VoxEmo (arXiv:2603.08936, 2026): Benchmarks speech emotion recognition with speech LLMs — confirms that LLMs have weak prosody perception, motivating our tri-modal approach.

**Emotion Frontier Seven Studies (findings #14–#20):**

| # | Study | RQ | Outcome | Key evidence |
|---|---|---|---|---|
| 14 | **Emotional Separation Tax** (#815) | Does separation preserve or distort per-speaker emotion? | ✅ Separation *helps* emotion at all overlaps (opposite of ASR tax). The separate-or-not decision is **objective-dependent** — a single switch cannot serve both text and emotion. | `results/frontier/emotion_separation_tax/emotion_asr_divergence.png` |
| 15 | **Arousal→ASR probe** (#817) | Does acoustic arousal predict ASR difficulty? | ❌ **Bounding negative**: Pearson(arousal, CER) = 0.002. The emotion↔ASR relationship is asymmetric — separation affects emotion, but emotion does NOT predict ASR difficulty. | `results/frontier/arousal_asr_probe/arousal_asr_probe.png` |
| 16 | **Lexical emotion + tri-modal tax** (#819) | Can regex/lexicon valence + acoustic arousal + lexical valence jointly characterize the separation tax? | ◐ Lexical arm underpowered (seed lexicon fires on 2/16 snippets). Motivates the LLM reader. | `results/frontier/lexical_emotion_tax/lexical_emotion_tax.png` |
| 17 | **LLM × ASR critic** (#821) | Can a local LLM serve as reference-free QE and repair? | ❌ **Bounding negative**: LLM judge is dominated by free compression-ratio signal (+0.74 vs −0.41). GER repair net-harms (CER 0.951→0.983). Simple beats fancy. | `results/frontier/llm_asr_critic/llm_asr_critic.png` |
| 18 | **Objective-aware decoupled routing** (#823) | Can decoupling text-route and emotion-route recover both? | ✅ **Capstone**: decoupled keeps same CER (0.528) but halves emotion distortion (0.139→0.079), cutting joint regret ~14×. | `results/frontier/objective_aware_routing/FINDINGS.md` |
| 19 | **Emotion fidelity meter** (#825) | Can we estimate emotion fidelity with NO clean reference? | ◐ Usable coarse clean/contaminated gate (r=−0.51) but weak graded predictor (r=−0.20) that saturates. | `results/frontier/emotion_fidelity_meter/FINDINGS.md` |
| 20 | **Gate emotion cost** (#827) | Do CER-tuned hallucination-cure gates damage emotion? | ◐ Both gates cure CER AND damage emotion (objective-blind). Speaker gate dominates on both axes (cures more, damages least). | `results/frontier/gate_emotion_cost/FINDINGS.md` |

**ASR×LLM Frontier Studies:**

| Study | RQ | Outcome | Key evidence |
|---|---|---|---|
| **Semantic Emotion Tax** (#831) | Can a local LLM read implicit emotion the lexicon misses? | ✅ LLM coverage 0.70 vs lexicon 0.10 (~7×). Orthogonal 3rd modality vs acoustic-arousal & lexical-valence. | `results/frontier/semantic_emotion_tax/FINDINGS.md` |
| **Emotion-anchored repair** (#833) | Does anchoring LLM repair to detected stance cure over-correction? | ❌ **Negative**: no-repair 0.924 < naive 1.082 < anchored 1.122. Anchoring *worsens* it — giving the model "more latitude to rewrite" causes more hallucination. | `results/frontier/emotion_anchored_repair/FINDINGS.md` |
| **Tri-modal fusion** (#835) | Do orthogonal emotion modalities fuse to predict emotion damage? | ◐ Fusion helps semantic target (R² 0.10→0.16) but hurts acoustic one. Acoustic-arousal is the single best reference-free emotion-damage signal. | `results/frontier/emotion_modality_fusion/FINDINGS.md` |
| **Noise-robust router** (#814) | Can a reference-free router beat fixed strategies under noise? | ✅✅ Router 0.778 vs mixed 1.214 / gate 1.531. Recovers ~92% of oracle gap. Pearson(CR, tax) = 0.82. | `results/frontier/noise_robust_router/noise_robust_router.png` |
| **LLM speaker attribution** (#838) | Can LLM affect repair who-said-what? | ◐ Valence strongly encodes speaker role (AUC strength 0.78) but sign isn't knowable reference-free (naive 0.08, calibrated 0.92). | `results/frontier/llm_speaker_attribution/FINDINGS.md` |

**Unified conclusion:** Cheap Whisper decoder signals are the deployable lever for routing; acoustic prosody handles "acoustic emotion"; the local LLM's true value is *covering implicit semantic emotion*, not providing free repair or attribution rules.

**Capstone:** `docs/frontier/asr_llm_emotion_capstone.md` — a one-page synthesis with deployable decision recipe.
**Hero figure:** `results/frontier/asr_llm_frontier_capstone.png` (all five results on one canvas).

---

### Research Thread 4: Research Entropy Audit — Meta-Research on Agentic Ceremony Collapse (Issues #785/#787, PRs #786/#788)

**RQ:** *When an autonomous agentic loop runs unsupervised on a research repo, does it keep producing substance or drift into self-referential ceremony?*

**Motivation.** A scan of `src/` revealed ~795 of 893 `*.py` files were ceremony-named (handoff/receipt/coordination/completion-summary). Independent content check: **0 of 795 contained real computation** (compute-import 3.5% vs 17% for substance; 0.11 vs 4.07 arithmetic ops/file). The git timeline shows a clean epidemic arc: birth (2026-06-02, 35 substance / 0 ceremony) → first collapse (06-07) → peak (+250 ceremony files on 06-12) → recovery (06-15 cleanup).

**Why this matters for research methodology.** This is not a code quality issue — it is a *research integrity* issue. Ceremony files that compute nothing but claim "completion" create an illusion of progress that misleads both human reviewers and automated agents. The phenomenon is relevant to any project using LLM-based code generation for research.

**Approach:**
- Built `src/research_entropy_audit.py` — a two-signal classifier (filename pattern + content computation check) + git timeline visualization + bounded degeneration index. `make entropy-audit`.
- Built `scripts/harness/entropy_guard.py` — a stdlib-only *advisory* guard wired into `make quality-predev` that warns (never blocks) when a change adds ceremony with no substance.
- **Cleaned 6,000+ ceremony files** (803 src/*.py + 1,112 tests + ~4,360 result artifacts). Lean-rewrote `project_harness.py` from ~4,400 lines to genuine baseline smoke.
- **Result:** Entropy saturation 0.894 → 0.035; degeneration index 0.46 → 0.00; tests 3,304 → 825 all green; import-closure 0 violations.

**Module:** `src/research_entropy_audit.py` + `scripts/harness/entropy_guard.py` + `docs/frontier/agentic_research_entropy.md`.

---

### Research Thread 5: Engineering Harness (Issue #780, PR #781)

**Motivation.** The project needed infrastructure to enforce research discipline: critical code changes must include paired tests, results must be labeled by evidence level, and PRs must include structured impact summaries. We adapted `ref/code-tape`'s Harness to this Python repository.

**Design choices:**
- **Why not adopt code-tape's training-camp scoring/auto-merge?** Those mechanisms optimize for *throughput* (maximize merged PRs), which directly contributed to the ceremony collapse documented in Thread 4. We adopted only the *quality* pillars: git hooks, knowledge-base contract, SDD, TDD.
- **Why GitNexus for the knowledge base?** GitNexus provides a code knowledge graph with symbol-level impact analysis, enabling the `Contract Guard` CI check that verifies critical skeleton changes include paired tests. No comparable open-source tool provides this at the symbol level.

**Four pillars:**
1. **Git hooks** (`.githooks/{pre-commit,pre-push}`): pre-commit runs fast test gate; pre-push runs GitNexus contract + full test gate. `SKIP_QUALITY_HOOKS=1` escape hatch.
2. **GitNexus knowledge-base contract** (`scripts/harness/contract_{rules,check}.py`): Critical skeleton classification (router-core / evaluation-core / harness / references / gold-results / authority-docs). Changes to critical code *must* include paired `tests/test_<module>*.py` + structured impact summary.
3. **SDD**: Authority-doc hierarchy + `docs/adr/ADR-001` + PR template with structured GitNexus impact summary.
4. **TDD**: Contract mechanically enforces paired tests for critical code changes. 41 harness contract tests cover the engine itself.
5. **repo-guard LLM code review** integration: every PR receives automated review comments; author must respond to every finding before merge.

**Verification:** Pre-push gate passes live — GitNexus index (26,296 nodes) + contract + full suite (3,253 tests OK at adoption time).

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

### Summary of Research Contributions

Across ~45 merged PRs and 36 frontier result directories, my contributions follow a consistent research methodology:

1. **Pre-registered hypotheses with falsifiable success/kill criteria** — every frontier study declares what would falsify it before running experiments.
2. **Honest negative results as findings** — 8 of 15+ frontier studies produced clean negatives (LLM rescoring catastrophic, cascade too coarse, arousal doesn't predict difficulty, etc.). Each negative narrows the solution space and is documented with the same rigor as positives.
3. **Literature-grounded novelty claims** — the causal hallucination probe includes a 6-agent literature sweep with per-hypothesis novelty assessment; honest about what is established bedrock vs genuinely new.
4. **Design choice justification** — model selection (Whisper-tiny for visibility, base for validity), LLM selection (deepseek-r1 for offline/reasoning), signal selection (gain-invariant prosody for label-free emotion) each grounded in specific constraints.
5. **Evidence discipline** — all frontier results labeled `experimental/frontier`; gold tables and verified references never touched; synthetic/silver references clearly marked.
6. **Reproducibility** — every module has paired unit tests; injected fake-LLM/Whisper for CI; all results in committed CSVs with reproducible `python -m src.<module>` commands.

### Modules (complete list)

`src/causal_hallucination_probe.py`, `src/model_scale_analysis.py`, `src/confidence_calibrated_router.py`, `src/multi_decode_voter.py`, `src/contrastive_decode.py`, `src/runtime_cascade.py`, `src/error_profile_decomposition.py`, `src/noise_robust_router.py`, `src/semantic_emotion_tax.py`, `src/emotion_anchored_repair.py`, `src/emotion_modality_fusion.py`, `src/llm_speaker_attribution.py`, `src/frontier_capstone_figure.py`, `src/emotion_separation_tax.py`, `src/arousal_asr_probe.py`, `src/lexical_emotion.py`, `src/lexical_emotion_tax.py`, `src/llm_asr_critic.py`, `src/emotion_fidelity_meter.py`, `src/gate_emotion_cost.py`, `src/objective_aware_routing.py`, `src/prosody.py`, `src/noise_robust_gate.py`, `src/speaker_conditioned_gate.py`, `src/gate_selector.py`, `src/decoder_cure_noise.py`, `src/hallucination_router.py`, `src/reference_free_qe.py`, `src/separation_tax_phase.py`, `src/hallucination_cure_eval.py`, `src/speaker_similarity_probe.py`, `src/noise_robustness.py`, `src/research_entropy_audit.py`, `src/adaptive_router_v2.py`, `src/risk_aware_selector.py`, `src/compute_aware_cascade.py`, `src/speaker_*.py`, `src/meeteval_*.py`, `src/external_validation_*.py`, `src/project_harness.py`; paired tests for all; `scripts/harness/*`, `.githooks/*`, `docs/harness/*`, `docs/frontier/*`.

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

### 5. Contribution boundary

吴方舟的贡献重点是主 ASR 实验管线、route-selection framing、AudioDepth 前沿
研究、证据边界维护和最终报告整合。已知限制仍然存在：gold benchmark 很小，
synthetic / silver 证据不能替代 gold，real-meeting generalization 未完全证明，
Stage-2 fallback / review policy 仍需更多验证，AudioDepth 需要独立评审后才
能进入任何 stable mainline claim。

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
