"""Resumable Ours1 experiment driver. Native benchmarks remain unchanged."""
import argparse
import fcntl
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
import threading
import time
import traceback

SYSTEM = '''你是处理合成任务的助手。只依据给出的用户消息和检索历史选择候选方案，区分仍有效的偏好和被明确更新的偏好。历史中的助手断言不是用户偏好证据。信息不足时可以针对一个偏好槽澄清；每个检查点至多一次。已给出的明确更新应当应用到当前行动。不要执行任何真实外部操作。
输出严格 JSON，不要 Markdown 或解释文字，恰好包含以下字段：
{"kind":"commit 或 ask 或 abstain","option_id":"候选ID或null","question_slot":"所问偏好槽或null","claims":[{"slot":"偏好槽","value":"你明确断言的当前用户偏好值","evidence_ids":["支持该断言的用户消息ID"]}]}
commit 必须选择一个候选且 question_slot=null；ask 必须 option_id=null 且 question_slot 为所问槽名；abstain 两字段均null。claims 仅记录你实际明确断言的当前偏好，可为空。不要编造证据ID。clarifications_remaining=0 时必须 commit 或 abstain。'''


def read_rows(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def now():
    return datetime.now().astimezone().isoformat()


class CachedEmbedder:
    def __init__(self, path):
        import torch
        from sentence_transformers import SentenceTransformer
        torch.set_num_threads(4)
        self.model = SentenceTransformer(path, device='cpu', local_files_only=True)
        self.cache, self.lock = {}, threading.Lock()
        self.calls = self.encoded_texts = 0
        self.seconds = 0.0

    def __call__(self, texts):
        with self.lock:
            missing = list(dict.fromkeys(x for x in texts if x not in self.cache))
            if missing:
                start = time.perf_counter()
                vectors = self.model.encode(missing, normalize_embeddings=True, batch_size=32).tolist()
                self.cache.update(zip(missing, vectors))
                self.seconds += time.perf_counter()-start
                self.calls += 1
                self.encoded_texts += len(missing)
            return [self.cache[x] for x in texts]

    def stats(self):
        return {'encode_batches':self.calls,'unique_texts_encoded':self.encoded_texts,'encode_seconds':self.seconds}


def quantile(values, q):
    if not values:
        return None
    values = sorted(values)
    return values[round((len(values)-1)*q)]


def select_cases(root, subset):
    public = {x['episode_id']:x for x in read_rows(root/'data/public/episodes.jsonl')}
    oracle = {x['episode_id']:x for x in read_rows(root/'data/private/oracle.jsonl')}
    subsets = json.loads((root/'data/private/subsets.json').read_text())
    ids = subsets[subset]
    # Finish the pilot first without executing these cases twice in a full run.
    priority = set(subsets['pilot'])
    ids = sorted(ids, key=lambda cid: (cid not in priority, cid))
    return [(public[cid], oracle[cid]) for cid in ids]


def atomic_json(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def case_key(root, case, baseline):
    return root.parent.name + '__' + case[0]['episode_id'] + '__' + baseline


def fingerprint(projects, args):
    files = [Path(__file__), Path(__file__).with_name('protocol.py')]
    for project in projects:
        root = project/'ours1'
        files += [root/x for x in ['data/public/episodes.jsonl', 'data/private/oracle.jsonl',
                  'data/private/subsets.json', 'configs/experiment.json', 'configs/response.schema.json']]
    return {'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
            'model':args.model,'model_kind':args.model_kind,'subset':args.subset,
            'max_tokens':args.max_tokens,'workers':args.workers,'temperature':0,'seed':42}


def prior_results(jobs, out, model):
    results=[]; pending=[]
    for root, case, baseline in jobs:
        path=out/(case_key(root,case,baseline)+'.json')
        if not path.exists():
            pending.append((root,case,baseline));continue
        row=json.loads(path.read_text())
        if row['episode_id']!=case[0]['episode_id'] or row['baseline']!=baseline or row['model']!=model:
            raise ValueError('Checkpoint identity mismatch: '+str(path))
        if set(row['checkpoint_scores'])!={'0','1','2'}:
            raise ValueError('Incomplete checkpoint: '+str(path))
        results.append(row)
    return results,pending


def normalize_response(content):
    if not isinstance(content,str) or not content.strip():
        raise ValueError('empty assistant content')
    text=content.strip()
    if text.startswith('```json') and text.endswith('```'):
        text=text[7:-3].strip()
    return json.loads(text)


def run_case(root, case, baseline, args, embedder, schema, client, out):
    from protocol import EpisodeController, summarize_episode
    import jsonschema
    public, gold = case
    controller=EpisodeController(public,gold,baseline,embedder,top_k=2)
    started=time.perf_counter()
    trace=[];errors=[];record_start=0
    key=case_key(root,case,baseline)
    for _ in range(6):
        if controller.closed:
            break
        phase=controller.phase
        observation_started=time.perf_counter()
        obs=controller.observation()
        observation_seconds=time.perf_counter()-observation_started
        row={'phase':phase,'observation':obs,'observation_seconds':observation_seconds,
             'active_evidence_visible':bool(controller.evidence & {x['id'] for x in obs['history']+obs['messages']}),
             'request_started_at':now()}
        kwargs={'model':args.model,'temperature':0,'max_tokens':args.max_tokens,'seed':42,
          'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps(obs,ensure_ascii=False)}],
          'response_format':{'type':'json_schema','json_schema':{'name':'ours1_response','strict':True,'schema':schema}}}
        if args.model_kind=='qwen':
            kwargs['extra_body']={'chat_template_kwargs':{'enable_thinking':False}}
        else:
            kwargs['reasoning_effort']='low'
        requested=time.perf_counter()
        try:
            response=client.chat.completions.create(**kwargs)
            row['request_seconds']=time.perf_counter()-requested
            row['content']=response.choices[0].message.content
            row['finish_reason']=response.choices[0].finish_reason
            row['usage']=response.usage.model_dump() if response.usage else {}
            parsed=normalize_response(row['content'])
            jsonschema.validate(parsed,schema)
            controller.respond(parsed)
            row['response']=parsed
            row['score_record']=controller.records[-1]
        except Exception as exc:
            row.setdefault('request_seconds',time.perf_counter()-requested)
            row['error']=type(exc).__name__+': '+str(exc)[:800]
            errors.append({'phase':phase,'error':row['error'],'category': 'model_output' if isinstance(exc,(ValueError,jsonschema.ValidationError)) else 'infrastructure'})
            # No repair retry: invalid replies remain errors in denominator.
            controller.respond({'kind':'abstain','option_id':None,'question_slot':None,'claims':[]})
            row['score_record']=controller.records[-1]
            row['synthetic_abstention_for_failure']=True
        trace.append(row)
    result={'benchmark':root.parent.name,'episode_id':public['episode_id'],'template_id':gold['template_id'],
      'condition':gold['condition'],'variant':gold['variant'],'baseline':baseline,'model':args.model,
      'seconds':time.perf_counter()-started,'status':'ok' if not errors and controller.closed else 'error',
      'errors':errors,'trace':trace,'checkpoint_scores':summarize_episode(controller.records)}
    atomic_json(out/(key+'.json'),result)
    return result


def summarize(results,wall):
    rows=[t for r in results for t in r['trace']]
    durations=[t['request_seconds'] for t in rows]
    comp=sum(t.get('usage',{}).get('completion_tokens',0) for t in rows)
    prompt=sum(t.get('usage',{}).get('prompt_tokens',0) for t in rows)
    groups={}
    for baseline in ['full_history','correction_priority']:
        items=[r for r in results if r['baseline']==baseline]
        groups[baseline]={'episodes':len(items),'mean_episode_seconds':statistics.mean(r['seconds'] for r in items) if items else None,
            'error_episodes':sum(r['status']!='ok' for r in items),
            'correct_actions':{str(p):sum(r['checkpoint_scores'][str(p)]['correct_action'] for r in items) for p in range(3)},
            'questions':sum(v['question_count'] for r in items for v in r['checkpoint_scores'].values()),
            'unsupported_claims':sum(v['unsupported_claim_count'] for r in items for v in r['checkpoint_scores'].values()),
            'claims':sum(v['claim_count'] for r in items for v in r['checkpoint_scores'].values())}
    return {'episodes':len(results),'successful_episodes':sum(r['status']=='ok' for r in results),'error_episodes':sum(r['status']!='ok' for r in results),
      'requests':len(rows),'wall_seconds':wall,'episodes_per_minute':len(results)*60/wall,
      'successful_episodes_per_minute':sum(r['status']=='ok' for r in results)*60/wall,
      'request_latency_p50':quantile(durations,.5),'request_latency_p95':quantile(durations,.95),
      'mean_episode_seconds':statistics.mean(r['seconds'] for r in results),
      'completion_tokens':comp,'prompt_tokens':prompt,'completion_tokens_per_wall_second':comp/wall,
      'length_finishes':sum(t.get('finish_reason')=='length' for t in rows),'groups':groups}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--projects',nargs='+',type=Path,required=True)
    parser.add_argument('--base-url',required=True)
    parser.add_argument('--model',required=True)
    parser.add_argument('--model-kind',choices=['qwen','gptoss'],required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=8,choices=[1,4,8])
    parser.add_argument('--subset',choices=['discussion','pilot','full'],default='full')
    parser.add_argument('--max-tokens',type=int,default=768)
    parser.add_argument('--authorized-run',action='store_true',required=True)
    args=parser.parse_args()
    for project in args.projects:
        cfg=json.loads((project/'ours1/configs/experiment.json').read_text())
        if not cfg.get('execution_enabled') or (args.subset=='full' and not cfg.get('full_execution_enabled')):
            raise SystemExit('Run not enabled: '+str(project))
    args.out.mkdir(parents=True,exist_ok=True)
    lock=(args.out/'run.lock').open('w')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    (args.out/'episodes').mkdir(exist_ok=True)
    manifest=fingerprint(args.projects,args)
    mf=args.out/'manifest.json'
    if mf.exists() and json.loads(mf.read_text())!=manifest:
        raise SystemExit('Frozen configuration/code/data changed; choose a NEW output directory')
    atomic_json(mf,manifest)
    jobs=[(p/'ours1',case,b) for p in args.projects for case in select_cases(p/'ours1',args.subset)
          for b in ['full_history','correction_priority']]
    # Interleave projects so both benches appear from the first batch onward.
    jobs.sort(key=lambda j: (j[1][1]['template_id'], j[1][0]['episode_id'], j[2]))
    pilot_ids={p.name:set(json.loads((p/'ours1/data/private/subsets.json').read_text())['pilot']) for p in args.projects}
    jobs.sort(key=lambda j:j[1][0]['episode_id'] not in pilot_ids[j[0].parent.name])
    results,pending=prior_results(jobs,args.out/'episodes',args.model)
    session_started=time.perf_counter();session_prior=len(results)
    previous=json.loads((args.out/'progress.json').read_text()) if (args.out/'progress.json').exists() else {}
    elapsed_before=previous.get('active_seconds',0)
    def progress(state):
        elapsed=elapsed_before+time.perf_counter()-session_started
        value={'updated_at':now(),'state':state,'model':args.model,'subset':args.subset,
               'completed':len(results),'total':len(jobs),'resumed':session_prior,
               'protocol_error_episodes':sum(r['status']!='ok' for r in results),
               'infrastructure_errors':sum(e.get('category')=='infrastructure' for r in results for e in r['errors']),
               'active_seconds':elapsed,'episodes_per_minute':len(results)*60/max(elapsed,1)}
        atomic_json(args.out/'progress.json',value)
        print(json.dumps(value),flush=True)
    progress('starting')
    if not pending:
        progress('complete');return
    from openai import OpenAI
    client=OpenAI(base_url=args.base_url,api_key='local-vllm',timeout=120,max_retries=2)
    cfg=json.loads((args.projects[0]/'ours1/configs/experiment.json').read_text())
    embed=CachedEmbedder(cfg['baselines']['history_retrieval']['embedding_path'])
    schema=json.loads((args.projects[0]/'ours1/configs/response.schema.json').read_text())
    # Bounded waves limit pending requests and make infrastructure failure a circuit breaker.
    progress('running')
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for offset in range(0,len(pending),args.workers):
            wave=pending[offset:offset+args.workers]
            futures=[pool.submit(run_case,*job,args,embed,schema,client,args.out/'episodes') for job in wave]
            for future in as_completed(futures):results.append(future.result())
            progress('running')
            if any(e.get('category')=='infrastructure' for r in results[-len(wave):] for e in r['errors']):
                progress('blocked_infrastructure');raise SystemExit(2)
            if (args.out.parent/'STOP').exists():
                progress('stopped');return
    elapsed=elapsed_before+time.perf_counter()-session_started
    atomic_json(args.out/'summary.json',dict(summarize(results,elapsed),model=args.model,
        subset=args.subset,workers=args.workers,embedding_current_session=embed.stats(),completed_at=now(),
        timing='active time including current initialization; resume downtime excluded',native_benchmark_harness=False))
    progress('complete')

if __name__=='__main__':
    main()
