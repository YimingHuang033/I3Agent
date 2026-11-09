"""Local transport bridge for native OpenRouter-only entrypoints.
Records actual backend identity. Original prompts and tool schemas are preserved.
"""
import json
import threading
import time
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from .core import Model


class Gateway:
    def __init__(self,routes,journal,embed=None):
        models={name:Model(cfg,journal,role) for name,(cfg,role) in routes.items()}
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def send(self,status,value):
                self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(value).encode())
            def do_GET(self):
                self.send(200,{'data':[{'id':m,'supported_parameters':['tools','tool_choice','temperature','response_format']} for m in models]})
            def do_POST(self):
                try:
                    body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    if self.path.endswith('/embeddings') and embed is not None:
                        texts=body['input'];texts=[texts] if isinstance(texts,str) else texts
                        if texts and not isinstance(texts[0],str):
                            import tiktoken
                            texts=[tiktoken.get_encoding('cl100k_base').decode(t) for t in texts]
                        vectors=embed(texts)
                        if body.get('encoding_format')=='base64':
                            import numpy as np,base64
                            vectors=[base64.b64encode(np.asarray(v,dtype=np.float32).tobytes()).decode() for v in vectors]
                        else:vectors=[list(map(float,v)) for v in vectors]
                        journal.add('embedding_call',model=body['model'],count=len(texts))
                        self.send(200,{'object':'list','data':[{'object':'embedding','index':i,'embedding':v} for i,v in enumerate(vectors)],'model':body['model'],'usage':{'prompt_tokens':0,'total_tokens':0}});return
                    model=models[body['model']]
                    extras={k:v for k,v in body.items() if k in {'temperature','max_tokens','tool_choice','response_format'}}
                    if extras.get('response_format',{}).get('type')=='json_schema' and 'deepseek' in model.config['model']:
                        extras['response_format']={'type':'json_object'}
                        journal.add('transport_conversion',conversion='json_schema_to_json_object',role=model.role)
                    # Max output bound is explicit in experiment config, not inherited huge caps.
                    extras['max_tokens']=min(extras.get('max_tokens',4096),model.config.get('max_tokens',4096))
                    result=model.request(body['messages'],body.get('tools'),**extras)
                    result['model']=body['model']
                    if not body.get('stream'): self.send(200,result);return
                    self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
                    message=result['choices'][0]['message']
                    tools=message.get('tool_calls',[])
                    delta={k:v for k,v in message.items() if k in {'role','content','reasoning_content'}}
                    if tools:delta['tool_calls']=[dict(t,index=i) for i,t in enumerate(tools)]
                    chunk={'id':result.get('id','bridge'),'object':'chat.completion.chunk','created':int(time.time()),'model':body['model'],'choices':[{'index':0,'delta':delta,'finish_reason':None}]}
                    self.wfile.write(('data: '+json.dumps(chunk)+'\n\n').encode())
                    chunk['choices']=[{'index':0,'delta':{},'finish_reason':result['choices'][0].get('finish_reason','stop')}];chunk['usage']=result.get('usage',{})
                    self.wfile.write(('data: '+json.dumps(chunk)+'\n\ndata: [DONE]\n\n').encode())
                except Exception as e:
                    journal.add('gateway_error',error=type(e).__name__)
                    self.send(502,{'error':{'message':type(e).__name__,'type':'backend_error'}})
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.url=f'http://127.0.0.1:{self.server.server_port}/v1'
    def __enter__(self):self.thread.start();return self
    def __exit__(self,*args):self.server.shutdown();self.server.server_close();self.thread.join()
