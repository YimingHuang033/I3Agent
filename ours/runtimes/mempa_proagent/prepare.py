"""Deterministic, source-linked preference overlays. Does not run native benchmarks."""
from pathlib import Path
import json,hashlib,shutil,subprocess,re
import yaml
R=Path('/home/tim/Proj/I3Agent');RT=R/'ours2_runtime'
def ident(s):return hashlib.sha256(s.encode()).hexdigest()[:16]
def save(p,j):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
def load(p):return yaml.safe_load(p.read_text())
def safe_text(s):
 s=re.sub(r'https?://\S+','[链接]',str(s));s=re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}','[邮箱]',s)
 s=re.sub(r'(?i)(?:[A-Z]:[\\/]|/home/|/Users/)\S+','[文件路径]',s)
 return s[:900]
def sources_mempa():
 repo=R/'MemPABench';data=R/'MemPABench-personas';defs={x['id']:x for x in load(repo/'configs/setting_definitions.yaml')['attributes']};items=[]
 for user in ['user_a','user_b','user_c','user_d']:
  prefs=load(data/user/'data/personas'/f'{user}_preferences.yaml')['matrix'];outline=load(data/user/'Authoring/outline/drafts'/user/'outline.yaml');changes=outline['evolving_map']
  for p in sorted((data/user/'Authoring/probe/drafts'/user).glob('fin_*/fin_*.yaml')):
   probe=load(p);cell=probe['meta']['cell'];context,attr=cell.split('_',1);definition=defs[attr];settings=definition['settings'];initial=prefs[context][attr]['setting']
   if cell in changes:
    old=changes[cell]['pre_setting'];new=changes[cell]['post_setting'];native_change=True
   else:
    old=initial;new=next(s['name'] for s in settings if s['name']!=old);native_change=False
   values=[old,new];desc={s['name']:s['pa_instruction'] for s in settings}
   items.append({'template_id':f'mempa_{user}_{cell}','domain':context,'scenario':f'{context} 场景：{definition["label"]}',
    'values':values,'descriptions':desc,'task':safe_text(probe['task']),'context_text':safe_text(probe.get('scenario','')),
    'source':{'repo':'MemPABench','persona':user,'probe':str(p.relative_to(data)),'cell':cell,'native_preference_change':native_change,'native_initial':initial},
    'split':'heldout' if user=='user_d' else 'development','cluster_id':f'{user}:{attr}',
    'review_status':'source_linked_synthetic_overlay_not_human_validated'})
 assert len(items)==112
 return items

def sources_pro():
 data=R/'ProAgentBench-events';attrs=[('work_response_detail',['先给结论，简短回应','给出详细解释和步骤']),('work_intervention',['等我主动询问再提供帮助','在我卡住时主动提供建议']),('work_solution_scope',['只完成当前明确请求','同时补充相关的下一步建议']),('work_action_control',['先展示计划并请我确认','选定方案后直接执行模拟行动'])]
 items=[];rawtotal=0
 for path in sorted(data.glob('志愿者*.json')):
  j=json.loads(path.read_text());events=j['events'];rawtotal+=len(events)
  # Deterministic temporal sampling, independent of outcome labels and future events.
  valid=[e for e in events if len(str(e.get('event_summary','')))>8]
  assert len(valid)>=8
  for k in range(8):
   index=round((len(valid)-1)*k/7);e=valid[index];slot,values=attrs[k%4]
   context=safe_text(e['event_summary']);history=[safe_text(x['event_summary']) for x in valid[max(0,index-3):index]]
   pid=path.stem;tid='pro_'+ident(pid+'|'+str(e['event_id'])+'|'+slot)
   items.append({'template_id':tid,'domain':'work','scenario':f'工作事件：{slot}','values':values,'descriptions':{v:v for v in values},
    'task':'针对当前工作上下文，选择本次助手的交互方式；不实际执行外部操作。','context_text':'当前事件摘要（发布方模型注释，非真值）：'+context,
    'source_history':history,'source':{'repo':'ProAgentBench public dataset','participant_file':path.name,'event_id':str(e['event_id']),'event_index':index,'annotation_is_ground_truth':False,'preferences':'synthetic_overlay'},
    'split':'heldout' if int(re.search(r'\d+',pid)[0])>=14 else 'development','cluster_id':pid,'review_status':'source_context_synthetic_preferences_not_human_validated'})
 assert len(items)==136, len(items)
 return items,rawtotal

