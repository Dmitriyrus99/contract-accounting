# CA-01 bench runtime evidence — 2026-08-18

**Вердикт:** `PASS — INSTALL / MIGRATE / 8 RUNTIME TESTS / SCHEMA ROLLBACK-REINSTALL`.

Проверка выполнена на новом disposable site `ca01.localhost` в отдельном WSL bench `/home/rus/contract-accounting-bench`. Существующий `ferum_custom` repository/site не использовался. Production data и production credentials не затрагивались.

## Зафиксированный вход

- repository commit: `fae65814433a0c44c383500bddab7f19ca73d2d4` (`main`, clean tree);
- runtime clone: `/home/rus/contract-accounting-runtime-source`, тот же clean commit;
- app/distribution: `contract_accounting 0.1.0`;
- Frappe `15.118.0`, commit `9b8d265b27a1dfb11c7aef21a533a127e14a0a5a`;
- ERPNext `15.119.2`, commit `d707cb1e0e808fa6699d29a2bbaf9310983e94ac`;
- runtime Python `3.12.3`; MariaDB `10.11.14`;
- final wheel: `contract_accounting-0.1.0-py3-none-any.whl`, SHA-256 `7f16b10d25bf19e848f7895771d9d7b6e2d0770f8af95baba5acfbac47ca6d7a`;
- wheel listing: 26 entries; оба DocType JSON и `fixtures/role.json` присутствуют.

Frappe выводит предупреждение, что MariaDB 10.11 новее указанной им проверенной границы 10.8. Это не скрыто и не трактуется как certification указанной версии БД.

## Установка и миграция

1. Новый site создан на отдельном user-owned MariaDB instance `127.0.0.1:3317`.
2. ERPNext Setup Wizard baseline создан без production data: `Russia`, `RUB`, тестовая Company и стандартные leaf Customer Group/Territory.
3. `bench --site ca01.localhost install-app contract_accounting` — PASS.
4. `bench --site ca01.localhost migrate` — PASS, включая model sync `contract_accounting` и `after_migrate` hooks.
5. Site apps после установки: `frappe 15.118.0`, `erpnext 15.119.2`, `contract_accounting 0.1.0`.

Для migrate был запущен bench cache Redis. Queue port `11000` уже обслуживался локальным Redis-процессом; queue jobs в acceptance-сценарии не запускались. Поэтому evidence подтверждает schema migration и синхронные DB-тесты, но не утверждает изоляцию/проверку background workers.

## Runtime suite

Финальная foreground-команда:

```bash
bench --site ca01.localhost run-tests \
  --app contract_accounting \
  --module contract_accounting.contract_accounting.doctype.ferum_service_project.test_ferum_service_project
```

Результат: exit code `0`, `Ran 8 tests in 15.101s`, `OK` после controlled reinstall. Все восемь versioned сценариев из [runtime_test_plan.md](runtime_test_plan.md) прошли.

Важная особенность harness: промежуточные неуспешные `bench run-tests` также возвращали process exit code `0`, хотя stdout содержал `FAILED`. Поэтому verdict определяется одновременно exit code и финальными строками `Ran 8 tests` + `OK`, а не exit code в одиночку.

Runtime-прогоны выявили и устранили:

- неверное distribution name для Frappe app — commit `12086072c91180bbc5d7e2aaa635179ad07cc9e4`;
- фикстуры с несуществующими Company/Customer links и group-only masters — commits `bc02264`, `7d6fd32`;
- запись timezone-aware значения с offset в MariaDB `Datetime` — commit `2eb76f0`;
- дублирующий физический index `correlation_id` — commit `fae6581`.

Standalone regression suite после исправлений: `python -m unittest discover -s tests -v` — PASS, 52 tests. `python -m compileall -q contract_accounting tests` и `git diff --check` — PASS.

## Физическая schema после reinstall

- custom DocType: `Ferum Service Project`, `Ferum Lifecycle Audit Event` — оба присутствуют;
- `DocField`: 41 строка для двух DocType;
- `DocPerm`: 30 строк для двух DocType;
- `Patch Log` с `contract_accounting`: 0 строк; schema создаётся model sync/hooks, data patches отсутствуют;
- Service Project indexes: `PRIMARY(name)`, `modified(modified)`, unique `unique_company_contract_number_contract_date(company, contract_number, contract_date)`;
- Lifecycle Audit indexes: `PRIMARY(name)`, `modified(modified)`, `occurred_at(occurred_at)`, `correlation_id(correlation_id)`, `service_project_occurred_at_index(service_project, occurred_at)`.

## Controlled schema rollback

На disposable site выполнены dry-run и затем:

```bash
bench --site ca01.localhost uninstall-app contract_accounting --yes --no-backup
```

Uninstall удалил оба DocType/table и Module Def; `list-apps` после rollback содержал только Frappe/ERPNext, а обе проверки DocType вернули `False`. Затем app повторно установлен, schema inventory восстановлен без дублирующего correlation index, и runtime suite повторно завершился `8/8 OK`.

`--no-backup` выбран только для disposable acceptance site. Полный backup/restore rehearsal site и перенос/возврат business records не выполнялись и этим evidence не подтверждаются.

## Credential handling

При диагностике первого зависшего `new-site` одна автоматически сгенерированная одноразовая Administrator credential попала в локальный process output. Она не относилась к production, была немедленно признана скомпрометированной и инвалидирована принудительным пересозданием site с новым сгенерированным значением. Credential-bearing строки `bench.log` заменены redaction marker; проверка показала `credential_lines_remaining=0`. Секретные значения и site configuration в repository не записывались.

## Оставшиеся границы CA-01

- перевод Amendment, Execution Stage, Security, Financial Plan и Object/System links на Service Project root — `PENDING`;
- background worker/queue E2E — `NOT RUN`;
- полный backup restore — `NOT RUN`;
- UAT, legal и finance sign-off — `NOT RUN`;
- production deployment — `NOT AUTHORIZED / NOT RUN`.
