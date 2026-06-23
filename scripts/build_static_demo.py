from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "demo"
OUT = DEMO_DIR / "index.html"


def read_csv(path: str) -> list[dict[str, str]]:
    full = ROOT / path
    if not full.exists():
        return []
    with full.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def fmt(value: Any, digits: int = 3) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def rel(path: str) -> str:
    return "../" + path


def compact_table(rows: list[dict[str, str]], columns: list[str], limit: int = 6) -> str:
    header = "".join(f"<th>{html.escape(col)}</th>" for col in columns)
    body = []
    for row in rows[:limit]:
        body.append("<tr>" + "".join(f"<td>{html.escape(row.get(col, ''))}</td>" for col in columns) + "</tr>")
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def contribution_card(title: str, owner: str, body: str, artifacts: str) -> str:
    return f"""
    <div class="contribution-card">
      <h3>{html.escape(title)}</h3>
      <p class="owner">{html.escape(owner)}</p>
      <p>{html.escape(body)}</p>
      <p class="artifact">{html.escape(artifacts)}</p>
    </div>
    """


def metric(label: str, value: str, note: str = "") -> str:
    return f"""
    <div class="metric">
      <div class="metric-value">{html.escape(value)}</div>
      <div class="metric-label">{html.escape(label)}</div>
      <div class="metric-note">{html.escape(note)}</div>
    </div>
    """


