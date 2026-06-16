# AudioDepth v2 Feature Audit

- labelled samples: `100`
- mixed-vs-separated overlap proxy mean gap: `0.035352`
- conclusion: Current deployable proxies show usable but modest route signal.

Top correlations:
- `overlap_proxy_mean` vs `route_gap`: `-0.364112`
- `overlap_uncertainty_product` vs `route_gap`: `-0.324056`
- `overlap_proxy_std` vs `oracle_route_code`: `0.304518`
- `overlap_proxy_std` vs `separation_helpful`: `0.304518`
- `uncertainty_proxy_std` vs `oracle_route_code`: `0.187115`

Cleaned route note: the current labelled controlled_v2 slice has no cleaned oracle winner, so cleaned-specific signature cannot be proven yet.
