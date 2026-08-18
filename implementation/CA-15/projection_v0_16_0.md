# CA-15 projection and integrity contract — v0.16.0

## SSOT boundary

- юридический и исполнимый корень: `Ferum Service Project`;
- факты исполнения, evidence, billing и accounting остаются в собственных source DocType;
- стандартные submitted ERPNext Sales/Purchase Invoice и Payment Entry остаются accounting SSOT;
- `Ferum Project Finance Summary` — перестраиваемая read model;
- CA-15 endpoints не создают persistent trace/cache/ledger records.

## E2E response

`contract_accounting.api.integration.get_end_to_end_trace(service_project, as_of)` возвращает:

1. `why` — Requirement/Obligation;
2. `where` — Project Object/Object System;
3. `when` — Schedule/deadline sources;
4. `who` — Assignment/engineer/responsible source;
5. `result` — Visit/Request/Finding;
6. `evidence` — Photo Evidence/Project Document;
7. `billing` — Billing Output и разрешённые Sales Invoice sources;
8. `payment` — разрешённые submitted Payment Entry references;
9. `margin` — разрешённая Finance Summary projection.

`cross_cutting_dimensions` отдельно возвращает contractor/material/cost/document/communication/deadline/audit rows. Finance-derived dimensions имеют `access=restricted` и пустые items, если роль не проходит единый CA-07 finance predicate.

Каждая доступная строка содержит exact `source_doctype`, `source_name` и `drilldown`. `source_fingerprint` исключает `generated_at`, поэтому одинаковый набор source facts даёт одинаковый fingerprint.

## Integrity dry-run

`contract_accounting.api.integration.get_project_integrity_report(service_project)`:

- разрешён только System Manager, Генеральному директору и Руководителю проектов;
- сканирует только читаемые записи выбранного Service Project и связанные Object System;
- классифицирует edge как `valid`, `optional_absent`, `missing_required`, `orphan` или `project_mismatch`;
- формирует stable `issue_key` из code/source/field/target;
- возвращает `records_hidden_by_permission` и не выдаёт ложную полноту для невидимых строк;
- не пишет и не исправляет данные.

Это project-scoped diagnostic, а не completed migration reconciliation. Portfolio-wide scan, exception approval registry, backfill/cutover/rollback и volume benchmark остаются OPEN.

## UI boundary

Три standard Page используют существующие whitelisted read APIs. Runtime подтверждает их metadata и role lists; `bench build` подтверждает asset compilation. Interactive browser/UAT, route restoration, export/report и accessibility не подтверждены.

## Import Batch

Capability state жёстко возвращается как `INACTIVE_NOT_PRODUCTION_PROVEN_PENDING_MG-CA-023`. Наличие historical model/FSM не считается entrypoint или E2E runtime evidence.
