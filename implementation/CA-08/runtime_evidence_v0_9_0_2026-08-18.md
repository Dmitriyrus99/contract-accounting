# CA-08 v0.9.0 bench runtime evidence — 2026-08-18

**Вердикт:** `PASS FOR ASSIGNMENT/COMMERCIAL SCOPE — MIGRATE / 47 TESTS / CLEAN REINSTALL; MG-CA-015 BLOCKED`.

## Зафиксированный вход

- repository/runtime CODE commit: `9af7a671b4016335c0ffe5ac3a8a55eddcf7312f`;
- app: `contract_accounting 0.9.0`;
- Frappe `15.118.0`, ERPNext `15.119.2`;
- Bench Python `3.11.14`, MariaDB `10.11.14`, Redis `7.0.15`;
- wheel: `contract_accounting-0.9.0-py3-none-any.whl`, 176,548 bytes;
- wheel SHA-256: `55ac0bcc3c314c6156bc09a9ea21decdbc91ca56ef8737cbae8364343239d915`.

Стенд: disposable `ca01.localhost`, отдельная user-owned MariaDB `127.0.0.1:3317` и cache Redis `127.0.0.1:13000`. Production/legacy site и business/PII data не использовались; secrets/site configuration не читались.

## Выполненные gates

- `python -m unittest discover -s tests` — `96 tests`, `OK`;
- `python -m compileall -q contract_accounting` — PASS;
- parse 36 JSON и `git diff --check` — PASS;
- Ruff `E4,E7,E9,F,I` для CA-08-owned modules — PASS;
- repository-wide тот же Ruff scope — OPEN: 32 `I001` и 1 `F401`, всего 33 baseline debt items вне CA-08-owned modules;
- PEP 517 wheel через `uv build --wheel` — PASS;
- migrate v0.8.0 → v0.9.0 — PASS;
- targeted CA-08 suite — `Ran 6 tests in 25.173s`, `OK`;
- foreground full-app suite до clean reinstall — `Ran 47 tests in 233.817s`, `OK`;
- controlled uninstall/install/migrate — PASS; удалены/созданы заново 35 DocType;
- после reinstall подтверждены 35 DocType, role `Подрядчик` и оба Invoice adapter field;
- post-reinstall full-app suite — `Ran 47 tests in 196.603s`, `OK`.

Все runtime suites запускались со штатным `--skip-test-records`; versioned tests создают scoped данные самостоятельно. Worker/Credential production records не создавались: negative runtime attempts подтверждают hard block и rollback.

## Подтверждённые CA-08 сценарии

1. Contractor Assignment сохраняет Supplier/project/object/system/work type/responsibility/period без цены; direct mutation отклоняется.
2. Overlap одного Supplier и dimension отклоняется без смены Draft status; другой Supplier на том же scope/period разрешён.
3. Missing Supplier и foreign Object System отклоняются fail-closed.
4. Terms создаются после Assignment; approval связывает их, margin 100000 − 60000 = 40000/40%, cancellation безопасно отвязывает.
5. Settlement и Material Expense сохраняют Assignment/commercial basis и возвращаются trace API.
6. Contractor user с User Permission видит только Assignment своего Supplier; чужой direct read отклоняется.
7. Worker insert отклоняется даже с ignored DocPerm, disallowed Credential holder отклоняется, таблицы остаются без test records.
8. Все 41 CA-01…07 regression tests продолжают проходить.

## Дефект, найденный до финального PASS

Commercial Terms без `effective_to` первоначально трактовались как бессрочные и отклонялись для finite Assignment. Семантика исправлена: конец наследуется из Assignment, явный выход за его interval остаётся запрещён.

## Ограничения

MG-CA-015 evidence отсутствует. Employee positive runtime, production Worker/Credential data, credentials readiness/PERSONNEL READY, cross-entity positive portal access, legacy migration, concurrent race/load, HR/privacy/legal UAT/sign-off и production deployment не выполнялись.
