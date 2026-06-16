# Team Contributions

## 分工说明

| 成员 | 主要贡献 | 模块 |
| --- | --- | --- |
| ceilf6 | **组长**，横跨基线+前沿双线。**稳定基线:** CER评估、Adaptive Router v1/v2、Risk-Aware Selector、Speaker-Aware CER、cpCER-lite。**前沿探索:** Compute-Aware Cascade、MeetEval/cpWER兼容性、Speaker Profile/声纹风险、外部验证、LLM Critic、Demo。**横切:** `project_harness` 协调主链。**辅助:** 仓库维护、Harness (Git hooks/知识库契约/SDD/TDD) + repo-guard CR。 | `src/adaptive_router_v2.py`, `src/risk_aware_selector.py`, `src/compute_aware_cascade.py`, `src/speaker_*.py`, `src/llm_critic_*.py`, `src/meeteval_*.py`, `src/external_validation_*.py`, `src/demo_*.py`, `src/project_harness.py`, `scripts/harness/*` |
| xyx12369 | **Mode B: 算力感知三层级联识别。** 设计 Tier 1 (便宜) → Tier 2 (风险触发更强ASR) → Tier 3 (LLM Critic/人工复核) 的参考无关级联架构。用可观测信号（text_length_ratio、duplicate_removed_count、runtime_ratio、overlap_level）驱动升级决策，CER 仅用于事后评估。产出 CER-cost tradeoff 对比图、覆盖率统计、成本感知路由表。24 单元测试 TDD。 | `src/cascade_tiers.py`, `tests/test_cascade_tiers.py`, `results/tables/cascade_tiers_*.csv`, `results/figures/cascade_tiers_*.md`, `results/figures/cascade_tiers_cer_cost_tradeoff.png` |
| Claude Code | AI agent 协作体，在 xyx12369 指导下实现 `cascade_tiers.py`（907行）及配套测试（389行），遵循仓库 TDD/Harness 流程。生成策略对比分析和 tradeoff 图表。 | 同上模块，代码实现 |

## Commit 规范

- feat: 新功能
- fix: 修复
- docs: 文档
- refactor: 重构
- eval: 评估实验

## 代码审查

所有 PR 需至少一人 review 后合并。
