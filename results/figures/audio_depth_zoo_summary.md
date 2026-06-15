# AudioDepth Zoo Plot Summary

The ablation matrix and family comparison are meant to keep the frontier story honest: what helped, what barely moved, and what still needs hybrid signal.

Best frontier model: `mlp_handcrafted` with CER `0.166381`.

Matched router_v2 CER: `0.335326`.
Oracle upper bound CER: `0.115181`.
Hybrid late fusion CER: `0.176381`.
Best confidence cascade threshold: `0.9` with CER `0.165545`.

If the hybrid rows do not beat the pure depth CNNs, that still tells us something useful: transcript-instability features may be necessary at routing time, not just helpful as a late add-on.
