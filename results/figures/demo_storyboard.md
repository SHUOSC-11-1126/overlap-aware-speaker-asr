# Demo Storyboard

This generated storyboard is a demo-facing summary of the repository's core story and current frontier extensions.

```mermaid
flowchart LR
    A["Mixed / Separated Audio"] --> B["ASR Paths"]
    B --> C["Router + Risk Selector"]
    C --> D["Speaker-aware / cpCER-lite Evaluation"]
    D --> E["Frontier Extensions"]
```

## Problem

Overlap-aware ASR should separate selectively instead of assuming separation always helps.

## Pipeline

Mixed ASR, separated ASR, duplicate suppression, adaptive routing, and speaker-aware evaluation form the main decision loop.

## Findings

Selective separation beats blind separation in the current gold benchmark. router_v2 is the balanced default, while cleaned separated output is the robust fallback.

## Frontier

Breadth-first artifacts now cover compute-aware cascade, MeetEval compatibility, speaker profile risk signaling, qualitative critics, and external prioritization.