def generate(name,templates):
 root=R/name;o=root/'ours1';o.mkdir(parents=True,exist_ok=True)
 if (o/'data/public/episodes.jsonl').exists():raise RuntimeError('Refusing to overwrite generated dataset')
 public=[];oracle=[];pairs=[]
 for t in templates:
  for direction in [0,1]:
   old,new=t['values'][direction],t['values'][1-direction]
   for noise in [0,8,24]:
    pairids={};suffix=f'{t["template_id"]}_d{direction}_h{noise}'
    # Candidate IDs/order depend only on template: no condition, direction or target leaks.
    choices=[{'option_id':'opt_'+ident(t['template_id']+'|'+v)[:8],'value':v,'description':t['descriptions'][v]} for v in t['values']]
    if int(ident(t['template_id']),16)%2:choices.reverse()
    options={c['value']:c['option_id'] for c in choices}
    for cond in ['S','R','U0','U1']:
     cid='ep_'+ident(suffix+'_'+cond);slot=t['template_id'];history=[]
     for i,txt in enumerate(t.get('source_history',[])):history.append({'id':f'context_{i}','role':'user','text':'工作上下文记录（不是偏好声明）：'+txt,'timestamp':i})
     history.append({'id':'h_old','role':'user','text':f'对于{t["scenario"]}，我以往的默认交互偏好是：{old}。','timestamp':10})
     if cond=='R':history.append({'id':'h_update','role':'user','text':f'我已经更改默认偏好：对于{t["scenario"]}，从现在起按{new}；旧的{old}已不再有效。','timestamp':20})
     if cond.startswith('U'):history.append({'id':'h_ambiguous','role':'user','text':f'对于{t["scenario"]}，这次我需要重新确认我的偏好；请不要把以往默认直接用于这次。','timestamp':20})
     for k in range(noise):history.append({'id':f'distractor_{k}','role':'user','text':f'其他工作事项记录{k+1}：整理项目资料；这条记录不改变当前交互偏好。','timestamp':30+k})
     target=old if cond in ['S','U0'] else new;final=new if target==old else old
     evidence=['h_old'] if cond=='S' else ['h_update'] if cond=='R' else []
     request=t['context_text']+'\n任务背景：'+t['task']+'\n现在请在给定候选中选择本次交互方式。'
     pub={'episode_id':cid,'scenario':t['scenario'],'slot':slot,'candidates':choices,'history':history,'initial_request':request}
     gold={'episode_id':cid,'template_id':t['template_id'],'condition':cond,'variant':{'direction':direction,'distractors':noise,'wording':0},'phase_targets':[target,final,final],
      'phase_options':[options[target],options[final],options[final]],'initial_evidence_ids':evidence,
      'correction_message':f'请修改刚才的选择：对于{t["scenario"]}，从现在起默认按{final}。之前的默认已被替换，以后省略偏好时也按这个新默认。',
      'followup_request':'现在开始新会话。'+request+' 请再给出一个选择。','source':t['source'],'cluster_id':t['cluster_id']}
     public.append(pub);oracle.append(gold);pairids[cond]=cid
    for kind,conds in [('retained_vs_revised',['S','R']),('ambiguity_twins',['U0','U1'])]:pairs.append({'pair_id':suffix+'_'+kind,'template_id':t['template_id'],'kind':kind,'episode_ids':[pairids[c] for c in conds]})
 for rel,rows in [('data/public/episodes.jsonl',public),('data/private/oracle.jsonl',oracle)]:
  p=o/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows))
 save(o/'data/private/templates.json',templates);save(o/'data/private/pairs.json',pairs)
 # Pilot spans all source cells/events, with short history and one direction; complete pairs.
 pilot=[x['episode_id'] for x in oracle if x['variant']['direction']==0 and x['variant']['distractors']==0]
 discussion=[x['episode_id'] for x in oracle if x['template_id'] in [t['template_id'] for t in templates[:2]] and x['variant']['direction']==0 and x['variant']['distractors']==0]
 save(o/'data/private/subsets.json',{'discussion':discussion,'pilot':pilot,'full':[p['episode_id'] for p in public]})
 cfg=json.loads((R/'pi_bench_ours1/ours1/configs/experiment.json').read_text());cfg.update(status='source_adaptation_authorized',execution_enabled=True,full_execution_enabled=True,training_enabled=False);save(o/'configs/experiment.json',cfg)
 shutil.copy2(R/'pi_bench_ours1/ours1/configs/response.schema.json',o/'configs/response.schema.json')
 return {'templates':len(templates),'episodes':len(public),'pairs':len(pairs),'pilot':len(pilot),'discussion':len(discussion)}

def main():
 mem=sources_mempa();pro,n=sources_pro();result={}
 for name,templates in [('mempabench_ours1',mem),('proagentbench_ours1',pro)]:result[name]=generate(name,templates)
 result['proagent_source_events']=n;save(RT/'preparation.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
