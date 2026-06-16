# Plan: Frontier Execution Queue Status Reentry Card

1. Add a focused failing unit test for the status reentry card row builder.
2. Extend the execution queue handoff packet coverage so it expects the new reentry card section.
3. Implement `src/frontier_execution_queue_status_reentry_card.py` using the existing status preflight bridge JSON and status JSON only.
4. Refresh the execution queue handoff packet so it includes the new status reentry card section.
5. Emit CSV, JSON, and Markdown outputs for the new card and refreshed packet under `results/`.
6. Update `.gitignore`, `README.md`, `docs/project_state.md`, and `docs/roadmap.md`.
7. Run focused unit tests around the new reentry card and adjacent execution queue artifacts.
8. Commit docs/plan first, then commit the feature and push both commits to `main`.
