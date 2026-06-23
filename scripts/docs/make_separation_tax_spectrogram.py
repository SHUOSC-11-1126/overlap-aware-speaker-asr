"""Generate a spectrogram visualization complementing fig5 (waveform).

While fig5 shows the time-domain amplitude (revealing the leading-silence
structure), fig6 shows the time-frequency content (revealing *what* Whisper
"sees" before it hallucinates). The leading-silence region in Speaker 2 is
spectrally empty — a blank canvas that Whisper's compression-seeking
attractor fills with confident token-id repetition.

Usage:
    .venv/bin/python scripts/docs/make_separation_tax_spectrogram.py
"""
from __future__ import annotations

import os
import numpy as np
import scipy.io.wavfile as wavfile
import scipy.signal as signal
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CON_PATH = os.path.join(REPO, "resources", "snippets", "con_006.wav")
PRO_PATH = os.path.join(REPO, "resources", "snippets", "pro_006.wav")
OUT_PATH = os.path.join(REPO, "results", "figures", "report", "fig6_separation_tax_spectrogram.png")


def load_mono(path: str) -> tuple[int, np.ndarray]:
    sr, data = wavfile.read(path)
    if data.ndim > 1:
        data = data.mean(axis=1)
    return sr, data.astype(np.float32)


def make_mix(con: np.ndarray, pro: np.ndarray, overlap_ratio: float):
    max_len = max(len(con), len(pro))
    con_p = np.zeros(max_len, dtype=np.float32)
    pro_p = np.zeros(max_len, dtype=np.float32)
    con_p[: len(con)] = con
    pro_p[: len(pro)] = pro
    offset = int((1.0 - overlap_ratio) * len(con))
    mixed = np.zeros(max_len, dtype=np.float32)
    mixed[: len(con)] += con_p[: len(con)]
    pro_len_in_mix = min(len(pro), max_len - offset)
    if pro_len_in_mix > 0:
        mixed[offset : offset + pro_len_in_mix] += pro_p[:pro_len_in_mix]
    spk1_track = np.zeros(max_len, dtype=np.float32)
    spk1_track[: len(con)] = con_p[: len(con)]
    spk2_track = np.zeros(max_len, dtype=np.float32)
    spk2_len = min(len(pro), max_len - offset)
    if spk2_len > 0:
        spk2_track[offset : offset + spk2_len] = pro_p[:spk2_len]
    return mixed, spk1_track, spk2_track


def plot_spectrogram(ax, data, sr, title, highlight_silence=None, silence_label=None):
    """Plot a log-frequency spectrogram."""
    nperseg = int(0.025 * sr)  # 25 ms window
    noverlap = int(0.010 * sr)  # 10 ms hop
    f, t_spec, Sxx = signal.spectrogram(
        data, fs=sr, nperseg=nperseg, noverlap=noverlap, mode="magnitude"
    )
    # Log-frequency axis
    Sxx_log = 10 * np.log10(Sxx + 1e-10)
    # Only show up to 8 kHz (speech-relevant band)
    f_mask = f <= 8000
    im = ax.pcolormesh(
        t_spec, f[f_mask] / 1000, Sxx_log[f_mask, :],
        shading="gouraud", cmap="magma", vmin=-60, vmax=0
    )
    ax.set_ylabel("Frequency (kHz)", fontsize=10)
    ax.set_title(title, fontsize=10, loc="left")
    ax.set_ylim(0, 8)
    if highlight_silence is not None:
        start, end = highlight_silence
        ax.axvspan(start, end, alpha=0.2, color="cyan",
                   label=silence_label or "silence")
        ax.legend(loc="upper right", fontsize=7, framealpha=0.8)
    return im


def main() -> None:
    sr, con = load_mono(CON_PATH)
    _, pro = load_mono(PRO_PATH)

    overlap_ratio = 0.05
    mixed, spk1, spk2 = make_mix(con, pro, overlap_ratio)

    offset_t = int((1.0 - overlap_ratio) * len(con)) / sr
    total_t = len(mixed) / sr

    fig, axes = plt.subplots(3, 1, figsize=(12, 9), gridspec_kw={"height_ratios": [1, 1, 1]})

    # Panel A: Mixed spectrogram
    plot_spectrogram(
        axes[0], mixed, sr,
        "(A) Mixed audio spectrogram — both speakers visible across full spectrum\n"
        "Whisper transcribes correctly: CER = 0.44"
    )
    axes[0].set_xlim(0, total_t)

    # Panel B: Speaker 1 spectrogram — speech then silence
    plot_spectrogram(
        axes[1], spk1, sr,
        "(B) Oracle-separated Speaker 1 — speech (0–2.1s) then SILENCE\n"
        "Whisper transcribes OK: CER = 0.44 (trailing silence is less harmful)",
        highlight_silence=(len(con) / sr, total_t),
        silence_label="trailing silence"
    )
    axes[1].set_xlim(0, total_t)

    # Panel C: Speaker 2 spectrogram — leading silence then speech
    plot_spectrogram(
        axes[2], spk2, sr,
        "(C) Oracle-separated Speaker 2 — LEADING SILENCE (0–2.0s) then speech\n"
        "Blank spectrogram triggers compression-seeking attractor: CER = 24.25, CR = 16.33",
        highlight_silence=(0, offset_t),
        silence_label="leading silence (hallucination trigger)"
    )
    axes[2].set_xlabel("Time (seconds)", fontsize=10)
    axes[2].set_xlim(0, total_t)

    plt.tight_layout()
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    fig.savefig(OUT_PATH, dpi=150, bbox_inches="tight")
    fig.savefig(OUT_PATH.replace(".png", ".pdf"), bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote: {OUT_PATH}")
    print(f"Wrote: {OUT_PATH.replace('.png', '.pdf')}")
    print(f"\n  Speaker 2 leading silence: {offset_t:.2f}s (spectrally empty → hallucination)")


if __name__ == "__main__":
    main()
