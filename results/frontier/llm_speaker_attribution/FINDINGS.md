# LLM Speaker-Attribution Repair — Findings

**Label:** `experimental/frontier`. Reference-free re-attribution by the LLM's cached (#831) per-track valence; truth from silver con/pro labels; attributed CER post-hoc. Issue #838.

n = 25 samples. NB: cpCER is permutation-invariant (swap-blind), so this uses fixed-assignment attribution accuracy + attributed CER instead.

## Can the LLM tell con from pro by emotion?

- **valence rank-AUC (pro vs con): 0.2160** — discriminative strength 0.7840 (0.5 = no signal; far from 0.5 either way = strong signal).
- naive reference-free rule (lower valence → con) accuracy: **0.0800** (abstain 0.0800).
- **sign-calibrated ceiling accuracy: 0.9200** (if the valence→role direction is known).
- detected direction: **con_higher_valence**; stance-disagreement rate 0.6000 (coarse 3-way stance mostly cannot separate roles).
- a separator that swaps at rate 0.5000 has accuracy 0.5000.

## Hypotheses

- **H1 — valence discriminates con/pro (AUC away from 0.5):** **SUPPORTED**.
- **H2 — naive (fixed-prior) reference-free rule beats chance (>0.6):** **NOT supported**.
- **H2b — sign-CALIBRATED rule beats chance (>0.6):** **SUPPORTED**.

## Attributed CER (fixed assignment; lower better)

- oracle (correct attribution): 0.2809
- LLM naive re-attribution: 1.1736

## Conclusion

**The signal exists but its SIGN is the catch.** The LLM's per-track valence is strongly discriminative of speaker role (AUC 0.2160, strength 0.7840) — but in the COUNTERINTUITIVE direction: the pro/支持 snippets read *more negative* than the con/反对 ones. So the naive reference-free prior (lower valence → con) is exactly backwards and collapses to 0.0800 accuracy (attributed CER 1.1736 ≫ oracle 0.2809), while a sign-calibrated rule would reach 0.9200. The reference-free limitation is therefore not the *signal* but the *sign*: a handful of labels to fix the valence→role direction would turn this into a usable attribution-repair cue that beats a swapping separator. A nuanced result — affect carries who-said-what information, but not its polarity for free. (Extends #831: the LLM reads emotion, but the emotion→role mapping is dataset-specific.)

## Honest limitations

Small n; Whisper-`tiny`; oracle separation with a *modelled* swap rate (no real swapping separator); con/pro discriminated only by the cached single-axis valence, not a full LLM role-classification call (which could read the sign from context); attributed CER is silver. `experimental/frontier`, not gold.
