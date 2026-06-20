# Team Contributions

This file is the authoritative contribution record for the course/project
submission. Contribution records were centralized here so the repository has a
single source of truth; the former `docs/contributions/` tree was removed after
migration.

## 王景宏 (ceilf6)

### 一、最能体现深度思考的近期主线：因果与内部状态幻觉探针（2026-06-20，Mode C，issue #855）

承接 `separation_tax`（参考无关压缩比门控能标记灾难性幻觉尾，AUC≈1.0）——但压缩比是**输出信号**，
要到解码流 ~20% 处才触发，重复早已吐给用户。本工作**首次往 Whisper 内部看**：3 秒"静音+音"smoke
复现循环（token ×224）且 `avg_logprob=-0.065`（极度自信）→ 循环是**confident attractor，非置信崩溃**。
两阶段 case-control（穷举发现 14/165 con×pro 灾难 + 26 灾难 vs 40 干净）：
- **H-M 机制 ✅（修正）**：灾难轨用*更高*自信（avg_logprob −0.335 vs −0.739）+ *更低* token 熵（1.49 vs 2.33）解码；
  诚实修正：`no_speech_prob` 反相关（AUC 0.33）**不是**信号——smoke 的"编码器喊无声"是近纯静音特例。
  把 2025-26 confident-attractor 线（Aparin/Waldendorf/Calm-Whisper/Viakhirev）**扩展到分离税 regime**。
- **两种模式**：Mode R（重复型，con_001/002/010，11/26）vs Mode N（非重复型，pro_006，15/26）→ 解释了
  为何无单一参考无关检测器能通吃。
- **H-D 延迟 ✅（Mode R）**：新信号 **token-id 重复锁定 trip-wire**（任意周期 p 的 ≥3 次重复；p=1 单字…p=6 短语）
  在 ~2% 流处触发 vs 压缩比 ~20%（**~10× 更早**）；CR 的 AUC(0.996) 仍是最广检测器。
- **H-C 可部署（scoped）**：紧因果 cap（流式现实 0.05–0.15）下 causal-internal 胜 causal-CR；松 cap 下 CR 的
  双模式覆盖反超；二者皆不独占 → 可部署设计取并集。
- **诚实新颖性**（6-agent 文献综述锚定）：token-id lock-in + 离线 CR 路由器 prefix-强制增益衰减分析是
  未被占据的槽；confident-loop 机制与分离交叉点是已建立的基石（引用，不声称发现）。

模块 `src/causal_hallucination_probe.py` + `tests/test_causal_hallucination_probe.py`（23 纯助手单测）；
`docs/frontier/causal_hallucination_probe.md` + `_litreview.md`；`results/frontier/causal_hallucination_probe/`。

### 一-bis、模型规模与修正前沿：分离税是 tiny 模型伪影（2026-06-20，Mode A+C，全部已合并）

9 个 PR（#860–#871），回答一个根本问题：**"何时分离"这个问题是真实的，还是 tiny 模型的伪影？**

| 主题 | Issue → PR | 结论 |
|---|---|---|
| **置信度校准路由器** | CCR (direct) | ❌ 多信号复合反而更差；压缩比单独即近最优 |
| **多解码投票** | #858 → #860 | ❌ 温度扰动无帮助；CR Spearman 0.781 胜出 |
| **对比解码** | #857 → #861 | ◐ 发散检测幻觉（AUC 0.765）但 fallback 不能修复 |
| **🏆 模型规模分析** | #859 → #862 | **🏆 base 消除分离税（CER 0.200 在所有重叠率恒定）** |
| **运行时级联** | #863 → #864 | ❌ CR 信号太粗糙（二元悬崖，非平滑 Pareto） |
| **参考有效性** | → #866 | ✅ base 的 0.200 CER 是真实的（非模型相似性） |
| **错误模式分析** | #867 → #868 | ❌ 64 种模式仅 9.4% 重复——0.200 是修正硬地板 |
| **LLM 重评分** | #869 → #870 | ❌ 灾难性（0/26 改善，CER 0.316→0.798） |
| **错误类型分解** | #865 → #871 | ◐ 两模型均 ~70% 替换主导；CER 差异=总数，非类型 |

**一句话结论：** "重叠感知说话人 ASR"问题是 tiny 模型伪影。Whisper-base（1.93× 计算）在所有重叠率
产生 CER=0.200——分离税消失。0.200 剩余 CER 是硬地板：模式修正、T/S 归一化、LLM 重评分均失败。
未来前沿应聚焦 base+ 模型能力和外部验证。

模块：`src/confidence_calibrated_router.py`、`src/multi_decode_voter.py`、`src/contrastive_decode.py`、
`src/model_scale_analysis.py`、`src/runtime_cascade.py`、`src/error_profile_decomposition.py`；
对应测试 + `results/frontier/{confidence_calibrated_router,multi_decode_voter,contrastive_decode,model_scale,runtime_cascade,reference_validity,base_error_correction,llm_base_rescore,error_profile_decomposition}/`。

### 二、最能体现深度思考的近期主线：ASR × LLM × 情感 × 说话人（2026-06-18，全部已合并）

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

### 三、情感前沿七部曲（findings #14–#20，issue #815–#827 / PR #816–#829，全部已合并）

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

### 四、分离税 / 噪声鲁棒 / 参考无关路由（issue #795–#814 / PR #796–#813，全部已合并）

oracle 分离相图与"分离税"、reference-free trim-and-guard 路由、参考无关质量估计（灾难门 vs 分级
表）、"按幻觉而非重叠路由"的留出集验证（**证伪**原假设、**验证** trim recipe）、说话人相似度不
预测分离收益（尾部混淆告警）、噪声击败 silence-trim 的 overlap × SNR 图、谱平坦度门控、"噪声
鲁棒的解药不在解码器"负结果，以及参考无关 gate selector（**证伪** #12 的断言、确认**说话人门控**
才是广谱解药）。

