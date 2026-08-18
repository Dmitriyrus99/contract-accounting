# CA-13 v0.14.0 bench runtime evidence — 2026-08-18

**Вердикт:** `PASS FOR RECURRING BILLING CYCLE CORE — REPEATED MIGRATE / 65 TESTS; CA-13 REMAINS PARTIAL`.

## Зафиксированный вход

- final CODE commit: `c6e591b8f70f3de13bde45e9c70eb1f42075e67b`;
- implementation/test commits: `91b16ee`, `7860f3f`, `c6e591b`;
- app: `contract_accounting 0.14.0`;
- Frappe `15.118.0`, ERPNext `15.119.2`;
- Bench Python `3.11.14`, MariaDB `10.11.14`, Redis `7.0.15`;
- wheel: `contract_accounting-0.14.0-py3-none-any.whl`, 273,121 bytes;
- wheel SHA-256: `2775B635570DF2DEACBE67C3DBA251E78783D708CED7F4F0B9330E447ADA0457`.

Стенд: disposable `ca01.localhost`, отдельная user-owned MariaDB `127.0.0.1:3317` и cache Redis `127.0.0.1:13000`. Production/legacy site и business data не использовались; secrets/site configuration не читались.

## Выполненные gates

- `py -m unittest discover -s tests` — `128 tests`, `OK`;
- `py -m compileall -q contract_accounting tests` — PASS;
- parse 49 JSON и `git diff --check` — PASS;
- full Ruff для CA-13-owned/touched files — PASS;
- repository-wide Ruff `E4,E7,E9,F,I` — OPEN: 31 `I001` и 1 `F401`, всего 32 baseline items;
- PEP 517 wheel через `py -m build --wheel` — PASS;
- migrate v0.13.0 → v0.14.0 — PASS; repeated migrate exact template idempotency — PASS;
- targeted final CA-13 suite — `Ran 2 tests in 12.370s`, `OK`;
- foreground full-app suite на final commit с `--skip-test-records` — `Ran 65 tests in 321.056s`, `OK`;
- после migrate подтверждены 48 Contract Accounting DocType: прежние 47 плюс parent `Ferum Billing Cycle`;
- reference template: Published, 1 stage / 9 steps.

## Runtime defect trail

Первый targeted запуск выполнил два CA-13 и шесть непреднамеренно импортированных CA-06 tests, после чего CA-13 approval fixture был отклонён корректным CA-11 guard: approver step нельзя завершить прямо из In Progress. Fixture import изолирован через module alias, а сценарий изменён на `In Progress → Waiting Approval → Completed`; production FSM не ослаблялась. Финальный targeted и два full-app прогона завершились `OK`.

## Подтверждённые runtime scenarios

- exact reference template, idempotent Cycle и no-history install;
- expected/accepted/unbilled/billed projection;
- Output/Basis/Invoice/Payment reverse trace и correction history;
- standard submitted Payment Entry и zero outstanding без Ferum GL write;
- nine milestone FSM, explicit conditional NA, Passed Gate, Completed Process/Cycle;
- overdue Cycle в source-linked Contract 360 control feed.

## Ограничения

Clean reinstall и legacy backfill rehearsal не выполнялись. Не проверялись automatic recurring trigger/scheduler, dedicated positive UPD/SF branch, external delivery/receipt integration, production notification/escalation, representative-volume performance/load/race, UAT/sign-off и production deployment.
