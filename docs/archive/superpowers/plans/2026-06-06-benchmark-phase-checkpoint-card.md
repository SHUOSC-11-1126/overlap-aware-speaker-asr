# Benchmark Phase Checkpoint Card Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a benchmark phase checkpoint card artifact that summarizes per-phase entry condition, current blocker, and completion signal.

**Architecture:** Keep the execution summary and benchmark plan as the source layers, then derive a small checkpoint card per phase. Each row should say what phase it is, what currently blocks it, and what signal marks that phase done. Publish it as both a small CSV and a markdown note so contributors can sanity-check phase readiness without reading the full packet.

**Tech Stack:** Python, `unittest`, CSV/JSON/Markdown artifact generation

---

### Task 1: Add checkpoint-card failing tests

**Files:**
- Modify: `tests/test_compute_aware_cascade.py`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_benchmark_phase_checkpoint_card_rows_pair_summary_with_plan(self) -> None:
    rows = build_benchmark_phase_checkpoint_card_rows(
        [{"phase": "foundation"}],
        [{"phase": "foundation"}],
    )
    self.assertEqual(rows[0]["phase"], "foundation")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_phase_checkpoint_card_rows_pair_summary_with_plan -v`
Expected: FAIL with `ImportError` or `NameError` because `build_benchmark_phase_checkpoint_card_rows` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
def build_benchmark_phase_checkpoint_card_rows(
    summary_rows: list[dict[str, Any]],
    plan_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_phase_checkpoint_card_rows_pair_summary_with_plan -v`
Expected: PASS after the real checkpoint logic is implemented.

- [ ] **Step 5: Commit**

```bash
git add tests/test_compute_aware_cascade.py src/compute_aware_cascade.py
git commit -m "feat: summarize cascade benchmark phase checkpoints"
```

### Task 2: Wire checkpoint-card outputs into artifacts and packet

**Files:**
- Modify: `src/compute_aware_cascade.py`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_benchmark_packet_lines_include_phase_checkpoint_card(self) -> None:
    lines = build_benchmark_packet_lines([], [], [], [], [], [], [], [], [], [], [], [], [
        {"phase": "foundation"}
    ])
    self.assertIn("## Phase Checkpoint Card", "\n".join(lines))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_packet_lines_include_phase_checkpoint_card -v`
Expected: FAIL because the handoff packet does not render the phase checkpoint section yet.

- [ ] **Step 3: Write minimal implementation**

```python
lines.extend(["", "## Phase Checkpoint Card", ""])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_packet_lines_include_phase_checkpoint_card -v`
Expected: PASS with the phase checkpoint section present.

- [ ] **Step 5: Commit**

```bash
git add src/compute_aware_cascade.py tests/test_compute_aware_cascade.py
git commit -m "feat: add cascade benchmark phase checkpoint outputs"
```

### Task 3: Refresh generated artifacts and docs

**Files:**
- Modify: `README.md`
- Modify: `docs/project_state.md`
- Modify: `docs/roadmap.md`
- Modify: `REPORT.md`
- Modify: `results/figures/cascade_benchmark_handoff_packet.md`
- Create: `results/figures/cascade_benchmark_phase_checkpoint_card.md`
- Create: `results/tables/cascade_benchmark_phase_checkpoint_card.csv`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Rebuild generated outputs**

Run: `python3 -m src.compute_aware_cascade --dataset synthetic_split`
Expected: Writes the new benchmark phase checkpoint artifacts and refreshed packet output.

- [ ] **Step 2: Run focused verification**

Run: `python3 -m unittest tests.test_compute_aware_cascade tests.test_project_harness -v`
Expected: PASS with the new phase-checkpoint coverage included.

- [ ] **Step 3: Update docs**

```markdown
- `results/figures/cascade_benchmark_phase_checkpoint_card.md` now shows each phase's blocker and completion signal in one short card.
```

- [ ] **Step 4: Commit**

```bash
git add README.md docs/project_state.md docs/roadmap.md REPORT.md results/figures/cascade_benchmark_phase_checkpoint_card.md results/figures/cascade_benchmark_handoff_packet.md results/tables/cascade_benchmark_phase_checkpoint_card.csv
git commit -m "docs: publish cascade benchmark phase checkpoint card"
```
