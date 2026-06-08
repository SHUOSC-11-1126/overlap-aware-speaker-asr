# Demo Go-No-Go Board Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a small decision board that shows what the demo-excellence chain is ready for, and what remains blocked from any live-delivery claim.

**Architecture:** Read the existing storyboard/walkthrough receipt and review-status artifacts, normalize them into per-checkpoint go/no-go rows, then emit one board plus one summary card. Keep all logic isolated in one new generator and cover the status mapping with unit tests.

**Tech Stack:** Python, CSV/JSON/Markdown artifact generation, `unittest`

---

### Task 1: Add failing tests for decision logic

**Files:**
- Create: `tests/test_demo_go_no_go_board.py`
- Test: `tests/test_demo_go_no_go_board.py`

- [ ] **Step 1: Write the failing test**

```python
from src.demo_go_no_go_board import (
    classify_go_no_go_state,
    build_summary_row,
)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_demo_go_no_go_board -v`
Expected: FAIL with missing module or symbol error.

- [ ] **Step 3: Write minimal implementation**

```python
def classify_go_no_go_state(...):
    ...

def build_summary_row(...):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_demo_go_no_go_board -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_demo_go_no_go_board.py src/demo_go_no_go_board.py
git commit -m "feat: add demo go-no-go board"
```

### Task 2: Generate go-no-go artifacts

**Files:**
- Create: `src/demo_go_no_go_board.py`
- Create: `results/tables/demo_go_no_go_board.csv`
- Create: `results/tables/demo_go_no_go_board.json`
- Create: `results/tables/demo_go_no_go_summary.csv`
- Create: `results/tables/demo_go_no_go_summary.json`
- Create: `results/figures/demo_go_no_go_board.md`
- Create: `results/figures/demo_go_no_go_summary.md`

- [ ] **Step 1: Implement board generator**

```python
def build_checkpoint_rows(...):
    ...

def write_outputs(...):
    ...
```

- [ ] **Step 2: Run generator**

Run: `python3 -m src.demo_go_no_go_board`
Expected: writes board and summary artifacts under `results/`

- [ ] **Step 3: Inspect generated summary**

Run: `sed -n '1,120p' results/figures/demo_go_no_go_summary.md`
Expected: distinguishes presentation writeback readiness from blocked live-delivery claims.

- [ ] **Step 4: Commit**

```bash
git add src/demo_go_no_go_board.py results/tables/demo_go_no_go_* results/figures/demo_go_no_go_*.md
git commit -m "feat: publish demo go-no-go board"
```

### Task 3: Document the new frontier evidence

**Files:**
- Modify: `README.md`
- Modify: `docs/project_state.md`
- Modify: `docs/roadmap.md`

- [ ] **Step 1: Add concise references**

```md
- board path
- what is ready
- what claim boundary remains blocked
```

- [ ] **Step 2: Run focused verification**

Run: `python3 -m unittest tests.test_demo_go_no_go_board tests.test_demo_walkthrough_review_pass_completion_summary tests.test_demo_storyboard_review_pass_status -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add README.md docs/project_state.md docs/roadmap.md
git commit -m "docs: record demo go-no-go board"
```
