# Causal & Internal-State Hallucination Probe (frontier)

**Label:** `experimental/frontier`. ASR = Whisper-`tiny` (offline, only cached model).
References `synthetic/silver` (Whisper-`small` on clean snippets). CER is post-hoc
evaluation only and is **never** a routing input. Stable tables are untouched; all outputs
live under `results/frontier/causal_hallucination_probe/`.

Module: `src/causal_hallucination_probe.py`. Issue: #855. Mode C (Frontier Exploration).

## The next question the prior frontier left open

`separation_tax` (findings under `results/frontier/separation_tax/`) closed the *acoustic*
loop on the separation tax: the low-overlap penalty is a heavy hallucination tail driven by
oracle-separated tracks with a long leading-silent region; a **reference-free
compression-ratio guard** ranks the catastrophic tracks at AUC = 1.0 and a guard-gated
trim/mixed-fallback router closes ~76% of the oracle gap (offline regret 0.239 → 0.058).

That result rests on two unexamined assumptions this probe attacks head-on:

1. **The detector is an OUTPUT signal.** Compression ratio is computed over the *full*
   decoded segment. By the time it inflates past 2.4, Whisper has *already emitted* the
   repetition loop. A deployed/streaming system has already shown the user garbage.
2. **The mechanism is a black box.** "Silence → repetition" is an acoustic correlation.
   We never looked *inside* Whisper to see *why* the decoder loops, or whether the
   encoder even agrees there is speech.

## A 3-second smoke test that reframed the hypothesis

Feeding Whisper-`tiny` a tone burst surrounded by silence (the catastrophic track shape)
reproduces the loop instantly: token 7322 × 224. The internal signals are *surprising*:

- `compression_ratio = 37.2` (the guard would fire),
- `no_speech_prob = 0.82` (the **encoder** is ~certain there is no speech), yet
- `avg_logprob = -0.065` (the **decoder** is highly *confident* in the repetition).

So the loop is **not a confidence collapse** — it is a *confident loop* under an input the
encoder itself flags as silent. That is an encoder/decoder **decoupling**, and it is the
mechanistic anchor of this study.

## Pre-registered research questions and hypotheses

**RQ-M (mechanism).** Is the catastrophic tail a *confident-loop* failure — high encoder
`no_speech_prob` coexisting with high decoder confidence (`avg_logprob` near 0) and low
token-id entropy (a locked repeat) — rather than high-entropy uncertainty?

- **H-M (confident loop / decoupling).** Catastrophic tracks (CER > 1) show
  mean(`no_speech_prob`) ≫ non-catastrophic **and** mean(`avg_logprob`) ≥ non-catastrophic
  **and** mean token-id entropy ≪ non-catastrophic. The encoder says "silence" while the
  decoder confidently repeats. *Kill:* if catastrophic tracks instead show low
  `avg_logprob` (a true uncertainty collapse), the confident-loop framing is wrong and we
  revert to a confidence-collapse story.

**RQ-D (detection latency).** Can an *internal-state* detector flag the catastrophe
**earlier in the causal stream** than the output compression-ratio?

- **H-D (early internal detection).** A token-repetition lock-in detector (fires once a
  single token repeats ≥ K times consecutively) fires at a **smaller emitted-token
  fraction** than the compression-ratio guard (which needs the full segment to inflate).
  *Honest scope:* detection **AUC** is not expected to beat compression-ratio (it is
  already AUC = 1.0 on this set); the contribution is **causal latency**, not ranking
  power. *Kill:* if lock-in latency ≥ CR latency, the internal signal adds no deployability.

**RQ-C (causal deployability — the bold one).** How much of the offline routing gain
survives a *causal* decision?

- **H-C (causal regret gap).** An offline router that uses the full-segment compression
  ratio reaches the separation_tax regret (~0.058). A *causal* router restricted to
  prefix signals at the moment of decision loses a measurable share of that gain, because
  the CR signal lags the emitted repetition. *Kill:* if causal routing recovers ≥ 80% of
  the offline gain, the offline result is directly deployable and H-C is moot.
- **H-C′ (internal-state closes the gap).** A causal router that **aborts to mixed** when
  the internal-state detector fires early recovers more of the offline gain than a
  causal-CR router does — i.e. internal-state detection is the deployable lever. *Kill:*
  if causal-internal ≤ causal-CR, the internal signal does not buy deployability.

## What is useful even if hypotheses fail

- A confident-loop negative (H-M killed) would itself be the first mechanistic
  characterization of the tax at the model level in this repo, and would redirect cures
  toward uncertainty-calibration.
- A causal-deployability negative (H-C/H-C′ killed: offline IS directly deployable) would
  be a strong, publishable "the offline router is streaming-safe" result.
- Either way we get the **latency ladder** — the ordering of detector fire-times
  (lock-in ≪ CR) — which is new evidence regardless of the deployability verdict.

## Design (reference-free; CER post-hoc only)

Reuse the `separation_tax` harness verbatim: `select_pairs`, `build_mixture` (oracle
separation), `compute_cer`, `repetition_count_from_text`. Per condition (pair × overlap ×
arm {mixed, sep1, sep2}) we decode greedy once and capture, per segment: `tokens` (ids),
`avg_logprob`, `no_speech_prob`, `compression_ratio`, `text`. From these we compute:

- **Mechanism vector** per track: `no_speech_prob`, `avg_logprob`, token-id entropy,
  dominant-token fraction, repetition lock-in index.
- **Causal latency**: the smallest emitted-token fraction at which (a) the CR guard fires
  (CR over the decoded prefix) and (b) the lock-in detector fires.
- **Causal router regret**: offline guard-gated regret vs causal-prefix regret vs
  causal-internal-abort regret, all measured against the same oracle (references used only
  to score regret, never to route).

## Labels, outputs, limitations

`experimental/frontier`. Outputs: `results/frontier/causal_hallucination_probe/`
(`probe_rows.csv`, `mechanism.csv`, `latency.csv`, `deployability.csv`, `FINDINGS.md`,
optional figure). Limitations: Whisper-`tiny`; oracle separation (upper bound); silver
references put a ~0.4 effective floor; catastrophic positives are rare (~1% of
conditions) so AUC/latency are encouraging-but-loosely-estimated; this is frontier
evidence, not a gold result. CER/reference never used as a routing input.
