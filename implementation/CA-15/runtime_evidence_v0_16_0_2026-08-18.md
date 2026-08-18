# CA-15 v0.16.0 bench runtime evidence — 2026-08-18

**Вердикт:** `PASS FOR READ-ONLY E2E/PROJECT-INTEGRITY CONTOUR — REPEATED MIGRATE / BUILD / 69 TESTS; CA-15 REMAINS PARTIAL`.

## Зафиксированный вход

- final CODE/test commit: `686f50e3e8733deeb280b303fd628a5081589e5c`;
- base implementation commit: `4a907f4b5cdade0f81d7bd28b4f2a454c6e34d94`;
- app: `contract_accounting 0.16.0`;
- Frappe `15.118.0`, ERPNext `15.119.2`;
- Bench Python `3.11.14`, MariaDB `10.11.14`, Redis `7.0.15`;
- user-owned build tools: Node.js `22.23.1`, Yarn `1.22.22`;
- wheel: `contract_accounting-0.16.0-py3-none-any.whl`, 304,880 bytes;
- wheel SHA-256: `777A2E3B06B19739AC6569849E8F84260D3688406B7285C6310223CB69F0329A`.

Стенд: disposable `ca01.localhost`, отдельная user-owned MariaDB `127.0.0.1:3317` и cache Redis `127.0.0.1:13000`. Production/legacy site и business data не использовались; secrets/site configuration не читались.

## Выполненные gates

- `py -m unittest discover -s tests` — `Ran 135 tests`, `OK`;
- traceability static gate — exact 557 unique req-id, 0 empty acceptance criterion, 0 empty owner;
- `python3 -m compileall -q contract_accounting tests` — PASS;
- scoped Ruff для CA-15 Python — PASS;
- parse Page JSON, `node --check` для CA-15 JS и `git diff --check` — PASS;
- `bench build --app contract_accounting` — PASS;
- migrate и repeated migrate — PASS на v0.16.0;
- targeted final CA-15 suite — `Ran 2 tests in 7.478s`, `OK`;
- foreground final full-app suite — `Ran 69 tests in 268.233s`, `OK`;
- PEP 517 wheel — PASS.

## Runtime scenarios

- одинаковые source facts дают одинаковый E2E fingerprint;
- response содержит exact девять E2E segments и семь cross-cutting dimensions;
- Request виден в result, Object System — в where, assignee — в who;
- finance-unprivileged Manager получает `payment/margin/materials/costs access=restricted`, без `profit_without_vat` в serialized payload;
- Manager denied на project integrity API;
- clean fixture даёт 0 issues;
- direct orphan fixture `Request.object_system → MISSING-CA15-SYSTEM` даёт stable `ORPHAN_LINK` issue key в повторном dry-run;
- integrity API не меняет число Project/Request/System records;
- три Page существуют после repeated migrate;
- Import Batch в обоих API остаётся inactive/not production-proven.

## Tooling defect trail

Первый `bench build` связал assets, но остановился: Linux `node` отсутствовал (`ValueError: Invalid version string: 'bin/sh: 1: node: not found'`). Без sudo и без запуска удалённого install script установлен официальный Linux x64 Node.js 22.23.1 в `/home/rus/.local`, archive SHA-256 проверен по official `SHASUMS256.txt`; Yarn 1.22.22 установлен в тот же user prefix. Повторный build прошёл. Первый failed build не засчитывался как PASS.

## Ограничения

Не выполнялись interactive browser/cross-role/export/report UAT, representative-volume performance/load/race, scheduler/retry production topology, portfolio-wide orphan reconciliation, approved exception registry, migration dry-run/cutover/rollback rehearsal, retention/archive, production deployment и sign-off. OQ-CA-022 review содержит explicit OPEN implementation rows. MG-CA-013/015/016/023 остаются OPEN.
