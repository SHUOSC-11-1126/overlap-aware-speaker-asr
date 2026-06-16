# When Should We Separate? Boundary-aware, Compute-aware, Speaker-aware, and Agent-augmented ASR for Overlapping Speech

## 1. Introduction

Multi-speaker audio is hard to transcribe reliably when speakers interrupt each other or talk at the same time. In those cases, a single ASR pass often produces repeated fragments, insertions, missing spans, and speaker attribution errors.

This project asks a focused question:

> When should we separate, and when does separation hurt more than it helps?

The answer is not a single model or a universal separation rule. Instead, the project studies mixed ASR, separated speaker-track ASR, cleaned separated transcripts, adaptive routing, speaker-aware evaluation, risk-aware selection, and now a broader agentic research direction.

## 2. Background and Motivation

The repository started from an earlier overlapping-speech ASR project and turned it into a benchmark-driven research engineering pipeline. The goal is to understand the conditions under which separation improves accuracy and when it introduces hallucinated repetition or over-deletion.

The motivation is practical:

- meeting and debate audio often contains overlap;
- raw ASR may transcribe the words but still lose who said what;
- separation can help, but it can also amplify repetition and insertion errors;
- a better system should select the safest transcript type for the observed overlap regime;
- once the baseline is stable, the project can also serve as an agentic research playground for more ambitious exploration.

## 3. Dataset and Benchmark

The gold benchmark contains five manually verified cases:

| case_id | overlap_level | purpose |
| --- | ---: | --- |
| NoOverlap | 0 | clean baseline |
| LightOverlap | 1 | light cross-talk |
| MidOverlap | 2 | moderate overlap |
| HeavyOverlap | 3 | strong overlap |
| OppositeOverlap | 4 | highly competitive overlap |

Each case has:

- mixed audio,
- separated speaker tracks,
- mixed ASR output,
- separated speaker-track ASR output,
- duplicate-suppressed cleaned separated output,
- a verified reference transcript pair for speaker-aware evaluation.

In addition, the repository contains synthetic silver benchmarks and a held-out synthetic split. These are used for robustness validation only and are not gold evaluation.

## 4. Method

### 4.1 Mixed ASR

The mixed baseline uses `whisper-small` directly on the mixed audio. It is the simplest non-separation path and provides the baseline against which all other methods are measured.

### 4.2 Separated Speaker-track ASR

For each case, the already-separated `spk1` and `spk2` waveforms are transcribed independently with `whisper-small`. The resulting segments are merged into a speaker-attributed transcript in start-time order.

### 4.3 Duplicate Suppression

The cleaned transcript is produced by a lightweight duplicate suppression pass over the separated speaker transcript. The goal is to remove repeated hallucinated fragments while preserving speaker order.

### 4.4 Error Type Analysis

We analyze the edit structure of the CER errors and summarize substitution, deletion, insertion, and repetition-related patterns.

This explains why separation can degrade quality in lighter overlap:

- `LightOverlap` is dominated by insertion and repetition hallucination;
- `MidOverlap` shows a similar pattern;
- `HeavyOverlap` and `OppositeOverlap` benefit more clearly from separation.

### 4.5 Adaptive Router v1 and v2

The router selects one of:

- `mixed_whisper`
- `separated_whisper`
- `separated_whisper_cleaned`

The router does not use ground-truth CER as an input feature. CER is only used after the decision is fixed.

The first router version is overlap-only. The second version adds transcript-instability signals such as:

- length inflation,
- duplicate removal count,
- repetition proxy signals,
- speaker length imbalance,
- method disagreement proxies.

### 4.6 Speaker-aware CER

Normal CER collapses the transcript into one string and can hide speaker attribution problems. Speaker-aware CER evaluates `speaker_1_text` and `speaker_2_text` separately and reports per-speaker CER, macro CER, and speaker gap.

### 4.7 cpCER-lite

cpCER-lite is a lightweight permutation-aware evaluation. It compares direct and swapped speaker mappings and chooses the better one. This helps check whether the main issue is speaker swap or content-level transcription quality.

### 4.8 Synthetic Silver Validation

Synthetic overlap samples are used as supplementary robustness evidence. They are not gold evaluation. Their purpose is to show whether the router behavior remains stable outside the five verified benchmark cases.

### 4.9 Held-out Synthetic Split

