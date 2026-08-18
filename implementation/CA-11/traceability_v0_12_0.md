# CA-11 grouped implementation traceability — v0.12.0

CA-11 содержит 169 req-id. Таблица группирует их по исходным секциям CSV; она не заменяет построчную `07_traceability.csv` и не присваивает blanket PASS всей группе.

| Requirement group | Реализованное CODE/runtime evidence | Вердикт v0.12.0 |
| --- | --- | --- |
| `TCA-B-01-*` | универсальный template step: action/input/responsible/deadline/evidence/approver/failure/dependencies | PARTIAL: core PASS; concrete regulations OPEN |
| `TCA-B-02-*` | Process Template `process_type` и один/несколько Project Process на Service Project | PARTIAL: engine PASS; named recurring/launch/completion processes не настроены |
| `TCA-B-03-*` | девять отдельных parent DocType Template/Stage/Step/Process/Stage/Step/Gate/Evidence/Event | CODE/runtime PASS |
| `TCA-B-04-*` | code/version/status/effective/supersedes/change note; publish freeze; v1 instance unchanged after v2 | CODE/runtime PASS |
| `TCA-B-05-*` | step action, input, responsible, timing, evidence и failure fields | CODE/schema PASS |
| `TCA-B-06-*` | optional Approved One-time Requirement selector + safe match rule + instance Link | PARTIAL: CODE PASS; positive runtime Requirement fixture OPEN |
| `TCA-B-07-*` | responsible role/user snapshot и standard ToDo adapter | PARTIAL: explicit/default user PASS; role-to-user resolver OPEN |
| `TCA-B-08-*` | None/Absolute/Relative, trigger, offset/unit/calendar, due/warning/escalation | PARTIAL: explicit snapshot runtime PASS; production MG-CA-013 OPEN |
| `TCA-B-09-*` | append-only Process Event и event trace для generation/transitions/evidence/stage | PARTIAL: internal events PASS; external event ingestion OPEN |
| `TCA-B-10-*` | JSON Logic allowlist for scope/condition/activation/exit; no eval; missing context fail-closed | CODE/pure-test PASS; full branch catalog OPEN |
| `TCA-B-11-*` | CA-02 Contract Requirement assessment/routing reused; approved one-time selector | PARTIAL: integration CODE present; dedicated runtime branch OPEN |
| `TCA-B-12-*` | technology-neutral action/step type fields | PARTIAL: generic types present; catalog semantics/configuration OPEN |
| `TCA-B-20-*` | distinct Waiting External, reason, timeout_action snapshot; overdue does not replace base state | PARTIAL: FSM PASS; timeout scheduler/action delivery OPEN |
| `TCA-B-24-*` | exact completion evidence enum, type/source allowlist, snapshot/hash/actor/time, validated completion runtime | PARTIAL: framework PASS; case templates for agreement/shipment/tracking/inventory OPEN |
| `TCA-B-26-*` | Stage Gate evaluates blocking steps; Failed Gate blocks next stage; Passed Gate opens next stage | CODE/runtime PASS |
| `TCA-B-27-*` | exact criticality enum plus independent blocking Check | CODE/schema/runtime PASS |
| `TCA-B-28-*` | false completion blocked by evidence; Not Applicable requires reason | CODE/pure-test PASS; dedicated runtime NA fixture OPEN |
| `TCA-B-29-*` | exact base statuses excluding persisted Overdue; Waiting External ≠ Blocked; derived display status | CODE/runtime PASS under approved OQ-CA-012 |
| `TCA-B-30-*` | due/warning/escalation calculated; explicit overdue projection | PARTIAL: calculation PASS; Department Head/Director delivery OPEN |
| `TCA-B-33-*` | explicit idempotent generation from published version and requirement revision | PARTIAL: command PASS; automatic project-start event/template selection OPEN |
| `TCA-B-34-*` | step model can represent individual work | OPEN/PARTIAL: no governed ad-hoc individual-step command |
| `TCA-B-35-*` | Process Step has Contract Requirement and Contract Obligation links | OPEN/PARTIAL: Requirement link generation exists; obligation-driven generation/population OPEN |
| `TCA-B-37-*` | approved physical parent topology, server permissions/typed writers and indexes | CODE/runtime PASS for core topology |
| `TCA-B-38-*` | declarative JSON/typed fields, no Python expression storage or hard-coded business template | CODE/pure-test PASS |
| `TCA-B-39-*` | Requirement→Template→Process→Stage→Step→Evidence→Gate vertical slice | PARTIAL: core formula PASS; configured processes/automation/UAT OPEN |

## Точно подтверждённые acceptance scenarios

- published v1 graph нельзя изменить; v2 не меняет существующий v1 instance;
- один exact generation key создаёт ровно один process, две stages и два steps;
- explicit Moscow calendar/holiday даёт due 2026-08-20, warning 2026-08-19, escalation 2026-08-24;
- Completed без evidence отклоняется; Draft evidence недостаточно; Validated exact type разрешает completion;
- один Ready blocking step даёт Failed Gate и stage остаётся Active;
- завершение blocking step даёт Passed Gate, закрывает ToDo и активирует следующий stage;
- direct mutation instance и forged Process Event отклоняются;
- `as_of` показывает Overdue, не меняя persisted base `Ready`.

Не присваивается PASS семистадийному launch, Inspection/personnel gates, Billing Cycle, automatic external triggers, scheduler/notifications, escalation delivery, ad-hoc steps, performance/load/race, UAT/sign-off или production deployment.
