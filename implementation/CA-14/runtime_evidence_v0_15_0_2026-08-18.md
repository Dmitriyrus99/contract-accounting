# CA-14 v0.15.0 bench runtime evidence — 2026-08-18

**Вердикт:** `PASS FOR READ-ONLY WORK QUEUES AND LAUNCH UI DATA — REPEATED MIGRATE / 67 TESTS; CA-14 REMAINS PARTIAL`.

## Зафиксированный вход

- final CODE/test commit: `48e1502524caf4735613b37b78aa4d8a806ecbba`;
- implementation commit: `daf48d6b3a2b11e653cc5e0a81b046f0c553c6b6`;
- app: `contract_accounting 0.15.0`;
- Frappe `15.118.0`, ERPNext `15.119.2`;
- Bench Python `3.11.14`, MariaDB `10.11.14`, Redis `7.0.15`;
- wheel: `contract_accounting-0.15.0-py3-none-any.whl`, 289,985 bytes;
- wheel SHA-256: `BFBBE81CE59E17CF3D57B094BE42A7DD816E6E2CEC1BDDE3CCD33E4DB42B1493`.

Стенд: disposable `ca01.localhost`, отдельная user-owned MariaDB `127.0.0.1:3317`, cache Redis `127.0.0.1:13000` и queue Redis `127.0.0.1:11000`. Production/legacy site и business data не использовались; secrets/site configuration не читались.

## Выполненные gates

- `python3 -m unittest discover -s tests` — `132 tests`, `OK`;
- `python3 -m compileall -q contract_accounting tests` — PASS;
- parse 51 JSON, `node --check` для 4 CA-14 JS и `git diff --check` — PASS;
- scoped Ruff для всех CA-14-owned/touched Python files — PASS;
- repository-wide Ruff `E4,E7,E9,F,I` — OPEN: 31 `I001` и 1 `F401`, всего 32 baseline items;
- PEP 517 wheel через `py -m build --wheel` — PASS;
- migrate v0.14.0 → v0.15.0 и repeated migrate — PASS;
- targeted final CA-14 suite — `Ran 2 tests in 8.395s`, `OK`;
- foreground final full-app suite с `--skip-test-records` — `Ran 67 tests in 284.206s`, `OK`;
- runtime metadata: Page `ferum-my-actions` и `ferum-project-launches` существуют; Service Project meta содержит `launch_view`;
- physical Contract Accounting DocType остаётся 48: CA-14 не создаёт второй task/cache SSOT.

## Runtime defect trail

Первый targeted прогон вернул все 25 шагов reference Launch вместо четырёх активных: responsible user был snapshot-назначен и на будущие `Planned` stages. API исправлен на exact actionable set `Ready / In Progress / Waiting External / Waiting Approval / Blocked`; повторный targeted прогон подтвердил 4 action rows и по одному merged ToDo delivery без дублей.

Первый вызов target suite после миграции использовал отдельное старое runtime source mirror. Зеркало синхронизировано без удаления файлов, migrate повторён на фактическом v0.15.0 source; это инфраструктурное рассогласование не засчитывалось как PASS до повторного прогона.

## Подтверждённые runtime scenarios

- Process Step + standard ToDo возвращаются одной canonical action с delivery reference;
- future Planned steps отсутствуют в My Actions;
- exact absolute due `2026-08-17 12:00` при `as_of=2026-08-18 12:00` классифицируется Overdue и стабильно сортируется первым;
- Engineer не получает action чужого project и не может вызвать Project Launches role API;
- Launch view возвращает exact 7 stages/25 steps и раскрываемые step statuses;
- Blocked Step даёт Failed Stage Gate, непустые failed criteria и concrete source blocker;
- `MG-CA-015` остаётся видимым missing-credentials blocker;
- read APIs не создают task/cache records и не меняют process state.

## Ограничения

Не выполнялись interactive browser/UAT, полный cross-role/export/report audit, representative-volume performance/load/race, production notification/escalation и deployment. Positive waiting-customer/counterparty и contractor-required semantics требуют дополнительных нормативных полей; positive personnel readiness требует закрытия `MG-CA-015`.
