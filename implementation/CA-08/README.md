# CA-08 — contractor assignment and guarded personnel topology

**Статус:** `CA-08 PARTIAL — ASSIGNMENT/COMMERCIAL CORE v0.9.0 BENCH VERIFIED; PERSONNEL READINESS BLOCKED BY MG-CA-015`.

Инкремент отделяет операционное назначение «кто/где/что/когда» от pricing и settlement. `Ferum Contractor Assignment` связывает единый `Ferum Service Project` с Supplier либо Employee, Project Object, optional Object System/Obligation, work type, responsibility и effective interval. Цены не хранятся в Assignment: отдельные `Ferum Contractor Commercial Terms` содержат client price, contractor cost и derived margin, а фактические начисление/оплата остаются в `Ferum Contractor Settlement` и стандартном `Payment Entry`.

Supplier-level Assignment доступен подрядчику только при совпадающем standard `User Permission` на Supplier. Один Supplier может быть назначен параллельно на другие object/system/work-type dimensions, но пересекающиеся active intervals одной dimension отклоняются.

`Ferum Contractor Worker` и `Ferum Personnel Credential` установлены только как schema/privacy spike. Их controllers безусловно отклоняют insert/update/delete до MG-CA-015; mutating API отсутствует, паспортных полей нет, `credentials_readiness` всегда `Disabled Pending MG-CA-015`, gate `PERSONNEL READY` не реализован.

FR-05 owners, field registry, purpose/retention/RBAC/private-file/break-glass decisions и FR-06 change-set заполнены в [legal/privacy package v1](legal_privacy_package_fr05_v1.md). Product Owner подписал свою строку 2026-08-19; Legal, Privacy/DPO, Security и Data Owner/HR signatures, FR-06 CODE/UAT и production-data permission остаются OPEN.

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

## Открытая граница

Не выполнялись production Worker/Credential data, Employee positive runtime, credential matching/expiry, `PERSONNEL READY`, cross-entity positive portal access к Finding/Photo/Visit, legacy assignment migration, concurrent overlap race/load, HR/privacy/legal UAT и production deployment. Эти пункты нельзя закрыть owner approval: для них требуется MG-CA-015 и последующая CA-12 реализация/приёмка.
