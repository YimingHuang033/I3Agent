"""Training-free adaptations; exact provenance and deviations in docs/methods.md.
Planning predictions are never written as observed user facts.
"""
from __future__ import annotations
import copy
import math
from .core import validate_action

ACTION = 'An action is {"type":"ask|respond|tool|wait", "text":"user-facing text", "name":"tool name if type=tool", "arguments":{}, "diagnostics":{"intent":"estimated intent"}}. Use only offered capabilities and tool schemas.'


def distribution(values):
    xs=[float(x) for x in values]
    if not xs or any(not math.isfinite(x) or x<0 for x in xs) or sum(xs)<=0:
        raise ValueError('invalid probability distribution')
    return [x/sum(xs) for x in xs]


def expected(utilities,weights):
    if len(utilities)!=len(weights): raise ValueError('utility/belief size mismatch')
    xs=[float(x) for x in utilities]
    if any(not math.isfinite(x) or x<0 or x>1 for x in xs): raise ValueError('utility outside [0,1]')
    return sum(x*w for x,w in zip(xs,weights))


def prune_dependencies(items):
    """A revoked premise invalidates derived conclusions transitively."""
    items=copy.deepcopy(items)
    ids={x['id'] for x in items}
    if len(ids)!=len(items): raise ValueError('duplicate state item id')
    changed=True
    while changed:
        active={x['id'] for x in items if x.get('active',True)}
        changed=False
        for x in items:
            if x.get('active',True) and any(d not in active for d in x.get('depends_on',[])):
                x['active']=False;changed=True
    return items


def fold(model,public,state,applicability=False,ablate=()):
    prompt=('Track evidence-grounded alternative applicability explanations: persistent default, one-off exception, scoped rule, revocation, other context, or unknown. Preserve competing supported interpretations rather than treating latest text as universally binding. ' if applicability else 'Fold the observed conversation into the single currently active intent state. Replace/revoke obsolete items; distinguish explicit requirements from derived conclusions. ')
    prompt+='Return {"items":[{"id":"stable ID","text":"...","active":true,"source_ids":["e1"],"scope":"...","revision_of":[],"depends_on":[]}],"interpretations":[{"text":"...","source_ids":["e1"],"scope":"...","revision":"..."}]}. Only cite observed event IDs, never hypothetical replies.'
    visible={x.get('id') for x in public['history'] if x.get('id')}
    request={'public':public,'previous':state.get('representation',{}),'allowed_source_ids':sorted(visible)}
    for attempt in range(2):
        result=model.json(prompt,request)
        invalid=[x for x in result.get('items',[])+result.get('interpretations',[]) if not x.get('source_ids') or not set(x['source_ids'])<=visible]
        if not invalid:break
        if attempt:raise ValueError('ungrounded state evidence after one repair')
        request={**request,'invalid_items':invalid,'instruction':'Regenerate grounded state. Cite ONLY allowed_source_ids; omit unsupported items instead of inventing sources.'}
    for x in result.get('items',[])+result.get('interpretations',[]):
        for key in ablate:x.pop(key,None)
    result['items']=prune_dependencies(result.get('items',[]))
    if not applicability: result.pop('interpretations',None)
    return result


def propose_actions(model,public,belief,config):
    k=config.get('actions',2)
    action_view=copy.deepcopy(public)
    action_view['capabilities']=[c for c in public['capabilities'] if c!='ask']
    schema=ACTION.replace('ask|respond|tool|wait','|'.join(action_view['capabilities']))
    prompt=f'Propose {k} distinct concrete candidate assistance actions, including safe compromises where useful. Do not ask here. Return {{"actions":[action,...]}}. '+schema
    request={'public':action_view,'belief':belief}
    for attempt in range(2):
        result=model.json(prompt,request)
        try:
            actions=result['actions'][:k]
            if not actions: raise ValueError('no candidate actions')
            for a in actions:
                validate_action(a,action_view['capabilities'])
                if a['type']=='tool' and a['name'] not in {t.get('function',t).get('name') for t in public.get('tools',[])}:
                    raise ValueError('unoffered candidate tool')
            return actions
        except (ValueError,KeyError,TypeError) as error:
            if attempt: raise
            request={**request,'invalid_candidates':result,'validation_error':str(error),'instruction':'Regenerate candidates obeying the offered action types and tools exactly.'}


def reward(model,public,belief,action):
    result=model.json('Estimate internal goal satisfaction of this action for each hypothetical intent, [0,1]. These are planning estimates, NOT benchmark scores. Consider public tools/state; do not claim execution occurred. Return {"utilities":[number per hypothesis]}.',{'public':public,'hypotheses':belief,'action':action})
    return expected(result['utilities'],[b['weight'] for b in belief]),result['utilities']


def best_action(model,public,belief,config):
    candidates=propose_actions(model,public,belief,config)
    scored=[]
    for a in candidates:
        value,u=reward(model,public,belief,a)
        scored.append((value-config.get('action_cost',0),a,u))
    return max(scored,key=lambda x:x[0]),scored


def beliefs(model,public,previous,config):
    n=config.get('hypotheses',3)
    proposed=model.json(f'Propose at most {n} distinct plausible natural-language user intent hypotheses. Retain/refine/drop old hypotheses using observed conversation. Return {{"hypotheses":[{{"text":"..."}}]}}.',{'public':public,'previous':previous})['hypotheses'][:n]
    if not proposed: raise ValueError('no hypotheses')
    scores=model.json('Rate consistency of each hypothesis against OBSERVED evidence on [0,10]. Return {"scores":[number per hypothesis]}.',{'public':public,'hypotheses':proposed})['scores']
    if len(scores)!=len(proposed) or any(not 0<=float(x)<=10 for x in scores): raise ValueError('invalid belief scores')
    weights=distribution([math.exp(float(x)-max(scores)) for x in scores])
    return [dict(h,weight=w) for h,w in zip(proposed,weights)]


