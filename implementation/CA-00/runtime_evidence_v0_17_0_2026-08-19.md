# Runtime evidence — master-data boundary v0.17.0

Дата: 2026-08-19. Итог: `PASS — STATIC / MIGRATE / BUILD / 79 BENCH TESTS`. Ручные и эксплуатационные gates не оценены.

## Вход и стенд

- app: `contract_accounting 0.17.0`;
- Frappe `15.118.0`, ERPNext `15.119.2`;
- disposable Bench: `/home/rus/contract-accounting-bench`;
- disposable site: `ca01.localhost`;
- отдельные user-owned MariaDB `127.0.0.1:3317`, Redis `127.0.0.1:13000/11000`;
- `ferum.localhost`, `dev.localhost`, legacy/production data и credentials не использовались;
- wheel: `contract_accounting-0.17.0-py3-none-any.whl`, 328,242 bytes;
- wheel SHA-256: `AFBE22C3214A2E194DD861E3756CA036FD1E820CBF6B70F9F2E37718D2772BCC`.

## Выполненные gates

1. Windows static quality gate: `PASS`.
   - release matrix exact: 557 rows;
   - Ruff/compileall/JSON/JS/secret scan/Markdown links: `PASS`;
   - standalone tests: `147/147 OK`;
   - mypy: 14 files, no issues;
   - isolated sdist/wheel build: `PASS`.
2. Source sync Windows → WSL: checksum dry-run produced no delta.
3. `bench --site ca01.localhost list-apps`: app version `0.17.0`.
4. `bench --site ca01.localhost migrate`: `PASS`.
5. `bench build --app contract_accounting`: `PASS`.
6. Targeted Party Identity acceptance: `7/7 OK`.
7. Final full application protocol: `bench --site ca01.localhost run-tests --app contract_accounting --skip-test-records` → `Ran 79 tests in 380.526s`, final `OK`.
8. После квалификации одноразовые MariaDB/Redis остановлены: `DISPOSABLE_BENCH_SERVICES=STOPPED`; порты `3317/13000/11000` закрыты проверкой stop-script.

## Диагностический прогон и исправление gate

Первый полный прогон выявил 7 ошибок Party Identity: Frappe повторно применял user-default Company внутри `Document.insert()` после очистки input. Одновременно Bench вернул exit code 0 при transcript `FAILED (errors=7)`, из-за чего ранняя версия wrapper ошибочно напечатала `BENCH_QUALITY_GATE=PASS`.

Исправлено до финального прогона:

- exact authorized-link map передаётся controller-у;
- `before_insert` удаляет только не запрошенные typed-командой user defaults;
- direct/unapproved link mutation остаётся fail-closed;
- `scripts/bench_quality_gate.py` теперь стримит transcript, отвергает `FAILED` даже при exit code 0 и требует финальный `OK`.

Диагностический ложный PASS не является release evidence. Evidence этого документа — только последующий targeted `7/7 OK` и полный `79/79 OK`.

## Не выполнено

- hosted GitHub Actions run;
- business/data-owner и browser UAT;
- race/load/performance qualification;
- restore rehearsal и off-host backup verification;
- standard Workflow/Communication positive acceptance;
- staging/production deploy, cutover, rollback rehearsal и sign-off.
