# Frontier Operator Next-Action Handoff Packet Design

## Goal

Add one single-entry handoff packet that consolidates the new top-level operator coordination chain.

## Why This Increment

The repository now has a full top-level operator chain:

- operator card
- bridge checklist
- operator brief
- runbook card
- frontier bridge
- frontier bridge checklist

What is still missing is the one-page entrypoint that lists these artifacts in order and gives the next contributor a clear first-open sequence.

## Scope

In scope:

- one new generator under `src/`
- one focused test file
- one handoff packet artifact in CSV/JSON/Markdown
- small doc updates referencing the packet

Out of scope:

- changing frontier priority
- changing any bridge logic
- executing frontier work
- claiming frontier completion

## Inputs

This packet can be built from the known artifact paths already defined by the top-level operator chain.

## Output Shape

Per-row fields should include:

- `packet_section`
- `artifact_path`
- `section_role`

## Decision Rules

- Preserve a sensible top-down order from operator card to frontier bridge checklist.
- Include the runbook card and both bridge checklists.
- Add a short recommended-first-action section in markdown that points to the current ready frontier.
- Keep all wording coordination-only and boundary-preserving.

## Verification

- unit tests should confirm that the packet includes the operator brief and runbook card
- unit tests should confirm that the frontier bridge checklist is present
- run the generator locally and inspect the markdown packet

## Labeling

Mark the output as experimental/frontier coordination only. The packet should reduce navigation cost, not imply that any frontier action has already been executed.
