"""One campaign, resumable workers, 20-minute monitoring; no chat wake facility."""
import argparse,fcntl,json,os,signal,socket,subprocess,time,urllib.request,sys
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parent
PYTHON='/home/tim/Proj/I3Agent/lifesim-venv/bin/python'
MODELS={'qwen':('Qwen3-8B',8020),'gptoss':('gpt-oss-20b',8021)}
def now():return datetime.now().astimezone().isoformat()
def write(path,value):
 p=path.with_suffix('.tmp');p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');p.replace(path)
def read(path):
 try:return json.loads(path.read_text())
 except (FileNotFoundError,json.JSONDecodeError):return {}
def service(action,label):
 return subprocess.run(['python3',str(ROOT/'manage_services.py'),action,'--model',label],capture_output=True,text=True)
def ready(port):
 try:
  with urllib.request.urlopen(f'http://127.0.0.1:{port}/v1/models',timeout=3) as r:return r.status==200
 except Exception:return False
def terminate(child):
 if child.poll() is None:
  child.terminate()
  try:child.wait(timeout=15)
  except subprocess.TimeoutExpired:child.kill();child.wait()
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['run','status','stop']);p.add_argument('--campaign',default='source-adapted-20261102-v1');p.add_argument('--interval',type=int,default=1200);p.add_argument('--subset',choices=['discussion','pilot','full'],default='full');a=p.parse_args()
 if Path(a.campaign).name!=a.campaign:raise SystemExit('campaign must be a directory name')
 campaign=ROOT/'campaigns'/a.campaign;campaign.mkdir(parents=True,exist_ok=True)
 if a.action=='status':print(json.dumps(read(campaign/'status.json'),ensure_ascii=False,indent=2));return
 if a.action=='stop':(campaign/'STOP').touch();print('Stop requested:',campaign);return
 lock=(ROOT/'monitor.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 if (campaign/'STOP').exists():raise SystemExit('STOP exists; remove explicitly to resume')
 write(ROOT/'monitor.pid.json',{'pid':os.getpid(),'campaign':str(campaign),'interval_seconds':a.interval,'started_at':now()})
 (ROOT/'current-campaign.txt').write_text(str(campaign)+'\n')
 children={};owned=[];phase='starting';error=None;last_change={};last_done={};next_tick=time.time()+a.interval;tick=0;judge=None
 env=os.environ.copy();env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='4',PYTHONDONTWRITEBYTECODE='1')
 def snapshot(event):
  state={'updated_at':now(),'phase':phase,'error':error,'monitor_pid':os.getpid(),'interval_seconds':a.interval,'next_tick_unix':next_tick,'campaign':str(campaign),'models':{m:read(campaign/m/'progress.json') for m in MODELS},'judge':read(campaign/'judge/summary.json'),'event':event,'worker_alive':{m:(m in children and children[m].poll() is None) for m in MODELS}}
  write(campaign/'status.json',state)
  if event!='heartbeat':
   with (campaign/'monitor.jsonl').open('a') as f:f.write(json.dumps(state,ensure_ascii=False)+'\n')
   print('AGENT_LOOP_TICK_OURS1 '+json.dumps({'at':now(),'phase':phase,'tick':tick,'status':str(campaign/'status.json')}),flush=True)
  return state
 def stop_services():
  for label in owned:service('stop',label)
  owned.clear()
 def cleanup(*_):raise KeyboardInterrupt
 signal.signal(signal.SIGTERM,cleanup);signal.signal(signal.SIGINT,cleanup)
 snapshot('initial')
 try:
  for label,(name,port) in MODELS.items():
   if read(campaign/label/'progress.json').get('state')=='complete':continue
   if ready(port):raise RuntimeError(f'Port {port} occupied; refusing to take over a server')
   result=service('start',label)
   if result.returncode:raise RuntimeError('Service startup failed: '+result.stderr[-600:])
   owned.append(label)
  deadline=time.time()+300
  while any(not ready(MODELS[label][1]) for label in owned):
   if time.time()>deadline:raise RuntimeError('Service readiness timeout')
   if (campaign/'STOP').exists():raise KeyboardInterrupt
   time.sleep(3)
  for label,(name,port) in MODELS.items():
   if read(campaign/label/'progress.json').get('state')=='complete':continue
   cmd=[PYTHON,str(ROOT/'run_local.py'),'--projects',str(ROOT.parent/'mempabench_ours1'),str(ROOT.parent/'proagentbench_ours1'),'--model',name,'--model-kind',label,'--base-url',f'http://127.0.0.1:{port}/v1','--out',str(campaign/label),'--workers','8','--subset',a.subset,'--authorized-run']
   with (campaign/(label+'.log')).open('a') as log:children[label]=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env)
   last_change[label]=time.time();last_done[label]=-1
  phase='running';snapshot('workers_started')
  while True:
   if (campaign/'STOP').exists():raise KeyboardInterrupt
   if phase=='running':
    for label,child in children.items():
     state=read(campaign/label/'progress.json');done=state.get('completed',0)
     if done!=last_done[label]:last_change[label]=time.time();last_done[label]=done
     if child.poll() is not None and (child.returncode!=0 or state.get('state')!='complete'):
      raise RuntimeError(f'{label} stopped, exit={child.returncode}; inspect {campaign/label}.log')
     if child.poll() is None and time.time()-last_change[label]>900:
      raise RuntimeError(f'{label} made no checkpoint progress for 15 minutes')
    if all(c.poll() is not None for c in children.values()):
     stop_services();phase='judging';snapshot('actors_complete')
     if not (campaign/'judge/summary.json').exists():
      command='source /home/tim/Proj/I3Agent/deepseek.env.sh; exec "$@"'
      args=['bash','-c',command,'judge',PYTHON,str(ROOT/'judge_audit.py'),'--runs',str(campaign/'qwen'),str(campaign/'gptoss'),'--out',str(campaign/'judge'),'--workers','4','--sample-rate','0.05']
      with (campaign/'judge.log').open('a') as log:judge=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT)
   if phase=='judging' and (judge is None or judge.poll() is not None):
    if judge is not None and judge.returncode!=0:raise RuntimeError('Judge process failed; inspect judge.log')
    js=read(campaign/'judge/summary.json')
    phase='complete' if js.get('successful')==js.get('episodes') and js else 'complete_with_judge_errors'
    analysis=subprocess.run([PYTHON,str(ROOT/'analyze.py'),'--campaign',a.campaign],capture_output=True,text=True)
    (campaign/'analysis.log').write_text(analysis.stdout+analysis.stderr)
    if analysis.returncode:phase='complete_with_analysis_error';error='Offline analysis failed; inspect analysis.log'
    snapshot('campaign_finished')
   if time.time()>=next_tick:
    tick+=1;next_tick+=a.interval;snapshot('scheduled_20m')
   else:snapshot('heartbeat')
   time.sleep(10)
 except KeyboardInterrupt:
  phase='stopped';snapshot('stopped')
 except Exception as exc:
  phase='blocked';error=type(exc).__name__+': '+str(exc);snapshot('blocked')
  # Stop compute safely, keep the 20-minute monitor alive for visibility.
  for child in children.values():terminate(child)
  if judge:terminate(judge)
  stop_services()
  # Retry only transport-triggered exits; immutable actor code/checkpoints stay unchanged.
  recoverable=any(child.poll()==2 for child in children.values())
  recovery=read(campaign/'recovery.json')
  completed=sum(read(campaign/m/'progress.json').get('completed',0) for m in MODELS)
  streak=0 if completed-recovery.get('last_completed',0)>=128 else recovery.get('streak',0)
  total=recovery.get('attempts',0)
  if recoverable and streak<3 and total<24 and not (campaign/'STOP').exists():
   recovery={'attempts':total+1,'streak':streak+1,'last_completed':completed,'last_error':error,'at':now()}
   write(campaign/'recovery.json',recovery)
   phase='recovering';snapshot('bounded_recovery')
   for _ in range(6):
    if (campaign/'STOP').exists():return
    time.sleep(5)
   lock.close()
   os.execv(sys.executable,[sys.executable,*sys.argv])
  try:
   while not (campaign/'STOP').exists():
    if time.time()>=next_tick:tick+=1;next_tick+=a.interval;snapshot('scheduled_20m')
    time.sleep(10)
  except KeyboardInterrupt:pass
 finally:
  for child in children.values():terminate(child)
  if judge:terminate(judge)
  stop_services()
if __name__=='__main__':main()
