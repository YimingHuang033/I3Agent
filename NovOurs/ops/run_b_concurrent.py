"""Sharded concurrent runner: one shard per job, TP=1 endpoint, circuit breaker."""
import json, os, subprocess, sys, time, fcntl
from pathlib import Path

V7 = Path('/projects/I3Agent/NovOurs/.local/campaigns/20261110-slai-qwen27-gemma31-v8')
ROOT = Path('/projects/I3Agent')
model, K, hours, shard, nshards = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])

plan = json.loads((V7 / model / 'B-lifesim.json').read_text())
out = V7 / model / 'runs' / 'B'
out.mkdir(parents=True, exist_ok=True)
guard = open(out / ('.runner-%d.lock' % shard), 'w')
fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)

interp = {'lifesim': 'lifesim-venv/bin/python', 'pi': '.venv-pibench311/bin/python',
          'mempa': 'NovOurs/.local/venv/bin/python'}
deadline = time.time() + hours * 3600


def complete(job_id):
    d = out / job_id
    if not d.exists():
        return False
    for p in sorted(d.glob('attempt-*')):
        try:
            if json.loads((p / 'status.json').read_text()).get('status') == 'complete':
                return True
        except Exception:
            pass
    return False


def fresh_attempt(job_id):
    d = out / job_id
    for k in range(1, 50):
        p = d / ('attempt-%04d' % k)
        if not p.exists():
            p.mkdir(parents=True)
            return p
        try:
            if json.loads((p / 'status.json').read_text()).get('status') == 'complete':
                return None
        except Exception:
            return p
    return None


jobs = [j for i, j in enumerate(plan['jobs']) if i % nshards == shard]
queue = [j for j in jobs if not complete(j['id'])]
running, done, fail, consecutive_fail = {}, 0, 0, 0
progress = out / ('progress-shard-%d.json' % shard)


def dump():
    json.dump({'model': model, 'shard': shard, 'nshards': nshards, 'shard_total': len(jobs),
               'done': done, 'failed': fail, 'running': len(running), 'queue': len(queue),
               'deadline': deadline, 'updated': time.time()}, open(progress, 'w'))


def say(msg):
    print('[%s] %s' % (time.strftime('%H:%M:%S'), msg), flush=True)


say('RUNNER2_START model=%s shard=%d/%d K=%d queue=%d' % (model, shard, nshards, K, len(queue)))
dump()
while queue or running:
    while queue and len(running) < K and time.time() < deadline:
        job = queue.pop(0)
        ad = fresh_attempt(job['id'])
        if ad is None:
            done += 1
            continue
        json.dump(job['config'], open(ad / 'config.json', 'w'))
        py = str(ROOT / interp[job['config']['source']])
        env = {**os.environ, 'PYTHONPATH': str(ROOT / 'NovOurs')}
        p = subprocess.Popen([py, '-m', 'novours', 'run', '--config', str(ad / 'config.json'),
                              '--output', str(ad)], cwd=str(ROOT), env=env,
                             stdout=open(ad / 'process.log', 'w'), stderr=subprocess.STDOUT)
        running[p] = job['id']
    time.sleep(5)
    for p in list(running):
        if p.poll() is not None:
            jid = running.pop(p)
            if complete(jid):
                done += 1
                consecutive_fail = 0
            else:
                fail += 1
                consecutive_fail += 1
            if (done + fail) % 25 == 0:
                say('PROGRESS done=%d failed=%d running=%d queue=%d' % (done, fail, len(running), len(queue)))
            dump()
    if consecutive_fail >= 20 and done == 0:
        say('CIRCUIT_BREAKER 20 consecutive failures before any success')
        break
    if time.time() > deadline:
        say('DEADLINE_REACHED running=%d' % len(running))
        break
for p in running:
    p.terminate()
say('RUNNER2_DONE done=%d failed=%d remaining=%d' % (done, fail, len(queue)))

