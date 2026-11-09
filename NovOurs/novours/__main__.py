from __future__ import annotations
import argparse
import importlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from .core import ROOT, SOURCES, Journal, dump, digest


def main():
    p = argparse.ArgumentParser()
    p.add_argument('command',choices=['run','evaluate','inventory','serve-agent'])
    p.add_argument('--config',type=Path)
    p.add_argument('--output',type=Path)
    p.add_argument('--resume',action='store_true')
    args = p.parse_args()
    if args.command=='inventory':
        from .inventory import inventory
        result=inventory()
        dump(args.output or ROOT/'NovOurs/docs/inventory.json',result)
        print(json.dumps(result.get('summary'),ensure_ascii=False)); return
    config = json.loads(args.config.read_text())
    if args.command=='serve-agent':
        from .rpc import serve
        serve(config);return
    out = (args.output or ROOT/'NovOurs/.local/runs'/time.strftime('%Y%m%d-%H%M%S')).resolve()
    out.mkdir(parents=True,exist_ok=True)
    fingerprint=digest(config)
    manifest=out/'manifest.json'
    if manifest.exists():
        if not args.resume and args.command!='evaluate': raise RuntimeError('Output already exists; use a new directory or --resume')
        if json.loads(manifest.read_text())['config_sha256']!=fingerprint: raise RuntimeError('Resume config mismatch')
        if args.command=='run' and (out/'result.json').exists():
            existing=json.loads((out/'result.json').read_text())
            skipped=isinstance(existing.get('native_metrics'),dict) and existing['native_metrics'].get('status')=='skipped'
            dump(out/'status.json',{'status':'skipped' if skipped else 'complete','note':'verified existing result on resume'}); print(json.dumps(existing,ensure_ascii=False)); return
        if args.command=='run': raise RuntimeError('Incomplete run: use evaluate for completed native logs, or start a fresh isolated run. No unsafe replay.')
    versions={}
    for source in ['Pi-Bench','lifesim','MemPABench','ProAgentBench']:
        v=subprocess.run(['git','-C',str(SOURCES/source),'rev-parse','HEAD'],capture_output=True,text=True)
        versions[source]=v.stdout.strip() if v.returncode==0 else 'not-a-git-checkout'
    import hashlib
    code_hashes={str(p.relative_to(ROOT/'NovOurs')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'NovOurs/novours').rglob('*.py')}
    if not manifest.exists():
        dump(manifest,dict(config=config,config_sha256=fingerprint,source_versions=versions,code_hashes=code_hashes,started=time.time(),pid=os.getpid()))
    journal=Journal(out/'trace.jsonl')
    dump(out/'status.json',{'status':'running'})
    try:
        adapter=importlib.import_module('novours.adapters.'+config['source'])
        result=getattr(adapter,args.command)(config,out,journal)
        dump(out/'result.json',{'source':config['source'],'native_metrics':result,'completed':time.time()})
        dump(out/'status.json',{'status':'skipped' if isinstance(result,dict) and result.get('status')=='skipped' else 'complete'})
        print(json.dumps(result,ensure_ascii=False,default=str))
    except BaseException as e:
        dump(out/'status.json',{'status':'failed','error_class':type(e).__name__,'error':str(e)[:500]})
        raise

if __name__=='__main__': main()
