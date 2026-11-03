"""Fetch public ProAgentBench event JSON at a fixed revision; verify LFS sha256."""
from pathlib import Path
import urllib.request,hashlib,json,concurrent.futures,time
ROOT=Path(__file__).resolve().parents[3]
repo=ROOT/'benchmarks/sources/ProAgentBench';out=ROOT/'benchmarks/data/ProAgentBench-events';out.mkdir(parents=True,exist_ok=True)
rev='b5388f02dd99777af1d5ea473ccb3436276e7c05'
files=sorted(repo.glob('志愿者*.json'))
def one(p):
 raw=p.read_bytes();pointer=raw.decode();target=out/p.name
 if not pointer.startswith('version https://git-lfs.github.com/spec/v1'):
  target.write_bytes(raw);return {'file':p.name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
 sha=pointer.split('oid sha256:')[1].splitlines()[0];size=int(pointer.split('size ')[1].strip())
 if not target.exists():
  url='https://huggingface.co/datasets/qv9n2xk7m1z8pt4/ProAgentBench/resolve/'+rev+'/'+urllib.parse.quote(p.name)
  data=urllib.request.urlopen(url,timeout=180).read();assert hashlib.sha256(data).hexdigest()==sha and len(data)==size
  target.write_bytes(data)
 assert hashlib.sha256(target.read_bytes()).hexdigest()==sha
 print(p.name,size,flush=True);return {'file':p.name,'sha256':sha,'bytes':size}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:result=list(pool.map(one,files))
(out/'SOURCE.json').write_text(json.dumps({'repo':'https://huggingface.co/datasets/qv9n2xk7m1z8pt4/ProAgentBench','revision':rev,'files':result},indent=2))
