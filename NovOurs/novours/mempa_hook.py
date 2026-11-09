"""Checkpoint-aware method/remote controller inside the native MemPA tool executor.
Session metadata is cloned by upstream checkpoints, so probes do not mutate the
mainline controller state. Native IX enforcement and all world tools stay intact.
"""
import asyncio
import copy
import json
import uuid
from novours.agents import Agent
from novours.core import Model,Journal,digest


def install(config,journal_path):
    if config['agent']['method'] in {'process','http','python'} and not config['agent'].get('checkpoint_protocol'):
        raise ValueError('MemPA external harness requires checkpoint_protocol=true and checkpoint/restore RPC to isolate probes')
    from pa.agent.loop import AgentLoop
    from pa.providers.base import LLMProvider,LLMResponse,ToolCallRequest
    original=AgentLoop._run_agent_loop
    journal=Journal(journal_path)
    async def wrapped(self,initial_messages,*args,**kwargs):
        session=self.sessions.get(kwargs['session_key'])
        state=copy.deepcopy(session.metadata.get('novours',{}))
        agent=Agent(config['agent'],Model(config['actor'],journal,'actor'),journal)
        agent.state=state.get('state',{})
        agent.history=state.get('history',[])
        agent.begin(kwargs.get('script_session_id') or 'session',{'source':'mempa','user_can_correct':True,'evidence_note':'Original public session messages are provided in context.native_messages on act; this context event is their source reference.'},['ask','respond','tool'])
        context_evidence_id=agent.history[-1]['id']
        if agent.remote and state.get('remote_checkpoint') is not None:
            agent.remote.call('restore',{'checkpoint':state['remote_checkpoint']})
        class Provider(LLMProvider):
            def get_default_model(self):return config['actor']['model']
            async def chat(self,messages,tools=None,**kw):
                agent.tools=tools or []
                # Original public system/memory/tool context, never simulator private U/G.
                agent.context={'source':'mempa','user_can_correct':True,'evidence_id':context_evidence_id,'native_messages':messages,'required_tool_choice':kw.get('tool_choice')}
                last=messages[-1]
                action=await asyncio.to_thread(agent.act,last.get('content') or '',last['role'])
                if action['type']=='tool':
                    return LLMResponse(content=None,tool_calls=[ToolCallRequest(id='call_'+uuid.uuid4().hex[:12],name=action['name'],arguments=action['arguments'])])
                return LLMResponse(content=action['text'])
        previous=self.runner.provider
        self.runner.provider=Provider()
        try:
            result=await original(self,initial_messages,*args,**kwargs)
            session.metadata['novours']={'state':agent.state,'history':agent.history}
            if agent.remote:
                session.metadata['novours']['remote_checkpoint']=agent.remote.call('checkpoint',{})
            self.sessions.save(session)
            agent.end()
            return result
        finally:
            self.runner.provider=previous;agent.close()
    AgentLoop._run_agent_loop=wrapped
