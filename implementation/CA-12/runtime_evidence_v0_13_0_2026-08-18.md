# CA-12 v0.13.0 bench runtime evidence — 2026-08-18

**Вердикт:** `PASS FOR SEVEN-STAGE LAUNCH + INSPECTION CORE — MIGRATE / 63 TESTS; CA-12 REMAINS PARTIAL`.

## Зафиксированный вход

- final CODE commit: `5fbb9a3e34c1b0c78a06d919a49b9958541e170b`;
- app: `contract_accounting 0.13.0`;
- Frappe `15.118.0`, ERPNext `15.119.2`;
- Bench Python `3.11.14`, MariaDB `10.11.14`, Redis `7.0.15`;
- wheel: `contract_accounting-0.13.0-py3-none-any.whl`, 255,978 bytes;
- wheel SHA-256: `A0781F09E08EDD4FD1B864AC14D2BDECED0956B0AEB2BDEE4A9E6C89A218B1E4`.

Стенд: disposable `ca01.localhost`, отдельная user-owned MariaDB `127.0.0.1:3317` и cache Redis `127.0.0.1:13000`. Production/legacy site и business data не использовались; secrets/site configuration не читались.

## Выполненные gates

- `py -m unittest discover -s tests` — `123 tests`, `OK`;
- `py -m compileall -q contract_accounting tests` — PASS;
- parse 48 JSON и `git diff --check` — PASS;
- Ruff `E4,E7,E9,F,I` для CA-12-owned и изменённых adapter files — PASS;
- repository-wide тот же Ruff scope — OPEN: 32 `I001` и 1 `F401`, всего 33 baseline items;
- full default Ruff — OPEN: 189 pre-existing/global items; это не подменяет scoped PASS;
- PEP 517 wheel через `python -m build --wheel` — PASS;
- migrate v0.12.0 → v0.13.0 — PASS; повторный migrate exact graph idempotency — PASS;
- targeted CA-12 suite — `Ran 4 tests in 13.727s`, `OK`;
- foreground full-app suite на final CODE commit с `--skip-test-records` — `Ran 63 tests in 277.867s`, `OK`;
- после migrate подтверждены 47 Contract Accounting DocType: прежние 44 плюс parent `Ferum Inspection` и два child DocType;
- reference template подтверждён как 7 stages / 25 steps.

## Fixture trail

Первый `--doctype Ferum Inspection` и обычный `--app` runner остановились до application tests на неполных standard ERP test fixtures: сначала отсутствовал `Gender: Female`. На disposable test site были восстановлены standard `Female`/`Male`; следующий обычный runner дошёл до отсутствующего optional standard `Payment Gateway` DocType. Это не отмечено PASS.

Authoritative full-app run выполнен с `--skip-test-records`: все 63 Ferum tests создают собственные fixtures и завершились `OK`. Bench может вернуть process exit 0 при текстовом `FAILED`, поэтому принимался только финальный текст `Ran ... / OK`, а не exit code отдельно.

## Подтверждённые runtime scenarios

- exact template seed и отсутствие automatic history;
- explicit generation token и negative MG-CA-015 gate;
- Inspection → report/Finding/photo → manager Approved → Validated Process Evidence exact step;
- all blocking gates → final Launch completion → audited project `Active`.

## Ограничения

Clean reinstall не выполнялся. Не проверялись automatic award/event generation, Personnel/Credential positive gate, separate child Inspection process, automatic act/defect-statement documents, Additional Work, B2G/B2B/subcontract pilots, CA-13 Billing readiness, UI, representative-volume performance/load/race, UAT/sign-off и production deployment. MG-CA-015 остаётся OPEN.