def hypothetical(public,action,reply):
    new=copy.deepcopy(public)
    new['history'] += [{'role':'assistant','content':action.get('text',''),'action':action},{'role':'user','content':reply,'hypothetical':True}]
    return new


def lookahead(model,public,belief,action,config,correction=False):
    total=0.;branches=[]
    for h in belief:
        forecast=model.json('Predict user feedback under this HYPOTHETICAL intent using public context only. Return {"reply":"...","terminate":false}. '+('The user may accept/end or correct this assistance. ' if correction else 'Answer the clarification; do not terminate.'),{'public':public,'hypothetical_intent':h['text'],'action':action})
        if correction and forecast.get('terminate'):
            value=0.
        else:
            future=hypothetical(public,action,forecast['reply'])
            posterior=beliefs(model,future,belief,config)
            (value,_,_),_=best_action(model,future,posterior,config)
        cost=config.get('correction_cost',0.05) if correction and not forecast.get('terminate') else 0.
        total+=h['weight']*(value-cost)
        branches.append({'hypothesis':h['text'],'forecast':forecast,'future_value':value,'cost':cost})
    return total,branches


def decide(method,model,public,state,config):
    state=copy.deepcopy(state)
    if method=='in3':
        from .in3 import decide as inquiry
        return inquiry(model,public,state,config)
    if method=='capture':
        raise RuntimeError(method+' requires original trained components; no prompt substitute is provided')
    allowed={'stateforge','voi','revoir','stateforge_revoir','stitch','stitch_revoir','stitch_official','stitch_official_revoir','p1','p2','p3'}
    if method not in allowed: raise ValueError('unknown method: '+method)
    view=copy.deepcopy(public)
    if method in {'stateforge','stateforge_revoir','p1','p3'}:
        representation=fold(model,public,state,method in {'p1','p3'},config.get('ablate',[]))
        state['representation']=representation
        view['active_state']=representation
    if method in {'stitch','stitch_revoir'}:
        from .stitch import retrieve
        view,state=retrieve(model,view,state,config)
    if method in {'stitch_official','stitch_official_revoir'}:
        from .stitch_official import retrieve
        view,state=retrieve(model,view,state,config)
    if method in {'stateforge','stitch','stitch_official'}:
        action=model.json('Execute the current request using relevant valid information. Return one action. '+ACTION,view)
        if method=='stateforge':
            formats=model.json('Track currently required output format using only actual conversation. Return {"constraints":["..."]}.',public)
            check=model.json('Check this action text against requested output conventions. Return {"valid":true,"issues":[]}.',{'format':formats,'action':action})
            if not check['valid']:
                action=model.json('Regenerate one action to satisfy the specified output conventions. '+ACTION,{'public':view,'action':action,'format':formats,'issues':check['issues']})
                final=model.json('Check format. Return {"valid":true}.',{'format':formats,'action':action})
                if not final['valid']: raise ValueError('format gate failed after regeneration')
            state['format']=formats
        return action,state
    belief=beliefs(model,view,state.get('belief',[]),config)
    state['belief']=belief
    (act_value,action,utilities),all_actions=best_action(model,view,belief,config)
    use_revoir=method!='voi'
    correction_allowed=public.get('context',{}).get('user_can_correct',False)
    action_branches=[]
    if use_revoir and correction_allowed:
        future,action_branches=lookahead(model,view,belief,action,config,correction=True)
        act_value+=future
    ask_value=-math.inf;question=None;ask_branches=[]
    if 'ask' in public['capabilities'] and state.get('questions',0)<config.get('max_questions',4):
        focus='Generate questions about scope/revision boundaries distinguishing the supported explanations (one-off versus persistent, which context, withdrawal versus exception).' if method in {'p2','p3'} else 'Generate questions about missing goal attributes that can change the action.'
        qs=model.json(f'{focus} Return {{"questions":["question text"]}} with at most {config.get("questions",2)} concise questions.',{'public':view,'belief':belief})['questions'][:config.get('questions',2)]
        for q in qs:
            qa={'type':'ask','text':q}
            future,branches=lookahead(model,view,belief,qa,config)
            value=future-config.get('question_cost',0.1)
            if value>ask_value: ask_value,question,ask_branches=value,qa,branches
    # Common-acceptable action is an agent estimate. Never query hidden rewards.
    if method in {'p1','p3'} and state.get('representation',{}).get('interpretations'):
        interpretations=state['representation']['interpretations']
        common=[]
        ib=[{'text':x['text'],'weight':1/len(interpretations)} for x in interpretations]
        for _,candidate,_ in all_actions:
            _,u=reward(model,view,ib,candidate)
            if min(u)>=config.get('acceptable_threshold',0.8): common.append(candidate)
        if common:
            action=common[0];ask_value=-math.inf
    selected=question if ask_value>act_value else action
    if selected['type']=='ask':state['questions']=state.get('questions',0)+1
    state['last_decision']={'act_value':act_value,'ask_value':ask_value if math.isfinite(ask_value) else None,'action_branches':action_branches,'ask_branches':ask_branches,'selected':selected}
    # Only actual evidence-derived representation/belief is carried to next turn.
    model.journal.add('planning',method=method,decision=state['last_decision'],representation=state.get('representation'))
    state.pop('last_decision')
    return selected,state
