from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "demo" / "asr_effect.html"

CASES = [
    {
        "case_id": "LightOverlap",
        "headline": "Light overlap: mixed ASR wins",
        "lesson": "A light-overlap clip can be harmed by separation because the separated route adds insertions and repetitions.",
    },
    {
        "case_id": "HeavyOverlap",
        "headline": "Heavy overlap: separation helps",
        "lesson": "A heavy-overlap clip shows the opposite behavior: mixed ASR misses too much speech, while the separated route is much closer.",
    },
    {
        "case_id": "NoOverlap",
        "headline": "No overlap: speaker-aware route is clean",
        "lesson": "The non-overlap baseline is useful in a live demo because the raw separated transcript is stored locally and easy to compare.",
    },
    {
        "case_id": "OppositeOverlap",
        "headline": "Opposite overlap: mixed ASR collapses",
        "lesson": "This case makes the routing story intuitive: the mixed transcript deletes a lot, while the separated route nearly matches the reference.",
    },
]


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def normalize_text(text: str, max_chars: int = 1400) -> str:
    text = " ".join(text.replace("\r", "\n").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "..."


def segment_text(segments: list[dict[str, Any]], max_chars: int = 1500) -> str:
    lines: list[str] = []
    for segment in segments:
        speaker = segment.get("speaker")
        timing = ""
        if "start" in segment and "end" in segment:
            try:
                timing = f"{float(segment['start']):.1f}-{float(segment['end']):.1f}s"
            except (TypeError, ValueError):
                timing = ""
        prefix_parts = [part for part in [speaker, timing] if part]
        prefix = f"[{' '.join(prefix_parts)}] " if prefix_parts else ""
        lines.append(prefix + str(segment.get("text", "")).strip())
    return normalize_text("\n".join(line for line in lines if line.strip()), max_chars)


def extract_transcript(data: dict[str, Any] | None, *, missing: str) -> str:
    if data is None:
        return missing
    for key in ("full_text", "cleaned_full_text", "text"):
        if data.get(key):
            return normalize_text(str(data[key]))
    for key in ("cleaned_segments", "segments"):
        if isinstance(data.get(key), list):
            return segment_text(data[key])
    return missing


def load_case_rows() -> tuple[dict[tuple[str, str], dict[str, str]], dict[tuple[str, str], dict[str, str]]]:
    cer_rows = read_csv(ROOT / "results" / "tables" / "cer_results.csv")
    error_rows = read_csv(ROOT / "results" / "tables" / "error_type_summary.csv")
    return (
        {(row["case_id"], row["method"]): row for row in cer_rows},
        {(row["case_id"], row["method"]): row for row in error_rows},
    )


def fmt_cer(row: dict[str, str] | None) -> str:
    if not row:
        return "n/a"
    return f"{float(row['cer']):.3f}"


def best_method(case_id: str, cer_index: dict[tuple[str, str], dict[str, str]]) -> tuple[str, float]:
    rows = [row for (cid, _), row in cer_index.items() if cid == case_id]
    best = min(rows, key=lambda row: float(row["cer"]))
    return best["method"], float(best["cer"])


def metric(label: str, value: str, note: str = "") -> str:
    return f"""
      <div class="metric">
        <div class="metric-value">{esc(value)}</div>
        <div class="metric-label">{esc(label)}</div>
        <div class="metric-note">{esc(note)}</div>
      </div>
    """


def transcript_panel(title: str, text: str, badge: str = "") -> str:
    return f"""
      <article class="transcript">
        <div class="panel-head">
          <h3>{esc(title)}</h3>
          <span>{esc(badge)}</span>
        </div>
        <pre>{esc(text)}</pre>
      </article>
    """


def case_section(case: dict[str, str], cer_index: dict[tuple[str, str], dict[str, str]], error_index: dict[tuple[str, str], dict[str, str]], references: dict[str, Any]) -> str:
    case_id = case["case_id"]
    mixed = read_json(ROOT / "results" / "transcripts_raw" / f"{case_id}_mixed_whisper.json")
    separated = read_json(ROOT / "results" / "transcripts_speaker" / f"{case_id}_separated_speaker_transcript.json")
    cleaned = read_json(ROOT / "results" / "transcripts_postprocessed" / f"{case_id}_separated_speaker_transcript_cleaned.json")
    ref = references.get(case_id, {})

    best, best_cer = best_method(case_id, cer_index)
    mixed_row = cer_index.get((case_id, "mixed_whisper"))
    separated_row = cer_index.get((case_id, "separated_whisper"))
    cleaned_row = cer_index.get((case_id, "separated_whisper_cleaned"))
    sep_error = error_index.get((case_id, "separated_whisper"), {})
    cleaned_error = error_index.get((case_id, "separated_whisper_cleaned"), {})

    missing_separated = (
        "Raw separated transcript JSON is not present in this checkout. "
        "The CER row is still shown from results/tables/cer_results.csv."
    )
    audio_path = f"../resources/mixed_audio/{case_id}.wav"
    source_note = "local audio + committed transcript JSON + committed CER CSV"

    return f"""
    <section class="case-card" id="{esc(case_id)}">
      <div class="case-top">
        <div>
          <p class="eyebrow">ASR transcript effect / {esc(case_id)}</p>
          <h2>{esc(case['headline'])}</h2>
          <p class="lesson">{esc(case['lesson'])}</p>
        </div>
        <div class="audio-box">
          <span>Play mixed audio</span>
          <audio controls preload="metadata" src="{esc(audio_path)}"></audio>
        </div>
      </div>
      <div class="metrics">
        {metric("Mixed CER", fmt_cer(mixed_row), "direct Whisper on mixed audio")}
        {metric("Separated CER", fmt_cer(separated_row), f"insertions {sep_error.get('insertion_count', 'n/a')}, repetitions {sep_error.get('repetition_count', 'n/a')}")}
        {metric("Cleaned CER", fmt_cer(cleaned_row), f"removed {cleaned_error.get('removed_count_if_cleaned', 'n/a')} duplicated segments")}
        {metric("Best route", best.replace('_', ' '), f"CER {best_cer:.3f}")}
      </div>
      <div class="transcript-grid">
        {transcript_panel("Reference transcript", extract_transcript(ref, missing="Reference transcript missing."), "human-verified")}
        {transcript_panel("Mixed Whisper output", extract_transcript(mixed, missing="Mixed transcript missing."), "asr output")}
        {transcript_panel("Separated speaker output", extract_transcript(separated, missing=missing_separated), "speaker route")}
        {transcript_panel("Cleaned separated output", extract_transcript(cleaned, missing="Cleaned separated transcript missing."), "postprocessed")}
      </div>
      <p class="source">{esc(source_note)}</p>
    </section>
    """


def build_html() -> str:
    cer_index, error_index = load_case_rows()
    references = read_json(ROOT / "references" / "reference_transcripts.json") or {}
    sections = "\n".join(case_section(case, cer_index, error_index, references) for case in CASES)
    nav = "".join(f'<a href="#{esc(case["case_id"])}">{esc(case["case_id"])}</a>' for case in CASES)
    css = """
    :root { color-scheme: light; --ink:#101828; --muted:#526071; --line:#d8dee8; --soft:#f4f7fb; --blue:#1f5eff; --green:#087f5b; --red:#c92a2a; --panel:#ffffff; }
    * { box-sizing:border-box; }
    body { margin:0; background:#eef3f8; color:var(--ink); font:17px/1.55 Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    header { position:sticky; top:0; z-index:10; background:rgba(255,255,255,.94); border-bottom:1px solid var(--line); padding:1rem clamp(1rem,3vw,2.5rem); display:flex; align-items:center; justify-content:space-between; gap:1rem; }
    .brand { font-weight:900; }
    nav { display:flex; gap:.5rem; flex-wrap:wrap; }
    nav a { border:1px solid var(--line); border-radius:7px; padding:.42rem .62rem; color:var(--ink); text-decoration:none; background:white; font-weight:750; }
    main { padding:1.3rem clamp(1rem,3vw,2.5rem) 3rem; }
    .hero, .case-card { max-width:1480px; margin:0 auto 1.2rem; background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:clamp(1rem,2vw,1.5rem); box-shadow:0 12px 35px rgba(16,24,40,.06); }
    .hero h1 { font-size:clamp(2.2rem,4.5vw,5rem); line-height:1.03; margin:.2rem 0 1rem; letter-spacing:0; }
    .hero p, .lesson { color:var(--muted); max-width:82rem; font-size:1.08rem; }
    .eyebrow { color:var(--blue); font-weight:900; text-transform:uppercase; letter-spacing:.06em; margin:0 0 .35rem; }
    .case-top { display:grid; grid-template-columns:minmax(0,1fr) minmax(22rem,34rem); gap:1rem; align-items:start; }
    h2 { font-size:clamp(1.8rem,3.4vw,3.6rem); line-height:1.08; margin:.1rem 0 .6rem; letter-spacing:0; }
    .audio-box { background:var(--soft); border:1px solid var(--line); border-radius:8px; padding:1rem; display:grid; gap:.6rem; }
    .audio-box span { font-weight:850; color:var(--green); }
    audio { width:100%; }
    .metrics { display:grid; grid-template-columns:repeat(4,minmax(12rem,1fr)); gap:.75rem; margin:1rem 0; }
    .metric { border:1px solid var(--line); border-radius:8px; padding:.85rem; background:#fbfcfe; }
    .metric-value { font-size:1.65rem; font-weight:950; }
    .metric-label { font-weight:900; color:var(--blue); }
    .metric-note { color:var(--muted); font-size:.92rem; }
    .transcript-grid { display:grid; grid-template-columns:repeat(4,minmax(16rem,1fr)); gap:.75rem; }
    .transcript { border:1px solid var(--line); border-radius:8px; overflow:hidden; background:white; min-height:24rem; }
    .panel-head { display:flex; align-items:center; justify-content:space-between; gap:.5rem; padding:.75rem .85rem; border-bottom:1px solid var(--line); background:#f8fafc; }
    .panel-head h3 { margin:0; font-size:1.02rem; }
    .panel-head span { color:var(--green); font-size:.82rem; font-weight:800; white-space:nowrap; }
    pre { margin:0; white-space:pre-wrap; word-break:break-word; font:1rem/1.65 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; padding:.85rem; max-height:31rem; overflow:auto; }
    .source { color:var(--muted); font-size:.95rem; margin-bottom:0; }
    .live-command { display:block; width:max-content; max-width:100%; background:#111827; color:#f9fafb; border-radius:8px; padding:.75rem .9rem; overflow:auto; font:1rem/1.45 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }
    @media (max-width:1180px) { .metrics, .transcript-grid { grid-template-columns:repeat(2,minmax(0,1fr)); } .case-top { grid-template-columns:1fr; } }
    @media (max-width:720px) { header { align-items:flex-start; flex-direction:column; } .metrics, .transcript-grid { grid-template-columns:1fr; } pre { max-height:24rem; } }
    """
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ASR Transcript Effect Demo</title>
  <style>{css}</style>
</head>
<body>
  <header>
    <div class="brand">Overlap-Aware Speaker ASR / Transcript Effect</div>
    <nav>{nav}<a href="./index.html">Main deck</a></nav>
  </header>
  <main>
    <section class="hero">
      <p class="eyebrow">Direct teacher-facing demo</p>
      <h1>Play the audio, then compare what ASR actually recognized.</h1>
      <p>This page turns the committed experiment artifacts into a visible ASR demo: local audio playback, verified reference text, mixed Whisper output, separated speaker output when present, cleaned separated output, and CER/error counts recomputed from local CSV tables. It is designed for a stable classroom demo without downloading models.</p>
      <code class="live-command">python3 -m scripts.build_asr_effect_demo &amp;&amp; python3 -m http.server 8765</code>
    </section>
    {sections}
  </main>
</body>
</html>
"""


def build_demo() -> Path:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_html(), encoding="utf-8")
    return OUT


def main() -> None:
    out = build_demo()
    cer_index, _ = load_case_rows()
    print(f"Wrote {out.relative_to(ROOT)}")
    print("Live classroom route summary:")
    for case in CASES:
        case_id = case["case_id"]
        best, best_cer = best_method(case_id, cer_index)
        mixed = fmt_cer(cer_index.get((case_id, "mixed_whisper")))
        separated = fmt_cer(cer_index.get((case_id, "separated_whisper")))
        cleaned = fmt_cer(cer_index.get((case_id, "separated_whisper_cleaned")))
        print(f"- {case_id}: mixed={mixed}, separated={separated}, cleaned={cleaned}, best={best} ({best_cer:.3f})")


if __name__ == "__main__":
    main()
