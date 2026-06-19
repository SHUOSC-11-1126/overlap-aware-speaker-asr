# Team Contributions

This file is the authoritative contribution record for the course/project
submission. Contribution records were centralized here so the repository has a
single source of truth; the former `docs/contributions/` tree was removed after
migration.

## 王景宏 (ceilf6)

### 一、最能体现深度思考的近期主线：ASR × LLM × 情感 × 说话人（2026-06-18，全部已合并）

围绕「参考无关地决定：何时分离 / 何时修复 / 如何读情感 / 是否信任说话人归属」。本地离线
`deepseek-r1`(ollama) + Whisper-tiny + silver 参考；缓存 + 注入式 fake-LLM 保证 CI 离线可复现。

| 主题                                   | Issue → PR        | 结论                                                                                                                                                                                                  |
| -------------------------------------- | ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **噪声鲁棒参考无关路由器**（capstone） | #814 → #837       | ✅ **强正**：仅凭门控输出的解码器退化信号在 mixed vs (分离+说话人门控) 间逐句路由，**优于两种固定策略**（0.778 vs 1.214 / 1.531），回收 **~92%** 的逐句 oracle 差距；Pearson(压缩比, 分离税)=**0.82** |
| **Semantic Emotion Tax**               | #831 → #832       | ✅ 本地 LLM 读隐式情感的覆盖率达词典 **~7×**（0.70 vs 0.10），与声学唤醒、词典效价**正交**——互补的第三情感模态                                                                                        |
| **情感锚定 ASR 修复**                  | #833 → #834       | ❌ **有界负结果**：用 LLM 检测到的立场锚定仍治不好过度修复（不修 0.924 < 朴素 1.082 < 锚定 1.122）；可部署结论=此设定下别做 LLM 盲修                                                                  |
| **三模态情感融合**                     | #835 → #836       | ◐ **微妙**：正交≠互补——融合仅对语义目标有增益、对声学目标反而有害；声学唤醒度是最强参考无关情感损伤信号                                                                                               |
| **LLM 说话人归属修复**                 | #838 → #839       | ◐ **微妙**：情感强烈编码 con/pro 角色（valence AUC 强度 0.78），但其极性参考无关**不可知**（朴素 0.08 / 符号校准上限 0.92）；并纠正"cpCER 换位不变=错误指标"的方法论陷阱                              |
| **前沿综述 + 主图（Mode D）**          | #840 → #841, #842 | 5 个结果综合成一页**可部署决策配方** + hero figure，并登上 README 首页                                                                                                                                |

**一句话统一结论：** 便宜的 Whisper 解码器信号是参考无关路由的可部署杠杆；声学韵律负责"声学
情感"；本地 LLM 的真正价值是**覆盖隐式语义**，而非免费的修复 / 归属规则。

### 二、情感前沿七部曲（findings #14–#20，issue #815–#827 / PR #816–#829，全部已合并）

把"何时分离"扩展到情感（gain-invariant 声学韵律 + 正则 valence reader，clean source 作 label-free 参考）：

- **#14 Emotional Separation Tax**：分离在所有重叠率都*帮助*情感，却在低 / 中重叠*损害* ASR——
  分离决策是**目标依赖**的。
- **#15 不对称**（负结果）：情感(arousal)**不**预测 ASR 难度（r≈0）——情感是要*保全*的结果，
  不是路由特征。
- **#17 LLM × ASR critic**（真实 deepseek-r1）：LLM 判官被免费的压缩比信号*支配*，GER 修复
  _过度纠正_——简单胜过花哨。
- **#18 目标感知解耦路由（capstone）**：按 ASR 信号路由文本、始终从分离轨读情感 → CER 不变、
  情感失真**减半**、联合 regret **降 ~14×**。
- **#19** 参考无关保真度计（粗粒度 clean/contaminated 门，r=−0.51）；**#20** CER 调优门控里
  **说话人门控对情感损害最小**而治 CER 最强。

### 三、分离税 / 噪声鲁棒 / 参考无关路由（issue #795–#814 / PR #796–#813，全部已合并）

oracle 分离相图与"分离税"、reference-free trim-and-guard 路由、参考无关质量估计（灾难门 vs 分级
表）、"按幻觉而非重叠路由"的留出集验证（**证伪**原假设、**验证** trim recipe）、说话人相似度不
预测分离收益（尾部混淆告警）、噪声击败 silence-trim 的 overlap × SNR 图、谱平坦度门控、"噪声
鲁棒的解药不在解码器"负结果，以及参考无关 gate selector（**证伪** #12 的断言、确认**说话人门控**
才是广谱解药）。

