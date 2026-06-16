# Plan: Frontier Execution Queue Phase Checkpoint Card

1. Add a focused unit test for the execution queue phase checkpoint card row builder.
2. Implement `src/frontier_execution_queue_phase_checkpoint_card.py` using the existing execution queue runbook card JSON only.
3. Extend the execution queue handoff packet so it includes the new checkpoint card section.
4. Emit CSV, JSON, and Markdown outputs for the checkpoint card and refreshed packet under `results/`.
5. Update `.gitignore`, `README.md`, `docs/project_state.md`, and `docs/roadmap.md`.
6. Run focused unit tests around the checkpoint card, runbook bridge, runbook card, operator brief, packet, and handoff stack.
7. Commit docs/plan first, then commit the feature and push both commits to `main`.
