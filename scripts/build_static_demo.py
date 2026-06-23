from __future__ import annotations

import html
import json
import re
import urllib.request
from urllib.error import HTTPError, URLError
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "demo"
OUT = DEMO_DIR / "index.html"

OWNER = "SHUOSC-11-1126"
REPO = "overlap-aware-speaker-asr"
BRANCH = "main"
GH = f"https://github.com/{OWNER}/{REPO}"
RAW = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/{BRANCH}"
API = f"https://api.github.com/repos/{OWNER}/{REPO}"

FALLBACK_REPO_INFO = {"stargazers_count": 6, "forks_count": 3}
FALLBACK_CONTRIBUTORS = [
    {"login": "ceilf6", "contributions": 2332, "html_url": "https://github.com/ceilf6"},
    {"login": "cursoragent", "contributions": 187, "html_url": "https://github.com/cursoragent"},
    {"login": "YuechuanLiang", "contributions": 18, "html_url": "https://github.com/YuechuanLiang"},
    {"login": "wfzark", "contributions": 18, "html_url": "https://github.com/wfzark"},
    {"login": "saayaya", "contributions": 17, "html_url": "https://github.com/saayaya"},
    {"login": "cursor[bot]", "contributions": 14, "html_url": "https://github.com/apps/cursor"},
    {"login": "xyx12369", "contributions": 2, "html_url": "https://github.com/xyx12369"},
    {"login": "haohaozhang776-maker", "contributions": 1, "html_url": "https://github.com/haohaozhang776-maker"},
]
FALLBACK_FRONTIER_DOCS = [
    {"name": "agentic_research_entropy.md", "type": "file", "html_url": f"{GH}/blob/{BRANCH}/docs/frontier/agentic_research_entropy.md"},
    {"name": "asr_llm_emotion_capstone.md", "type": "file", "html_url": f"{GH}/blob/{BRANCH}/docs/frontier/asr_llm_emotion_capstone.md"},
    {"name": "audio-depth-router.md", "type": "file", "html_url": f"{GH}/blob/{BRANCH}/docs/frontier/audio-depth-router.md"},
    {"name": "causal_hallucination_probe.md", "type": "file", "html_url": f"{GH}/blob/{BRANCH}/docs/frontier/causal_hallucination_probe.md"},
    {"name": "causal_hallucination_probe_litreview.md", "type": "file", "html_url": f"{GH}/blob/{BRANCH}/docs/frontier/causal_hallucination_probe_litreview.md"},
]


def fetch_text(path: str) -> str:
    url = f"{RAW}/{path}"
    with urllib.request.urlopen(url, timeout=20) as response:
        return response.read().decode("utf-8")


def fetch_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError):
        if url == API:
            return FALLBACK_REPO_INFO
        if url.endswith("/contributors?per_page=100"):
            return FALLBACK_CONTRIBUTORS
        if "contents/docs/frontier" in url:
            return FALLBACK_FRONTIER_DOCS
        raise


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def raw_url(path: str) -> str:
    return f"{RAW}/{path}"


def github_url(path: str = "") -> str:
    return f"{GH}/blob/{BRANCH}/{path}" if path else GH


def md_link(path: str) -> str:
    return f'<a href="{esc(github_url(path))}" target="_blank" rel="noreferrer">{esc(path)}</a>'


def compact_table(rows: list[dict[str, str]], columns: list[str], limit: int = 8) -> str:
    header = "".join(f"<th>{esc(col)}</th>" for col in columns)
    body = []
    for row in rows[:limit]:
        body.append("<tr>" + "".join(f"<td>{row.get(col, '')}</td>" for col in columns) + "</tr>")
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def metric(label: str, value: str, note: str = "") -> str:
    return f"""
    <div class="metric">
      <div class="metric-value">{esc(value)}</div>
      <div class="metric-label">{esc(label)}</div>
      <div class="metric-note">{esc(note)}</div>
    </div>
    """


def card(title: str, owner: str, body: str, source: str) -> str:
    return f"""
    <div class="card">
      <h3>{esc(title)}</h3>
      <p class="owner">{esc(owner)}</p>
      <p>{esc(body)}</p>
      <p class="source">{source}</p>
    </div>
    """


def frontier_card(title: str, status: str, body: str, evidence: str, visual: str) -> str:
    return f"""
    <div class="frontier-card">
      <div class="frontier-status">{esc(status)}</div>
      <h3>{esc(title)}</h3>
      <p>{esc(body)}</p>
      <p class="source">{evidence}</p>
      <div class="visual-chip">{esc(visual)}</div>
    </div>
    """


