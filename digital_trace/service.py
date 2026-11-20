from __future__ import annotations
import uuid,hashlib
from pathlib import Path
from decimal import Decimal
from datetime import timedelta
from .common import *
from .store import Store
from . import capture,evidence,assessment,runner

def newid(prefix):return prefix+'-'+uuid.uuid4().hex
class Service:
 def __init__(self,root):self.root=Path(root).resolve();self.store=Store(root);self.config=self.store.get('config','main')
 def close(self):self.store.close()
 def teacher(self):
  if self.config['role'] not in ('teacher','commission'):raise TraceError('Teacher workspace required')
 def owner(self,s):
  if self.config['role']=='student' and s!=self.config['actor']:raise TraceError('Wrong student identity')
 def timely(self):
  if self.config['environment']=='pilot':
   d=date(now());start=date(self.config['semester_start'])
   if not start<=d<start+timedelta(weeks=15):raise TraceError('Outside 15-week semester; existing work is preserved')
 def enroll(self,sid,name,group,email=''):
  self.teacher();ident(sid);text(name);text(group)
  r={'student':sid,'name':name,'group':group,'email':email}
  with self.store.transaction():self.store.put('roster',sid,r)
  return r
 def begin(self,sid,name,group,lesson,session,mode='individual'):
  self.owner(sid);ident(sid);text(name);text(group);evidence.lesson_info(lesson)
  if mode not in ('demo','learning','individual'):raise TraceError('Unknown mode')
  if mode=='individual':self.timely()
  es=capture.read(self.root/'captured');capture.validate(es);ps=[e for e in es if e['session_id']==session and e['hook_event_name']=='UserPromptSubmit']
  if not ps:raise TraceError('No observed original prompt for this session; do not invent a session ID')
  a={'id':newid('attempt'),'student':sid,'name':name,'group':group,'lesson':lesson,'mode':mode,'environment':self.config['environment'],'semester_start':self.config['semester_start'],'status':'active','started_at':now(),'sessions':[{'id':session,'start_seq':ps[-1]['seq']}],'runs':[],'variant_seed':int(hashlib.sha256((sid+':'+str(lesson)).encode()).hexdigest()[:8],16),'variant_note':'Seed only; task parameters must be taken from source and recorded in dialogue'}
  with self.store.transaction():
   if any(x['status']=='active' and any(s['id']==session for s in x['sessions']) for x in self.store.all('attempt')):raise TraceError('An active attempt already uses this session')
   self.store.put('attempt',a['id'],a);self.store.audit('begin',a['id'])
  return a
 def resume(self,aid,session):
  with self.store.transaction():
   a=self.store.get('attempt',aid);self.owner(a['student'])
   if a['status']!='active':raise TraceError('Attempt is sealed')
   es=capture.read(self.root/'captured');capture.validate(es);ps=[e for e in es if e['session_id']==session and e['hook_event_name']=='UserPromptSubmit']
   if not ps:raise TraceError('No observed prompt')
   if not any(s['id']==session for s in a['sessions']):a['sessions'].append({'id':session,'start_seq':ps[-1]['seq']})
   self.store.put('attempt',aid,a)
  return a
 def quota(self,add=0):
  if type(add)!=int or add<0:raise TraceError('Nonnegative integer required')
  with self.store.transaction():
   c=self.store.get('config','main');c['limit']+=add;self.store.put('config','main',c)
   if add:self.store.audit('local_operator_quota_add',{'add':add,'identity_assurance':'local operator; not university authorization'})
  return {'used':c['used'],'limit':c['limit'],'warning':c['used']>=.8*c['limit'],'remaining':max(0,c['limit']-c['used']),'grade_penalty':0,'scope':'local experiment executions; NOT ChatGPT tokens or subscription credit'}
 def run(self,aid,code,params,timeout=60):
  with self.store.transaction():
   a=self.store.get('attempt',aid);self.owner(a['student']);c=self.store.get('config','main')
   if a['status']!='active':raise TraceError('Attempt is sealed')
   if a['mode']=='individual':self.timely()
   if c['used']>=c['limit']:raise TraceError('Organizational resource exhausted; work preserved. Operator can add access.')
   c['used']+=1;self.store.put('config','main',c)
   # Serialize the attempt while executing, preventing freeze/run races.
   r=runner.execute(self.root,code,params,timeout);a['runs'].append(r);self.store.put('attempt',aid,a);self.store.audit('run',r)
  return r
 def freeze(self,aid,confirmed=False):
  if not confirmed:raise TraceError('Student confirmation required before sealing')
  with self.store.transaction():
   a=self.store.get('attempt',aid);self.owner(a['student'])
   if a['status']=='submitted':return self.store.get('submission',a['submission_id'])
   if a['mode']=='individual':self.timely()
   b=evidence.freeze(self.root,a);sid=newid('submission');record={'id':sid,'bundle':b,'submitted_at':now()};self.store.put('submission',sid,record)
   a['status']='submitted';a['submission_id']=sid;self.store.put('attempt',aid,a);self.store.audit('freeze',{'submission':sid,'digest':b['research_digest']})
  save(self.root/'submissions'/sid/'bundle.json',b);return record
 def analysis_request(self,sid):
  b=self.store.get('submission',sid)['bundle'];self.owner(b['attempt']['student']);r=assessment.request(b);save(self.root/'analysis'/sid/'request.json',r);return r
 def analyze(self,sid,response,reason=None):
  req=self.analysis_request(sid)
  if response is None:raise TraceError('Semantic model response required; no fallback or keyword score')
  result=assessment.validate_response(req,response)
  with self.store.transaction():
   old=[x for x in self.store.all('assessment') if x['submission_id']==sid]
   for x in old:
    if x['response']==response:return x
   if old and not reason:raise TraceError('Reason required for reanalysis; old result preserved')
   result.update(id=newid('assessment'),submission_id=sid,version=len(old)+1,created_at=now(),reason=reason);self.store.put('assessment',result['id'],result);self.store.audit('analysis',result['id'])
  save(self.root/'analysis'/sid/(result['id']+'.json'),result);return result
 def check_roster(self,b):
  a=b['attempt'];r=self.store.get('roster',a['student'])
  if (r['name'],r['group'])!=(a['name'],a['group']):raise TraceError('Roster mismatch')
  if a['environment']!=self.config['environment'] or a['semester_start']!=self.config['semester_start']:raise TraceError('Environment/semester mismatch')
  if a['mode']!='individual':raise TraceError('Demo/learning attempts cannot enter gradebook')
  if self.config['environment']=='pilot' and any(e['raw_payload'].get('test_fixture') or e['raw_payload'].get('synthetic_commission_example') for e in b['captured_events']):raise TraceError('Synthetic example cannot become a pilot grade')
  evidence.verify_bundle(b)
 def _result(self,a,score,reason):
  b=self.store.get('submission',a['submission_id'])['bundle'];self.check_roster(b)
  for r in self.store.all('result'):
   if r['submission_id']==a['submission_id'] and r['active']:r['active']=False;self.store.put('result',r['id'],r)
  r={'id':newid('result'),'submission_id':a['submission_id'],'assessment_id':a['id'],'student':b['attempt']['student'],'lesson':b['attempt']['lesson'],'score':str(score),'active':True,'confirmed_at':now(),'reason':text(reason),'teacher':self.config['actor']};self.store.put('result',r['id'],r);return r
 def approve(self,aid,reason,confirmed=False):
  self.teacher()
  if not confirmed:raise TraceError('Teacher confirmation required')
  with self.store.transaction():
   a=self.store.get('assessment',aid)
   if a['score'] is None:raise TraceError('No sufficient evidence for numeric result')
   if any(x['submission_id']==a['submission_id'] and x['status']=='open' for x in self.store.all('appeal')):raise TraceError('Resolve open appeal first')
   existing=[r for r in self.store.all('result') if r['assessment_id']==aid and r['active']]
   if existing:return existing[0]
   r=self._result(a,a['score'],reason);self.store.audit('approve',r)
  return r
 def appeal(self,sid,reason):
  b=self.store.get('submission',sid)['bundle'];self.owner(b['attempt']['student']);text(reason)
  with self.store.transaction():
   if any(x['submission_id']==sid and x['status']=='open' for x in self.store.all('appeal')):raise TraceError('Appeal already open')
   grades=[g for g in self.store.all('assessment') if g['submission_id']==sid]
   target=max(grades,key=lambda g:g['version'])['id'] if grades else None
   a={'id':newid('appeal'),'submission_id':sid,'student':b['attempt']['student'],'lesson':b['attempt']['lesson'],'target_assessment_id':target,'research_digest':b['research_digest'],'reason':reason,'status':'open','created_at':now()};self.store.put('appeal',a['id'],a);self.store.audit('appeal',a)
  return a
 def decide(self,apid,decision,reason,score=None,confirmed=False):
  self.teacher();text(reason)
  if not confirmed or decision not in ('confirm_existing','teacher_override'):raise TraceError('Explicit teacher decision required')
  with self.store.transaction():
   ap=self.store.get('appeal',apid)
   if ap['status']!='open':raise TraceError('Appeal already resolved')
   analyses=[a for a in self.store.all('assessment') if a['submission_id']==ap['submission_id']]
   if not analyses:raise TraceError('Teacher analysis of imported evidence required first')
   target=[x for x in analyses if x['id']==ap.get('target_assessment_id')]
   a=target[0] if target else max(analyses,key=lambda x:x['version'])
   if decision=='confirm_existing' and a['score'] is None:raise TraceError('No numeric recommendation to confirm')
   v=Decimal(str(a['score'] if decision=='confirm_existing' else score))
   if not v.is_finite() or not 0<=v<=100:raise TraceError('Score must be finite in 0..100')
   r=self._result(a,str(v.quantize(Decimal('.1'))),reason);ap.update(status='resolved',decision=decision,decision_reason=reason,result_id=r['id'],resolved_at=now());self.store.put('appeal',apid,ap)
   roster=self.store.get('roster',ap['student']);notice={'id':newid('notice'),'student':ap['student'],'appeal':ap,'score':r['score'],'email':{'to':roster['email'],'status':'not_sent_stub'},'message':reason};self.store.put('notice',notice['id'],notice);self.store.audit('appeal_decision',notice)
  save(self.root/'outbox'/(notice['id']+'.json'),notice);return notice
 def gradebook(self,group=None):
  self.teacher();rows=[]
  for s in self.store.all('roster'):
   if group and s['group']!=group:continue
   for n in range(1,16):
    rr=[r for r in self.store.all('result') if r['student']==s['student'] and r['lesson']==n and r['active']]
    appeals=[a for a in self.store.all('appeal') if a['student']==s['student'] and a['lesson']==n and a['status']=='open']
    best=sorted(rr,key=lambda x:(-Decimal(x['score']),x['confirmed_at'],x['id']))[0] if rr else None
    rows.append({'student':s['student'],'name':s['name'],'group':s['group'],'lesson':n,'score':best['score'] if best else None,'result_id':best['id'] if best else None,'assessment_id':best['assessment_id'] if best else None,'status':'appeal_open' if appeals else ('approved' if best else 'missing_or_pending'),'transfer_allowed':bool(best and not appeals)})
  return {'generated_at':now(),'environment':self.config['environment'],'selection':'best whole active teacher-confirmed result per lesson; any open appeal blocks this lesson','rows':rows}
 def semester(self,sid):
  rows=[x for x in self.gradebook()['rows'] if x['student']==sid];missing=[x['lesson'] for x in rows if not x['transfer_allowed']]
  return {'student':sid,'missing_lessons':missing,'deadline':(date(self.config['semester_start'])+timedelta(weeks=15)).isoformat(),'summer_semester_review_required':bool(missing and date(now())>=date(self.config['semester_start'])+timedelta(weeks=15)),'university_enrollment_or_payment_action':'not performed; university authorization/integration required'}
