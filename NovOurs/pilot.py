"""Freeze an explicit config matrix, or execute it with source-specific Python.
No model calls happen in plan mode. Existing failed runs are never overwritten.
"""
import argparse
import copy
import json
import os
import subprocess
from pathlib import Path
from novours.core import ROOT,digest,dump
p=argparse.ArgumentParser();p.add_argument('command',choices=['plan','run']);p.add_argument('--plan',type=Path,required=True);p.add_argument('--configs',nargs='+',type=Path);p.add_argument('--methods',nargs='+',default=['native','direct','stateforge','voi','revoir','stateforge_revoir','p1','p2','p3']);p.add_argument('--output',type=Path);a=p.parse_args()
if a.command=='plan':
    if not a.configs:raise SystemExit('--configs required; all task/session selections must be explicit in those files')
    if a.plan.exists():raise SystemExit('Plan already exists; use a new plan path')
    jobs=[]
    for path in a.configs:
        original=json.loads(path.read_text())
        for method in a.methods:
            c=copy.deepcopy(original)
            c['agent']={'hypotheses':2,'actions':2,'questions':1,'max_questions':2,**c.get('agent',{}),'method':method}
            jobs.append({'id':path.stem+'-'+method,'config':c,'config_sha256':digest(c)})
    if len({j['id'] for j in jobs})!=len(jobs):raise SystemExit('Duplicate config stem/method')
    dump(a.plan,{'version':1,'jobs':jobs,'jobs_sha256':digest(jobs)})
    print(json.dumps({'jobs':len(jobs),'plan':str(a.plan),'model_calls':0}))
else:
    if not a.output:raise SystemExit('--output required')
    plan=json.loads(a.plan.read_text())
    if plan['jobs_sha256']!=digest(plan['jobs']):raise SystemExit('Plan hash mismatch')
    interpreters={'pi':ROOT/'.venv-pibench311/bin/python','lifesim':ROOT/'lifesim-venv/bin/python','mempa':ROOT/'NovOurs/.local/venv/bin/python','proagent':ROOT/'lifesim-venv/bin/python'}
    a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    ledger=[]
    for job in plan['jobs']:
        c=job['config']
        if job['config_sha256']!=digest(c):raise SystemExit('Job config hash mismatch')
        out=a.output/job['id'];config_path=a.output/'configs'/(job['id']+'.json');dump(config_path,c)
        if (out/'manifest.json').exists() and not (out/'result.json').exists():
            ledger.append({'id':job['id'],'status':'needs_inspection','reason':'Incomplete prior run preserved'})
        else:
            with (a.output/(job['id']+'.log')).open('a') as log:
                result=subprocess.run([str(interpreters[c['source']]),'-m','novours','run','--config',str(config_path),'--output',str(out),'--resume'],env={**os.environ,'PYTHONPATH':str(ROOT/'NovOurs')},stdout=log,stderr=subprocess.STDOUT)
            ledger.append({'id':job['id'],'exit_code':result.returncode})
        dump(a.output/'progress.json',{'jobs_sha256':plan['jobs_sha256'],'finished':len(ledger),'total':len(plan['jobs']),'runs':ledger})
    raise SystemExit(int(any(x.get('exit_code')!=0 for x in ledger)))
