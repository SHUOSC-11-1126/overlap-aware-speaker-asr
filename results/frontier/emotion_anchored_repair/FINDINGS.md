# Emotion-Anchored ASR Repair — Findings

**Label:** `experimental/frontier`. ASR Whisper-`tiny`; LLM `deepseek-r1:7b` (local ollama, offline); references synthetic/silver; CER post-hoc only; no gold tables. Issue #833.

Cases: 12 curated separated tracks (2 clean, 6 hallucinated) — the same clean→hallucinated spread as #822, so naive vs anchored repair are compared on identical inputs.

## Pipelines (mean CER; lower is better)

- no-repair baseline: **0.9244**
- naive repair (#822): 1.0820
- emotion-anchored repair (this work): 1.1215
- CR-gated anchored (repair only when compression-ratio>2.4): 0.9244

## Hypotheses

- **H1 — less over-correction on clean tracks:** clean ΔCER naive **0.0000** vs anchored **-0.0714** (less negative = less damage). Verdict: **NOT supported**.
- **H2 — not worse on net:** pooled ΔCER naive -0.1576 vs anchored -0.1971. Verdict: **NOT supported**. (hallucinated-track recovery: naive -0.2107, anchored -0.1640.)
- **H3 — stance preserved:** mean LLM-read stance distance to the clean source, naive 0.3981 vs anchored 0.4821. Verdict: **NOT supported**.

## Deployable conclusion

**No-repair is best (0.924 CER) — both naive (1.082) and emotion-anchored (1.122) repair are net-harmful.** Anchoring the edit to the LLM-detected stance worsens it further, so #822's over-correction tax is ROBUST to the most natural fix: the small reasoning model rewrites/hallucinates regardless (e.g. emitting a literal placeholder, or substituting a proverb for the transcript). The deployable policy is to NOT run LLM repair in this setting; the CR-gated variant is identical to no-repair because the compression-ratio guard never fires on any of these 12 cases. A clean bounding negative result.

## Cost / benefit (repo-guard #833)

Per-pipeline LLM calls — naive: 12, anchored: 24 (read+repair), CR-gated anchored: 12 (read everywhere, repair only when gated). Anchored doubles the call budget; the CR-gated variant pays the read but spends repairs only where the cheap compression-ratio guard flags risk — weigh any accuracy gain above against this.

## Honest limitations

Small n; Whisper-`tiny`; synthetic oracle/leaky separation; local `deepseek-r1` reasoning model (temperature 0, still has variance); stance preservation is measured by the same LLM that does the anchoring, so H3 is self-consistent rather than externally validated; CER post-hoc. `experimental/frontier`, not a gold result.
