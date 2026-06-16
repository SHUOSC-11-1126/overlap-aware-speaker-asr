# Contribution Record: 王景宏 (WangJingHong / ceilf6)

> Course final-submission contribution record. The estimated contribution in §6
> is a basis for team discussion, not a unilateral claim. Every attribution
> below is grounded in git history (representative commit hashes in §5), and
> founding/parallel work by other members is credited explicitly in §7 so this
> record reads honestly alongside the other contribution statements.

GitHub: [@ceilf6](https://github.com/ceilf6) · git identities: `ceilf6 <3506456886@qq.com>`, `ceilf6 <wangjinghong02@meituan.com>`, `WJH <3506456886@qq.com>`.

## 1. Role

Primary developer for the main development sprint
(2026-06-06 → 2026-06-16). Owner of the experimental frontier, the always-on
development harness, the project-wide coordination backbone, and the
demo / presentation system. Co-developer and maintainer of the stable baseline
that was founded by 吴方舟.

## 2. Contribution Summary

王景宏 is the dominant contributor to the repository by every git measure:
roughly **3,374 non-merge commits** across all branches (**2,171 on `main`**),
**116 merge/PR commits**, references to **639 distinct PR numbers**, and
first-authorship of about **856 of ~892 current `src/*.py` modules (~96%)**.

After 吴方舟 founded the baseline skeleton on 2026-06-02, 王景宏 drove the
project from 2026-06-06 onward: building the entire experimental frontier, the
engineering harness (Git hooks / knowledge-base contract / SDD / TDD), the
`project_harness` coordination main line, and the demo system, while extending
and maintaining the baseline evaluation and routing modules. Of the 133 PRs
merged into `main`, 116 (~87%) were authored by 王景宏.

## 3. Main Technical Contributions

### 3.1 Stable baseline — extended and maintained (founded by 吴方舟)

- Extended and maintained CER evaluation, adaptive router v1/v2, risk-aware
  selector, speaker-aware CER, cpCER-lite, and error-type analysis. These
  modules were first created by 吴方舟 on 2026-06-02 and subsequently carried,
  refactored, and integrated into the harness/coordination flow by 王景宏.

### 3.2 Experimental frontier — created

- **Compute-aware cascaded recognition** — `src/compute_aware_cascade.py`
  (created in `513d9f82`): cost-aware routing where CER is used only _after_
  each route is fixed; labeled `experimental/frontier`.
- **Frontier coordination board** — `src/frontier_go_no_go_board.py`
  (created in `c8286679`), with paired tests.
- **Demo / presentation system** — `src/demo_go_no_go_board.py`
  (created in `440c699f`) plus the demo storyboard, walkthrough, and
  presentation-polish receipts under `results/`.
- **Frontier scaffolds** — MeetEval / cpWER compatibility, external
  mini-validation (license gate + slice manifest), and speaker-profile /
  voiceprint risk scaffolds. All kept as clearly labeled scaffolding rather
  than being promoted to gold claims.

### 3.3 Development harness — created

- Integrated and strengthened the code-tape-inspired **Harness**
  (`75a4d15c`, `ccdcbab5`, PR #781): `pre-commit` fast test gate and
  `pre-push` contract + full test gate via `core.hooksPath`, the GitNexus
  **knowledge-base contract**, the **SDD** authority hierarchy + ADRs, and
  **TDD** paired-test enforcement for critical code. Documented as the
  "Harness Engineering Loop" (`921abeb7`) with the
  `issue → PR → repo-guard CR → respond` workflow.

### 3.4 Coordination backbone — created and massively expanded

- `src/project_harness.py` — the single most-edited file in the repository
  (~982 commit touches): the coordination main line that ties baseline and
  frontier together, the "wave" coordination/writeback system (e.g. Wave148
  #731, Wave162 #771, Wave163 #774, Wave164 #779), and the frontier execution
  queue.

### 3.5 Documentation & governance — created

- `docs/project_state.md`, `docs/roadmap.md`, `docs/maintenance_harness.md`,
  `docs/harness/*`, ADRs, the agent challenge board, and the README structure
  (including the Harness Engineering Loop and OpenClaw sections).

### 3.6 Test discipline

- **568 `test`-prefixed commits** reflect a test-first workflow; paired tests
  accompany critical-code changes as required by the harness contract.
  Overall type mix: ~584 `feat`, ~568 `test`, ~352 `docs`, ~289 `chore`,
  ~44 `fix` (plus `wave*` coordination commits).

## 4. Key Findings / Engineering Contributions

- Compute-aware cascading can hold router_v2 gold CER (≈0.120) while reducing
  relative cost (~0.93×) using only reference-free signals.
- Established the result-labeling discipline (stable/gold, synthetic/silver,
  experimental/frontier, qualitative/demo, external/sanity-check,
  oracle/analysis-only) that prevents silver/frontier evidence from being
  promoted into gold claims.
- Built the always-on harness that mechanically protects the stable baseline
  (paired-test contract + knowledge-base impact check) while still enabling
  high-velocity frontier exploration.

## 5. Evidence (selected commits)

- `513d9f82` feat: add compute-aware cascade analysis
- `c8286679` feat: add frontier go-no-go board
- `440c699f` feat: add demo go-no-go board
- `75a4d15c` chore: integrate and strengthen code-tape Harness (hooks / KB contract / SDD / TDD)
- `ccdcbab5` integrate and strengthen code-tape Harness (PR #781)
- `921abeb7` docs: expand Harness Engineering Loop section in README
- `407971e8` Wave162 exploration + baseline closure after external-validation chain (PR #771)
- `876f462f` Wave163 exploration + baseline closure after MeetEval chain (PR #774)
- `91c0d066` Wave164 MidOverlap diagnostic coordination writeback (PR #779)
- `fd8bca62` docs: restore Harness Engineering Loop and add OpenClaw section to README

Aggregate evidence: ~3,374 non-merge commits (2,171 on `main`), 116 PRs
authored of 133 merged into `main`, 639 distinct PR references, and
~856 / 892 `src/*.py` modules first-authored. Activity window:
2026-06-06 → 2026-06-16. (Counts from `git log --all` at the time of writing.)

## 6. Estimated Contribution

Dominant contributor by commit volume and module authorship. Suggested range
for team discussion: **primary / lead contributor**. The final percentage split
should be confirmed by the whole team and read together with the other records
(see §7), not derived from commit counts in isolation — per
[docs/contributions/README.md](README.md).

## 7. Boundaries / Honest Attribution

To keep this record fair and verifiable, the following work is **not** claimed
by 王景宏:

- **Baseline founding (吴方舟):** the core evaluation/routing modules
  (`evaluate_cer.py`, `adaptive_router.py`, `adaptive_router_v2.py`,
  `risk_aware_selector.py`, `evaluate_speaker_cer.py`, `evaluate_cpcer_lite.py`,
  `evaluate_error_types.py`, and the initial `project_harness.py` skeleton) were
  first created by 吴方舟 on 2026-06-02. See [WUFANGZHOU.md](WUFANGZHOU.md).
- **LLM / RAG collaborative repair (saayaya):** `src/llm_repair_loop.py` and
  `src/rag_repair.py` were authored by saayaya on 2026-06-09.
- **Mode B three-tier cascade (谢宇轩 / xyx12369):** `src/cascade_tiers.py`
  and `tests/test_cascade_tiers.py` were authored by 谢宇轩; 王景宏's role on
  Mode B was limited to integration and documentation.

## 8. Handoff Status

As of this record, 王景宏 has delivered the experimental frontier, the
development harness, the coordination backbone, the demo system, and the
documentation/governance layer, and has maintained the stable baseline. Natural
next steps for other members: final report polish, demo video, literature
review, and continued frontier experiments under clearly labeled result
directories.
