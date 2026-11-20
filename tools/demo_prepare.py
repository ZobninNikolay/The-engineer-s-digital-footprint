"""Fictional commission example. NEVER a live hook test or a real student record."""
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from digital_trace.common import *
from digital_trace import capture
from digital_trace.store import initialize
from digital_trace.service import Service

DIALOGUE=[
('Нужно исследовать цех электролиза на 15 т меди в сутки. Ограничение ширины здания 12 м. Не прошу один ответ: сравним две компоновки и выявим ограничения методички. Сначала выполни базовую модель с реальной длиной электродного пакета.','Базовая программа исполнена. Сохраняем код, параметры и выходные данные; геометрическая проверка отделена от производительности.'),
('Теперь изменим число рядов с двух на один. Хочу проверить гипотезу, что ограничение ширины можно выполнить ценой большей длины. Не выбирай вариант только по числу ванн.','Выполнен второй запуск с одним рядом. Сравниваем ширину, площадь и кратность числа ванн числу рядов.'),
('В методичке встречается длина ванны 3 м. Она выглядит несовместимой с количеством электродов. Давай проверим этот вариант отдельно и уменьшим теплопотери до 7000 Вт. Если теплоотдача меняет знак, нулевой расход нагрева не означает отсутствие охлаждения.','Третий запуск показывает несовместимость укороченной ванны с электродным пакетом и избыток джоулева тепла. Такой вариант нельзя принимать как готовое проектное решение.'),
('Для однорядного варианта поднимем плотность тока в шинах до 1,5 А/мм². Проверим экономию меди. Но уменьшение массы ещё не доказывает экономический оптимум: надо учесть сопротивление, нагрев и стоимость потерь.','Четвёртый запуск показывает уменьшение расчётной массы шин. Электрическое сопротивление и температурный режим в текущей модели ещё не верифицированы.'),
('Мой вывод: один ряд вписывается в 12 м, но площадь увеличилась. Укороченную ванну 3 м отклоняю до пересмотра электродного пакета. Выбор шин пока предварительный: нужно добавить сопротивление и годовые потери, затем провести чувствительность к цене меди и электроэнергии. По этой модели не объявляю промышленный проект проверенным.','Исследовательский цикл завершён. Модель имеет явные границы применимости, а дальнейшая работа сформулирована по результатам экспериментов.')]
PARAMS=[{}, {'rows_count':1}, {'rows_count':1,'use_shortened_bath_3m':True,'heat_loss_per_bath_W':7000}, {'rows_count':1,'j_busbar_econ_A_mm2':1.5}]

def prepare(root):
 root=Path(root)
 if root.exists():raise TraceError('Use a NEW demo directory. Existing data will not be overwritten.')
 initialize(root,'commission','demo','commission','2026-09-01T00:00:00+05:00');s=Service(root);s.enroll('demo_student','Иванов Демонстрационный','DEMO','student@example.invalid')
 def emit(kind,**extra):capture.record(canonical({'hook_event_name':kind,'session_id':'fictional-commission','synthetic_commission_example':True,**extra}).encode(),root/'captured')
 emit('SessionStart');a=None
 for i,(user,assistant) in enumerate(DIALOGUE):
  emit('UserPromptSubmit',prompt=user)
  if a is None:a=s.begin('demo_student','Иванов Демонстрационный','DEMO',8,'fictional-commission')
  if i<4:s.run(a['id'],ROOT/'models/copper_model.py',PARAMS[i])
  emit('Stop',last_assistant_message=assistant)
 sub=s.freeze(a['id'],True);req=s.analysis_request(sub['id']);save(root/'DEMO.json',{'submission_id':sub['id'],'request_digest':req['request_digest'],'fictional_dialogue':True,'actual_python_runs':4});s.close();return root/'analysis'/sub['id']/'request.json'
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(prepare(a.out))
