# 10 Minute Demo Runbook

## Feasibility on This Machine

The current system Python is `3.14` and lacks the project scientific/ASR dependencies (`PyYAML`, `numpy`, `scipy`, `soundfile`, `matplotlib`, Whisper-compatible ASR). A live ASR rerun is therefore not the reliable demo path on this machine.

The recommended demo is a static GitHub-online evidence deck:

```bash
python3 -m scripts.build_static_demo
open demo/index.html
```

It rebuilds the HTML from the online GitHub `main` branch: README, `CONTRIBUTIONS.md`, implementation status, results index, contributor API, and raw GitHub figures. It does not call Whisper, NumPy, or Streamlit.

## Whole-project Demo Rule

This is a complete project demo, not an AudioDepth-only demo. The talk should cover:

- data preparation, audio splitting, and Whisper-style baselines;
- mixed / separated / cleaned transcript routes;
- adaptive router v1/v2 and risk-aware route selection;
- CER, speaker-aware CER, cpCER-lite, and error-type analysis;
- synthetic robustness and held-out split validation;
- compute-aware cascade and deployment profiles;
- MeetEval/cpWER, speaker-profile, LLM critic/RAG, external-validation, demo-excellence, and AudioDepth tracks as research frontiers with explicit claim boundaries.

If a teammate's research track cannot be rerun on this laptop, present it through its committed evidence artifact instead of hiding it. Use the rule:

| Layer | Use in demo | Examples |
| --- | --- | --- |
| live | Only for zero-dependency interactions | `demo/index.html`, local audio playback, route-choice quiz |
| artifact | Default for dependency-heavy work | committed CSV tables, generated figures, `REPORT.md`, `results/figures/*.md` |
| boundary | Always say what is not proven live | no live Whisper rerun, no production claim, no unverified repair claim |

## 10 Minute Arc

| Time | Demo beat | Action |
| ---: | --- | --- |
| 0:00-1:00 | Whole-project hook | Present the complete pipeline: data, separation, ASR, cleaning, routing, evaluation, frontier work. |
| 1:00-2:20 | Contribution map and ledger | Show the six contribution lanes from `CONTRIBUTIONS.md`; make it clear this is team work. |
| 2:20-3:00 | Team highlights | Emphasize Whisper/separation baseline, router_v2, evaluation, synthetic validation, LLM/RAG, and demo/visualization. |
| 3:00-4:00 | Listen and guess | Play one or two gold audio clips in the route challenge. |
| 4:00-4:45 | Stable result | Show router_v2 vs fixed routes on the five-case gold benchmark. |
| 4:45-5:30 | Evaluation contribution | Show why CER, speaker-aware CER, cpCER-lite, and error-type analysis matter. |
| 5:30-6:10 | Router lesson | Show why separation is a route decision, not a universal rule. |
| 6:10-6:50 | Frontier breadth | Cover compute-aware cascade, MeetEval/cpWER, speaker profile, LLM critic/RAG, external validation, and demo excellence. |
| 6:50-7:45 | AudioDepth attempt | Show RGB-D style acoustic-depth maps as one exploratory branch, not the central team claim. |
| 7:45-9:15 | Evidence hygiene | Show risk guard, source-disjoint audit, unified eval, and micro-gold prep. |
| 9:15-10:00 | Honest close | Repeat claim boundary: stable narrow gold result, complete project workflow, next micro-gold step. |

## Fun Interaction

Use the second slide as a mini-game:

1. Play a clip.
2. Ask the audience to vote: keep mixed, separate, clean, or review.
3. Click the answer.
4. Emphasize that the surprising cases are LightOverlap and MidOverlap, where separation can hurt.

## Speaker Notes

- The stable win is narrow: five manually verified gold cases.
- The team highlights are the full pipeline, router_v2, evaluation stack, synthetic/held-out validation, and evidence discipline.
- AudioDepth is a visually useful attempt, not the mainline claim.
- The strongest narrative is honesty: the project finds both wins and failure modes.
- The next serious proof is micro-gold annotation, not more decorative modeling.

## Fallback

If audio playback fails in a browser, skip the audio player and use the same slide as a route-choice quiz. The visual and table evidence still works offline.

If a research track cannot be rerun locally, say: "This part is not being recomputed live on this laptop; the committed artifact is the evidence surface." Then show the linked artifact and continue. This is safer than attempting a slow model download or a dependency install during a 10 minute demo.