### 四、工程 Harness（仓库基础设施，全队受益）— issue #780 → PR #781

把 `ref/code-tape` 的 Harness 适配到本 Python 仓库，四大支柱 + 标准化「issue → PR → repo-guard CR
→ 回应」回路：

- **Git hooks**：`.githooks/{pre-commit,pre-push}` 经 `core.hooksPath`（pre-commit 快测门、
  pre-push GitNexus 契约 + 全测门），安装器 + `SKIP_QUALITY_HOOKS` 逃生阀。
- **GitNexus 知识库契约**：`scripts/harness/contract_{rules,check}.py`——关键骨架分类
  (router-core / evaluation-core / harness / references / gold-results / authority-docs)，改动
  **强制配对** `tests/test_<module>*.py` + 结构化 impact summary + 结果标签；CI 新增 `Contract Guard`。
- **SDD / TDD**：authority-doc 层级 + `docs/adr/`(ADR-001) + PR 模板 impact summary；契约机械要求
  关键改动配对测试。
- **repo-guard LLM 代码评审**接入与评审回路（每个 PR 逐条回应 guard findings 后才合并）。
- 验证：pre-push 实跑通过——GitNexus 索引（26,296 节点）+ 契约 + 全测（当时 3,253 tests OK），
  41 个 harness 契约测试。

### 五、研究熵自审与自我纠偏（元认知，最体现研究成熟度）— issue #785/#787 → PR #786/#788

诊断出本仓库正经历"**agentic 仪式塌缩**"：`src/*.py` 中 **~89%** 是自指的
handoff / receipt / coordination / completion-summary 仪式代码、**计算为零**（795 个仪式命名文件里
**0 个**含真实计算；compute-import 3.5% vs 实质 17%；0.11 vs 4.07 算术操作/文件）。

- 建**研究熵度量** `src/research_entropy_audit.py`（双信号分类器 + git 时间线 + 有界退化指数，
  `make entropy-audit`）+ **advisory** `scripts/harness/entropy_guard.py`（接入 `make quality-predev`，
  加仪式无实质即告警、从不阻断）。
- 据此**清理 6,000+ 个仪式文件**（803 个仪式 `src/*.py` + 1,112 个仪式测试 + ~4,360 个仪式结果
  工件），并把 ~4,400 行的 `project_harness.py` lean 重写为真实基线 smoke。
  **熵饱和度 0.894 → 0.035、退化指数 0.46 → 0.00、测试 3,304 → 825 全绿**，import-closure 0 违例、
  全程可从 git 历史恢复（#793/#794 顺手修复清理误删导致的红测门）。

### 六、稳定基线 & 横切

- **稳定基线**：CER 评估、Adaptive Router v1/v2、Risk-Aware Selector、Speaker-Aware CER、cpCER-lite。
- **前沿（基线侧）**：Compute-Aware Cascade、MeetEval/cpWER 兼容性、Speaker Profile/声纹风险、
  外部验证、LLM Critic、Demo。
- **横切**：`project_harness` 协调主链。

### 模块

`src/noise_robust_router.py`、`semantic_emotion_tax.py`、`emotion_anchored_repair.py`、
`emotion_modality_fusion.py`、`llm_speaker_attribution.py`、`frontier_capstone_figure.py`、
`emotion_separation_tax.py`、`arousal_asr_probe.py`、`lexical_emotion.py`/`lexical_emotion_tax.py`、
`llm_asr_critic.py`、`emotion_fidelity_meter.py`、`gate_emotion_cost.py`、`objective_aware_routing.py`、
`prosody.py`、`noise_robust_gate.py`、`speaker_conditioned_gate.py`、`gate_selector.py`、
`decoder_cure_noise.py`、`hallucination_router.py`、`reference_free_qe.py`、`separation_tax_phase.py`、
`research_entropy_audit.py`、`adaptive_router_v2.py`、`risk_aware_selector.py`、
`compute_aware_cascade.py`、`speaker_*.py`、`meeteval_*.py`、`external_validation_*.py`、
`project_harness.py`；以及 `scripts/harness/*`、`.githooks/*`、`docs/harness/*`、
`docs/frontier/asr_llm_emotion_capstone.md`。

## 吴方舟/wfzark（23123986）

**Role:** Core technical contributor; route-selection problem framer; main
experimental pipeline owner; AudioDepth frontier explorer; team report and
research-visualization contributor.

吴方舟的贡献主线是把项目从“比较一个固定 ASR 输出”推进为一个系统问题：
**when should an overlap-aware ASR system separate speech, keep mixed audio, or
fall back to a safer route?** 这一 framing 贯穿主实验、风险选择、前沿探索和
最终报告，使项目围绕 route selection、claim boundary 和 evidence level
组织，而不是只报告单一 CER 表。

