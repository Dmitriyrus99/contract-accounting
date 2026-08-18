# CA-06 v0.7.0 bench runtime evidence — 2026-08-18

**Вердикт:** `PASS — MIGRATE / 35 RUNTIME TESTS / CLEAN UNINSTALL-INSTALL-MIGRATE`.

## Зафиксированный вход

- repository/runtime CODE commit: `5b2d79a5c4d4f3350d598ea797a6fbac0e592cf5`;
- app: `contract_accounting 0.7.0`;
- Frappe `15.118.0`, ERPNext `15.119.2`;
- Bench Python `3.11.14`, MariaDB `10.11.14`, Redis `7.0.15`;
- wheel: `contract_accounting-0.7.0-py3-none-any.whl`, 136,202 bytes;
- wheel SHA-256: `8d2f35a2de368a25da8748ddd250524054bf5e22002ae8542f1a8eb92debb446`.

Стенд: disposable `ca01.localhost`, отдельная user-owned MariaDB `127.0.0.1:3317` и cache Redis `127.0.0.1:13000`. Production/legacy site и business data не использовались; secrets/site configuration не читались.

## Выполненные gates

- `python -m unittest discover -s tests` — `83 tests`, `OK`;
- `python -m compileall -q contract_accounting` — PASS;
- JSON parse и `git diff --check` — PASS;
- Ruff — SKIPPED: executable/package отсутствует в локальном WSL runtime;
- PEP 517 wheel через `uv build --wheel` — PASS;
- migrate v0.6.0 → v0.7.0 — PASS;
- targeted CA-06 suite — `Ran 6 tests in 26.315s`, `OK`;
- foreground full-app suite до clean reinstall — `Ran 35 tests in 117.442s`, `OK`;
- controlled uninstall/install/migrate — PASS; удалены/созданы заново 28 DocType;
- после reinstall подтверждены 28 DocType и `Sales Invoice-ferum_service_project`;
- post-reinstall full-app suite — `Ran 35 tests in 118.220s`, `OK`.

Runtime suite запускалась со штатным `--skip-test-records`: versioned tests создают scoped Company/Customer/Service Project/Object/Obligation/Visit/Request/Sales Invoice/File records.

## Подтверждённые CA-06 сценарии

1. Selector включает accepted billing-eligible Visit и resolved completed Request с evidence и исключает claimed source.
2. Output создаёт canonical immutable child snapshots; физический unique claim не допускает один execution result в двух активных closing documents.
3. Final и Signed artifact получают version/current history, File hash и активную Project Document projection.
4. Issue без Final, прямое изменение Output/basis и update/delete Event отклоняются fail-closed.
5. Создание/отмена Output не пишет GL/Payment Ledger; активный Output блокирует cancel стандартного Invoice, cancelled Output освобождает его.
6. Supersede сохраняет старый basis, переводит его claim в Reversed и создаёт связанный Correction draft с новым active claim.
7. Все 29 CA-01…05 regression tests продолжают проходить.

## Дефекты, найденные до финального PASS

- Frappe user defaults заполняли контекст нового Output до controller validation; context creation изменён на безусловный server derivation из Service Project, а post-insert identity остаётся immutable;
- Datetime/JSON/number значения child snapshot после MariaDB reload имели иное runtime-представление; сравнение и hash переведены на canonical typed payload.

## Ограничения

PDF/УПД generator, ЭДО/КЭП, Purchase Invoice, concurrent race/load, бухгалтерский UAT, legal/operations sign-off и production deployment не выполнялись.