A larger synthetic split is divided into dev and test subsets. Dev is useful for inspecting thresholds and behavior, but test is reserved for final evaluation.

### 4.10 Risk-aware Final Selector

The risk-aware selector is a reference-free final selection layer. It uses only deployment-visible stability signals and risk proxies to choose a final transcript type. Ground-truth CER is used only after selection, for evaluation.

## 5. Experiments

### 5.1 Global CER

| strategy | average CER |
| --- | ---: |
| fixed_mixed_whisper | 0.302093 |
| fixed_separated_whisper | 0.191846 |
| fixed_separated_whisper_cleaned | 0.181681 |
| router_v2 | 0.120042 |
| oracle_best | 0.120042 |

### 5.2 Error Type Analysis

The error-type study reveals the main failure mode of separated ASR under light and moderate overlap:

- repeated hallucinations,
- insertion-heavy errors,
- duplicated tail fragments.

### 5.3 Adaptive Routing

The router chooses the following best method per gold case:

| case_id | selected_method |
| --- | --- |
| NoOverlap | separated_whisper |
| LightOverlap | mixed_whisper |
| MidOverlap | mixed_whisper |
| HeavyOverlap | separated_whisper |
| OppositeOverlap | separated_whisper |

### 5.4 Synthetic Silver Validation

Original synthetic silver results:

| strategy | average CER |
| --- | ---: |
| v1 | 0.350902 |
| v2 | 0.167553 |
| oracle | 0.082239 |

The synthetic silver benchmark exposed a stability issue in the overlap-only router. It looked strong on the gold benchmark but failed on synthetic NoOverlap. The feature-based router v2 improved robustness by reacting to instability signals.

### 5.5 Held-out Synthetic Split

Held-out synthetic test results:

| strategy | average CER |
| --- | ---: |
| v1 | 0.361350 |
| v2 | 0.335326 |
| oracle | 0.115181 |

The held-out split confirms that v2 is more stable than v1, but there is still a non-trivial gap to oracle performance.

### 5.6 Router Ablation

Router ablation shows that repetition and duplicate-removal features are more useful than length ratio alone. This supports the idea that instability signals matter more than overlap level by itself.

### 5.7 Speaker-aware CER

Speaker-aware CER shows that cleaned separated output can improve some overlap cases, but raw separated output remains better in others.

| case_id | separated_whisper macro CER | separated_whisper_cleaned macro CER |
| --- | ---: | ---: |
| NoOverlap | 0.054312 | 0.089278 |
| LightOverlap | 0.194170 | 0.135164 |
| MidOverlap | 0.175908 | 0.168620 |
| HeavyOverlap | 0.110821 | 0.146535 |
| OppositeOverlap | 0.047479 | 0.083193 |

### 5.8 cpCER-lite

cpCER-lite did not find speaker permutation mismatch in the five gold cases. The direct speaker assignment is always better than the swapped one, which means the main errors are content-level rather than speaker-swap-level.

### 5.9 Risk-aware Selector

| strategy | average CER |
| --- | ---: |
| risk_aware_selector | 0.134587 |
| router_v2 | 0.120042 |
| oracle_best | 0.120042 |

The risk-aware selector is deliberately conservative and explainable. It is not the best-CER result, but it is useful as a deployment-oriented final selector.

### 5.10 Compute-aware Cascade Frontier

The repository now includes an `experimental/frontier` compute-aware cascade analysis layer. This layer does not change any stable gold benchmark references or use CER as an input signal. Instead, it scores already-fixed route choices using observed runtime fields, route-normalized RTF, and held-out synthetic-split robustness views.

#### Gold compute-aware view

| strategy | average CER | relative cost vs fixed separated |
| --- | ---: | ---: |
| router_v2_costed | 0.120042 | 0.929533 |
| risk_aware_costed | 0.134587 | 0.929533 |
| budget_cascade | 0.134587 | 0.929533 |

Key observations:

- `router_v2_costed` is the strongest gold adaptive route.
- The committed gold cascade tables are fully backed by observed runtime rather than proxy fallback.
- Under the joint CER/cost Pareto view, the gold frontier reduces to `fixed_mixed_whisper` and `router_v2_costed`.

#### Held-out synthetic split cascade validation

| strategy | average CER | relative cost vs fixed separated |
| --- | ---: | ---: |
| router_v2_synthetic_costed | 0.285187 | 0.704888 |
| budget_cascade | 0.367582 | 0.854921 |
| cleaned_preferred_cascade | 0.249877 | 0.945686 |

