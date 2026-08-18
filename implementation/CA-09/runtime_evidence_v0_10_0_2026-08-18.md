# CA-09 v0.10.0 bench runtime evidence — 2026-08-18

**Вердикт:** `PASS FOR SOURCE-PROJECTION SCOPE — MIGRATE / 50 TESTS; MG-CA-013 BLOCKED`.

## Зафиксированный вход

- repository/runtime CODE commit: `a08b70902d10425c04610f1bc7e13454c97604fb`;
- app: `contract_accounting 0.10.0`;
- Frappe `15.118.0`, ERPNext `15.119.2`;
- Bench Python `3.11.14`, MariaDB `10.11.14`, Redis `7.0.15`;
- wheel: `contract_accounting-0.10.0-py3-none-any.whl`, 184,015 bytes;
- wheel SHA-256: `6a08548256958e1d488a0ecaf5e37f23f8cfc4807faab99a4602955bad4a1a39`.

Стенд: disposable `ca01.localhost`, отдельная user-owned MariaDB `127.0.0.1:3317` и cache Redis `127.0.0.1:13000`. Production/legacy site и business data не использовались; secrets/site configuration не читались.

## Выполненные gates

- `python -m unittest discover -s tests` — `100 tests`, `OK`;
- `python -m compileall -q contract_accounting` — PASS;
- parse 36 JSON и `git diff --check` — PASS;
- Ruff `E4,E7,E9,F,I` для CA-09-owned modules — PASS;
- repository-wide тот же Ruff scope — OPEN: 32 `I001` и 1 `F401`, всего 33 baseline debt items вне CA-09-owned modules;
- PEP 517 wheel через `python -m build --wheel` — PASS;
- migrate v0.9.0 → v0.10.0 — PASS;
- targeted CA-09 suite — `Ran 3 tests in 11.790s`, `OK`;
- foreground full-app suite на финальном CODE commit — `Ran 50 tests in 232.509s`, `OK`;
- после migrate подтверждены прежние 35 Contract Accounting DocType; `Ferum Deadline` отсутствует.

## Подтверждённые сценарии

1. Explicit calendar fixture с T0, `Europe/Moscow`, holiday 2026-08-18, Calendar/Business Days, cut-off, warning/escalation выдаёт детерминированные timestamps и hash.
2. Unknown trigger, timezone и offset unit отклоняются fail-closed.
3. Timeline строки имеют точный primary source key; duplicate source key запрещён.
4. Изменение Execution Stage source date отражается новым due date/fingerprint без отдельной записи или orphan.
5. Без `as_of` overdue/warning classification отключена; explicit `as_of` включает только absolute overdue.
6. Guest без read permission не получает projection.
7. Все 47 CA-01…08 regression tests продолжают проходить.

## Ограничения

MG-CA-013 configuration evidence отсутствует. Не выполнялись production calendar selection, scheduler/notification delivery, automatic warning/escalation, structured signature/customer-response/general-warranty dates, BPM integration, representative-volume latency, UAT/sign-off и production deployment. Clean reinstall не повторялся: v0.10.0 не добавляет и не изменяет DocType schema; migrate и точный 35-DocType inventory проверены.
