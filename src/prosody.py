"""Offline prosody / acoustic-emotion feature library (experimental/frontier).

The emotion frontier of this project needs to estimate *emotional* content of speech with NO
pretrained SER model and NO human emotion labels (both unavailable offline here). The defensible
substitute is acoustic PROSODY: the energy, pitch, and spectral cues that carry the arousal dimension
of emotion (loud/fast/bright = high arousal; quiet/flat/dark = low arousal). Valence (positive vs
negative) is acoustically hard and deliberately NOT claimed here.

Two design commitments make this usable as a research instrument:

1. **Gain invariance.** A separation artifact or an SNR change alters loudness; that is NOT an
   emotional change. So `prosody_distance(..., energy_invariant=True)` is built only from
   gain-invariant cues (pitch, energy *dynamics* in dB, spectral shape, voicing) and reports the raw
   loudness change separately as `gain_component_db`. This is the confound control the
   emotional-separation-tax study stands on: any measured "emotional distortion" cannot be just volume.

2. **Label-free reference.** Emotional change is always measured as a DISTANCE to a reference signal
   (e.g. the clean source track), never to a class label. The clean source's own prosody is the
   ground truth, exactly as the verified transcript is the ground truth for CER.

Everything is computed offline with numpy + librosa (already a project dep). No new dependency.

Labels: experimental/frontier. Pure feature math; unit-tested with synthetic signals.
"""
from __future__ import annotations

from typing import Any

import numpy as np

SR = 16000

# Per-feature normalization scales (typical human-speech spans) so heterogeneous prosodic features
# combine into one comparable distance. Chosen a priori from speech-science ranges, NOT tuned on any
# outcome. Only gain-INVARIANT features appear here; rms_mean (loudness) is handled separately.
_AROUSAL_FEATURES = {
    "f0_median": 120.0,     # Hz   (pitch height)
    "f0_iqr": 60.0,         # Hz   (pitch range / variability -> arousal)
    "voiced_frac": 0.5,     # ratio
    "rms_dyn_db": 18.0,     # dB   (energy dynamics -> arousal/emphasis)
    "centroid_mean": 1200.0,  # Hz (spectral brightness -> arousal/tension)
    "centroid_std": 600.0,    # Hz (brightness variability)
    "rolloff_mean": 2500.0,   # Hz
    "bandwidth_mean": 1500.0,  # Hz
    "zcr_mean": 0.12,         # ratio (noisiness/fricatives)
}


def _safe(x: float, default: float = 0.0) -> float:
    return float(x) if np.isfinite(x) else default


