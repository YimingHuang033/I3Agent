"""Source inventory: no invented rubrics or targets for incomplete releases."""
import json
import hashlib
from pathlib import Path
from .core import SOURCES, ROOT


def inventory():
    rows=[]
    for p in sorted((SOURCES/'Pi-Bench/data').glob('*/tasks/*/task.yaml')):
        rows.append({'source':'pi','id':p.parent.name,'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'status':'available','requirements':'native files/tools, simulator and original evaluator; AppWorld/web credentials where required'})
    for setting in ['single_session','long_horizon']:
        p=SOURCES/'lifesim/data'/setting/'events.jsonl'
        for row in map(json.loads,p.read_text().splitlines()):
            rows.append({'source':'lifesim','setting':setting,'id':row['id'],'status':'available'})
    data=ROOT/'benchmarks/data/MemPABench-personas'
    for p in sorted(data.glob('user_*')):
        rows.append({'source':'mempa','id':p.name,'status':'available','requirements':'native timeline plus checkpointed probes; full scoring requires 33 probes'})
    pro=SOURCES/'ProAgentBench'
    evaluator_files=list(pro.glob('**/*eval*.py'))
    has_screenshots=bool(list(pro.glob('**/screenshots/*.png')))
    for p in sorted(pro.glob('志愿者*.json')):
        try: d=json.loads(p.read_text())
        except json.JSONDecodeError:
            rows.append({'source':'proagent','unit':'file','id':p.stem,'status':'skipped','reasons':['unresolved_lfs_or_invalid_source_json'],'path':str(p.relative_to(ROOT))})
            continue
        for e in d['events']:
            reasons=[]
            if not evaluator_files: reasons.append('original_evaluator_not_in_release')
            # These texts are model generated; is_llm_event is not a scored help target.
            if not any(k in e for k in ['ground_truth','rubric','target_label']): reasons.append('no_original_scoring_target')
            if not has_screenshots: reasons.append('screenshots_not_in_checkout')
            rows.append({'source':'proagent','unit':'event','id':e['event_id'],'participant':d['metadata']['participant_id'],'status':'skipped' if reasons else 'requires_original_evaluator_review','reasons':reasons,'path':str(p.relative_to(ROOT))})
    summary={s:{status:sum(r['source']==s and r['status']==status for r in rows) for status in sorted({r['status'] for r in rows if r['source']==s})} for s in ['pi','lifesim','mempa','proagent']}
    summary['proagent']['skipped_event_records']=sum(r['source']=='proagent' and r.get('unit')=='event' for r in rows)
    summary['proagent']['unresolved_source_files']=sum(r['source']=='proagent' and r.get('unit')=='file' for r in rows)
    return {'summary':summary,'units':{'pi':'task','lifesim':'event sequence','mempa':'persona','proagent':'mixed; see event and file counts separately'},'entries':rows}
