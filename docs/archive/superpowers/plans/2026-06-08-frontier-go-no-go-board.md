# Frontier Go-No-Go Board Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one unified board that shows which frontier tracks are ready for a narrow next action and which are still blocked.

**Architecture:** Read the existing frontier-specific summary artifacts, normalize them into per-frontier go/no-go rows, then emit one top-level board plus one summary card. Keep the logic isolated in a new generator and cover the classification rules with unit tests.

**Tech Stack:** Python, CSV/JSON/Markdown artifact generation, `unittest`

---

### Task 1: Add failing tests for decision logic

**Files:**
- Create: `tests/test_frontier_go_no_go_board.py`
- Test: `tests/test_frontier_go_no_go_board.py`

- [ ] **Step 1: Write the failing test**

```python
from src.frontier_go_no_go_board import (
    classify_go_no_go_state,
    build_summary_row,
)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_frontier_go_no_go_board -v`
Expected: FAIL with missing module or symbol error.

- [ ] **Step 3: Write minimal implementation**

```python
def classify_go_no_go_state(...):
    ...

def build_summary_row(...):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_frontier_go_no_go_board -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_frontier_go_no_go_board.py src/frontier_go_no_go_board.py
git commit -m "feat: add frontier go-no-go board"
```

### Task 2: Generate unified frontier artifacts

**Files:**
- Create: `src/frontier_go_no_go_board.py`
- Create: `results/tables/frontier_go_no_go_board.csv`
- Create: `results/tables/frontier_go_no_go_board.json`
- Create: `results/tables/frontier_go_no_go_summary.csv`
- Create: `results/tables/frontier_go_no_go_summary.json`
- Create: `results/figures/frontier_go_no_go_board.md`
- Create: `results/figures/frontier_go_no_go_summary.md`

- [ ] **Step 1: Implement board generator**

```python
def build_frontier_rows(...):
    ...

def write_outputs(...):
    ...
```

- [ ] **Step 2: Run generator**

Run: `python3 -m src.frontier_go_no_go_board`
Expected: writes board and summary artifacts under `results/`

- [ ] **Step 3: Inspect generated summary**

Run: `sed -n '1,120p' results/figures/frontier_go_no_go_summary.md`
Expected: shows ready count, blocked count, and operator focus in documented queue order.

- [ ] **Step 4: Commit**

```bash
git add src/frontier_go_no_go_board.py results/tables/frontier_go_no_go_* results/figures/frontier_go_no_go_*.md
git commit -m "feat: publish frontier go-no-go board"
```

### Task 3: Document the new coordination evidence

**Files:**
- Modify: `README.md`
- Modify: `docs/project_state.md`
- Modify: `docs/roadmap.md`

- [ ] **Step 1: Add concise references**

```md
- board path
- which frontier is blocked
- which ready frontier should be focused next
```

- [ ] **Step 2: Run focused verification**

Run: `python3 -m unittest tests.test_frontier_go_no_go_board tests.test_frontier_execution_queue_status tests.test_frontier_execution_queue_completion_summary -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add README.md docs/project_state.md docs/roadmap.md
git commit -m "docs: record frontier go-no-go board"
```
