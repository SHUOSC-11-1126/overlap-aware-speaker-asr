# Benchmark Blocker Matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a benchmark blocker matrix artifact that consolidates blocker type, execution priority, dependency state, and missing-field scale for each benchmark step.

**Architecture:** Keep the status board, execution queue, and dependency graph as the source layers, then derive a blocker matrix by joining those rows on `plan_step_id`. Render both a table and markdown note so contributors can judge urgency and blockage without hopping across multiple handoff artifacts.

**Tech Stack:** Python, `unittest`, CSV/JSON/Markdown artifact generation

---

### Task 1: Add blocker-matrix failing tests

**Files:**
- Modify: `tests/test_compute_aware_cascade.py`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_benchmark_blocker_matrix_rows_join_status_queue_and_dependency(self) -> None:
    rows = build_benchmark_blocker_matrix_rows(
        [{"plan_step_id": "phase1_gold_runtime_foundation"}],
        [{"plan_step_id": "phase1_gold_runtime_foundation"}],
        [{"plan_step_id": "phase1_gold_runtime_foundation"}],
    )
    self.assertEqual(rows[0]["plan_step_id"], "phase1_gold_runtime_foundation")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_blocker_matrix_rows_join_status_queue_and_dependency -v`
Expected: FAIL with `ImportError` or `NameError` because `build_benchmark_blocker_matrix_rows` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
def build_benchmark_blocker_matrix_rows(
    status_rows: list[dict[str, Any]],
    queue_rows: list[dict[str, Any]],
    dependency_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_blocker_matrix_rows_join_status_queue_and_dependency -v`
Expected: PASS after the real join logic is implemented.

- [ ] **Step 5: Commit**

```bash
git add tests/test_compute_aware_cascade.py src/compute_aware_cascade.py
git commit -m "feat: summarize cascade benchmark blocker matrix"
```

### Task 2: Wire blocker matrix outputs into artifacts and packet

**Files:**
- Modify: `src/compute_aware_cascade.py`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_benchmark_packet_lines_include_blocker_matrix(self) -> None:
    lines = build_benchmark_packet_lines([], [], [], [], [], [], [], [], [], [
        {"plan_step_id": "phase1_gold_runtime_foundation"}
    ])
    self.assertIn("## Blocker Matrix", "\n".join(lines))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_packet_lines_include_blocker_matrix -v`
Expected: FAIL because the handoff packet does not render the blocker matrix section yet.

- [ ] **Step 3: Write minimal implementation**

```python
lines.extend(["", "## Blocker Matrix", ""])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_packet_lines_include_blocker_matrix -v`
Expected: PASS with the blocker matrix section present.

- [ ] **Step 5: Commit**

```bash
git add src/compute_aware_cascade.py tests/test_compute_aware_cascade.py
git commit -m "feat: add cascade benchmark blocker matrix outputs"
```

### Task 3: Refresh generated artifacts and docs

**Files:**
- Modify: `README.md`
- Modify: `docs/project_state.md`
- Modify: `docs/roadmap.md`
- Modify: `REPORT.md`
- Modify: `results/figures/cascade_benchmark_handoff_packet.md`
- Create: `results/figures/cascade_benchmark_blocker_matrix.md`
- Create: `results/tables/cascade_benchmark_blocker_matrix.csv`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Rebuild generated outputs**

Run: `python3 -m src.compute_aware_cascade --dataset synthetic_split`
Expected: Writes the new benchmark blocker matrix artifacts and refreshed packet output.

- [ ] **Step 2: Run focused verification**

Run: `python3 -m unittest tests.test_compute_aware_cascade tests.test_project_harness -v`
Expected: PASS with the new blocker-matrix coverage included.

- [ ] **Step 3: Update docs**

```markdown
- `results/figures/cascade_benchmark_blocker_matrix.md` now shows blocker type, queue priority, dependency state, and pending-field scale in one place.
```

- [ ] **Step 4: Commit**

```bash
git add README.md docs/project_state.md docs/roadmap.md REPORT.md results/figures/cascade_benchmark_blocker_matrix.md results/figures/cascade_benchmark_handoff_packet.md results/tables/cascade_benchmark_blocker_matrix.csv
git commit -m "docs: publish cascade benchmark blocker matrix"
```
