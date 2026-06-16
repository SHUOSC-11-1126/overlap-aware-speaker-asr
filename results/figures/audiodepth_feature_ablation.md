# AudioDepth vs Text Feature Ablation

- AudioDepth independent value: gate accuracy `0.758621`, false-safe rate `0.034483`.
- text-only CER: `0.64352`
- two-stage CER: `0.64352`
- two-stage text-probe reduction: `0.016667`
- Conclusion: AudioDepth is most meaningful as a pre-ASR acoustic gate; text features remain the stronger posterior routing signal.
