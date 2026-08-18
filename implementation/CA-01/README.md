# CA-01 — Service Project contract root and dual-status lifecycle

**Статус:** `CA-01 CODE COMPLETE — SCHEMA v0.2.0 BENCH VERIFIED; MANUAL/DOWNSTREAM GATES PENDING`

Первый кодовый инкремент реализует owner-approved OQ-CA-003/OQ-CA-020 как чистую server-side domain policy:

- точные enums `legal_status` и `execution_status`;
- исчерпывающие transition matrices;
- взаимные ограничения двух осей;
- атомарные связанные переходы без промежуточной недопустимой пары;
- единый `correlation_id` для двух audit events;
- транзакционный application service с row-lock persistence port и rollback при ошибке state/audit;
- Frappe v15 app scaffold, Service Project schema и immutable Lifecycle Audit Event;
- guarded whitelisted transition/Suspend/Resume commands и versioned role fixture;
- обязательные reason/date/comment/evidence для Cancelled/Terminated и termination basis/document;
- Suspend/Resume с `suspended_from_status` для Launching и Active;
- терминальность и запрет `Suspended→Completed`;
- запрет нового исполнения для Cancelled/Terminated/Expired.

Код: [`contract_accounting/domain/lifecycle.py`](../../contract_accounting/domain/lifecycle.py).
Транзакционная граница: [`contract_accounting/application/lifecycle_service.py`](../../contract_accounting/application/lifecycle_service.py).
Frappe adapter: [`contract_accounting/infrastructure/frappe_lifecycle.py`](../../contract_accounting/infrastructure/frappe_lifecycle.py).
Schema evidence: [schema_v0_2_0.md](schema_v0_2_0.md) и исторический [v0.1.0](schema_v0_1_0.md).
Bench plan и versioned runtime suite: [runtime_test_plan.md](runtime_test_plan.md).
Runtime evidence: [v0.2.0](runtime_evidence_v0_2_0_2026-08-18.md) и исторический [v0.1.0](runtime_evidence_2026-08-18.md).
Implementation traceability: [traceability_v0_2_0.md](traceability_v0_2_0.md).
Тесты: [`tests/test_lifecycle.py`](../../tests/test_lifecycle.py), [`tests/test_lifecycle_service.py`](../../tests/test_lifecycle_service.py), [`tests/test_frappe_lifecycle_adapter.py`](../../tests/test_frappe_lifecycle_adapter.py) и [`tests/test_frappe_schema.py`](../../tests/test_frappe_schema.py).

## Проверка инкремента

- `python -m compileall -q contract_accounting tests` — PASS;
- `python -m unittest discover -s tests -v` — PASS, 56 tests;
- JSON parse Service Project, Lifecycle Audit Event и Role fixture — PASS;
- isolated PEP 517 wheel build — PASS, `contract_accounting-0.2.0-py3-none-any.whl`; Frappe metadata, 10 DocType JSON и Role fixture присутствуют внутри wheel;
- `git diff --check` — PASS.
- отдельный ERPNext v15 site: install + migrate — PASS;
- Frappe/MariaDB runtime suite — PASS, 11/11;
- controlled app schema uninstall/reinstall и повторный suite — PASS.

Точные версии, SHA, wheel hash, schema inventory, rollback и границы проверки записаны в [runtime evidence](runtime_evidence_2026-08-18.md).

## Граница этого инкремента

Domain/application модули не зависят от Frappe. Adapter реализует обязательный persistence contract (`lock_state` → `save_state` → `append_audit_events`) без implicit commit. Amendment/Stage/Security/Financial Plan и Object/System direct links добавлены без второго Contract SSOT; их guards и schema uninstall/reinstall подтверждены на disposable bench.

Versioned `FrappeTestCase` suite имеет подтверждённый статус `PASS 11/11` только для зафиксированного стенда и commit из runtime evidence; это не заменяет downstream CA-02…07, UAT/legal/finance или production deployment.
