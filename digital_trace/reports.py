from __future__ import annotations
import csv
from pathlib import Path
from docx import Document
from docx.shared import Pt,Inches,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from .common import *
from .assessment import RUBRIC

def document(title,intro):
 d=Document();s=d.sections[0];s.page_width=Inches(8.5);s.page_height=Inches(11);s.top_margin=s.bottom_margin=Inches(.75);s.left_margin=s.right_margin=Inches(.8)
 for name in ('Normal','Title','Heading 1','Heading 2','Subtitle'):
  st=d.styles[name];st.font.name='Calibri';st.font.color.rgb=RGBColor(0,0,0)
 d.styles['Normal'].font.size=Pt(11);d.styles['Normal'].paragraph_format.space_after=Pt(6)
 d.add_heading(title,0);d.add_paragraph(intro);return d

def table(d,headers,rows):
 t=d.add_table(rows=1,cols=len(headers));t.style='Table Grid'
 for cell,value in zip(t.rows[0].cells,headers):cell.text=str(value)
 for cell in t.rows[0].cells:
  tcPr=cell._tc.get_or_add_tcPr();sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'E5EDF5');tcPr.append(sh)
  for run in cell.paragraphs[0].runs:run.bold=True
 trpr=t.rows[0]._tr.get_or_add_trPr();trpr.append(OxmlElement('w:tblHeader'))
 for row in rows:
  for cell,value in zip(t.add_row().cells,row):cell.text=str(value)
 for row in t.rows:
  for cell in row.cells:
   for p in cell.paragraphs:p.paragraph_format.space_after=Pt(4);p.paragraph_format.space_before=Pt(4)
 return t

def individual(service,aid,out):
 a=service.store.get('assessment',aid);b=service.store.get('submission',a['submission_id'])['bundle'];service.owner(b['attempt']['student'])
 d=document('Аналитический отчёт о работе студента',f"{b['attempt']['name']} · {b['attempt']['group']} · Занятие {b['attempt']['lesson']}. Рекомендуемый балл: {a['score'] if a['score'] is not None else 'недостаточно свидетельств'}.")
 if any(e['raw_payload'].get('synthetic_commission_example') for e in b['captured_events']):d.add_paragraph('Демонстрационный вымышленный диалог. Расчётные запуски исполнены программой. Это не проверка работы реального студента.')
 d.add_paragraph(a['response']['summary'])
 table(d,['Критерий','Вес','Уровень'],[(r['id']+' '+r['name'],r['weight'],str(c['level']) if c['level'] is not None else 'Нет данных') for r,c in zip(RUBRIC,a['response']['criteria'])])
 for r,c in zip(RUBRIC,a['response']['criteria']):
  d.add_heading(r['id']+' '+r['name'],1);d.add_paragraph(c['rationale']);d.add_paragraph('Что ограничивает вывод: '+c['counterevidence'])
  for ref in c['evidence']:d.add_paragraph(ref['event_id']+': «'+ref['quote']+'»')
 d.add_heading('Рекомендации',1)
 for x in a['response']['recommendations']:d.add_paragraph(x,style='List Bullet')
 d.add_heading('Границы заключения',1)
 for x in a['response']['limitations']:d.add_paragraph(x)
 d.add_paragraph('Смысловой анализ выполнен моделью текущего чата. Независимость контекста не заявляется. Программа проверила точные цитаты и арифметику; релевантность суждений требует рассмотрения преподавателем.')
 d.add_paragraph('Основание: '+a['research_digest']);d.add_paragraph('Оценка: '+aid)
 out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);d.save(out);return {'path':str(out.resolve())}

def safe_csv(v):
 s='' if v is None else str(v)
 return "'"+s if s.startswith(('=','+','-','@','\t','\r')) else s

def register(service,out,group=None):
 data=service.gradebook(group);out=Path(out);out.mkdir(parents=True,exist_ok=True);save(out/'gradebook.json',data)
 fields=['student','name','group','lesson','score','status','transfer_allowed','assessment_id']
 for name,rows in [('gradebook.csv',data['rows']),('ready_for_transfer.csv',[r for r in data['rows'] if r['transfer_allowed']])]:
  with (out/name).open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.writer(f);w.writerow(fields);w.writerows([[safe_csv(r[k]) for k in fields] for r in rows])
 d=document('Ведомость дисциплины','Лучший действующий результат по каждому занятию после подтверждения преподавателем. При открытой апелляции перенос результата блокируется. Среда: '+data['environment']+'. Автоматическая отправка в Платонус не выполняется.')
 table(d,['Студент','№','Балл','Состояние'],[(r['student'],r['lesson'],r['score'] or '—',r['status']) for r in data['rows']]);d.save(out/'gradebook.docx');return {'directory':str(out.resolve()),'ready_rows':sum(r['transfer_allowed'] for r in data['rows'])}

def course_report(service,sid,out):
 service.teacher();student=service.store.get('roster',sid);rows=[r for r in service.gradebook()['rows'] if r['student']==sid];good=[r for r in rows if r['transfer_allowed']]
 d=document('Индивидуальный отчёт по курсу',student['name']+' · '+student['group']+'. Подтверждено занятий: '+str(len(good))+' из 15. '+('Промежуточный отчёт.' if len(good)<15 else 'Итоговый отчёт.'))
 d.add_paragraph('Рекомендации относятся к наблюдаемым учебным действиям. Это не психологический профиль и не прогноз профессиональной пригодности.')
 recommendations=[]
 for row in good:
  a=service.store.get('assessment',row['assessment_id']);d.add_heading('Занятие '+str(row['lesson']),1);d.add_paragraph(a['response']['summary']);d.add_paragraph('Действующий результат: '+row['score']+'. Основание: '+a['id'])
  for rec in a['response']['recommendations']:
   if rec not in recommendations:recommendations.append(rec)
 d.add_heading('Направления дальнейшей работы',1)
 if recommendations:
  for rec in recommendations:d.add_paragraph(rec,style='List Bullet')
  d.add_paragraph('После выпуска используйте эти направления для учебного или производственного проекта с верификацией модели и портфолио воспроизводимых экспериментов. Выбор темы уточните с наставником по мере накопления практических данных.')
 else:d.add_paragraph('Подтверждённых работ пока нет. Персональные выводы не сформированы.')
 d.add_paragraph('Открытые апелляции и отсутствующие результаты не использованы как доказательства недостаточного понимания. Оценка курса будет полнее после завершения всех 15 занятий.')
 out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);d.save(out);save(out.with_suffix('.json'),{'student':sid,'completed':len(good),'partial':len(good)<15,'recommendations':recommendations,'rows':rows});return {'path':str(out.resolve()),'completed':len(good)}
