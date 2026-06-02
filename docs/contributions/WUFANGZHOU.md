# Contribution Record: WUFANGZHOU / 吴方舟

## 1. Role

Core technical lead / project architecture lead / main experimental pipeline owner.

## 2. Contribution Summary

WUFANGZHOU led the core technical development of the project, including project direction design, benchmark organization, ASR pipeline construction, gold reference workflow, CER evaluation, error type analysis, adaptive routing, synthetic robustness validation, speaker-aware evaluation, risk-aware selection, and project maintenance documentation.

## 3. Main Technical Contributions

- Initialized and organized the project repository.
- Built the benchmark structure for mixed audio, separated speaker tracks, snippets, and synthetic samples.
- Implemented / coordinated Whisper mixed ASR baseline.
- Implemented / coordinated separated speaker-track ASR and speaker transcript merging.
- Created comparison tables for mixed vs separated ASR.
- Built verified reference workflow for five gold cases.
- Generated and manually corrected LLM-assisted reference drafts.
- Implemented CER evaluation for mixed / separated / cleaned methods.
- Implemented duplicate suppression post-processing.
- Implemented error type analysis for insertion / deletion / substitution / repetition.
- Implemented adaptive router v1 and feature-based router v2.
- Implemented router ablation.
- Built synthetic silver benchmark and held-out synthetic split validation.
- Implemented synthetic audit to distinguish pipeline bugs from real hallucination / length inflation.
- Implemented speaker-aware CER and cpCER-lite speaker permutation analysis.
- Implemented risk-aware final selector.
- Added AGENTS.md, project_state.md, skills, roadmap, maintenance harness, and documentation refresh.

## 4. Key Findings Contributed

- Speech separation is useful but not universally beneficial.
- LightOverlap / MidOverlap degradation is mainly caused by insertion and repetition hallucination.
- Speaker swap is not the dominant error source in the five gold cases.
- Overlap-only routing can overfit small gold benchmarks.
- Repetition and duplicate-removal signals are useful for routing stability.
- Router v2 improves synthetic robustness while preserving gold performance.
- Risk-aware selector provides reference-free risk detection, but router_v2 remains the best-CER route on gold.

## 5. Evidence

Selected commits:

- `6c0bd00` create project skeleton and audio manifest
- `b68846a` run mixed whisper baseline for all benchmark cases
- `66476e4` run separated whisper baseline for all benchmark cases
- `640578d` implement CER evaluation for NoOverlap
- `efdebba` add final CER figures and adaptive routing analysis
- `6037c78` implement rule-based adaptive routing
- `74aba21` add error type analysis for ASR methods
- `6da42b2` add speaker-aware CER evaluation
- `4a6fc53` add synthetic benchmark silver evaluation
- `be09d54` add feature-based adaptive router v2
- `da66fef` add router feature ablation analysis
- `a3baf55` add held-out synthetic split validation
- `a27b8c0` add cpCER-lite speaker permutation evaluation
- `da63400` add risk-aware final selector
- `aabcf91` add project context for future agents
- `f4fc8a7` refresh documentation and maintenance alignment
- `86a4272` add project skills roadmap and maintenance harness

## 6. Estimated Contribution

Suggested status: core technical contribution completed.

Estimated percentage: TBD by team discussion.

Suggested range for team discussion: high / core contributor.

Final percentage should be confirmed by all team members before submission.

## 7. Handoff Status

As of this handoff, WUFANGZHOU has completed the core technical pipeline and documentation alignment. Further work should be handled by remaining team members, especially final report polish, demo, video, literature review, and optional future skills.
