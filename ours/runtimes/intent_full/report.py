"""Join existing B0/B1 and new diagnostics only on the fixed full-dataset IDs."""
import json,hashlib
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parent;P=ROOT.parent;C=ROOT/'campaigns/full-20261103-v1'
def load(p):return json.loads(p.read_text())
def main():
 groups=defaultdict(list);missing=[];sources={}
 for model in ['qwen','gptoss']:
  for name in ['pi_bench_ours1','lifesim_ours1','mempabench_ours1','proagentbench_ours1']:
   ids=load(P/name/'ours1/data/private/subsets.json')['full']
   old=P/('ours1_runtime/campaigns/full-20261102-v1' if name in ['pi_bench_ours1','lifesim_ours1'] else 'ours2_runtime/campaigns/source-adapted-20261102-v1')/model
   for base in ['current_session','history_retrieval','full_history','correction_priority']:
    folder=old if base in ['current_session','history_retrieval'] else C/model
    for cid in ids:
     p=folder/'episodes'/f'{name}__{cid}__{base}.json'
     if not p.exists():missing.append(str(p));continue
     row=load(p);sources[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();groups[(model,name,base)].append(row)
 data={};lines=['# 新增策略全集结果','现有B0/B1仅复用相同任务ID的轨迹；新基线单独运行。受控合成任务探索，无训练，不是原版benchmark分数。','纠正优先为文本规则，其命中受明确措辞影响；full-history上下文更长，属于诊断参照。','规则unsupported不等于完整语义无依据假设；judge仅补充审核。','']
 for (model,name,base),rows in sorted(groups.items()):
  phases={}
  for k in ['0','1','2']:
   scores=[r['checkpoint_scores'][k] for r in rows];first=[next(t for t in r['trace'] if str(t['phase'])==k) for r in rows]
   phases[k]={'n':len(rows),'correct':sum(s['correct_action'] for s in scores),'first_correct':sum(t['score_record']['kind']=='commit' and t['score_record']['correct_action']==1 for t in first),'questions':sum(s['question_count'] for s in scores),'unnecessary_questions':sum(s['unnecessary_questions'] for s in scores),'irrelevant_questions':sum(s['irrelevant_questions'] for s in scores),'claims':sum(s['claim_count'] for s in scores),'unsupported_rule_claims':sum(s['unsupported_claim_count'] for s in scores),'checkpoints_with_claims':sum(s['claim_count']>0 for s in scores),'evidence_visible':sum(t['active_evidence_visible'] for t in first)}
  key='/'.join([model,name,base]);data[key]={'phases':phases,'error_episodes':sum(r['status']!='ok' for r in rows)}
  acc=', '.join(f"{phases[k]['correct']}/{len(rows)}" for k in phases)
  lines.append(f"- {key}：三阶段最终正确 {acc}；新会话首次直接正确 {phases['2']['first_correct']}/{len(rows)}；总问题数 {sum(s['questions'] for s in phases.values())}；错误episode {data[key]['error_episodes']}。")
 lines+=['',f'缺少轨迹：{len(missing)}；必须结合status.json判断是否运行完成。','详细分阶段指标及缺失清单见analysis.json，来源轨迹哈希见analysis-sources.json。']
 (C/'analysis.json').write_text(json.dumps({'groups':data,'missing':missing},ensure_ascii=False,indent=2));(C/'analysis-sources.json').write_text(json.dumps(sources,indent=2));(C/'RESULTS.md').write_text('\n'.join(lines)+'\n')
if __name__=='__main__':main()
