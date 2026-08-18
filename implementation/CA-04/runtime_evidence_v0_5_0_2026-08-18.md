# CA-04 v0.5.0 bench runtime evidence — 2026-08-18

**Вердикт:** `PASS — MIGRATE / 24 RUNTIME TESTS / SCHEMA ROLLBACK-REINSTALL`.

## Зафиксированный вход

- repository/runtime CODE commit: `5bc0bc91c1d0a39cf9ce7db68dd9f45cc9dd49f5`;
- app: `contract_accounting 0.5.0`;
- Frappe `15.118.0`, ERPNext `15.119.2`;
- runtime Python `3.11.14`, MariaDB `10.11.14`, Redis `7.0.15`;
- wheel: `contract_accounting-0.5.0-py3-none-any.whl`, 96,355 bytes;
- wheel SHA-256: `644cda07304ab306310dd06343eb4e2a0fdee1db2a3fce366f0430a22710d438`.

Стенд: disposable `ca01.localhost`, отдельная user-owned MariaDB `127.0.0.1:3317` и cache Redis `127.0.0.1:13000`. Production/legacy site и business data не использовались; secrets/site configuration не читались.

## Выполненные gates

- `python -m unittest discover -s tests -v` — `72 tests`, `OK`;
- `python -m compileall -q contract_accounting tests` — PASS;
- JSON parse и `git diff --check` — PASS;
- PEP 517 wheel build — PASS;
- migrate с v0.4.0 на окончательную v0.5.0 schema — PASS, model sync 21/21;
- foreground full-app suite до clean reinstall — `Ran 24 tests in 92.573s`, `OK`;
- controlled uninstall/install/migrate — PASS, удалён и создан заново 21 DocType;
- post-reinstall full-app suite — `Ran 24 tests in 89.511s`, `OK`.

Runtime suite запускается со штатным `--skip-test-records`: versioned tests сами создают scoped Company/Customer/Project/Object/System/Requirement/Obligation/Schedule/Visit/Finding/Request/File/Photo Evidence.

## Подтверждённые CA-04 сценарии

1. Finding создаётся из Visit, сервер выводит и замораживает project/object/system/source snapshot; Service Request автоматически не создаётся. Произвольный source и отсутствующий Inspection fail-closed.
2. Confirmation требует decision/responsible/due date. Exception report вычисляет open critical, overdue и отсутствие решения.
3. Resolution/close блокируются без evidence и actor/dates. Accepted Photo Evidence с реальным File hash удовлетворяет gate; Closed Finding и Accepted photo immutable.
4. Явная Finding→Service Request команда идемпотентна и не изменяет source/provenance Finding.
5. Execution link отвергает запрещённый DocType и foreign project context; повторный event key не создаёт дубль.
6. Все 19 CA-01…03 regression tests продолжают проходить.

## Дефекты, найденные до финального PASS

- первый migrate удалил `Ferum Finding Execution Link` как orphan: child module не экспортировал импортируемый Frappe controller class. Класс добавлен, повторные migrate/install не содержат orphan deletion;
- первый runtime прогон дал 23 PASS + 1 timezone fixture error: due date строилась от OS `datetime.now`, а не от Frappe `found_at`. Fixture привязана к сохранённому source timestamp; production due-date guard не ослаблялся;
- exact traceability review выявил отсутствующий физический `Ferum Photo Evidence`; добавлен parent DocType с File hash/review/provenance, затем выполнены новые migrate, clean reinstall и полные suite.

Замечание evidence parser: `bench run-tests` вернул process code 0 даже для предварительного `FAILED (errors=1)`, поэтому PASS фиксировался только по финальной строке `OK`, а не по exit code.

## Ограничения

Inspection/CA-12, assigned-contractor/portal scoping/CA-08, approved work-order adapter, legacy candidate conversion, full backup restore, concurrent race/load test, UAT/legal/operations sign-off и production deployment не выполнялись.
