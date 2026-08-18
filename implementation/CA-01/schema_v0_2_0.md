# CA-01 schema evidence — v0.2.0

**Статус:** `STATIC + BENCH RUNTIME VERIFIED AT 23b0dff`.

**Дата:** 2026-08-18.

Версия 0.2.0 расширяет подтверждённый contract root v0.1.0 прямыми TARGET-связями и object hierarchy. Второй `Ferum Contract` или `Ferum Project Contract Link` не создаётся.

## Физическая модель

| DocType | Тип | Владелец / ключевая связь |
| --- | --- | --- |
| `Ferum Service Project` | parent | единый legal/execution contract root |
| `Ferum Lifecycle Audit Event` | parent, insert-only | `service_project` |
| `Ferum Contract Amendment` | parent, append-only lifecycle | обязательный `service_project` |
| `Ferum Contract Amendment Change` | child | structured field old/new JSON |
| `Ferum Contract Execution Stage` | parent | обязательный `service_project` |
| `Ferum Contract Security` | parent | обязательный `service_project` |
| `Ferum Contract Financial Plan Row` | child | Table `Service Project.financial_plan` |
| `Ferum Service Object` | parent master | Customer-owned object; прямой project link отсутствует |
| `Ferum Project Object` | parent effective membership | `service_project` + `service_object` |
| `Ferum Object System` | parent | обязательный `service_object` |

Физический inventory после migrate/reinstall: 10 DocType, 143 DocField, 58 DocPerm. Link-полей с options `Ferum Contract` или `Ferum Project Contract Link`: 0.

## Service Project

К v0.1.0 добавлены:

- `project_manager`;
- `procurement_law` с точными вариантами `44-ФЗ`, `223-ФЗ`, `Commercial`;
- `procurement_number`, `igk`, `source_advance`;
- `performance_security_percent`, `quality_guarantee_terms`;
- child Table `financial_plan`;
- reverse links Amendment, Execution Stage, Security и Project Object.

После legal status `Signed`/`In Force` и в terminal legal states договорные суммы, сроки, payment/security/guarantee terms и financial plan не меняются прямым save. Разрешён только выделенный server flag Amendment apply. Lifecycle fields сохраняют отдельный typed writer из v0.1.0.

## Amendment

Lifecycle: `Draft → Under Review → Approved → Applied`; из `Under Review` разрешён `Rejected`. Applied/Rejected terminal и append-only.

- Юрист подаёт Draft на review;
- Генеральный директор approve/reject/apply;
- System Manager — техническая роль;
- shape и роли перехода проверяются server-side;
- `(service_project, amendment_number)` физически unique;
- change rows проходят field allowlist, unique field check и JSON validation;
- apply сверяет old value с текущим состоянием, fail-closed отказывает при concurrent conflict, сохраняет before/after snapshots и только затем меняет Service Project в той же внешней DB-транзакции.

До CA-05 `source_document_reference` остаётся Data reference. Он не объявляется доказанной Link-связью с ещё не реализованным `Ferum Project Document`.

## Object hierarchy

Навигация: `Service Project → Project Object → Service Object → Object System`.

`Project Object` проверяет:

- Customer объекта равен Customer договора;
- интервал находится внутри заданного срока договора;
- интервалы одной пары Project/Object не пересекаются;
- root/object/effective_from неизменяемы после insert;
- закрытая строка не переоткрывается и не удаляется;
- added/removed Amendment относится к тому же Service Project.

Service Object не содержит прямого `service_project`: участие в договорах моделируется только effective membership. Object System классифицирует APS, SOUE, Smoke Control, Internal Fire Water, suppression, ACS, CCTV, Intrusion Alarm, Monitoring и Other; покомпонентный учёт оборудования не требуется.

## Stage, Security и Financial Plan

- Execution Stage: unique `(service_project, stage_number)`, проверка execution/service period и same-project Amendment;
- Security: same-project Amendment, date ordering, non-negative amounts, индексы project/status и expiry/status;
- Financial Plan: period, revenue/cost/cash-in/cash-out/tax plan, optional source Stage/Amendment; currency и обе ссылки обязаны совпадать с parent Service Project. Это план, не бухгалтерский ledger.

## Незакрытые границы

- Project Document и типизированные original/appendix links — CA-05;
- Scope/SLA/maintenance frequency — CA-02/CA-03;
- post-expiry closing documents/AR — CA-06/CA-07;
- full site backup restore, worker/queue E2E, UAT/legal/finance и production deployment — не подтверждены.

Runtime evidence: [runtime_evidence_v0_2_0_2026-08-18.md](runtime_evidence_v0_2_0_2026-08-18.md).
