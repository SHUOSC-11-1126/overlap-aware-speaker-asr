# Team Contributions

## 分工说明

| 成员 | 主要贡献 | 模块 |
| --- | --- | --- |
| 王景宏 (ceilf6) | **组长**，横跨基线+前沿双线。**稳定基线:** CER评估、Adaptive Router v1/v2、Risk-Aware Selector、Speaker-Aware CER、cpCER-lite。**前沿探索:** Compute-Aware Cascade、MeetEval/cpWER兼容性、Speaker Profile/声纹风险、外部验证、LLM Critic、Demo。**横切:** `project_harness` 协调主链。**辅助:** 仓库维护、Harness (Git hooks/知识库契约/SDD/TDD) + repo-guard CR。 | `src/adaptive_router_v2.py`, `src/risk_aware_selector.py`, `src/compute_aware_cascade.py`, `src/speaker_*.py`, `src/llm_critic_*.py`, `src/meeteval_*.py`, `src/external_validation_*.py`, `src/demo_*.py`, `src/project_harness.py`, `scripts/harness/*` |
| 谢宇轩 (xyx12369) | **Mode B: 算力感知三层级联识别。** 设计并实现参考无关的三层级联架构——Tier 1 (便宜) → Tier 2 (风险触发更强ASR) → Tier 3 (LLM Critic/人工复核)。升级决策仅依赖可观测信号（重复段数、运行时间膨胀、文本长度比、重叠等级），CER 仅用于事后评估。产出 CER-cost tradeoff 散点图、成本感知路由表、覆盖率统计、与固定策略及 router_v2 的横向对比分析。24 单元测试 TDD。标签: `experimental/frontier`。 | `src/cascade_tiers.py`, `tests/test_cascade_tiers.py` |

## Commit 规范

- feat: 新功能
- fix: 修复
- docs: 文档
- refactor: 重构
- eval: 评估实验

## 代码审查

所有 PR 需至少一人 review 后合并。
