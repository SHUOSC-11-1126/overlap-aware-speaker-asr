# Frontier Operator Next-Action Operator Brief Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one plain-language operator brief that summarizes the top-level frontier ready lane, blocked lane, and evidence path.

**Architecture:** Read the generated operator card and summary, select the ready and blocked rows, then emit one compact operator brief row in CSV/JSON/Markdown.

**Tech Stack:** Python, CSV/JSON/Markdown artifact generation, `unittest`

---

### Task 1: Add failing tests for operator brief mapping

**Files:**
- Create: `tests/test_frontier_operator_next_action_operator_brief.py`

- [ ] **Step 1: Write the failing test**

```python
from src.frontier_operator_next_action_operator_brief import build_operator_brief_row
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_operator_brief -v`
Expected: FAIL with missing module or symbol error.

- [ ] **Step 3: Write minimal implementation**

```python
def build_operator_brief_row(...):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_operator_brief -v`
Expected: PASS

### Task 2: Generate operator brief artifacts

**Files:**
- Create: `src/frontier_operator_next_action_operator_brief.py`
- Create: `results/tables/frontier_operator_next_action_operator_brief.csv`
- Create: `results/tables/frontier_operator_next_action_operator_brief.json`
- Create: `results/figures/frontier_operator_next_action_operator_brief.md`

- [ ] **Step 1: Implement generator**
- [ ] **Step 2: Run generator**

Run: `python3 -m src.frontier_operator_next_action_operator_brief`
Expected: writes operator brief artifacts under `results/`

- [ ] **Step 3: Inspect generated brief**

Run: `sed -n '1,120p' results/figures/frontier_operator_next_action_operator_brief.md`
Expected: clearly shows the ready lane, blocked lane, and evidence path in plain language.

### Task 3: Document the operator brief layer

**Files:**
- Modify: `.gitignore`
- Modify: `README.md`
- Modify: `docs/project_state.md`
- Modify: `docs/roadmap.md`

- [ ] **Step 1: Add artifact allowlist and concise references**
- [ ] **Step 2: Run focused verification**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_operator_brief tests.test_frontier_operator_next_action_bridge_checklist tests.test_frontier_operator_next_action_card -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add .gitignore tests/test_frontier_operator_next_action_operator_brief.py src/frontier_operator_next_action_operator_brief.py \
  results/tables/frontier_operator_next_action_operator_brief.* results/figures/frontier_operator_next_action_operator_brief.md \
  README.md docs/project_state.md docs/roadmap.md
git commit -m "feat: add frontier operator next-action operator brief"
```
