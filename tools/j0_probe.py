"""Prepare/check a real platform probe; never inject events."""
import argparse,json,secrets,sys,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from digital_trace import capture
from digital_trace.common import load,save

def check(c,events):
 capture.validate(events);tail=events[c['baseline_count']:];ps=[e for e in tail if e['hook_event_name']=='UserPromptSubmit' and e['raw_payload'].get('prompt')==c['user_prompt']];sessions={e['session_id'] for e in ps}
 tail=[e for e in tail if e['session_id'] in sessions];starts=[e['seq'] for e in events if e['session_id'] in sessions and e['hook_event_name']=='SessionStart']
 answers=[e['seq'] for e in tail if e['hook_event_name']=='Stop' and e['raw_payload'].get('last_assistant_message')==c['assistant_reply']];outputs=[]
 for e in tail:
  if e['hook_event_name']!='PostToolUse':continue
  t=json.dumps(e['raw_payload'].get('tool_response'),ensure_ascii=False)
  if c['marker']+'-STDOUT' in t and c['marker']+'-STDERR' in t and re.search(r'(?:exit_code|returncode|exitCode)["\s:]+3\b|(?:exited with code|exit code)\s*:?\s*3\b',t,re.I):outputs.append(e['seq'])
 synthetic=any(e['raw_payload'].get('test_fixture') or e['raw_payload'].get('synthetic_commission_example') for e in events if e['session_id'] in sessions)
 return {'basic_probe':'passed' if ps and answers and outputs and starts and not synthetic else 'not_complete','exact_prompt':[e['seq'] for e in ps],'exact_reply':answers,'session_start':starts,'executor_stdout_stderr_exit3':outputs,'synthetic_payload_detected':synthetic,'full_J0':'not_certified; interruption, fork, compaction, long dialogues still need actual tests','external_attestation':False}

def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','check']);p.add_argument('--workspace',type=Path,required=True);a=p.parse_args();f=a.workspace/'j0_control.json'
 if a.action=='prepare':
  if f.exists():raise SystemExit('Control already exists; use check, do not keep changing marker')
  m='DTJ0-'+secrets.token_hex(6).upper();r={'marker':m,'baseline_count':len(capture.read(a.workspace/'captured')),'user_prompt':m+'\nСохрани точно: ёж, Й, №, I²R.\nОтветь ровно: '+m+'-ОТВЕТ','assistant_reply':m+'-ОТВЕТ','execution_prompt':'Выполни Python: stdout '+m+'-STDOUT, stderr '+m+'-STDERR, exit code 3. Не имитируй результат.'};save(f,r)
 else:r=check(load(f),capture.read(a.workspace/'captured'));save(a.workspace/'j0_report.json',r)
 print(json.dumps(r,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
