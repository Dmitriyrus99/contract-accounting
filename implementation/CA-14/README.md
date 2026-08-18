# CA-14 — «Мои действия» и «Запуск проектов»

**Статус:** `CA-14 PARTIAL — PERMISSION-SAFE WORK QUEUES + LAUNCH UI v0.15.0 BENCH VERIFIED`.

Инкремент добавляет две standard Desk Page `ferum-my-actions` и `ferum-project-launches`, а также вкладку «Запуск» в `Ferum Service Project`. Все представления строятся при чтении поверх существующих Process Step, ToDo, Service Request, Maintenance Visit, Project Document, Launch Process/Stage/Gate и Contractor Assignment; новый task/cache DocType не создавался.

`Ferum Project Process Step` остаётся процессным SSOT, а standard `ToDo` — персональной доставкой. Проекция сводит их к одному `canonical_key`, переносит ToDo IDs в `delivery_todos` и не выдаёт будущие `Planned` steps как текущие действия. Сортировка детерминирована: overdue → today → upcoming → unscheduled, с независимыми state dimensions Blocked / Waiting External / Waiting Approval.

Launch view показывает 7-stage progress, раскрываемые steps/status/due dates, failed Stage Gate criteria и конкретные blocking conditions. `MG-CA-015` отображается как fail-closed credentials blocker; система не заявляет готовность персонала без legal/privacy evidence.

Projection contract: [projection_v0_15_0.md](projection_v0_15_0.md).

Runtime evidence: [runtime_evidence_v0_15_0_2026-08-18.md](runtime_evidence_v0_15_0_2026-08-18.md).

Implementation traceability: [traceability_v0_15_0.md](traceability_v0_15_0.md).

## Подтверждённые проверки

- standalone unit/schema suite: `132 tests`, `OK`;
- targeted final CA-14 Frappe suite: `2/2`, `OK`;
- foreground full-app Frappe suite: `67/67`, `OK` with `--skip-test-records`;
- repeated migrate: PASS; 2 Page и Launch Tab/HTML metadata установлены;
- Contract Accounting DocType count не изменился: 48;
- PEP 517 wheel v0.15.0: PASS;
- scoped Ruff/compileall/JSON/JS syntax/diff-check: PASS;
- repository-wide 32-item `E4,E7,E9,F,I` baseline debt остаётся OPEN.

## Открытая граница

Не выполнены browser/UAT и cross-role matrix для всех целевых ролей, representative-volume performance/load/race, production deployment и notification/escalation delivery. `missing_contractor` означает «contractor documents step открыт, но Approved assignment не подтверждён»; отдельный нормативный признак `contractor_required` отсутствует. `waiting_customer` распознаётся только по Waiting External steps утверждённого Launch graph и не содержит отдельные counterparty/expected-response поля. Positive personnel/credential readiness остаётся заблокированным `MG-CA-015`.
