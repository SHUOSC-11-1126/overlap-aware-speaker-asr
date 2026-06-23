# Demo Recording Plan: 7 Minute Project Demo + 3 Minute GitHub Walkthrough

## Goal

Produce a 10 minute group-friendly demo video:

- first 7 minutes: polished project story using the offline static deck;
- final 3 minutes: GitHub repository/workspace walkthrough;
- voiceover can be recorded by different teammates after the visual recording is ready.

The visual recording should not depend on live Whisper, model downloads, Streamlit, NumPy, or network access.

## Recommended Recording Shape

| Segment | Duration | Visual | Voiceover owner |
| --- | ---: | --- | --- |
| Project hook and team map | 0:00-1:20 | `demo/index.html`, slides 1-2 | baseline/data + project lead |
| Route challenge | 1:20-2:20 | route-choice mini-game, one audio clip | routing/evaluation speaker |
| Stable result | 2:20-3:10 | gold result card | router speaker |
| Evaluation contribution | 3:10-4:10 | CER/error/speaker-aware metrics | metric speaker |
| Router lesson | 4:10-4:50 | best route by case | router speaker |
| Frontier breadth | 4:50-5:40 | compute, MeetEval, speaker-profile, LLM critic, demo excellence | each teammate can claim one sentence |
| AudioDepth attempt | 5:40-6:25 | AudioDepth maps and risk gate | wfzark or frontier speaker |
| Evidence hygiene close | 6:25-7:00 | source-disjoint, unified eval, micro-gold | reviewer/evidence speaker |
| GitHub README walkthrough | 7:00-8:00 | repository README top, figures, links | project lead |
| Docs/results structure | 8:00-9:00 | `docs/`, `results/figures/`, `results/tables/` | documentation/results speaker |
| Contribution and reproducibility | 9:00-10:00 | `CONTRIBUTIONS.md`, quick-start commands, demo runbook | final speaker |

## Recording URL

Run:

```bash
python3 -m scripts.build_static_demo
python3 -m http.server 8765
```

Open:

```text
http://127.0.0.1:8765/demo/index.html?autoplay=1&seconds=420
```

This auto-advances the deck over 7 minutes. Use the normal URL for manual practice:

```text
http://127.0.0.1:8765/demo/index.html
```

Use the local HTTP URL rather than `file://` for recording. It makes browser media loading and full-size artifact links more predictable.

## Readability Rules

The demo deck is designed for projection and video capture:

- every dense figure has a large-text slide or readable table nearby;
- key numbers are repeated as HTML metrics instead of relying only on image text;
- architecture flow is repeated as a six-step large-text pipeline;
- critical figures are clickable so the presenter can open the full-size artifact if a projector makes text too small;
- avoid zooming rapidly during recording; open full-size figures only when a number is genuinely hard to see.

## GitHub Walkthrough Targets

Use these repository surfaces in the final 3 minutes:

1. `README.md`
   - title and final architecture image;
   - Stable vs Frontier table;
   - Quick Start commands;
   - Where To Read More.
2. `REPORT.md`
   - final research narrative;
   - dataset/method/results sections;
   - limitations and next steps.
3. `CONTRIBUTIONS.md`
   - team contribution table;
   - mention that the demo intentionally treats AudioDepth as one attempt, not the central team proof.
4. `docs/demo_10min_runbook.md`
   - evidence/artifact/fallback rule for dependency-heavy tracks.
5. `results/figures/` and `results/tables/`
   - generated artifacts show reproducibility and audit trail.

## Voiceover Guidance

Keep the tone confident but not overclaiming:

- "The stable result is router_v2 on a five-case manually verified gold benchmark."
- "The project contribution is the whole workflow: data, separation, ASR, cleaning, routing, evaluation, robustness checks, and frontier audits."
- "Some frontier tracks are scaffolds or diagnostics. We show them because they make the next work clearer, not because they are production claims."
- "AudioDepth is an exploratory acoustic-triage attempt. It is visually useful and scientifically interesting, but the team baseline comes first."
- "If something cannot rerun live on this laptop, the committed artifact is the evidence surface."

## If Direct Screen Recording Works

macOS provides `screencapture` video mode:

```bash
screencapture -v -V 600 -g -k demo_recording.mov
```

This may require Screen Recording and microphone permissions. If permission prompts appear, use QuickTime or the built-in Screenshot app instead, while keeping the same URL and timeline.

## If We Split Recording And Dubbing

1. Record visuals without microphone.
2. Each teammate records their assigned 30-60 second voice segment.
3. Combine in any video editor.
4. Keep the final 3 minute GitHub walkthrough as live narration if editing time is short.
