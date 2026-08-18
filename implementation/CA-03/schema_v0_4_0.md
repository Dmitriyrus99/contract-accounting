# CA-03 schema evidence — v0.4.0

**Статус:** `STATIC + BENCH RUNTIME VERIFIED AT d85488b`.

**Дата:** 2026-08-18.

## Физическая модель

| DocType | Тип | Назначение |
| --- | --- | --- |
| `Ferum Maintenance Schedule` | parent | одна immutable плановая строка Obligation/period key |
| `Ferum Maintenance Visit` | parent | плановый и фактический выезд, review/acceptance |
| `Ferum Visit Checklist Item` | child | snapshot выполненных проверок |
| `Ferum Execution Evidence` | child | typed Link на стандартный ERPNext/Frappe `File` |
| `Ferum Service Request` | parent | самостоятельное внеплановое обращение/поручение |

После clean install приложение содержит 18 custom DocType. CA-03 добавляет 79 DocField и 12 DocPerm. Legacy options `Ferum Contract`/`Ferum Project Contract Link` отсутствуют.

## Schedule и generation idempotency

Physical unique `(contract_obligation, period_key)` — `ca_sched_period_uniq`. `period_key` обязан совпадать с ISO planned date. Schedule копирует immutable project/object/system/work-type context из Active Obligation и хранит planned date, window и due date.

POST-команда `generate_planned_visits` блокирует строку Obligation `FOR UPDATE`, использует CA-02 recurrence engine и для каждого occurrence создаёт:

1. ровно один Schedule;
2. ровно один primary Visit с unique `generation_key`;
3. обратную ссылку Schedule→generated Visit.

Повторный вызов возвращает те же IDs и нулевые created counts. Cancelled primary Visit не создаётся заново. Единственная replacement coverage создаётся отдельной POST-командой и защищена unique `replacement_for`.

## Maintenance Visit

Плановая provenance (`service_project`, obligation, schedule, project/service object, system, period key, planned date/window, generation key) immutable.

Execution FSM: `Planned → In Progress|Cancelled`, `In Progress → Completed|Cancelled`. Completion требует actual start/end, work result и report. Review FSM: `Pending → Approved|Rejected`, `Rejected → Pending`; approval доступен только для Completed Visit с полностью заполненным checklist и File evidence. После Approved business snapshot checklist/evidence/result/report не меняется.

Acceptance FSM: `Pending → Accepted|Rejected`, `Rejected → Pending`. Accepted требует Completed + Approved review + checklist + evidence. Accepted Visit immutable, сервер выставляет `billing_eligible=1`; это не создаёт accounting/billing records.

Schedule автоматически получает `Completed` при завершении Visit. Reverse query возвращает Obligation/Schedule/все primary+replacement Visits и start deviation days.

## Service Request

Service Request не содержит Schedule link. Обязательны Service Project и Project Object; Service Object и Customer выводятся сервером и проверяются против Project/Object. Object System и Obligation optional, но при наличии обязаны совпадать с контекстом.

FSM: `Open → Assigned|In Progress|Cancelled`, `Assigned → In Progress|Cancelled`, `In Progress → Resolved|Cancelled`, `Resolved → Closed|In Progress`. Resolution требует actual start/end, resolution, work result и File evidence. Non-customer source требует стабильный source reference до появления typed Finding/Document links.

## Не закрыто этой схемой

- Finding links — CA-04;
- Project Document/report registry — CA-05;
- Act/UPD/Sales Invoice/Payment reverse trace — CA-06/07;
- record-level assigned contractor/customer portal permissions — CA-08;
- Holiday List/working-day/SLA timestamps — CA-09;
- legacy Visit/Schedule backfill на combined app/site — отдельный migration rehearsal.
