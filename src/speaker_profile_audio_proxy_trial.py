from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from .config import PROJECT_ROOT, load_config


AUDIO_PROXY_COLUMNS = [
    "case_id",
    "hypothesis_source",
    "best_audio_alignment",
    "direct_audio_score",
    "swapped_audio_score",
    "audio_confidence_gap",
    "result_label",
    "observation",
]


def cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    left_norm = float(np.linalg.norm(left))
    right_norm = float(np.linalg.norm(right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return round(float(np.dot(left, right) / (left_norm * right_norm)), 6)


def load_waveform(path: Path) -> tuple[int, np.ndarray]:
    from scipy.io import wavfile

    sample_rate, waveform = wavfile.read(path)
    waveform = np.asarray(waveform, dtype=np.float64)
    if waveform.ndim > 1:
        waveform = waveform.mean(axis=1)
    peak = float(np.max(np.abs(waveform))) if waveform.size else 0.0
    if peak > 0.0:
        waveform = waveform / peak
    return int(sample_rate), waveform


def extract_audio_profile_vector(path: Path) -> np.ndarray:
    sample_rate, waveform = load_waveform(path)
    if waveform.size == 0:
        return np.zeros(9, dtype=np.float64)

    duration = waveform.size / float(sample_rate)
    rms = float(np.sqrt(np.mean(np.square(waveform))))
    zero_crossing_rate = float(np.mean(np.abs(np.diff(np.signbit(waveform)))))

    spectrum = np.abs(np.fft.rfft(waveform))
    freqs = np.fft.rfftfreq(waveform.size, d=1.0 / sample_rate)
    spectral_sum = float(np.sum(spectrum))
    if spectral_sum == 0.0:
        centroid = 0.0
        rolloff = 0.0
        band_energies = np.zeros(4, dtype=np.float64)
    else:
        centroid = float(np.sum(freqs * spectrum) / spectral_sum)
        cumulative = np.cumsum(spectrum)
        rolloff_idx = int(np.searchsorted(cumulative, 0.85 * cumulative[-1], side="left"))
        rolloff = float(freqs[min(rolloff_idx, len(freqs) - 1)])
        band_edges = [0.0, 300.0, 1000.0, 3000.0, 8000.0]
        energy_values: list[float] = []
        power = np.square(spectrum)
        total_power = float(np.sum(power)) or 1.0
        for lower, upper in zip(band_edges[:-1], band_edges[1:]):
            mask = (freqs >= lower) & (freqs < upper)
            energy_values.append(float(np.sum(power[mask]) / total_power))
        band_energies = np.asarray(energy_values, dtype=np.float64)

    return np.asarray(
        [
            duration,
            rms,
            zero_crossing_rate,
            centroid / max(sample_rate, 1),
            rolloff / max(sample_rate, 1),
            *band_energies.tolist(),
        ],
        dtype=np.float64,
    )


def average_profile_vector(paths: list[Path]) -> np.ndarray:
    vectors = [extract_audio_profile_vector(path) for path in paths if path.exists()]
    if not vectors:
        return np.zeros(9, dtype=np.float64)
    return np.mean(np.stack(vectors, axis=0), axis=0)


def load_hypothesis_sources() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "speaker_profile_similarity.csv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return {str(row.get("case_id", "")): str(row.get("hypothesis_source", "")) for row in reader}


def build_audio_proxy_row(
    case_id: str,
    hypothesis_source: str,
    con_vector: np.ndarray,
    pro_vector: np.ndarray,
    speaker_1_vector: np.ndarray,
    speaker_2_vector: np.ndarray,
) -> dict[str, str]:
    direct_score = round(
        (cosine_similarity(con_vector, speaker_1_vector) + cosine_similarity(pro_vector, speaker_2_vector)) / 2,
        6,
    )
    swapped_score = round(
        (cosine_similarity(con_vector, speaker_2_vector) + cosine_similarity(pro_vector, speaker_1_vector)) / 2,
        6,
    )
    best_alignment = "direct" if direct_score >= swapped_score else "swapped"
    return {
        "case_id": case_id,
        "hypothesis_source": hypothesis_source or "separated_whisper",
        "best_audio_alignment": best_alignment,
        "direct_audio_score": f"{direct_score:.6f}",
        "swapped_audio_score": f"{swapped_score:.6f}",
        "audio_confidence_gap": f"{abs(direct_score - swapped_score):.6f}",
        "result_label": "experimental/frontier",
        "observation": "Lightweight audio-profile proxy only; this is not voiceprint identification.",
    }


def build_audio_proxy_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Speaker Profile Audio Proxy Trial",
        "",
        "This generated note records a narrow lightweight audio-profile trial using snippet enrollment and separated tracks.",
        "Results remain experimental/frontier and are a risk signal only, not a speaker-ID claim.",
        "",
        "| case_id | hypothesis_source | best_audio_alignment | direct_audio_score | swapped_audio_score | audio_confidence_gap | result_label | observation |",
        "| --- | --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['case_id']} | {row['hypothesis_source']} | {row['best_audio_alignment']} | "
            f"{row['direct_audio_score']} | {row['swapped_audio_score']} | {row['audio_confidence_gap']} | "
            f"{row['result_label']} | {row['observation']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "speaker_profile_audio_proxy_trial.csv"
    json_path = tables_dir / "speaker_profile_audio_proxy_trial.json"
    md_path = figures_dir / "speaker_profile_audio_proxy_trial.md"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=AUDIO_PROXY_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text("\n".join(build_audio_proxy_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    config = load_config()
    snippets_dir = PROJECT_ROOT / str(config["paths"]["snippets_dir"])
    separated_audio_dir = PROJECT_ROOT / str(config["paths"]["separated_audio_dir"])
    hypothesis_sources = load_hypothesis_sources()

    con_vector = average_profile_vector(sorted(snippets_dir.glob("con_*.wav")))
    pro_vector = average_profile_vector(sorted(snippets_dir.glob("pro_*.wav")))
    rows: list[dict[str, str]] = []
    for case in config.get("audio_cases", []):
        case_id = str(case["id"])
        speaker_1_vector = extract_audio_profile_vector(separated_audio_dir / str(case["separated"]["spk1"]))
        speaker_2_vector = extract_audio_profile_vector(separated_audio_dir / str(case["separated"]["spk2"]))
        rows.append(
            build_audio_proxy_row(
                case_id=case_id,
                hypothesis_source=hypothesis_sources.get(case_id, "separated_whisper"),
                con_vector=con_vector,
                pro_vector=pro_vector,
                speaker_1_vector=speaker_1_vector,
                speaker_2_vector=speaker_2_vector,
            )
        )

    csv_path, json_path, md_path = write_outputs(rows)
    print(f"Wrote speaker profile audio proxy trial CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile audio proxy trial JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile audio proxy trial note: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
