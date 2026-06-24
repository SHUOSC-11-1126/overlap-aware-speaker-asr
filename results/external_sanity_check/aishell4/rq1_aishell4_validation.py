"""
RQ1: AISHELL-4 external validation of overlap-aware router v2.

Validates H1a (router v2 routing accuracy > always-mixed) and H1b (mixed ASR
achieves lower cpWER than separated ASR on low-overlap utterances) on a real
AISHELL-4 meeting (S_R004S03C01) using oracle separation from TextGrid boundaries.

Label: external/sanity-check
"""
from __future__ import annotations

import json
import re
import wave
import struct
import time
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np

# --- Configuration ---
MEETING_ID = "M_R003S02C01"  # Diverse overlap: 40 NoOv, 24 Light, 11 Mid, 1 Heavy
TEXTGRID_PATH = Path(f"/tmp/{MEETING_ID}.TextGrid")
FULL_WAV_PATH = Path(f"/tmp/wt-rq1/{MEETING_ID}.wav")
OUTPUT_DIR = Path("/tmp/wt-rq1/results/external_sanity_check/aishell4")
WINDOW_SEC = 30.0
NUM_WINDOWS = 77  # full meeting (~38.7 min)
WHISPER_MODEL = "tiny"
LANGUAGE = "zh"
SAMPLE_RATE = 16000

# --- TextGrid Parser ---
def parse_textgrid(path: Path) -> dict[str, list[tuple[float, float, str]]]:
    """Parse a Praat TextGrid file. Returns {speaker_tier: [(start, end, text), ...]}."""
    text = path.read_text(encoding="utf-8")
    tiers: dict[str, list[tuple[float, float, str]]] = {}
    # Match each item block
    item_pattern = re.compile(
        r'item\s*\[(\d+)\]:\s*\n\s*class\s*=\s*"IntervalTier"\s*\n\s*name\s*=\s*"([^"]+)"'
        r'.*?intervals:\s*size\s*=\s*(\d+)(.*?)(?=\s*item\s*\[|\Z)',
        re.DOTALL,
    )
    for match in item_pattern.finditer(text):
        tier_name = match.group(2)
        intervals_text = match.group(4)
        intervals: list[tuple[float, float, str]] = []
        interval_pattern = re.compile(
            r'intervals\s*\[\d+\]:\s*\n\s*xmin\s*=\s*([\d.]+)\s*\n\s*xmax\s*=\s*([\d.]+)\s*\n\s*text\s*=\s*"(.*?)"',
            re.DOTALL,
        )
        for imatch in interval_pattern.finditer(intervals_text):
            start = float(imatch.group(1))
            end = float(imatch.group(2))
            raw_text = imatch.group(3)
            # Decode TextGrid escapes
            text_val = raw_text.replace("<%>", "").replace("<sil>", "")
            text_val = text_val.strip()
            if text_val:
                intervals.append((start, end, text_val))
        tiers[tier_name] = intervals
    return tiers


