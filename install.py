from __future__ import annotations
import argparse,os,shlex,subprocess,sys
from pathlib import Path
from digital_trace.common import *
from digital_trace.capture import EVENTS

def command_for(python,entry,output,windows=False):
 args=[str(python),str(entry),'capture','--output',str(output)]
 return subprocess.list2cmdline(args) if windows else shlex.join(args)

def install(project,workspace):
 project=Path(project).resolve();workspace=Path(workspace).resolve()
 if os.name=='nt' and any(x in str(project)+str(workspace)+sys.executable for x in '%\r\n'):raise TraceError('Choose a path without %, CR, LF')
 p=project/'.codex/hooks.json';doc=load(p) if p.exists() else {'hooks':{}};before=canonical(doc)
 if not isinstance(doc.get('hooks'),dict):raise TraceError('Invalid existing hook configuration')
 command=command_for(sys.executable,ROOT/'dt.py',workspace/'captured',os.name=='nt')
 for name in EVENTS:
  keep=[]
  for group in doc['hooks'].get(name,[]):
   hs=[h for h in group.get('hooks',[]) if not h.get('statusMessage','').startswith('Digital Trace v2:')]
   if hs:keep.append({**group,'hooks':hs})
  h={'type':'command','command':command,'timeout':20,'statusMessage':'Digital Trace v2: '+name}
  if os.name=='nt':h['commandWindows']=command
  keep.append({'hooks':[h]});doc['hooks'][name]=keep
 changed=canonical(doc)!=before
 if changed:
  if p.exists():atomic(p.with_name('hooks.before-dt-'+__import__('hashlib').sha256(before.encode()).hexdigest()[:12]+'.json'),before.encode())
  save(p,doc)
 return {'status':'configuration_created' if changed else 'unchanged','path':str(p),'command':command,'trusted':False,'capture_proven':False,'next_action':'Review and allow Digital Trace v2 definitions using the hook icon below the composer. Project trust is separate. No trust bypass performed.'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--project',type=Path,default=ROOT);p.add_argument('--workspace',type=Path,default=ROOT/'workspace');a=p.parse_args();print(canonical(install(a.project,a.workspace)))
