# Runtime evidence — production calendar v0.18.0

Дата: 2026-08-19. Вердикт: `PASS — MIGRATE / BUILD / TARGETED 4+3 / FULL 83 TESTS`; UAT/performance/restore/deployment не оценены.

## Стенд

- disposable Bench `/home/rus/contract-accounting-bench`, site `ca01.localhost`;
- Frappe `15.118.0`, ERPNext `15.119.2`, `contract_accounting 0.18.0`;
- отдельные MariaDB `127.0.0.1:3317`, Redis `127.0.0.1:13000/11000`;
- `ferum.localhost`, `dev.localhost`, legacy/production data и credentials не использовались;
- Windows→WSL rsync dry-run после синхронизации: no delta.

## Принятые результаты

1. Финальный и повторный `bench --site ca01.localhost migrate`: PASS; source-controlled fixture повторно не изменён.
2. `bench build --app contract_accounting`: PASS.
3. Fixture runtime verification: `247 working / 118 non-working / 4 shortened`, hash `56691dc76841c9ef33550cec0539c82010f1e1277055c5f2ffdfec029744d917`.
4. Targeted production-calendar acceptance: `4/4 OK`.
5. Targeted existing deadline timeline: `3/3 OK`.
6. Full application protocol с `--skip-test-records`: `Ran 83 tests in 395.740s`, final `OK`, `BENCH_QUALITY_GATE=PASS`.
7. Final Windows static gate: release-scope `557/554/Absent=0`, Ruff, format ratchet `99/121`, 63 JSON, 8 JS, secret scan 392 files, 431 local Markdown links, standalone `154/154`, mypy 14 modules, package build; `STATIC_QUALITY_GATE=PASS`.
8. Final wheel: `contract_accounting-0.18.0-py3-none-any.whl`, 355726 bytes, SHA-256 `c4771eea0813de76871281f2d4511e52200599e0779bc29b4697748ef7d96b52`.
9. `git diff --check`: PASS.

Targeted acceptance включает Company assignment, Contract precedence с обязательной evidence, 08:00/19:00 и сокращённый день, holiday/weekend roll, idempotent initial calculation, role/reason manual recalculation, неизменность старого snapshot, direct-write denial и source-linked Customer Response timeline.

## Диагностические отказы

Три первых migrate после schema sync были корректно отклонены в `after_migrate`: importer сначала валидировал candidate без Frappe `__islocal`, затем выявил автоматически подставляемое текущее время в пустых child Time fields. Fixture не был принят частично. Loader исправлен: новое значение валидируется внутри insert, а необязательные child times передаются явно как zero; последующий и повторный migrate завершились PASS. Эти FAIL не считаются release evidence.

## Открытые gates

- terminal hosted CI на зафиксированном commit;
- site-specific Company assignment и Operations/browser/RBAC UAT;
- annual revision 2027 до расчётов, пересекающих границу года;
- FR-04 scheduler/notification retry/dead-letter и полный FR-08 lifecycle;
- representative-volume recompute/load/race;
- restore, staging/production cutover/rollback и sign-off.