def figure(path: str, caption: str) -> str:
    url = raw_url(path)
    return f"""
    <figure class="figure-card">
      <a href="{esc(github_url(path))}" target="_blank" rel="noreferrer">
        <img class="hero-img" src="{esc(url)}" alt="{esc(caption)}">
      </a>
      <figcaption>{esc(caption)} <span>GitHub raw image, click for repository file.</span></figcaption>
    </figure>
    """


def parse_contribution_people(contrib_md: str) -> list[dict[str, str]]:
    people: list[dict[str, str]] = []
    blocks = re.split(r"(?m)^## ", contrib_md)
    for block in blocks[1:]:
        lines = block.strip().splitlines()
        if not lines:
            continue
        name = lines[0].strip()
        if name in {"Commit 规范", "代码审查"}:
            continue
        role = ""
        scope = ""
        for i, line in enumerate(lines):
            if line.startswith("**Role:**"):
                role = line.replace("**Role:**", "").strip()
                # Some roles wrap onto the next line in Markdown.
                if i + 1 < len(lines) and lines[i + 1] and not lines[i + 1].startswith(("**", "#", "-", "|")):
                    role += " " + lines[i + 1].strip()
            if line.startswith("**Scope summary:**"):
                scope = line.replace("**Scope summary:**", "").strip()
        people.append({"name": name, "role": role, "scope": scope})
    return people


