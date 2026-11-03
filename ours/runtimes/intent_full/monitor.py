"""Full-dataset diagnostic experiment; independent from frozen campaigns."""
import json, os, signal, subprocess, time, urllib.request, fcntl, hashlib
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
CAMPAIGN=ROOT/'campaigns/full-20261103-v1'
PYTHON=str(PROJECT/'lifesim-venv/bin/python')
MODELS={'qwen':('Qwen3-8B',8030),'gptoss':('gpt-oss-20b',8031)}
PROJECTS=['pi_bench_ours1','lifesim_ours1','mempabench_ours1','proagentbench_ours1']
def read(p):
 return json.loads(p.read_text()) if p.exists() else {}
def write(p,d):
 t=p.with_suffix('.tmp');t.write_text(json.dumps(d,ensure_ascii=False,indent=2));t.replace(p)
def ready(port):
 try:
  with urllib.request.urlopen(f'http://127.0.0.1:{port}/v1/models',timeout=2) as r:return r.status==200
 except Exception:return False
def main():
 CAMPAIGN.mkdir(parents=True,exist_ok=True);(ROOT/'logs').mkdir(exist_ok=True)
 lock=(ROOT/'monitor.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 children={};owned=[];phase='starting';error=None;last_tick=0
 def snapshot():
  nonlocal last_tick
  d={'updated_at':datetime.now().astimezone().isoformat(),'phase':phase,'error':error,'monitor_pid':os.getpid(),'models':{m:read(CAMPAIGN/m/'progress.json') for m in MODELS},'judge':read(CAMPAIGN/'judge/summary.json')}
  write(CAMPAIGN/'status.json',d)
  if time.monotonic()-last_tick>=1200 or phase!='running':
   with (CAMPAIGN/'monitor.jsonl').open('a') as f:f.write(json.dumps(d)+'\n')
   last_tick=time.monotonic()
 def service(action,label):
  subprocess.run(['python3',str(ROOT/'manage_services.py'),action,'--model',label],check=True,timeout=30)
 def stop_services():
  for m in owned[:]:
   service('stop',m);owned.remove(m)
 def stop(*_):raise KeyboardInterrupt
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 env=os.environ.copy();env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='4',PYTHONDONTWRITEBYTECODE='1')
 try:
  snapshot()
  for path,expected in read(CAMPAIGN/'scheduled-inputs.json')['sha256'].items():
   if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:raise RuntimeError('Scheduled input changed: '+path)
  if (CAMPAIGN/'STOP').exists():raise RuntimeError('STOP exists')
  # Refuse to steal GPUs or ports. Other campaign monitors may remain idle.
  usage=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True)
  if any(int(x)>1024 for x in usage.splitlines()):raise RuntimeError('GPUs occupied; no process stopped')
  for m,(_,port) in MODELS.items():
   if ready(port):raise RuntimeError(f'Port {port} occupied')
   if read(CAMPAIGN/m/'progress.json').get('state')!='complete':service('start',m);owned.append(m)
  deadline=time.monotonic()+600
  while any(not ready(MODELS[m][1]) for m in owned):
   if (CAMPAIGN/'STOP').exists():raise KeyboardInterrupt
   if time.monotonic()>deadline:raise RuntimeError('Service startup exceeded 10 minutes')
   time.sleep(5)
  for m,(name,port) in MODELS.items():
   if read(CAMPAIGN/m/'progress.json').get('state')=='complete':continue
   cmd=[PYTHON,str(ROOT/'run_local.py'),'--projects',*[str(PROJECT/p) for p in PROJECTS],'--model',name,'--model-kind',m,'--base-url',f'http://127.0.0.1:{port}/v1','--out',str(CAMPAIGN/m),'--workers','8','--subset','full','--authorized-run']
   with (CAMPAIGN/(m+'.log')).open('a') as log:children[m]=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env)
  phase='running';started=time.monotonic();last_progress={m:started for m in children};count={m:-1 for m in children}
  while any(c.poll() is None for c in children.values()):
   snapshot()
   for m,child in children.items():
    done=read(CAMPAIGN/m/'progress.json').get('completed',0)
    if done!=count[m]:count[m]=done;last_progress[m]=time.monotonic()
    if child.poll() is None and time.monotonic()-last_progress[m]>900:raise RuntimeError(f'{m}: no progress for 15 minutes')
   if (CAMPAIGN/'STOP').exists():raise KeyboardInterrupt
   if time.monotonic()-started>86400:raise RuntimeError('Actor stage exceeded 24 hours')
   if any(c.poll() not in (None,0) for c in children.values()):raise RuntimeError('Actor failed; checkpoints retained, inspect model log')
   time.sleep(10)
  if any(c.returncode for c in children.values()):raise RuntimeError('Actor failed')
  if any(read(CAMPAIGN/m/'progress.json').get('state')!='complete' for m in MODELS):raise RuntimeError('Incomplete actor output')
  stop_services();phase='judging';snapshot()
  args=['bash','-c','source /home/tim/Proj/I3Agent/deepseek.env.sh; exec "$@"','judge',PYTHON,str(ROOT/'judge_audit.py'),'--runs',*[str(CAMPAIGN/m) for m in MODELS],'--out',str(CAMPAIGN/'judge'),'--sample-rate','0.05']
  with (CAMPAIGN/'judge.log').open('a') as log:
   j=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,env=env);children['judge']=j
   j.wait(timeout=14400)
  phase='complete' if j.returncode==0 and read(CAMPAIGN/'judge/summary.json').get('successful')==read(CAMPAIGN/'judge/summary.json').get('episodes') else 'complete_with_judge_errors'
 except KeyboardInterrupt:phase='stopped'
 except Exception as exc:phase='blocked';error=f'{type(exc).__name__}: {exc}'
 finally:
  for child in children.values():
   if child.poll() is None:
    child.terminate()
    try:child.wait(timeout=20)
    except subprocess.TimeoutExpired:child.kill();child.wait()
  stop_services()
  if all(read(CAMPAIGN/m/'progress.json').get('state')=='complete' for m in MODELS):
   result=subprocess.run(['python3',str(ROOT/'report.py')],capture_output=True,text=True)
   (CAMPAIGN/'analysis.log').write_text(result.stdout+result.stderr)
   if result.returncode:error=(error or '')+'; report failed';phase='blocked'
  snapshot()
 if phase=='blocked':raise SystemExit(1)
if __name__=='__main__':main()