### 1. Mainline ASR pipeline and route-selection evidence

在稳定主线上，吴方舟组织并实现/协调了项目的核心实验路径：

- mixed Whisper baseline；
- separated speaker-track ASR；
- speaker transcript merging；
- duplicate-suppressed cleaned separated transcript；
- verified gold-reference workflow；
- CER evaluation and comparison tables；
- error-type analysis for insertion / deletion / substitution / repetition；
- adaptive router v1；
- feature-based router v2；
- router ablation；
- synthetic silver validation；
- held-out synthetic split interpretation；
- speaker-aware CER；
- cpCER-lite speaker permutation checks；
- risk-aware final selector。

这些工作建立了项目最核心的比较面：`mixed_whisper`、
`separated_whisper`、`separated_whisper_cleaned`、router v1/v2、
risk-aware selector 和 oracle-best 的关系。对应的系统性文档入口包括
[Current results summary](results/figures/curated/current_results_summary.md),
[Results Index](docs/results-index.md), and
[Implementation Status](docs/implementation-status.md).

### 2. Evidence discipline and claim-boundary cleanup

吴方舟持续维护项目的证据边界，区分：

- five-case gold benchmark；
- synthetic silver validation；
- held-out synthetic split；
- silver-plus / proxy / diagnostic references；
- sampled real-Whisper validation；
- optional integration scaffolds；
- frontier exploratory research。

这部分贡献体现在主文档、结果索引和最终报告中，尤其是
[REPORT.md](REPORT.md) 中的 evidence-level table、limitations、team
contribution synthesis，以及对“CER is evaluation-only, never a routing input”
的反复约束。该工作避免把 synthetic、frontier 或 roadmap-only 内容误写成
stable mainline claim。

### 3. AudioDepth frontier research

吴方舟提出并推进 AudioDepth 方向，把 overlapping speech 解释为
time-frequency occlusion，并借鉴 RGB-D / depth-style visual recognition 中
“depth is an additional view, not a replacement for RGB”的思想。AudioDepth
探索 pre-ASR acoustic maps 是否能在 Whisper 产生不稳定 transcript 前暴露
overlap risk，从而辅助 mixed / separated / cleaned / review 路由。

该方向包括：

- overlap as time-frequency occlusion；
- RGB-D / depth-style research motivation and citations；
- deployable mixed-only AudioDepth maps；
- analysis-only separated-track diagnostics；
- AudioDepth MVP；
- weak simple-CNN negative result；
- model zoo, handcrafted features, CNN-depth models, balanced depth models；
- hybrid late fusion with transcript instability；
- controlled route-sensitive benchmark；
- balanced benchmark v2；
- real Whisper validation and proxy-to-real gap analysis；
- Stage-1 acoustic gate；
- risk-guarded sweep；
- end-to-end safety audit；
- curated 3D / channel / route-space visualizations。

AudioDepth 始终被标为 Frontier Branch Only / Exploratory Research，不替代
mainline pipeline，也不作为 stable deployment claim。完整研究叙事见
[AudioDepth Router Exploratory Study](docs/frontier/audio-depth-router.md)。

### 4. Team report, documentation integration, and research figures

近期贡献中，吴方舟推动并整理了团队级 [REPORT.md](REPORT.md)，把原本分散的
主线实验、Mode B cascade、speaker-aware evaluation、MeetEval/cpWER、
speaker-profile diagnostics、LLM critic、AudioDepth、OpenClaw / harness
等内容整合成一份 team-level research report。该报告删除了低信息密度的
handoff / receipt / checklist / queue 流水账，并改为围绕 research
question、benchmark evidence、core results、boundary analysis、compute-aware
routing、frontier studies 和 limitations 展开。

同时，吴方舟补充了可复现的科研绘图脚本
[`scripts/report/make_report_figures.py`](scripts/report/make_report_figures.py)，
并生成报告级图表：

- route map；
- gold CER strategy comparison；
- separation boundary phase plane；
- compute-aware cascade 3D surface。

这些图表服务于报告表达，不引入新 benchmark claim；数值图读取 curated
result tables，概念图明确标注为 decision surface / visualization。

### 5. Contribution boundary

吴方舟的贡献重点是主 ASR 实验管线、route-selection framing、AudioDepth 前沿
研究、证据边界维护和最终报告整合。已知限制仍然存在：gold benchmark 很小，
synthetic / silver 证据不能替代 gold，real-meeting generalization 未完全证明，
Stage-2 fallback / review policy 仍需更多验证，AudioDepth 需要独立评审后才
能进入任何 stable mainline claim。

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
