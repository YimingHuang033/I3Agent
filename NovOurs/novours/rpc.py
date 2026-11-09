import json
import sys
from pathlib import Path
from .agents import Agent
from .core import Model, Journal, ROOT


def serve(config):
    journal=Journal(Path(config.get('journal',str(ROOT/'NovOurs/.local/rpc-trace.jsonl'))))
    agent=Agent(config['agent'],Model(config['actor'],journal,'actor'),journal)
    for line in sys.stdin:
        req=json.loads(line)
        try:
            p=req['params']
            if req['method']=='initialize':
                agent.begin(p['session_id'],p['context'],p['capabilities'],p.get('tools'));result={}
            elif req['method']=='act':
                # Incoming public full history is canonical (supports process restart).
                agent.history=p['history'][:-1]
                last=p['history'][-1]
                result=agent.act(last['content'],last['role'])
            elif req['method']=='finish': agent.end();result={}
            elif req['method']=='checkpoint':result={'history':agent.history,'state':agent.state,'questions':agent.questions}
            elif req['method']=='restore':
                checkpoint=p['checkpoint'];agent.history=checkpoint['history'];agent.state=checkpoint['state'];agent.questions=checkpoint.get('questions',0);result={}
            else: raise ValueError('unknown method')
            print(json.dumps({'id':req['id'],'result':result}),flush=True)
        except Exception as e:
            print(json.dumps({'id':req['id'],'error':type(e).__name__}),flush=True)