def parse_quick_results(readme: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    in_table = False
    for line in readme.splitlines():
        if line.startswith("| Finding |"):
            in_table = True
            continue
        if in_table:
            if not line.startswith("|"):
                break
            if set(line.replace("|", "").strip()) <= {"-", ":"}:
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 3:
                rows.append({"Finding": esc(cells[0]), "Result": esc(cells[1]), "Evidence": esc(cells[2])})
    return rows


def human_contributors(api_rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    humans = []
    for row in api_rows:
        login = row.get("login", "")
        if "cursor" in login.lower():
            continue
        humans.append(
            {
                "GitHub": f'<a href="{esc(row.get("html_url"))}" target="_blank" rel="noreferrer">{esc(login)}</a>',
                "Commits": esc(row.get("contributions")),
                "Role source": md_link("CONTRIBUTIONS.md") if login in {"ceilf6", "wfzark", "saayaya", "xyx12369"} else "GitHub contributor API",
            }
        )
    return humans


def build_demo() -> str:
    readme = fetch_text("README.md")
    contrib_md = fetch_text("CONTRIBUTIONS.md")
    status_md = fetch_text("docs/implementation-status.md")
    results_index = fetch_text("docs/results-index.md")
    repo_info = fetch_json(API)
    contributors = fetch_json(f"{API}/contributors?per_page=100")
    frontier_docs = fetch_json(f"{API}/contents/docs/frontier?ref={BRANCH}")

    people = parse_contribution_people(contrib_md)
    quick_results = parse_quick_results(readme)
    frontier_doc_rows = [
        {
            "file": f'<a href="{esc(item["html_url"])}" target="_blank" rel="noreferrer">{esc(item["name"])}</a>',
            "type": esc(item.get("type")),
            "source": "GitHub docs/frontier",
        }
        for item in frontier_docs
        if item.get("name", "").endswith(".md")
    ]

    online_source = f"{GH}/tree/{BRANCH}"
    slides = [
        f"""
        <section class="slide active" data-title="Online Source">
          <div class="eyebrow">GitHub-online evidence deck</div>
          <h1>Overlap-Aware Speaker ASR</h1>
          <p class="lead">This demo is rebuilt from the online GitHub repository: README, CONTRIBUTIONS, implementation status, results index, contributors API, and raw GitHub figures.</p>
          <div class="metrics">
            {metric("Online branch", BRANCH, "source of truth for this deck")}
            {metric("Stars / forks", f"{repo_info.get('stargazers_count', 0)} / {repo_info.get('forks_count', 0)}", "GitHub API")}
            {metric("Human contributors", str(len(human_contributors(contributors))), "cursor/tool accounts excluded")}
          </div>
          <p class="source big-source"><a href="{esc(online_source)}" target="_blank" rel="noreferrer">{esc(online_source)}</a></p>
        </section>
        """,
        f"""
        <section class="slide" data-title="Research Question">
          <div class="eyebrow">From online README.md</div>
          <h2>When should we separate, keep mixed, or escalate?</h2>
          <p>The online README frames the problem across transcription and emotion: separation can help recover masked speech, but it can also inject hallucination artifacts. The answer depends on overlap intensity, model scale, acoustic conditions, and whether the downstream goal is accurate text or faithful emotion.</p>
          <div class="flow-grid">
            <div class="flow-step"><div class="flow-title">Text objective</div><div class="flow-body">Minimize CER while avoiding hallucination and repetition.</div></div>
            <div class="flow-step"><div class="flow-title">Speaker objective</div><div class="flow-body">Keep speaker attribution visible with speaker CER and cpCER-lite.</div></div>
            <div class="flow-step"><div class="flow-title">Emotion objective</div><div class="flow-body">Do not assume the best transcript route is also the best affect route.</div></div>
          </div>
          <p class="source">{md_link("README.md")}</p>
        </section>
        """,
        f"""
        <section class="slide" data-title="Online Contributors">
          <div class="eyebrow">GitHub contributors + online CONTRIBUTIONS.md</div>
          <h2>Team members visible from the online repository.</h2>
          <p>The member names below come from GitHub contributors and the online contribution record. Cursor/tool accounts are not counted as human members.</p>
          {compact_table(human_contributors(contributors), ["GitHub", "Commits", "Role source"], 8)}
        </section>
        """,
        f"""
        <section class="slide" data-title="Contribution Records">
          <div class="eyebrow">Authoritative CONTRIBUTIONS.md</div>
          <h2>Contribution records from GitHub, by name.</h2>
          <div class="card-grid">
            {''.join(card(p['name'], p['role'] or 'Role recorded online', p['scope'] or 'Detailed contribution is recorded in the online CONTRIBUTIONS.md.', md_link('CONTRIBUTIONS.md')) for p in people)}
          </div>
        </section>
        """,
        f"""
        <section class="slide" data-title="Architecture">
          <div class="eyebrow">Online system architecture</div>
          <h2>Mixed, separated, cleaned, routed, evaluated.</h2>
          <p>The online README presents the full pipeline: ASR strategies, adaptive routing, evaluation, and frontier extensions.</p>
          {figure("results/figures/report/fig1_system_route_map.png", "System route map from online README")}
          <p class="source">{md_link("README.md")}</p>
        </section>
        """,
        f"""
        <section class="slide" data-title="Quick Results">
          <div class="eyebrow">Online README quick results</div>
          <h2>Core findings and evidence levels.</h2>
          {compact_table(quick_results, ["Finding", "Result", "Evidence"], 11)}
        </section>
        """,
        f"""
        <section class="slide" data-title="Mainline Matrix">
          <div class="eyebrow">Implementation status</div>
          <h2>Stable mainline vs optional/frontier.</h2>
          <div class="card-grid">
            {card("Stable mainline", "Gold benchmark + Whisper baselines", "Gold cases, mixed/separated Whisper, CER, error analysis, speaker CER, cpCER-lite, harness and CI.", md_link("docs/implementation-status.md"))}
            {card("Mainline experimental", "Routing and cascade", "Router v1/v2, risk-aware selector, compute-aware cascade, Mode B cascade tiers, synthetic silver validation.", md_link("docs/implementation-status.md"))}
            {card("Optional/frontier", "MeetEval, LLM, speaker-profile, AudioDepth", "Optional dependencies and exploratory branches are kept claim-bounded, not treated as stable production claims.", md_link("docs/implementation-status.md"))}
          </div>
          <p class="source">{md_link("docs/results-index.md")}</p>
        </section>
        """,
        f"""
        <section class="slide" data-title="Separation Tax">
          <div class="eyebrow">Frontier: separation and hallucination</div>
          <h2>Separation tax is heavy-tailed, not uniform.</h2>
          <div class="metrics">
            {metric("Crossover", "r* ≈ 0.17", "online README")}
            {metric("Failure shape", "heavy tail", "6/600 tracks blow up")}
            {metric("Detector", "AUC ≈ 1.0", "compression-ratio catastrophe gate")}
          </div>
          <div class="image-grid">
            <img src="{esc(raw_url('results/figures/cer_by_case.png'))}" alt="CER by case">
            <img src="{esc(raw_url('results/figures/error_type_by_case.png'))}" alt="Error type by case">
          </div>
        </section>
        """,
        f"""
        <section class="slide" data-title="Compute + Model Scale">
          <div class="eyebrow">Frontier: model scale and compute-aware routing</div>
          <h2>The route decision changes with model scale and cost.</h2>
          <div class="card-grid">
            {frontier_card("Whisper-base scale", "experimental/frontier", "The online README says Whisper-base at 1.93x compute eliminates the separation tax, turning the tiny-model problem into a scale finding.", md_link("README.md"), "model-scale result card")}
            {frontier_card("Compute-aware cascade", "mainline experimental", "Cost-aware and Mode B cascade tiers compare accuracy-first, balanced, and cost-first decisions.", md_link("docs/results-index.md"), "CER/cost tradeoff")}
            {frontier_card("Noise-robust router", "experimental/frontier", "Noise-robust routing recovers about 92% of oracle gap using decoder degeneracy signals.", md_link("docs/results-index.md"), "noise frontier")}
          </div>
          {figure("results/figures/cascade_tiers_cer_cost_tradeoff.png", "Cascade CER/cost tradeoff")}
        </section>
        """,
        f"""
        <section class="slide" data-title="Emotion + LLM">
          <div class="eyebrow">Frontier: ASR x LLM x emotion</div>
          <h2>Emotion is a separate downstream objective.</h2>
          <div class="card-grid">
            {frontier_card("Emotion separation tax", "experimental/frontier", "The online README reports the surprising opposite direction: separation helps emotion, even when ASR routing has a separation tax.", md_link("README.md"), "objective-aware routing")}
            {frontier_card("LLM emotion coverage", "experimental/frontier", "Local LLM semantic emotion reads implicit emotion about 7x more than a lexicon according to the online results index.", md_link("docs/results-index.md"), "semantic emotion")}
            {frontier_card("LLM rescoring / repair", "negative frontier", "LLM rescoring is not a free repair path: online README reports 0/26 helped and CER 0.316 to 0.798.", md_link("README.md"), "negative result")}
          </div>
          <p class="source">{md_link("docs/frontier/asr_llm_emotion_capstone.md")} · {md_link("docs/emotion_frontier.md")}</p>
        </section>
        """,
        f"""
        <section class="slide" data-title="Evaluation Frontiers">
          <div class="eyebrow">Frontier: evaluation systems</div>
          <h2>Evaluation is bigger than one CER number.</h2>
          <div class="card-grid">
            {frontier_card("MeetEval / cpWER", "optional/frontier", "Official meeting-style evaluation is staged as optional integration with readiness and compatibility notes.", md_link("docs/results-index.md"), "cpWER bridge")}
            {frontier_card("Speaker-profile diagnostics", "frontier scaffold", "Speaker-profile work is diagnostic and claim-bounded; it supports attribution risk investigation.", md_link("docs/implementation-status.md"), "speaker profile")}
            {frontier_card("Cross-benchmark analysis", "evaluation system", "Evaluation System & Cross-Benchmark Analysis is recorded as 张浩豪 / haohaozhang776's contribution.", md_link("CONTRIBUTIONS.md"), "benchmark alignment")}
          </div>
        </section>
        """,
        f"""
        <section class="slide" data-title="Separation Phase">
          <div class="eyebrow">Frontier: separation phase diagram</div>
          <h2>Separation is visualized as a phase decision.</h2>
          <div class="card-grid">
            {frontier_card("Separation Phase Diagram", "Mode C frontier", "梁跃川 / liang-yuechuan is credited online for the Separation Phase Diagram design and implementation.", md_link("CONTRIBUTIONS.md"), "phase boundary")}
            {frontier_card("Phase diagram repair + learned router", "bugfix + model design", "邵俊霖 / saayaya is credited online for phase diagram repair, learned router design, implementation, and bugfix.", md_link("CONTRIBUTIONS.md"), "learned router")}
            {frontier_card("Mode B cascade", "compute-aware", "谢宇轩 / xyx12369 is credited online for compute-aware three-tier cascade recognition.", md_link("CONTRIBUTIONS.md"), "three-tier cascade")}
          </div>
          {figure("results/figures/cer_runtime_tradeoff.png", "Online CER/runtime tradeoff figure")}
        </section>
        """,
        f"""
        <section class="slide" data-title="AudioDepth">
          <div class="eyebrow">Frontier branch only</div>
          <h2>AudioDepth is one exploratory branch, not the whole project.</h2>
          <p>Online `docs/frontier/audio-depth-router.md` frames AudioDepth as pre-ASR acoustic triage inspired by RGB-D / depth-style visual recognition. It complements transcript-instability features; it does not replace them.</p>
          <div class="image-grid">
            <img src="{esc(raw_url('docs/assets/audio-depth/audio_depth_3d_occlusion_landscape.png'))}" alt="AudioDepth 3D occlusion landscape">
            <img src="{esc(raw_url('docs/assets/audio-depth/audio_depth_channel_triptych.png'))}" alt="AudioDepth channel triptych">
          </div>
          <p class="source">{md_link("docs/frontier/audio-depth-router.md")}</p>
        </section>
        """,
        f"""
        <section class="slide" data-title="Frontier Index">
          <div class="eyebrow">Online docs/frontier index</div>
          <h2>Frontier files visible in the GitHub repository.</h2>
          {compact_table(frontier_doc_rows, ["file", "type", "source"], 8)}
        </section>
        """,
        f"""
        <section class="slide" data-title="GitHub Walkthrough">
          <div class="eyebrow">Final 3 minutes</div>
          <h2>Show the repository, not only the slides.</h2>
          <div class="card-grid">
            {card("README", "Project entry", "Research question, quick results, architecture, mainline/frontier boundary.", md_link("README.md"))}
            {card("CONTRIBUTIONS", "Team record", "Named roles and contribution narratives from the online source of truth.", md_link("CONTRIBUTIONS.md"))}
            {card("Implementation status", "Claim matrix", "Stable, experimental, optional, and frontier labels.", md_link("docs/implementation-status.md"))}
            {card("Results index", "Evidence map", "Curated result entry points and frontier notes.", md_link("docs/results-index.md"))}
          </div>
        </section>
        """,
        f"""
        <section class="slide" data-title="Boundaries">
          <div class="eyebrow">Do not overclaim</div>
          <h2>The strongest demo is honest.</h2>
          <div class="flow-grid">
            <div class="flow-step"><div class="flow-title">Stable</div><div class="flow-body">Gold benchmark, Whisper baselines, CER/error/speaker-aware evaluation, router evidence.</div></div>
            <div class="flow-step"><div class="flow-title">Experimental</div><div class="flow-body">Compute cascade, Mode B tiers, synthetic validation, model-scale and noise frontiers.</div></div>
            <div class="flow-step"><div class="flow-title">Frontier only</div><div class="flow-body">AudioDepth, emotion/LLM, speaker profile, MeetEval optional paths, and agentic scaffolds.</div></div>
          </div>
          <p class="source">{md_link("docs/implementation-status.md")} · {md_link("CONTRIBUTIONS.md")}</p>
        </section>
        """,
    ]

    slide_data = {"minutes": 10}
    css = """
    :root { --bg:#07111f; --panel:#111c2f; --text:#f7f9fc; --muted:#b5c1d5; --line:#31415f; --accent:#66e0b5; --gold:#ffd166; --hot:#ff7a70; }
    * { box-sizing:border-box; }
    body { margin:0; background:#07111f; color:var(--text); font:16px/1.55 Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    .shell { min-height:100vh; display:grid; grid-template-rows:auto 1fr auto; }
    header, footer { display:flex; align-items:center; justify-content:space-between; gap:1rem; padding:1rem 1.35rem; border-color:var(--line); background:rgba(7,17,31,.92); }
    header { border-bottom:1px solid var(--line); position:sticky; top:0; z-index:10; }
    footer { border-top:1px solid var(--line); color:var(--muted); }
    .brand { font-weight:850; }
    .slide { display:none; min-height:calc(100vh - 8rem); padding:2.3rem clamp(1.2rem,3.4vw,3.5rem); }
    .slide.active { display:block; }
    h1, h2 { max-width:74rem; margin:.2rem 0 1rem; line-height:1.03; letter-spacing:0; }
    h1 { font-size:clamp(3rem,7vw,6.3rem); }
    h2 { font-size:clamp(2.1rem,5vw,4.8rem); }
    h3 { margin:.1rem 0 .35rem; font-size:1.25rem; }
    p { color:var(--muted); max-width:72rem; font-size:1.16rem; }
    .lead { font-size:1.35rem; color:#d8e0ef; }
    .eyebrow { color:var(--accent); font-weight:850; text-transform:uppercase; letter-spacing:.08em; }
    a { color:#9fe7ff; text-decoration:none; }
    a:hover { text-decoration:underline; }
    .metrics, .card-grid, .flow-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(15rem,1fr)); gap:1rem; margin:1.3rem 0; max-width:82rem; }
    .metric, .card, .frontier-card, .flow-step { border:1px solid var(--line); background:rgba(17,28,47,.84); border-radius:8px; padding:1rem; }
    .metric-value { font-size:2rem; font-weight:900; color:var(--text); }
    .metric-label, .owner, .flow-title { color:var(--accent); font-weight:850; }
    .metric-note, .source { color:var(--muted); font-size:.98rem; }
    .big-source { font-size:1.2rem; }
    .frontier-status, .visual-chip { display:inline-block; border:1px solid var(--line); border-radius:999px; padding:.2rem .55rem; color:var(--gold); font-weight:750; font-size:.86rem; }
    .visual-chip { color:var(--accent); margin-top:.35rem; }
    .figure-card { width:min(100%,82rem); margin:1rem 0; }
    .hero-img { display:block; width:100%; max-height:56vh; object-fit:contain; background:white; border:1px solid var(--line); border-radius:8px; }
    figcaption { color:var(--muted); margin-top:.45rem; }
    figcaption span { color:var(--gold); }
    .image-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(20rem,1fr)); gap:1rem; margin-top:1rem; max-width:82rem; }
    .image-grid img { width:100%; max-height:48vh; object-fit:contain; background:white; border:1px solid var(--line); border-radius:8px; }
    table { border-collapse:collapse; width:min(100%,82rem); margin:1.1rem 0; font-size:1rem; background:rgba(17,28,47,.84); }
    th, td { border:1px solid var(--line); padding:.68rem .75rem; text-align:left; vertical-align:top; }
    th { color:var(--accent); background:#0c1628; }
    .controls { display:flex; gap:.6rem; align-items:center; flex-wrap:wrap; }
    button { border:1px solid var(--line); border-radius:8px; background:#17243a; color:var(--text); padding:.62rem .85rem; font-weight:800; cursor:pointer; }
    button:hover { color:var(--accent); border-color:var(--accent); }
    .pill { border:1px solid var(--line); border-radius:999px; padding:.35rem .65rem; color:var(--muted); }
    .progress { height:.5rem; background:#1d2a43; border-radius:999px; overflow:hidden; min-width:13rem; }
    .progress span { display:block; height:100%; width:0; background:linear-gradient(90deg,var(--accent),var(--gold)); }
    @media (max-width:820px) { header { flex-direction:column; align-items:flex-start; } .progress { width:100%; } }
    """
    js = f"""
    const DATA = {json.dumps(slide_data)};
    const params = new URLSearchParams(window.location.search);
    const autoplay = params.get('autoplay') === '1';
    const autoplaySeconds = Math.max(60, Number(params.get('seconds') || 420));
    let current = 0;
    const slides = [...document.querySelectorAll('.slide')];
    const bar = document.querySelector('#progressBar');
    const counter = document.querySelector('#counter');
    const title = document.querySelector('#titles');
    function show(i) {{
      current = Math.max(0, Math.min(slides.length - 1, i));
      slides.forEach((s, idx) => s.classList.toggle('active', idx === current));
      counter.textContent = `${{current + 1}} / ${{slides.length}}`;
      title.textContent = slides[current].dataset.title || '';
      bar.style.width = `${{((current + 1) / slides.length) * 100}}%`;
    }}
    document.querySelector('#prev').onclick = () => show(current - 1);
    document.querySelector('#next').onclick = () => show(current + 1);
    document.addEventListener('keydown', (e) => {{
      if (e.key === 'ArrowRight' || e.key === ' ') show(current + 1);
      if (e.key === 'ArrowLeft') show(current - 1);
    }});
    show(0);
    if (autoplay) {{
      const stepMs = Math.floor((autoplaySeconds * 1000) / Math.max(1, slides.length - 1));
      setInterval(() => {{ if (current < slides.length - 1) show(current + 1); }}, stepMs);
    }}
    """

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Overlap-Aware Speaker ASR Online GitHub Demo</title>
  <style>{css}</style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <div class="brand">Overlap-Aware Speaker ASR · GitHub Online Demo</div>
        <div class="pill" id="titles">Online Source</div>
      </div>
      <div class="controls">
        <button id="prev">Back</button>
        <button id="next">Next</button>
        <span class="pill" id="counter">1 / {len(slides)}</span>
      </div>
      <div class="progress"><span id="progressBar"></span></div>
    </header>
    <main>{''.join(slides)}</main>
    <footer>
      <span>Source: online GitHub main branch, contributors API, raw figures, README, CONTRIBUTIONS, docs/results.</span>
      <span>Keys: Left / Right / Space. Autoplay: ?autoplay=1&amp;seconds=420.</span>
    </footer>
  </div>
  <script>{js}</script>
</body>
</html>
"""


def main() -> int:
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_demo(), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} from {GH}/tree/{BRANCH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
