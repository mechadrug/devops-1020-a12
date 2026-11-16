"""Single-worker asynchronous classroom job API, bound to loopback by default."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import threading
import uuid
from urllib.parse import unquote
from pipeline import ROOT,execute,save

class Store:
    def __init__(self, root):
        self.root=root;root.mkdir(parents=True,exist_ok=True)
        self.lock=threading.Lock();self.pool=ThreadPoolExecutor(max_workers=1)
        self.jobs={};self.keys={}
        for p in root.glob('job-*/state.json'):
            state=json.loads(p.read_text())
            if state['status'] in ('QUEUED','RUNNING'):
                state.update(status='FAILED',error={'code':'SERVER_RESTARTED','message':'Resubmit with a new key'})
                save(p,state)
            self.jobs[state['job_id']]=state
            self.keys[state['idempotency_key']]=(state['request_hash'],state['job_id'])
    def submit(self, request, key):
        if not isinstance(request,dict):raise ValueError('input must be a JSON object')
        if not isinstance(key,str) or not key or len(key)>128:raise ValueError('idempotency_key required, max 128 characters')
        if request.get('mode') not in ('e11-a','e11-b','e12'):raise ValueError('Unknown mode')
        for field in ('repo','candidate','fixed_report'):
            if field in request:
                path=Path(request[field]).resolve()
                if not path.is_relative_to((ROOT/'data').resolve()):raise ValueError(field+' must be under /course/data')
        if not all(request.get(k) for k in ('repo','base','target')):raise ValueError('repo/base/target required')
        digest=hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest()
        with self.lock:
            if key in self.keys:
                old,jid=self.keys[key]
                if old!=digest:raise ValueError('IDEMPOTENCY_CONFLICT')
                return dict(self.jobs[jid])
            jid='job-'+uuid.uuid4().hex
            state={'schema_version':'e11e12-1','job_id':jid,'status':'QUEUED','idempotency_key':key,'request_hash':digest}
            self.jobs[jid]=state;self.keys[key]=(digest,jid);save(self.root/jid/'state.json',state)
            self.pool.submit(self.work,jid,request)
            return dict(state)
    def work(self,jid,request):
        state=self.jobs[jid]
        with self.lock:state['status']='RUNNING';save(self.root/jid/'state.json',state)
        try:r=execute(request,self.root/jid/'evidence',jid)
        except Exception as ex:r={'status':'FAILED','error':{'code':'WORKER_FAILED','message':str(ex)}}
        with self.lock:
            state.update({k:r[k] for k in ('status','trace_id','error') if k in r});save(self.root/jid/'state.json',state)

def serve(host='127.0.0.1',port=8080):
    store=Store(ROOT/'work/api-jobs')
    class Handler(BaseHTTPRequestHandler):
        def reply(self,code,obj):
            data=json.dumps(obj,ensure_ascii=False).encode();self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.end_headers();self.wfile.write(data)
        def do_POST(self):
            if self.path!='/v1/jobs':return self.reply(404,{'error':'NOT_FOUND'})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=65536:raise ValueError('Request size must be 1..65536')
                body=json.loads(self.rfile.read(size));state=store.submit(body['input'],body['idempotency_key']);self.reply(202,state)
            except (ValueError,KeyError,TypeError) as ex:self.reply(409 if str(ex)=='IDEMPOTENCY_CONFLICT' else 400,{'error':str(ex)})
        def do_GET(self):
            if self.path=='/health':return self.reply(200,{'status':'ok','schema_version':'e11e12-1'})
            parts=self.path.split('?')[0].strip('/').split('/')
            if len(parts)<3 or parts[:2]!=['v1','jobs'] or parts[2] not in store.jobs:return self.reply(404,{'error':'NOT_FOUND'})
            jid=parts[2];out=store.root/jid/'evidence'
            if len(parts)==3:return self.reply(200,dict(store.jobs[jid]))
            if parts[3:]==['artifacts']:
                if not (out/'result.json').exists():return self.reply(409,{'error':'RESULT_NOT_READY'})
                return self.reply(200,json.loads((out/'result.json').read_text()))
            if len(parts)>=5 and parts[3]=='files':
                name=unquote('/'.join(parts[4:]));path=(out/name).resolve()
                if not path.is_relative_to(out.resolve()) or '.git' in path.parts or not path.is_file():return self.reply(404,{'error':'NOT_FOUND'})
                data=path.read_bytes();self.send_response(200);self.send_header('Content-Type','application/octet-stream');self.send_header('X-Content-SHA256',hashlib.sha256(data).hexdigest());self.end_headers();self.wfile.write(data);return
            self.reply(404,{'error':'NOT_FOUND'})
    ThreadingHTTPServer((host,port),Handler).serve_forever()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=8080);a=p.parse_args();serve(a.host,a.port)
