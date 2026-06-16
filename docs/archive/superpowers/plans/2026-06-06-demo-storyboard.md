# Demo Storyboard Plan

## Goal

Add a lightweight `demo_excellence` artifact that turns the current repository state into a one-page demo storyboard.

## Why This Next

This direction broadens the project again without requiring a full UI. The repository already has enough evidence to support a compact demo-facing story:

- stable baseline findings
- compute-aware cascade figures and summaries
- breadth-first frontier artifacts

What is missing is a single generated note that a new visitor can read quickly to understand:

- the problem
- the core pipeline
- the most important findings
- the current frontier directions

## Proposed Outputs

- `results/tables/demo_storyboard_cards.json`
- `results/figures/demo_storyboard.md`

## Scope

- generate short storyboard cards, not a full app
- include a simple Mermaid pipeline diagram
- keep the output aligned with the research narrative
- avoid decorative content with no explanatory value

## Verification

- add unit tests for storyboard card construction
- add unit tests for markdown rendering
- run `python3 -m src.demo_storyboard`
- run `python3 -m unittest tests.test_demo_storyboard tests.test_llm_critic_qualitative tests.test_speaker_profile_similarity tests.test_export_meeteval_compatibility tests.test_project_harness tests.test_compute_aware_cascade -v`
