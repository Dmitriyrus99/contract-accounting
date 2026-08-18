# CA-08 schema evidence — v0.9.0

**Статус:** `ASSIGNMENT/COMMERCIAL STATIC + BENCH VERIFIED AT 9af7a67; PERSONNEL SCHEMA FAIL-CLOSED`.

**Дата:** 2026-08-18.

## Физическая модель

| DocType | Runtime status | Назначение |
| --- | --- | --- |
| `Ferum Contractor Assignment` | enabled | effective-dated operational responsibility без pricing SSOT |
| `Ferum Contractor Commercial Terms` | enabled | отдельный approved commercial basis и derived margin |
| `Ferum Contractor Worker` | disabled pending MG-CA-015 | protected external-worker topology, records forbidden |
| `Ferum Personnel Credential` | disabled pending MG-CA-015 | Employee/Worker holder topology, records forbidden |

После clean install приложение содержит 35 custom DocType, role `Подрядчик` и прежние Sales/Purchase Invoice adapters. `Ferum Contractor Payment` не создаётся: target-модель сохраняет `Ferum Contractor Settlement`, а платёжным SSOT остаётся standard `Payment Entry`.

## Contractor Assignment

Assignment хранит Service Project/company, `execution_mode=Internal|Contractor`, XOR executor (`employee` либо `supplier`; external worker link выключен), Project Object, optional Object System/Contract Obligation, work type, responsibility, effective dates и lifecycle `Draft / Approved / Suspended / Completed / Cancelled`.

Server invariants:

- Project Object принадлежит Service Project; Object System принадлежит Service Object membership;
- optional Obligation совпадает по project/object/system/work type;
- Contractor требует Supplier и запрещает Employee; Internal требует Employee той же Company и запрещает Supplier;
- interval находится внутри договора и Project Object membership;
- Approved/Suspended interval не пересекается с другим active Assignment той же executor/object/system/work-type dimension;
- lifecycle и post-approval identity меняются только typed commands;
- физический unique `overlap_guard_key` страхует exact duplicate, а interval check отклоняет последовательные overlap attempts;
- `contractor_worker` и readiness fail-closed до MG-CA-015.

Роль `Подрядчик` имеет только read. `permission_query_conditions` и `has_permission` разрешают Assignment только для Supplier values из standard `User Permission`; без них результат пуст и direct read отклоняется.

## Commercial Terms и settlement

Terms создаются только для Contractor Assignment и наследуют project/company/supplier/object/system/work type/currency. Effective interval не выходит за Assignment; пустой `effective_to` наследуется. Lifecycle: `Draft → Approved / Cancelled`, approved identity immutable. Один Assignment имеет не более одного Approved terms row за счёт unique claim.

Поля `client_price`, `contractor_cost`, `margin_amount` и `margin_percent` принадлежат Terms, не Assignment. Approved Terms автоматически связываются с Assignment; Cancelled Terms отвязываются, если не используются признанным Settlement. `Ferum Contractor Settlement` и `Ferum Material Expense` получили optional Link на Assignment, Settlement — также Link на Approved Terms. Supplier/project/basis consistency проверяется сервером.

## Privacy boundary MG-CA-015

Worker содержит только proposed minimal metadata topology на permlevel 1; паспортных полей нет. Credential имеет `holder_type + holder` Dynamic Link и code allowlist `Employee | Ferum Contractor Worker`. Оба DocType не имеют create/write/delete DocPerm, не имеют mutating API и безусловно выбрасывают PermissionError при попытке записи даже с `ignore_permissions=True`.

Это не production-ready privacy model. Legal basis, consent, retention, protected-field allowlist, role/export/delete policy, encryption, audit и data-subject workflow отсутствуют, поэтому records/readiness остаются технически заблокированы.

## Не закрыто

- Employee positive runtime и одинаковая credential evaluation для Employee/Worker;
- qualification matching, expiry и PERSONNEL READY gate CA-12;
- positive assigned-only access к связанным Finding/Photo/Visit/Request;
- conflict migration from legacy direct contractor links;
- concurrent overlap/load qualification, UAT/sign-off и production deployment.