Key observations:

- `router_v2_synthetic_costed` is the best balanced synthetic-split route.
- `fixed_separated_whisper_cleaned` remains the strongest synthetic-split accuracy-first route.
- `budget_cascade` is cheaper than always separated, but it degrades more sharply on held-out synthetic split.

#### Decision-support layer

The frontier work now includes:

- runtime provenance audits
- route-normalized RTF audits
- Pareto frontier classification
- profile-based recommendation cards
- cross-dataset robustness gap comparisons
- family-level recommendation stability
- a consolidated decision matrix
- a generated artifact index
- a generated benchmark-readiness scaffold
- a generated benchmark handoff plan
- a generated profile playbook
- a generated benchmark checklist
- a generated benchmark manifest template
- a generated benchmark status board
- a generated benchmark execution summary
- a generated benchmark execution queue
- a generated benchmark session ledger
- a generated benchmark dependency graph
- a generated benchmark blocker matrix
- a generated benchmark runbook card
- a generated benchmark milestone card
- a generated benchmark phase checkpoint card
- a generated benchmark completion dashboard
- a generated benchmark handoff packet

This turns the cascade from a single offline plot into a small decision-support stack. The current evidence suggests:

- `router_v2` is the cleanest default balanced family.
- `fixed_mixed_whisper` is the most stable cost-first choice.
- `fixed_separated_whisper_cleaned` is the most robust accuracy-first alternative across gold and held-out synthetic split.

## 6. Results and Discussion

The project leads to eight main findings:

1. Speech separation is useful, but not universally beneficial.
2. The main degradation in `LightOverlap` and `MidOverlap` is caused by insertion and repetition hallucination.
3. Speaker swap is not the dominant error source in the five gold cases.
4. Router v1 is fragile outside the small gold benchmark, while router v2 is more stable.
5. Synthetic silver validation is valuable for exposing overfitting, but it is not gold evaluation.
6. Speaker-aware and permutation-aware evaluation reveal behaviors that global CER alone does not show.
7. Compute-aware cascade analysis is now strong enough to support deployment-style trade-off discussion, not just raw CER comparison.
8. The repository now supports a second, broader interpretation: the stable baseline is complete, and the project can also serve as an agentic research workspace for ambitious extensions.

The strongest practical conclusion is that a system should separate selectively, not blindly. A mixed transcript is safer in some overlap regimes, while separated or cleaned separated output is better in others.

The newer frontier conclusion is more specific: once selective separation is accepted, the next question is no longer only "which route wins CER?" but also "which route family is stable across operating points?" The current evidence favors `router_v2` as the default balanced family, `fixed_mixed_whisper` as the cheapest stable fallback, and `fixed_separated_whisper_cleaned` as the strongest robustness-oriented accuracy path.

## 7. Limitations

This project is intentionally bounded.

- No new ASR model training was performed.
- The gold benchmark is small.
- Synthetic references are silver, not gold.
- The router is rule-based rather than learned.
- External benchmark validation is not yet complete.
- LLM/RAG remains a future extension rather than the core quantitative result.

## 8. Future Work

The stable baseline opens a path toward more ambitious agentic ASR systems:

1. Boundary-aware phase diagram
2. Compute-aware cascaded recognition
3. Speaker-profile-assisted risk detection
4. Agentic LLM critic and repair loop
5. External mini validation
6. Learned router from synthetic split
7. Demo-oriented ASR intelligence system

AudioDepth-Router is a new learned-router frontier experiment inspired by RGB-D image recognition. It treats overlapping speech as time-frequency occlusion: a mixed-audio log-mel spectrogram is augmented with depth-like overlap and uncertainty channels, then a small CNN predicts whether a sample should route to `mixed`, `separated`, or `cleaned` ASR output. This is not a new ASR model and does not replace router_v2.

The current deployable AudioDepth result is deliberately labeled `experimental/frontier` plus `synthetic/silver`. Deployable mode uses only mixed audio. Analysis-only mode can use separated tracks to build simultaneous-activity and speaker-dominance maps, so it must not be described as deployable. On synthetic split TEST, deployable AudioDepth currently reports `classification_accuracy = 0.7200` and `routing_average_cer = 0.436666`; this is worse than router_v2 (`0.335326`) and oracle (`0.115181`). The useful finding is therefore negative/diagnostic: local audio-visual depth proxies alone do not yet capture the text-level instability signals that router_v2 uses.