def prosodic_features(wav: np.ndarray, sr: int = SR, fmin: float = 65.0, fmax: float = 400.0) -> dict[str, float]:
    """Extract a fixed dict of prosodic / arousal-relevant features from a 1-D waveform. Robust to
    silence and to pitch-tracker dropouts (returns finite values throughout). F0 via librosa.pyin
    (voiced frames only); energy dynamics in dB; spectral shape via librosa spectral features."""
    import librosa

    x = np.asarray(wav, dtype=np.float32)
    out: dict[str, float] = {
        "f0_median": 0.0, "f0_iqr": 0.0, "voiced_frac": 0.0, "rms_mean": 0.0, "rms_dyn_db": 0.0,
        "centroid_mean": 0.0, "centroid_std": 0.0, "rolloff_mean": 0.0, "bandwidth_mean": 0.0, "zcr_mean": 0.0,
    }
    if x.size < 512 or float(np.max(np.abs(x))) < 1e-6:
        return out

    # Energy: mean level (gain-dependent) + dynamic range in dB (gain-INVARIANT).
    rms = librosa.feature.rms(y=x, frame_length=1024, hop_length=256)[0]
    rms = rms[np.isfinite(rms)]
    if rms.size:
        out["rms_mean"] = _safe(np.mean(rms))
        p5, p95 = np.percentile(rms, 5), np.percentile(rms, 95)
        out["rms_dyn_db"] = _safe(20.0 * np.log10((p95 + 1e-8) / (p5 + 1e-8)))

    # Spectral shape (gain-invariant).
    out["centroid_mean"] = _safe(np.mean(librosa.feature.spectral_centroid(y=x, sr=sr)))
    out["centroid_std"] = _safe(np.std(librosa.feature.spectral_centroid(y=x, sr=sr)))
    out["rolloff_mean"] = _safe(np.mean(librosa.feature.spectral_rolloff(y=x, sr=sr)))
    out["bandwidth_mean"] = _safe(np.mean(librosa.feature.spectral_bandwidth(y=x, sr=sr)))
    out["zcr_mean"] = _safe(np.mean(librosa.feature.zero_crossing_rate(y=x)))

    # Pitch (gain-invariant). pyin is the slow part; guarded for short/unvoiced input.
    try:
        f0, _, _ = librosa.pyin(x, sr=sr, fmin=fmin, fmax=fmax, frame_length=1024)
        voiced = f0[np.isfinite(f0)]
        out["voiced_frac"] = _safe(np.mean(np.isfinite(f0)))
        if voiced.size:
            out["f0_median"] = _safe(np.median(voiced))
            out["f0_iqr"] = _safe(np.percentile(voiced, 75) - np.percentile(voiced, 25))
    except Exception:
        pass  # leave pitch fields at 0.0; energy+spectral cues still carry arousal
    return out


def arousal_index(feat: dict[str, float]) -> float:
    """A documented, label-free arousal proxy (higher = more aroused): a weighted blend of energy
    dynamics, pitch range, pitch height, and spectral brightness, each on its a-priori scale. This is
    a RELATIVE index — meaningful only when comparing signals, never as an absolute emotion score."""
    return float(
        0.35 * feat.get("rms_dyn_db", 0.0) / _AROUSAL_FEATURES["rms_dyn_db"]
        + 0.25 * feat.get("f0_iqr", 0.0) / _AROUSAL_FEATURES["f0_iqr"]
        + 0.20 * feat.get("f0_median", 0.0) / _AROUSAL_FEATURES["f0_median"]
        + 0.20 * feat.get("centroid_mean", 0.0) / _AROUSAL_FEATURES["centroid_mean"]
    )


def prosody_distance(ref: dict[str, float], hyp: dict[str, float], energy_invariant: bool = True) -> dict[str, float]:
    """Distance between two prosody feature dicts. With `energy_invariant=True` (default) the headline
    `emotional_distortion` is a normalized RMS difference over GAIN-INVARIANT arousal features only, so
    pure loudness changes do not count as emotional change — they are reported as `gain_component_db`.

    Returns:
      emotional_distortion  normalized RMS distance over the arousal-feature subspace (>=0; 0 = identical)
      arousal_distance      |arousal_index(ref) - arousal_index(hyp)| (signed magnitude of arousal change)
      gain_component_db     |level difference| in dB (loudness change, excluded from emotional_distortion)
    """
    diffs = []
    for k, scale in _AROUSAL_FEATURES.items():
        diffs.append((ref.get(k, 0.0) - hyp.get(k, 0.0)) / scale)
    emotional = float(np.sqrt(np.mean(np.square(diffs)))) if diffs else 0.0

    rms_r, rms_h = ref.get("rms_mean", 0.0), hyp.get("rms_mean", 0.0)
    gain_db = abs(20.0 * np.log10((rms_r + 1e-8) / (rms_h + 1e-8))) if (rms_r > 0 and rms_h > 0) else 0.0

    out = {
        "emotional_distortion": emotional,
        "arousal_distance": abs(arousal_index(ref) - arousal_index(hyp)),
        "gain_component_db": float(gain_db),
    }
    if not energy_invariant:
        # Optional: fold loudness back in (NOT the default; documented escape hatch).
        out["emotional_distortion"] = float(np.sqrt(emotional ** 2 + (gain_db / 18.0) ** 2))
    return out
