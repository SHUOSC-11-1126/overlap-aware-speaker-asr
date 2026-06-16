# Benchmark Execution Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a benchmark execution queue artifact that turns the benchmark status stack into an ordered next-run list for the compute-aware cascade handoff workflow.

**Architecture:** Keep the benchmark status board as the step-level source of truth and the execution summary as the phase-level rollup, then derive a queue that sorts pending work by phase order, blocker type, and pending-field weight. Surface the queue in the handoff packet so the next contributor can start from an execution order rather than reconstructing one manually.

**Tech Stack:** Python, `unittest`, CSV/JSON/Markdown artifact generation

---

### Task 1: Add queue-focused failing tests

**Files:**
- Modify: `tests/test_compute_aware_cascade.py`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_benchmark_execution_queue_rows_prioritize_pending_steps(self) -> None:
    rows = build_benchmark_execution_queue_rows([
        {
            "plan_step_id": "phase1_gold_runtime_foundation",
            "phase": "foundation",
            "pending_field_count": 6,
            "blocking_category": "runtime_capture_missing",
        }
    ])
    self.assertEqual(rows[0]["plan_step_id"], "phase1_gold_runtime_foundation")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_execution_queue_rows_prioritize_pending_steps -v`
Expected: FAIL with `ImportError` or `NameError` because `build_benchmark_execution_queue_rows` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
def build_benchmark_execution_queue_rows(status_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_execution_queue_rows_prioritize_pending_steps -v`
Expected: PASS after the real queue logic is implemented.

- [ ] **Step 5: Commit**

```bash
git add tests/test_compute_aware_cascade.py src/compute_aware_cascade.py
git commit -m "feat: prioritize cascade benchmark execution queue"
```

### Task 2: Wire queue outputs into artifacts and packet

**Files:**
- Modify: `src/compute_aware_cascade.py`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_benchmark_packet_lines_include_execution_queue(self) -> None:
    lines = build_benchmark_packet_lines([], [], [], [], [], [], [
        {"queue_rank": 1, "plan_step_id": "phase1_gold_runtime_foundation"}
    ])
    self.assertIn("## Execution Queue", "\n".join(lines))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_packet_lines_include_execution_queue -v`
Expected: FAIL because the handoff packet does not render the queue yet.

- [ ] **Step 3: Write minimal implementation**

```python
lines.extend(["", "## Execution Queue", ""])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_packet_lines_include_execution_queue -v`
Expected: PASS with the new queue section present.

- [ ] **Step 5: Commit**

```bash
git add src/compute_aware_cascade.py tests/test_compute_aware_cascade.py
git commit -m "feat: add cascade benchmark execution queue outputs"
```

### Task 3: Refresh generated artifacts and docs

**Files:**
- Modify: `README.md`
- Modify: `docs/project_state.md`
- Modify: `docs/roadmap.md`
- Modify: `REPORT.md`
- Modify: `results/figures/cascade_benchmark_handoff_packet.md`
- Create: `results/figures/cascade_benchmark_execution_queue.md`
- Create: `results/tables/cascade_benchmark_execution_queue.csv`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Rebuild generated outputs**

Run: `python3 -m src.compute_aware_cascade --dataset synthetic_split`
Expected: Writes the new benchmark execution queue artifacts and refreshed packet output.

- [ ] **Step 2: Run focused verification**

Run: `python3 -m unittest tests.test_compute_aware_cascade tests.test_project_harness -v`
Expected: PASS with the new queue coverage included.

- [ ] **Step 3: Update docs**

```markdown
- `results/figures/cascade_benchmark_execution_queue.md` now gives the ordered next-run list before contributors dive into the lower-level status board.
```

- [ ] **Step 4: Commit**

```bash
git add README.md docs/project_state.md docs/roadmap.md REPORT.md results/figures/cascade_benchmark_execution_queue.md results/figures/cascade_benchmark_handoff_packet.md results/tables/cascade_benchmark_execution_queue.csv
git commit -m "docs: publish cascade benchmark execution queue"
```