The frontier has now been widened into a model-zoo and hybrid-routing exploration pass. The follow-up scripts test whether log-mel-only models, balanced depth CNNs, tiny ResNet/CRNN/transformer variants, late fusion, and confidence cascades can recover more signal than the MVP. This is still frontier work, not a baseline rewrite.

On the current synthetic split TEST run, the best frontier row is `mlp_handcrafted` with routing CER `0.166381`; `hybrid_late_fusion` reaches `0.176381`; and the best confidence cascade reaches `0.165545`. These rows beat the MVP and the matched router_v2 synthetic split row, but they remain synthetic/silver evidence and should be rechecked before being treated as a stable routing replacement.

The next systematic validation pass adds a controlled stress benchmark and application layer. It generates 150 synthetic stress audio samples and evaluates 80 with a clearly labeled `synthetic/silver_proxy` route-CER model because Whisper is unavailable in the current runtime. On 64 held-out systematic samples, `hybrid_late_fusion_v2` reaches routing CER `0.249477`, improving over the old router_v2 proxy row (`0.355793`) and the MVP-style separated route (`0.392813`). It does not beat the earlier model-zoo best (`0.166381`) or the fixed-cleaned proxy row (`0.196876`), so the honest conclusion is narrower: systematic hybrid features remain promising and interpretable, but this pass is not a stable-baseline replacement.

Bootstrap CI for the systematic pass shows `hybrid_late_fusion_v2` mean CER `0.251083` with 95% CI `[0.140321, 0.387586]`, `hybrid_mlp_v2` mean CER `0.387153` with 95% CI `[0.198248, 0.608961]`, `old_router_v2` mean CER `0.355984` with 95% CI `[0.289375, 0.425755]`, and oracle mean CER `0.127656` with 95% CI `[0.095779, 0.160191]`. The cost cascade is a simulated application proof rather than hardware timing evidence; in this pass it mainly identifies review burden and does not yet save cost versus all-strong routing at high confidence thresholds.

Stage 24 resolves the missing-Whisper blocker for a small sampled run by installing and selecting `faster-whisper` `1.2.1` in the bundled Python runtime. The system `ffmpeg` command remains unavailable, so the real-ASR path uses faster-whisper/PyAV rather than openai-whisper. The sampled run uses model size `base`, language `zh`, and 10 stress samples, producing 50 transcript rows under `results/transcripts_audio_depth_real_asr/`. Runtime was `144.3034` seconds total, with the first sample including model download/warmup cost.

The real-ASR evaluation is deliberately separate from Stage 23 proxy evidence. It compares real Whisper hypotheses against synthetic/silver references, not gold human transcripts. On this 10-sample slice, fixed mixed CER is `0.778020`, fixed separated CER is `0.790631`, fixed cleaned CER is `0.790631`, router_v2 CER is `0.718965`, `hybrid_late_fusion_v2` CER is also `0.718965`, and oracle CER is `0.713965`. This is a useful negative or boundary finding: the sampled real Whisper run does not yet show the systematic AudioDepth router beating router_v2, even though the proxy run did. The honest next step is a larger real-ASR sample and a gold sanity subset before any stable-routing claim.

Stage 25 turns that boundary into a failure audit. The first finding is that the evaluation slice gives routing very little room: 7 of 10 audited samples have real route gap `<0.01`, and 8 of 10 have all-route CER above `0.65`. The second finding is that reference quality is a real limitation: all audited references are synthetic/silver, several are short, and length ratios show that Whisper often outputs substantially shorter or longer text than the reference. The third finding is that normalization is not the main issue; the normalized hybrid CER remains `0.718965`.

The Whisper configuration sweep shows that `base_beam1` is the best tested mixed-audio setting on this slice, with average mixed CER `0.747664`; `base_beam5` is `0.778020`; VAD is `0.779231`; and the tested prompt is worse at `1.290242`. `small_beam5` was blocked as a partial run because model download did not complete in the session. The stratified 20-sample expansion is more balanced but reaches the same router conclusion: router_v2 CER `0.696410`, `hybrid_late_fusion_v2` CER `0.696410`, oracle CER `0.674610`. The scientific interpretation is not that AudioDepth failed as an idea; it is that the current real-ASR validation pipeline is not yet strong enough to adjudicate the proxy-trained router. The next move should be gold reference sanity checks, stronger Whisper settings once models are cached, and route-gap-aware evaluation.

