import copy,importlib.util,json,subprocess,sys,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from digital_trace.common import *
from digital_trace.store import initialize
from digital_trace.service import Service
from digital_trace import capture,assessment,evidence,exchange,reports
from install import install,command_for
from tools.j0_probe import check

def event(root,kind,session='fixture',**extra):
 return capture.record(canonical({'hook_event_name':kind,'session_id':session,'test_fixture':True,**extra}).encode(),Path(root)/'captured')
def fixture(s,session='fixture',mode='individual'):
 event(s.root,'SessionStart',session);event(s.root,'UserPromptSubmit',session,prompt='Проверю две компоновки и ограничения ширины. Меняю модель, а не считаю вручную.')
 a=s.begin('student1','Тестовый студент','DEMO',8,session,mode);s.run(a['id'],ROOT/'models/copper_model.py',{})
 event(s.root,'Stop',session,last_assistant_message='Результаты исполнения сохранены.')
 event(s.root,'UserPromptSubmit',session,prompt='Проверю исходную геометрию и теплоотвод. Вывод ограничен принятыми допущениями.');s.run(a['id'],ROOT/'models/copper_model.py',{'rows_count':1})
 event(s.root,'Stop',session,last_assistant_message='Исследование завершено.');return s.freeze(a['id'],True)
def response(req,levels=None):
 # Synthetic parser fixture. Never used as an AI analysis or grading benchmark.
 stu=next(e for e in req['evidence'] if e['actor']=='student');run=next(e for e in req['evidence'] if e['kind']=='research_run');levels=levels or [3]*6
 return {'request_digest':req['request_digest'],'summary':'Синтетическая фикстура формата.','recommendations':['Проверить геометрию.'],'limitations':['Не является смысловой оценкой.'],'criteria':[{'criterion_id':f'K{i+1}','level':v,'rationale':'Проверяется сохранение уровня и цитат.','counterevidence':'Смысл не проверяется этим unit-тестом.','evidence':[{'event_id':stu['event_id'],'quote':stu['text']},{'event_id':run['event_id'],'quote':run['text'][:50]}]} for i,v in enumerate(levels)]}
class Base(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='dt-тест space-');self.root=Path(self.tmp.name);initialize(self.root,'commission','demo','teacher','2026-09-01T00:00:00+05:00');self.s=Service(self.root)
 def tearDown(self):self.s.close();self.tmp.cleanup()
 def graded(self,session='fixture',levels=None):
  b=fixture(self.s,session);a=self.s.analyze(b['id'],response(self.s.analysis_request(b['id']),levels));return b,a
 def roster(self):self.s.enroll('student1','Тестовый студент','DEMO','student@example.invalid')
