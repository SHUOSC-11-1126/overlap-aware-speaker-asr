# Plan: Frontier Operator Next-Action Status Handoff Packet Full Refresh

1. Update the focused packet unit test first so it expects the full current section list.
2. Extend `src/frontier_operator_next_action_status_handoff_packet.py` to include the missing `status/handoff` artifact layers.
3. Regenerate CSV, JSON, and Markdown packet outputs under `results/`.
4. Update `README.md`, `docs/project_state.md`, and `docs/roadmap.md` to describe the refreshed packet scope.
5. Run focused unit tests around the refreshed packet and adjacent `status/handoff` artifacts.
6. Commit docs/plan first, then commit the feature and push both commits to `main`.
