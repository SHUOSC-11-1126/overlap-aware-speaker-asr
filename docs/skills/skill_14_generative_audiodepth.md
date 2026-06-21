# Generative AudioDepth: Promptable Acoustic Scene Maps for Overlap-Aware ASR Routing

Status: `experimental/frontier`.

This skill extends AudioDepth from handcrafted mixed-only acoustic channels into
a promptable acoustic structure-map generation problem. It is inspired by the
vision-side framing where depth, segmentation, normals, and related perception
tasks can be treated as conditional image generation tasks. This is inspiration,
not a direct reproduction of any visual model.

## 1. Difference From Existing AudioDepth

Existing AudioDepth in this branch uses:

- handcrafted depth-like channels;
- mixed-only deployable proxies;
- Stage-1 classification / triage;
- route and review policies built on AudioDepth summary features.

Generative AudioDepth asks a different question: can a mixed-audio-only student
generate structured acoustic maps that become a reusable interface for routing,
safety triage, visualization, and future local separation support?

The intended model family is:

- shared encoder-decoder;
- task-conditioned map generation;
- one model generating multiple acoustic perception outputs;
- downstream router or review guard consuming generated maps and vector heads.

The router is only one downstream user of the generated acoustic scene maps.

## 2. Difference From RGB-D Classification

This is not:

```text
logmel + depth channel -> classifier
```

The target formulation is:

```text
mixed spectrogram + task token -> structured acoustic map or vector
```

Task tokens include:

- `<OVERLAP_MAP>`;
- `<DOMINANCE_MAP>`;
- `<UNCERTAINTY_MAP>`;
- `<ROUTE_REGRET>`;
- `<REVIEW_RISK>`.

The first implementation is dependency-light and deterministic. It establishes
the dataset, leakage boundaries, task interface, and baseline metrics before
any larger neural generator is justified.

## 3. Research Hypotheses

H1: Generated structure maps may learn a more interpretable overlap structure
than direct route classification.

H2: Multi-task map generation may improve source-disjoint and unseen-overlap
generalization over direct classifiers.

H3: Oracle teacher maps derived from source tracks can be distilled into a
deployable mixed-only student.

H4: Route-regret prediction is a better target than route classification for
expressing route gap, ambiguity, review-needed status, and cost-aware routing.

## 4. Evidence Boundaries

The following evidence types must remain separate:

| Evidence Type | Meaning | Deployable? |
|---|---|---|
| analysis-only teacher map | Built with source tracks or oracle structure | No |
| mixed-only student map | Generated from mixed audio / mixed logmel only | Potentially |
| controlled silver-plus result | Controlled route-sensitive benchmark evidence | No broad deployment claim |
| real Whisper-derived route target | CER-derived sample-level target for analysis | Evaluation target only |
| diagnostic visualization | Human-readable map comparison | Not a routing claim |

Route regret remains sample-level unless reliable window-level CER exists. A
scalar regret may be broadcast for visualization only when explicitly labeled
`global_scalar_broadcast`; it must not be described as a local route map.

## 5. First-Pass Success Criteria

The first pass should answer:

- Does promptable map generation reduce map MAE versus an unconditioned map
  prototype?
- Does route-regret prediction show non-trivial MAE / rank correlation?
- Does direct classification remain stronger than map generation?
- Do review-risk heuristics recall unsafe or ambiguous cases without increasing
  false-safe mixed selections?
- Is student/deployable inference strictly mixed-only?

Negative findings are valid. If direct classification is stronger or generated
maps are only visually pleasing, the conclusion should say so plainly.