class CaptureTests(Base):
 def test_no_capture_is_not_success(self):self.assertEqual(capture.doctor(self.root/'captured')['status'],'no_events')
 def test_unicode_exact(self):
  t='ёж Й № I²R\n  две строки\n';event(self.root,'UserPromptSubmit',prompt=t);self.assertEqual(capture.read(self.root/'captured')[0]['raw_payload']['prompt'],t)
 def test_repeat_delivery_preserved(self):
  event(self.root,'UserPromptSubmit',prompt='one');event(self.root,'UserPromptSubmit',prompt='one');es=capture.read(self.root/'captured');self.assertEqual(len(es),2);self.assertEqual(es[1]['duplicate_of_seq'],1)
 def test_model_args_not_execution(self):
  e=event(self.root,'PreToolUse',tool_input={'result':100});self.assertEqual(capture.normalized(e)['actor'],'model_tool_arguments')
  e=event(self.root,'PostToolUse',tool_response={'result':2});self.assertEqual(capture.normalized(e)['actor'],'executor')
 def test_tamper_detected(self):
  e=event(self.root,'UserPromptSubmit',prompt='one');e['raw_payload']['prompt']='fake'
  with self.assertRaises(TraceError):capture.validate([e])
 def test_bad_payload_not_stored(self):
  with self.assertRaises(TraceError):capture.record(b'{}',self.root/'captured')
  self.assertEqual(capture.read(self.root/'captured'),[])
 def test_jsonl_projection_recovers(self):
  event(self.root,'UserPromptSubmit',prompt='one');(self.root/'captured/events.jsonl').write_text('{broken');event(self.root,'Stop',last_assistant_message='two')
  self.assertEqual(len([json.loads(x) for x in (self.root/'captured/events.jsonl').read_text().splitlines()]),2)
 def test_concurrent_collectors(self):
  ps=[]
  for i in range(4):
   p=subprocess.Popen([sys.executable,str(ROOT/'dt.py'),'capture','--output',str(self.root/'captured')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE);p.stdin.write(canonical({'hook_event_name':'UserPromptSubmit','session_id':'fixture','test_fixture':True,'prompt':str(i)}).encode());p.stdin.close();ps.append(p)
  for p in ps:self.assertEqual(p.wait(timeout=20),0);p.stdout.close();p.stderr.close()
  es=capture.read(self.root/'captured');self.assertEqual(len(es),4);capture.validate(es)
 def test_probe_does_not_certify_synthetic(self):
  c={'baseline_count':1,'user_prompt':'TEST','assistant_reply':'OK','marker':'TEST'}
  event(self.root,'SessionStart');event(self.root,'UserPromptSubmit',prompt='TEST');event(self.root,'Stop',last_assistant_message='OK');event(self.root,'PostToolUse',tool_response={'stdout':'TEST-STDOUT','stderr':'TEST-STDERR','exit_code':3});r=check(c,capture.read(self.root/'captured'));self.assertEqual(r['session_start'],[1]);self.assertEqual(r['basic_probe'],'not_complete');self.assertTrue(r['synthetic_payload_detected'])
class AnalysisTests(Base):
 def setUp(self):super().setUp();self.b=fixture(self.s);self.req=self.s.analysis_request(self.b['id'])
 def test_no_canned_grade(self):
  with self.assertRaises(TraceError):self.s.analyze(self.b['id'],None)
 def test_score_arithmetic(self):
  a=self.s.analyze(self.b['id'],response(self.req,[4,3,2,4,1,3]));self.assertEqual(a['score'],'72.5')
 def test_null_is_not_zero(self):self.assertIsNone(self.s.analyze(self.b['id'],response(self.req,[4,3,None,4,1,3]))['score'])
 def test_false_quote_rejected(self):
  r=response(self.req);r['criteria'][0]['evidence'][0]['quote']='НЕСУЩЕСТВУЮЩИЙ ТЕКСТ'
  with self.assertRaises(TraceError):self.s.analyze(self.b['id'],r)
 def test_bad_digest_rejected(self):
  r=response(self.req);r['request_digest']='wrong'
  with self.assertRaises(TraceError):self.s.analyze(self.b['id'],r)
 def test_no_student_no_level(self):
  r=response(self.req)
  for c in r['criteria']:c['evidence']=c['evidence'][1:]
  with self.assertRaises(TraceError):self.s.analyze(self.b['id'],r)
 def test_total_score_cannot_be_supplied(self):
  r=response(self.req);r['score']=100
  with self.assertRaises(TraceError):self.s.analyze(self.b['id'],r)
 def test_boolean_not_level(self):
  r=response(self.req);r['criteria'][0]['level']=True
  with self.assertRaises(TraceError):self.s.analyze(self.b['id'],r)
 def test_reanalysis_reason(self):
  self.s.analyze(self.b['id'],response(self.req))
  with self.assertRaises(TraceError):self.s.analyze(self.b['id'],response(self.req,[2]*6))
 def test_idempotent_response(self):
  r=response(self.req);a=self.s.analyze(self.b['id'],r);b=self.s.analyze(self.b['id'],r);self.assertEqual(a['id'],b['id'])
 def test_no_expected_labels_in_request(self):self.assertNotIn('expected_levels',self.req);self.assertNotIn('analysis_candidates',self.req)
 def test_injected_bundle_rejected(self):
  b=copy.deepcopy(self.b['bundle']);b['captured_events'][0]['raw_payload']['prompt']='forged';b.pop('research_digest');b['research_digest']=digest(b)
  with self.assertRaises(TraceError):evidence.verify_bundle(b)
class WorkflowTests(Base):
 def setUp(self):super().setUp();self.roster()
 def test_end_to_end(self):
  b,a=self.graded();self.s.approve(a['id'],'Проверено',True);self.assertTrue(self.s.gradebook()['rows'][7]['transfer_allowed']);ap=self.s.appeal(b['id'],'Не согласен');self.assertFalse(self.s.gradebook()['rows'][7]['transfer_allowed']);n=self.s.decide(ap['id'],'teacher_override','Дополнительное обоснование',80,True);self.assertEqual(n['email']['status'],'not_sent_stub');self.assertEqual(self.s.gradebook()['rows'][7]['score'],'80.0');self.assertEqual(self.s.store.get('assessment',a['id'])['score'],'75.0')
  reports.individual(self.s,a['id'],self.root/'report.docx');reports.register(self.s,self.root/'register');reports.course_report(self.s,'student1',self.root/'course.docx');self.assertTrue(load(self.root/'course.json')['partial'])
 def test_teacher_confirmation_required(self):
  b,a=self.graded()
  with self.assertRaises(TraceError):self.s.approve(a['id'],'reason')
 def test_student_cannot_approve(self):
  b,a=self.graded();self.s.config['role']='student';self.s.config['actor']='student1'
  with self.assertRaises(TraceError):self.s.approve(a['id'],'reason',True)
 def test_demo_not_gradebook(self):
  b=fixture(self.s,mode='demo');a=self.s.analyze(b['id'],response(self.s.analysis_request(b['id'])))
  with self.assertRaises(TraceError):self.s.approve(a['id'],'reason',True)
 def test_no_stop_no_freeze(self):
  event(self.root,'UserPromptSubmit',prompt='Start');a=self.s.begin('student1','Тестовый студент','DEMO',8,'fixture')
  with self.assertRaises(TraceError):self.s.freeze(a['id'],True)
 def test_unlimited_attempts_best_whole_result(self):
  b,a=self.graded('one',[4,4,1,4,1,4]);self.s.approve(a['id'],'reason',True);b,a2=self.graded('two',[1,1,4,1,4,1]);self.s.approve(a2['id'],'reason',True);self.assertEqual(self.s.gradebook()['rows'][7]['score'],max([a['score'],a2['score']],key=float))
 def test_quota_preserves_work(self):
  with self.s.store.transaction():c=self.s.store.get('config','main');c['limit']=0;self.s.store.put('config','main',c)
  event(self.root,'UserPromptSubmit',prompt='Start');a=self.s.begin('student1','Тестовый студент','DEMO',8,'fixture')
  with self.assertRaises(TraceError):self.s.run(a['id'],ROOT/'models/copper_model.py',{})
  self.s.quota(1);self.s.run(a['id'],ROOT/'models/copper_model.py',{});self.assertEqual(self.s.quota()['grade_penalty'],0)
 def test_late_submission_preserves(self):
  self.s.config['environment']='pilot';event(self.root,'UserPromptSubmit',prompt='Start')
  with patch('digital_trace.service.now',return_value='2026-10-01T00:00:00+05:00'):a=self.s.begin('student1','Тестовый студент','DEMO',8,'fixture')
  event(self.root,'Stop',last_assistant_message='Done')
  with patch('digital_trace.service.now',return_value='2027-01-01T00:00:00+05:00'):
   with self.assertRaises(TraceError):self.s.freeze(a['id'],True)
  self.assertEqual(self.s.store.get('attempt',a['id'])['status'],'active')
 def test_roster_mismatch(self):
  b,a=self.graded();b['bundle']['attempt']['name']='Other'
  with self.assertRaises(TraceError):self.s.check_roster(b['bundle'])
 def test_nan_override_rejected(self):
  b,a=self.graded();ap=self.s.appeal(b['id'],'Reason')
  with self.assertRaises(TraceError):self.s.decide(ap['id'],'teacher_override','reason','NaN',True)
 def test_changed_execution_rejected(self):
  b,a=self.graded();rid=b['bundle']['runs'][0]['execution']['run_id'];(self.root/'runs'/rid/'stdout.txt').write_text('fake')
  with self.assertRaises(TraceError):exchange.export_packet(self.s,b['id'],self.root/'bad.zip')
 def test_zip_traversal(self):
  p=self.root/'bad.zip'
  with zipfile.ZipFile(p,'w') as z:z.writestr('../outside','x')
  with self.assertRaises(TraceError):exchange.import_packet(self.s,p)
 def test_import_and_appeal(self):
  b,a=self.graded();ap=self.s.appeal(b['id'],'Reason');p=self.root/'work.dt.zip';exchange.export_packet(self.s,b['id'],p)
  target=self.root/'teacher';initialize(target,'teacher','demo','teacher2','2026-09-01T00:00:00+05:00');t=Service(target)
  try:
   t.enroll('student1','Тестовый студент','DEMO');exchange.import_packet(t,p);self.assertEqual(exchange.import_packet(t,p)['status'],'already_imported');self.assertEqual(t.store.all('assessment'),[])
   with self.assertRaises(TraceError):t.decide(ap['id'],'confirm_existing','Reason',confirmed=True)
   t.analyze(b['id'],response(t.analysis_request(b['id'])));t.decide(ap['id'],'confirm_existing','Reason',confirmed=True);self.assertTrue(t.gradebook()['rows'][7]['transfer_allowed'])
  finally:t.close()
class AdditionalRegressionTests(Base):
 def test_run_utf8_and_failure_are_real(self):
  from digital_trace.runner import execute
  p=self.root/'utf8.py';p.write_text("import sys\nprint('ёж Й № I²R')\nprint('ошибка',file=sys.stderr)\nsys.exit(3)\n",encoding='utf-8')
  r=execute(self.root,p,{});self.assertEqual(r['status'],'failed');self.assertEqual(r['exit_code'],3);self.assertEqual((self.root/'runs'/r['run_id']/'stdout.txt').read_text(encoding='utf-8'),'ёж Й № I²R\n')
 def test_appeal_keeps_target_version(self):
  self.roster();b,a=self.graded();ap=self.s.appeal(b['id'],'Reason');self.s.analyze(b['id'],response(self.s.analysis_request(b['id']),[2]*6),'Second independent review');n=self.s.decide(ap['id'],'confirm_existing','Confirmed challenged version',confirmed=True);self.assertEqual(n['score'],'75.0')
 def test_open_appeal_does_not_fall_back_to_lower_grade(self):
  self.roster();b,a=self.graded('one',[4]*6);self.s.approve(a['id'],'Reason',True);b2,a2=self.graded('two',[2]*6);self.s.approve(a2['id'],'Reason',True);self.s.appeal(b['id'],'Reason');row=self.s.gradebook()['rows'][7];self.assertEqual(row['score'],'100.0');self.assertFalse(row['transfer_allowed'])

class InstallTests(Base):
 def test_idempotent_preserve_hooks(self):
  p=self.root/'.codex/hooks.json';save(p,{'hooks':{'Stop':[{'hooks':[{'type':'command','command':'echo other'}]}]}});install(self.root,self.root/'work space');r=install(self.root,self.root/'work space');self.assertEqual(r['status'],'unchanged');self.assertFalse(r['trusted']);self.assertEqual(load(p)['hooks']['Stop'][0]['hooks'][0]['command'],'echo other')
 def test_windows_quoting(self):
  c=command_for(r'C:\Program Files\Python\python.exe',r'C:\Учебный проект\dt.py',r'C:\Учебный проект\captured',True);self.assertIn('"C:\\Program Files\\Python\\python.exe"',c);self.assertNotIn('\\"',c)
 def test_all_materials(self):
  for n in range(1,16):self.assertGreater(evidence.lesson_info(n)['paragraph_count'],10)
 def test_cli_other_cwd(self):
  p=subprocess.run([sys.executable,str(ROOT/'dt.py'),'lesson','8'],cwd=self.root,capture_output=True,text=True,encoding='utf-8');self.assertEqual(p.returncode,0,p.stderr)
 def test_model_guards_geometry(self):
  spec=importlib.util.spec_from_file_location('copper',ROOT/'models/copper_model.py');m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
  for p in ({'rows_count':0},{'current_efficiency':1.1},{'current_per_bath_A':float('nan')},{'rows_count':True}):
   with self.assertRaises(ValueError):m.run_simulation('t',m.ElectrolysisInputs(**p))
  r=m.run_simulation('t',m.ElectrolysisInputs());self.assertTrue(r['geometry_feasible']);self.assertLessEqual(r['outputs']['actual_current_density_A_m2'],400);self.assertFalse(m.run_simulation('t',m.ElectrolysisInputs(use_shortened_bath_3m=True))['geometry_feasible'])
if __name__=='__main__':unittest.main()
