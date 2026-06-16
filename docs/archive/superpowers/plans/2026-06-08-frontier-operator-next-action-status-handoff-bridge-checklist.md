# Plan: Frontier Operator Next-Action Status Handoff Bridge Checklist

1. Add a focused failing unit test for the handoff bridge checklist row builder.
2. Implement `src/frontier_operator_next_action_status_handoff_bridge_checklist.py` using the existing status handoff JSON only.
3. Emit CSV, JSON, and Markdown outputs under `results/`.
4. Update `.gitignore`, `README.md`, `docs/project_state.md`, and `docs/roadmap.md`.
5. Run focused unit tests around the new bridge and adjacent top-level operator handoff artifacts.
6. Commit docs/plan first, then commit the feature and push both commits to `main`.
