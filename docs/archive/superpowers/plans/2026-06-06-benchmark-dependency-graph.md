# Benchmark Dependency Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a benchmark dependency graph artifact that makes the execution dependencies between benchmark steps explicit inside the compute-aware cascade handoff stack.

**Architecture:** Keep the benchmark plan as the source of step ordering, then derive dependency edges and blocker explanations by combining plan rows with the execution queue. Render the result as both a table and a markdown note so contributors can see which step unlocks which later step without reconstructing the chain manually.

**Tech Stack:** Python, `unittest`, CSV/JSON/Markdown artifact generation

---

### Task 1: Add dependency-graph failing tests

**Files:**
- Modify: `tests/test_compute_aware_cascade.py`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_benchmark_dependency_graph_rows_connect_predecessors(self) -> None:
    rows = build_benchmark_dependency_graph_rows(
        [{"plan_step_id": "phase1_gold_runtime_foundation", "step_order": 1}],
        [{"plan_step_id": "phase1_gold_runtime_foundation", "queue_rank": 1}],
    )
    self.assertEqual(rows[0]["plan_step_id"], "phase1_gold_runtime_foundation")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_dependency_graph_rows_connect_predecessors -v`
Expected: FAIL with `ImportError` or `NameError` because `build_benchmark_dependency_graph_rows` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
def build_benchmark_dependency_graph_rows(plan_rows: list[dict[str, Any]], queue_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_dependency_graph_rows_connect_predecessors -v`
Expected: PASS after the real dependency logic is implemented.

- [ ] **Step 5: Commit**

```bash
git add tests/test_compute_aware_cascade.py src/compute_aware_cascade.py
git commit -m "feat: map cascade benchmark dependencies"
```

### Task 2: Wire dependency graph outputs into artifacts and packet

**Files:**
- Modify: `src/compute_aware_cascade.py`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_benchmark_packet_lines_include_dependency_graph(self) -> None:
    lines = build_benchmark_packet_lines([], [], [], [], [], [], [], [], [
        {"plan_step_id": "phase1_gold_runtime_foundation"}
    ])
    self.assertIn("## Dependency Graph", "\n".join(lines))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_packet_lines_include_dependency_graph -v`
Expected: FAIL because the handoff packet does not render the dependency graph section yet.

- [ ] **Step 3: Write minimal implementation**

```python
lines.extend(["", "## Dependency Graph", ""])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_packet_lines_include_dependency_graph -v`
Expected: PASS with the dependency graph section present.

- [ ] **Step 5: Commit**

```bash
git add src/compute_aware_cascade.py tests/test_compute_aware_cascade.py
git commit -m "feat: add cascade benchmark dependency graph outputs"
```

### Task 3: Refresh generated artifacts and docs

**Files:**
- Modify: `README.md`
- Modify: `docs/project_state.md`
- Modify: `docs/roadmap.md`
- Modify: `REPORT.md`
- Modify: `results/figures/cascade_benchmark_handoff_packet.md`
- Create: `results/figures/cascade_benchmark_dependency_graph.md`
- Create: `results/tables/cascade_benchmark_dependency_graph.csv`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Rebuild generated outputs**

Run: `python3 -m src.compute_aware_cascade --dataset synthetic_split`
Expected: Writes the new benchmark dependency graph artifacts and refreshed packet output.

- [ ] **Step 2: Run focused verification**

Run: `python3 -m unittest tests.test_compute_aware_cascade tests.test_project_harness -v`
Expected: PASS with the new dependency-graph coverage included.

- [ ] **Step 3: Update docs**

```markdown
- `results/figures/cascade_benchmark_dependency_graph.md` now shows which benchmark step unlocks which downstream step.
```

- [ ] **Step 4: Commit**

```bash
git add README.md docs/project_state.md docs/roadmap.md REPORT.md results/figures/cascade_benchmark_dependency_graph.md results/figures/cascade_benchmark_handoff_packet.md results/tables/cascade_benchmark_dependency_graph.csv
git commit -m "docs: publish cascade benchmark dependency graph"
```
