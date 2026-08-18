# CA-01 — Service Project contract root and dual-status lifecycle

**Статус:** `IN PROGRESS — DOMAIN POLICY UNIT-TESTED`

Первый кодовый инкремент реализует owner-approved OQ-CA-003/OQ-CA-020 как чистую server-side domain policy:

- точные enums `legal_status` и `execution_status`;
- исчерпывающие transition matrices;
- взаимные ограничения двух осей;
- атомарные связанные переходы без промежуточной недопустимой пары;
- единый `correlation_id` для двух audit events;
- обязательные reason/date/comment/evidence для Cancelled/Terminated и termination basis/document;
- Suspend/Resume с `suspended_from_status` для Launching и Active;
- терминальность и запрет `Suspended→Completed`;
- запрет нового исполнения для Cancelled/Terminated/Expired.

Код: [`contract_accounting/domain/lifecycle.py`](../../contract_accounting/domain/lifecycle.py).
Тесты: [`tests/test_lifecycle.py`](../../tests/test_lifecycle.py).

## Проверка инкремента

- `python -m compileall -q contract_accounting tests` — PASS;
- `python -m unittest discover -s tests -v` — PASS, 30 tests;
- `git diff --check` — PASS.

Это статические и unit-проверки чистого Python. Bench/Frappe runtime, миграция schema и DB-транзакции в этом инкременте не выполнялись.

## Граница этого инкремента

Модуль не зависит от Frappe и не пишет БД. Следующий шаг CA-01 должен добавить Frappe adapter, DocType schema, immutable audit DocType/event writer и server actions, которые применяют `TransitionResult` в одной транзакции. До появления adapter прямое редактирование полей в Frappe ещё не закрыто runtime-проверкой.
