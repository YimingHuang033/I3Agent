from __future__ import annotations
import copy
import hashlib
import json
import os
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT / 'benchmarks/sources'


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n')
    temp.replace(path)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


class Journal:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

    def add(self, kind, **fields):
        with self.lock, self.path.open('a') as f:
            f.write(json.dumps(dict(kind=kind, time=time.time(), **fields), ensure_ascii=False, default=str) + '\n')


class Model:
    """Shared OpenAI-compatible transport. No automatic retries or hidden fallbacks."""
    def __init__(self, config, journal, role):
        self.config, self.journal, self.role = config, journal, role
        self.calls = 0
        self.tokens = 0
        self.lock = threading.Lock()

    def request(self, messages, tools=None, **overrides):
        c = self.config
        with self.lock:
            if self.calls >= c.get('max_calls', 10000):
                raise RuntimeError(f'{self.role}: model call budget exhausted')
            self.calls += 1
        payload = dict(model=c['model'], messages=copy.deepcopy(messages), temperature=c.get('temperature', 0), max_tokens=c.get('max_tokens', 4096))
        payload.update(c.get('extra_body', {}))
        payload.update({k:v for k,v in overrides.items() if v is not None})
        if tools:
            payload['tools'] = tools
        key = (os.environ.get(c['key_env']) if c.get('key_env') else c.get('local_key', 'EMPTY'))
        if c.get('key_env') and not key:
            raise RuntimeError(f'Missing credential environment variable {c["key_env"]}')
        req = urllib.request.Request(c['base_url'].rstrip('/') + '/chat/completions', data=json.dumps(payload).encode(), headers={'Content-Type':'application/json','Authorization':f'Bearer {key}'})
        start = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=c.get('timeout',180)) as r:
                data = json.load(r)
            choice = data['choices'][0]
            self.journal.add('model_call', role=self.role, request=payload, response=data, elapsed=time.monotonic()-start)
            if choice.get('finish_reason') == 'length':
                raise RuntimeError(f'{self.role}: truncated model response')
            self.tokens += data.get('usage',{}).get('total_tokens',0)
            return data
        except Exception as e:
            detail=''
            if hasattr(e,'read'):
                try:
                    error=json.loads(e.read())
                    detail=str(error.get('error',{}).get('message',''))[:1500].replace(key or '\0','[REDACTED]')
                except Exception: pass
            self.journal.add('model_error', role=self.role, request=payload, error=type(e).__name__, detail=detail, status=getattr(e,'code',None), elapsed=time.monotonic()-start)
            raise

    def chat(self, messages, **kwargs):
        return self.request(messages, **kwargs)['choices'][0]['message'].get('content') or ''

    def json(self, instruction, value):
        text = self.chat([{'role':'system','content':instruction + '\nReturn one JSON object only.'}, {'role':'user','content':json.dumps(value,ensure_ascii=False)}], response_format={'type':'json_object'})
        return json.loads(text)

    def save(self, path):
        dump(path, {'calls':self.calls,'tokens':self.tokens,'journal':str(self.journal.path)})


def validate_action(action, capabilities):
    if not isinstance(action, dict) or action.get('type') not in {'ask','respond','tool','wait','finish'}:
        raise ValueError('invalid action type')
    if action['type'] not in capabilities:
        raise ValueError(f'unsupported source action: {action["type"]}')
    if action['type'] in {'ask','respond'} and not isinstance(action.get('text'),str):
        raise ValueError('text required')
    if action['type'] == 'tool' and (not isinstance(action.get('name'),str) or not isinstance(action.get('arguments'),dict)):
        raise ValueError('tool name and arguments required')
    return action


class RemoteAgent:
    """Stateful JSONL subprocess or HTTP RPC. Only public payloads cross this boundary."""
    def __init__(self, config):
        self.config = config
        self.process = None
        if config.get('command'):
            self.process = subprocess.Popen(config['command'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self.seq = 0

    def call(self, method, payload):
        self.seq += 1
        req = {'version':1,'id':self.seq,'method':method,'params':payload}
        if self.process:
            import selectors
            self.process.stdin.write(json.dumps(req)+'\n'); self.process.stdin.flush()
            with selectors.DefaultSelector() as sel:
                sel.register(self.process.stdout, selectors.EVENT_READ)
                if not sel.select(self.config.get('timeout',180)):
                    raise TimeoutError('agent RPC timeout')
            response = json.loads(self.process.stdout.readline())
        else:
            request = urllib.request.Request(self.config['url'],data=json.dumps(req).encode(),headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(request,timeout=self.config.get('timeout',180)) as r:
                response = json.load(r)
        if response.get('id') != req['id'] or response.get('error'):
            raise RuntimeError('agent RPC failed: response ID mismatch or error')
        return response['result']

    def close(self):
        if self.process:
            self.process.terminate()
            try: self.process.wait(timeout=5)
            except subprocess.TimeoutExpired: self.process.kill(); self.process.wait()
            self.process.stdin.close();self.process.stdout.close()


class PythonAgent:
    def __init__(self,config):
        import importlib
        module,name=config['factory'].split(':',1)
        self.instance=getattr(importlib.import_module(module),name)(config.get('options',{}))
    def call(self,method,payload):
        return getattr(self.instance,method)(copy.deepcopy(payload))
    def close(self):
        if hasattr(self.instance,'close'):self.instance.close()