Stage 26 addresses that evaluation-pipeline issue by building a controlled route-sensitive benchmark from known snippet utterances. The inventory contains 26 source utterances, all with candidate Whisper-small transcripts and no manual verified transcript yet. The benchmark therefore runs in `silver_plus_unverified` mode and exports `controlled_verification_pack.csv` so future manual review can upgrade it to micro-gold.

The generated controlled benchmark contains 80 samples spanning overlap ratios from `0.0` to `0.8`, speaker dominance settings, durations, and interruption styles. The first real Whisper route evaluation covers 40 samples with `faster-whisper` base in `60.7795` seconds. Unlike the Stage 24/25 slice, this controlled set creates a strong route-level contrast between fixed mixed and separated routes: fixed mixed CER is `0.467818`, fixed separated and fixed cleaned are `0.260124`, and oracle is `0.255923`, for oracle headroom of `0.211895` over fixed mixed. The separation gain curve is negative across all evaluated overlap ratios, meaning separation helps relative to mixed throughout this controlled slice.

The router result is encouraging but bounded. Router_v2 reaches CER `0.383122`, the Stage 23 heuristic reaches `0.319713`, and the newly trained controlled hybrid/fusion routers reach CER `0.256816` with route accuracy `0.95`, close to oracle `0.255923`. However, fixed separated is already `0.260124`, so the controlled router's gain over that simple policy is small. The controlled result proves that real-ASR routing can beat router_v2 when the benchmark is route-sensitive, but it also shows that the current benchmark is separation-dominant rather than a perfectly balanced mixed/separated/cleaned decision set.

Stage 27 responds to that limitation with a balanced route-sensitive v2 benchmark rather than a stable-baseline change. The generator creates a 240-sample candidate pool and a 120-sample final benchmark with equal mixed-win, separated-win, cleaned-win, and review-needed anchors. The real-ASR evaluation is stratified across those anchors and covers 60 samples with `faster-whisper` base. References remain `silver_plus_unverified`, so the result is frontier evidence, not gold evidence.

The actual real Whisper oracle distribution is mixed `34`, separated `26`, and cleaned `0`, with `57` review candidates flagged by high CER, low route gap, duplicate density, or length inflation. This is more balanced than Stage 26 because fixed separated no longer dominates the whole slice, but it also exposes a negative finding: the cleaned-win anchors did not become cleaned-oracle cases under the current ASR and post-processing path.

The balanced route-winner router reaches CER `0.502854` and route accuracy `0.983333`, matching oracle CER `0.502854` on this evaluated v2 slice. Router_v2 reaches `0.643520`, fixed mixed `0.726484`, fixed separated `0.667789`, and fixed cleaned `0.667789`. The predicted route distribution is mixed `33`, separated `27`, cleaned `0`, which is the key proof that this router is not blindly selecting separated. The remaining gap is equally important: cleaned routing is still unproven and should be treated as a future-target or negative result until a real cleaned-win slice appears.

AudioDepth v2 maps were generated for the 60 evaluated samples under `analysis_only_irm_proxy`, using mixed pseudo-logmel plus source-energy overlap and dominance proxies. These maps are useful for diagnosing RGB-D-inspired time-frequency occlusion structure, but they are not deployable because they use source tracks.

Stage 28 then separates the deployable AudioDepth question from the analysis-only upper-bound question. The new deployable AudioDepth v2 maps use mixed audio only: C1 is mixed logmel, C2 is a mixed-only overlap proxy built from energy variation, spectral entropy/flatness, high-band density, and zero-crossing density, and C3 is a mixed-only uncertainty proxy built from spectral flux, entropy movement, energy variance, and band conflict. The run generated 200 maps total, 120 from controlled_v2 and 80 from controlled_v1, with 100 labelled real-ASR rows available for audits.

The feature audit finds modest but real signal rather than a decisive route detector. The strongest simple correlations include overlap_proxy_std with separation helpfulness (`0.304518`) and overlap_proxy_mean with route_gap (`-0.364112`). The embedding probe is more encouraging: the small resnet oracle-route probe reaches accuracy `0.655172` and macro-F1 `0.618421`, while target-family embeddings show route-regime structure even though route-gap prediction remains weak.

