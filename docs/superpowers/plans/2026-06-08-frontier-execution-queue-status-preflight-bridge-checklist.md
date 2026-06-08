# Plan: Frontier Execution Queue Status Preflight Bridge Checklist

1. Add a focused failing unit test for the status preflight bridge checklist row builder.
2. Extend the execution queue handoff packet coverage so it expects the new status preflight bridge section.
3. Implement `src/frontier_execution_queue_status_preflight_bridge_checklist.py` using the existing completion dashboard bridge JSON only.
4. Refresh the execution queue handoff packet so it includes the new status preflight bridge section.
5. Emit CSV, JSON, and Markdown outputs for the new bridge checklist and refreshed packet under `results/`.
6. Update `.gitignore`, `README.md`, `docs/project_state.md`, and `docs/roadmap.md`.
7. Run focused unit tests around the new bridge checklist and adjacent execution queue artifacts.
8. Commit docs/plan first, then commit the feature and push both commits to `main`.
