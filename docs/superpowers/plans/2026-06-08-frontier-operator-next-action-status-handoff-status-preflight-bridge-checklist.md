# Plan: Frontier Operator Next-Action Status Handoff Status Preflight Bridge Checklist

1. Add a focused unit test for the status preflight bridge checklist row builder.
2. Implement `src/frontier_operator_next_action_status_handoff_status_preflight_bridge_checklist.py` using the existing completion-dashboard bridge checklist JSON only.
3. Extend the top-level packet section list so it includes the new preflight layer before the status rollup.
4. Emit CSV, JSON, and Markdown outputs for the new checklist and refresh the packet artifacts under `results/`.
5. Update `.gitignore`, `README.md`, `docs/project_state.md`, and `docs/roadmap.md`.
6. Run focused unit tests around the new checklist, status rollup, status bridge checklist, dashboard bridge checklist, and packet chain.
7. Commit docs/plan first, then commit the feature and push both commits to `main`.
