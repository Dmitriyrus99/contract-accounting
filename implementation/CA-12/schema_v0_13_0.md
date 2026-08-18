# CA-12 physical schema and command contract — v0.13.0

**Статус:** `SEVEN-STAGE LAUNCH GRAPH + INSPECTION CORE BENCH VERIFIED AT 5fbb9a3`.

## Reference Launch graph

`ensure_reference_launch_template()` создаёт или fail-closed проверяет Published `FERUM-LAUNCH` v1. Graph содержит 7 stage codes и 25 step codes:

| Sequence | Stage code | Title | Steps |
| --- | --- | --- | ---: |
| 1 | `INITIATION` | Initiation | 4 |
| 2 | `CUSTOMER_ONBOARDING` | Customer Contact | 3 |
| 3 | `EXECUTION_MODEL` | Execution Scheme | 3 |
| 4 | `PERSONNEL_READINESS` | Personnel Readiness | 1 |
| 5 | `SITE_MOBILIZATION` | Mobilization | 7 |
| 6 | `INITIAL_INSPECTION` | Initial Inspection | 5 |
| 7 | `HANDOVER_TO_OPERATIONS` | Launch Readiness | 2 |

Published graph использует CA-11 parent topology. Installer не создаёт process instances и не меняет историю проектов. `generate_reference_launch_process` требует role, project с `execution_status=Launching`, explicit generation key и exact confirmation token; assessment — отдельная read-only команда.

## Inspection DocType

| DocType | Назначение | Ключевой invariant |
| --- | --- | --- |
| `Ferum Inspection` | parent inspection fact | unique idempotency key; context выводится из Project Object; lifecycle только typed commands |
| `Ferum Inspection Checklist Item` | system/component result | unique item code внутри Inspection; Defect/Observation требует title и detail |
| `Ferum Inspection Team Member` | inspection team | unique `(member_doctype, member)`; allowlist User/Employee/Contractor Worker |

Основные immutable links/snapshots parent: Service Project, Project Process, Process Step, Project Object, Service Object, Object System, inspection type/date, `template_version_snapshot`, `system_inventory_snapshot`, `report_snapshot`, report Project Document и idempotency key.

Inspection lifecycle: `Planned → In Progress → Completed → Approved`; `Planned/In Progress → Cancelled`. Start требует непустой inventory snapshot. Completion требует результат каждого checklist item, evidence File с exact content hash, outcome, summary и report. Approved fact неизменяем, кроме отдельного customer flow `Pending → Sent → Approved|Rejected`.

Contractor Worker остаётся в утверждённой физической модели, но добавление его в team fail-closed до MG-CA-015.

## Typed commands и outputs

- `create_inspection_from_step`: только Ready/In Progress action типа Inspection, exact idempotency context и непустой template-version snapshot;
- `start_inspection`: фиксирует server timestamp и inventory snapshot;
- `complete_inspection`: создаёт structured report, draft Project Document, Findings и Photo Evidence в одной транзакции;
- `approve_inspection`: разрешён manager/RP/System Manager и требует Finding для каждого Defect/Observation;
- `record_customer_inspection_status`: отдельная отправка/фиксация решения заказчика;
- `cancel_inspection`, `get_inspection_trace`: управляемая отмена и source-linked trace.

Повтор completion/approval не создаёт дубли. Finding description сохраняет item code, system, component, question и result detail. Photo Evidence ссылается на exact attached File.

## BPM integration

Process Evidence типа `Inspection` валидирует существующий `Approved Ferum Inspection` с exact Process Step. `PERSONNEL_READY` нельзя перевести ни в Completed, ни в Not Applicable до MG-CA-015. Завершение последней Launch stage требует project `Launching`, роль RP/System Manager и проводит переход в `Active` через `contract_accounting.api.lifecycle.change_status`, сохраняя CA-01 audit.
