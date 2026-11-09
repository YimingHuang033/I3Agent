"""Bounded, sequential live smoke suite; failures remain explicit per run."""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--methods',nargs='+',default=['stateforge','voi','revoir','stitch','stateforge_revoir','stitch_revoir','p1','p2']);p.add_argument('--name',default='methods-v1');a=p.parse_args()
root=Path(__file__).resolve().parent
base=root/'.local/suites'/a.name;base.mkdir(parents=True,exist_ok=False)
rows=[]
for method in a.methods:
    output=base/method
    with (base/(method+'.log')).open('w') as log:
        try:
            r=subprocess.run([sys.executable,'-m','novours','run','--config',str(root/'configs'/f'lifesim-{method}.json'),'--output',str(output)],env={**os.environ,'PYTHONPATH':str(root)},stdout=log,stderr=subprocess.STDOUT,timeout=1200)
            rows.append({'method':method,'exit_code':r.returncode,'output':str(output)})
        except subprocess.TimeoutExpired:rows.append({'method':method,'exit_code':'timeout','output':str(output)})
    (base/'progress.json').write_text(json.dumps({'finished':len(rows),'total':len(a.methods),'runs':rows},indent=2))
    print(json.dumps(rows[-1]),flush=True)
sys.exit(int(any(r['exit_code']!=0 for r in rows)))
