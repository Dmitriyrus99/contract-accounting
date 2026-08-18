# CA-00 rollback rehearsal — 2026-08-18

**Вердикт:** `PARTIAL / FULL RESTORE NOT EVIDENCED`

**Стенд:** `w2t12b.localhost` в уже запущенном `ferum-vstand`

**Граница:** только disposable test-site; production/dev sites не затрагивались.

## Baseline before mutation

| Проверка | Значение |
| --- | --- |
| `Ferum Settings.maintenance_source_schedule` | `0` |
| schema probe column | отсутствует |
| Ferum Custom DocType | `54`, SHA-256 `4290bd674b2930172c6010114c5637112ada519a2bb614d0b92356b523ca6efd` |
| DocField | `828`, SHA-256 `9c0dae4596b66f5298150599ae475b751152c8f37b325e7cf7a97777ecf7955d` |
| Custom Field | `69`, SHA-256 `71006b232f44c8627c12ecea136b09f5bb3ae0f7adae7d123e01f709fda19f07` |
| applied ferum_custom patches | `21`, SHA-256 `9ae7d60bc6f69d9f019c627be29f3077402db2c174ad3d4ecd8a20b85e79df54` |

## Backup

`bench --site w2t12b.localhost backup` завершился с exit code `0`.

- Database artifact: `sites/w2t12b.localhost/private/backups/20260818_055737-w2t12b_localhost-database.sql.gz`
- Size: `908968` bytes
- SHA-256: `29ca0eb624a6ac73ba91998599fc6f5f89aec352f7887a444065e0a80e7f5953`
- Frappe также создал `site_config_backup.json`; его содержимое и hash намеренно не читались из-за secret boundary.

## Controlled mutation

На test-site успешно применены два наблюдаемых изменения:

1. Добавлена SQL-колонка `tabFerum Service Project.ca00_rollback_probe INT NOT NULL DEFAULT 0`.
2. Несекретный Check-флаг `maintenance_source_schedule` изменён `0 → 1`.

Проверка после mutation показала `probe_columns = 1`, `setting = 1`.

## Restore attempt

Команда `bench --site w2t12b.localhost restore <database.sql.gz>` остановилась до начала восстановления на интерактивном запросе `MySQL root password`. Credential не читался, не передавался и не выводился. Поэтому этот запуск не является backup/restore PASS.

## Compensating rollback

Чтобы не оставлять test-site изменённым после остановленного restore:

1. schema probe удалён точным `ALTER TABLE ... DROP COLUMN`;
2. `maintenance_source_schedule` возвращён `1 → 0`;
3. повторно рассчитаны исходные hashes.

После compensating rollback:

- `probe_columns = 0`;
- `setting = 0`;
- все четыре baseline count/hash совпали побайтно с before-state.

## Что требуется для полного PASS

Полный MG-CA-016 restore gate остаётся OPEN. Его можно закрыть только повторным `bench restore` с credential, предоставленным безопасным runtime-механизмом без чтения/печати секрета, и теми же after-restore hashes. Текущий прогон доказывает backup creation и точный compensating rollback, но не работу restore command.
