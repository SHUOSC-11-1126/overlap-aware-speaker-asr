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
print('validate_demo OK')
print(f'contributors={len(data["contributors"])} sources={len(data["sources"])}')
