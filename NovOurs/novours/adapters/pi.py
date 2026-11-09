"""Native Pi user lifecycle, NanoBot tools and original evaluators."""
from __future__ import annotations
import asyncio
import dataclasses
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from novours.core import SOURCES, Model, dump
from novours.agents import Agent


def load_native():
    root=SOURCES/'Pi-Bench'
    sys.path[:0]=[str(root),str(root/'third_party/nanobot')]
    return root


def llm(config,journal,role):
    from src.llm import LLMClient
    class LoggedClient(LLMClient):
        def _post_json(self,url,payload,headers):
            import time
            start=time.monotonic()
            try:
                response=super()._post_json(url,payload,headers)
                journal.add('model_call',role=role,request=payload,response=response,elapsed=time.monotonic()-start)
                return response
            except Exception as error:
                journal.add('model_error',role=role,error=type(error).__name__,elapsed=time.monotonic()-start)
                raise
    return LoggedClient(model=config['model'],base_url=config['base_url'],api_key=os.environ.get(config.get('key_env',''),config.get('local_key','EMPTY')),temperature=config.get('temperature',0),max_retries=2,request_timeout=180,extra_kwargs={'max_tokens':config.get('max_tokens',4096),**config.get('extra_body',{})})


def run(config,out,journal):
    return asyncio.run(arun(config,out,journal))


async def arun(config,out,journal):
    root=load_native()
    os.chdir(root)
    from src.channels.base import BaseChannel
    from src.user_agent.user_agent import UserAgent
    from src.data import UserDataRepository
    from src.runner.runner import BenchmarkRunner
    from nanobot.agent.loop import AgentLoop
    from nanobot.agent.hooks import JsonStorageHook,TurnRecord,ToolStep,LLMStep
    from nanobot.bus.queue import MessageBus
    from nanobot.bus.events import InboundMessage
    from nanobot.providers.base import LLMProvider,LLMResponse,ToolCallRequest
    actor=Model(config['actor'],journal,'actor')
    class Provider(LLMProvider):
        def get_default_model(self): return config['actor']['model']
        async def chat(self,messages,tools=None,**kwargs):
            data=await asyncio.to_thread(actor.request,messages,tools)
            c=data['choices'][0];m=c['message']
            return LLMResponse(content=m.get('content'),tool_calls=[ToolCallRequest(id=t['id'],name=t['function']['name'],arguments=json.loads(t['function']['arguments'])) for t in m.get('tool_calls',[])],usage=data.get('usage',{}),finish_reason=c.get('finish_reason','stop'),reasoning_content=m.get('reasoning_content'))
    workspace=out/'workspace';workspace.mkdir(exist_ok=True)
    hook=JsonStorageHook(out/'native_traces',filename_pattern='turn_{timestamp}_{session_key}.json')
    executor=AgentLoop(MessageBus(),Provider(),workspace,model=config['actor']['model'],max_iterations=config.get('tool_iterations',20),max_tokens=config['actor'].get('max_tokens',4096),restrict_to_workspace=True,brave_api_key=os.environ.get('BRAVE_SEARCH_API_KEY'),hooks=[hook],mcp_servers=config.get('mcp_servers',{}))
    agent=Agent(config['agent'],actor,journal)
    session_started_at=datetime.now().strftime('%Y%m%d_%H%M%S')
    class Channel(BaseChannel):
        def set_runtime_identity(self,*,sender_id,chat_id): self.sender,self.chat=sender_id,chat_id
        async def connect(self): pass
        async def disconnect(self):
            try:
                await executor.close_mcp()
                if config['agent']['method']!='native':agent.end(out/'agent_state.json')
            finally:agent.close()
        async def reset(self):
            nonlocal agent
            self.flush()
            if config['agent']['method']=='native':
                await executor._process_message(InboundMessage(channel='novours',sender_id=self.sender,chat_id=self.chat,content='/new'),session_key='novours:'+self.sender)
            else:
                agent.end()
                agent.close()
                agent=Agent(config['agent'],actor,journal)
                agent.begin(self.chat,{'workspace':str(workspace),'user_can_correct':True},['ask','respond','tool'],executor.tools.get_definitions())
        async def send(self,message):
            if config['agent']['method']=='native':
                result=await executor._process_message(InboundMessage(channel='novours',sender_id=self.sender,chat_id=self.chat,content=message),session_key='novours:'+self.sender)
                reply=result.content if result else ''
            else:
                await executor._connect_mcp()
                agent.tools=executor.tools.get_definitions()
                if agent.session!=self.chat:
                    agent.begin(self.chat,{'workspace':str(workspace),'user_can_correct':True},['ask','respond','tool'],executor.tools.get_definitions())
                record=TurnRecord(session_key='novours:'+self.sender,channel='novours',chat_id=self.chat,input=message,sender_id=self.sender,model=config['actor']['model'],session_started_at=session_started_at)
                text=message;role='user'
                for iteration in range(config.get('tool_iterations',20)):
                    a=await asyncio.to_thread(agent.act,text,role)
                    record.iterations+=1
                    if a['type']!='tool':
                        reply=a['text'];break
                    result=await executor.tools.execute(a['name'],a['arguments'])
                    text=str(result);role='tool'
                    record.tool_steps.append(ToolStep(a['name'],a['arguments'],text))
                    record.tools_used.append(a['name'])
                else: raise RuntimeError('tool iteration budget exhausted')
                record.output=reply
                record.messages=[{'role':x['role'],'content':x['content']} for x in agent.history]
                await hook.on_turn_end(record)
            journal.add('source_reply',source='pi',task=self.chat,text=reply)
            await self._recv(reply)
    user_id=config.get('user_id','researcher')
    user=UserAgent(user_root=str(root/'data'/user_id),repository=UserDataRepository(str(root/'data'),root),llm_client=llm(config['user'],journal,'user'),task_ids=config.get('task_ids'),model_id=config['actor']['model'],output_root=str(out/'native_outputs'),workspace_dir=workspace,history_config_path=root/'config/bench/evaluation/trace_history.yaml',intent_parse_retries=2)
    channel=Channel({})
    async with channel:
        result=await BenchmarkRunner(channel,user,max_turns=config.get('max_turns',30),turn_timeout=config.get('turn_timeout',600)).run()
    dump(out/'native_run.json',dataclasses.asdict(result))
    if any(t.status in {'ERROR','TIMEOUT'} for t in result.tasks): raise RuntimeError('native Pi task failed')
    return await aevaluate(config,out,journal)


def evaluate(config,out,journal): return asyncio.run(aevaluate(config,out,journal))


async def aevaluate(config,out,journal):
    root=load_native()
    from src.evaluation.runner import TraceEvaluationRunner
    result=await TraceEvaluationRunner(model_id=config['actor']['model'],user_id=config.get('user_id','researcher'),logs_dir=out/'native_traces',workspace_dir=out/'workspace',config_path=root/'config/bench/evaluation/trace_history.yaml',output_dir=out/'native_outputs',scoring='both',llm_client=llm(config['judge'],journal,'judge'),task_ids=config.get('task_ids'),data_root=root/'data').run()
    result=dataclasses.asdict(result)
    result['task_results']=[json.loads(Path(p).read_text()) for p in result['score_paths']]
    dump(out/'scores.json',result)
    return result
