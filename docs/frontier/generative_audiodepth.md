# Generative AudioDepth: Promptable Acoustic Structure-Map Generation

Status: `experimental/frontier`.

Decision after the first executable pass: **keep as an interpretable auxiliary
experiment**, not yet a major replacement line for balanced AudioDepth routing.

## Motivation

Existing AudioDepth v2 builds handcrafted mixed-only acoustic channels and uses
them for route selection, confidence, and safety triage. Generative AudioDepth
tests a more ambitious framing:

```text
mixed spectrogram + task token -> acoustic structure map or route-risk vector
```

The inspiration is the vision-side reformulation of perception tasks as image
generation. In this ASR setting, the generated outputs are:

- overlap maps;
- speaker dominance / acoustic-depth maps;
- uncertainty maps;
- route-regret vectors;
- review-risk vectors.

This is inspiration, not a direct reproduction of a visual model.

## Data Sources

The first pass reuses only existing branch artifacts:

- `results/tables/controlled_v2_manifest.csv`;
- `results/tables/controlled_v2_real_whisper_cer.csv`;
- `results/tables/audio_depth_v2_map_metadata.csv`;
- `results/tables/audiodepth_v2_metadata.csv`;
- `results/tables/controlled_v2_route_gap_filtered.csv`;
- Stage-2 review and safety audit outputs for review-risk interpretation.

The resulting dataset contains 60 usable samples and 300 task rows:

- 60 `OVERLAP_MAP`;
- 60 `DOMINANCE_MAP`;
- 60 `UNCERTAINTY_MAP`;
- 60 `ROUTE_REGRET`;
- 60 `REVIEW_RISK`.

See `results/figures/generative_audiodepth_repo_input_audit.md`.

## Leakage Boundary

Teacher maps may use source tracks. The deployable student/prototype is
mixed-only:

- teacher: source-track-derived overlap/dominance maps;
- student input: mixed audio, mixed logmel, or deployable mixed-only AudioDepth
  metadata;
- route regret: sample-level real-Whisper CER vector;
- review risk: Stage-2-style heuristic target.

No local CER map is claimed. Route regret remains sample-level.

## First-Pass Results

The source/counterfactual-disjoint split produced:

- train: 42 samples;
- validation: 9 samples;
- test: 9 samples.

No source/counterfactual group leakage was detected.

### Map Generation

| model | map MAE |
|---|---:|
| unconditioned prototype | 0.246685 |
| promptable prototype | 0.241263 |

The promptable generator is slightly better than a global unconditioned map
prototype, but the margin is small. This is a weak positive signal, not a strong
modeling result.

### Route Regret

| policy | regret MAE | Spearman | route accuracy | selected CER | false-safe | review recall |
|---|---:|---:|---:|---:|---:|---:|
| no-cost regret | 0.077426 | 0.888212 | 0.777778 | 0.671608 | 4 | 1.0 |
| cost-aware regret | 0.077426 | 0.888212 | 0.777778 | 0.671608 | 4 | 1.0 |

Route-regret prediction has a useful ranking signal, but it still leaves
false-safe mixed selections.

### Downstream Routing

| model | selected CER | oracle gap | route accuracy | false-safe |
|---|---:|---:|---:|---:|
| fixed mixed | 0.739509 | 0.117901 | 0.777778 | 6 |
| fixed separated | 0.840462 | 0.218854 | 0.222222 | 0 |
| fixed cleaned | 0.840462 | 0.218854 | 0.0 | 0 |
| generative regret | 0.671608 | 0.05 | 0.777778 | 4 |
| oracle | 0.621608 | 0.0 | 1.0 | 4 |

Generative regret improves over fixed mixed on this test split, but it is still
not a safety-complete route policy.

## Counterfactual Limitation

The controlled v2 data does not provide enough exact same-source
counterfactual pairs for a strong monotonicity claim. The current
counterfactual output is proxy-only:

- 20 proxy pairs;
- 11 monotonic overlap-proxy pairs;
- 20 proxy-only pairs.

This is a diagnostic, not proof of learned acoustic structure.

## Interpretation

Positive finding:

- Promptable map generation produces a small map-MAE improvement over an
  unconditioned map prototype.
- Route-regret prediction shows non-trivial ranking signal and improves
  selected-route CER over fixed mixed on the current test split.

Negative finding:

- The promptable map advantage is small.
- False-safe mixed selections remain.
- Counterfactual consistency is currently proxy-only.
- The first pass is a deterministic prototype, not a trained U-Net or
  transformer.

## Next Step

Continue this line as an interpretable auxiliary experiment. The next meaningful
upgrade is not a large model; it is a stricter data design:

1. Build exact same-source counterfactual scenes.
2. Train a small U-Net only after exact counterfactual splits exist.
3. Optimize review-risk recall and false-safe reduction before claiming routing
   improvement.
4. Keep route regret sample-level unless reliable window-level CER labels are
   created.