# --- Audio Helpers ---
def read_wav(path: Path) -> tuple[np.ndarray, int]:
    """Read a WAV file into a numpy array."""
    with wave.open(str(path), "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)
    if sampwidth == 2:
        dtype = np.int16
    elif sampwidth == 4:
        dtype = np.int32
    else:
        raise ValueError(f"Unsupported sample width: {sampwidth}")
    audio = np.frombuffer(raw, dtype=dtype)
    if n_channels > 1:
        audio = audio[::n_channels]  # take first channel
    return audio.astype(np.float32), framerate


def write_wav(path: Path, audio: np.ndarray, framerate: int = SAMPLE_RATE) -> None:
    """Write a numpy array to a 16-bit mono WAV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Clip and convert to int16
    audio_clipped = np.clip(audio, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(framerate)
        wf.writeframes(audio_clipped.tobytes())


def extract_window(audio: np.ndarray, framerate: int, start_sec: float, duration_sec: float) -> np.ndarray:
    """Extract a time window from the audio array."""
    start_sample = int(start_sec * framerate)
    end_sample = int((start_sec + duration_sec) * framerate)
    return audio[start_sample:end_sample]


def create_speaker_track(
    full_audio: np.ndarray,
    framerate: int,
    window_start: float,
    window_duration: float,
    intervals: list[tuple[float, float, str]],
) -> np.ndarray:
    """Create a per-speaker track for a window: speech at original positions, silence elsewhere."""
    window_samples = int(window_duration * framerate)
    track = np.zeros(window_samples, dtype=np.float32)
    for start, end, _ in intervals:
        # Clip to window
        seg_start = max(start, window_start)
        seg_end = min(end, window_start + window_duration)
        if seg_end <= seg_start:
            continue
        start_sample = int((seg_start - window_start) * framerate)
        end_sample = int((seg_end - window_start) * framerate)
        full_start = int(seg_start * framerate)
        full_end = int(seg_end * framerate)
        # Guard against off-by-one rounding mismatches
        n = min(end_sample - start_sample, full_end - full_start)
        if n > 0:
            track[start_sample:start_sample + n] = full_audio[full_start:full_start + n]
    return track


# --- Overlap Computation ---
def compute_overlap_ratio(
    window_start: float,
    window_duration: float,
    speaker_intervals: dict[str, list[tuple[float, float, str]]],
) -> float:
    """Compute the fraction of time in the window where 2+ speakers are active."""
    # Build a timeline of speaker counts
    timeline: list[tuple[float, int]] = []  # (time, delta)
    for speaker, intervals in speaker_intervals.items():
        for start, end, _ in intervals:
            s = max(start, window_start)
            e = min(end, window_start + window_duration)
            if e <= s:
                continue
            timeline.append((s, 1))
            timeline.append((e, -1))
    if not timeline:
        return 0.0
    timeline.sort()
    overlap_time = 0.0
    current_speakers = 0
    prev_time = timeline[0][0]
    for t, delta in timeline:
        if current_speakers >= 2:
            overlap_time += t - prev_time
        current_speakers += delta
        prev_time = t
    return min(overlap_time / window_duration, 1.0)


def overlap_ratio_to_level(ratio: float) -> int:
    """Map overlap ratio to the project's overlap_level (0-4)."""
    if ratio < 0.05:
        return 0  # NoOverlap
    elif ratio < 0.2:
        return 1  # LightOverlap
    elif ratio < 0.5:
        return 2  # MidOverlap
    else:
        return 3  # HeavyOverlap


# --- Router v2 (from src/adaptive_router_v2.py) ---
def is_unstable(mixed_len: int, separated_len: int, duplicate_removed_count: int, runtime_ratio: float) -> bool:
    if mixed_len <= 0:
        return False
    length_ratio = separated_len / mixed_len if mixed_len > 0 else 0
    if length_ratio > 1.35:
        return True
    if duplicate_removed_count >= 10:
        return True
    if runtime_ratio > 1.8:
        return True
    return False


def choose_method_v2(
    overlap_level: int,
    mixed_len: int,
    separated_len: int,
    cleaned_len: int,
    duplicate_removed_count: int,
    runtime_ratio: float,
    cleaned_exists: bool,
    mixed_segments_count: int,
) -> tuple[str, str]:
    """Router v2 decision logic (reference-free: no CER used). Returns (method, rule)."""
    unstable = is_unstable(mixed_len, separated_len, duplicate_removed_count, runtime_ratio)
    if overlap_level == 0:
        if mixed_segments_count > 5:
            return "separated", "overlap==0 and mixed transcript long; keep separated"
        if unstable and duplicate_removed_count >= 10:
            return "mixed", "overlap==0 and high hallucinations; fall back to mixed"
        if cleaned_exists and abs(cleaned_len - mixed_len) < abs(separated_len - mixed_len) and duplicate_removed_count < 5:
            return "separated_cleaned", "overlap==0 cleaned closer to mixed"
        return "mixed", "overlap==0 short; choose mixed"
    if overlap_level in (1, 2):
        return "mixed", "overlap in [1,2]; choose mixed"
    if overlap_level >= 3:
        return "separated", "overlap>=3; choose separated"
    return "mixed", "fallback mixed"


# --- Whisper ASR ---
_whisper_model = None

def get_whisper_model(model_name: str = WHISPER_MODEL):
    global _whisper_model
    if _whisper_model is None:
        import whisper
        _whisper_model = whisper.load_model(model_name)
    return _whisper_model


def transcribe(audio: np.ndarray, framerate: int = SAMPLE_RATE) -> dict[str, Any]:
    """Run Whisper on an audio array. Returns {text, segments, runtime_sec}."""
    model = get_whisper_model()
    # Write to temp file
    tmp_path = Path("/tmp/wt-rq1/_tmp_asr_input.wav")
    write_wav(tmp_path, audio, framerate)
    t0 = time.time()
    result = model.transcribe(str(tmp_path), language=LANGUAGE, verbose=False)
    elapsed = time.time() - t0
    segments = [{"start": s["start"], "end": s["end"], "text": s["text"].strip()} for s in result.get("segments", [])]
    return {
        "text": result["text"].strip(),
        "segments": segments,
        "runtime_sec": round(elapsed, 3),
    }


# --- MeetEval cpWER/orcWER ---
def compute_cpwer(ref_speakers: dict[str, str], hyp_speakers: dict[str, str]) -> dict[str, Any]:
    """Compute cpWER for multi-speaker hypothesis vs reference.
    Returns {error_rate, errors, length}.
    """
    from meeteval.wer import cpwer
    session_id = "s1"
    ref_segs = [{"session_id": session_id, "speaker": spk, "words": txt} for spk, txt in ref_speakers.items() if txt.strip()]
    hyp_segs = [{"session_id": session_id, "speaker": spk, "words": txt} for spk, txt in hyp_speakers.items() if txt.strip()]
    if not ref_segs or not hyp_segs:
        return {"error_rate": 1.0, "errors": -1, "length": -1, "note": "empty"}
    result = cpwer(ref_segs, hyp_segs)
    r = result[session_id]
    return {"error_rate": float(r.error_rate), "errors": int(r.errors), "length": int(r.length)}


def compute_orcwer(ref_speakers: dict[str, str], mixed_text: str) -> dict[str, Any]:
    """Compute orcWER for single mixed hypothesis vs multi-speaker reference."""
    from meeteval.wer import orcwer
    session_id = "s1"
    ref_segs = [{"session_id": session_id, "speaker": spk, "words": txt} for spk, txt in ref_speakers.items() if txt.strip()]
    hyp_segs = [{"session_id": session_id, "speaker": "mix", "words": mixed_text}] if mixed_text.strip() else []
    if not ref_segs or not hyp_segs:
        return {"error_rate": 1.0, "errors": -1, "length": -1, "note": "empty"}
    result = orcwer(ref_segs, hyp_segs)
    r = result[session_id]
    return {"error_rate": float(r.error_rate), "errors": int(r.errors), "length": int(r.length)}


# --- Main Validation ---
def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=== RQ1: AISHELL-4 External Validation ===")
    print(f"Label: external/sanity-check")
    print(f"Meeting: {MEETING_ID} (AISHELL-4 test set)")
    print(f"License: CC BY-SA 4.0 (https://www.openslr.org/111/)")
    print(f"Window: {WINDOW_SEC}s x {NUM_WINDOWS} = {WINDOW_SEC * NUM_WINDOWS}s ({WINDOW_SEC * NUM_WINDOWS / 60:.1f} min)")
    print(f"ASR: Whisper-{WHISPER_MODEL}, language={LANGUAGE}")
    print()

    # 1. Parse TextGrid
    print("Parsing TextGrid...")
    tiers = parse_textgrid(TEXTGRID_PATH)
    print(f"  Speakers: {list(tiers.keys())}")
    for spk, intervals in tiers.items():
        total_speech = sum(e - s for s, e, _ in intervals)
        print(f"  {spk}: {len(intervals)} segments, {total_speech:.1f}s speech")

    # 2. Read full audio
    print("Reading full audio...")
    full_audio, framerate = read_wav(FULL_WAV_PATH)
    print(f"  Duration: {len(full_audio) / framerate:.1f}s, rate={framerate}")

    # 3. Process windows
    results: list[dict[str, Any]] = []
    for i in range(NUM_WINDOWS):
        window_start = i * WINDOW_SEC
        window_end = window_start + WINDOW_SEC
        if window_end > len(full_audio) / framerate:
            break

        # Find speakers active in this window
        active_speakers: dict[str, list[tuple[float, float, str]]] = {}
        for spk, intervals in tiers.items():
            window_intervals = [
                (s, e, t) for s, e, t in intervals
                if s < window_end and e > window_start
            ]
            if window_intervals:
                active_speakers[spk] = window_intervals

        if not active_speakers:
            print(f"  Window {i}: no speech, skipping")
            continue

        overlap_ratio = compute_overlap_ratio(window_start, WINDOW_SEC, active_speakers)
        overlap_level = overlap_ratio_to_level(overlap_ratio)

        # Reference text per speaker (clipped to window)
        ref_speakers: dict[str, str] = {}
        for spk, intervals in active_speakers.items():
            texts = [t for s, e, t in intervals if s < window_end and e > window_start]
            ref_speakers[spk] = "".join(texts)

        # Mixed audio
        mixed_audio = extract_window(full_audio, framerate, window_start, WINDOW_SEC)

        # Per-speaker tracks
        speaker_tracks: dict[str, np.ndarray] = {}
        for spk, intervals in active_speakers.items():
            speaker_tracks[spk] = create_speaker_track(full_audio, framerate, window_start, WINDOW_SEC, intervals)

        # Run Whisper on mixed
        mixed_result = transcribe(mixed_audio, framerate)
        mixed_text = mixed_result["text"]
        mixed_len = len(mixed_text)
        mixed_runtime = mixed_result["runtime_sec"]
        mixed_segments_count = len(mixed_result["segments"])

        # Run Whisper on each speaker track
        separated_texts: dict[str, str] = {}
        separated_runtime_total = 0.0
        separated_total_len = 0
        for spk, track in speaker_tracks.items():
            if np.max(np.abs(track)) < 100:  # essentially silent
                continue
            spk_result = transcribe(track, framerate)
            separated_texts[spk] = spk_result["text"]
            separated_runtime_total += spk_result["runtime_sec"]
            separated_total_len += len(spk_result["text"])

        separated_full_text = "".join(separated_texts.values())
        runtime_ratio = round(separated_runtime_total / mixed_runtime, 3) if mixed_runtime > 0 else 0.0

        # Compute cpWER (separated) and orcWER (mixed)
        cpwer_sep = compute_cpwer(ref_speakers, separated_texts)
        orcwer_mixed = compute_orcwer(ref_speakers, mixed_text)

        # Also compute cpWER for mixed (treating mixed as single speaker vs N refs)
        # This is the "pooled" comparison
        cpwer_mixed = compute_orcwer(ref_speakers, mixed_text)  # same as orcwer for 1 hyp

        # Router v2 decision (reference-free)
        router_method, router_rule = choose_method_v2(
            overlap_level=overlap_level,
            mixed_len=mixed_len,
            separated_len=separated_total_len,
            cleaned_len=0,  # no cleaned variant
            duplicate_removed_count=0,  # no postprocessing
            runtime_ratio=runtime_ratio,
            cleaned_exists=False,
            mixed_segments_count=mixed_segments_count,
        )

        # Map router method to cpWER
        if router_method == "mixed":
            router_cpwer = orcwer_mixed["error_rate"]
        elif router_method == "separated":
            router_cpwer = cpwer_sep["error_rate"]
        else:
            router_cpwer = cpwer_sep["error_rate"]

        # Oracle best
        oracle_cpwer = min(orcwer_mixed["error_rate"], cpwer_sep["error_rate"])

        window_result = {
            "window_id": i,
            "window_start_sec": window_start,
            "window_end_sec": window_end,
            "overlap_ratio": round(overlap_ratio, 4),
            "overlap_level": overlap_level,
            "overlap_label": ["NoOverlap", "LightOverlap", "MidOverlap", "HeavyOverlap"][overlap_level],
            "num_speakers": len(active_speakers),
            "speakers": list(active_speakers.keys()),
            "ref_text_per_speaker": ref_speakers,
            "ref_total_length": sum(len(v) for v in ref_speakers.values()),
            "mixed_text": mixed_text,
            "mixed_text_length": mixed_len,
            "mixed_segments_count": mixed_segments_count,
            "mixed_runtime_sec": mixed_runtime,
            "separated_text_per_speaker": separated_texts,
            "separated_total_length": separated_total_len,
            "separated_runtime_sec": round(separated_runtime_total, 3),
            "runtime_ratio": runtime_ratio,
            "cpwer_separated": cpwer_sep,
            "orcwer_mixed": orcwer_mixed,
            "router_v2_method": router_method,
            "router_v2_rule": router_rule,
            "router_v2_cpwer": router_cpwer,
            "oracle_best_cpwer": oracle_cpwer,
            "always_mixed_cpwer": orcwer_mixed["error_rate"],
            "always_separated_cpwer": cpwer_sep["error_rate"],
        }
        results.append(window_result)

        print(f"  Window {i:2d} [{window_start:.0f}-{window_end:.0f}s] "
              f"ov={overlap_ratio:.3f}({window_result['overlap_label']}) "
              f"spk={len(active_speakers)} "
              f"mixed_cpWER={orcwer_mixed['error_rate']:.3f} "
              f"sep_cpWER={cpwer_sep['error_rate']:.3f} "
              f"router={router_method}({router_cpwer:.3f})")

    # 4. Aggregate
    print("\n=== Aggregation ===")
    n = len(results)
    if n == 0:
        print("No valid windows!")
        return

    avg_mixed = sum(r["always_mixed_cpwer"] for r in results) / n
    avg_separated = sum(r["always_separated_cpwer"] for r in results) / n
    avg_router = sum(r["router_v2_cpwer"] for r in results) / n
    avg_oracle = sum(r["oracle_best_cpwer"] for r in results) / n

    # Router accuracy: fraction where router picks the oracle-best method
    router_correct = sum(
        1 for r in results
        if (r["router_v2_method"] == "mixed" and r["always_mixed_cpwer"] <= r["always_separated_cpwer"])
        or (r["router_v2_method"] == "separated" and r["always_separated_cpwer"] <= r["always_mixed_cpwer"])
    )

    print(f"  Windows: {n}")
    print(f"  Always-mixed cpWER:     {avg_mixed:.4f}")
    print(f"  Always-separated cpWER: {avg_separated:.4f}")
    print(f"  Router v2 cpWER:        {avg_router:.4f}")
    print(f"  Oracle best cpWER:      {avg_oracle:.4f}")
    print(f"  Router v2 accuracy:     {router_correct}/{n} ({router_correct/n*100:.1f}%)")

    # H1a: Router v2 vs always-mixed
    delta_router_mixed = avg_router - avg_mixed
    print(f"\n  H1a: ΔcpWER(router_v2 - always_mixed) = {delta_router_mixed:.4f}")
    if delta_router_mixed < 0:
        print(f"  H1a: SUPPORTED (router v2 < always-mixed by {-delta_router_mixed:.4f})")
    else:
        print(f"  H1a: NOT SUPPORTED (router v2 >= always-mixed by {delta_router_mixed:.4f})")

    # H1b: Stratify by overlap
    print(f"\n  H1b: Stratified by overlap level:")
    for level in range(4):
        level_results = [r for r in results if r["overlap_level"] == level]
        if not level_results:
            continue
        ln = len(level_results)
        lm = sum(r["always_mixed_cpwer"] for r in level_results) / ln
        ls = sum(r["always_separated_cpwer"] for r in level_results) / ln
        label = ["NoOverlap", "LightOverlap", "MidOverlap", "HeavyOverlap"][level]
        delta = ls - lm
        print(f"    {label} (n={ln}): mixed={lm:.4f}, separated={ls:.4f}, Δ(sep-mixed)={delta:+.4f}")

    # Low-overlap specifically (levels 0-1)
    low_results = [r for r in results if r["overlap_level"] <= 1]
    if low_results:
        ln = len(low_results)
        lm = sum(r["always_mixed_cpwer"] for r in low_results) / ln
        ls = sum(r["always_separated_cpwer"] for r in low_results) / ln
        delta = ls - lm
        print(f"\n  H1b (low-overlap, n={ln}): mixed={lm:.4f}, separated={ls:.4f}")
        if delta > 0:
            print(f"  H1b: SUPPORTED (separated > mixed by {delta:.4f}; mixed is better at low overlap)")
        else:
            print(f"  H1b: NOT SUPPORTED (separated <= mixed by {-delta:.4f})")

    # Paired bootstrap CI for H1a
    import random
    random.seed(42)
    n_boot = 10000
    boot_deltas: list[float] = []
    for _ in range(n_boot):
        sample = [results[random.randint(0, n - 1)] for _ in range(n)]
        bm = sum(r["always_mixed_cpwer"] for r in sample) / n
        br = sum(r["router_v2_cpwer"] for r in sample) / n
        boot_deltas.append(br - bm)
    boot_deltas.sort()
    ci_low = boot_deltas[int(0.025 * n_boot)]
    ci_high = boot_deltas[int(0.975 * n_boot)]
    print(f"\n  H1a paired bootstrap 95% CI: [{ci_low:.4f}, {ci_high:.4f}]")

    # Save results
    summary = {
        "label": "external/sanity-check",
        "dataset": "AISHELL-4",
        "meeting_id": MEETING_ID,
        "source_url": f"https://huggingface.co/datasets/AISHELL/AISHELL-4/resolve/main/test/wav/{MEETING_ID}.flac",
        "license": "CC BY-SA 4.0",
        "paper": "https://arxiv.org/abs/2104.03603",
        "asr_model": f"whisper-{WHISPER_MODEL}",
        "language": LANGUAGE,
        "window_sec": WINDOW_SEC,
        "num_windows": n,
        "separation": "oracle (TextGrid boundaries)",
        "metrics": {
            "always_mixed_cpwer": round(avg_mixed, 6),
            "always_separated_cpwer": round(avg_separated, 6),
            "router_v2_cpwer": round(avg_router, 6),
            "oracle_best_cpwer": round(avg_oracle, 6),
            "router_v2_accuracy": round(router_correct / n, 4),
            "h1a_delta_router_minus_mixed": round(delta_router_mixed, 6),
            "h1a_bootstrap_ci_95": [round(ci_low, 6), round(ci_high, 6)],
        },
        "h1a_supported": delta_router_mixed < 0,
        "h1b_low_overlap": {},
        "windows": results,
    }

    # H1b summary
    if low_results:
        ln = len(low_results)
        lm = sum(r["always_mixed_cpwer"] for r in low_results) / ln
        ls = sum(r["always_separated_cpwer"] for r in low_results) / ln
        summary["h1b_low_overlap"] = {
            "n": ln,
            "mixed_cpwer": round(lm, 6),
            "separated_cpwer": round(ls, 6),
            "delta_sep_minus_mixed": round(ls - lm, 6),
            "supported": (ls - lm) > 0,
        }

    # Stratified summary
    stratified: list[dict[str, Any]] = []
    for level in range(4):
        level_results = [r for r in results if r["overlap_level"] == level]
        if not level_results:
            continue
        ln = len(level_results)
        stratified.append({
            "overlap_level": level,
            "overlap_label": ["NoOverlap", "LightOverlap", "MidOverlap", "HeavyOverlap"][level],
            "n": ln,
            "mixed_cpwer": round(sum(r["always_mixed_cpwer"] for r in level_results) / ln, 6),
            "separated_cpwer": round(sum(r["always_separated_cpwer"] for r in level_results) / ln, 6),
            "router_v2_cpwer": round(sum(r["router_v2_cpwer"] for r in level_results) / ln, 6),
        })
    summary["stratified_by_overlap"] = stratified

    output_path = OUTPUT_DIR / "rq1_aishell4_validation_results.json"
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
