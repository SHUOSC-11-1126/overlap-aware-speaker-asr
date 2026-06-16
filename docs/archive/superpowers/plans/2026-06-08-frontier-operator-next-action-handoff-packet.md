# Frontier Operator Next-Action Handoff Packet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one single-entry handoff packet that consolidates the new top-level operator coordination chain.

**Architecture:** Define the ordered top-level operator artifact list, emit packet rows in CSV/JSON/Markdown, and include a short first-open sequence in the markdown note.

**Tech Stack:** Python, CSV/JSON/Markdown artifact generation, `unittest`

---

### Task 1: Add failing tests for packet row coverage

**Files:**
- Create: `tests/test_frontier_operator_next_action_handoff_packet.py`

- [ ] **Step 1: Write the failing test**

```python
from src.frontier_operator_next_action_handoff_packet import build_handoff_packet_rows
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_handoff_packet -v`
Expected: FAIL with missing module or symbol error.

- [ ] **Step 3: Write minimal implementation**

```python
def build_handoff_packet_rows(...):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_handoff_packet -v`
Expected: PASS

### Task 2: Generate handoff packet artifacts

**Files:**
- Create: `src/frontier_operator_next_action_handoff_packet.py`
- Create: `results/tables/frontier_operator_next_action_handoff_packet.csv`
- Create: `results/tables/frontier_operator_next_action_handoff_packet.json`
- Create: `results/figures/frontier_operator_next_action_handoff_packet.md`

- [ ] **Step 1: Implement generator**
- [ ] **Step 2: Run generator**

Run: `python3 -m src.frontier_operator_next_action_handoff_packet`
Expected: writes handoff packet artifacts under `results/`

- [ ] **Step 3: Inspect generated packet**

Run: `sed -n '1,160p' results/figures/frontier_operator_next_action_handoff_packet.md`
Expected: lists the operator artifacts in order and gives a short first-open sequence.

### Task 3: Document the handoff packet layer

**Files:**
- Modify: `.gitignore`
- Modify: `README.md`
- Modify: `docs/project_state.md`
- Modify: `docs/roadmap.md`

- [ ] **Step 1: Add artifact allowlist and concise references**
- [ ] **Step 2: Run focused verification**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_handoff_packet tests.test_frontier_operator_next_action_frontier_bridge_checklist tests.test_frontier_operator_next_action_frontier_bridge -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add .gitignore tests/test_frontier_operator_next_action_handoff_packet.py src/frontier_operator_next_action_handoff_packet.py \
  results/tables/frontier_operator_next_action_handoff_packet.* results/figures/frontier_operator_next_action_handoff_packet.md \
  README.md docs/project_state.md docs/roadmap.md
git commit -m "feat: add frontier operator next-action handoff packet"
```
