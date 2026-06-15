# AudioDepth Real-ASR Stratified Summary

- Samples: `20`
- Transcript rows: `100`
- Total runtime sec: `109.2177`
- `oracle_real`: CER `0.67461`
- `router_v2_real`: CER `0.69641`
- `hybrid_late_fusion_v2_real`: CER `0.69641`
- `fixed_separated_real`: CER `0.702363`
- `fixed_cleaned_real`: CER `0.702363`
- `fixed_mixed_real`: CER `0.709019`

The stratified expansion still does not show `hybrid_late_fusion_v2` beating router_v2; both are tied on this run. The evidence remains real Whisper ASR against synthetic/silver references, not gold validation.
