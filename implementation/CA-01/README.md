# CA-01 — Service Project contract root and dual-status lifecycle

**Статус:** `IN PROGRESS — FRAPPE SCHEMA/ADAPTER STATIC VERIFIED; BENCH NOT RUN`

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
Schema evidence: [schema_v0_1_0.md](schema_v0_1_0.md).
Bench plan и versioned runtime suite: [runtime_test_plan.md](runtime_test_plan.md).
Тесты: [`tests/test_lifecycle.py`](../../tests/test_lifecycle.py), [`tests/test_lifecycle_service.py`](../../tests/test_lifecycle_service.py), [`tests/test_frappe_lifecycle_adapter.py`](../../tests/test_frappe_lifecycle_adapter.py) и [`tests/test_frappe_schema.py`](../../tests/test_frappe_schema.py).

## Проверка инкремента

- `python -m compileall -q contract_accounting tests` — PASS;
- `python -m unittest discover -s tests -v` — PASS, 52 tests;
- JSON parse Service Project, Lifecycle Audit Event и Role fixture — PASS;
- isolated PEP 517 wheel build — PASS, `contract_accounting-0.1.0-py3-none-any.whl`; Frappe metadata, DocType JSON и Role fixture присутствуют внутри wheel;
- `git diff --check` — PASS.

Это статические и unit-проверки Python, fake-Frappe adapter и versioned JSON schema. Bench/Frappe runtime, установка app, миграция schema и реальные DB-транзакции в этом инкременте не выполнялись.

## Граница этого инкремента

Domain/application модули не зависят от Frappe. Adapter реализует обязательный persistence contract (`lock_state` → `save_state` → `append_audit_events`) без implicit commit, а controller содержит direct-edit guard. Следующий шаг CA-01 — установить app на отдельный ERPNext v15 test site, выполнить runtime tests и затем добавить Amendment/Stage/Security/Financial Plan links. До bench-проверки direct-edit guard и транзакционный rollback считаются реализованными в CODE, но не подтверждёнными runtime evidence.

Versioned `FrappeTestCase` suite уже присутствует, но имеет статус `PRESENT / NOT RUN`; наличие тестового файла не является runtime PASS.
