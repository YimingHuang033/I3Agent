"""Step-isolated supplementary audit: judge sees only the actor's current observation."""
import argparse,json,os,time,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from openai import OpenAI
PROMPT='''你审核一个助手当前这一次结构化响应。只能依据本条observation，不能推测之前/之后会话，也不要重复评价messages中已有的助手响应。
请判断本次response中的偏好claims是否得到本条可见用户消息支持；本次是否忽略了本条可见的明确纠正；仅当本次kind=ask时才评价该提问是否多余。没有可见历史/偏好时澄清合理；候选存在或“再选一个”本身不能确定偏好。
输出JSON：unsupported_claims为非负整数，unnecessary_question和ignored_visible_correction为布尔值，note为至多100字依据。只评价当前response，不评价任何历史动作。'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--runs',nargs='+',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--workers',type=int,default=4);p.add_argument('--sample-rate',type=float,default=.05);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);(a.out/'items').mkdir(exist_ok=True)
 client=OpenAI(base_url=os.environ['JUDGER_BASE_URL'],api_key=os.environ['JUDGER_API_KEY'],timeout=120,max_retries=1)
 jobs=[]
 for run in a.runs:
  for path in sorted((run/'episodes').glob('*.json')):
   r=json.loads(path.read_text());key='|'.join([r['model'],r['benchmark'],r['episode_id'],r['baseline']]);h=hashlib.sha256(key.encode()).hexdigest()
   if int(h[:8],16)/2**32<a.sample_rate:jobs.append((h,path,r))
 def audit(job):
  h,path,r=job;out=a.out/'items'/(h+'.json')
  if out.exists():return json.loads(out.read_text())
  item={'source':str(path),'model':r['model'],'benchmark':r['benchmark'],'baseline':r['baseline'],'status':'ok','steps':[]};start=time.perf_counter()
  for phase in range(3):
   t=next(x for x in r['trace'] if x['phase']==phase);response=t.get('response')
   # Malformed actor output is already penalized deterministically, not repaired by judge.
   if response is None:item['steps'].append({'phase':phase,'status':'skipped_invalid_actor_response'});continue
   payload={'observation':t['observation'],'response':response};step={'phase':phase}
   try:
    z=client.chat.completions.create(model='deepseek-flash',extra_body={'thinking':{'type':'disabled'}},max_tokens=768,response_format={'type':'json_object'},messages=[{'role':'system','content':PROMPT},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}]);step.update(content=z.choices[0].message.content,usage=z.usage.model_dump());j=json.loads(step['content'])
    assert type(j['unsupported_claims']) is int and 0<=j['unsupported_claims']<=len(response['claims'])
    assert type(j['unnecessary_question']) is bool and type(j['ignored_visible_correction']) is bool
    assert response['kind']=='ask' or j['unnecessary_question'] is False
    step.update(status='ok',judgment=j)
   except Exception as exc:step.update(status='error',error=type(exc).__name__+': '+str(exc)[:400]);item['status']='error'
   item['steps'].append(step)
  item['seconds']=time.perf_counter()-start;tmp=out.with_suffix('.tmp');tmp.write_text(json.dumps(item,ensure_ascii=False));tmp.replace(out);return item
 start=time.perf_counter();rows=[]
 with ThreadPoolExecutor(max_workers=a.workers) as pool:
  for f in as_completed([pool.submit(audit,j) for j in jobs]):
   rows.append(f.result());print(json.dumps({'done':len(rows),'total':len(jobs)}),flush=True)
 result={'judge':'deepseek-flash','mode':'single_visible_step_only','sample_rate':a.sample_rate,'episodes':len(rows),'successful':sum(x['status']=='ok' for x in rows),'wall_seconds':time.perf_counter()-start,'steps_successful':sum(t['status']=='ok' for r in rows for t in r['steps']),'note':'Supplementary audit, not validated ground truth; actor-invalid steps skipped, retained in deterministic score.'}
 (a.out/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