As a Stage-1 acoustic gate, the current deployable AudioDepth v2 is conservative. Held-out gate accuracy is `0.758621` and macro-F1 is `0.431525`; ambiguous/review recall is high at `0.958333`, false-safe rate is `0.034483`, but easy_mixed recall and separation_helpful recall are both `0.0`. The two-stage cascade therefore does not beat router_v2 yet: both reach controlled_v2 CER `0.643520`, and the text-probe reduction rate is only `0.016667`. This is still useful evidence for the new positioning: AudioDepth has pre-ASR acoustic representation value, but the handcrafted deployable channels need stronger learned overlap detection before they can confidently resolve many samples before text probing.

The immediate follow-up calibration changes that picture. Instead of letting `review_risk` swallow every high-CER route, the calibrated gate separates the route-action label from the risk flag and treats separation gain over mixed as the signal for `likely_separation_helpful`. The calibrated held-out gate reaches accuracy `0.724138`, macro-F1 `0.475000`, easy_mixed recall `0.400000`, and separation_helpful recall `0.800000`. The controlled_v2 threshold sweep reaches CER `0.533160` while reducing text-probe calls by `0.716667` at thresholds `0.30` to `0.50`. This is the first evidence in this line that deployable AudioDepth can serve as a useful pre-ASR gate, though its false-safe rate remains `0.183333` and the stronger Stage 27 balanced router/oracle CER remains lower at `0.502854`.

The compute-aware line is now beyond a placeholder idea: the immediate next step is a controlled hardware/runtime benchmark that can replace repository-local runtime comparisons with stronger deployment evidence. The repository now includes a generated benchmark-readiness scaffold, a staged benchmark handoff plan, a profile playbook, a benchmark checklist, a benchmark manifest template, a benchmark status board, a benchmark execution summary, a benchmark execution queue, a benchmark session ledger, a benchmark dependency graph, a benchmark blocker matrix, a benchmark runbook card, a benchmark milestone card, a benchmark phase checkpoint card, a benchmark completion dashboard, a benchmark operator brief, a benchmark evidence receipt, and a benchmark handoff packet, so the next contributor can see which artifacts matter first, what order to refresh them in, how the resulting profile choices should be interpreted, which run metadata must be captured during execution, where to record that metadata, which phases are still template-only, which blocker category each pending phase belongs to, which phase should move next, which exact benchmark step should run first, what evidence each step must leave behind, which step unlocks the next one, how urgent each blocker is, what the first one-page execution brief should say, where the next milestone boundary sits, how each phase should be checked off, what the top-level pending state looks like, which single plain-language operator note should be read first, which writeback receipt should be checked before closing the run, and which single note to start from before touching the lower-level files. After that, the most interesting future work will still be the work that clarifies a boundary, exposes a failure mode, or tests an idea that is intentionally a little risky.

That benchmark coordination stack is now also linked back to the broader frontier workflow: `results/figures/cascade_benchmark_frontier_bridge.md` connects the current benchmark operator step to the newer breadth-first frontier queue. This does not add any new measurement result. Its value is organizational: it shows why the controlled runtime foundation still deserves priority even while several narrower frontier handoffs are now ready in parallel.

That benchmark stack is now also slightly easier to close out correctly: `results/figures/cascade_benchmark_receipt_bridge.md` links the benchmark handoff packet directly to the evidence receipt target. This still adds no new benchmark claim. Its value is procedural: it reduces the last bit of ambiguity between the note that tells the next contributor where to start and the receipt that should eventually capture what happened.

To support a broader next phase, the harness now also exposes a generated breadth-first frontier status table in `results/figures/project_harness_report.md`. That table does not claim new experimental results; it simply makes the current evidence path, expected output, and next step visible for `speaker_profile`, `meeteval_compatibility`, `llm_critic`, `external_validation`, and `demo_excellence`, which makes it easier for future agents to spread effort across multiple frontiers instead of deepening only one line at a time.

That coordination layer is now also more executable: `results/figures/frontier_execution_queue.md` adds a lightweight breadth-first queue across the same frontiers. This is not new model evidence. Its value is organizational: it turns the growing set of frontier handoff cards into one short ordered list so the next contributor can choose the first breadth-first move with less friction.

The current queue head is `meeteval_compatibility`, and the immediate next move is to use the MeetEval readiness path to stage a narrow dry run before the remaining frontier backlog is touched.

