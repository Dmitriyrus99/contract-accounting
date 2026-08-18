# Service Request disposition — v0.16.3 — 2026-08-18

**Вердикт:** `CORE BENCH VERIFIED; CA-15/RA-09 PARTIAL`.

Инкремент реализует однозначную часть утверждённого OQ-CA-022 без второго финансового или файлового SSOT.

## Реализовано

- `subject` (`Data`) и `description` (`Text`) обязательны на server-side; миграция не изобретает legacy-содержание и маркирует отсутствующий текст `[MIGRATION REVIEW REQUIRED]`.
- Provenance для `Finding` и `Maintenance Visit` хранится как пара `source_doctype` (`Link DocType`) + `source_name` (`Dynamic Link`) и проверяется по типу, существованию и project context. `source_reference` оставлен read-only legacy mirror и выводится из typed source.
- `source_request`, `successor_kind` и `exception_key` являются service-owned successor identity. Установлены уникальности `exception_key` и `(source_request, successor_kind)`.
- `create_paid_work_request` создаёт не более одного `Additional Work` successor, не пишет цену/счёт и запрещает terminal/recursive source.
- `partial_close_request` под блокировкой строки атомарно создаёт единственный `Remaining` successor и закрывает только `Resolved + Partially Completed` source.
- `get_request_successors` строит reverse projection; поле-мirror `remaining_request` не введено.
- `register_customer_approval_evidence` принимает только standard `File`, exact-attached к текущей заявке, и создаёт/reuses confidential `Ferum Project Document`. Переход `Additional Work → In Progress` fail-closed без такого evidence.
- Finding creation и integration trace переведены на typed request provenance.

## Миграция

Patch `contract_accounting.patches.v0_16_3.backfill_service_request_disposition` выполняется после model sync:

- сохраняет существующий текст;
- подставляет review-marker только при реально пустом `subject`/`description`;
- переводит Finding/Maintenance Visit только при существующем exact target;
- останавливает миграцию при отсутствующем или конфликтующем typed source;
- не создаёт финансовых, approval или successor фактов.

Первый migrate применил patch. Повторный migrate завершился с кодом `0`, patch повторно не исполнялся.

## Проверки

- standalone schema/unit suite: `138/138`, `OK`;
- новый Service Request runtime suite: `2/2`, `OK`;
- затронутые runtime suites: Finding `5/5`, Maintenance Visit `4/4`, Billing Output `6/6`, Contract 360 `4/4`, Integration `2/2`, все `OK`;
- foreground full-app Frappe suite: `71/71`, `OK`, `278.587 s`;
- repeated `bench --site ca01.localhost migrate`: PASS;
- `bench build --app contract_accounting`: PASS;
- PEP 517 wheel: `contract_accounting-0.16.3-py3-none-any.whl`, `315467` bytes;
- scoped Ruff, compileall, JSON parse и `git diff --check`: PASS.

## Открытые ворота

- Фактический параллельный race/load test в production-подобной topology не выполнен. Row lock, две DB uniqueness и последовательная idempotency проверены, но это не заменяет конкурентную квалификацию.
- Для `Internal`/`Other` не утверждён typed owner; до решения требуется read-only legacy reference, автоматический mapping запрещён.
- Request-specific access-denied Process Event command не реализован.
- Browser/cross-role UAT новых команд, representative-volume performance, production data dry-run/cutover/rollback, legal/finance acceptance и production deployment не выполнялись.
- Никакие coexistence/merge/retire действия над production DocType и данными не выполнялись.
