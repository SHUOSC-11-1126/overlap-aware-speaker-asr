# Error Profile Decomposition — Findings

## Label: experimental/frontier (Issue #865)

## Results (25 conditions: 5 pairs × 5 overlap ratios, separated tracks)

### Error Type Distribution

| Model | CER | Substitution | Deletion | Insertion | Halluc-dominated |
|-------|-----|-------------|----------|-----------|-----------------|
| **Base** | 0.198 | **70.0%** | 10.0% | 20.0% | 20% of samples |
| **Tiny** | 0.465 | **75.7%** | 12.3% | 12.0% | 0% of samples |

### H1 REJECTED ❌
Base has a HIGHER insertion fraction (0.20) than tiny (0.12). Base makes
proportionally more insertions, not fewer. This is surprising — it suggests
base's errors include some hallucination-like insertions despite being
generally more accurate.

### H2 PARTIALLY CONFIRMED ⚠️
- Base IS substitution-dominated (70% > 20%) ✅
- Tiny is ALSO substitution-dominated (75.7% > 12%) ❌
  (H2 expected tiny to be insertion-dominated)

Both models are primarily substitution-dominated. The difference is in
absolute count: base makes fewer total errors, but the TYPE distribution
is similar.

### H3 CONFIRMED for base ⚠️
Base's error profile is COMPLETELY CONSTANT across all overlap ratios
(70/10/20 at every ratio). This confirms #859's finding: base is
completely unaffected by overlap conditions.

Tiny's profile is ALSO constant (75.7/12.3/12). This is because both
models run on the separated oracle tracks (clean single-speaker audio),
so overlap ratio doesn't directly affect the input.

### Key Insight

The error profiles are remarkably similar between models — both are
~70-76% substitution, ~10-12% deletion, ~12-20% insertion. The dramatic
CER difference (0.198 vs 0.465) comes from the TOTAL error count, not
from different error types. Base simply makes fewer of the same kinds of
errors.

## Files
- profile_curve.csv — raw per-condition data
- profile_summary.json — full analysis with hypothesis verdicts
- error_profile_by_model.png — stacked area visualization
