# Plan: Frontier Execution Queue Milestone Card

1. Add a focused unit test for the execution queue milestone card row builder.
2. Implement `src/frontier_execution_queue_milestone_card.py` using the existing execution queue completion summary and handoff JSON only.
3. Extend the execution queue handoff packet so it includes the new milestone card section.
4. Emit CSV, JSON, and Markdown outputs for the milestone card and refreshed packet under `results/`.
5. Update `.gitignore`, `README.md`, `docs/project_state.md`, and `docs/roadmap.md`.
6. Run focused unit tests around the milestone card, phase checkpoint, runbook bridge, runbook card, operator brief, packet, and handoff stack.
7. Commit docs/plan first, then commit the feature and push both commits to `main`.
