# Prosody-grounded LLM × ASR critic: judge dominated by compression-ratio, repair over-corrects — Findings

**Label:** `experimental/frontier`. ASR Whisper-`tiny`; references synthetic/silver; LLM = local
**deepseek-r1:7b via ollama** (fully offline, weights on disk); separation = cross-talk leakage
(α=0.15). CER is post-hoc; the LLM never sees the reference. No gold tables touched. Outputs in
`results/frontier/llm_asr_critic/`. Reproduce: `python -m src.llm_asr_critic --pairs 8 --max-cases 16`
(curates a balanced clean+hallucinated set, then runs a JUDGE pass and a separate REPAIR pass per case).

## Question and design

Direction B of the emotion/LLM frontier, grounded in 2025/26 work (see `docs/emotion_frontier.md`
References): generative error correction (GER), the documented weak prosody perception of speech-LLMs
(so we inject **explicit** prosodic + lexical-emotion cues as text), and the over-correction failure
mode. Following code-tape's **generation-evaluation separation**, the *repairer* and the *judge* are
separate roles / separate LLM calls. Two falsifiable claims:

- **C1 (QE):** the judge's reference-free quality score predicts true CER.
- **C2 (repair):** GER reduces CER on separation-induced hallucination without harming clean tracks.

## Result — both claims fail against the cheap baseline

**C1: the LLM judge is a real but WEAKER QE signal than the free compression-ratio signal.**

| reference-free QE signal | correlation with CER | cost |
|---|---:|---|
| Whisper compression-ratio (continuous) | **+0.737** | free (already computed) |
| deepseek-r1:7b judge score | −0.409 | ~10 s/call |

The judge does trend the right way (clean cases score highest: CER 0.23→1.0, 0.10→0.7) but is harsh and
compressed on disfluent ASR (most cases collapse to 0.2), and the cheap compression-ratio signal tracks
CER **almost twice as strongly** (|0.74| vs |0.41|). `qe_winner = compression_ratio`. The expensive LLM
judge does not justify its cost as a quality estimator here.

**C2: GER repair net-harms CER and over-corrects clean text; no reference-free gate rescues it.**

| repair policy | mean CER (16 cases) |
|---|---:|
| no repair (baseline) | **0.951** |
| naive LLM repair (always) | 0.983 (worse) |
| compression-ratio-gated repair (CR>2.4) | 0.951 (gate never fires — CR<1 here) |
| judge-gated repair (score<0.5) | 0.992 (worse) |

Per-class: on **clean** tracks repair *hurts* (mean CER reduction **−0.25**; e.g. 0.10→0.60 — textbook
over-correction in a well-posed region), on **hallucinated** tracks it is net-neutral (+0.01: a few
wins like 1.45→0.82, offset by losses like 1.36→1.73). Gating cannot save it: the absolute
compression-ratio guard never fires (these separation errors are substitution/deletion, not the
repetition type that inflates CR > 2.4), and judge-gating still applies the unreliable repair.

## Synthesis

For this offline, small-model, overlapping-speech setting, a local-7B LLM × ASR critic **adds cost
without winning**: as a quality estimator it is dominated by the free compression-ratio signal, and as
a repairer it over-corrects and net-harms CER. This is the same "simple reference-free signal beats the
fancier approach" motif as finding #13 (gate selector) — now for LLM-as-judge and GER. The deployable
cure for the separation-hallucination tail remains input-side gating / routing (findings #11–#13), and
the reference-free quality signal of choice remains compression-ratio, not an LLM judge. The 2026
literature's over-correction warning reproduces here even outside ill-posed regions.

What would change the verdict (honest scope): a larger/instruct (non-reasoning) LLM, true N-best GER
input (we feed only 1-best), an edit-distance-bounded acceptance gate, or real human emotion/quality
labels. These are the next steps, not claims of this experiment.

## Honest limitations

n=16 curated cases (8 hallucinated, 2 strictly clean, rest medium) — small, so magnitudes are
indicative, not precise; the *directions* (CR > judge for QE; repair net-harm + clean over-correction)
are the robust claims. deepseek-r1:7b is a reasoning model (slow, ~10–40 s/call) used greedily; prompts
are fixed, not optimized; 1-best input only. The critic's pure logic (think-stripping, score/repair
parsing, over-correction fallback, QE/gating summary) is unit-tested without ollama (17 tests) via an
injected fake LLM. `experimental/frontier`. Artifacts: `critic_curve.csv` (16 rows incl. hyp/repaired),
`critic_summary.json`, `llm_asr_critic.png`.
