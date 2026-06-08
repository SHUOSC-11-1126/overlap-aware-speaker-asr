# Frontier Operator Next-Action Frontier Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one bridge artifact that reconnects the top-level operator runbook card to the broader frontier board focus.

**Architecture:** Read the runbook card and the top-level go/no-go summary, compare the recommended frontier with the highest-priority ready frontier, and emit one compact bridge row in CSV/JSON/Markdown.

**Tech Stack:** Python, CSV/JSON/Markdown artifact generation, `unittest`

---

### Task 1: Add failing tests for bridge row mapping

**Files:**
- Create: `tests/test_frontier_operator_next_action_frontier_bridge.py`

- [ ] **Step 1: Write the failing test**

```python
from src.frontier_operator_next_action_frontier_bridge import build_frontier_bridge_row
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_frontier_bridge -v`
Expected: FAIL with missing module or symbol error.

- [ ] **Step 3: Write minimal implementation**

```python
def build_frontier_bridge_row(...):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_frontier_bridge -v`
Expected: PASS

### Task 2: Generate frontier bridge artifacts

**Files:**
- Create: `src/frontier_operator_next_action_frontier_bridge.py`
- Create: `results/tables/frontier_operator_next_action_frontier_bridge.csv`
- Create: `results/tables/frontier_operator_next_action_frontier_bridge.json`
- Create: `results/figures/frontier_operator_next_action_frontier_bridge.md`

- [ ] **Step 1: Implement generator**
- [ ] **Step 2: Run generator**

Run: `python3 -m src.frontier_operator_next_action_frontier_bridge`
Expected: writes frontier bridge artifacts under `results/`

- [ ] **Step 3: Inspect generated bridge**

Run: `sed -n '1,120p' results/figures/frontier_operator_next_action_frontier_bridge.md`
Expected: shows `meeteval_compatibility` aligned with the broader frontier queue head.

### Task 3: Document the frontier bridge layer

**Files:**
- Modify: `.gitignore`
- Modify: `README.md`
- Modify: `docs/project_state.md`
- Modify: `docs/roadmap.md`

- [ ] **Step 1: Add artifact allowlist and concise references**
- [ ] **Step 2: Run focused verification**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_frontier_bridge tests.test_frontier_operator_next_action_runbook_card tests.test_frontier_operator_next_action_operator_brief -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add .gitignore tests/test_frontier_operator_next_action_frontier_bridge.py src/frontier_operator_next_action_frontier_bridge.py \
  results/tables/frontier_operator_next_action_frontier_bridge.* results/figures/frontier_operator_next_action_frontier_bridge.md \
  README.md docs/project_state.md docs/roadmap.md
git commit -m "feat: add frontier operator next-action frontier bridge"
```
