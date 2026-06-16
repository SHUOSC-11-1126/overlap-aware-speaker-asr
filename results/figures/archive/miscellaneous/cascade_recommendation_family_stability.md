# Cascade Recommendation Stability Audit

This audit checks how often each recommendation profile keeps the same strategy across audited scopes.

| profile | distinct_strategy_count | most_common_strategy | consensus_ratio | scope_count | strategy_set |
| --- | ---: | --- | ---: | ---: | --- |
| accuracy_first | 2 | fixed_separated_whisper_cleaned | 0.75 | 4 | fixed_separated_whisper_cleaned;router_v2 |
| balanced | 1 | router_v2 | 1.0 | 4 | router_v2 |
| cost_first | 1 | fixed_mixed_whisper | 1.0 | 4 | fixed_mixed_whisper |