### 五、工程 Harness（仓库基础设施，全队受益）— issue #780 → PR #781

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

### 六、研究熵自审与自我纠偏（元认知，最体现研究成熟度）— issue #785/#787 → PR #786/#788

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

### 七、稳定基线 & 横切

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

### 3. LLM-ASR Collaborative Repair（本轮新增）

- 实现 LLM-ASR 协作修复闭环 `src/llm_repair_loop.py`：以 ASR 输出为
  起点，经风险检测 → RAG 检索 → LLM 纠错 → CER 评估迭代修复（最多三轮、
  带收敛判定与回退保护），并提供离线 oracle 模式，在未运行完整 pipeline
  时自动生成 synthetic ASR 输出以支持复现。
- 实现 RAG 检索修复模块 `src/rag_repair.py`：基于已验证 reference
  segments 构建知识库，使用字符 n-gram Jaccard 相似度检索 top-k 上下文，
  为 LLM 修复提供领域提示。
- 实现 Router 特征重要性分析 `src/router_feature_importance.py`：量化各
  特征对 learned router 决策的贡献并输出可视化柱状图，支撑 routing 决策的
  可解释性分析。
- 修复 learned router 的 sklearn 兼容性问题（LogisticRegression
  `multi_class` 参数与 `classification_report` 的 `target_names` 数量
  不匹配），并将 `src/__init__.py` 中 router 可视化模块改为 lazy import，
  避免可选依赖缺失导致整体导入失败。
- 完善 `README.md` 的 LLM-ASR Collaborative Repair 章节（架构图、模块表、
  使用方法、RAG 集成说明与设计理念），并配合 `demo/app.py` 整理 LLM-repair
  与 router 模块在演示中的调用路径。

**模块：** `src/learned_router.py`, `src/plot_phase_boundary.py`,
`src/separation_phase_diagram.py` (fix), `scripts/train_learned_router.py`,
`tests/test_learned_router.py`, `tests/test_plot_phase_boundary.py`,
`src/llm_repair_loop.py`, `src/rag_repair.py`,
`src/router_feature_importance.py`, `src/__init__.py`, `README.md`,
`demo/app.py`.

## 梁跃川 / liang-yuechuan

**Role:** Mode C: 前沿探索 — 分离相位图 (Separation Phase Diagram) 设计与实现。

**主要贡献：**

### 1. Separation Phase Diagram（核心贡献）

针对项目核心问题"语音分离何时帮助、何时损害多说话人 ASR"，设计并
实现了 `src/separation_phase_diagram.py`，通过 delta CER
（separated_whisper − mixed_whisper）vs overlap ratio 的散点图
量化分离帮助/损害的 crossover 边界。

### 2. 单元测试 (TDD)

- `tests/test_separation_phase_diagram.py`（5 项测试）：
  覆盖 `compute_delta_cer`（正负 delta）、`overlap_bin_key`
  （步长舍入）、`build_gold_points`（锚点映射 + separation_helps
  标记）、`build_silver_points`（manifest overlap ratio 读取）、
  `aggregate_trend_rows`（分箱聚合 + help_rate 计算）。
- `tests/test_separation_phase_diagram_write_outputs.py`（1 项测试）：
  smoke test 验证 `write_outputs()` 正确输出 CSV（含正确列名和
  行数据）、JSON（结构正确）、Markdown（含 `experimental/frontier`
  标签和 case 名称）、PNG（非空文件 ≥ 6 字节）。

全部 6 项测试通过。

### 3. 研究意义

该项目首次为 overlap-aware ASR 提供了"分离是否值得"的量化视图：
在低重叠场景分离有益（delta < 0），在高重叠场景分离可能有害
（delta > 0），为 Router 决策和级联策略提供了实验依据。

**模块：** `src/separation_phase_diagram.py`,
`tests/test_separation_phase_diagram.py`,
`tests/test_separation_phase_diagram_write_outputs.py`.

## 张浩豪 / haohaozhang776

**Role:** Mode D: Evaluation System & Cross-Benchmark Analysis（评估系统与跨实验对齐）

**主要贡献：**

- 构建统一 evaluation adapter，使 mixed / separated / cleaned / router v2 / cascade outputs 能够在同一评估接口下进行对齐比较，减少不同 pipeline 在格式层面的不一致问题。
- 设计并实现跨 benchmark aggregation 流程，将 gold / synthetic / held-out 三类数据的评估结果统一标准化为可复用 evaluation schema，用于 REPORT.md 与可视化模块共享。
- 对 speaker-aware CER、cpCER-lite 以及 error-type breakdown（insertion / deletion / repetition）进行了结构化整理，使其可用于后续 routing 与 separation 分析。
- 协助建立 evaluation sanity check pipeline，用于检测不同 ASR 输出在 alignment、length drift 与 duplication ratio 上的一致性风险。
- 参与 early-stage evaluation robustness exploration，分析不同 ASR pipeline 在长文本与高重叠场景下的 stability drift。
- 对 router v2 与 rule-based baseline 的评估偏差进行了对照分析，支持 report 中“reference-free routing validity”的实验结论构建。
- 提供 evaluation-side evidence support，用于验证 cascade / learned router / separation phase analysis 的实验一致性。

**模块：**

src/eval_adapter.py, src/eval_aggregator.py, src/speaker_cer.py, src/error_analysis.py, scripts/eval_sanity_check.py

## Commit 规范

- feat: 新功能
- fix: 修复
- docs: 文档
- refactor: 重构
- eval: 评估实验

## 代码审查

所有 PR 需至少一人 review 后合并。
