# CA-08 — contractor assignment and guarded personnel topology

**Статус:** `CA-08/FR-06 PARTIAL — CURRENT LOCAL STATIC/FULL DISPOSABLE BENCH + FULL-STACK SYNTHETIC ENGINEER ACL PASS; PRIOR ROLE MATRIX SUPERSEDED; UI REVIEW AND HUMAN UAT PENDING; PRODUCTION PII DISABLED`.

Инкремент отделяет операционное назначение «кто/где/что/когда» от pricing и settlement. `Ferum Contractor Assignment` связывает единый `Ferum Service Project` с Supplier либо Employee, Project Object, optional Object System/Obligation, work type, responsibility и effective interval. Цены не хранятся в Assignment: отдельные `Ferum Contractor Commercial Terms` содержат client price, contractor cost и derived margin, а фактические начисление/оплата остаются в `Ferum Contractor Settlement` и стандартном `Payment Entry`.

Supplier-level Assignment доступен подрядчику только при совпадающем standard `User Permission` на Supplier. Один Supplier может быть назначен параллельно на другие object/system/work-type dimensions, но пересекающиеся active intervals одной dimension отклоняются.

В v0.20.0 прежний schema/privacy spike заменён fail-closed FR-06 implementation: typed Worker/Credential FSM, versioned policy stamp, dual verification, masking, project-scoped RBAC, private-file guard, live readiness fingerprint, exact-target break-glass, joint legal hold и dry-run-first retention. Production activation отделена от Synthetic Test и не выполнялась; `PERSONNEL_READY` positive path требует активную policy и актуальное PM confirmation.

FR-05 owners, field registry, purpose/retention/RBAC/private-file/break-glass decisions и FR-06 change-set заполнены в [legal/privacy package v1](legal_privacy_package_fr05_v1.md). Product Owner подписал пакет и 2026-08-19 аттестовал получение подтверждений от Legal/Privacy/DPO, Security и Data Owner/HR; номера формальных актов не предоставлены. Human sign-off закрыт в этой границе. Earlier credential-specific Bench and 12-role matrix сохранены как historical provenance. Current accepted local evidence on Friday, August 21, 2026 — static `209/209`, scoped policy `9/9`, alias/retention `24/24`, File boundaries `3/3`, full disposable Bench `179/179 OK`, and the full-stack Engineer own/foreign browser slice with `socket.io` polling `200`; blanket browser/File acceptance остаётся OPEN. До реальных пользователей обязательно совместно утвердить Workspace, списки, формы/labels и timezone; actual scanner, human UAT, hosted CI on the current change-set и отдельное production-data permission остаются OPEN.

Typed API: [contractors.py](../../contract_accounting/api/contractors.py).

Supplier isolation: [contractor_permissions.py](../../contract_accounting/infrastructure/contractor_permissions.py).

Схема и privacy boundary: [schema_v0_9_0.md](schema_v0_9_0.md).

Runtime evidence: [runtime_evidence_v0_9_0_2026-08-18.md](runtime_evidence_v0_9_0_2026-08-18.md).

Implementation traceability: [traceability_v0_9_0.md](traceability_v0_9_0.md).

## Подтверждённые проверки

- standalone unit/schema suite: `96 tests`, `OK`;
- compileall, parse 36 JSON и `git diff --check`: PASS;
- Ruff для CA-08-owned modules: PASS; repository-wide 33-item baseline debt остаётся OPEN;
- PEP 517 wheel v0.9.0: PASS;
- ERPNext v15 migrate v0.8.0 → v0.9.0: PASS;
- targeted CA-08 Frappe suite: `6/6`, `OK`;
- foreground full-app suite: `47/47`, `OK`;
- controlled uninstall/install/migrate: 35 DocType, contractor role и adapters восстановлены;
- post-reinstall full-app suite: `47/47`, `OK`.

## Открытая граница v0.20.0

Authenticated synthetic browser cross-role/RBAC matrix выполнена, но не является human UAT. Не выполнялись actual scanner integration, concurrent race/load, HR/DPO/Security human UAT, production activation и deployment. До совместного Product Owner UI review и отдельного production-PII permission settings остаются Disabled, а `MG-CA-015` — PARTIAL.
