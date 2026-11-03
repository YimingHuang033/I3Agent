"""Read-only trajectory aggregation; writes reports, never changes scores or reruns models."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,json,hashlib,random,statistics
from datetime import datetime
ROOT=Path(__file__).resolve().parent
MODELS=['Qwen3-8B','gpt-oss-20b'];BASES=['current_session','history_retrieval'];PHASES=['初次省略','明确纠正','新会话省略']
def dump(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
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
def differences(rows):
 out={}
 for model in MODELS:
  items=[r for r in rows if r['model']==model];mapped={(r['benchmark'],r['episode_id'],r['baseline']):r for r in items}
  templates=defaultdict(lambda:defaultdict(list))
  for r in items:
   if r['baseline']!=BASES[0]:continue
   other=mapped[(r['benchmark'],r['episode_id'],BASES[1])];key=(r['benchmark'],r['template_id'])
   for p in range(3):templates[key]['phase'+str(p)].append(other['checkpoint_scores'][str(p)]['correct_action']-r['checkpoint_scores'][str(p)]['correct_action'])
   templates[key]['questions'].append(sum(s['question_count'] for s in other['checkpoint_scores'].values())-sum(s['question_count'] for s in r['checkpoint_scores'].values()))
  rng=random.Random(42);keys=sorted(templates);out[model]={}
  for metric in ['phase0','phase1','phase2','questions']:
   vals=[statistics.mean(templates[k][metric]) for k in keys]
   boots=sorted(statistics.mean(rng.choices(vals,k=len(vals))) for _ in range(2000))
   out[model][metric]={'B1_minus_B0':statistics.mean(vals),'template_bootstrap_95_interval':[boots[49],boots[1949]],'templates':len(vals),'replicates':2000}
 return out

def summarize(rows,pairs_by_bench,judge):
 groups={};conditions={};splits={};distractors={};paired={};worst={}
 for m in MODELS:
  groups[m]={};conditions[m]={};splits[m]={};distractors[m]={};paired[m]={};worst[m]={}
  for b in BASES:
   selected=[r for r in rows if r['model']==m and r['baseline']==b];groups[m][b]=aggregate(selected)
   conditions[m][b]={k:aggregate([r for r in selected if r['condition']==k]) for k in ['S','R','U0','U1']}
   splits[m][b]={k:aggregate([r for r in selected if r['split']==k]) for k in ['development','heldout']}
   distractors[m][b]={str(k):aggregate([r for r in selected if r['variant']['distractors']==k]) for k in [0,8,24]}
   byid={(r['benchmark'],r['episode_id']):r for r in selected};out=defaultdict(Counter)
   for bench,pairs in pairs_by_bench.items():
    for pair in pairs:
     if (bench,pair['episode_ids'][0]) not in byid:continue
     twins=[byid[(bench,cid)] for cid in pair['episode_ids']];c=out[pair['kind']];c['pairs']+=1
     c['both_correct_phase0']+=all(r['checkpoint_scores']['0']['correct_action'] for r in twins)
     c['both_first_correct_phase0']+=all(next(t for t in r['trace'] if t['phase']==0)['score_record']['correct_action'] for r in twins)
     c['both_asked_phase0']+=all(r['checkpoint_scores']['0']['question_count'] for r in twins)
   paired[m][b]={k:dict(v) for k,v in out.items()}
   tg=defaultdict(list)
   for r in selected:tg[r['benchmark']+'/'+r['template_id']].append(r)
   worst[m][b]=sorted([{'template':k,'episodes':len(v),'phase2_accuracy':aggregate(v)['phase']['2']['accuracy']} for k,v in tg.items()],key=lambda x:(x['phase2_accuracy'],x['template']))[:5]
 audit={}
 for m in MODELS:
  audit[m]={}
  for b in BASES:
   js=[j for j in judge if j['model']==m and j['baseline']==b];valid=[j for j in js if j['status']=='ok']
   audit[m][b]={'sampled':len(js),'successful':len(valid),'failed':len(js)-len(valid),'judge_events':{k:sum(j['judgment'][k] for j in valid) for k in ['unsupported_preference_claims','unnecessary_questions','ignored_explicit_corrections']}}
 quality={'b0_successful_judge_items':0,'b0_judge_unnecessary_positive_but_rule_zero':0,'examples':[]}
 for j in judge:
  if j['baseline']!=BASES[0] or j['status']!='ok':continue
  quality['b0_successful_judge_items']+=1
  source=json.loads(Path(j['source']).read_text())
  rule=sum(x['unnecessary_questions'] for x in source['checkpoint_scores'].values())
  if rule==0 and j['judgment']['unnecessary_questions']>0:
   quality['b0_judge_unnecessary_positive_but_rule_zero']+=1
   if len(quality['examples'])<3:quality['examples'].append({'source':j['source'],'judgment':j['judgment']})
 return {'judge_quality_check':quality,'groups':groups,'condition':conditions,'split':splits,'distractors':distractors,'paired':paired,'baseline_difference':differences(rows),'worst_phase2_templates':worst,'judge':audit}

def report(name,s,campaign):
 lines=[f'# {name}：实验设计与结果\n',f'运行：`{campaign.name}`；统计生成：{datetime.now().astimezone().isoformat()}。数据来源为完整逐episode轨迹，未修改评分或补跑模型/裁判。\n',
 '## 设计与范围\n',
 '目标：区分当前省略但仍有效的历史偏好，以及被用户明确替换的旧偏好。每项目32个合成模板，交叉2个方向×3种历史长度（0/8/24）×3种措辞×S/R/U0/U1四条件，得到2304条任务、1152对。S/R检验保留/修改；U0/U1披露前信息相同但私有目标不同，澄清后可区分。模板24个development、8个heldout；每模板72条变体，不能把变体视为独立真实任务。\n',
 '每条任务三阶段：初次省略 → 外生、明确且持久的纠正 → 新会话再次省略。每阶段最多一次澄清，脚本用户直接给出偏好答案；每条最多6次请求。动作是合成候选ID，未调用AppWorld、网页或原版工具链。没有训练。\n',
 'B0=current_session：只保留当前会话，阶段2没有历史，因此可以重新提问。B1=history_retrieval：在同样提示词/预算下，CPU Qwen3-Embedding-0.6B按相似度取top2用户历史并按时间排序；没有结构化偏好记忆或显式最新状态管理。\n',
 '模型：Qwen3-8B关闭thinking；gpt-oss-20b low reasoning；两张4090各一模型，8并发、temperature=0、seed=42、max_tokens=768，JSON结构约束。每项目2304×2基线×2模型=9216次模型episode，单次运行；模型间推理设置不同，不能归因于纯模型参数量。数据/提示词/actor代码在manifest中冻结，完整快照见campaign/reproducibility.tar.gz。\n',
 '## 指标口径\n',
 '阶段正确率以该组所有episode为分母；非法动作、弃权、连接失败均保留，失败阶段计0。协议完成不等于正确。first-correct为未提问就直接做对；问题负担为三阶段问题总数/episode。阶段2最终准确率允许重新询问，因此不等于无澄清的记忆保持率。规则unsupported计数要求同时匹配私有当前目标与有效引用，不完全等同可见依据幻觉；另有约5%轨迹的DeepSeek Flash非thinking语义抽查。claims可为空，必须同时报告断言覆盖率。\n',
 '## 主要结果\n',
 '| 模型 | 基线 | 初次省略正确 | 明确纠正正确 | 新会话省略正确 | 提问/episode | 含错误episode |\n|---|---|---:|---:|---:|---:|---:|\n']
 for m in MODELS:
  for b in BASES:
   g=s['groups'][m][b];n=g['episodes'];values=[f"{pct(g['phase'][str(p)]['accuracy'])} ({g['phase'][str(p)]['correct']}/{n})" for p in range(3)]
   lines.append(f"| {m} | {'B0 当前会话' if b==BASES[0] else 'B1 历史检索'} | {' | '.join(values)} | {g['questions_per_episode']:.3f} | {g['error_episodes']}/{n} |\n")
 lines+=['\n### 检索相对B0的配对差值\n','以下在同一episode上比较B1−B0，再以模板为簇做2000次bootstrap（seed=42），给出探索性95%区间。区间反映模板构成不确定性，不反映跨模型重跑或真实用户分布；不作显著性或因果宣称。\n']
 for m in MODELS:
  d=s['baseline_difference'][m];p=d['phase2'];q=d['questions'];lines.append(f"- {m}：阶段2准确率差 {100*p['B1_minus_B0']:+.2f} 个百分点，区间 [{100*p['template_bootstrap_95_interval'][0]:.2f}, {100*p['template_bootstrap_95_interval'][1]:.2f}]；问题数差 {q['B1_minus_B0']:+.3f}/episode，区间 [{q['template_bootstrap_95_interval'][0]:.3f}, {q['template_bootstrap_95_interval'][1]:.3f}]。\n")
 lines+=['\n### 首答、证据可见性与断言覆盖\n']
 for m in MODELS:
  for b in BASES:
   g=s['groups'][m][b];p=g['phase']['2'];lines.append(f"- {m} / {b}：阶段2首次直接正确 {p['first_correct_commit']}/{p['n']}；有效纠正证据首次可见 {p['first_active_evidence_visible']}/{p['n']}；可见时最终正确 {p['correct_when_visible']}/{p['first_active_evidence_visible']}，不可见时正确 {p['correct_when_missing']}/{p['n']-p['first_active_evidence_visible']}（0分母不定义）。有断言的检查点占比 {pct(g['claim_checkpoint_coverage'])}；规则不支持断言 {g['unsupported_oracle_claims']}/{g['claims']}。\n")
 lines+=['\n### 条件与成对检查（阶段0）\n']
 for m in MODELS:
  for b in BASES:
   cond=s['condition'][m][b];parts=[f"{k} {pct(cond[k]['phase']['0']['accuracy'])}" for k in ['S','R','U0','U1']];pairs=s['paired'][m][b];sr=pairs['retained_vs_revised'];u=pairs['ambiguity_twins']
   lines.append(f"- {m} / {b}：{'；'.join(parts)}。S/R双方最终正确 {sr['both_correct_phase0']}/{sr['pairs']}对；双方首答直接正确 {sr['both_first_correct_phase0']}/{sr['pairs']}对。U0/U1双方都提问 {u['both_asked_phase0']}/{u['pairs']}对，双方最终正确 {u['both_correct_phase0']}/{u['pairs']}对。\n")
 lines+=['\n### development / heldout与干扰长度\n']
 for m in MODELS:
  for b in BASES:
   sp=s['split'][m][b];ds=s['distractors'][m][b];lines.append(f"- {m} / {b}：阶段2 development {pct(sp['development']['phase']['2']['accuracy'])}，heldout {pct(sp['heldout']['phase']['2']['accuracy'])}；0/8/24条干扰下分别为 {' / '.join(pct(ds[str(k)]['phase']['2']['accuracy']) for k in [0,8,24])}。\n")
 lines+=['\n## 错误与裁判\n']
 for m in MODELS:
  for b in BASES:
   g=s['groups'][m][b];j=s['judge'][m][b];lines.append(f"- {m} / {b}：基础设施错误事件 {g['infrastructure_error_events']}，输出达到长度上限 {g['length_finishes']} 次；错误类型 `{json.dumps(g['errors'],ensure_ascii=False)}`。裁判 {j['successful']}/{j['sampled']} 成功，失败{j['failed']}；审核判定的无依据断言/多余提问/忽略纠正事件数分别为 {list(j['judge_events'].values())}（仅成功抽查样本，未经人工校准，不是全集真值）。\n")
 q=s['judge_quality_check']
 lines.append(f"\n**裁判质量检查：** B0成功抽查{q['b0_successful_judge_items']}条，其中{q['b0_judge_unnecessary_positive_but_rule_zero']}条在协议记录的多余提问数为0时，裁判仍给出正的多余提问数。检查说明可见跨会话可见性误解、重复轨迹计数或自相矛盾；该指标不可作为本轮主结论。此对照是设计一致性诊断，不是完整人工真值标注。裁判其他维度也未经人工校准，均仅保留为探索性附件。\n")
 lines+=['\n## 解释与限制\n',
 '1. B0可在每个缺信息阶段直接询问脚本用户，接近满分不证明它推断出了历史偏好。当前设计主要揭示“省问题”与“最终正确”的权衡，不能单用最终正确率选出最佳意图推断系统。\n',
 '2. B1减少问题，但阶段2丢失/误用纠正的风险需要结合有效证据可见率、首答和最终准确率判断。相似度top2不保证取到最新纠正；也不能仅凭总体差异断言所有错误都由检索造成。\n',
 '3. gpt-oss的无效提交等协议问题会影响动作分数；这是模型与本次结构化接口组合的表现，不等同纯偏好推断能力。空claims、不同推理设置和输出预算也限制跨模型比较。\n',
 '4. 合成模板尚未经过系统人工审核；只做一轮、只含两基线，没有真实工具状态、长期用户行为或训练。heldout是未用于校准的模板分组，不是训练泛化证明。裁判为固定哈希约5%抽样，失败不自动补判，成功不保证语义正确。\n',
 '5. 原版Pi-Bench/LifeSim源码和tim环境保持不变。11月2日02:01因一次连接错误暂停，11:20恢复；模型在12:55/13:20完成。active time排除长时间暂停，不能与实际墙钟跨度混淆。\n',
 '\n## 复现与文件\n',f'完整轨迹：`{campaign}/{{qwen,gptoss}}/episodes/`。裁判：`{campaign}/judge/`。本报告机器可读统计：`results/{campaign.name}/summary.json`；包含完整分组、配对计数、置信区间及最弱模板。共享汇总入口：`python3 ours1_runtime/analyze.py --campaign {campaign.name}`。读取既有结果，无API调用，错误和失败不移除。\n']
 return ''.join(lines)

def overview(s,campaign):
 lines=['# Ours1 全集结果汇总\n',
 '两项目合计64个模板、4608条任务，两个模型×两基线，共18432次模型episode，全部有记录。它们是合成偏好选择任务，不是原版Pi-Bench/LifeSim工具执行任务；没有AppWorld或网页操作。\n',
 '## 主要结果\n',
 '| 模型 | 基线 | 初次省略正确率 | 明确纠正正确率 | 新会话省略正确率 | 问题数/episode |\n|---|---|---:|---:|---:|---:|\n']
 for m in MODELS:
  for b in BASES:
   g=s['groups'][m][b];lines.append(f"| {m} | {'B0 当前会话' if b==BASES[0] else 'B1 检索历史'} | {' | '.join(pct(g['phase'][str(p)]['accuracy']) for p in range(3))} | {g['questions_per_episode']:.3f} |\n")
 lines+=['\n每行分母4608。正确率包括澄清后的最终选择，错误/弃权不移出分母。B0阶段2几乎全部重新提问，因此100%不能解释为记住了偏好。\n',
 '## 观察与解释\n']
 for m in MODELS:
  g=s['groups'][m][BASES[1]];d=s['baseline_difference'][m];p=g['phase']['2'];pair=s['paired'][m][BASES[1]]
  lines.append(f"- {m}：检索每任务减少 {-d['questions']['B1_minus_B0']:.3f} 次提问，但阶段2准确率下降 {-100*d['phase2']['B1_minus_B0']:.2f} 个百分点。阶段2首次直接做对 {p['first_correct_commit']}/{p['n']}，有效纠正证据首次进入上下文仅 {pct(p['visible_rate'])}；可见时最终做对 {p['correct_when_visible']}/{p['first_active_evidence_visible']}。\n")
  lines.append(f"  S/R配对的双方首答正确为 {pair['retained_vs_revised']['both_first_correct_phase0']}/{pair['retained_vs_revised']['pairs']}；U0/U1歧义配对双方都澄清为 {pair['ambiguity_twins']['both_asked_phase0']}/{pair['ambiguity_twins']['pairs']}。这区分了省提问和在真正歧义时提问，不能只用一个总分排名。\n")
 lines+=['\n证据表明本次相似度top2检索常遗漏新会话所需的纠正；这是现有检索基线的局限，不足以证明所有历史检索或所有harness都无效。下一轮可预注册full-history上界、最近纠正优先/结构化偏好状态，并分开报告澄清前后正确率。先修正裁判的可见性边界，不据现有裁判分数优化模型。这里只提出后续设计，未启动新实验或训练。\n',
 '## 数据完整性、错误与裁判\n',
 '- 从18432份轨迹独立重算，ID完整且唯一，分组计数/请求数/提问数与runner汇总一致；冻结代码/数据/配置哈希一致。原始结果未覆盖。\n',
 '- Qwen含1条基础设施连接错误；gpt-oss含718条模型输出错误，其中706次Invalid commit。gpt-oss有11次输出达到长度上限；所有失败都保留。\n',
 '- 裁判903条抽查，902条成功、1条JSON字符串未闭合；未重试或人工修补评分。B0的419条成功审核中，275条在协议记录的多余提问为0时仍被judge判为多余。示例说明有跨会话可见性混淆、重复计数和自相矛盾。**裁判多余提问指标不可支撑本轮结论**；其他语义指标也未经人工校准，只存档作探索。\n',
 '- 分析按模板聚类，使用2000次bootstrap生成B1−B0的探索性区间，详情在分项目报告与analysis.json；单次运行不提供跨随机种子的稳定性结论。\n',
 '## 时间与复现\n',
 '2026-11-02凌晨启动，02:01因连接错误暂停，11:20恢复；gpt-oss于12:55:57完成，Qwen于13:20:07完成，之后裁判约4.76分钟。Qwen累计active time约125.1分钟，gpt-oss约100.9分钟，排除长时间暂停，不是从首次启动到结束的墙钟时间。\n',
 '所有原版源码与tim环境未改。本次只增加离线analyze.py和报告，不调用模型。复现：`python3 ours1_runtime/analyze.py --campaign full-20261102-v1`。同目录analysis.json含全部分组、配对、模板bootstrap区间和诊断。\n',
 '## 分项目报告\n',
 '- [Pi-Bench Ours1设计与结果](../../../pi_bench_ours1/ours1/EXPERIMENT.md)\n',
 '- [LifeSim Ours1设计与结果](../../../lifesim_ours1/ours1/EXPERIMENT.md)\n']
 return ''.join(lines)


def main():
 p=argparse.ArgumentParser();p.add_argument('--campaign',default='full-20261102-v1');a=p.parse_args();campaign=ROOT/'campaigns'/a.campaign
 rows=[];pairs={};templates={};expected={};integrity={}
 for name in ['pi_bench_ours1','lifesim_ours1']:
  root=ROOT.parent/name/'ours1';expected[name]=set(json.loads((root/'data/private/subsets.json').read_text())['full']);pairs[name]=json.loads((root/'data/private/pairs.json').read_text());templates[name]={x['template_id']:x for x in json.loads((root/'data/private/templates.json').read_text())}
 for label in ['qwen','gptoss']:
  folder=campaign/label;before=json.loads((folder/'summary.json').read_text());r=[]
  for path in sorted((folder/'episodes').glob('*.json')):
   j=json.loads(path.read_text());j['split']=templates[j['benchmark']][j['template_id']]['split'];assert set(j['checkpoint_scores'])=={'0','1','2'};r.append(j)
  assert len(r)==9216 and len({(x['benchmark'],x['episode_id'],x['baseline']) for x in r})==9216
  for name in expected:
   for b in BASES:assert {x['episode_id'] for x in r if x['benchmark']==name and x['baseline']==b}==expected[name]
  agg=aggregate(r);assert agg['error_episodes']==before['error_episodes'] and agg['requests']==before['requests']
  for b in BASES:
   g=aggregate([x for x in r if x['baseline']==b]);old=before['groups'][b]
   assert g['questions']==old['questions'] and all(g['phase'][str(i)]['correct']==old['correct_actions'][str(i)] for i in range(3))
  manifest=json.loads((folder/'manifest.json').read_text());bad=[str(path) for path,h in manifest['files'].items() if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=h]
  assert not bad,bad
  integrity[label]={'episodes':len(r),'unique_and_complete':True,'matches_runner_summary':True,'frozen_input_hashes_match':True};rows.extend(r)
 judge=[json.loads(p.read_text()) for p in (campaign/'judge/items').glob('*.json')];assert len(judge)==903
 allsummary=summarize(rows,pairs,judge);allsummary.update(integrity=integrity,campaign=str(campaign),generated_at=datetime.now().astimezone().isoformat())
 dump(campaign/'analysis.json',allsummary)
 (campaign/'RESULTS.md').write_text(overview(allsummary,campaign))
 for name in expected:
  subset=[r for r in rows if r['benchmark']==name];js=[j for j in judge if j['benchmark']==name];s=summarize(subset,{name:pairs[name]},js);s.update(integrity=integrity,campaign=str(campaign),benchmark=name)
  root=ROOT.parent/name/'ours1';dump(root/'results'/a.campaign/'summary.json',s);(root/'EXPERIMENT.md').write_text(report(name,s,campaign))
 print(json.dumps({'groups':allsummary['groups'],'differences':allsummary['baseline_difference'],'integrity':integrity},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
