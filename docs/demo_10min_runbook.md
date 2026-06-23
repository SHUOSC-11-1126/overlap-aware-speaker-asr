# 10 Minute Demo Runbook

## Feasibility on This Machine

The current system Python is `3.14` and lacks the project scientific/ASR dependencies (`PyYAML`, `numpy`, `scipy`, `soundfile`, `matplotlib`, Whisper-compatible ASR). A live ASR rerun is therefore not the reliable demo path on this machine.

The recommended demo has two stable local surfaces:

```bash
python3 -m scripts.build_asr_effect_demo
python3 -m scripts.build_static_demo
python3 -m scripts.run_live_results_demo
open demo/asr_effect.html
open demo/index.html
```

`demo/asr_effect.html` is the direct teacher-facing ASR demo. It plays the local mixed audio and shows the verified reference transcript, mixed Whisper output, separated-speaker output when stored locally, cleaned separated output, and CER/error counts loaded from committed result tables. It does not rerun Whisper live; it visualizes the saved experiment artifacts so the presentation stays reliable.

`demo/index.html` is the whole-project GitHub-online evidence deck. It rebuilds the HTML from the online GitHub `main` branch: README, `CONTRIBUTIONS.md`, implementation status, results index, contributor API, and raw GitHub figures. It does not call Whisper, NumPy, or Streamlit.

For live result calculation, run `python3 -m scripts.run_live_results_demo`. This recomputes gold CER averages, best-by-case routing, error-type counts, speaker-aware CER, and synthetic silver averages from committed CSV tables. It does not rerun Whisper or LLM models, so it is safe for a short presentation.

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
| 3:00-4:20 | Listen and read | Open `demo/asr_effect.html`; play LightOverlap and HeavyOverlap, then compare reference vs recognized text. |
| 4:20-5:00 | Stable result | Run `python3 -m scripts.run_live_results_demo` and show router_v2/oracle-style best-by-case results from CSV. |
| 4:45-5:30 | Evaluation contribution | Show why CER, speaker-aware CER, cpCER-lite, and error-type analysis matter. |
| 5:30-6:10 | Router lesson | Show why separation is a route decision, not a universal rule. |
| 6:10-6:50 | Frontier breadth | Cover compute-aware cascade, MeetEval/cpWER, speaker profile, LLM critic/RAG, external validation, and demo excellence. |
| 6:50-7:45 | AudioDepth attempt | Show RGB-D style acoustic-depth maps as one exploratory branch, not the central team claim. |
| 7:45-9:15 | Evidence hygiene | Show risk guard, source-disjoint audit, unified eval, and micro-gold prep. |
| 9:15-10:00 | Honest close | Repeat claim boundary: stable narrow gold result, complete project workflow, next micro-gold step. |

## Fun Interaction

Use `demo/asr_effect.html` as a mini-game:

1. Play a clip.
2. Ask the audience to vote: keep mixed, separate, clean, or review.
3. Click the answer.
4. Emphasize that LightOverlap is the surprising failure case where separation hurts, while HeavyOverlap and OppositeOverlap are the intuitive success cases where separation helps.

## Speaker Notes

- The stable win is narrow: five manually verified gold cases.
- The team highlights are the full pipeline, router_v2, evaluation stack, synthetic/held-out validation, and evidence discipline.
- AudioDepth is a visually useful attempt, not the mainline claim.
- The strongest narrative is honesty: the project finds both wins and failure modes.
- The next serious proof is micro-gold annotation, not more decorative modeling.

## Fallback

If audio playback fails in a browser, skip the audio player and use the transcript columns as a route-choice quiz. The reference text, ASR output, and CER table evidence still works offline.

If a research track cannot be rerun locally, say: "This part is not being recomputed live on this laptop; the committed artifact is the evidence surface." Then show the linked artifact and continue. This is safer than attempting a slow model download or a dependency install during a 10 minute demo.
