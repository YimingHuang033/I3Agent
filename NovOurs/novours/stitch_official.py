"""Original STITCH pipeline on observed history, using its file-backed retrieval.
Only provider configs and downstream execution/evaluation are replaced.
"""
import copy
import json
import os
import subprocess
from pathlib import Path
from .core import ROOT,dump,digest
from .gateway import Gateway


def retrieve(model,public,state,config):
    upstream=ROOT/'NovOurs/.local/upstream/stitch'
    python=ROOT/'NovOurs/.local/stitch-venv/bin/python'
    if not python.exists():raise RuntimeError('Install pinned STITCH requirements in NovOurs/.local/stitch-venv')
    out=model.journal.path.parent/'stitch_official'/digest(public['history'])[:16]
    out.mkdir(parents=True,exist_ok=True)
    (out/'notes').mkdir(exist_ok=True)
    from sentence_transformers import SentenceTransformer
    encoder=SentenceTransformer(str(ROOT/'models/Qwen3-Embedding-0.6B'),device='cpu')
    turns=[{'id':f'conv-1_turn_{i+1}','role':'agent' if e['role']=='assistant' else e['role'],'content':e['content'],'partition':['conv-1']} for i,e in enumerate(public['history'])]
    (out/'turns.jsonl').write_text('\n'.join(json.dumps(t,ensure_ascii=False) for t in turns)+'\n')
    # No hidden answer, evidence label or future turn is supplied to retrieval.
    (out/'questions.jsonl').write_text(json.dumps({'id':'conv-1_question_1','content':turns[-1]['content'],'type':'FREE_FORM','answer_type':'ANSWER_TYPE_FREEFORM','question_turn_ids':[t['id'] for t in turns]})+'\n')
    with Gateway({model.config['model']:(model.config,'actor_stitch')},model.journal,embed=lambda texts:encoder.encode(texts,normalize_embeddings=True)) as gateway:
        lm={'provider':'LANGUAGE_MODEL_PROVIDER_OPENAI','model_name':'openai/'+model.config['model'],'temperature':0,'max_tokens':model.config.get('max_tokens',4096),'openai_config':{'api_key':'LOCAL_GATEWAY','api_base':gateway.url}}
        emb={'provider':'EMBEDDING_MODEL_PROVIDER_OPENAI','model_name':'text-embedding-3-small','max_concurrent':1,'openai_config':{'api_key':'LOCAL_GATEWAY','api_base':gateway.url}}
        def transform(x):
            if isinstance(x,dict):
                return {k:copy.deepcopy(lm) if 'language_model_provider_config' in k else copy.deepcopy(emb) if k in {'encoder_config','query_embedding_model_provider_config'} else transform(v) for k,v in x.items() if k!='qdrant_config_turn_collection'}
            if isinstance(x,list):return [transform(v) for v in x]
            if isinstance(x,str) and x.startswith('path/to/'):
                return str(out/('notes' if Path(x).name=='structured_turn_notes.jsonl' else '')/Path(x).name)
            return x
        names=['dataset_description','segment_level_note_maintainer','event_type_labeler','turn_level_note_generator','label_based_context_retrieval']
        for name in names:
            data=transform(json.loads((upstream/'sample_config_files'/f'{name}_config.json').read_text()))
            if name=='dataset_description':data['dataset_description_config'].update(dataset_type='observed personal assistant conversation',sample_rate=1.0)
            if name=='event_type_labeler':data['event_type_labeler_config']['max_workers']=1
            dump(out/(name+'.json'),data)
        commands=[['-c','from came_bench.proto import LanguageModelProviderConfig'],['-m','method_stitch.dataset_description','-c',str(out/'dataset_description.json')],['-m','method_stitch.turn_scope_generator','--config',str(out/'segment_level_note_maintainer.json'),'--overwrite'],['-m','method_stitch.segment_note_generator','--config',str(out/'segment_level_note_maintainer.json'),'--output',str(out/'segment_level_notes.jsonl'),'--overwrite'],['-m','method_stitch.event_type_labeler','-c',str(out/'event_type_labeler.json'),'--overwrite'],['-m','method_stitch.turn_level_note_generator','-c',str(out/'turn_level_note_generator.json'),'--overwrite'],['-m','method_stitch.label_based_context_retrieval','--config',str(out/'label_based_context_retrieval.json'),'--overwrite']]
        with (out/'pipeline.log').open('w') as log:
            for command in commands:
                log.write('COMMAND '+json.dumps(command)+'\n');log.flush()
                if command[0]=='-m':
                    # Upstream CLIs still call load_turns(dataset, path), while
                    # this pinned release's universal reader takes only path.
                    # Bridge the obsolete argument, without changing algorithms.
                    shim="import sys,importlib.util; from pathlib import Path; import came_bench.utils.io as io; original=io.load_turns; io.load_turns=lambda *args: original(args[-1]); module=sys.argv.pop(1); __spec__=importlib.util.find_spec(module); __package__=module.rpartition('.')[0]; __file__=__spec__.origin; source=Path(__file__).read_text().replace('from __future__ import annotations',''); exec(compile(source,__file__,'exec'),globals())"
                    command=['-c',shim]+command[1:]
                subprocess.run([str(python)]+command,cwd=upstream,env={**os.environ,'PYTHONPATH':str(upstream),'DSPY_CACHEDIR':str(out/'dspy_cache')},stdout=log,stderr=subprocess.STDOUT,timeout=config.get('pipeline_timeout',600),check=True)
    result=json.loads((out/'label_based_retrieval.json').read_text())
    questions=result.get('question_results',[])
    if len(questions)!=1:raise RuntimeError('Original STITCH did not produce the requested retrieval result')
    result=questions[0]
    view=copy.deepcopy(public);view['history']=[public['history'][-1]]
    view['retrieved_memories']=result['node_selected_turn_details']
    view['semantic_candidates']=result['embedding_candidate_turn_details']
    model.journal.add('official_stitch',artifacts=str(out),result=result)
    return view,state
