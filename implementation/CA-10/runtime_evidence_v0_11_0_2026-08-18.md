# CA-10 v0.11.0 bench runtime evidence — 2026-08-18

**Вердикт:** `PASS FOR CONTRACT-360 API CORE — MIGRATE / 54 TESTS; DELIVERY PARTIAL`.

## Зафиксированный вход

- repository/runtime CODE commit: `19d912445bbfe85fcd1603101c64055a0c8abe4a`;
- app: `contract_accounting 0.11.0`;
- Frappe `15.118.0`, ERPNext `15.119.2`;
- Bench Python `3.12.3`, MariaDB `10.11.14`, Redis `7.0.15`;
- wheel: `contract_accounting-0.11.0-py3-none-any.whl`, 193,086 bytes;
- wheel SHA-256: `fc2bd81af12dfaf3208519656971f0b9552550181212f089ff708d83827d0317`.

Стенд: disposable `ca01.localhost`, отдельная user-owned MariaDB `127.0.0.1:3317` и cache Redis `127.0.0.1:13000`. Production/legacy site и business data не использовались; secrets/site configuration не читались.

## Выполненные gates

- `python -m unittest discover -s tests` — `104 tests`, `OK`;
- `python -m compileall -q contract_accounting` — PASS;
- parse 36 JSON и pre-doc `git diff --check` — PASS;
- Ruff `E4,E7,E9,F,I` для CA-10-owned modules — PASS;
- repository-wide тот же Ruff scope — OPEN: 31 `I001` и 1 `F401`, всего 32 baseline items вне CA-10-owned modules;
- PEP 517 wheel через `python -m build --wheel` — PASS;
- migrate v0.10.0 → v0.11.0 — PASS;
- targeted CA-10 suite — `Ran 4 tests in 17.943s`, `OK`;
- foreground full-app suite — `Ran 54 tests in 266.029s`, `OK`;
- после migrate подтверждены ровно 35 Contract Accounting DocType; Contract 360/Exception cache DocType отсутствует.

## Подтверждённые сценарии

1. Project card собирает identity, object/system, maintenance, request, Finding, document, billing, contractor, deadline и stored finance sources с drilldown.
2. Повторный вызов по неизменным sources даёт тот же fingerprint и не выполняет writes; source change отражается новым fingerprint.
3. Finance Summary читается как сохранённый CA-07 snapshot: Contract 360 не запускает самостоятельный финансовый расчёт.
4. Не-финансовая роль получает restricted finance без monetary keys, unpaid invoices, AR или margin exceptions.
5. Director endpoint отклоняет обычную роль, принимает разрешённую и возвращает project/exception drilldown.
6. Новый persistent DocType/cache не появился; все 50 CA-01…09 regression tests продолжают проходить.

## Ограничения

Не выполнялись Workspace/List/Report UI и export tests, representative-volume latency, load/race, UAT/sign-off и production deployment. BPM blocked/stage-gate sources отсутствуют до CA-11. Photo-required exception не активирован без структурированной policy. Production time classification/warning/escalation остаётся зависимой от открытого MG-CA-013. Clean reinstall не повторялся: v0.11.0 не меняет DocType schema; migrate и точный 35-DocType inventory проверены.
