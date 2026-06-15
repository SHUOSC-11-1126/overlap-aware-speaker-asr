# AudioDepth-Router Ablation

This ablation compares fixed routes, oracle best, and the current AudioDepth learned router output on the same synthetic split test scope.

Best row: `oracle_best` with routing CER `0.115181`.

AudioDepth rows:
- `audio_depth_cnn_analysis`: routing CER `0.436666`, accuracy `0.72`
- `audio_depth_cnn_deployable`: routing CER `0.436666`, accuracy `0.72`
- `audio_depth_cnn_logmel`: routing CER `0.436666`, accuracy `0.72`

Conclusion: this first pass is an `experimental/frontier` evidence stack. It should not be promoted into the stable baseline unless it beats router_v2 on matched rows with a larger controlled run.

Figure: `results/figures/audio_depth_router_ablation.png`