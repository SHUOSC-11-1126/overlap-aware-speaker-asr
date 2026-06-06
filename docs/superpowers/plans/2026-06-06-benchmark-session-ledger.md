# Benchmark Session Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a benchmark session ledger artifact that connects the execution queue to the manifest template and spells out what evidence each pending benchmark step must leave behind.

**Architecture:** Keep the status board, execution summary, and execution queue as derived scheduling layers, then derive a ledger from queue plus manifest template rows. The ledger should expose the ordered step, evidence anchor, metadata footprint, and completion note so a contributor can move from “what runs next” to “what must be recorded” without opening multiple files.

**Tech Stack:** Python, `unittest`, CSV/JSON/Markdown artifact generation

---

### Task 1: Add ledger-focused failing tests

**Files:**
- Modify: `tests/test_compute_aware_cascade.py`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_benchmark_session_ledger_rows_join_queue_and_manifest(self) -> None:
    rows = build_benchmark_session_ledger_rows(
        [{"queue_rank": 1, "plan_step_id": "phase1_gold_runtime_foundation"}],
        [{"plan_step_id": "phase1_gold_runtime_foundation", "hardware_label": "TODO"}],
    )
    self.assertEqual(rows[0]["plan_step_id"], "phase1_gold_runtime_foundation")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_session_ledger_rows_join_queue_and_manifest -v`
Expected: FAIL with `ImportError` or `NameError` because `build_benchmark_session_ledger_rows` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
def build_benchmark_session_ledger_rows(queue_rows: list[dict[str, Any]], manifest_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_session_ledger_rows_join_queue_and_manifest -v`
Expected: PASS after the real join logic is implemented.

- [ ] **Step 5: Commit**

```bash
git add tests/test_compute_aware_cascade.py src/compute_aware_cascade.py
git commit -m "feat: derive cascade benchmark session ledger"
```

### Task 2: Wire ledger outputs into artifacts and packet

**Files:**
- Modify: `src/compute_aware_cascade.py`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_benchmark_packet_lines_include_session_ledger(self) -> None:
    lines = build_benchmark_packet_lines([], [], [], [], [], [], [], [
        {"queue_rank": 1, "plan_step_id": "phase1_gold_runtime_foundation"}
    ])
    self.assertIn("## Session Ledger", "\n".join(lines))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_packet_lines_include_session_ledger -v`
Expected: FAIL because the handoff packet does not render the ledger yet.

- [ ] **Step 3: Write minimal implementation**

```python
lines.extend(["", "## Session Ledger", ""])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_packet_lines_include_session_ledger -v`
Expected: PASS with the new ledger section present.

- [ ] **Step 5: Commit**

```bash
git add src/compute_aware_cascade.py tests/test_compute_aware_cascade.py
git commit -m "feat: add cascade benchmark session ledger outputs"
```

### Task 3: Refresh generated artifacts and docs

**Files:**
- Modify: `README.md`
- Modify: `docs/project_state.md`
- Modify: `docs/roadmap.md`
- Modify: `REPORT.md`
- Modify: `results/figures/cascade_benchmark_handoff_packet.md`
- Create: `results/figures/cascade_benchmark_session_ledger.md`
- Create: `results/tables/cascade_benchmark_session_ledger.csv`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Rebuild generated outputs**

Run: `python3 -m src.compute_aware_cascade --dataset synthetic_split`
Expected: Writes the new benchmark session ledger artifacts and refreshed packet output.

- [ ] **Step 2: Run focused verification**

Run: `python3 -m unittest tests.test_compute_aware_cascade tests.test_project_harness -v`
Expected: PASS with the new ledger coverage included.

- [ ] **Step 3: Update docs**

```markdown
- `results/figures/cascade_benchmark_session_ledger.md` now tells contributors which evidence anchor and metadata footprint each queued benchmark step must leave behind.
```

- [ ] **Step 4: Commit**

```bash
git add README.md docs/project_state.md docs/roadmap.md REPORT.md results/figures/cascade_benchmark_session_ledger.md results/figures/cascade_benchmark_handoff_packet.md results/tables/cascade_benchmark_session_ledger.csv
git commit -m "docs: publish cascade benchmark session ledger"
```
