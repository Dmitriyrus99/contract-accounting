# CA-02 schema evidence — v0.3.0

**Статус:** `STATIC + BENCH RUNTIME VERIFIED AT b52f61b`.

**Дата:** 2026-08-18.

## Физическая модель

| DocType | Тип | Назначение |
| --- | --- | --- |
| `Ferum Contract Requirement` | parent | source clause, applicability, assessment и routing |
| `Ferum Contract Obligation` | parent | нормализованное recurring promise «что/где/когда» |
| `Ferum Obligation Recurrence Rule` | child | frequency/interval/anchor/window/due offset/calendar/horizon |

После clean install приложение содержит 13 custom DocType. CA-02 добавляет 48 DocField и 9 DocPerm; полей с options `Ferum Contract` или `Ferum Project Contract Link` — 0. Составной source index Requirement физически создан как `ca_req_source_idx`; короткое имя необходимо из-за MariaDB identifier limit 64.

## Requirement lifecycle и routing

Assessment FSM: `Draft → Assessed → Approved|Rejected`; Approved/Rejected terminal и immutable. Assessment/approval роли проверяются server-side, Administrator остаётся техническим bypass. `assessed_by/assessed_on` задаёт сервер.

Routing choices фиксированы:

- `Recurring Obligation` — только Applicable Requirement;
- `One-time Process Step` — точка интеграции CA-11;
- `Informational`;
- `Not Applicable` — только с такой же applicability.

Approved Requirement обязан иметь route. Source uniqueness проверяется по `(service_project, source_document_reference, source_clause, requirement_type)`. До CA-05 `source_document_reference` — Data с явным описанием временной границы.

## Obligation integrity

Lifecycle: `Draft → Active|Cancelled`, `Active → Suspended|Closed`, `Suspended → Active|Closed`; terminal state не переоткрывается. Activation требует Approved + Applicable + Recurring Requirement.

Server-side проверяются:

- Requirement и Project Object принадлежат одному Service Project;
- Object System входит в Service Object выбранного Project Object;
- effective interval Obligation полностью входит в interval Project Object;
- currency совпадает с Service Project;
- active versions одного business context не пересекаются;
- обязательные recurrence rules, positive interval/horizon, non-negative window, valid JSON objects;
- Dynamic Link party pair заполнена целиком и ограничена `Company`, `Customer`, `Supplier`;
- identity и recurrence после activation не меняются; закрытие effective period допустимо как controlled version boundary.

Reverse links добавлены в Service Project, Requirement, Project Object и Object System.

## Recurrence preview

Pure domain поддерживает Daily, Weekly, Monthly, Quarterly, Semiannual, Annual. Месячные периоды вычисляются от исходного anchor, поэтому `31 Jan → 28 Feb → 31 Mar`, без накопительного дрейфа. Результат содержит period key, planned/due date и allowed window, ограничивается effective period и generation horizon, дедуплицирует одинаковые правила и отклоняет конфликтующие правила для одной даты.

CA-02 реализует только `Contract Start` + `Calendar Days`: непроверенные Working Days/Holiday List/Custom не имитируются и fail-closed не допускаются.

## Не закрыто этой схемой

- Schedule/Visit writer, period-key provenance и cancelled-period policy — CA-03;
- Project Document Link — CA-05;
- generic SLA/holiday/deadline engine — CA-09;
- one-time Process Step materialization — CA-11;
- legacy Scope backfill и combined-app DB rehearsal — отдельный migration gate, не выполнялся на clean disposable site.
