"""Mistral-Interact inquiry -> summary -> executor bridge (pretrained system arm)."""
import ast
from .core import ROOT,Model
from .methods import ACTION


def decide(model,public,state,config):
    inquiry=config.get('inquiry')
    if not inquiry or inquiry.get('checkpoint')!='hbx/Mistral-Interact':
        raise RuntimeError('IN3 requires an endpoint serving the original hbx/Mistral-Interact checkpoint; set agent.inquiry config')
    path=ROOT/'NovOurs/.local/upstream/in3/src/test_one.py'
    module=ast.parse(path.read_text())
    prompt=next(ast.literal_eval(n.value) for n in module.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SYS_PROMPT' for t in n.targets))
    client=Model(inquiry,model.journal,'inquiry_pretrained')
    messages=[{'role':'system','content':prompt}]+[{'role':e['role'] if e['role'] in {'user','assistant','system'} else 'user','content':e['content']} for e in public['history']]
    reply=client.chat(messages)
    if '[SUMMARY]' in reply:
        summary=reply.split('[SUMMARY]',1)[1].strip()
        state['inquiry_summary']=summary
        return model.json('Execute the user request using this elicited summary and actual public context. '+ACTION,{'public':public,'summary':summary}),state
    if '[INQUIRY]' not in reply:raise ValueError('Mistral-Interact response lacks INQUIRY/SUMMARY marker')
    if state.get('questions',0)>=4:raise RuntimeError('Mistral-Interact inquiry budget exceeded without summary')
    state['questions']=state.get('questions',0)+1
    return {'type':'ask','text':reply.split('[INQUIRY]',1)[1].strip()},state
