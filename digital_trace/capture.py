"""Platform input bytes are stored verbatim. JSONL files are rebuildable views."""
from __future__ import annotations
import base64,json,sqlite3,sys
from pathlib import Path
from .common import *
EVENTS=('SessionStart','UserPromptSubmit','PreToolUse','PostToolUse','Stop','SessionEnd','Interrupt','PreCompact','PostCompact')
def connect(root):
 root=Path(root);root.mkdir(parents=True,exist_ok=True)
 c=sqlite3.connect(root/'capture.sqlite3',timeout=15);c.execute('PRAGMA journal_mode=WAL');c.execute('PRAGMA synchronous=FULL')
 c.execute('CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY, body TEXT NOT NULL)');return c
def read(root):
 if not (Path(root)/'capture.sqlite3').exists():return []
 c=connect(root)
 try:return [json.loads(x[0]) for x in c.execute('SELECT body FROM events ORDER BY seq')]
 finally:c.close()
def validate(events):
 previous='0'*64
 for n,e in enumerate(events,1):
  body=dict(e);h=body.pop('research_digest',None)
  if e['seq']!=n or e['previous_digest']!=previous or digest(body)!=h:raise TraceError('Capture chain mismatch')
  raw=base64.b64decode(e['raw_input_base64'],validate=True)
  if __import__('hashlib').sha256(raw).hexdigest()!=e['raw_sha256'] or json.loads(raw.decode('utf-8-sig'))!=e['raw_payload']:raise TraceError('Original payload mismatch')
  previous=h
 return previous
def normalized(e):
 p=e['raw_payload'];kind=e['hook_event_name'];actor='platform';value=None
 for k,field,a in [('UserPromptSubmit','prompt','student'),('Stop','last_assistant_message','assistant'),('PreToolUse','tool_input','model_tool_arguments'),('PostToolUse','tool_response','executor')]:
  if kind==k:actor=a;value=p.get(field)
 return {'event_id':'hook-'+str(e['seq']),'session_id':e['session_id'],'kind':kind,'actor':actor,'text':value if isinstance(value,str) else canonical(value),'missing':value is None and actor!='platform'}
def _project(c,root):
 events=[json.loads(r[0]) for r in c.execute('SELECT body FROM events ORDER BY seq')]
 for name,rows in [('events.jsonl',events),('platform_payloads.jsonl',[e['raw_payload'] for e in events]),('normalized_events.jsonl',[normalized(e) for e in events])]:
  atomic(Path(root)/name,(''.join(canonical(x)+'\n' for x in rows)).encode())
def record(raw,root):
 p=json.loads(raw.decode('utf-8-sig'))
 if not isinstance(p,dict) or p.get('hook_event_name') not in EVENTS or not p.get('session_id'):raise TraceError('Unsupported or incomplete hook payload')
 c=connect(root)
 try:
  c.execute('BEGIN IMMEDIATE');events=[json.loads(x[0]) for x in c.execute('SELECT body FROM events ORDER BY seq')];previous=validate(events)
  fp=digest(p);e={'seq':len(events)+1,'session_id':p['session_id'],'hook_event_name':p['hook_event_name'],'received_at':now(),'raw_payload':p,'raw_input_base64':base64.b64encode(raw).decode(),'raw_sha256':__import__('hashlib').sha256(raw).hexdigest(),'fingerprint':fp,'duplicate_of_seq':next((x['seq'] for x in events if x['fingerprint']==fp),None),'previous_digest':previous}
  e['research_digest']=digest(e);c.execute('INSERT INTO events VALUES(?,?)',(e['seq'],canonical(e)));c.commit()
  # Separate transaction: a failed projection never destroys captured bytes.
  c.execute('BEGIN IMMEDIATE');_project(c,root);c.commit();return e
 except Exception:c.rollback();raise
 finally:c.close()
def doctor(root,marker=None):
 es=read(root);validate(es)
 return {'status':'captured_local_payloads' if es else 'no_events','events':len(es),'types':sorted({e['hook_event_name'] for e in es}),'marker_events':[e['seq'] for e in es if marker and marker in canonical(e['raw_payload'])],'full_J0':'not_certified','external_anchor':False,'sessions':sorted({e['session_id'] for e in es})}
def main(root):
 try:
  e=record(sys.stdin.buffer.read(),root)
  out={'hookSpecificOutput':{'hookEventName':'UserPromptSubmit','additionalContext':'Digital Trace observed session_id='+e['session_id']}} if e['hook_event_name']=='UserPromptSubmit' else {}
  print(json.dumps(out));return 0
 except Exception as exc:
  Path(root).mkdir(parents=True,exist_ok=True)
  with (Path(root)/'hook_errors.log').open('a',encoding='utf-8') as f:f.write(now()+' '+str(exc)+'\n')
  print(str(exc),file=sys.stderr);return 1
