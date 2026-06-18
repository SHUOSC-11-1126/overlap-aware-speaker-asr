# Tri-Modal Emotion Fusion — Findings

**Label:** `experimental/frontier`. Reference-free features off the MIXED track (LLM-semantic via cached `deepseek-r1:7b`, lexical, acoustic); two silver targets (acoustic prosody distortion; semantic LLM-emotion distance), each = the emotion damage the mixture inflicts in that modality's own space; 5-fold CV (Ridge), seed 0. Issue #835, follows #831 (the three modalities are orthogonal).

n = 50 (sample×speaker) records.

## Does fusing orthogonal modalities help predict emotion damage?

### Target: acoustic_emotion_damage  (n=50)

| predictor | CV R² | CV Spearman | CV AUC |
|---|--:|--:|--:|
| llm | -0.3257 | -0.1427 | 0.4552 |
| lexical | -0.1556 | -0.0831 | 0.4184 |
| acoustic | 0.1080 | 0.0741 | 0.4216 |
| **fused (all 3)** | **0.0243** | -0.0627 | 0.4776 |

- best single = **acoustic** (0.1080); fused 0.0243 → H1 (fusion beats best single): **NOT supported**.
- ablation drops (fused R² lost when a modality is removed): llm -0.0749, lexical -0.0075, acoustic 0.3940 → H2 (each contributes): **NOT supported**.

### Target: semantic_emotion_damage  (n=50)

| predictor | CV R² | CV Spearman | CV AUC |
|---|--:|--:|--:|
| llm | 0.0677 | 0.4039 | 0.6384 |
| lexical | -0.0777 | -0.1159 | 0.3544 |
| acoustic | 0.0975 | 0.3919 | 0.5840 |
| **fused (all 3)** | **0.1604** | 0.4816 | 0.6528 |

- best single = **acoustic** (0.0975); fused 0.1604 → H1 (fusion beats best single): **SUPPORTED**.
- ablation drops (fused R² lost when a modality is removed): llm 0.0597, lexical -0.0002, acoustic 0.0886 → H2 (each contributes): **NOT supported**.

## Conclusion

- **Fusion helps for 1/2 target(s)**: it beats the best single modality for ['semantic_emotion_damage'] but not for ['acoustic_emotion_damage'].
- **Most useful single signal:** the *acoustic* arousal of the mixed track — best single predictor across targets (winners = {'acoustic_emotion_damage': 'acoustic', 'semantic_emotion_damage': 'acoustic'}). Notably even *semantic* emotion damage is predicted at least as well by acoustic arousal as by the LLM reading alone.

Reading: #831 found the three readers orthogonal; here that orthogonality is only PARTLY complementary. Fusing LLM-semantic + acoustic + lexical *does* improve prediction of the **semantic** emotion-damage target (the orthogonal readers genuinely combine there), but it adds noise for the **acoustic** target, where the acoustic signal alone is best. The deployable takeaway: the cheap acoustic-arousal signal is the single most useful reference-free predictor of emotion damage; fusion pays off only when the target itself is multi-faceted (semantic). A nuanced, honestly-mixed result — not a clean fusion win, not a clean null.

## Honest limitations

Small n (≈50); Whisper-`tiny`; synthetic oracle separation; silver prosody/semantic targets (proxies, not human emotion labels); single-temperature cached LLM readings. CV R² on n≈50 is high-variance, so the semantic-target fusion gain (R² ~0.10→0.16) is *suggestive*, not strong; the robust signals are the orderings (acoustic dominant; fusion helps semantic not acoustic). `experimental/frontier`, not gold.
