# Команды для помощника и разработчика

Пользователь общается обычным языком. ИИ выполняет команды в локальной папке.
Параметр `--workspace PATH` ставится ПЕРЕД подкомандой. ID берутся из реального
вывода предыдущих команд; в примерах ниже ID — обозначение, не буквальный ID.

```
python dt.py --workspace workspace init --role commission --environment demo --actor commission --semester-start 2026-09-01T00:00:00+05:00
python dt.py --workspace workspace doctor
python dt.py lesson 8
python dt.py --workspace workspace enroll --student demo_student --name "Иванов Демонстрационный" --group DEMO
python dt.py --workspace workspace begin --student demo_student --name "Иванов Демонстрационный" --group DEMO --lesson 8 --session OBSERVED_SESSION --mode individual
python dt.py --workspace workspace run ATTEMPT --code models/copper_model.py --input experiment.json
python dt.py --workspace workspace freeze ATTEMPT --confirmed
python dt.py --workspace workspace analysis-request SUBMISSION
python dt.py --workspace workspace analyze SUBMISSION --response semantic_response.json
python dt.py --workspace workspace report ASSESSMENT --out reports/student.docx
python dt.py --workspace workspace approve ASSESSMENT --reason "Рассмотрены исходные свидетельства" --confirmed
python dt.py --workspace workspace appeal SUBMISSION --reason "Объяснение студента"
python dt.py --workspace workspace decide APPEAL --decision teacher_override --score 88 --reason "Заключение преподавателя" --confirmed
python dt.py --workspace workspace gradebook --group DEMO --out reports/gradebook
python dt.py --workspace workspace course-report demo_student --out reports/course.docx
python dt.py --workspace workspace semester demo_student
```

Для демонстрационного вымышленного примера, отдельно от реального журнала:
`python tools/demo_prepare.py --out NEW_DEMO_FOLDER`.
Скрипт готовит запрос анализа и четыре реальных запуска. Он не ставит оценок.
После него анализирующая модель читает request.json и создаёт осмысленный ответ.

Для передачи:
`export SUBMISSION --out OUTBOX/work.dt.zip` в студенческой рабочей папке;
`import PATH/work.dt.zip` или `sync --inbox INBOX` в преподавательской.
Сначала преподаватель регистрирует roster через enroll. Студенческие оценки
не превращаются в преподавательские автоматически. Нужен новый анализ.
При разборе входящей апелляции подтверждается преподавательская рекомендация,
если исходный идентификатор студенческого анализа не существует в его workspace.
Решение явно сохраняется в notice; почта остаётся not_sent_stub.

`resume ATTEMPT --session OBSERVED_SESSION` связывает новый захваченный чат.
`quota` показывает локальные запуски; `quota --add N` — действие местного оператора.
`list attempt|submission|assessment|result|appeal|notice|roster` возвращает ID.
Нельзя выдавать локальный quota за управление тарифом ChatGPT.

Данные рабочего места — SQLite и каталоги runs/submissions/analysis/outbox.
Перед обновлением сохраните папку целиком при закрытом приложении либо используйте
штатный SQLite backup. Не переносите открытую SQLite-базу через облачную синхронизацию.
Не редактируйте журнал задним числом. Ошибку оформляйте новым результатом с причиной.
