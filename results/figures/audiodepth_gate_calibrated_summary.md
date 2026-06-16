# AudioDepth Gate Calibration

- model path: `models/audiodepth_gate_calibrated.pt`
- held-out accuracy: `0.724138`
- held-out macro-F1: `0.475`
- easy_mixed recall: `0.4`
- separation_helpful recall: `0.8`
- best threshold by CER: `0.3` CER `0.53316` text-probe reduction `0.716667`
- Calibration separates route-action labels from risk flags, so review risk no longer swallows every high-CER separated-helpful case.
