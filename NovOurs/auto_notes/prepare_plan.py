"""Prepare the operations pilot plans without loading models or calling APIs."""
import argparse
import copy
import hashlib
import json
import random
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'NovOurs'))
from novours.core import digest, dump

METHODS = ['native', 'direct', 'stateforge', 'voi', 'revoir',
           'stateforge_revoir', 'stitch_official', 'p1', 'p2', 'p3']


def config(name):
    return json.loads((ROOT / 'NovOurs/configs' / name).read_text())


def job(name, cfg, method):
    cfg = copy.deepcopy(cfg)
    cfg['agent'] = {'method': method, 'hypotheses': 2, 'actions': 2,
                    'questions': 1, 'max_questions': 2}
    # One shared 32K endpoint makes context capacity the same across methods.
    cfg['actor']['base_url'] = 'http://127.0.0.1:8012/v1'
    return {'id': name + '-' + method, 'config': cfg, 'config_sha256': digest(cfg)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--seed', type=int, default=20261110)
    args = p.parse_args()
    out = args.output.resolve()
    if out.exists():
        raise SystemExit('Output exists; choose a new campaign directory. Nothing overwritten.')
    # Validate source data before creating the campaign directory.
    inputs = {}
    selected = []
    excluded = []
    for setting in ['single_session', 'long_horizon']:
        path = ROOT / 'benchmarks/sources/lifesim/data' / setting / 'events.jsonl'
        rows = sorted((json.loads(line) for line in path.read_text().splitlines()),
                      key=lambda row: row['id'])
        counts = Counter(r['id'] for r in rows)
        excluded.extend({'setting': setting, 'sequence_id': key, 'occurrences': count,
                         'reason': 'ambiguous_duplicate_id'}
                        for key, count in sorted(counts.items()) if count > 1)
        rows = [row for row in rows if counts[row['id']] == 1]
        if len(rows) < 30:
            raise SystemExit('Source has fewer than 30 unambiguous sequence IDs: ' + setting)
        inputs[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        users = path.with_name('users.jsonl')
        inputs[str(users.relative_to(ROOT))] = hashlib.sha256(users.read_bytes()).hexdigest()
        sample = random.Random(str(args.seed) + ':' + setting).sample(rows, 30)
        for row in sorted(sample, key=lambda r: r['id']):
            if not row['events']:
                raise SystemExit('Empty native sequence: ' + row['id'])
            selected.append({'setting': setting, 'sequence_id': row['id'],
                             'user_id': row['user_id'], 'source_path': str(path.relative_to(ROOT)),
                             'sequence_sha256': digest(row)})
    a = [job(name, cfg, method)
         for name, cfg in [('lifesim', config('smoke.json')),
                           ('pi', config('pi-tools-native.json')),
                           ('mempa', config('mempa-native.json'))]
         for method in ['native', 'direct', 'p3']]
    b = []
    for i, selection in enumerate(selected):
        cfg = config('smoke.json')
        cfg.pop('sequence_index', None)
        cfg.update(setting=selection['setting'], sequence_id=selection['sequence_id'],
                   events=1, rounds=2)
        b.extend(job(f'life-{i:03d}', cfg, method) for method in METHODS)
    c = [job('researcher-task-011', config('pi-tools-native.json'), method) for method in METHODS]
    out.mkdir(parents=True)
    for name, jobs in [('A-regression', a), ('B-lifesim', b), ('C-pi', c)]:
        dump(out / (name + '.json'), {'version': 1, 'jobs': jobs, 'jobs_sha256': digest(jobs)})
    dump(out / 'selection.json', selected)
    dump(out / 'excluded.json', excluded)
    annotations = [{**s, 'review_status': 'pending', 'category': None,
                    'evidence_refs': [], 'notes': ''} for s in selected]
    (out / 'coverage.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in annotations))
    version = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True, text=True)
    dump(out / 'campaign.json', {'schema_version': 1, 'seed': args.seed,
                               'preparation_git_head': version.stdout.strip(),
                               'source_file_sha256': inputs, 'methods': METHODS,
                               'jobs': {'A-regression': len(a), 'B-lifesim': len(b), 'C-pi': len(c)},
                               'model_calls': 0, 'execution_started': False,
                               'mempa_full': 'blocked: acc_list/timeline/probe integration required'})
    print(json.dumps({'output': str(out), 'jobs': [len(a), len(b), len(c)], 'model_calls': 0}))


if __name__ == '__main__':
    main()