def build_demo() -> str:
    balanced = read_csv("results/tables/audio_depth_balanced_router_comparison.csv")
    risk = read_csv("results/tables/audiodepth_risk_guarded_gate_best_policies.csv")
    unified = read_csv("results/tables/unified_router_eval_summary.csv")
    split = read_csv("results/tables/source_disjoint_v2_split_audit.csv")
    micro = read_csv("results/tables/micro_gold_candidate_manifest.csv")
    runtime = read_csv("results/tables/end_to_end_runtime_components.csv")

    balanced_router = next((r for r in balanced if r.get("model_name") == "audio_depth_balanced_route_winner_router"), {})
    router_v2 = next((r for r in balanced if r.get("model_name") == "router_v2"), {})
    risk_balanced = next((r for r in risk if r.get("policy_tier") == "balanced"), risk[0] if risk else {})
    fixed_mixed = next((r for r in unified if r.get("policy") == "fixed_mixed"), {})
    safe_fusion = next((r for r in unified if r.get("policy") == "stage33_safe_regret_fusion_refit"), {})
    leakage = next((r for r in split if r.get("split") == "leakage"), {})
    test_split = next((r for r in split if r.get("split") == "test"), {})
    head_runtime = next((r for r in runtime if r.get("component") == "metadata_policy_eval"), {})
    asr_runtime = next((r for r in runtime if r.get("component") == "all_routes_per_sample"), {})

    challenge_cases = [
        {
            "case": "NoOverlap",
            "audio": rel("resources/mixed_audio/NoOverlap.wav"),
            "best": "separate",
            "why": "Clean speech is easy, but the separated speaker-track route is strongest on the gold case.",
        },
        {
            "case": "LightOverlap",
            "audio": rel("resources/mixed_audio/LightOverlap.wav"),
            "best": "keep mixed",
            "why": "Light overlap can make separation hallucinate repeated fragments, so mixed wins.",
        },
        {
            "case": "MidOverlap",
            "audio": rel("resources/mixed_audio/MidOverlap.wav"),
            "best": "keep mixed",
            "why": "Moderate overlap still shows insertion and repetition risk after separation.",
        },
        {
            "case": "HeavyOverlap",
            "audio": rel("resources/mixed_audio/HeavyOverlap.wav"),
            "best": "separate",
            "why": "Heavy overlap benefits from separating competing speech streams.",
        },
        {
            "case": "OppositeOverlap",
            "audio": rel("resources/mixed_audio/OppositeOverlap.wav"),
            "best": "separate",
            "why": "Highly competitive opposite overlap is where separation helps most.",
        },
    ]

    slide_data = {
        "challengeCases": challenge_cases,
        "minutes": 10,
    }

    slides = [
        f"""
        <section class="slide active" data-title="Hook">
          <div class="eyebrow">10 minute demo</div>
          <h1>A complete overlap-aware ASR project, not one trick.</h1>
          <p class="lead">The project starts with a simple question: when should a multi-speaker ASR system keep mixed audio, separate speakers, clean transcripts, route adaptively, or abstain for review?</p>
          <div class="metrics">
            {metric("Gold router_v2 CER", "0.120", "5 manually verified cases")}
            {metric("Fixed mixed CER", "0.302", "gold baseline")}
            {metric("Core result", "router_v2", "team routing baseline")}
          </div>
          <img class="hero-img" src="{rel('results/figures/final_system_architecture.png')}" alt="Final system architecture">
        </section>
        """,
        f"""
        <section class="slide" data-title="Team map">
          <div class="eyebrow">Full project map</div>
          <h2>Everybody's work fits into one pipeline.</h2>
          <p>This slide is the answer to "what did the whole project build?" It keeps the team contributions visible before the demo zooms into the route challenge.</p>
          <div class="contribution-grid">
            {contribution_card("Data + Whisper baseline", "Team baseline track", "Prepared mixed/separated audio, transcript candidates, and reproducible Whisper-style baselines.", "resources/, results/transcripts/, src/whisper_transcribe.py")}
            {contribution_card("Separation + postprocess", "Pipeline track", "Compared mixed, separated, and duplicate-suppressed cleaned transcript routes.", "src/separate_speakers.py, src/postprocess.py")}
            {contribution_card("Adaptive routing", "Router track", "Built router_v1/v2 and risk-aware selection from deployment-visible instability signals.", "src/adaptive_router_v2.py, src/risk_aware_selector.py")}
            {contribution_card("Evaluation stack", "Metric track", "Implemented CER, speaker-aware CER, cpCER-lite, error-type analysis, and evidence ledgers.", "REPORT.md, docs/final_claim_ledger.md")}
            {contribution_card("Synthetic robustness", "Validation track", "Created synthetic silver and held-out split checks to expose overfitting and oracle gaps.", "src/synthetic_*.py, results/tables/")}
            {contribution_card("Frontier systems", "Research-expansion track", "Explored MeetEval/cpWER, speaker-profile diagnostics, LLM critic/RAG, demo excellence, and AudioDepth.", "docs/frontier/, results/figures/")}
          </div>
        </section>
        """,
        f"""
        <section class="slide" data-title="Listen">
          <div class="eyebrow">Act 1: make the audience judge</div>
          <h2>Route challenge: listen first, then guess.</h2>
          <p>Play one clip, then ask: keep mixed, separate, clean, or review? This makes the core routing problem memorable before the results table appears.</p>
          <div id="challenge" class="challenge"></div>
        </section>
        """,
        f"""
        <section class="slide" data-title="Stable result">
          <div class="eyebrow">Stable baseline</div>
          <h2>The five-case gold story</h2>
          <p>The stable claim is deliberately narrow: on five verified gold cases, route selection beats fixed routes and matches the oracle average. This is the strongest quantitative claim in the project.</p>
          <div class="metrics">
            {metric("router_v2", "0.120", "average CER")}
            {metric("fixed separated", "0.192", "average CER")}
            {metric("fixed mixed", "0.302", "average CER")}
          </div>
          <img class="hero-img" src="{rel('results/figures/final_key_results_card.png')}" alt="Final key results">
        </section>
        """,
        f"""
        <section class="slide" data-title="Evaluation">
          <div class="eyebrow">Metric contribution</div>
          <h2>We also measured the right failure modes.</h2>
          <p>Normal CER is not enough for multi-speaker audio. The project adds error-type analysis, speaker-aware CER, and cpCER-lite so routing decisions are judged by content and attribution behavior.</p>
          <div class="image-grid">
            <img src="{rel('results/figures/error_type_by_case.png')}" alt="Error type by case">
            <img src="{rel('results/figures/cer_by_case.png')}" alt="CER by case">
          </div>
        </section>
        """,
        f"""
        <section class="slide" data-title="Router lesson">
          <div class="eyebrow">Why fixed separation fails</div>
          <h2>Separation is a tool, not a law.</h2>
          <p>Light and mid overlap can suffer from insertion and repetition artifacts after separation. Heavy and opposite overlap benefit more clearly. The router contribution is making that boundary explicit.</p>
          <div class="metrics">
            {metric("NoOverlap", "separate", "gold best route")}
            {metric("Light/Mid", "mixed", "separation can hurt")}
            {metric("Heavy/Opposite", "separate", "separation helps")}
          </div>
          {compact_table([
              {'case': 'NoOverlap', 'best_route': 'separated_whisper', 'lesson': 'clean audio can still benefit from speaker-track structure'},
              {'case': 'LightOverlap', 'best_route': 'mixed_whisper', 'lesson': 'separation can introduce insertion/repetition artifacts'},
              {'case': 'MidOverlap', 'best_route': 'mixed_whisper', 'lesson': 'moderate overlap is not automatically a separation win'},
              {'case': 'HeavyOverlap', 'best_route': 'separated_whisper', 'lesson': 'strong overlap benefits from separated streams'},
              {'case': 'OppositeOverlap', 'best_route': 'separated_whisper', 'lesson': 'competitive overlap benefits from separated streams'},
          ], ['case', 'best_route', 'lesson'], 5)}
        </section>
        """,
        f"""
        <section class="slide" data-title="Frontiers">
          <div class="eyebrow">Breadth-first frontier work</div>
          <h2>The repository became a team research workbench.</h2>
          <p>Beyond the stable router, the strongest team value is the organized spread of evaluation and research tracks. Some are real results, some are honest scaffolds, and each has claim boundaries in the docs.</p>
          <div class="contribution-grid compact">
            {contribution_card("Compute-aware cascade", "Deployment track", "Recorded cost/RTF tradeoffs and profile cards for accuracy-first, balanced, and cost-first use.", "results/figures/cascade_*.md")}
            {contribution_card("MeetEval / cpWER", "Evaluation frontier", "Built compatibility exports, dry-run handoffs, and cpWER alignment scorecards.", "results/figures/meeteval_*.md")}
            {contribution_card("Speaker profile", "Attribution frontier", "Found a swapped-bias failure mode and staged stronger profile/embedding baselines.", "results/figures/speaker_profile_*.md")}
            {contribution_card("LLM critic / RAG", "Agentic frontier", "Prepared qualitative critic queues and repair directions without claiming verified repair.", "results/figures/llm_critic_*.md")}
            {contribution_card("External validation", "Generalization frontier", "Kept external validation visible as a blocker instead of pretending local slices prove deployment.", "results/figures/frontier_*.md")}
            {contribution_card("AudioDepth attempt", "Acoustic triage frontier", "Tests RGB-D-style acoustic maps as a pre-ASR signal. Useful and visual, but not the team's central proof.", "docs/frontier/audiodepth_one_page.md")}
            {contribution_card("Demo excellence", "Presentation frontier", "Turned results into walkthroughs, runbooks, and now a static 10-minute offline deck.", "demo/index.html")}
          </div>
        </section>
        """,
        f"""
        <section class="slide" data-title="AudioDepth">
          <div class="eyebrow">Frontier branch</div>
          <h2>AudioDepth: RGB-D intuition for sound</h2>
          <p>This is one exploratory branch: treat overlap like time-frequency occlusion, where logmel is the image and overlap/uncertainty are depth-like channels.</p>
          <div class="metrics">
            {metric("Balanced router CER", fmt(balanced_router.get('average_cer'), 3), "controlled silver-plus")}
            {metric("router_v2 on same slice", fmt(router_v2.get('average_cer'), 3), "controlled silver-plus")}
            {metric("Route accuracy", fmt(balanced_router.get('accuracy_vs_oracle_route'), 3), "not gold")}
          </div>
          <img class="hero-img" src="{rel('results/figures/audiodepth_v2_examples.png')}" alt="AudioDepth examples">
        </section>
        """,
        f"""
        <section class="slide" data-title="Safety">
          <div class="eyebrow">Safety twist</div>
          <h2>The router needs a seatbelt.</h2>
          <p>This branch is most useful when framed modestly: the risk-guarded AudioDepth gate explores whether an acoustic prefilter can reduce text probing while constraining unsafe mixed bypasses.</p>
          <div class="metrics">
            {metric("Balanced gate CER", fmt(risk_balanced.get('selected_route_CER'), 3), "controlled silver-plus")}
            {metric("False-safe rate", fmt(risk_balanced.get('false_safe_rate'), 3), "direct bypass")}
            {metric("Text probe reduction", fmt(risk_balanced.get('text_probe_reduction_rate'), 3), "less downstream work")}
          </div>
          <img class="hero-img" src="{rel('results/figures/audiodepth_risk_guarded_gate_pareto.png')}" alt="Risk guarded Pareto">
        </section>
        """,
        f"""
        <section class="slide" data-title="Evidence hygiene">
          <div class="eyebrow">Act 2: evidence hygiene</div>
          <h2>Source-disjoint audit: then we made the split stricter.</h2>
          <p>Stage 34 uses a source-disjoint test so that source utterances do not leak across train, validation, and test.</p>
          <div class="metrics">
            {metric("Strict test rows", test_split.get('route_cer_rows', '7'), "with route CER")}
            {metric("Source leakage", leakage.get('manifest_rows', '0'), "source utterance leaks")}
            {metric("Micro-gold candidates", str(len(micro)), "prepared, not annotated")}
          </div>
          {compact_table(split, ['split', 'manifest_rows', 'route_cer_rows', 'unique_source_tokens'], 5)}
        </section>
        """,
        f"""
        <section class="slide" data-title="Unified eval">
          <div class="eyebrow">Act 3: router showdown</div>
          <h2>On strict test, fixed mixed is risky.</h2>
          <p>Use this slide as a scoreboard. The point is not huge-data victory; it is evidence discipline. Review rows use the explicit oracle_for_abstained_rows handoff assumption.</p>
          <div class="metrics">
            {metric("Fixed mixed false-safe", fixed_mixed.get('false_safe_count', '3'), "strict test")}
            {metric("Safe fusion false-safe", safe_fusion.get('false_safe_count', '0'), "with review tradeoff")}
            {metric("Review coverage", fmt(safe_fusion.get('coverage'), 3), "coverage after abstention")}
          </div>
          {compact_table(unified, ['policy', 'mean_selected_cer', 'false_safe_count', 'high_error_mixed_count', 'review_rate', 'coverage'], 8)}
        </section>
        """,
        f"""
        <section class="slide" data-title="Runtime">
          <div class="eyebrow">Act 4: can it run here?</div>
          <h2>This demo is offline by design.</h2>
          <p>Your current system Python lacks the full ASR/scientific stack. So the demo reads committed evidence and local media, then presents the whole project without pretending to rerun Whisper live.</p>
          <div class="metrics">
            {metric("Head-only router", head_runtime.get('mean_runtime_sec', '0.0001') + 's', "lightweight")}
            {metric("All routes ASR", asr_runtime.get('mean_runtime_sec', '2.0924') + 's', "existing runtime record")}
            {metric("Demo dependency", "none", "open demo/index.html")}
          </div>
          {compact_table(runtime, ['level', 'component', 'mean_runtime_sec', 'provenance'], 6)}
        </section>
        """,
        f"""
        <section class="slide" data-title="Close">
          <div class="eyebrow">Final 60 seconds</div>
          <h2>The honest ending is the strongest ending.</h2>
          <p>Stable baseline: router_v2 on five gold cases. Whole-project contribution: a pipeline that combines data preparation, separation, postprocessing, adaptive routing, speaker-aware metrics, robustness checks, risk controls, and frontier scaffolds. AudioDepth is one attempt inside that larger story. Next proof: annotate the micro-gold pack and rerun gold/silver-separated evaluation.</p>
          <div class="metrics">
            {metric("Main claim", "narrow", "five-case gold benchmark")}
            {metric("Project claim", "systematic", "complete evidence workflow")}
            {metric("Next step", "micro-gold", "11 candidates ready")}
          </div>
          <img class="hero-img" src="{rel('results/figures/final_evidence_levels.png')}" alt="Evidence levels">
        </section>
        """,
    ]

    css = """
    :root { --bg:#0b1020; --panel:#121a31; --text:#f5f7fb; --muted:#aab3c5; --line:#263453; --accent:#65d6ad; --hot:#ff7a70; --gold:#ffd166; }
    * { box-sizing: border-box; }
    body { margin:0; background: radial-gradient(circle at 10% 10%, #1b2a4a 0, #0b1020 36rem); color:var(--text); font: 16px/1.55 Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    .shell { min-height:100vh; display:grid; grid-template-rows:auto 1fr auto; }
    header, footer { display:flex; align-items:center; justify-content:space-between; gap:1rem; padding:1rem 1.35rem; border-color:var(--line); }
    header { border-bottom:1px solid var(--line); background:rgba(8,12,25,.82); backdrop-filter: blur(14px); position:sticky; top:0; z-index:10; }
    footer { border-top:1px solid var(--line); color:var(--muted); }
    .brand { font-weight:800; letter-spacing:0; }
    .timer { font-variant-numeric: tabular-nums; color:var(--gold); }
    .progress { height:.5rem; background:#1f2944; border-radius:999px; overflow:hidden; min-width:14rem; }
    .progress span { display:block; height:100%; width:0; background:linear-gradient(90deg,var(--accent),var(--gold)); transition:width .2s ease; }
    main { position:relative; overflow:hidden; }
    .slide { display:none; min-height:calc(100vh - 8rem); padding:3rem clamp(1.2rem,4vw,4rem); animation: pop .25s ease; }
    .slide.active { display:block; }
    @keyframes pop { from { opacity:.2; transform: translateY(8px); } to { opacity:1; transform:none; } }
    h1, h2 { max-width:62rem; margin:.2rem 0 1rem; line-height:1.02; letter-spacing:0; }
    h1 { font-size:clamp(2.6rem,7vw,6rem); }
    h2 { font-size:clamp(2rem,5vw,4.6rem); }
    .lead, p { color:var(--muted); max-width:58rem; font-size:clamp(1rem,1.5vw,1.28rem); }
    .eyebrow { color:var(--accent); font-weight:800; text-transform:uppercase; letter-spacing:.08em; }
    .metrics { display:grid; grid-template-columns:repeat(auto-fit,minmax(12rem,1fr)); gap:1rem; margin:1.4rem 0; max-width:72rem; }
    .metric { border:1px solid var(--line); background:rgba(18,26,49,.76); border-radius:8px; padding:1rem; min-height:7rem; }
    .metric-value { font-size:2rem; font-weight:850; color:var(--text); }
    .metric-label { color:var(--accent); font-weight:750; }
    .metric-note { color:var(--muted); font-size:.9rem; }
    .hero-img { width:min(100%,72rem); max-height:42vh; object-fit:contain; display:block; margin:1.5rem 0; border:1px solid var(--line); border-radius:8px; background:#fff; }
    .image-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(18rem,1fr)); gap:1rem; margin-top:1.5rem; }
    .image-grid img { width:100%; border:1px solid var(--line); border-radius:8px; background:white; }
    .contribution-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(18rem,1fr)); gap:1rem; margin-top:1.5rem; max-width:78rem; }
    .contribution-grid.compact { grid-template-columns:repeat(auto-fit,minmax(15rem,1fr)); }
    .contribution-card { border:1px solid var(--line); background:rgba(18,26,49,.76); border-radius:8px; padding:1rem; min-height:12rem; }
    .contribution-card h3 { margin:.1rem 0 .25rem; color:var(--text); font-size:1.12rem; }
    .contribution-card p { font-size:.96rem; margin:.45rem 0; }
    .owner { color:var(--accent); font-weight:800; }
    .artifact { color:var(--gold); font-size:.86rem !important; }
    table { border-collapse:collapse; width:min(100%,72rem); margin:1.3rem 0; font-size:.92rem; background:rgba(18,26,49,.7); }
    th, td { border:1px solid var(--line); padding:.6rem .7rem; text-align:left; }
    th { color:var(--accent); background:#10182d; }
    .challenge { display:grid; grid-template-columns: minmax(16rem, 28rem) 1fr; gap:1.2rem; align-items:start; margin-top:1.5rem; }
    .case-card, .answer-card { border:1px solid var(--line); background:rgba(18,26,49,.78); border-radius:8px; padding:1rem; }
    audio { width:100%; margin:.75rem 0; }
    button { border:1px solid var(--line); background:#17213c; color:var(--text); border-radius:8px; padding:.7rem .9rem; font-weight:750; cursor:pointer; }
    button:hover, button.active { border-color:var(--accent); color:var(--accent); }
    .choices { display:flex; flex-wrap:wrap; gap:.6rem; margin-top:.8rem; }
    .answer { color:var(--gold); font-weight:800; font-size:1.3rem; }
    .controls { display:flex; gap:.6rem; align-items:center; }
    .pill { border:1px solid var(--line); border-radius:999px; padding:.35rem .65rem; color:var(--muted); }
    @media (max-width: 820px) { .challenge { grid-template-columns:1fr; } header { align-items:flex-start; flex-direction:column; } .progress { width:100%; } }
    """

    js = f"""
    const DATA = {json.dumps(slide_data)};
    let current = 0;
    const slides = [...document.querySelectorAll('.slide')];
    const bar = document.querySelector('#progressBar');
    const counter = document.querySelector('#counter');
    const timer = document.querySelector('#timer');
    const titles = document.querySelector('#titles');
    const start = Date.now();
    function show(i) {{
      current = Math.max(0, Math.min(slides.length - 1, i));
      slides.forEach((s, idx) => s.classList.toggle('active', idx === current));
      counter.textContent = `${{current + 1}} / ${{slides.length}}`;
      bar.style.width = `${{((current + 1) / slides.length) * 100}}%`;
      titles.textContent = slides[current].dataset.title || '';
    }}
    function tick() {{
      const elapsed = Math.floor((Date.now() - start) / 1000);
      const total = DATA.minutes * 60;
      const remain = Math.max(0, total - elapsed);
      timer.textContent = `${{Math.floor(remain / 60)}}:${{String(remain % 60).padStart(2,'0')}}`;
    }}
    document.querySelector('#prev').onclick = () => show(current - 1);
    document.querySelector('#next').onclick = () => show(current + 1);
    document.addEventListener('keydown', (e) => {{
      if (e.key === 'ArrowRight' || e.key === ' ') show(current + 1);
      if (e.key === 'ArrowLeft') show(current - 1);
    }});
    function renderChallenge() {{
      const root = document.querySelector('#challenge');
      let idx = 0;
      function draw(choice='') {{
        const item = DATA.challengeCases[idx];
        root.innerHTML = `
          <div class="case-card">
            <div class="eyebrow">Audio case ${{idx + 1}} of ${{DATA.challengeCases.length}}</div>
            <h3>${{item.case}}</h3>
            <audio controls src="${{item.audio}}"></audio>
            <div class="choices">
              ${{['keep mixed','separate','clean','review'].map(c => `<button class="${{choice===c?'active':''}}" data-choice="${{c}}">${{c}}</button>`).join('')}}
            </div>
            <div class="choices">
              <button id="casePrev">Previous case</button>
              <button id="caseNext">Next case</button>
            </div>
          </div>
          <div class="answer-card">
            <div class="eyebrow">Reveal</div>
            ${{choice ? `<p>Your guess: <strong>${{choice}}</strong></p><p class="answer">Best route: ${{item.best}}</p><p>${{item.why}}</p>` : '<p>Make a guess first. The reveal is better when the room commits.</p>'}}
          </div>`;
        root.querySelectorAll('[data-choice]').forEach(btn => btn.onclick = () => draw(btn.dataset.choice));
        root.querySelector('#casePrev').onclick = () => {{ idx = (idx + DATA.challengeCases.length - 1) % DATA.challengeCases.length; draw(); }};
        root.querySelector('#caseNext').onclick = () => {{ idx = (idx + 1) % DATA.challengeCases.length; draw(); }};
      }}
      draw();
    }}
    renderChallenge();
    show(0);
    tick();
    setInterval(tick, 1000);
    """

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Overlap-aware Speaker ASR Demo</title>
  <style>{css}</style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <div class="brand">Overlap-aware Speaker ASR</div>
        <div class="pill" id="titles">Hook</div>
      </div>
      <div class="controls">
        <button id="prev">Back</button>
        <button id="next">Next</button>
        <span class="pill" id="counter">1 / {len(slides)}</span>
        <span class="timer" id="timer">10:00</span>
      </div>
      <div class="progress" aria-label="slide progress"><span id="progressBar"></span></div>
    </header>
    <main>
      {''.join(slides)}
    </main>
    <footer>
      <span>Keys: Left / Right / Space. Demo mode: offline, evidence-backed, no live ASR rerun.</span>
      <span>Claim boundary: team baseline first, frontier attempts second.</span>
    </footer>
  </div>
  <script>{js}</script>
</body>
</html>
"""


def main() -> int:
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_demo(), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
