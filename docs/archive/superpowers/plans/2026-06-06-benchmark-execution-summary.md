# Benchmark Execution Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a benchmark execution summary layer that condenses the status board into execution-ready blocker totals, phase readiness, and next-action guidance for the compute-aware cascade handoff stack.

**Architecture:** Keep the existing benchmark status board as the per-step source of truth, then derive a compact summary table and markdown note from those rows. Wire the summary into the handoff packet so contributors can start from one high-level view before drilling into individual steps.

**Tech Stack:** Python, `unittest`, CSV/JSON/Markdown artifact generation

---

### Task 1: Add summary-focused failing tests

**Files:**
- Modify: `tests/test_compute_aware_cascade.py`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_benchmark_execution_summary_rows_aggregates_blockers(self) -> None:
    rows = build_benchmark_execution_summary_rows([
        {
            "phase": "foundation",
            "blocking_category": "runtime_capture_missing",
            "execution_status": "template_only",
            "pending_field_count": 6,
            "next_action": "collect_controlled_runtime",
        }
    ])
    self.assertEqual(rows[0]["phase"], "foundation")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_execution_summary_rows_aggregates_blockers -v`
Expected: FAIL with `ImportError` or `NameError` because `build_benchmark_execution_summary_rows` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
def build_benchmark_execution_summary_rows(status_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_execution_summary_rows_aggregates_blockers -v`
Expected: PASS after the real aggregation logic is implemented.

- [ ] **Step 5: Commit**

```bash
git add tests/test_compute_aware_cascade.py src/compute_aware_cascade.py
git commit -m "feat: summarize cascade benchmark execution status"
```

### Task 2: Wire summary outputs into artifact generation

**Files:**
- Modify: `src/compute_aware_cascade.py`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_benchmark_packet_lines_include_execution_summary(self) -> None:
    lines = build_benchmark_packet_lines([], [], [], [], [], [
        {"phase": "foundation", "blocking_category": "runtime_capture_missing"}
    ])
    self.assertIn("## Execution Summary", "\n".join(lines))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_packet_lines_include_execution_summary -v`
Expected: FAIL because the handoff packet does not render the new section yet.

- [ ] **Step 3: Write minimal implementation**

```python
lines.extend(["", "## Execution Summary", ""])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_packet_lines_include_execution_summary -v`
Expected: PASS with the summary section present.

- [ ] **Step 5: Commit**

```bash
git add src/compute_aware_cascade.py tests/test_compute_aware_cascade.py
git commit -m "feat: add cascade benchmark execution summary outputs"
```

### Task 3: Refresh generated artifacts and docs

**Files:**
- Modify: `README.md`
- Modify: `docs/project_state.md`
- Modify: `docs/roadmap.md`
- Modify: `REPORT.md`
- Modify: `results/figures/cascade_benchmark_handoff_packet.md`
- Create: `results/figures/cascade_benchmark_execution_summary.md`
- Create: `results/tables/cascade_benchmark_execution_summary.csv`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Rebuild generated outputs**

Run: `python3 -m src.compute_aware_cascade`
Expected: Writes the new benchmark execution summary artifacts and refreshed packet output.

- [ ] **Step 2: Run focused verification**

Run: `python3 -m unittest tests.test_compute_aware_cascade tests.test_project_harness -v`
Expected: PASS with the new execution summary coverage included.

- [ ] **Step 3: Update docs**

```markdown
- `results/figures/cascade_benchmark_execution_summary.md` now gives the top-level blocker totals and next-action guidance before the step-by-step board.
```

- [ ] **Step 4: Commit**

```bash
git add README.md docs/project_state.md docs/roadmap.md REPORT.md results/figures/cascade_benchmark_execution_summary.md results/figures/cascade_benchmark_handoff_packet.md results/tables/cascade_benchmark_execution_summary.csv
git commit -m "docs: publish cascade benchmark execution summary"
```
