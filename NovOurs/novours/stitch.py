"""STITCH adaptation: original density ranker, online labels, local dense retrieval.
The full upstream dspy/Qdrant pipeline remains available via external-agent RPC.
"""
import ast
import copy
import logging
import re
from pathlib import Path
from .core import ROOT


def upstream_ranker(path):
    source=Path(path).read_text()
    tree=ast.parse(source)
    function=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='rank_turns_by_representativeness')
    module=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),function],type_ignores=[])
    def index(s):
        m=re.search(r'(\d+)$',s)
        return int(m.group(1)) if m else None
    scope={'logger':logging.getLogger('stitch'),'_extract_turn_index_from_id':index}
    exec(compile(ast.fix_missing_locations(module),str(path),'exec'),scope)
    return scope['rank_turns_by_representativeness']


_EMBEDDER=None

def retrieve(model,public,state,config):
    global _EMBEDDER
    notes=state.setdefault('notes',{})
    for event in public['history']:
        eid=event.get('id')
        if not eid or eid in notes:continue
        note=model.json('Construct a contextual memory snippet from this observed event using prior labels for stable scopes and reference resolution. Return {"context_scope":"...","event_types":["..."],"target":"...","functional_type_seeds":["..."],"summary":"grounded event summary"}. Do not invent personal facts.',{'event':event,'prior_notes':notes})
        notes[eid]=dict(note,original=event)
    query=public['history'][-1]['content']
    labels=model.json('Select only relevant existing label values for the current request. Return {"scopes":[],"events":[],"targets":[],"functional_types":[]}.',{'query':query,'notes':notes})
    path=ROOT/'NovOurs/.local/upstream/stitch/method_stitch/label_based_context_retrieval.py'
    rank=upstream_ranker(path)
    ranked=rank(list(notes),notes,labels['scopes'],labels['events'],labels['targets'],labels['functional_types'])
    candidates=[k for k,_ in ranked[:config.get('label_cap',40)]] or list(notes)
    if _EMBEDDER is None:
        from sentence_transformers import SentenceTransformer
        _EMBEDDER=SentenceTransformer(str(ROOT/'models/Qwen3-Embedding-0.6B'),device='cpu')
    vectors=_EMBEDDER.encode([query]+[notes[k]['summary'] for k in candidates],normalize_embeddings=True)
    ordered=sorted(zip(candidates,(vectors[1:]@vectors[0]).tolist()),key=lambda x:x[1],reverse=True)
    selected=[k for k,_ in ordered[:config.get('retrieval_top_k',20)]]
    view=copy.deepcopy(public)
    view['retrieved_memories']=[notes[k] for k in selected]
    # Current event retained even when not among retrieved historical snippets.
    view['history']=[public['history'][-1]]
    model.journal.add('retrieval',selected=selected,labels=labels)
    return view,state
