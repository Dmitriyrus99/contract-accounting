# CA-01 — Service Project contract root and dual-status lifecycle

**Статус:** `IN PROGRESS — DOMAIN POLICY UNIT-TESTED`

Первый кодовый инкремент реализует owner-approved OQ-CA-003/OQ-CA-020 как чистую server-side domain policy:

- точные enums `legal_status` и `execution_status`;
- исчерпывающие transition matrices;
- взаимные ограничения двух осей;
- атомарные связанные переходы без промежуточной недопустимой пары;
- единый `correlation_id` для двух audit events;
- транзакционный application service с row-lock persistence port и rollback при ошибке state/audit;
- обязательные reason/date/comment/evidence для Cancelled/Terminated и termination basis/document;
- Suspend/Resume с `suspended_from_status` для Launching и Active;
- терминальность и запрет `Suspended→Completed`;
- запрет нового исполнения для Cancelled/Terminated/Expired.

Код: [`contract_accounting/domain/lifecycle.py`](../../contract_accounting/domain/lifecycle.py).
Транзакционная граница: [`contract_accounting/application/lifecycle_service.py`](../../contract_accounting/application/lifecycle_service.py).
Тесты: [`tests/test_lifecycle.py`](../../tests/test_lifecycle.py) и [`tests/test_lifecycle_service.py`](../../tests/test_lifecycle_service.py).

## Проверка инкремента

- `python -m compileall -q contract_accounting tests` — PASS;
- `python -m unittest discover -s tests -v` — PASS, 35 tests;
- `git diff --check` — PASS.

Это статические и unit-проверки чистого Python. Bench/Frappe runtime, миграция schema и DB-транзакции в этом инкременте не выполнялись.

## Граница этого инкремента

Модули не зависят от Frappe и не пишут БД. Application service определяет обязательный persistence contract (`lock_state` → `save_state` → `append_audit_events`) и не выполняет implicit commit. Следующий шаг CA-01 должен добавить Frappe adapter, DocType schema, immutable audit DocType/event writer и server actions поверх этой границы. До появления adapter прямое редактирование полей в Frappe ещё не закрыто runtime-проверкой.
