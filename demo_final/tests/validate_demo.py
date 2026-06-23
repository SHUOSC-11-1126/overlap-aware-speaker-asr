from __future__ import annotations
import json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[0]
BAD=[chr(47)+'Users'+chr(47)+'ark','Running '+'Whisper now','Live separation '+'in progress','Model is currently '+'recognizing speech']

def fail(msg): print('FAIL:',msg); sys.exit(1)
def read(p): return p.read_text(encoding='utf-8', errors='ignore')
files=[p for p in ROOT.rglob('*') if p.is_file() and p.suffix.lower() not in {'.png','.wav'}]
for p in files:
    t=read(p)
    for b in BAD:
        if b in t: fail(f'{b} found in {p}')
    if re.search(chr(47)+'Users'+chr(47)+r'[^\s"\']+', t): fail(f'absolute user path in {p}')
for required in ['index.html','styles.css','app.js','demo_data.js','README.md','PRESENTER_RUNBOOK.md','EVIDENCE_MANIFEST.md','backup_slides.html','start_windows.bat','start_macos.command','start_linux.sh']:
    if not (ROOT/required).exists(): fail(f'missing {required}')
if 'Replay Demo — all outputs are precomputed from committed research artifacts.' not in read(ROOT/'index.html'): fail('missing replay notice')
if 'fetch(' in read(ROOT/'app.js') or 'XMLHttpRequest' in read(ROOT/'app.js'): fail('file:// unsafe network/json loading')
data_text=read(ROOT/'demo_data.js')
data=json.loads(data_text.split('=',1)[1].strip().rstrip(';'))
if len(data.get('contributors',[])) < 6: fail('too few contributors; do not list only three people')
contrib_count=sum(1 for line in read(REPO/'CONTRIBUTIONS.md').splitlines() if line.startswith('## ') and 'Commit 规范' not in line and '代码审查' not in line)
if len(data['contributors']) != contrib_count: fail('contribution member count does not match CONTRIBUTIONS.md')
for contributor in data['contributors']:
    if not contributor.get('role') or not contributor.get('scope'):
        fail(f'empty contributor role/scope: {contributor.get("name")}')
    fields=[contributor.get('role',''), contributor.get('scope','')] + contributor.get('highlights',[])
    for field in fields:
        if any(mark in field for mark in ['**', '[', '](', '*Role:**']):
            fail(f'markdown residue in contributor card: {contributor.get("name")}: {field}')
        if field.strip() in {'--', '---'}:
            fail(f'dash-only contributor highlight: {contributor.get("name")}')
        if field.rstrip().endswith((' and', ' or', ' 和', ' 与', ' 以及')):
            fail(f'truncated contributor text: {contributor.get("name")}: {field}')
        if field.startswith(('src/', 'tests/', 'scripts/')):
            fail(f'module list used as presentation text: {contributor.get("name")}: {field}')
    if not contributor.get('highlights'):
        fail(f'empty contributor highlights: {contributor.get("name")}')
if 'Frontier Branch Only' not in data_text or 'Not merged into stable mainline' not in data_text or 'Not production-ready' not in data_text: fail('AudioDepth boundary missing')
if 'origin/frontier/audio-depth-router' not in data_text: fail('AudioDepth branch source missing')
for key,src in data['sources'].items():
    for f in ['path','branch','commit','evidenceLevel']:
        if not src.get(f): fail(f'source {key} missing {f}')
for c in data['cases'].values():
    for part in ['reference','mixed','separated','cleaned']:
        if not c[part].get('sourcePath') or not c[part].get('sourceId'): fail(f'transcript source missing {c["caseId"]} {part}')
    if not (ROOT/c['audio']).exists(): fail(f'audio missing {c["audio"]}')
for rel in re.findall(r'(?:src|href)="([^"]+)"', read(ROOT/'index.html')+read(ROOT/'backup_slides.html')):
    if rel.startswith(('http','#')): continue
    if not (ROOT/rel).exists(): fail(f'linked asset missing {rel}')
for fig in data['assets']['figures'].values():
    if not (ROOT/fig).exists(): fail(f'figure missing {fig}')
for fig in data['assets']['audiodepth'].values():
    if not (ROOT/fig).exists(): fail(f'audiodepth figure missing {fig}')
for shot in ['01_overview.png','02_mixed_win.png','03_separated_win.png','04_separation_tax.png','05_frontiers.png','06_limitations.png']:
    if not (ROOT/'screenshots'/shot).exists(): fail(f'screenshot missing {shot}')
if data['cases']['mixedWin']['caseId'] not in ['LightOverlap','MidOverlap']: fail('mixed-win case is not preferred case')
if data['cases']['separatedWin']['caseId'] not in ['HeavyOverlap','OppositeOverlap','NoOverlap']: fail('separated-win case invalid')
expected_missing='Raw separated transcript artifact is not bundled in main. The committed CER value is shown, and no transcript is reconstructed or fabricated.'
if data['cases']['mixedWin']['separated']['text'] != expected_missing:
    fail('LightOverlap missing raw separated transcript notice changed')
if 'control separated-win case' not in data['cases']['separatedWin']['label'].lower():
    fail('NoOverlap is not labeled as control separated-win case')
if 'HeavyOverlap and OppositeOverlap also favor separated ASR in the gold CER table.' not in data['cases']['separatedWin']['why']:
    fail('Separated-win case does not mention HeavyOverlap and OppositeOverlap')
app_text=read(ROOT/'app.js')
if 'No single fixed route dominates across all evaluated conditions.' not in app_text:
    fail('polished fixed-route conclusion missing from app')
runbook=read(ROOT/'PRESENTER_RUNBOOK.md')
if 'Overview → Core Routing: Mixed-win → Core Routing: Separated-win → Separation Tax → Routing + Evaluation → Team Frontiers → Evidence' not in runbook:
    fail('runbook click path is stale')
if 'fixed routing is wrong' in runbook or 'fixed routing is wrong' in app_text:
    fail('old conclusion wording remains')
print('validate_demo OK')
print(f'contributors={len(data["contributors"])} sources={len(data["sources"])}')
