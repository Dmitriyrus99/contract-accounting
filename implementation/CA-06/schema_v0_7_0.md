# CA-06 schema evidence — v0.7.0

**Статус:** `STATIC + BENCH RUNTIME VERIFIED AT 5b2d79a`.

**Дата:** 2026-08-18.

## Физическая модель

| DocType | Тип | Назначение |
| --- | --- | --- |
| `Ferum Billing Output` | parent | документарный Act/UPD/Invoice output над стандартным Sales Invoice |
| `Ferum Billing Basis Item` | child | immutable snapshot строки принятой выработки и active claim |
| `Ferum Billing Artifact` | parent | versioned generated/signed File и projection в Project Document |
| `Ferum Billing Event` | parent, insert-only | неизменяемое событие billing-команды |

После clean install приложение содержит 28 custom DocType. В стандартный `Sales Invoice` штатным Custom Field добавляется только `ferum_service_project` (Link → `Ferum Service Project`). Собственные Invoice, Payment, GL или Payment Ledger DocType отсутствуют.

## Billing Output и Basis

Output хранит Service Project, company/customer/currency, submitted Sales Invoice, период, тип `Invoice Print / Act / UPD / Invoice Factura / Correction`, optional UPD status, basis hash/amount и lifecycle `Draft / Generated / Issued / Signed / Superseded / Cancelled`.

Контекст выводится сервером из Service Project и проверяется против стандартного Sales Invoice. Идентичность после insert неизменяема. Issue требует current Final artifact, юридический номер и server actor/time. Signed требует Signed Scan artifact и server stamps.

Selector возвращает только:

- `Ferum Maintenance Visit` с `acceptance_status=Accepted`, `billing_eligible=1`, complete provenance и датой результата в периоде;
- `Ferum Service Request` в `Resolved/Closed`, с `Completed/Partially Completed`, evidence и датой результата в периоде;
- источники без активного claim другого Draft/Generated/Issued/Signed Output.

Basis row фиксирует source DocType/name, Obligation/Object/System, result date/period key, quantity/UOM/amount/currency, acceptance actor/time, canonical JSON snapshot и SHA-256. `active_claim_key` имеет unique constraint. На issue и после него snapshot сравнивается канонически и не меняется; cancel/supersede переводит claim в `Reversed` без стирания истории.

## Artifact, Project Document и аудит

Artifact связывает стандартный `File`, server content hash, тип `Generated / Signed Scan / Other`, mode `Preview / Final`, version/current key и predecessor. Регистрируется только typed API. Новый current artifact делает прежний non-current, не перезаписывая историю.

Final Generated и Signed Scan проецируются в `Ferum Project Document` CA-05. Generated copy проходит Uploaded → Verified → Active; Signed Scan — Uploaded → Signed → Active. Удаление File, на который ссылается Billing Artifact, блокируется.

Event создаётся только CA-06 writer, хранит actor/time, reason, correlation и related Output/Artifact. Update/delete запрещены.

## Standard accounting boundary

Hook `Sales Invoice.validate` проверяет company/customer проекта, а `before_cancel` блокирует отмену Invoice, пока существует активный Billing Output. После cancel/supersede Output штатная отмена Invoice разрешается. CA-06 не вызывает submit/cancel Invoice автоматически и не создаёт/изменяет GL Entry, Payment Ledger Entry или Payment Entry.

## Не закрыто этой схемой

- PDF/печатные формы, XML/УПД, ЭДО и КЭП;
- Purchase Invoice и contractor billing (CA-07/08 downstream);
- concurrent load/race test, бухгалтерский UAT, legal/operations sign-off и production deployment.
