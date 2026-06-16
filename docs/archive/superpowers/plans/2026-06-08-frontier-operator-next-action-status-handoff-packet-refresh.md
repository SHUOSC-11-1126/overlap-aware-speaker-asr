# Plan: Frontier Operator Next-Action Status Handoff Packet Refresh

1. Update the focused packet unit test first so it expects the refreshed section list.
2. Extend `src/frontier_operator_next_action_status_handoff_packet.py` to include the new `status` and `status` bridge checklist layers.
3. Regenerate CSV, JSON, and Markdown packet outputs under `results/`.
4. Update `README.md`, `docs/project_state.md`, and `docs/roadmap.md` to describe the refreshed packet shape.
5. Run focused unit tests around the refreshed packet and adjacent `status/handoff` artifacts.
6. Commit docs/plan first, then commit the feature and push both commits to `main`.
