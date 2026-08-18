# CA-01 schema evidence — v0.1.0

**Статус:** `STATIC VERIFIED / BENCH RUNTIME NOT RUN`

**Дата:** 2026-08-18.

**Основание:** OQ-CA-001, OQ-CA-003, OQ-CA-020; [05_target_model.md](../../05_target_model.md), раздел 4; [06_roadmap.md](../../06_roadmap.md), CA-01.

## Frappe app scaffold

- app: `contract_accounting`;
- module: `Contract Accounting`;
- required app: `erpnext`;
- packaging: PEP 517 / `flit_core`, Python 3.10+;
- patches: отсутствуют; `patches.txt` содержит пустые pre/post model sync секции;
- business-record backfill и mapping старой status model отсутствуют по утверждённому reset/recreate решению.

## DocType `Ferum Service Project`

DocType является новым clean TARGET contract root. В schema v0.1.0 присутствуют:

| Группа | Поля | Frappe type / policy |
| --- | --- | --- |
| Identity | `project_name`, `company`, `customer`, `contract_number`, `contract_date`, `contract_subject` | Data/Link/Date/Small Text; required; legal permlevel 1 |
| Term | `effective_from`, `effective_to` | Date; `effective_from <= effective_to` server-side |
| Execution | `launch_date` | Date; execution permlevel 2 |
| Commercial | `currency`, `contract_amount_with_vat`, `contract_amount_without_vat`, `vat_amount`, `payment_terms`, `payment_due_days` | Link/Currency/Small Text/Int; finance permlevel 3, write Юрист/Бухгалтер |
| Legal FSM | `legal_status` | Select; exact 9 values OQ-CA-003; default Draft; read-only |
| Execution FSM | `execution_status` | Select; exact 6 values OQ-CA-003; default Not Started; read-only |
| Suspend projection | `suspended_from_status` | hidden read-only Select: Launching/Active |
| Termination exception | `documented_termination_completion_exception` | hidden read-only Check |
| Archive metadata | `is_archived`, `archived_at`, `archived_by` | read-only; archive не входит в FSM |

Composite unique key `(company, contract_number, contract_date)` регистрируется через `on_doctype_update`. Новый документ разрешён только в паре Draft + Not Started. Контроллер всегда проверяет cross-axis pair через domain policy и отклоняет прямое изменение lifecycle fields без выделенного server flag.

## DocType `Ferum Lifecycle Audit Event`

Insert-only DocType хранит отдельное событие для каждой изменённой оси:

- Service Project, dimension, from/to status;
- actor и timezone-aware occurred_at;
- reason, comment, effective date, evidence JSON;
- termination basis и related document;
- признак документированного исключения Terminated + Completed;
- общий `correlation_id` для атомарного изменения двух осей.

Обычные create/write/delete permissions отсутствуют. Controller принимает insert только под typed-writer flag, запрещает update и delete. Индексы: `(service_project, occurred_at)` и `(correlation_id)`.

## Transaction boundary и API

`FrappeLifecycleUnitOfWork` выполняет:

1. private database savepoint;
2. чтение Service Project с `for_update=True`;
3. domain transition validation;
4. guarded `Document.save()` новой projection;
5. typed insert одного или двух immutable audit events;
6. rollback к savepoint при любой ошибке; implicit commit отсутствует.

Whitelisted mutating commands:

- `contract_accounting.api.lifecycle.change_status`;
- `contract_accounting.api.lifecycle.suspend`;
- `contract_accounting.api.lifecycle.resume`.

Каждая команда повторно проверяет document permission. Legal, execution и dual-axis команды имеют разные role allowlist. Технический System Manager разрешён во всех трёх группах; business roles фиксируются versioned Role fixture.

## Static verification

| Проверка | Результат | Граница |
| --- | --- | --- |
| `python -m compileall -q contract_accounting tests` | PASS | синтаксис; не импортирует Frappe runtime controllers |
| `python -m unittest discover -s tests -v` | PASS, 52 tests | domain/application/authorization/fake-Frappe/schema/legacy-link tests |
| JSON parse трёх versioned fixtures/schema | PASS | синтаксис JSON |
| isolated PEP 517 wheel build + archive listing | PASS | package build; hooks/modules/patches, оба DocType JSON и Role fixture присутствуют; app на site не устанавливался |
| `git diff --check` | PASS | whitespace/conflict markers |

## Незакрытые CA-01 gates

- app install/migrate на отдельном ERPNext v15 test site — `NOT RUN`;
- runtime controller, DocPerm, row-lock и immutable audit tests под Frappe — `NOT RUN`;
- schema/link перевод Amendment, Execution Stage, Security и Financial Plan на этот root — `PENDING`;
- Service Project → Object → Object System integrity — `PENDING`;
- controlled schema/config rollback — `PENDING`; старые business records и status history не восстанавливаются и не backfill-ятся;
- UAT/legal/finance approval — `NOT RUN`.

Следовательно, этот артефакт подтверждает installable-intent и локальную логику, но не утверждает успешную установку или миграцию Frappe.
