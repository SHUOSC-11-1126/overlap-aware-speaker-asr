# Cascade Recommendation Stability Audit

This audit checks how often each recommendation profile keeps the same strategy across audited scopes.

| profile | distinct_strategy_count | most_common_strategy | consensus_ratio | scope_count | strategy_set |
| --- | ---: | --- | ---: | ---: | --- |
| accuracy_first | 2 | fixed_separated_whisper_cleaned | 0.75 | 4 | fixed_separated_whisper_cleaned;router_v2_costed |
| balanced | 2 | router_v2_synthetic_costed | 0.75 | 4 | router_v2_costed;router_v2_synthetic_costed |
| cost_first | 1 | fixed_mixed_whisper | 1.0 | 4 | fixed_mixed_whisper |
