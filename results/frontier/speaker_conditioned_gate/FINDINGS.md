# Speaker-conditioned gate: curing babble where spectral gating cannot — Findings

**Label:** `experimental/frontier`. ASR Whisper-`tiny`; references synthetic/silver; speaker
embedder = Resemblyzer GE2E (256-d, pretrained, **weights ship in the pip wheel so it runs fully
offline**); CER post-hoc only, never a gate input. No gold tables touched; outputs in
`results/frontier/speaker_conditioned_gate/`. Grid: 8 pairs × 2 low overlaps × 3 noise types × 3
SNR = 144 conditions (16 separated-track samples/cell). Reproduce:
`pip install -r requirements-frontier.txt` then
`python -m src.speaker_conditioned_gate --pairs 8 --types babble,white,pink`.

## Question (acting on the noise-robust-gate synthesis)

The noise-robust-gate study showed a spectral-flatness gate recovers the separation-hallucination
cure under broadband noise but **fails under babble** — the residual is speech-like, so flatness
carries no signal (target-vs-residual AUC 0.56; a cheap mel-centroid embedding 0.52 ≈ chance). The
synthesis was that babble needs *speaker identity*. An earlier turn wrongly concluded a trained
speaker model was out of reach offline. It is not: Resemblyzer's GE2E encoder loads in 0.02 s with
no network. So: **can a real speaker embedding crop babble residual where flatness cannot?**

## Feature level: yes, decisively

Target-vs-residual window separability (cosine to a reference embedding estimated, reference-free,
from the track's top-energy windows):

| noise | flatness AUC | speaker-embedding AUC |
|---|---:|---:|
| white | 1.00 | 1.00 |
| pink | 0.91 | 1.00 |
| babble (5 dB) | 0.56 | **0.95** |

And it degrades gracefully with babble SNR: AUC **1.00 / 0.95 / 0.81** at 10 / 5 / 0 dB. The
speaker embedding sees what flatness is blind to.

## CER level: a real cure at moderate babble, with honest edges

Mean separated CER by noise type × SNR (16 samples/cell):

| noise | SNR | raw sep | flatness gate | **speaker gate** | spk vs sep | spk vs flatness | tail sep → spk |
|---|---:|---:|---:|---:|---:|---:|---:|
| babble | 10 dB | 1.634 | 0.803 | **0.669** | +0.964 | +0.134 | 0.375 → **0.000** |
| babble | 5 dB | 1.518 | 1.975 | **1.271** | +0.247 | +0.704 | 0.375 → 0.125 |
| babble | 0 dB | 2.930 | **1.407** | 3.159 | −0.229 | −1.752 | 0.562 → 0.500 |
| white | 0–10 dB | 1.418 | **1.222** | 1.408 | +0.010 | −0.186 | 0.083 → 0.062 |
| pink | 0–10 dB | 0.682 | 0.681 | 0.886 | −0.204 | −0.205 | 0.042 → 0.042 |

What is true, and what is not:

1. **At moderate babble (5–10 dB) the speaker gate beats both raw separation and the flatness
   gate.** At 10 dB it cuts CER 1.634 → 0.669 and **eliminates the catastrophic tail (0.375 →
   0.000)** — the exact failure the flatness gate could not touch. This is the headline win.

2. **At 0 dB babble it fails** (3.159, worse than raw sep). The discrimination signal is still
   present (AUC 0.81), but when babble power equals speech power there is little clean target left
   to recover, and any mis-crop only adds deletions. The gate helps when a recoverable target
   exists; at 0 dB nothing does. Pooled over all babble SNRs the flatness gate (1.395) therefore
   still edges the speaker gate (1.700) — dragged down by the 0 dB cell — even though the speaker
   gate **halves the pooled babble catastrophic tail (0.438 → 0.208)**.

3. **On non-babble noise the speaker gate is neutral-to-harmful** (white ≈ sep; pink −0.204). It
   over-crops when the residual is not speech-like. It is a *complementary* tool, not a replacement.

## Synthesis: the deployable answer is gate *selection*, not one gate

No single gate dominates: flatness for broadband noise, speaker-conditioning for moderate babble,
neither at 0 dB. The right system is reference-free **selection** among {no gate, flatness gate,
speaker gate} keyed on an observable signal — and the residual region's own spectral flatness is
exactly that signal (high → broadband → flatness gate; low → speech-like → speaker gate). This is
the project's reference-free-router thesis applied at the gate level, and it is the concrete next
build. The speaker-profile / voiceprint frontier is now load-bearing: this is the first place in
the project where a real speaker embedding produces a measurable ASR-CER win (babble 10 dB,
1.63 → 0.67), not just a diagnostic risk score.

## Honest limitations

Whisper-`tiny`; silver references; synthetic oracle separation; synthetic noise (white/pink/babble
from the project's own snippets — real babble differs). n = 16/cell with heavy CER tails, so
per-cell point estimates are high-variance; the robust claims are the *direction* (speaker > both
at 5–10 dB babble; speaker < flatness at 0 dB; speaker harmful on pink) and the *tail* numbers, not
the exact means. Adds a real dependency (Resemblyzer, optional, in `requirements-frontier.txt`); the
gate's pure logic is unit-tested without it via an injected embedder. The 0 dB failure and the
no-single-winner result are reported as-is — this is a complementary cure with a clear operating
range, not a universal one. `experimental/frontier`, not a gold result. Artifacts:
`speaker_gate_curve.csv` (144 rows), `speaker_gate_summary.json`, `speaker_gate.png`.
