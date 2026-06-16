# Risk-Guarded AudioDepth Gate

- Stage 29 calibrated false-safe rate: `0.183333`
- Stage 29 calibrated CER: `0.53316`

| tier | CER | false-safe bypass | selected mixed high-error | text-probe reduction | direct bypass | review rate | note |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| aggressive | `0.537082` | `0.0` | `12` | `0.65` | `0.65` | `0.316667` | safe_frontier_policy |
| balanced | `0.529082` | `0.0` | `12` | `0.416667` | `0.416667` | `0.316667` | safe_frontier_policy |
| conservative | `0.529082` | `0.0` | `12` | `0.416667` | `0.416667` | `0.316667` | safe_frontier_policy |

- false-safe <= 0.10 and CER < router_v2 exists: `yes`
- false-safe <= 0.05 policy exists: `yes`
- Here false-safe means an AudioDepth direct bypass selected mixed without Stage-2 review even though the offline minimum route CER is high.
- Risk guarding lowers unsafe bypasses by sending high-risk or review-like samples to Stage-2 text routing / review instead of trusting confidence alone.
- It can still leave selected mixed high-error cases after Stage-2 fallback; those are tracked separately and should be treated as review policy risk, not acoustic-gate bypass risk.
- It does sacrifice some direct bypass capacity under conservative settings; the balanced setting keeps a useful probe-reduction margin while preserving a CER advantage over router_v2.
- Deployment conclusion: this supports AudioDepth as a safety-aware acoustic triage module, not as a standalone production router.
- Safety wording: results are experimental/frontier and controlled_v2 references remain silver_plus_unverified; do not claim real-meeting generalization.
