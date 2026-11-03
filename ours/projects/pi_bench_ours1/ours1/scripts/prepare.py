"""Offline-only preparation audit. Never imports protocol/model clients."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def rows(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]

def main():
    public = rows(ROOT/'data/public/episodes.jsonl')
    gold = rows(ROOT/'data/private/oracle.jsonl')
    pairs = json.loads((ROOT/'data/private/pairs.json').read_text())
    cfg = json.loads((ROOT/'configs/experiment.json').read_text())
    assert cfg['execution_enabled'] is False and cfg['training_enabled'] is False
    assert len(public) == len(gold) == cfg['generation']['expected_episodes']
    assert len(pairs) == cfg['generation']['expected_pairs']
    p = {x['episode_id']: x for x in public}
    g = {x['episode_id']: x for x in gold}
    assert len(p) == len(public) and set(p) == set(g)
    assert {x['condition'] for x in gold} == {'S','R','U0','U1'}
    for pair in pairs:
        a,b = [p[k] for k in pair['episode_ids']]
        for key in ['initial_request','slot','candidates','scenario']:
            assert a[key] == b[key], (pair,key)
        if pair['kind'] == 'ambiguity_twins':
            aa,bb = dict(a),dict(b);aa.pop('episode_id');bb.pop('episode_id')
            assert aa == bb, pair
        else:
            assert a['history'][:2] == b['history'][:2]
            assert a['history'][2]['text'] != b['history'][2]['text']
    for x in public:
        assert not ({'condition','target','phase_targets','pair_id','template_id'} & set(x))
        targets = g[x['episode_id']]['phase_options']
        options = {o['option_id'] for o in x['candidates']}
        assert all(t in options for t in targets)
        assert len({h['id'] for h in x['history']}) == len(x['history'])
    for file in ROOT.rglob('*.py'):
        ast.parse(file.read_text(), filename=str(file))
    for file in (ROOT/'configs').glob('*.json'):
        json.loads(file.read_text())
    report = {'status':'static_preparation_passed','model_calls':0,'episodes_executed':0,
        'training_steps':0,'base_templates':cfg['generation']['base_templates'], 'public_episodes':len(public),'paired_sets':len(pairs),
        'proposed_baselines':list(cfg['baselines']),
        'functional_protocol_tests_run':False,'native_integration_run':False,
        'sha256':{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest()
                  for f in sorted(ROOT.rglob('*')) if f.is_file() and f.suffix in ['.json','.jsonl','.py']
                  and f.name != 'preparation-report.json'}}
    (ROOT/'preparation-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'sha256'},ensure_ascii=False))

if __name__ == '__main__':
    main()
