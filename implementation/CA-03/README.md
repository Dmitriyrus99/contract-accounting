# CA-03 — Plan-to-fact execution

**Статус:** `CA-03 CORE CODE COMPLETE — SCHEMA v0.4.0 BENCH VERIFIED; BILLING/FINDING/CONTRACTOR GATES PENDING`

Инкремент материализует проверяемую цепочку:

`Service Project → Contract Requirement → Contract Obligation → Maintenance Schedule(period_key) → Maintenance Visit → checklist/File evidence → PM review → acceptance`.

Отдельный `Ferum Service Request` сохраняет внеплановый путь и выводит Customer/Service Object из Project Object/Service Project без зависимости от Schedule.

Код генератора и команд: [`execution.py`](../../contract_accounting/api/execution.py).
Schedule: [`ferum_maintenance_schedule.py`](../../contract_accounting/contract_accounting/doctype/ferum_maintenance_schedule/ferum_maintenance_schedule.py).
Visit: [`ferum_maintenance_visit.py`](../../contract_accounting/contract_accounting/doctype/ferum_maintenance_visit/ferum_maintenance_visit.py).
Service Request: [`ferum_service_request.py`](../../contract_accounting/contract_accounting/doctype/ferum_service_request/ferum_service_request.py).

Схема и invariants: [schema_v0_4_0.md](schema_v0_4_0.md).
Runtime evidence: [runtime_evidence_v0_4_0_2026-08-18.md](runtime_evidence_v0_4_0_2026-08-18.md).
Implementation traceability: [traceability_v0_4_0.md](traceability_v0_4_0.md).

## Подтверждённые проверки

- standalone unit/schema suite: `67 tests`, `OK`;
- compileall, JSON parse и `git diff --check`: PASS;
- PEP 517 wheel v0.4.0: PASS;
- ERPNext v15 migrate: PASS;
- foreground Frappe suite: `19/19`, `OK`;
- controlled uninstall/install/migrate и повторный suite: `19/19`, `OK`.

## Граница инкремента

CA-03 не создаёт Act/UPD/Sales Invoice/Payment и не пишет в GL: эти связи остаются CA-06/07. Finding появится в CA-04, Project Document — CA-05, record-level contractor/portal scoping — CA-08, SLA/Holiday engine — CA-09. `billing_eligible` — только guarded execution projection, не бухгалтерский документ и не основание само по себе.
