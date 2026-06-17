# Team Contributions

This file is the authoritative contribution record for the course/project
submission. Contribution records were centralized here so the repository has a
single source of truth; the former `docs/contributions/` tree was removed after
migration.

## WU FANGZHOU / 吴方舟

**Role:** Core technical contributor; project route designer; main experimental
pipeline owner; AudioDepth frontier explorer.

WU FANGZHOU contributed to the project from the mainline system design through
evaluation, routing, documentation, and frontier research planning. A central
part of this work was framing the project around a system-level question:
**when should an overlap-aware ASR system separate speech, keep mixed audio, or
fall back to a safer review path?** This framing helped keep the repository
focused on route selection rather than only reporting one fixed ASR result.

On the stable mainline, WU FANGZHOU helped organize the benchmark structure for
mixed audio, separated speaker tracks, snippets, and synthetic samples. He
implemented or coordinated the mixed-Whisper baseline, separated-track ASR,
speaker transcript merging, comparison tables, verified gold-reference
workflow, CER evaluation, duplicate suppression, error-type analysis, adaptive
router v1, feature-based router v2, router ablation, synthetic silver
validation, speaker-aware CER, cpCER-lite speaker permutation checks, and the
risk-aware final selector. This work established the main experimental path used
to compare mixed, separated, cleaned, routed, and risk-aware ASR outputs.

He also contributed to evidence discipline. The project distinguishes gold
cases, silver-plus references, synthetic silver validation, proxy simulation,
sampled real-Whisper validation, diagnostic experiments, and roadmap-only
claims. WU FANGZHOU helped keep these boundaries visible so the project does not
overstate synthetic or exploratory evidence as final benchmark proof. His
documentation work included project state refreshes, maintenance alignment,
claim-boundary cleanup, and review-facing summaries.

As frontier exploration, WU FANGZHOU proposed and developed the AudioDepth
direction. This work treats overlapping speech as a time-frequency occlusion
problem and explores whether pre-ASR acoustic representations can help routing
or safety-aware triage. The AudioDepth work should be read as exploratory
frontier research only. It is not claimed as a stable mainline feature, and it
does not replace the documented mainline evaluation pipeline. For the detailed
AudioDepth exploratory study, see
[AudioDepth Router Exploratory Study](docs/frontier/audio-depth-router.md).

Known limitations remain: some controlled references are silver-plus or
synthetic, real-meeting generalization is not fully proven, Stage-2 fallback /
review policy still needs further work, and AudioDepth requires separate review
before any merge into stable claims.

## 王景宏 (ceilf6)

**Role:** 组长，横跨基线+前沿双线。

**主要贡献：**

- **稳定基线:** CER评估、Adaptive Router v1/v2、Risk-Aware Selector、
  Speaker-Aware CER、cpCER-lite。
- **前沿探索:** Compute-Aware Cascade、MeetEval/cpWER兼容性、Speaker
  Profile/声纹风险、外部验证、LLM Critic、Demo、噪声鲁棒
  separation-hallucination 门控（`noise_robust_gate`，谱平坦度 VAD，承接
  #806 "noise defeats the silence-trim cure"）。
- **横切:** `project_harness` 协调主链。
- **辅助:** 仓库维护、Harness (Git hooks/知识库契约/SDD/TDD) +
  repo-guard CR。

**模块：** `src/adaptive_router_v2.py`, `src/risk_aware_selector.py`,
`src/compute_aware_cascade.py`, `src/speaker_*.py`,
`src/llm_critic_*.py`, `src/meeteval_*.py`,
`src/external_validation_*.py`, `src/demo_*.py`,
`src/project_harness.py`, `src/noise_robust_gate.py`, `scripts/harness/*`.

## 谢宇轩 (xyx12369)

**Role:** Mode B: 算力感知三层级联识别。

**主要贡献：**

- 设计并实现参考无关的三层级联架构：Tier 1 (便宜) → Tier 2
  (风险触发更强ASR) → Tier 3 (LLM Critic/人工复核)。
- 升级决策仅依赖可观测信号，包括重复段数、运行时间膨胀、文本长度比
  和重叠等级；CER 仅用于事后评估。
- 产出 CER-cost tradeoff 散点图、成本感知路由表、覆盖率统计，以及与
  固定策略及 router_v2 的横向对比分析。
- 完成 24 单元测试 TDD。
- 标签: `experimental/frontier`。

**模块：** `src/cascade_tiers.py`, `tests/test_cascade_tiers.py`.

## 邵俊霖 / saayaya (23124001)

**Role:** Separation Phase Diagram 修复；Learned Router 设计与实现；bugfix。

**主要贡献：**

### 1. Phase Diagram Bugfix
- 修复 `separation_phase_diagram.py` 中因合并冲突导致的内容重复和
  import 损坏问题（移除 374 行重复代码，修复 `collections.defaultdict` 
  import）。
- 创建缺失模块 `src/plot_phase_boundary.py`：
  实现 `plot_enhanced_phase_diagram()`（带 crossover 标记和 CI 区域的
  增强相图）和 `plot_bootstrap_probability_curve()`（bootstrap P(helps)
  概率曲线+ΔCER双轴图）。
- 补充 `tests/test_plot_phase_boundary.py`（5 项 smoke test，覆盖
  有无 boundary_metadata 两种路径）。

### 2. Learned Router（主要贡献）
- 针对 REPORT.md §7 "router is entirely rule-based" 的局限性，设计并
  实现了监督学习路由器 `src/learned_router.py`，替代手写规则 router_v2。
- 使用 synthetic split 的 CER 表自动生成 oracle-best 标签，训练
  Logistic Regression 和 Decision Tree 两种模型。
- 特征完全基于可观测信号（overlap_level、text_length_ratio、
  runtime_ratio、duplicate_removed_count 等 10 维特征），无 CER 泄露。
- 评估结果：Logistic Regression 在 held-out test split 达到
  **78% accuracy，平均 CER 0.168**（优于 cleaned baseline 0.185，
  接近 oracle 0.115）。
- Decision Tree 输出可解释规则树，可与 v2 手写规则直接对比。
- 编写 `scripts/train_learned_router.py` 一键训练脚本，输出
  `learned_router_evaluation.json/csv` 和 `learned_router_tree_rules.txt`。
- 完成 `tests/test_learned_router.py` 共 11 项单元测试（全部通过）。
- 标签: `experimental/frontier`。

**模块：** `src/learned_router.py`, `src/plot_phase_boundary.py`,
`src/separation_phase_diagram.py` (fix), `scripts/train_learned_router.py`,
`tests/test_learned_router.py`, `tests/test_plot_phase_boundary.py`.

## Additional Contributors

Additional team members can add concise contribution statements here before the
final course submission. New entries should keep the same format: role,
mainline contribution, frontier or exploratory contribution if applicable, and
claim boundaries.

## Commit 规范

- feat: 新功能
- fix: 修复
- docs: 文档
- refactor: 重构
- eval: 评估实验

## 代码审查

所有 PR 需至少一人 review 后合并。
