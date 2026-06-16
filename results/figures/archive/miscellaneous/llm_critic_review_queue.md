# LLM Critic Review Queue

This generated queue is qualitative only. It suggests which cases should receive the next critic-style review pass first.

| queue_order | case_id | label | review_priority | why_now | candidate_repair |
| --- | --- | --- | --- | --- | --- |
| 1 | HeavyOverlap | qualitative/demo | high | Risk flags plus swapped-profile uncertainty make this the strongest first review target. | Try repair separated output with cleaned transcript before treating the current transcript as final. |
| 2 | LightOverlap | qualitative/demo | high | Risk flags plus swapped-profile uncertainty make this the strongest first review target. | Try keep mixed output because separated looks risky before treating the current transcript as final. |
| 3 | MidOverlap | qualitative/demo | high | Risk flags plus swapped-profile uncertainty make this the strongest first review target. | Try keep mixed output because separated looks risky before treating the current transcript as final. |
| 4 | NoOverlap | qualitative/demo | high | Risk flags plus swapped-profile uncertainty make this the strongest first review target. | Try base separated output is stable enough before treating the current transcript as final. |
| 5 | OppositeOverlap | qualitative/demo | high | Risk flags plus swapped-profile uncertainty make this the strongest first review target. | Try repair separated output with cleaned transcript before treating the current transcript as final. |
