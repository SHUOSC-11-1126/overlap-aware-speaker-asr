# Plan: Frontier Operator Next-Action Status Handoff Operator Brief Bridge Checklist

1. Add a focused failing unit test for the bridge checklist row builder.
2. Implement `src/frontier_operator_next_action_status_handoff_operator_brief_bridge_checklist.py` using the existing operator brief bridge JSON only.
3. Emit CSV, JSON, and Markdown outputs under `results/`.
4. Update `.gitignore`, `README.md`, `docs/project_state.md`, and `docs/roadmap.md`.
5. Run focused unit tests around the new checklist and adjacent `status/handoff` artifacts.
6. Commit docs/plan first, then commit the feature and push both commits to `main`.
