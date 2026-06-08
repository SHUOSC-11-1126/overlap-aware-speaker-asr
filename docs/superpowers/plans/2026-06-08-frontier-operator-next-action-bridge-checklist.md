# Frontier Operator Next-Action Bridge Checklist Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one bridge checklist that converts the top-level frontier operator card into an ordered verification path before opening each target artifact.

**Architecture:** Read the generated operator card rows, normalize them into checklist rows that preserve lane order, and emit one bridge checklist in CSV/JSON/Markdown.

**Tech Stack:** Python, CSV/JSON/Markdown artifact generation, `unittest`

---

### Task 1: Add failing tests for bridge row mapping

**Files:**
- Create: `tests/test_frontier_operator_next_action_bridge_checklist.py`

- [ ] **Step 1: Write the failing test**

```python
from src.frontier_operator_next_action_bridge_checklist import build_bridge_checklist_rows
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_bridge_checklist -v`
Expected: FAIL with missing module or symbol error.

- [ ] **Step 3: Write minimal implementation**

```python
def build_bridge_checklist_rows(...):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_bridge_checklist -v`
Expected: PASS

### Task 2: Generate operator bridge checklist artifacts

**Files:**
- Create: `src/frontier_operator_next_action_bridge_checklist.py`
- Create: `results/tables/frontier_operator_next_action_bridge_checklist.csv`
- Create: `results/tables/frontier_operator_next_action_bridge_checklist.json`
- Create: `results/figures/frontier_operator_next_action_bridge_checklist.md`

- [ ] **Step 1: Implement generator**
- [ ] **Step 2: Run generator**

Run: `python3 -m src.frontier_operator_next_action_bridge_checklist`
Expected: writes operator bridge checklist artifacts under `results/`

- [ ] **Step 3: Inspect generated checklist**

Run: `sed -n '1,120p' results/figures/frontier_operator_next_action_bridge_checklist.md`
Expected: shows `ready_lane` first and `blocked_lane` second with the same target artifacts as the operator card.

### Task 3: Document the bridge layer

**Files:**
- Modify: `.gitignore`
- Modify: `README.md`
- Modify: `docs/project_state.md`
- Modify: `docs/roadmap.md`

- [ ] **Step 1: Add artifact allowlist and concise references**
- [ ] **Step 2: Run focused verification**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_bridge_checklist tests.test_frontier_operator_next_action_card tests.test_frontier_execution_queue_handoff_bridge_checklist -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add .gitignore tests/test_frontier_operator_next_action_bridge_checklist.py src/frontier_operator_next_action_bridge_checklist.py \
  results/tables/frontier_operator_next_action_bridge_checklist.* results/figures/frontier_operator_next_action_bridge_checklist.md \
  README.md docs/project_state.md docs/roadmap.md
git commit -m "feat: add frontier operator next-action bridge checklist"
```
