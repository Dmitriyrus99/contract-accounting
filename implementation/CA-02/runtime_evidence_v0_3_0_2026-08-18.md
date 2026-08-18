# CA-02 v0.3.0 bench runtime evidence — 2026-08-18

**Вердикт:** `PASS — MIGRATE / 15 RUNTIME TESTS / SCHEMA ROLLBACK-REINSTALL`.

## Зафиксированный вход

- repository/runtime CODE commit: `b52f61b5ee35dfc8495a3f5354be8fc44f3f2908`;
- app: `contract_accounting 0.3.0`;
- Frappe `15.118.0`, ERPNext `15.119.2`;
- runtime Python `3.11.14`, MariaDB `10.11.14`;
- wheel: `contract_accounting-0.3.0-py3-none-any.whl`, 59,315 bytes;
- wheel SHA-256: `4b424fb0396f0884a301d148379453ff7da5174df432bdf4f246729880477908`.

Стенд: disposable `ca01.localhost`, отдельная user-owned MariaDB `127.0.0.1:3317` и cache Redis `127.0.0.1:13000`. Production/legacy `ferum_custom` site и business data не использовались; site configuration и DB credentials не читались.

## Выполненные gates

- `python -m unittest discover -s tests -v` — `63 tests`, `OK`;
- `python -m compileall -q contract_accounting tests` — PASS;
- `git diff --check` — PASS;
- PEP 517 wheel build — PASS;
- `bench --site ca01.localhost migrate` — PASS, model sync 13/13 и `after_migrate` выполнены;
- `bench --site ca01.localhost run-tests --app contract_accounting --skip-test-records` — `Ran 15 tests in 49.851s`, `OK`;
- после controlled uninstall/install/migrate тот же suite — `Ran 15 tests in 47.011s`, `OK`.

`--skip-test-records` выбран намеренно: versioned tests сами создают scoped Company/Customer/Project/Object/System/Requirement/Obligation, а глобальная Frappe auto-fixture graph на этом clean site до тестов пыталась создать отсутствующий стандартный Gender `Female`. Первый full-app запуск без этого флага не считается PASS.

## Подтверждённые CA-02 runtime-сценарии

1. Approved Applicable Requirement с recurring route активирует Obligation; два preview вызова дают одинаковый результат и не создают records.
2. One-time Process Step Requirement не может быть источником recurring Obligation.
3. Object System другого Service Object отвергается.
4. Active effective versions не пересекаются, active identity immutable, active record не удаляется.
5. Все 11 CA-01 lifecycle/amendment/object/stage/security/financial regression tests продолжают проходить.

## Исправленный дефект миграции

Первый migrate остановился с MariaDB `1059`: автоматически полученное имя четырёхколоночного Requirement index было длиннее 64 символов. CODE исправлен явным именем `ca_req_source_idx`; повторный migrate, clean reinstall и suite прошли. Физический index содержит `service_project`, `source_document_reference`, `source_clause`, `requirement_type` в указанном порядке.

## Controlled rollback

На disposable site выполнен `uninstall-app contract_accounting --yes --no-backup`: удалены все 13 custom DocType/table и Module Def. Затем `install-app contract_accounting` и migrate создали 13/13 DocType заново, после чего suite повторно завершился `15/15 OK`.

`--no-backup` применён только к disposable site. Full backup restore, legacy data migration, worker/queue E2E, UAT/legal/operations sign-off и production deployment этим evidence не подтверждены.
