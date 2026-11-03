import argparse,json,os,signal,socket,subprocess,time
from pathlib import Path
ROOT=Path('/home/tim/Proj/I3Agent/ours2_runtime')
MODELS={'qwen':{'gpu':'0','port':8020,'path':'/mnt/data/Qwen3-8B','name':'Qwen3-8B'},'gptoss':{'gpu':'1','port':8021,'path':'/mnt/data/gpt-oss-20b','name':'gpt-oss-20b'}}
p=argparse.ArgumentParser();p.add_argument('action',choices=['start','stop','status']);p.add_argument('--model',choices=list(MODELS));a=p.parse_args()
for label,m in MODELS.items():
 if a.model and a.model!=label:continue
 pidfile=ROOT/(label+'-managed.pid');metadata=ROOT/(label+'-service.json')
 if a.action=='start':
  with socket.socket() as s:
   if s.connect_ex(('127.0.0.1',m['port']))==0:raise SystemExit('Port already in use; refusing duplicate launch')
  env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES=m['gpu'],HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',VLLM_NO_USAGE_STATS='1',OMP_NUM_THREADS='4',VLLM_USE_FLASHINFER_SAMPLER='0')
  cmd=['/home/tim/miniconda3/envs/tim/bin/python','-m','vllm.entrypoints.openai.api_server','--model',m['path'],'--served-model-name',m['name'],'--host','127.0.0.1','--port',str(m['port']),'--gpu-memory-utilization','0.88','--max-model-len','8192','--max-num-seqs','16','--max-num-batched-tokens','4096','--enable-prefix-caching','--compilation-config',json.dumps({'cudagraph_capture_sizes':[1,2,4,8,16]})]
  log=ROOT/'logs'/(label+'-managed-'+time.strftime('%Y%m%d-%H%M%S')+'.log')
  with log.open('w') as f:
   child=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,env=env,start_new_session=True)
  pidfile.write_text(str(child.pid)+'\n')
  data={**m,'pid':child.pid,'command':cmd,'log':str(log),'started_at':time.time(),'env_overrides':{k:env[k] for k in ['CUDA_VISIBLE_DEVICES','HF_HUB_OFFLINE','VLLM_USE_FLASHINFER_SAMPLER','OMP_NUM_THREADS']}}
  metadata.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data))
 elif a.action=='stop':
  if pidfile.exists():
   pid=int(pidfile.read_text());proc=Path('/proc')/str(pid)/'cmdline'
   if proc.exists() and m['path'].encode() in proc.read_bytes() and b'vllm.entrypoints.openai.api_server' in proc.read_bytes():
    os.kill(pid,signal.SIGTERM);print(label,'sent SIGTERM',pid)
   else:print(label,'not running or identity mismatch; no signal sent')
 else:
  print(metadata.read_text() if metadata.exists() else label+' not started')
