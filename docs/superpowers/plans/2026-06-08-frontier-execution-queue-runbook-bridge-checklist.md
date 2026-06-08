# Plan: Frontier Execution Queue Runbook Bridge Checklist

1. Add a focused unit test for the execution queue runbook bridge checklist row builder.
2. Implement `src/frontier_execution_queue_runbook_bridge_checklist.py` using the existing execution queue runbook card JSON only.
3. Extend the execution queue handoff packet so it includes the new bridge layer.
4. Emit CSV, JSON, and Markdown outputs for the bridge checklist and refreshed packet under `results/`.
5. Update `.gitignore`, `README.md`, `docs/project_state.md`, and `docs/roadmap.md`.
6. Run focused unit tests around the runbook bridge, runbook card, operator brief, packet, and handoff stack.
7. Commit docs/plan first, then commit the feature and push both commits to `main`.
