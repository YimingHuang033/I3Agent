"""Agent boundary shared by native sources; all state derives from public events."""
from __future__ import annotations
import copy
import json
from .core import Model, RemoteAgent, PythonAgent, dump, validate_action


class Agent:
    def __init__(self, config, model, journal):
        self.config, self.model, self.journal = config, model, journal
        self.method = config.get('method','direct')
        self.history = []
        self.state = {}
        self.session = None
        self.questions = 0
        self.remote = RemoteAgent(config) if self.method in {'process','http'} else None
        if self.method=='python':self.remote=PythonAgent(config)

    def begin(self, session_id, public_context, capabilities=('ask','respond'), tools=None):
        self.session = session_id
        self.state['questions'] = 0
        self.capabilities = list(capabilities)
        self.tools = tools or []
        self.context = copy.deepcopy(public_context)
        self.history.append({'id':f'c{len(self.history)}','role':'system','content': 'New source session (public context evidence): ' + json.dumps(public_context, ensure_ascii=False)})
        if self.remote:
            self.remote.call('initialize', {'session_id':session_id,'context':public_context,'capabilities':self.capabilities,'tools':self.tools})

    def act(self, text, role='user'):
        self.history.append({'id':f'e{len(self.history)}','role':role,'content':text})
        public = {'context':self.context,'history':self.history,'capabilities':self.capabilities,'tools':self.tools}
        if self.remote:
            action = self.remote.call('act',public)
        else:
            if self.method == 'direct':
                prompt='You are a personal assistant. Use only the public conversation and offered tools. Return one action JSON with fields type, text, name (only for tools), arguments (only for tools), diagnostics.intent (estimated current intent). Allowed type values: '+', '.join(self.capabilities)+'.'
                request=public
                for attempt in range(2):
                    action=self.model.json(prompt,request)
                    try:
                        validate_action(action,self.capabilities)
                        if action['type']=='tool' and action['name'] not in {x['function']['name'] for x in self.tools}:raise ValueError('unoffered tool')
                        break
                    except ValueError as error:
                        if attempt:raise
                        request={**public,'invalid_action':action,'validation_error':str(error),'instruction':'Regenerate one action obeying the offered capabilities.'}
            else:
                from .methods import decide
                action, self.state = decide(self.method, self.model, public, self.state, self.config)
        validate_action(action,self.capabilities)
        if action['type']=='tool' and action['name'] not in {x['function']['name'] for x in self.tools}:
            raise ValueError('unoffered tool')
        if action['type']=='ask': self.questions+=1
        self.history.append({'role':'assistant','content':action.get('text',''),'action':action})
        self.journal.add('agent_action',session=self.session, action=action)
        return action

    def end(self, path=None):
        if self.remote and self.session is not None:
            self.remote.call('finish', {'session_id':self.session})
        if path:
            dump(path, {'history':self.history,'state':self.state,'questions':self.questions})

    def close(self):
        if self.remote: self.remote.close()
