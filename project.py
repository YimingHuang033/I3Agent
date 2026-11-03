#!/usr/bin/env python3
"""Read-only entrypoint for I3Agent experiment status (local or BBQCard2)."""
import argparse,json,shlex,subprocess,sys
from pathlib import Path
REMOTE_ROOT='/home/tim/Proj/I3Agent'
CAMPAIGNS={'intent-full':('intent_full_runtime','full-20261103-v1'),'intent-diagnostics':('intent_diagnostics_runtime','discussion-20261102-v1'),'pi-lifesim':('ours1_runtime','full-20261102-v1'),'mempa-proagent':('ours2_runtime','source-adapted-20261102-v1')}
def collect(root,selected):
 result={}
 for label,(runtime,campaign) in selected.items():
  folder=root/runtime/'campaigns'/campaign
  try:
   state=json.loads((folder/'status.json').read_text())
   for model in list(state.get('models',{})):
    p=folder/model/'progress.json'
    if p.exists():state['models'][model]=json.loads(p.read_text())
   pid=state.get('monitor_pid');proc=Path('/proc')/str(pid)/'cmdline'
   state['monitor_alive']=bool(pid and proc.exists() and str(root/runtime/'monitor.py').encode() in proc.read_bytes())
   result[label]=state
  except (OSError,ValueError) as exc:result[label]={'phase':'unavailable','error':str(exc)}
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('action',choices=['status'],nargs='?',default='status')
 p.add_argument('group',choices=['all',*CAMPAIGNS],nargs='?',default='all')
 p.add_argument('--json',action='store_true');p.add_argument('--on-server',action='store_true',help=argparse.SUPPRESS)
 a=p.parse_args();selected=CAMPAIGNS if a.group=='all' else {a.group:CAMPAIGNS[a.group]}
 if a.on_server or Path(__file__).resolve().parent==Path(REMOTE_ROOT):data=collect(Path(REMOTE_ROOT),selected)
 else:
  cmd=shlex.join(['python3',REMOTE_ROOT+'/project.py','status',a.group,'--json','--on-server'])
  response=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','BBQCard2',cmd],capture_output=True,text=True,timeout=30)
  if response.returncode:raise SystemExit(response.stderr.strip() or 'SSH status check failed')
  data=json.loads(response.stdout)
 if a.json:print(json.dumps(data,ensure_ascii=False,indent=2));return
 for label,state in data.items():
  print(f"{label}: {state.get('phase')} | updated={state.get('updated_at','unknown')} | monitor_alive={state.get('monitor_alive',False)}")
  for model,v in state.get('models',{}).items():
   done,total=v.get('completed',0),v.get('total',0)
   print(f"  {model}: {done}/{total} ({done/total:.1%}) | error episodes={v.get('protocol_error_episodes',0)} | infrastructure events={v.get('infrastructure_errors',0)}" if total else f'  {model}: starting')
  if state.get('error'):print('  error:',state['error'])
if __name__=='__main__':main()
