"""Isolated native MemPABench checkout, original orchestration and scores.
All transport changes are applied only to a disposable copy and recorded.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from novours.core import ROOT,SOURCES,dump
from novours.gateway import Gateway


def prepare(config,out,gateway):
    import yaml
    source=SOURCES/'MemPABench'
    native=out/'native'
    if not native.exists():
        shutil.copytree(source,native,ignore=shutil.ignore_patterns('.git','.venv','__pycache__','workspace','memory_raw_repos'))
    persona=config.get('persona_id','user_a')
    # Use exactly upstream's pinned persona file manifest, no generated persona data.
    for line in (native/'mempabench/persona_data_files.tsv').read_text().splitlines():
        if not line or line.startswith('#'):continue
        cells=line.split('\t')
        if cells[0]!=persona:continue
        relative=cells[1]
        src=ROOT/'benchmarks/data/MemPABench-personas'/persona/relative
        if not src.is_file(): raise FileNotFoundError(str(src))
        dest=native/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
    changes=[]
    registry=native/'memory/registry.py'
    registry_text=registry.read_text()
    registry_text=registry_text.replace('    from memory.backends.mem0_adapter import Mem0Adapter\n','')
    registry_text=registry_text.replace('    from memory.backends.memos_adapter import MemOSAdapter\n','')
    registry_text=registry_text.replace('    reg.register("mem0", Mem0Adapter, kind="backend")','    reg.register("mem0", lambda **kw: __import__("memory.backends.mem0_adapter", fromlist=["Mem0Adapter"]).Mem0Adapter(**kw), kind="backend")')
    registry_text=registry_text.replace('    reg.register("memos", MemOSAdapter, kind="backend")','    reg.register("memos", lambda **kw: __import__("memory.backends.memos_adapter", fromlist=["MemOSAdapter"]).MemOSAdapter(**kw), kind="backend")')
    registry_text=registry_text.replace('    return Mem0Adapter(infer=False, **kwargs)','    return __import__("memory.backends.mem0_adapter", fromlist=["Mem0Adapter"]).Mem0Adapter(infer=False, **kwargs)')
    registry.write_text(registry_text)
    changes.append({'file':'memory/registry.py','change':'Lazy imports of unselected Mem0/MemOS dependencies; selected original memory implementation unchanged'})
    for path in native.rglob('*.py'):
        text=path.read_text()
        updated=text.replace('https://openrouter.ai/api/v1',gateway.url)
        # A completed run may be evaluated in a new gateway process/port.
        import re
        updated=re.sub(r'http://127\.0\.0\.1:\d+/v1',gateway.url,updated)
        if updated!=text:
            path.write_text(updated);changes.append({'file':str(path.relative_to(native)),'change':'OpenRouter transport URL -> local audited gateway'})
    catalog=native/'configs/model_request_policies.yaml'
    data=yaml.safe_load(catalog.read_text())
    data['models']=[x for x in data.get('models',[]) if x.get('model') not in {'qwen/Qwen3-8B','deepseek/deepseek-v4-flash'}]
    for name in ['qwen/Qwen3-8B','deepseek/deepseek-v4-flash']:
        data['models'].append({'provider_name':'openrouter','model':name,'temperature':'send','completion_tokens_parameter':'max_tokens','reasoning_effort':'omit','supports_tools':True,'supports_forced_tool_choice':True,'validated_roles':['pa','consolidation']})
    catalog.write_text(yaml.safe_dump(data,sort_keys=False))
    changes.append({'file':str(catalog.relative_to(native)),'change':'explicit model transport policies for pilot backends'})
    dump(out/'overlay_changes.json',changes)
    return native


def run(config,out,journal):
    import importlib.metadata
    if int(importlib.metadata.version('mcp').split('.')[0])!=1:
        raise RuntimeError('Native MemPA requires MCP 1.x; run with NovOurs/.local/venv, not the vLLM environment')
    # Native memory/checkpoint ownership is preserved. Alternative PA adapters can
    # be supplied as a native factory entrypoint; never approximate probe isolation.
    routes={
        'qwen/Qwen3-8B':(config['actor'],'actor'),
        'deepseek/deepseek-v4-flash':(config['user'],'user'),
        'google/gemini-3.8-flash':(config['judge'],'judge'),
        'gemma-4-12b-it':(config['judge'],'live_judge'),
    }
    with Gateway(routes,journal) as gateway:
        native=prepare(config,out,gateway)
        env=dict(os.environ,OPENROUTER_API_KEY='LOCAL_GATEWAY',MEMPA_WORKSPACE_ROOT=str(out),MEMPA_RUNS_ROOT=str(out/'runs'),MEMPA_JUDGE='live',MEMPA_JUDGE_PIN='NovOurs bounded pilot with explicitly recorded DeepSeek judge backend',MEMPA_JUDGE_URL=gateway.url,MEMPA_JUDGE_API_KEY='LOCAL_GATEWAY',MEMPA_JUDGE_MODEL='gemma-4-12b-it',MEMPA_JUDGE_RETRIES='0',MEMPA_JUDGE_POOL_ROUNDS='1',PYTHONPATH=str(ROOT/'NovOurs')+os.pathsep+str(native))
        launcher=native/'novours_entry.py'
        launcher.write_text('import json,sys\nfrom pathlib import Path\nfrom novours.mempa_hook import install\nconfig=json.loads(Path(sys.argv.pop(1)).read_text())\nif config["agent"]["method"]!="native": install(config,sys.argv.pop(1))\nelse: sys.argv.pop(1)\nfrom mempabench.cli import main\nraise SystemExit(main())\n')
        dump(out/'effective_config.json',config)
        env['PATH']=str(Path(sys.executable).parent)+os.pathsep+os.environ.get('PATH','')
        cmd=[sys.executable,str(launcher),str(out/'effective_config.json'),str(out/'agent_trace.jsonl'),'run','--run-id',config.get('run_id','novours'),'--persona-id',config.get('persona_id','user_a'),'--acc-range',config.get('acc_range','1-108'),'--memory-condition',config.get('memory_condition','nanobot_file_memory'),'--pa-model','qwen/Qwen3-8B','--consolidation-model','qwen/Qwen3-8B','--simulator-model','deepseek/deepseek-v4-flash']
        dump(out/'native_command.json',{'argv':cmd,'actual_model_routes':{k:dict(model=v[0]['model'],role=v[1]) for k,v in routes.items()},'configuration_warning':'Pilot backend substitutions; not leaderboard-comparable'})
        with (out/'native.log').open('w') as log:
            subprocess.run(cmd,cwd=native,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=config.get('timeout_seconds',1800))
        # Original scorer itself decides whether all required probes exist.
        if config.get('score',False):
            plans=list((out/'runs').rglob('run_plan.yaml'))
            if len(plans)!=1:raise RuntimeError('expected exactly one native run')
            with (out/'score.log').open('w') as log:
                subprocess.run([sys.executable,'-m','mempabench.cli','score','--run-dir',str(plans[0].parent)],cwd=native,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
            results={str(p.relative_to(out)):json.loads(p.read_text()) for p in plans[0].parent.glob('metrics/llm__*.json')}
            return results
        return {'status':'native_session_completed','aggregate_scores':None,'reason':'Full original score requires all probes; score flag disabled for bounded smoke'}


def evaluate(config,out,journal):
    plans=list((out/'runs').rglob('run_plan.yaml'))
    if len(plans)!=1:raise RuntimeError('expected exactly one existing native run')
    routes={'qwen/Qwen3-8B':(config['actor'],'actor'),'deepseek/deepseek-v4-flash':(config['user'],'user'),'google/gemini-3.8-flash':(config['judge'],'judge'),'gemma-4-12b-it':(config['judge'],'live_judge')}
    with Gateway(routes,journal) as gateway:
        native=prepare(config,out,gateway)
        env=dict(os.environ,OPENROUTER_API_KEY='LOCAL_GATEWAY',MEMPA_WORKSPACE_ROOT=str(out),MEMPA_RUNS_ROOT=str(out/'runs'),PYTHONPATH=str(native))
        with (out/'score.log').open('a') as log:
            subprocess.run([sys.executable,'-m','mempabench.cli','score','--run-dir',str(plans[0].parent)],cwd=native,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=config.get('timeout_seconds',1800))
        results={str(p.relative_to(out)):json.loads(p.read_text()) for p in plans[0].parent.glob('metrics/llm__*.json')}
        if not results:raise RuntimeError('native scorer produced no metrics')
        return results
