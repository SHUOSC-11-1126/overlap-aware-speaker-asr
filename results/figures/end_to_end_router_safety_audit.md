# End-to-End Router Safety Audit

- evaluated samples: `60`
- high-error mixed selections: `12`
- direct-bypass high-error count: `0`
- Stage-2/review-path high-error count: `12`
- source breakdown: `stage2_after_review_candidate:12`
- oracle breakdown: `mixed:11; separated:1`
- review-needed family count: `8`
- weak silver reference count: `12`
- balanced risk-guarded CER: `0.529082`
- router_v2 CER: `0.64352`
- Conclusion: AudioDepth direct bypass safety is solved in the selected Stage 30 policy, but end-to-end safety is not solved because the Stage-2/review path can still choose mixed on high-error silver-plus cases.
- Current largest risk: weak references plus missing abstention/review enforcement after Stage-2 mixed decisions.
