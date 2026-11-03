"""Generate synthetic preparation data only. No model calls or experiments."""
from pathlib import Path
import argparse,hashlib,json
from templates import PI,LIFE
parser=argparse.ArgumentParser()
parser.add_argument('--benchmark',choices=['pi_bench_ours1','lifesim_ours1'],required=True)
parser.add_argument('--output',type=Path,default=Path('generated-ours1'))
args=parser.parse_args()
destination=args.output.resolve()
if destination.exists():
    raise SystemExit('Refusing to overwrite existing output: '+str(destination))
destination.mkdir(parents=True)
distractors=['我整理了今天的本地文件，编号为 {i}。','今天的讨论已做笔记，待办编号为 {i}。','我稍后会查看材料，提醒编号为 {i}。','附件已经放在本地，记录编号为 {i}。','今天没有新增任务要求，记录编号为 {i}。','这条只是进度记录，不改变任何默认偏好，编号为 {i}。']
for name,specs in [(args.benchmark, PI if args.benchmark == 'pi_bench_ours1' else LIFE)]:
 r=destination
 for sub in ['data/public','data/private']:(r/sub).mkdir(parents=True,exist_ok=True)
 public=[];gold=[];pairs=[];subsets={'discussion':[],'pilot':[],'full':[]};template_meta=[]
 for ti,(slot,title,a,b,asset,goal,domain) in enumerate(specs):
  template_meta.append({'template_id':slot,'domain':domain,'scenario':title,'values':[a,b],'synthetic_asset_description':asset,'goal':goal,'review_status':'generated_draft_not_human_validated','split':'heldout' if ti%4==3 else 'development'})
  for direction in [0,1]:
   old,new=([a,b] if direction==0 else [b,a])
   options=[{'option_id':'opt_'+hashlib.sha256((slot+v).encode()).hexdigest()[:8],'value':v,'description':f'合成候选方案：按“{v}”处理。候选的其他条件均满足请求；不作真实外部操作。'} for v in [a,b]]
   if ti%2:options.reverse()
   oid={o['value']:o['option_id'] for o in options}
   for noise in [0,8,24]:
    for wording in [0,1,2]:
     requests=[f'给定{asset}。请{goal}。',f'这次处理{title}：材料是{asset}，请帮我{goal}。',f'我已准备好{asset}。现在需要你{goal}，其他条件按给定候选。']
     request=requests[wording]
     old_texts=[f'关于{title}，从现在起默认按{old}处理，以后我不重说时也照此办理。',f'请记住我的长期默认：{title}采用{old}，后续省略这个要求也沿用。',f'{title}这方面，我固定偏好{old}。没有新说明时就按它来。']
     updates=[f'更新一下：{title}从现在起默认改成{new}，之前的{old}已经不适用。',f'我的{title}偏好已修改：今后使用{new}，替换之前的{old}，不是仅这一次。',f'请把{title}的长期默认更新为{new}；旧的{old}偏好已取消。']
     stables=['补充一下：我稍后再看结果，输出保持简短即可。','另外，材料都在本地，等你整理完我再看。','顺便记录一下进度：我已经把所需附件准备好了。']
     unknowns=[f'关于{title}，我的安排可能变了，旧默认暂时不要当成已确认的安排。具体值我还没说明。',f'{title}的旧偏好现在需要确认；我尚未告诉你这次用哪一个。',f'先别认定{title}仍沿用旧默认，我的新安排还没说明清楚。']
     combo=f'{slot}_d{direction}_h{noise}_w{wording}';ids={}
     for arm in ['S','R','U0','U1']:
      cid='ep_'+hashlib.sha256((name+combo+arm).encode()).hexdigest()[:16];ids[arm]=cid
      history=[{'id':'h01','timestamp':1,'role':'user','text':old_texts[wording]},
       {'id':'h02','timestamp':2,'role':'user','text':'请选择给定的合成候选，不要执行真实外部操作。'},
       {'id':'h03','timestamp':3,'role':'user','text':updates[wording] if arm=='R' else unknowns[wording] if arm.startswith('U') else stables[wording]}]
      history += [{'id':f'n{i:02d}','timestamp':4+i,'role':'user','text':distractors[i%len(distractors)].format(i=i+1)} for i in range(noise)]
      initial=new if arm in ['R','U1'] else old;final=old if initial==new else new
      public.append({'schema_version':'ours1.v1','episode_id':cid,'scenario':title,'slot':slot,'candidates':options,'history':history,'initial_request':request})
      gold.append({'schema_version':'ours1.v1','episode_id':cid,'template_id':slot,'condition':arm,'domain':domain,
       'variant':{'direction':direction,'distractors':noise,'wording':wording},'split':'heldout' if ti%4==3 else 'development',
       'source_inspiration':domain+' 场景的合成偏好选择；不是原版任务或官方指标',
       'initial_target_value':initial,'corrected_target_value':final,'initial_option_id':oid[initial],'corrected_option_id':oid[final],
       'initial_evidence_ids':['h03'] if arm=='R' else ['h01'] if arm=='S' else [],'initial_ambiguous':arm.startswith('U'),
       'clarification_initial':f'这次请按{initial}处理。',
       'correction_message':f'请修改刚才的选择：关于{title}，从现在起默认按{final}。之前的默认已被替换，后续不重说时也按这个新默认。',
       'followup_request':f'现在开始一个新会话。{request} 请再给我一个选择。','phase_targets':[initial,final,final],'phase_options':[oid[initial],oid[final],oid[final]]})
      subsets['full'].append(cid)
      if direction==0 and noise==0 and wording==0:
       subsets['pilot'].append(cid)
       if ti in [0,8,16,24]:subsets['discussion'].append(cid)
     pairs += [{'pair_id':combo+'_SR','template_id':slot,'kind':'retained_vs_revised','episode_ids':[ids['S'],ids['R']]},
               {'pair_id':combo+'_U','template_id':slot,'kind':'ambiguity_twins','episode_ids':[ids['U0'],ids['U1']]}]
 for path,data in [('data/public/episodes.jsonl',public),('data/private/oracle.jsonl',gold)]:
  (r/path).write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in data))
 for path,data in [('data/private/pairs.json',pairs),('data/private/templates.json',template_meta),('data/private/subsets.json',subsets)]:
  (r/path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

print(json.dumps({'benchmark':args.benchmark,'output':str(destination),'episodes':len(public),'pairs':len(pairs),'model_calls':0},ensure_ascii=False))
