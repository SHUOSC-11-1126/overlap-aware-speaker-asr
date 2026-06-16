# Plan: Frontier Execution Queue Milestone Bridge Checklist

1. Add a focused failing unit test for the milestone bridge checklist row builder.
2. Extend the execution queue handoff packet coverage so it expects the new bridge section.
3. Implement `src/frontier_execution_queue_milestone_bridge_checklist.py` using the existing milestone card JSON only.
4. Refresh the execution queue handoff packet so it includes the new milestone bridge section.
5. Emit CSV, JSON, and Markdown outputs for the new bridge checklist and refreshed packet under `results/`.
6. Update `.gitignore`, `README.md`, `docs/project_state.md`, and `docs/roadmap.md`.
7. Run focused unit tests around the new bridge checklist and adjacent execution queue artifacts.
8. Commit docs/plan first, then commit the feature and push both commits to `main`.
