# CA-05 v0.6.0 bench runtime evidence — 2026-08-18

**Вердикт:** `PASS — MIGRATE / 29 RUNTIME TESTS / SCHEMA ROLLBACK-REINSTALL`.

## Зафиксированный вход

- repository/runtime CODE commit: `0c8546d3c71d3b857cf7bfcda0527cbaeaf58425`;
- app: `contract_accounting 0.6.0`;
- Frappe `15.118.0`, ERPNext `15.119.2`;
- runtime Python `3.11.14`, MariaDB `10.11.14`, Redis `7.0.15`;
- wheel: `contract_accounting-0.6.0-py3-none-any.whl`, 112,290 bytes;
- wheel SHA-256: `93ede80aa95a387ffadb58c80a4de79e1bf980ab2d0773cd54260b04804f8dce`.

Стенд: disposable `ca01.localhost`, отдельная user-owned MariaDB `127.0.0.1:3317` и cache Redis `127.0.0.1:13000`. Production/legacy site и business data не использовались; secrets/site configuration не читались.

## Выполненные gates

- `python -m unittest discover -s tests -v` — `77 tests`, `OK`;
- `python -m compileall -q contract_accounting tests` — PASS;
- JSON parse и `git diff --check` — PASS;
- Ruff — SKIPPED: executable/package отсутствует в локальном WSL runtime;
- PEP 517 wheel через `uv build --wheel` — PASS;
- migrate v0.5.0 → v0.6.0 и повторный migrate на exact CODE commit — PASS;
- foreground full-app suite до clean reinstall — `Ran 29 tests in 97.771s`, `OK`;
- controlled uninstall/install/migrate — PASS, удалены и созданы заново 24 DocType;
- post-reinstall full-app suite — `Ran 29 tests in 92.906s`, `OK`;
- после final fail-closed link hardening — CA-05 `5/5`, затем full app `Ran 29 tests in 94.120s`, `OK`.

Runtime suite запускается со штатным `--skip-test-records`: versioned tests создают scoped Company/Customer/Service Project/Object/Project Document/File/Event records.

## Подтверждённые CA-05 сценарии

1. Digital Copy проходит Missing → Uploaded → Verified, не меняя Original; Original проходит Not Requested → Requested → Received → Archived, не меняя Digital Copy.
2. Каждый успешный переход создаёт отдельный immutable event с actor/time, correlation ID, evidence и snapshot; direct CRUD статусов отклоняется.
3. `Not Required` по каждой оси отклоняется без отдельного нормативного basis и evidence File. Карточка не становится Active, если нет принятой цифровой или бумажной формы.
4. Received/Archived требуют evidence; server ставит actor/time, Archived требует storage location.
5. Accepted binary и audit evidence File нельзя удалить; карточку после перехода удалить нельзя.
6. Source выводит Service Project/Object context; foreign context, запрещённый billing DocType и target без Service Project adapter отклоняются.
7. Физический unique version key блокирует дубли одной версии документа.
8. Все 24 CA-01…04 regression tests продолжают проходить.

## Дефекты, найденные до финального PASS

- `.pdf` test fixture с текстовым содержимым был корректно отклонён встроенной Frappe PDF-проверкой; fixture переведён на текстовый тип;
- одинаковый test payload вызывал File hash deduplication между транзакционными тестами; каждый fixture получил уникальный hash;
- финальный fail-closed review запретил generic related/billing targets без allowlist и проверяемого Service Project adapter.

## Ограничения

Legacy projection из Billing Artifact/attached File не запускалась: owner утвердил reset/recreate непродукционных тестовых данных. CA-06/07 billing adapter, CA-11 BPM links, concurrent race/load, UAT, legal/operations sign-off и production deployment не выполнялись.
