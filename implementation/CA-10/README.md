# CA-10 — Contract 360° и exception center

**Статус:** `CA-10 PARTIAL — CONTRACT 360 / EXCEPTION CORE v0.11.0 BENCH VERIFIED`.

Инкремент добавляет два read-only Frappe API: карточку одного `Ferum Service Project` и портфельный Director Control Center. Оба представления строятся при каждом запросе из первичных записей CA-01…09; отдельный Contract 360 DocType, таблица исключений или materialized cache не создаются.

Каждая строка widget и каждое исключение возвращают `source_doctype`, `source_name` и `drilldown`. Исключения дополнительно содержат rule, severity, owner, age и при наличии `source_field`/`due_at`. Сортировка детерминирована: severity, убывающий age, rule, source key.

Финансовый widget читает сохранённый `Ferum Project Finance Summary` CA-07 и не пересчитывает ledger/маржу. Единый role predicate закрывает snapshot, суммы, unpaid invoices и финансовые исключения. Runtime-тест подтверждает, что не-финансовая роль не получает ни денежных ключей, ни margin/AR exceptions.

Projection contract: [projection_v0_11_0.md](projection_v0_11_0.md).

Runtime evidence: [runtime_evidence_v0_11_0_2026-08-18.md](runtime_evidence_v0_11_0_2026-08-18.md).

Implementation traceability: [traceability_v0_11_0.md](traceability_v0_11_0.md).

## Подтверждённые проверки

- standalone unit/schema suite: `104 tests`, `OK`;
- CA-10 pure rules: source contract, severity, age и deterministic order;
- targeted Frappe CA-10 suite: `4/4`, `OK`;
- foreground full-app Frappe suite: `54/54`, `OK`;
- migrate v0.10.0 → v0.11.0: PASS;
- после migrate сохранены 35 Contract Accounting DocType; второй SSOT/cache не появился;
- PEP 517 wheel v0.11.0: PASS;
- Ruff для CA-10-owned файлов: PASS; repository-wide 32-item baseline debt остаётся OPEN.

## Открытая граница

Это API/read-model core, а не завершённый UI. Не закрыты Workspace/List/Report UI, экспорт и UI permission tests, representative-volume latency/load/race, UAT/sign-off и production deployment. BPM `Blocked`/stage-gate источники появятся только в CA-11. Для специального правила «обязательное фото отсутствует» нет утверждённой структурированной policy; существующие review/evidence gates не переименовываются в неё. Time-based exceptions требуют явный `as_of`; production calendar/warning/escalation остаются fail-closed по MG-CA-013. Стандартные Sales Invoice возвращаются только при существующем read permission пользователя.
