# CA-09 projection contract — v0.10.0

**Статус:** `READ-ONLY SOURCE PROJECTION BENCH VERIFIED AT a08b709; MG-CA-013 FAIL-CLOSED`.

## Нормализованная строка

| Поле | Семантика |
| --- | --- |
| `kind` | тип контрольной даты projection, не новый business fact |
| `source_doctype/name/field` | точный первичный владелец даты |
| `source_key` | `<doctype>:<name>:<field>`, duplicate запрещён |
| `owner` | первичный assignee/owner, если source его хранит |
| `due_at` | ISO date/datetime непосредственно из source |
| `source_status` | статус первичной записи |
| `is_overdue/overdue_since/display_status/severity` | derived attributes; без явного `as_of` не вычисляются |

`source_fingerprint` строится только по source identity/date/status/owner. Изменение первичной даты отражается новым fingerprint; cache/table и rebuild write отсутствуют.

## Source adapters

| Source | Поля | Timeline kind |
| --- | --- | --- |
| `Ferum Service Project` | `effective_from`, `effective_to` | Contract Start / Contract Expiry |
| `Ferum Maintenance Schedule` | `due_date` | Maintenance Due |
| `Ferum Service Request` | `reaction_due`, `resolution_due` | Request Reaction / Resolution Due |
| `Ferum Contract Execution Stage` | `acceptance_due_date`, `billing_due_date`, `payment_due_date` | Acceptance / Billing Issue / Stage Payment Due |
| `Ferum Contract Security` | `reminder_date`, `valid_until`, `return_due_date` | Security Reminder / Performance or Warranty or Bank Guarantee Expiry / Return Due |
| `Ferum Project Document` | `valid_until`, `original_expected_at` | Document Expiry / Original Expected |
| `Ferum Finding` | `due_date` | Finding Resolution Due |
| submitted `Sales Invoice` | `due_date` | Invoice Payment Due |

Project read permission проверяется до projection. Каждый дочерний source дополнительно проходит Frappe read permission; финансовые суммы не извлекаются и не возвращаются.

## Calendar calculation boundary

Pure `calculate_deadline` принимает только явные `triggered_at`, `DeadlineRule` и `CalendarSnapshot`. Snapshot включает IANA timezone, revision, holidays, weekend weekdays, cut-off и after-cutoff policy; rule включает Calendar/Business Days, due time, warning и escalation offsets. Результат timezone-aware и имеет SHA-256 полного input/result snapshot.

Этот engine не подключён к scheduler или автоматической записи. До MG-CA-013 production API не выбирает Company calendar, Holiday List или cut-off самостоятельно.

## Не создаётся

- `Ferum Deadline` / `Ferum Contract Milestone`;
- editable timeline row;
- materialized cache/index без измеренной необходимости;
- inferred date из `payment_terms`, `quality_guarantee_terms` или другого текста;
- automatic notification/escalation без конфигурационного evidence.
