from __future__ import annotations
import subprocess,sys,shutil,uuid
from pathlib import Path
from .common import *
def execute(root,code,params,timeout=60):
 if type(timeout)!=int or not 1<=timeout<=300:raise TraceError('Timeout must be 1..300 seconds')
 ident_run='run-'+uuid.uuid4().hex;p=Path(root)/'runs'/ident_run;p.mkdir(parents=True)
 shutil.copyfile(code,p/'model.py');save(p/'input.json',params)
 start=now();status='executed';returncode=None
 with (p/'stdout.txt').open('wb') as out,(p/'stderr.txt').open('wb') as err:
  try:
   r=subprocess.run([sys.executable,'-I','-X','utf8',str((p/'model.py').resolve()),str((p/'input.json').resolve())],cwd=p,stdout=out,stderr=err,timeout=timeout);returncode=r.returncode
   if returncode!=0:status='failed'
  except subprocess.TimeoutExpired:status='timeout'
 hashes={}
 for f in sorted(p.rglob('*')):
  if f.is_symlink():raise TraceError('Symlink artifact rejected')
  if f.is_file():
   if f.stat().st_size>10*1024*1024:raise TraceError('Artifact exceeds 10 MB; files preserved for review')
   hashes[f.relative_to(p).as_posix()]=filehash(f)
 e={'run_id':ident_run,'started_at':start,'finished_at':now(),'status':status,'exit_code':returncode,'python':sys.version.split()[0],'files':hashes,'sandbox':'none: local Python execution'};save(p/'execution.json',e);return e
def verify(root,r):
 p=Path(root)/'runs'/ident(r['run_id'])
 if load(p/'execution.json')!=r:raise TraceError('Execution metadata changed')
 for f,h in r['files'].items():
  q=Path(f)
  if q.is_absolute() or '..' in q.parts or (p/q).is_symlink() or filehash(p/q)!=h:raise TraceError('Execution artifact changed')
 return p
