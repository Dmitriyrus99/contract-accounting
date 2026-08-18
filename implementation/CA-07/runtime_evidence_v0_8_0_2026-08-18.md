# CA-07 v0.8.0 bench runtime evidence — 2026-08-18

**Вердикт:** `PASS — MIGRATE / 41 RUNTIME TESTS / CLEAN UNINSTALL-INSTALL-MIGRATE`.

## Зафиксированный вход

- repository/runtime CODE commit: `f7217f3ca9fca90217353044ecd822a603141c3f`;
- app: `contract_accounting 0.8.0`;
- Frappe `15.118.0`, ERPNext `15.119.2`;
- Bench Python `3.11.14`, MariaDB `10.11.14`, Redis `7.0.15`;
- wheel: `contract_accounting-0.8.0-py3-none-any.whl`, 157,052 bytes;
- wheel SHA-256: `f11d4944b1f86a34d9b6954dd78b9d98ab7f286853782d4f3a753d9c5c7bab33`.

Стенд: disposable `ca01.localhost`, отдельная user-owned MariaDB `127.0.0.1:3317` и cache Redis `127.0.0.1:13000`. Production/legacy site и business data не использовались; secrets/site configuration не читались.

## Выполненные gates

- `python -m unittest discover -s tests` — `89 tests`, `OK`;
- `python -m compileall -q contract_accounting` — PASS;
- parse 32 JSON и `git diff --check` — PASS;
- Ruff `E4,E7,E9,F,I` для CA-07-owned modules — PASS;
- repository-wide тот же Ruff scope — OPEN: 32 `I001` и 1 `F401`, всего 33 baseline debt items вне CA-07-owned modules;
- PEP 517 wheel через `uv build --wheel` — PASS;
- migrate v0.7.0 → v0.8.0 — PASS;
- targeted CA-07 suite — `Ran 6 tests in 36.431s`, `OK`;
- foreground full-app suite до clean reinstall с `--skip-test-records` — `Ran 41 tests in 155.512s`, `OK`;
- controlled uninstall/install/migrate — PASS; удалены/созданы заново 31 DocType;
- после reinstall подтверждены 31 DocType и custom fields `Sales Invoice-ferum_service_project`, `Purchase Invoice-ferum_service_project`;
- post-reinstall full-app suite с `--skip-test-records` — `Ran 41 tests in 148.429s`, `OK`.

Первый запуск полного runner без `--skip-test-records` — FAIL до app tests: стандартная ERPNext fixture не нашла `Gender: Female`. Этот запуск не засчитан как PASS. Versioned app tests создают scoped Company/Customer/Project/Invoice/Payment/cost records самостоятельно, поэтому оба квалификационных full-app запуска выполнены со штатным `--skip-test-records`.

## Подтверждённые CA-07 сценарии

1. Standard SI 120000 и PE 60000 дают paid/outstanding/overdue по 60000; costs 30000 + 40000 + 6000 дают 76000, profit 44000 и profitability 36.666667%.
2. Opening SI 5000 увеличивает AR до 65000, но не recognized/invoiced revenue; cancel возвращает AR к 60000.
3. Один submitted PI не может одновременно иметь Approved Material Expense и Contractor Settlement; foreign-project PI отклоняется.
4. Повторный rebuild сохраняет fingerprint и суммы и не меняет количество Sales/Purchase Invoice, Payment Entry или GL Entry; прямая mutation/delete Summary отклоняется.
5. Reconciliation обнаруживает намеренно устаревший cache, а portfolio rollup точно совпадает с суммой Service Project.
6. Активная cost classification блокирует cancel PI, её Cancelled status освобождает PI; Settlement нельзя закрыть без полного standard Payment Entry.
7. Все 35 CA-01…06 regression tests продолжают проходить.

## Дефекты, найденные до финального PASS

- runtime invoice fixture не сохраняла backdated posting date без `set_posting_time`; fixture исправлена без ослабления ERPNext validation;
- opening Sales Invoice ошибочно использовал P&L account; fixture переведена на standard Temporary Opening account;
- trace map не сохранял явную `Other` classification обычного Purchase Invoice; read-model исправлена через deterministic fallback entry.

## Ограничения

Положительный VAT tax-row сценарий, отдельный tool/rent bucket, legacy before/after reconciliation, после-commit worker observation, concurrent race/load, Finance UAT, legal/operations sign-off и production deployment не выполнялись.
