# Presenter Runbook — 8 Minutes

Replay Demo — all outputs are precomputed from committed research artifacts.

## Presenter A — Research Narrative (0:00–3:20)

- 0:00–0:35: State the question: when should we separate, keep mixed audio, or escalate?
- 0:35–1:15: Show Overview and the system map. Say this is a team demo, not an AudioDepth-only demo.
- 1:15–2:00: Explain that always-separate fails: LightOverlap/MidOverlap prefer mixed, while NoOverlap/Heavy/Opposite prefer separated.
- 2:00–2:45: Say router v2 average CER is 0.120 on the five-case gold benchmark, matching oracle without CER input.
- 2:45–3:20: Introduce the separation-tax mechanism: low-overlap harm is a heavy hallucination tail, not uniform degradation.

Presenter A does not operate the mouse.

## Presenter B — Demo Operator and System Extensions (3:20–7:10)

1. Open Core Routing.
2. Select Mixed-win.
3. Play the short LightOverlap audio.
4. Point at the reference, mixed transcript, the raw-separated artifact notice, and the cleaned separated transcript. Do not imply the missing LightOverlap raw separated transcript is being reconstructed.
5. Switch to Separated-win: the NoOverlap control separated-win case.
6. Play the NoOverlap audio and explain it is the control separated-win case because main includes complete raw transcript artifacts. Add that HeavyOverlap and OppositeOverlap also favor separated ASR in the gold CER table.
7. Open Separation Tax and point to leading silence, repetition loop, and confident attractor.
8. Open Team Frontiers and summarize learned router, Mode B cascade, emotion/LLM, and AudioDepth.

Presenter B owns mouse and audio. Do not switch terminals, install dependencies, or change Git branches during the talk.

## Presenter A — Conclusion (7:10–8:00)

- Evidence levels: stable/gold, synthetic/silver, experimental/frontier, qualitative/demo, branch-only exploratory.
- Limitations: small five-case gold benchmark, oracle separation, synthetic/silver frontier references, branch-specific model-scale and AudioDepth results, replay demo not live inference.
- Final conclusion: No single fixed route dominates across all evaluated conditions; boundary-aware and objective-aware routing is the contribution.

Detailed individual contributions are documented in the authoritative contribution record.

## Fixed Click Path

Overview → Core Routing: Mixed-win → Core Routing: Separated-win → Separation Tax → Routing + Evaluation → Team Frontiers → Evidence

Keep total clicks under 8.
