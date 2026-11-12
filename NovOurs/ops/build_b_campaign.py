"""Build v8: B = 200 sequences (40 single + 160 long) x 10 methods = 2000 jobs, fresh run."""
import json, sys, shutil, random, collections
from pathlib import Path
sys.path.insert(0, '/projects/I3Agent/NovOurs')
from novours.core import digest, dump

BASE = Path('/projects/I3Agent/NovOurs/.local/campaigns')
V7 = BASE / '20261110-slai-qwen27-gemma31-v7'
V8 = BASE / '20261110-slai-qwen27-gemma31-v8'
ROOT = Path('/projects/I3Agent')
SEED = 20261110
SIZES = {'single_session': 60, 'long_horizon': 240}

if V8.exists():
    shutil.rmtree(V8)

selected, excluded = [], []
for setting in ['single_session', 'long_horizon']:
    p = ROOT / 'benchmarks/sources/lifesim/data' / setting / 'events.jsonl'
    rows = sorted((json.loads(l) for l in p.read_text().splitlines() if l.strip()), key=lambda r: r['id'])
    counts = collections.Counter(r['id'] for r in rows)
    excluded += [{'setting': setting, 'sequence_id': k, 'occurrences': v,
                  'reason': 'ambiguous_duplicate_id'} for k, v in sorted(counts.items()) if v > 1]
    rows = [r for r in rows if counts[r['id']] == 1]
    n = SIZES[setting]
    if len(rows) < n:
        raise SystemExit('%s has only %d unambiguous rows' % (setting, len(rows)))
    sample = random.Random('%d:%s' % (SEED, setting)).sample(rows, n)
    for row in sorted(sample, key=lambda r: r['id']):
        selected.append({'setting': setting, 'sequence_id': row['id'], 'user_id': row['user_id'],
                         'source_path': str(p.relative_to(ROOT)), 'sequence_sha256': digest(row)})
print('selected', len(selected), dict(collections.Counter(s['setting'] for s in selected)))

methods = json.loads((V7 / 'gemma-4-31B-it/campaign.json').read_text())['methods']

for model in ['gemma-4-31B-it', 'Qwen3.8-27B']:
    src = V7 / model
    dst = V8 / model
    dst.mkdir(parents=True)
    for name in ['A-regression.json', 'C-pi.json', 'campaign.json', 'runtime-frozen.json']:
        if (src / name).exists():
            shutil.copy2(src / name, dst / name)
        else:
            print('missing (skipped):', model, name)
    v7b = json.loads((src / 'B-lifesim.json').read_text())
    templates = {}
    for j in v7b['jobs']:
        m = j['id'].rsplit('-', 1)[1]
        if m not in templates:
            templates[m] = j['config']
    assert set(templates) == set(methods)
    jobs = []
    for i, s in enumerate(selected):
        for m in methods:
            cfg = json.loads(json.dumps(templates[m]))
            cfg.pop('sequence_index', None)
            cfg.update(setting=s['setting'], sequence_id=s['sequence_id'], events=1, rounds=2)
            jobs.append({'id': 'life-%03d-%s' % (i, m), 'config': cfg, 'config_sha256': digest(cfg)})
    dump(dst / 'B-lifesim.json', {'version': 1, 'jobs': jobs, 'jobs_sha256': digest(jobs)})
    ann = [{**s, 'review_status': 'waived_by_owner', 'category': None, 'evidence_refs': [],
            'notes': 'v8 gate-free'} for s in selected]
    (dst / 'coverage.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in ann))
    dump(dst / 'selection.json', selected)
    dump(dst / 'excluded.json', excluded)
    meta = json.loads((dst / 'campaign.json').read_text())
    meta['previous_campaign'] = str(src)
    meta['restart_reason'] = ('owner request 2026-11-11: rerun including previously failed jobs on a fresh run tree; '
                              'B reduced to 300 sequences (60 single_session + 240 long_horizon) x 10 methods = 3000; '
                              'runtime unchanged 131072 ctx, actor max_tokens 32768')
    meta['jobs'] = {'A-regression': 9, 'B-lifesim': len(jobs), 'C-pi': 10}
    meta['coverage_gate'] = 'waived_by_owner'
    meta['preparation_only'] = True
    meta.pop('execution_started', None)
    meta['sample_mix'] = {'single_session': SIZES['single_session'], 'long_horizon': SIZES['long_horizon'],
                          'note': 'v8: 3000 jobs, fresh runs, 20:80 ratio'}
    dump(dst / 'campaign.json', meta)
    print(model, 'B jobs', len(jobs), 'sha', digest(jobs)[:16])

dump(V8 / 'v8-change-note.json', {
    'date': '2026-11-11',
    'previous': str(V7),
    'changes': ['B reduced to 3000 jobs (300 sequences x 10 methods)',
                'fresh run tree: all previous failures re-run, nothing reused',
                'sample 60 single_session + 240 long_horizon (20:80)'],
    'unchanged': ['128K context (131072)', 'actor max_tokens 32768', 'temperature 0', 'thinking false',
                  'A-regression 9 per model', 'C-pi 10 per model', 'scoring'],
})
print('V8_READY', V8)

