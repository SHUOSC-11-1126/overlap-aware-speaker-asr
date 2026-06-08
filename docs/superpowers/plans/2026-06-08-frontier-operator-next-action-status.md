# Plan: Frontier Operator Next-Action Status

1. Add a focused unit test that defines the desired mixed-ready and fallback status behavior.
2. Implement `src/frontier_operator_next_action_status.py` by reading existing coordination JSON artifacts only.
3. Emit CSV, JSON, and Markdown outputs under `results/`.
4. Update `.gitignore`, `README.md`, `docs/project_state.md`, and `docs/roadmap.md`.
5. Run focused unit tests for the new status artifact and adjacent operator-chain artifacts.
6. Commit docs/plan first, then commit the feature and push both commits to `main`.