That queue is now also easier to scan at a glance: `results/figures/frontier_focus_card.md` compresses the current queue head into a one-card starting point. This is still purely coordination support, but it reduces the time from opening the repository to seeing the current breadth-first priority.

That queue head is now also easier to hand off without file-hopping: `results/figures/frontier_handoff_packet.md` points the current frontier directly at its next artifact and expected evidence target. This still adds no new research claim. It is a tiny coordination convenience, but one that makes the breadth-first workflow more executable for the next contributor.

That queue head is now also easier to close out cleanly: `results/figures/frontier_receipt_packet.md` pushes the same coordination thread one step further down to the receipt layer. This still adds no new research claim. Its value is organizational: it reduces the last bit of ambiguity between the artifact to open now and the receipt target that should eventually capture what happened.

That receipt-aware layer is now also broader rather than head-only: `results/figures/frontier_receipt_map.md` lays out the prerequisite artifact and receipt target for every current frontier in one table. This still adds no new research claim. Its value is again organizational, but in a slightly different way: it makes it easier for future contributors to pick up any frontier in parallel without first reverse-engineering where its writeback should land.

That broader receipt-aware layer is now also easier to act on in parallel: `results/figures/frontier_parallel_picklist.md` turns the same current frontier set into a parallel-friendly pickup table with queue order, pickup artifact, and receipt target side by side. This still adds no new research claim. Its value is practical rather than analytic: it lowers the overhead for contributors who want to pick up one frontier slice without losing sight of the broader breadth-first order.

That breadth-first push now also includes a first concrete `meeteval_compatibility` bridge: `results/figures/meeteval_compatibility_note.md` plus JSONL exports for verified reference segments and speaker-attributed hypothesis segments. This is intentionally framed as a compatibility scaffold rather than a completed MeetEval / cpWER result, but it turns that frontier from a pure idea into a reusable artifact.

That bridge is now also easier to hand off: `results/figures/meeteval_readiness.md` adds a narrow dry-run readiness card. It still does not claim that MeetEval has been executed. Instead, it makes the current state more honest and more usable at the same time by showing that the export is ready for a diagnostic next step while also exposing that cleaned fallback still dominates the current hypothesis mix.

That handoff is now one step more executable: `results/figures/meeteval_dry_run_handoff.md` compresses the next action into a single-row packet with a recommended first slice, a primary blocker, and an expected evidence file. This still does not claim any completed MeetEval or cpWER run. Its value is narrower and more practical: it reduces the ambiguity around what the first diagnostic follow-up should actually look like.

That expected evidence file now also exists as a template: `results/figures/meeteval_dry_run_receipt.md` defines the narrow run scope, expected inputs, expected outputs, and post-run writeback note for the first diagnostic pass. This still stops well short of claiming that any dry run has happened. What it adds is a cleaner handoff boundary: the next contributor no longer has to infer what the first evidence writeback should contain.

That handoff boundary is now also ordered as a checklist: `results/figures/meeteval_dry_run_checklist.md` ranks the verified cases for the first diagnostic pass so the next contributor can choose a concrete exported case before filling the receipt slot. This still does not claim MeetEval or cpWER execution. It simply makes the pre-evaluation queue more actionable.

It now also includes a first concrete `speaker_profile` bridge: `results/figures/speaker_profile_risk_summary.md` plus a lightweight text-profile similarity table built from the `con/pro` snippet transcripts. This is deliberately not presented as a voiceprint success story. In fact, its current research value comes from a failure signal: the simple overlap-based profile prefers swapped alignment across the verified gold cases, which makes the limitation visible and gives future agents a sharper target for stronger profile methods.

That bridge is now also easier to scan in one glance: `results/figures/speaker_profile_triage.md` adds an aggregate handoff card that compresses the current result into a single dominant pattern. It still does not claim any speaker-attribution success. Instead, it makes the present limitation even clearer by recording that the current gold set collapses into `swapped_bias`, which strengthens the case for trying a materially stronger profile method next.

That aggregate finding is now also easier to pick up as a concrete next move: `results/figures/speaker_profile_method_handoff.md` compresses the stronger-method recommendation into a one-row packet. This still does not claim that any improved profile method has succeeded. Its role is narrower and more operational: it names the first method direction and expected evidence target so the next contributor can test a stronger baseline without first reinterpreting the triage card.

