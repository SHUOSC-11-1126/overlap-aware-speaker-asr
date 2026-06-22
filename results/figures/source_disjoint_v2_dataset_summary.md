# Source-disjoint v2 dataset summary

| split | manifest rows | route-CER rows | source tokens |
| --- | ---: | ---: | ---: |
| train | 26 | 20 | 12 |
| validation | 10 | 9 | 7 |
| test | 11 | 7 | 7 |
| excluded | 73 | 24 | 26 |

- source-utterance leakage: `0`
- source-pair leakage: `0`
- excluded rows are cross-partition by source token and are not used for strict train/validation/test claims.
