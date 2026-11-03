"""Supplementary DeepSeek semantic audit; deterministic scores remain authoritative."""
import argparse,json,os,time,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from openai import OpenAI

PROMPT='''你是多轮用户偏好任务的独立语义审核者。仅使用提供的 observation（助手当时可见的信息）与 response，不猜测隐藏目标。
统计该 episode：1. unsupported_preference_claims：缺少可见用户依据、使用已明确失效的证据或编造证据的偏好断言数量；2. unnecessary_questions：可见信息已足够明确却仍提问的次数；3. ignored_explicit_corrections：在明确纠正后仍采用旧偏好的动作次数。没有历史可见时提问不算多余；抽样不到更新导致历史不完整时，不以你看不到的目标判断无依据。只评结构化断言，不要求模型展示思维链。
输出一个 JSON 对象，字段为 unsupported_preference_claims、unnecessary_questions、ignored_explicit_corrections（非负整数）和 note（简短中文说明，最多150字）。'''

def main():
 p=argparse.ArgumentParser();p.add_argument('--runs',nargs='+',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--workers',type=int,default=4);p.add_argument('--sample-rate',type=float,default=0.05);args=p.parse_args()
 assert 0 < args.sample_rate <= 1
 args.out.mkdir(parents=True,exist_ok=True)
 (args.out/"items").mkdir(exist_ok=True)
 client=OpenAI(base_url=os.environ['JUDGER_BASE_URL'],api_key=os.environ['JUDGER_API_KEY'],timeout=180,max_retries=0)
 selected={}
 for run in args.runs:
  for path in sorted((run/'episodes').glob('*.json')):
   r=json.loads(path.read_text())
   key='|'.join([r['model'],r['benchmark'],r['episode_id'],r['baseline']])
   if int(hashlib.sha256(key.encode()).hexdigest()[:8],16)/2**32 < args.sample_rate:
    selected[key]=(path,r)
 def one(pair):
  path,r=pair
  visible=[{'phase':t['phase'],'observation':t['observation'],'response':t.get('response', t.get('content')), 'protocol_error':t.get('error')} for t in r['trace']]
  identity=hashlib.sha256('|'.join([r['model'],r['benchmark'],r['episode_id'],r['baseline']]).encode()).hexdigest()
  checkpoint=args.out/'items'/(identity+'.json')
  if checkpoint.exists():return json.loads(checkpoint.read_text())
  st=time.perf_counter();item={'source':str(path),'model':r['model'],'benchmark':r['benchmark'],'baseline':r['baseline'],'source_status':r['status']}
  try:
   z=client.chat.completions.create(model='deepseek-flash',extra_body={'thinking':{'type':'disabled'}},max_tokens=1024,response_format={'type':'json_object'},messages=[{'role':'system','content':PROMPT},{'role':'user','content':json.dumps(visible,ensure_ascii=False)}])
   item.update(seconds=time.perf_counter()-st,usage=z.usage.model_dump(),content=z.choices[0].message.content,finish_reason=z.choices[0].finish_reason)
   parsed=json.loads(item['content'])
   for k in ['unsupported_preference_claims','unnecessary_questions','ignored_explicit_corrections']:
    assert isinstance(parsed[k],int) and parsed[k]>=0
   item.update(status='ok',judgment=parsed)
  except Exception as exc:item.update(status='error',seconds=time.perf_counter()-st,error=type(exc).__name__+': '+str(exc)[:500])
  tmp=checkpoint.with_suffix(".tmp");tmp.write_text(json.dumps(item,ensure_ascii=False));tmp.replace(checkpoint)
  return item
 start=time.perf_counter();results=[]
 with ThreadPoolExecutor(max_workers=args.workers) as pool:
  for f in as_completed([pool.submit(one,v) for v in selected.values()]):
   row=f.result();results.append(row);print(json.dumps({'completed':len(results),'total':len(selected),'status':row['status']},ensure_ascii=False),flush=True)
 wall=time.perf_counter()-start
 (args.out/'audit.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in results))
 summary={'judge':'deepseek-flash','thinking':'disabled','max_tokens':1024,'sample_rate':args.sample_rate,'episodes':len(results),'successful':sum(r['status']=='ok' for r in results),'workers':args.workers,'wall_seconds':wall,'sum_request_seconds':sum(r['seconds'] for r in results),'prompt_tokens':sum(r.get('usage',{}).get('prompt_tokens',0) for r in results),'completion_tokens':sum(r.get('usage',{}).get('completion_tokens',0) for r in results),'purpose':'supplementary visible-evidence semantic audit; not replacement for hidden-target scores'}
 (args.out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
