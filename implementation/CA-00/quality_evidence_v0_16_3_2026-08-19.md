# Quality evidence — working tree `0.16.3`, 2026-08-19

**Вердикт:** `LOCAL STATIC QUALITY PASS / DISPOSABLE BENCH PASS / REMOTE CI NOT RUN`.

**Source boundary:** проверен текущий Windows working tree после completion baseline `7145d87` и наблюдаемой commit-дельты `5249e00`. Документация, Release Scope и quality files ещё не зафиксированы новым commit, поэтому этот акт не является immutable RC evidence. Каталог `contract_accounting/` checksum-синхронизирован в disposable runtime mirror; повторный `rsync -rcni --delete --exclude __pycache__/` дал output `0`.

## 1. Static CI-equivalent run

Команда: `python scripts/quality_gate.py`; exit code `0`.

| Проверка | Результат |
| --- | --- |
| Release Scope regeneration/check | PASS: 557 rows; Mandatory 554; Absent 2 |
| Ruff correctness/import profile | PASS |
| Ruff format ratchet | PASS: current/baseline 121; new debt 0 |
| Python compileall | PASS |
| JSON parse | PASS: 55 files |
| JavaScript syntax | PASS: 8 files |
| Secret scan | PASS: 354 Git-visible text files; findings 0 |
| Local Markdown links | PASS: 402 |
| Standalone/schema tests | PASS: 138/138 |
| mypy | PASS: 14 source modules |
| isolated package build | PASS: `contract_accounting-0.16.3.tar.gz` и wheel |

Локальные версии: Python `3.14.3`, Ruff `0.16.3`, mypy `1.20.2`, build `1.5.0`, Node.js `24.13.1`.

## 2. Disposable Bench run

Стенд: `/home/rus/contract-accounting-bench`, site `ca01.localhost`, отдельная MariaDB `127.0.0.1:3317`, Redis cache/queue `127.0.0.1:13000/11000`. Legacy/Production site и business data не использовались; credential values не читались и не выводились.

Версии:

- Frappe `15.118.0`;
- ERPNext `15.119.2`;
- `contract_accounting 0.16.3`;
- Bench `5.29.1`, Python `3.11.14`, Node.js `22.23.1`, Yarn `1.22.22`;
- MariaDB `10.11.14`, Redis `7.0.15`.

| Команда | Exit / результат |
| --- | --- |
| `bench --site ca01.localhost list-apps` | `0`; exact three apps above |
| `bench --site ca01.localhost migrate` | `0`; DocTypes/Dashboards/after_migrate completed |
| `bench build --app contract_accounting` | `0`; assets linked and build completed |
| `bench --site ca01.localhost run-tests --app contract_accounting` | non-zero before app tests: upstream record traversal requested missing `Payment Gateway` |
| `bench --site ca01.localhost run-tests --app contract_accounting --skip-test-records` | `0`; `Ran 71 tests in 382.003s`, `OK` |

`--skip-test-records` соответствует ранее сохранённому full-app protocol для этой версии. Отдельные app tests создают controlled test records; initial diagnostic failure сохранён как environment/tooling boundary и не объявляется product-test FAIL или PASS.

## 3. Не проверено этим актом

- hosted GitHub Actions run и branch protection;
- fresh-site install/reinstall на новом database instance;
- scheduler/worker/email/print delivery;
- browser/cross-role/API/report/export/private-file RBAC matrix;
- representative load/race/performance;
- business/finance/legal/security UAT;
- backup restore, rollback/cutover, Staging/Production deployment.

Следовательно, общий release status остаётся `NOT READY FOR PRODUCTION`.
