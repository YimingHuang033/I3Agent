import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from novours.core import validate_action, RemoteAgent, Journal
from novours.methods import distribution, expected, prune_dependencies, fold, hypothetical
from novours.agents import Agent
from novours.core import PythonAgent, SOURCES
from novours.methods import propose_actions
from novours.adapters.lifesim import AssistantBridge


class FakeModel:
    def __init__(self,response): self.response=response;self.seen=[]
    def json(self,instruction,value):self.seen.append(copy.deepcopy(value));return copy.deepcopy(self.response)


class Contracts(unittest.TestCase):
    def test_mempa_external_harness_requires_checkpoint(self):
        from novours.mempa_hook import install
        for method in ['python','http','process']:
            with self.assertRaisesRegex(ValueError,'checkpoint_protocol'):
                install({'agent':{'method':method}},'unused.jsonl')
    def test_native_checkpoint_metadata_isolation(self):
        if sys.version_info<(3,10):self.skipTest('Native MemPA requires Python 3.10+')
        sys.path.insert(0,str(SOURCES/'MemPABench'))
        from pa.session.manager import SessionManager
        with tempfile.TemporaryDirectory() as d:
            main=SessionManager(Path(d)/'main')
            session=main.create('main')
            session.metadata['novours']={'state':{'items':[{'id':'e1','active':True}]}}
            main.checkpoint(session,Path(d)/'checkpoint')
            branch=SessionManager(Path(d)/'probe')
            probe=branch.restore_checkpoint('probe',Path(d)/'checkpoint')
            probe.metadata['novours']['state']['items'][0]['active']=False
            branch.save(probe)
            reread=SessionManager(Path(d)/'main').get('main')
            self.assertTrue(reread.metadata['novours']['state']['items'][0]['active'])
    def test_invalid_candidate_has_only_one_repair(self):
        model=FakeModel({'actions':[{'type':'tool','name':'invented','arguments':{}}]})
        with self.assertRaises(ValueError):propose_actions(model,{'capabilities':['respond'],'tools':[]},[],{})
        self.assertEqual(len(model.seen),2)
    def test_http_rpc_lifecycle(self):
        import threading
        from http.server import HTTPServer,BaseHTTPRequestHandler
        seen=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*a):pass
            def do_POST(self):
                req=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                seen.append(req['method'])
                self.send_response(200);self.end_headers()
                self.wfile.write(json.dumps({'id':req['id'],'result':{'ok':True}}).encode())
        server=HTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            agent=RemoteAgent({'url':f'http://127.0.0.1:{server.server_port}'})
            for method in ['initialize','act','finish']:self.assertTrue(agent.call(method,{})['ok'])
            self.assertEqual(seen,['initialize','act','finish'])
        finally:server.shutdown();server.server_close();thread.join()
    def test_no_new_capabilities(self):
        for a in [{'type':'wait'},{'type':'finish'},{'type':'tool','name':'exec','arguments':{}}]:
            with self.assertRaises(ValueError):validate_action(a,['ask','respond'])
    def test_probability_and_value(self):
        self.assertEqual(distribution([2,2]),[.5,.5])
        self.assertEqual(expected([0,1],[.5,.5]),.5)
        for p in [[0,0],[-1,2],[float('nan'),1]]:
            with self.assertRaises(ValueError):distribution(p)
    def test_transitive_invalidation(self):
        items=[{'id':'old','active':False},{'id':'plan','depends_on':['old']},{'id':'booking','depends_on':['plan']},{'id':'unrelated'}]
        new=prune_dependencies(items)
        self.assertFalse(new[2]['active']);self.assertNotIn('active',new[3]);self.assertNotIn('active',items[2])
    def test_private_lifesim_fields_never_cross_boundary(self):
        class Spy:
            def begin(self,*args):self.args=args
        spy=Spy();bridge=AssistantBridge(spy,None,[])
        event={'dialogue_scene':'station','conv_history':['hello'],'intent':'SECRET_INTENT','sub_intents':['SECRET_REQUIREMENT'],'event':'SECRET_CONTEXT'}
        bridge._build_system_prompt(event)
        encoded=json.dumps(spy.args)
        self.assertNotIn('SECRET',encoded);self.assertIn('station',encoded)
    def test_reject_invented_sources(self):
        model=FakeModel({'items':[{'id':'x','source_ids':['future_secret']} ]})
        with self.assertRaises(ValueError):fold(model,{'history':[{'id':'e1','content':'hello'}]}, {})
    def test_hypothetical_branch_does_not_mutate_observed_history(self):
        public={'history':[{'role':'user','content':'hello'}]};before=copy.deepcopy(public)
        branch=hypothetical(public,{'type':'ask','text':'which?'},'imagined')
        self.assertEqual(public,before);self.assertTrue(branch['history'][-1]['hypothetical'])
    def test_checkpoint_state_independent(self):
        main={'state':{'items':[{'id':'a','active':True}]}}
        branch=copy.deepcopy(main);branch['state']['items'][0]['active']=False
        self.assertTrue(main['state']['items'][0]['active'])
    def test_unoffered_tool_fails(self):
        with tempfile.TemporaryDirectory() as d:
            agent=Agent({'method':'direct'},FakeModel({'type':'tool','name':'invented','arguments':{}}),Journal(Path(d)/'log'))
            agent.begin('x',{},['tool'],[])
            with self.assertRaises(ValueError):agent.act('hello')
    def test_process_rpc(self):
        code='import sys,json\nfor s in sys.stdin:\n r=json.loads(s);print(json.dumps({"id":r["id"],"result":{"echo":r["params"]}}),flush=True)'
        agent=RemoteAgent({'command':[sys.executable,'-u','-c',code]})
        try:self.assertEqual(agent.call('act',{'public':1}),{'echo':{'public':1}})
        finally:agent.close()

if __name__=='__main__':unittest.main()
