# Runtime evidence — notification delivery v0.19.0

Дата: 2026-08-19. Вердикт: `PASS — MIGRATE / BUILD / TARGETED 6 / FULL 89 TESTS`; production activation, external SMTP receipt, UAT/performance/restore/deployment не оценены.

## Стенд

- disposable Bench `/home/rus/contract-accounting-bench`, site `ca01.localhost`;
- Frappe `15.118.0`, ERPNext `15.119.2`, `contract_accounting 0.19.0`;
- MariaDB `127.0.0.1:3317`, Redis `127.0.0.1:13000/11000`;
- site timezone `Asia/Kolkata`, calendar timezone `Europe/Moscow` — эта разница использована как positive timezone-boundary test;
- `ferum.localhost`, `dev.localhost`, legacy/production data и credentials не использовались.

## Принятые результаты

1. Финальный и повторный `bench --site ca01.localhost migrate`: PASS; runtime inventory `58` Contract Accounting DocType соответствует `58` source JSON schemas.
2. `bench build --app contract_accounting`: PASS.
3. Targeted FR-04 suite: `6/6`, final `OK`.
4. Full application protocol с `--skip-test-records`: `Ran 89 tests in 537.357s`, final `OK`, `BENCH_QUALITY_GATE=PASS`.
5. Standalone/schema suite: `161/161 OK`; scoped Ruff `E4/E7/E9/F/I` и `git diff --check`: PASS.
6. Реальные standard transport records: in-app `Notification Log` и delayed `Email Queue`; deterministic Message-ID и reconciliation `Queued → Sent` проверены без внешнего SMTP send.
7. Idempotent повтор не создаёт delivery duplicates; due/channel identities разделены.
8. `MINUS_3` batching, `MINUS_1`, due-08, overdue, `OVERDUE_PLUS_1`, daily 09:00 digest, short `50/80/breach`, closed-source exclusion, retry→Dead Letter и typed manual retry проверены.
9. После acceptance teardown и отдельной typed deactivation `Ferum Notification Settings.enabled=0`; scheduler не оставлен активным.
10. Final static gate: release-scope `557/554/Absent=0`, Ruff, format ratchet `99/121`, 66 JSON, 8 JS, secret scan 413 files, 455 local Markdown links, standalone `161/161`, mypy 15 modules, package build; `STATIC_QUALITY_GATE=PASS`.
11. Final wheel: `contract_accounting-0.19.0-py3-none-any.whl`, 375689 bytes, SHA-256 `203ef8497055ffac59456b73e5d38840e88897c6fad7f7bf5c2269efc008c478`.
12. После проверок одноразовые MariaDB/Redis services остановлены штатным script; ports `3317/11000/13000` и соответствующие processes подтверждены как stopped.

## Диагностические отказы

- первый schema migrate v0.19.0 остановился на отсутствующем обязательном Python-модуле child DocType; модуль добавлен, последующий и повторный migrate PASS;
- первые digest assertions выявили, что site `Asia/Kolkata` нельзя считать договорной timezone; cron изменён на 15-минутный tick с локальным calendar окном 09:00, после чего timezone-boundary test PASS;
- первые acceptance assertions считали delivery соседних test projects; проверки сужены до exact source/correlation keys;
- Frappe email HTML renderer выводит CSS parser warnings для upstream `#0000001a`, но создание Email Queue и тест завершаются `OK`.

Диагностические FAIL не считаются evidence. Приняты только последующие terminal `OK` и wrapper PASS.

## Открытые gates

- terminal hosted CI на зафиксированном commit;
- production activation с утверждённым watermark и outgoing Email Account;
- реальная SMTP delivery/receipt/bounce и scheduler worker heartbeat;
- browser/RBAC/Operations UAT, representative-volume load/race;
- restore, Staging/Production cutover/rollback и sign-off.
