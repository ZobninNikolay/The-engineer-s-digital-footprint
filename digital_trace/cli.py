from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from .common import *
from .service import Service
from .store import initialize
from . import capture,exchange,reports,evidence

def parser():
 p=argparse.ArgumentParser(description='Digital Trace 2.0 commands for the chat assistant');p.add_argument('--workspace',type=Path,default=ROOT/'workspace');sp=p.add_subparsers(dest='cmd',required=True)
 def cmd(name):return sp.add_parser(name)
 s=cmd('init');s.add_argument('--role',choices=['student','teacher','commission'],required=True);s.add_argument('--environment',choices=['demo','pilot'],default='demo');s.add_argument('--actor',required=True);s.add_argument('--semester-start',required=True)
 s=cmd('capture');s.add_argument('--output',type=Path,required=True)
 s=cmd('doctor');s.add_argument('--marker')
 s=cmd('lesson');s.add_argument('number',type=int)
 s=cmd('enroll');s.add_argument('--student',required=True);s.add_argument('--name',required=True);s.add_argument('--group',required=True);s.add_argument('--email',default='')
 s=cmd('begin');s.add_argument('--student',required=True);s.add_argument('--name',required=True);s.add_argument('--group',required=True);s.add_argument('--lesson',type=int,required=True);s.add_argument('--session',required=True);s.add_argument('--mode',choices=['demo','learning','individual'],default='individual')
 s=cmd('resume');s.add_argument('attempt');s.add_argument('--session',required=True)
 s=cmd('run');s.add_argument('attempt');s.add_argument('--code',type=Path,required=True);s.add_argument('--input',type=Path,required=True);s.add_argument('--timeout',type=int,default=60)
 s=cmd('quota');s.add_argument('--add',type=int,default=0)
 s=cmd('freeze');s.add_argument('attempt');s.add_argument('--confirmed',action='store_true')
 s=cmd('analysis-request');s.add_argument('submission')
 s=cmd('analyze');s.add_argument('submission');s.add_argument('--response',type=Path,required=True);s.add_argument('--reason')
 s=cmd('approve');s.add_argument('assessment');s.add_argument('--reason',required=True);s.add_argument('--confirmed',action='store_true')
 s=cmd('appeal');s.add_argument('submission');s.add_argument('--reason',required=True)
 s=cmd('decide');s.add_argument('appeal');s.add_argument('--decision',choices=['confirm_existing','teacher_override'],required=True);s.add_argument('--score');s.add_argument('--reason',required=True);s.add_argument('--confirmed',action='store_true')
 s=cmd('export');s.add_argument('submission');s.add_argument('--out',type=Path,required=True)
 s=cmd('import');s.add_argument('file',type=Path)
 s=cmd('sync');s.add_argument('--inbox',type=Path,required=True)
 s=cmd('import-notice');s.add_argument('file',type=Path)
 s=cmd('report');s.add_argument('assessment');s.add_argument('--out',type=Path,required=True)
 s=cmd('gradebook');s.add_argument('--group');s.add_argument('--out',type=Path,required=True)
 s=cmd('course-report');s.add_argument('student');s.add_argument('--out',type=Path,required=True)
 s=cmd('semester');s.add_argument('student')
 s=cmd('list');s.add_argument('kind',choices=['attempt','submission','assessment','result','appeal','notice','roster'])
 return p

def main(argv=None):
 a=parser().parse_args(argv);s=None
 try:
  c=a.cmd
  if c=='capture':return capture.main(a.output)
  if c=='doctor':r=capture.doctor(a.workspace/'captured',a.marker)
  elif c=='lesson':r=evidence.lesson_info(a.number)
  elif c=='init':initialize(a.workspace,a.role,a.environment,a.actor,a.semester_start);r={'status':'initialized'}
  else:
   s=Service(a.workspace)
   if c=='enroll':r=s.enroll(a.student,a.name,a.group,a.email)
   elif c=='begin':r=s.begin(a.student,a.name,a.group,a.lesson,a.session,a.mode)
   elif c=='resume':r=s.resume(a.attempt,a.session)
   elif c=='run':r=s.run(a.attempt,a.code,load(a.input),a.timeout)
   elif c=='quota':r=s.quota(a.add)
   elif c=='freeze':
    v=s.freeze(a.attempt,a.confirmed);r={'submission_id':v['id'],'research_digest':v['bundle']['research_digest'],'coverage':v['bundle']['coverage']}
   elif c=='analysis-request':v=s.analysis_request(a.submission);r={'request_digest':v['request_digest'],'path':str(s.root/'analysis'/a.submission/'request.json')}
   elif c=='analyze':r=s.analyze(a.submission,load(a.response),a.reason)
   elif c=='approve':r=s.approve(a.assessment,a.reason,a.confirmed)
   elif c=='appeal':r=s.appeal(a.submission,a.reason)
   elif c=='decide':r=s.decide(a.appeal,a.decision,a.reason,a.score,a.confirmed)
   elif c=='export':r=exchange.export_packet(s,a.submission,a.out)
   elif c=='import':r=exchange.import_packet(s,a.file)
   elif c=='sync':
    r=[]
    for f in sorted(a.inbox.glob('*.dt.zip')):
     try:r.append({'file':f.name,**exchange.import_packet(s,f)})
     except (ValueError,KeyError,OSError) as exc:r.append({'file':f.name,'status':'rejected','error':str(exc)})
   elif c=='import-notice':r=exchange.import_notice(s,a.file)
   elif c=='report':r=reports.individual(s,a.assessment,a.out)
   elif c=='gradebook':r=reports.register(s,a.out,a.group)
   elif c=='course-report':r=reports.course_report(s,a.student,a.out)
   elif c=='semester':r=s.semester(a.student)
   elif c=='list':
    if a.kind=='roster':s.teacher()
    r=s.store.all(a.kind)
  print(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False));return 0
 except (ValueError,KeyError,OSError,ImportError,ArithmeticError) as exc:print(json.dumps({'status':'error','error':str(exc)},ensure_ascii=False),file=sys.stderr);return 1
 finally:
  if s:s.close()
