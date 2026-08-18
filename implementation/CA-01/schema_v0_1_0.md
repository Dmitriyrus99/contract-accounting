# CA-01 schema evidence — v0.1.0

**Статус:** `STATIC + BENCH RUNTIME VERIFIED AT fae6581`

**Дата:** 2026-08-18.

**Основание:** OQ-CA-001, OQ-CA-003, OQ-CA-020; [05_target_model.md](../../05_target_model.md), раздел 4; [06_roadmap.md](../../06_roadmap.md), CA-01.

## Frappe app scaffold

- app: `contract_accounting`;
- module: `Contract Accounting`;
- required app: `erpnext`;
- packaging: PEP 517 / `flit_core`, Python 3.10+; distribution/app import name `contract_accounting`;
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
- actor и timezone-aware domain timestamp; при записи Frappe `Datetime` хранится naive wall time site timezone по конвенции Frappe;
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
| isolated PEP 517 wheel build + archive listing | PASS | package build; hooks/modules/patches, оба DocType JSON и Role fixture присутствуют |
| `git diff --check` | PASS | whitespace/conflict markers |
| separate-site install + migrate | PASS | Frappe 15.118.0 / ERPNext 15.119.2 / MariaDB 10.11.14 |
| versioned Frappe runtime suite | PASS, 8/8 | реальные DocType, permissions, savepoint/rollback и audit persistence |
| schema uninstall/reinstall | PASS | disposable site; без backup/restore business data |

## Незакрытые CA-01 gates

- schema/link перевод Amendment, Execution Stage, Security и Financial Plan на этот root — `PENDING`;
- Service Project → Object → Object System integrity — `PENDING`;
- full site backup/restore — `NOT RUN`; controlled app schema uninstall/reinstall — `PASS`;
- UAT/legal/finance approval — `NOT RUN`.

Точные runtime evidence и ограничения: [runtime_evidence_2026-08-18.md](runtime_evidence_2026-08-18.md). Успешная bench-проверка не утверждает production deployment или ручные approvals.