That stronger-method packet now also has an explicit evidence slot: `results/figures/speaker_profile_method_receipt.md` defines the template-only writeback target for the first stronger profile trial. This still does not claim that any profile improvement has happened. What it adds is a cleaner handoff boundary, because the next contributor no longer has to invent the first receipt format before recording what the stronger baseline actually did.

The breadth-first push now also includes a first `llm_critic` bridge: `results/figures/llm_critic_qualitative_note.md` plus a qualitative summary table derived from structured risk cues. This is not a true repair loop yet, and it is not presented as verified correction. Its value is that it turns existing risk signals into an explicit critique, candidate repair direction, and uncertainty statement, which makes the next agentic step more concrete.

That critic bridge is now slightly more executable: `results/figures/llm_critic_review_queue.md` adds a lightweight review order for the next critic-style pass. This still does not claim repaired output. In fact, its current value is partly diagnostic: the queue makes it obvious that swapped-profile uncertainty still appears broadly, so the frontier remains more about exposing a failure mode than demonstrating a solved agent loop.

That first-pass queue now also has an explicit evidence slot: `results/figures/llm_critic_review_receipt.md` defines the template-only writeback target for the first critic-style review pass. This still does not claim that any qualitative repair loop has worked. What it adds is a cleaner handoff boundary, because the next contributor no longer has to invent the first receipt format before recording what the review actually found.

It now also includes a first `external_validation` bridge: `results/figures/external_validation_candidates.md` plus a small candidate table covering AISHELL-4, AliMeeting, AMI, and LibriCSS. This is explicitly labeled `external/sanity-check`: it records source, license, fit, preprocessing, and next-action notes so future agents can move toward a narrow external mini validation without overstating the current evidence.

That bridge is now one step more actionable: `results/figures/external_validation_prioritization.md` adds a lightweight execution order across the same candidates and currently recommends AISHELL-4 as the first tiny sanity-check target. This still does not claim that any external benchmark has been run; it simply reduces the next contributor's decision surface before data staging begins.

That recommendation is now also easier to pick up without extra interpretation: `results/figures/external_validation_slice_handoff.md` compresses the next external step into a one-row first-slice packet. This still does not claim any external benchmark execution. Its value is narrower and operational: it names the first slice shape, the license gate, the mapping artifact, and the dry-run goal before any external data is actually staged.

That first-slice packet now also has an explicit evidence slot: `results/figures/external_validation_slice_receipt.md` defines the template-only writeback target for the first narrow external sanity-check. This still does not claim that any external slice has been executed. What it adds is a clearer handoff boundary, because the next contributor no longer has to invent the first receipt format before recording what happened.

The external-mini-validation frontier now also has a dedicated skill card: `docs/skills/skill_07_external_validation.md`. That makes the queue head pickable from the skills index instead of only from the roadmap and project-state layers, which is a small but useful improvement in how the frontier work is surfaced.

It now also includes a first `demo_excellence` bridge: `results/figures/demo_storyboard.md` plus a small JSON card set. This is intentionally light-weight rather than a full demo app, but it already improves onboarding by giving a one-page story that connects the problem, pipeline, main findings, and frontier extensions.

That demo bridge is now also easier to present live: `results/figures/demo_walkthrough.md` adds a short ordered talk track anchored to existing artifacts. This is still presentation support rather than a new benchmark layer, but it makes the demo frontier more executable without forcing a UI build first.

That walkthrough now also has an explicit evidence slot: `results/figures/demo_walkthrough_receipt.md` defines the template-only writeback target for the first presentation pass. This still does not claim that any live demo or recording has been completed. What it adds is a cleaner handoff boundary, because the next contributor no longer has to invent the first demo receipt format before recording what the walkthrough actually covered.

## 9. Conclusion

This project establishes a stable experimental baseline and opens a path toward more ambitious agentic ASR systems. Mixed ASR is safer under light overlap, separated ASR is stronger under heavier overlap, and duplicate suppression can reduce repetition without fully solving separated hallucinations. Router_v2 matches the oracle-best average CER on the gold benchmark, while synthetic validation and risk-aware selection help explain where the system remains fragile and where further exploration may be most valuable. The newer compute-aware frontier work adds a practical decision layer on top: it shows that `router_v2` is the cleanest balanced default, `fixed_mixed_whisper` is the most stable cost-first option, and `fixed_separated_whisper_cleaned` remains a strong robustness-oriented accuracy choice when cross-dataset stability matters.
