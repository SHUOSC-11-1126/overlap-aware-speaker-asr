# AudioDepth-Router Summary

## What was attempted
AudioDepth-Router tests whether a lightweight learned router can choose between mixed, separated, and cleaned ASR outputs from depth-augmented spectrogram maps.

## RGB-D inspiration
The experiment treats overlapping speech as time-frequency occlusion. A log-mel spectrogram is augmented with overlap/depth and uncertainty/dominance channels, mirroring RGB-D image recognition where depth helps explain occluded structure.

## Dataset used
The run uses the synthetic split CER table as `synthetic/silver` evidence. Gold cases remain sanity-only and are not used as training data.

## Deployable vs analysis-only
`deployable` maps use only mixed audio. `analysis` maps may use separated tracks and must be read as `analysis_only`, not a deployable claim.

## Classification result
Mode `deployable` achieved accuracy `0.7200` and macro-F1 `0.2791` on the held-out synthetic test split. Model status: `cnn`.

## Routing CER result
AudioDepth routing average CER was `0.436666` on `50` test samples.

## Comparison
- `audio_depth_cnn_deployable`: routing_average_cer `0.436666`
- `fixed_mixed`: routing_average_cer `0.44473`
- `fixed_separated`: routing_average_cer `0.436666`
- `fixed_cleaned`: routing_average_cer `0.185238`
- `oracle_best`: routing_average_cer `0.115181`
- `v1_overlap_only`: routing_average_cer `0.36135`
- `v2_full_features`: routing_average_cer `0.335326`
- router_v2: v2_full_features routing_average_cer `0.335326` on the matched TEST scope.

## Did AudioDepth help?
This first frontier pass is useful even when it underperforms: it isolates how much local audio-visual structure can explain route labels without text-level instability features.

## Failure modes
- small synthetic data may be insufficient
- overlap proxy may be too weak
- oracle labels may be noisy
- text-level instability features remain important
- audio visual features alone may not capture ASR hallucination risk

## What should happen next
Run the same pipeline with a larger synthetic sweep, add explicit log-mel-only comparison, and compare against router_v2 on exactly matched synthetic split rows.