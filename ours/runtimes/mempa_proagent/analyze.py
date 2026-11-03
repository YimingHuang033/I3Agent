"""Summarize source-adapted Ours experiments without altering native results."""
from pathlib import Path
from collections import Counter,defaultdict
import json,argparse,hashlib
ROOT=Path(__file__).resolve().parent
MODELS=['Qwen3-8B','gpt-oss-20b'];BASES=['current_session','history_retrieval']
def rate(x,n):return x/n if n else None
def pct(x):return f'{100*x:.2f}%' if x is not None else 'NA'
def aggregate(rows):
 n=len(rows);phases={}
 for p in range(3):
  key=str(p);first=[next(t for t in r['trace'] if t['phase']==p) for r in rows]
  visible=[(r,t) for r,t in zip(rows,first) if t['active_evidence_visible']]
  missing=[(r,t) for r,t in zip(rows,first) if not t['active_evidence_visible']]
  scores=[r['checkpoint_scores'][key] for r in rows]
  phases[key]={'n':n,'correct':sum(s['correct_action'] for s in scores),'accuracy':rate(sum(s['correct_action'] for s in scores),n),
    'first_commit':sum(s['first_response_commit'] for s in scores),
    'first_correct_commit':sum(t['score_record']['kind']=='commit' and t['score_record']['correct_action']==1 for t in first),
    'questions':sum(s['question_count'] for s in scores),'unnecessary_questions_oracle':sum(s['unnecessary_questions'] for s in scores),
    'irrelevant_questions':sum(s['irrelevant_questions'] for s in scores),
    'abstentions':sum(not s['committed'] for s in scores),'wrong_commits':sum(s['committed'] and not s['correct_action'] for s in scores),
    'first_active_evidence_visible':len(visible),'visible_rate':rate(len(visible),n),
    'correct_when_visible':sum(r['checkpoint_scores'][key]['correct_action'] for r,t in visible),
    'correct_when_missing':sum(r['checkpoint_scores'][key]['correct_action'] for r,t in missing),
    'claims':sum(s['claim_count'] for s in scores),'unsupported_oracle_claims':sum(s['unsupported_claim_count'] for s in scores),
    'checkpoints_with_claims':sum(s['claim_count']>0 for s in scores)}
 errors=Counter(e['error'].split(':',1)[0]+': '+e['error'].split(':',1)[-1].strip().splitlines()[0] for r in rows for e in r['errors'])
 questions=sum(x['questions'] for x in phases.values());claims=sum(x['claims'] for x in phases.values())
 return {'episodes':n,'error_episodes':sum(r['status']!='ok' for r in rows),'infrastructure_error_events':sum(e.get('category')=='infrastructure' for r in rows for e in r['errors']),
  'errors':dict(errors),'all_three_correct':sum(all(s['correct_action'] for s in r['checkpoint_scores'].values()) for r in rows),
  'phase':phases,'questions':questions,'questions_per_episode':rate(questions,n),'claims':claims,
  'unsupported_oracle_claims':sum(x['unsupported_oracle_claims'] for x in phases.values()),
  'claim_checkpoint_coverage':rate(sum(x['checkpoints_with_claims'] for x in phases.values()),n*3),
  'requests':sum(len(r['trace']) for r in rows),'length_finishes':sum(t.get('finish_reason')=='length' for r in rows for t in r['trace'])}

def main():
 p=argparse.ArgumentParser();p.add_argument('--campaign',default='source-adapted-20261102-v1');a=p.parse_args();campaign=ROOT/'campaigns'/a.campaign;rows=[]
 for label in ['qwen','gptoss']:
  out=campaign/label;manifest=json.loads((out/'manifest.json').read_text())
  assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==sha for p,sha in manifest['files'].items())
  for path in sorted((out/'episodes').glob('*.json')):rows.append(json.loads(path.read_text()))
 assert len(rows)==len({(r['benchmark'],r['model'],r['baseline'],r['episode_id']) for r in rows})
 result={'campaign':str(campaign),'completed_model_episodes':len(rows),'projects':{}}
 for name in ['mempabench_ours1','proagentbench_ours1']:
  root=ROOT.parent/name/'ours1';groups={};participants=defaultdict(list)
  gold={x['episode_id']:x for x in map(json.loads,(root/'data/private/oracle.jsonl').read_text().splitlines())}
  allrows=[r for r in rows if r['benchmark']==name]
  for m in MODELS:
   groups[m]={}
   for b in BASES:
    selected=[r for r in allrows if r['model']==m and r['baseline']==b]
    if selected:groups[m][b]=aggregate(selected)
  for r in allrows:participants[gold[r['episode_id']]['source'].get('persona',gold[r['episode_id']]['source'].get('participant_file'))].append(r)
  stats={'groups':groups,'source_subject_counts':{k:len(v) for k,v in participants.items()},'campaign':str(campaign),'native_benchmark_score':False}
  result['projects'][name]=stats;dest=root/'results'/a.campaign;dest.mkdir(parents=True,exist_ok=True);(dest/'summary.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2))
  design=(root/'EXPERIMENT.md').read_text().split('<!-- RESULTS -->')[0]
  lines=['<!-- RESULTS -->\n\n## 已执行结果\n',f'运行 `{a.campaign}`；此表只汇总已保存的{len(allrows)}次模型episode，不把尚未执行项目计为成功。\n',
  '| 模型 | 基线 | 已执行 | 阶段0正确 | 阶段1正确 | 阶段2正确 | 问题/episode | 错误episode |\n|---|---|---:|---:|---:|---:|---:|---:|\n']
  for m,bs in groups.items():
   for b,g in bs.items():lines.append(f"| {m} | {b} | {g['episodes']} | {' | '.join(pct(g['phase'][str(i)]['accuracy']) for i in range(3))} | {g['questions_per_episode']:.3f} | {g['error_episodes']} |\n")
  lines+=['\n阶段2允许澄清后的最终正确率不等同记忆保持。B0可重新询问脚本用户；B1的有效证据可见率、首答正确率及断言覆盖率详见JSON。无效输出和基础设施失败均保留，不能把协议完成当作做对。没有把本表称作原版PSA/PET/BRS或When/How成绩。\n',f'机器结果：`results/{a.campaign}/summary.json`；全轨迹：`{campaign}/{{qwen,gptoss}}/episodes/`。\n']
  (dest/'EXPERIMENT.md').write_text(design+''.join(lines));(root/'EXPERIMENT.md').write_text(design+''.join(lines))
 (campaign/'analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({'completed_model_episodes':len(rows),'projects':list(result['projects'])}))
if __name__=='__main__':main()
