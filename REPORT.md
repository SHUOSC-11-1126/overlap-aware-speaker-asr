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

The compute-aware line is now beyond a placeholder idea: the immediate next step is a controlled hardware/runtime benchmark that can replace repository-local runtime comparisons with stronger deployment evidence. The repository now includes a generated benchmark-readiness scaffold, a staged benchmark handoff plan, a profile playbook, a benchmark checklist, a benchmark manifest template, a benchmark status board, a benchmark execution summary, a benchmark execution queue, a benchmark session ledger, a benchmark dependency graph, a benchmark blocker matrix, a benchmark runbook card, a benchmark milestone card, a benchmark phase checkpoint card, a benchmark completion dashboard, a benchmark operator brief, a benchmark evidence receipt, and a benchmark handoff packet, so the next contributor can see which artifacts matter first, what order to refresh them in, how the resulting profile choices should be interpreted, which run metadata must be captured during execution, where to record that metadata, which phases are still template-only, which blocker category each pending phase belongs to, which phase should move next, which exact benchmark step should run first, what evidence each step must leave behind, which step unlocks the next one, how urgent each blocker is, what the first one-page execution brief should say, where the next milestone boundary sits, how each phase should be checked off, what the top-level pending state looks like, which single plain-language operator note should be read first, which writeback receipt should be checked before closing the run, and which single note to start from before touching the lower-level files. After that, the most interesting future work will still be the work that clarifies a boundary, exposes a failure mode, or tests an idea that is intentionally a little risky.

That benchmark coordination stack is now also linked back to the broader frontier workflow: `results/figures/cascade_benchmark_frontier_bridge.md` connects the current benchmark operator step to the newer breadth-first frontier queue. This does not add any new measurement result. Its value is organizational: it shows why the controlled runtime foundation still deserves priority even while several narrower frontier handoffs are now ready in parallel.

To support a broader next phase, the harness now also exposes a generated breadth-first frontier status table in `results/figures/project_harness_report.md`. That table does not claim new experimental results; it simply makes the current evidence path, expected output, and next step visible for `speaker_profile`, `meeteval_compatibility`, `llm_critic`, `external_validation`, and `demo_excellence`, which makes it easier for future agents to spread effort across multiple frontiers instead of deepening only one line at a time.

That coordination layer is now also more executable: `results/figures/frontier_execution_queue.md` adds a lightweight breadth-first queue across the same frontiers. This is not new model evidence. Its value is organizational: it turns the growing set of frontier handoff cards into one short ordered list so the next contributor can choose the first breadth-first move with less friction.

That queue is now also easier to scan at a glance: `results/figures/frontier_focus_card.md` compresses the current queue head into a one-card starting point. This is still purely coordination support, but it reduces the time from opening the repository to seeing the current breadth-first priority.

That queue head is now also easier to hand off without file-hopping: `results/figures/frontier_handoff_packet.md` points the current frontier directly at its next artifact and expected evidence target. This still adds no new research claim. It is a tiny coordination convenience, but one that makes the breadth-first workflow more executable for the next contributor.

That breadth-first push now also includes a first concrete `meeteval_compatibility` bridge: `results/figures/meeteval_compatibility_note.md` plus JSONL exports for verified reference segments and speaker-attributed hypothesis segments. This is intentionally framed as a compatibility scaffold rather than a completed MeetEval / cpWER result, but it turns that frontier from a pure idea into a reusable artifact.

That bridge is now also easier to hand off: `results/figures/meeteval_readiness.md` adds a narrow dry-run readiness card. It still does not claim that MeetEval has been executed. Instead, it makes the current state more honest and more usable at the same time by showing that the export is ready for a diagnostic next step while also exposing that cleaned fallback still dominates the current hypothesis mix.

That handoff is now one step more executable: `results/figures/meeteval_dry_run_handoff.md` compresses the next action into a single-row packet with a recommended first slice, a primary blocker, and an expected evidence file. This still does not claim any completed MeetEval or cpWER run. Its value is narrower and more practical: it reduces the ambiguity around what the first diagnostic follow-up should actually look like.

That expected evidence file now also exists as a template: `results/figures/meeteval_dry_run_receipt.md` defines the narrow run scope, expected inputs, expected outputs, and post-run writeback note for the first diagnostic pass. This still stops well short of claiming that any dry run has happened. What it adds is a cleaner handoff boundary: the next contributor no longer has to infer what the first evidence writeback should contain.

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

It now also includes a first `demo_excellence` bridge: `results/figures/demo_storyboard.md` plus a small JSON card set. This is intentionally light-weight rather than a full demo app, but it already improves onboarding by giving a one-page story that connects the problem, pipeline, main findings, and frontier extensions.

That demo bridge is now also easier to present live: `results/figures/demo_walkthrough.md` adds a short ordered talk track anchored to existing artifacts. This is still presentation support rather than a new benchmark layer, but it makes the demo frontier more executable without forcing a UI build first.

That walkthrough now also has an explicit evidence slot: `results/figures/demo_walkthrough_receipt.md` defines the template-only writeback target for the first presentation pass. This still does not claim that any live demo or recording has been completed. What it adds is a cleaner handoff boundary, because the next contributor no longer has to invent the first demo receipt format before recording what the walkthrough actually covered.

## 9. Conclusion

This project establishes a stable experimental baseline and opens a path toward more ambitious agentic ASR systems. Mixed ASR is safer under light overlap, separated ASR is stronger under heavier overlap, and duplicate suppression can reduce repetition without fully solving separated hallucinations. Router_v2 matches the oracle-best average CER on the gold benchmark, while synthetic validation and risk-aware selection help explain where the system remains fragile and where further exploration may be most valuable. The newer compute-aware frontier work adds a practical decision layer on top: it shows that `router_v2` is the cleanest balanced default, `fixed_mixed_whisper` is the most stable cost-first option, and `fixed_separated_whisper_cleaned` remains a strong robustness-oriented accuracy choice when cross-dataset stability matters.
