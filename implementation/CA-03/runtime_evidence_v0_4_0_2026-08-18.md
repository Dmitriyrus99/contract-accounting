# CA-03 v0.4.0 bench runtime evidence — 2026-08-18

**Вердикт:** `PASS — MIGRATE / 19 RUNTIME TESTS / SCHEMA ROLLBACK-REINSTALL`.

## Зафиксированный вход

- repository/runtime CODE commit: `d85488b917f1cef75e210a086f48628b62a77563`;
- app: `contract_accounting 0.4.0`;
- Frappe `15.118.0`, ERPNext `15.119.2`;
- runtime Python `3.11.14`, MariaDB `10.11.14`;
- wheel: `contract_accounting-0.4.0-py3-none-any.whl`, 80,263 bytes;
- wheel SHA-256: `823a9a09c31dafe3c62b870e0a3c97722e7219c49e6e5dbbad3210344f439951`.

Стенд: disposable `ca01.localhost`, отдельная user-owned MariaDB `127.0.0.1:3317` и cache Redis `127.0.0.1:13000`. Production/legacy site и business data не использовались; secrets/site configuration не читались.

## Выполненные gates

- `python -m unittest discover -s tests -v` — `67 tests`, `OK`;
- `python -m compileall -q contract_accounting tests` — PASS;
- `git diff --check` — PASS;
- PEP 517 wheel build — PASS;
- migrate на существующую v0.3.0 schema — PASS, model sync 18/18;
- foreground full-app suite — `Ran 19 tests in 58.440s`, `OK`;
- controlled uninstall/install/migrate — PASS, удалены и созданы заново 18 DocType;
- post-reinstall suite — `Ran 19 tests in 70.929s`, `OK`;
- final full-app regression after tightening both Accepted and Rejected decisions to Completed+Approved — `Ran 19 tests in 59.897s`, `OK`.

Runtime suite запускается со штатным `--skip-test-records`: versioned tests сами создают scoped Company/Customer/Project/Object/System/Requirement/Obligation/Schedule/Visit/Request/File evidence.

## Подтверждённые CA-03 сценарии

1. Повторная generation создаёт 1 Schedule + 1 primary Visit, затем возвращает те же IDs с `created=0`; reverse trace содержит исходный Obligation.
2. Cancelled primary не восстанавливается молча; явная replacement команда создаёт ровно одну replacement запись и повторяется идемпотентно.
3. Completion разделяет planned/actual dates. PM approval отвергается без completed checklist и физического private File evidence; Accepted выставляет billing eligibility, а последующая silent rewrite блокируется.
4. Service Request существует без Schedule, выводит Customer/Service Object, отвергает foreign Object System и переходит в Resolved только с actual dates/result/resolution/File evidence.
5. Все 15 CA-01/02 regression tests продолжают проходить.

## Исправленные runtime-дефекты

- initial File test fixture ссылалась на несуществующий путь, затем использовала невалидное image content; заменена штатным `save_file` с валидным disposable PNG — production File guard не ослаблялся;
- первоначальный review snapshot включал технические child-row metadata, меняющиеся после ORM reload; snapshot нормализован по business fields checklist/evidence и повторно проверен acceptance/immutability тестом.

## Controlled rollback и ограничения

`uninstall-app contract_accounting --yes --no-backup` удалил все 18 custom DocType/table, затем install+migrate восстановили schema и suite. `--no-backup` относится только к disposable site.

Full backup restore, concurrent multi-worker race/load test, legacy backfill, assigned-contractor/portal permissions, UAT/legal/operations sign-off и production deployment не выполнялись.
