from __future__ import annotations
import zipfile,json,hashlib,shutil
from pathlib import Path,PurePosixPath
from .common import *
from . import evidence,runner

def export_packet(service,sid,out):
 sub=service.store.get('submission',sid);b=sub['bundle'];service.owner(b['attempt']['student']);evidence.verify_bundle(b)
 packet={'version':'2.0.0','submission':sub,'analysis_candidates':[a for a in service.store.all('assessment') if a['submission_id']==sid],'appeals':[a for a in service.store.all('appeal') if a['submission_id']==sid]}
 files={'packet.json':canonical(packet).encode()}
 for r in b['runs']:
  p=runner.verify(service.root,r['execution'])
  for name in [*r['execution']['files'],'execution.json']:files['runs/'+r['execution']['run_id']+'/'+name]=(p/name).read_bytes()
 manifest={n:hashlib.sha256(data).hexdigest() for n,data in files.items()};out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
  for name,data in files.items():z.writestr(name,data)
  z.writestr('manifest.json',canonical(manifest))
 return {'packet':str(out.resolve()),'files':len(files),'submission_id':sid}

def import_packet(service,path):
 service.teacher()
 with zipfile.ZipFile(path) as z:
  infos=z.infolist()
  if len(infos)>1000 or sum(i.file_size for i in infos)>60*1024*1024:raise TraceError('Packet exceeds limits')
  names=[i.filename for i in infos]
  if len(names)!=len(set(names)):raise TraceError('Duplicate ZIP entry')
  for i in infos:
   p=PurePosixPath(i.filename)
   if p.is_absolute() or '..' in p.parts or '\\' in i.filename or ':' in i.filename or (i.external_attr>>16)&0o170000==0o120000:raise TraceError('Unsafe ZIP path')
  files={n:z.read(n) for n in names};manifest=json.loads(files.pop('manifest.json'))
 if set(files)!=set(manifest) or any(hashlib.sha256(v).hexdigest()!=manifest[k] for k,v in files.items()):raise TraceError('Packet manifest mismatch')
 packet=json.loads(files['packet.json']);sub=packet['submission'];sid=ident(sub['id']);b=sub['bundle'];evidence.verify_bundle(b);service.check_roster(b)
 allowed={'packet.json'}
 for r in b['runs']:
  e=r['execution'];rid=ident(e['run_id'])
  for name,h in e['files'].items():
   p=PurePosixPath(name)
   if p.is_absolute() or '..' in p.parts:raise TraceError('Unsafe artifact path')
   key='runs/'+rid+'/'+name;allowed.add(key)
   if key not in files or hashlib.sha256(files[key]).hexdigest()!=h:raise TraceError('Missing or altered run artifact')
  key='runs/'+rid+'/execution.json';allowed.add(key)
  if json.loads(files[key])!=e:raise TraceError('Run metadata mismatch')
 if set(files)!=allowed:raise TraceError('Unexpected archive files')
 for ap in packet['appeals']:
  ident(ap['id'])
  if ap['submission_id']!=sid or ap['student']!=b['attempt']['student'] or ap['lesson']!=b['attempt']['lesson']:raise TraceError('Wrong appeal scope')
  text(ap['reason'])
 with service.store.transaction():
  old=[x for x in service.store.all('submission') if x['id']==sid]
  if old and old[0]!=sub:raise TraceError('Conflicting submission ID')
  if not old:
   for name,data in files.items():
    if name.startswith('runs/'):
     p=service.root/name
     if p.exists() and p.read_bytes()!=data:raise TraceError('Existing artifact collision')
     atomic(p,data)
   service.store.put('submission',sid,sub)
   # Untrusted student model outputs never become the teacher's own assessment.
   service.store.put('analysis_candidates',sid,packet['analysis_candidates'])
  for ap in packet['appeals']:
   previous=[x for x in service.store.all('appeal') if x['id']==ap['id']]
   if previous:
    if any(previous[0].get(k)!=ap.get(k) for k in ('submission_id','student','lesson','reason')):raise TraceError('Conflicting appeal ID')
   elif ap['status']=='open':service.store.put('appeal',ap['id'],{**ap,'origin':'student_packet'})
  service.store.audit('packet_import',{'submission':sid,'already_imported':bool(old)})
 return {'status':'already_imported' if old else 'imported','submission_id':sid,'student_analysis':'untrusted candidate only; fresh teacher analysis required'}

def import_notice(service,path):
 n=load(path);service.owner(n['student']);ident(n['id'])
 if n['email']['status']!='not_sent_stub':raise TraceError('This release only supports explicit email stub notices')
 ap=service.store.get('appeal',n['appeal']['id'])
 if ap['submission_id']!=n['appeal']['submission_id'] or ap['student']!=n['student']:raise TraceError('Wrong notice target')
 with service.store.transaction():
  service.store.put('notice',n['id'],n);ap.update(status='resolved',decision=n['appeal']['decision'],decision_reason=n['message']);service.store.put('appeal',ap['id'],ap)
 return n
