# CA-14 implementation traceability — v0.15.0

CA-14 содержит 14 exact req-id. Таблица не изменяет исходную `07_traceability.csv` и не присваивает blanket PASS инкременту.

| Requirement | Реализованное CODE/runtime evidence | Вердикт v0.15.0 |
| --- | --- | --- |
| `TCA-B-31-01` | Service Project metadata содержит Tab Break «Запуск» и HTML view | CODE/runtime PASS |
| `TCA-B-31-02` | ordered stage rows показывают completed/total и progress percent | CODE/runtime PASS |
| `TCA-B-31-03` | stage раскрывается до exact source-linked step rows | CODE/runtime PASS |
| `TCA-B-31-04` | каждый step показывает base status и independent overdue badge | CODE/runtime PASS |
| `TCA-B-31-05` | step row содержит due/warning/escalation; UI показывает due или explicit No deadline | CODE PASS; reference Launch positive deadline UAT OPEN |
| `TCA-B-32-01` | standard Page «Мои действия» выдаёт user/role/ToDo-assigned actionable steps | CODE/runtime PASS |
| `TCA-B-32-02` | exact due_at выводится из source Step и проверен absolute deadline fixture | CODE/runtime PASS |
| `TCA-B-32-03` | derived Overdue badge и stable first ordering проверены explicit as_of | CODE/runtime PASS |
| `TCA-B-32-04` | standard Page «Запуск проектов» выдаёт permitted Not Started/Launching projects | CODE/runtime PASS |
| `TCA-B-32-05` | Launch projection вычисляет overdue по Step due_at | CODE PASS; positive overdue Launch runtime/UAT OPEN |
| `TCA-B-32-06` | Blocked Step и Failed Gate выдают concrete conditions/failed criteria | CODE/runtime PASS |
| `TCA-B-32-07` | open contractor-doc step без Approved Assignment даёт contractor-not-confirmed flag | PARTIAL: CODE/runtime branch; explicit contractor_required SSOT OPEN |
| `TCA-B-32-08` | reference customer/mobilization Waiting External codes дают waiting_customer | PARTIAL: CODE branch; counterparty/expected-response positive runtime OPEN |
| `TCA-B-32-09` | PERSONNEL_READY выдаёт exact MG-CA-015 credentials blocker | FAIL-CLOSED PARTIAL; positive readiness запрещён MG-CA-015 |

## Точно подтверждённые acceptance scenarios

- одна операция не дублируется как независимые Step и ToDo rows;
- future Planned stages не загрязняют текущую очередь;
- non-permitted user не получает action project и denied на Launch API;
- overdue/today/upcoming/unscheduled и blocked/waiting dimensions сортируются воспроизводимо;
- Service Project Launch tab, My Actions и Project Launches установлены repeated migrate;
- stage раскрывается до step status/deadline/source;
- Failed Gate возвращает непустые exact criteria и blocking source;
- credentials readiness не выдаёт ложный PASS при открытом MG-CA-015;
- никаких новых persistent task/cache/ledger entities не создано.

Не присваивается PASS browser/UAT, complete role/export/report permission matrix, high-volume pagination/performance/race, automatic notifications, explicit contractor-required model, structured external counterparty response, positive personnel readiness или production deployment.
