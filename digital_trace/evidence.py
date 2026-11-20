from __future__ import annotations
import base64,json,hashlib
from pathlib import Path
from .common import *
from . import capture,runner

def lesson_info(n):
 if type(n)!=int or n not in range(1,16):raise TraceError('Lesson must be 1..15')
 d=load(ROOT/f'course/profiles/lesson_{n:02d}.json')
 if filehash(ROOT/d['source'])!=d['sha256']:raise TraceError('Course source changed; review/version it first')
 return d

def freeze(root,attempt):
 all_events=capture.read(Path(root)/'captured');capture.validate(all_events);selected=[];gaps=[]
 for link in attempt['sessions']:
  es=[e for e in all_events if e['session_id']==link['id'] and e['seq']>=link['start_seq']]
  stops=[e['seq'] for e in es if e['hook_event_name']=='Stop']
  if not stops:raise TraceError('No completed captured assistant turn for session')
  es=[e for e in es if e['seq']<=max(stops)];selected.extend(es)
  if not any(e['hook_event_name']=='SessionStart' and e['session_id']==link['id'] for e in all_events):gaps.append('session_start_missing')
  for e in es:
   n=capture.normalized(e)
   if n['missing']:gaps.append('missing_'+n['kind'])
   if n['kind']=='Interrupt':gaps.append('interrupted_text_unavailable')
   if n['kind']=='PostToolUse' and ('tokens truncated' in n['text'].lower() or 'output truncated' in n['text'].lower()):gaps.append('tool_output_truncated')
 selected=sorted({e['seq']:e for e in selected}.values(),key=lambda e:e['seq'])
 if not any(e['hook_event_name']=='UserPromptSubmit' for e in selected):raise TraceError('No original student message')
 runs=[]
 for r in attempt['runs']:
  p=runner.verify(root,r);runs.append({'execution':r,'stdout':(p/'stdout.txt').read_text(encoding='utf-8',errors='replace'),'stderr':(p/'stderr.txt').read_text(encoding='utf-8',errors='replace')})
 b={'version':'2.0.0','attempt':attempt,'lesson':lesson_info(attempt['lesson']),'captured_events':selected,'runs':runs,'coverage':{'gaps':sorted(set(gaps)),'intermediate_assistant_messages':'not guaranteed by Stop hook','after_last_stop':'excluded; current confirmation turn is not part of research slice','external_anchor':False,'identity':'local declared; not SSO'},'frozen_at':now()}
 b['research_digest']=digest(b);return b

def verify_bundle(b):
 body=dict(b);observed=body.pop('research_digest',None)
 if digest(body)!=observed:raise TraceError('Research digest mismatch')
 seqs=[]
 for e in b['captured_events']:
  ee=dict(e);h=ee.pop('research_digest',None)
  if digest(ee)!=h:raise TraceError('Event digest mismatch')
  raw=base64.b64decode(e['raw_input_base64'],validate=True)
  if hashlib.sha256(raw).hexdigest()!=e['raw_sha256'] or json.loads(raw.decode('utf-8-sig'))!=e['raw_payload']:raise TraceError('Original event bytes mismatch')
  if not any(e['session_id']==s['id'] and e['seq']>=s['start_seq'] for s in b['attempt']['sessions']):raise TraceError('Wrong event scope')
  seqs.append(e['seq'])
 if seqs!=sorted(set(seqs)):raise TraceError('Duplicate/reordered events')
 if b['lesson']!=lesson_info(b['attempt']['lesson']):raise TraceError('Different course version')
 for r in b['runs']:
  for field in ('stdout','stderr'):
   if hashlib.sha256(r[field].encode()).hexdigest()!=r['execution']['files'][field+'.txt']:raise TraceError('Run text/hash mismatch; use UTF-8 execution output')
 return True

def evidence_list(b):
 verify_bundle(b);out=[capture.normalized(e) for e in b['captured_events']]
 for r in b['runs']:out.append({'event_id':r['execution']['run_id'],'actor':'executor','kind':'research_run','text':canonical(r),'missing':False})
 return out
