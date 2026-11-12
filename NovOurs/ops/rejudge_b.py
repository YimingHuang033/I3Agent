"""Re-judge failed attempts using the CURRENT plan config (latest judge settings).

Run with the lifesim venv interpreter:
  /projects/I3Agent/lifesim-venv/bin/python rejudge.py <campaign>/<model> [--dry-run]
"""
import json, sys, os
from pathlib import Path

sys.path.insert(0, '/projects/I3Agent/NovOurs')


def main():
    base = Path(sys.argv[1])
    dry = '--dry-run' in sys.argv
    shard = int(sys.argv[sys.argv.index('--shard')+1]) if '--shard' in sys.argv else 0
    nshards = int(sys.argv[sys.argv.index('--nshards')+1]) if '--nshards' in sys.argv else 1
    plan = json.loads((base / 'B-lifesim.json').read_text())
    by_id = {j['id']: j['config'] for j in plan['jobs']}
    from novours.core import Journal
    from novours.adapters.lifesim import evaluate

    ok = failed = skipped = 0
    all_atts = sorted(base.glob('runs/B/life-*/attempt-*'))
    for idx, att in enumerate(all_atts):
        if idx % nshards != shard:
            continue
        jid = att.parent.name
        st_path = att / 'status.json'
        try:
            status = json.loads(st_path.read_text()).get('status') if st_path.exists() else None
        except Exception:
            status = None
        if status == 'complete':
            skipped += 1
            continue
        if not (att / 'logs').is_dir() or jid not in by_id:
            skipped += 1
            continue
        if dry:
            print('WOULD_REJUDGE', jid, att.name, flush=True)
            ok += 1
            continue
        cfg = by_id[jid]                      # current judge/model settings
        journal = Journal(att / 'trace.jsonl')
        journal.add('rejudge_start', attempt=str(att), judge=cfg['judge'])
        try:
            scores = evaluate(cfg, att, journal)
            json.dump({'status': 'complete', 'rejudged': True }, open(st_path, 'w'))
            json.dump(scores, open(att / 'scores.json', 'w'))
            journal.add('rejudge_done', scores=scores)
            ok += 1
            if ok % 10 == 0:
                print('PROGRESS ok=%d failed=%d skipped=%d' % (ok, failed, skipped), flush=True)
        except Exception as exc:
            journal.add('rejudge_failed', error=type(exc).__name__, message=str(exc)[:300])
            failed += 1
            print('FAIL', jid, att.name, type(exc).__name__, str(exc)[:160], flush=True)
    print('REJUDGE_DONE ok=%d failed=%d skipped=%d' % (ok, failed, skipped), flush=True)


if __name__ == '__main__':
    main()

