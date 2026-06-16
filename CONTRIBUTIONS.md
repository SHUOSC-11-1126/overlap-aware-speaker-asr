# Team Contributions

## 分工说明

| 成员 | 主要贡献 | 模块 |
| --- | --- | --- |
| ceilf6 | 项目负责人，横跨基线+前沿双线。**稳定基线:** CER评估、Adaptive Router v1/v2、Risk-Aware Selector、Speaker-Aware CER、cpCER-lite。**前沿探索:** Compute-Aware Cascade、MeetEval/cpWER兼容性、Speaker Profile/声纹风险、外部验证、LLM Critic、Demo。**横切:** `project_harness` 协调主链。**辅助:** 仓库维护、Harness (Git hooks/知识库契约/SDD/TDD) + repo-guard CR。 | `src/adaptive_router_v2.py`, `src/risk_aware_selector.py`, `src/compute_aware_cascade.py`, `src/cascade_tiers.py`, `src/speaker_*.py`, `src/llm_critic_*.py`, `src/meeteval_*.py`, `src/external_validation_*.py`, `src/demo_*.py`, `src/project_harness.py`, `scripts/harness/*` |

## Commit 规范

- feat: 新功能
- fix: 修复
- docs: 文档
- refactor: 重构
- eval: 评估实验

## 代码审查

所有 PR 需至少一人 review 后合并。
