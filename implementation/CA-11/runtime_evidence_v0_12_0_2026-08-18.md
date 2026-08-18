# CA-11 v0.12.0 bench runtime evidence — 2026-08-18

**Вердикт:** `PASS FOR VERSIONED BPM CORE — MIGRATE / 59 TESTS; CA-11 REMAINS PARTIAL`.

## Зафиксированный вход

- final repository/runtime CODE commit: `b474d7430d328e6ceed3a1c87a2697f8fd8e2c87`;
- implementation commits: `ddf1950`, `0b58467`, `c4c76ca`, `b474d74`;
- app: `contract_accounting 0.12.0`;
- Frappe `15.118.0`, ERPNext `15.119.2`;
- Bench Python `3.11.14`, MariaDB `10.11.14`, Redis `7.0.15`;
- wheel: `contract_accounting-0.12.0-py3-none-any.whl`, 233,148 bytes;
- wheel SHA-256: `560ed5cd2a0172750a55829a06e049cdfb08944f6e1bf3f6ef3ab02d2dbac92c`.

Стенд: disposable `ca01.localhost`, отдельная user-owned MariaDB `127.0.0.1:3317` и cache Redis `127.0.0.1:13000`. Production/legacy site и business data не использовались; secrets/site configuration не читались.

## Выполненные gates

- `python -m unittest discover -s tests` — `117 tests`, `OK`;
- `python -m compileall -q contract_accounting` — PASS;
- parse 45 JSON и `git diff --check` — PASS;
- Ruff `E4,E7,E9,F,I` для CA-11-owned и изменённых adapter files — PASS;
- repository-wide тот же Ruff scope — OPEN: 31 `I001` и 1 `F401`, всего 32 baseline items вне CA-11-owned files;
- PEP 517 wheel через `python -m build --wheel` — PASS;
- migrate v0.11.0 → v0.12.0 — PASS;
- targeted CA-11 suite — `Ran 5 tests in 16.049s`, `OK`;
- targeted CA-09 deadline suite — `3/3`, `OK`;
- targeted CA-10 Contract 360 suite — `4/4`, `OK`;
- foreground full-app suite на final CODE commit — `Ran 59 tests in 351.470s`, `OK`;
- после migrate подтверждены ровно 44 Contract Accounting DocType: прежние 35 плюс 9 новых BPM parent DocType.

## Runtime defect trail

Первый targeted запуск выявил нормализацию Frappe JSON field: строка `{}` должна означать отсутствие rule; исправлено `0b58467`. Второй запуск выявил границу timezone-aware pure calculation → site-local Frappe Datetime; wall-clock storage исправлено `c4c76ca`, immutable timezone/revision hash сохранён. Третий запуск показал дефект fixture, создававшего новый UUID вместо повтора exact generation key; test исправлен `b474d74`. Финальный targeted и full suites зелёные.

## Ограничения

Не выполнялись clean reinstall, automatic event/scheduler/notification delivery, production Company calendar selection, Department Head/Director escalation delivery, role-to-user resolution, configured CA-12/13 process templates, ad-hoc individual steps, representative-volume performance, load/race, UAT/sign-off и production deployment. MG-CA-013 остаётся OPEN.
