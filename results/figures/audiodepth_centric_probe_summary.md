# AudioDepth-Centric Embedding Probe

- labelled maps: `100`
- models: `cnn,resnet`
- no large AST dependency was used in this stage

Best rows:
- `resnet` `route_gap_bucket` accuracy `0.793103` macro-F1 `0.404444` separability `-0.075729`
- `cnn` `route_gap_bucket` accuracy `0.689655` macro-F1 `0.343578` separability `-0.00442`
- `resnet` `oracle_route` accuracy `0.655172` macro-F1 `0.618421` separability `0.228582`
- `cnn` `oracle_route` accuracy `0.62069` macro-F1 `0.589447` separability `0.13937`
