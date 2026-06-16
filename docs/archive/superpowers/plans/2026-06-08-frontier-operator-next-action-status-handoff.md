# Plan: Frontier Operator Next-Action Status Handoff

1. Add a focused failing unit test for the new top-level handoff row builder.
2. Implement `src/frontier_operator_next_action_status_handoff.py` using existing status and card JSON artifacts only.
3. Emit CSV, JSON, and Markdown outputs under `results/`.
4. Update `.gitignore`, `README.md`, `docs/project_state.md`, and `docs/roadmap.md`.
5. Run focused unit tests around the new handoff and adjacent operator status artifacts.
6. Commit docs/plan first, then commit the feature and push both commits to `main`.
