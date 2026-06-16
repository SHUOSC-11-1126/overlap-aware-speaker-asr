# LLM Critic Review Receipt Plan

## Goal

Extend the `llm_critic` coordination line with a template-only review receipt so the next contributor has an explicit evidence writeback target before any critic-style review loop is claimed to work.

## Why This Next

The repository already has:

- a qualitative critic note
- a critic review queue

Those layers now describe which case should be reviewed first, but they do not yet provide the concrete evidence slot that a future critic-style pass should fill. Adding a receipt template keeps the work breadth-first because:

- it closes a coordination gap without pretending any verified repair has happened
- it defines the minimal writeback schema before a review pass is attempted
- it reduces ambiguity around what the first critic-style follow-up should record

## Proposed Outputs

- `results/tables/llm_critic_review_receipt.json`
- `results/figures/llm_critic_review_receipt.md`

## Scope

- derive one receipt template row from the current review queue head
- record execution status, review scope, expected inputs, expected outputs, and writeback note
- keep the artifact explicitly marked as template-only / not-yet-executed
- avoid claiming any actual transcript repair success

## Verification

- add unit tests for receipt row construction
- add unit tests for markdown rendering
- run `python3 -m src.llm_correct`
- run `python3 -m unittest tests.test_llm_critic_qualitative tests.test_project_harness -v`
