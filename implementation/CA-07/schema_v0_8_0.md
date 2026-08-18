# CA-07 schema evidence — v0.8.0

**Статус:** `STATIC + BENCH RUNTIME VERIFIED AT f7217f3`.

**Дата:** 2026-08-18.

## Физическая модель

| DocType | Тип | Назначение |
| --- | --- | --- |
| `Ferum Project Finance Summary` | parent, service-managed | удаляемая read-model проекта, уникальная по `service_project` |
| `Ferum Material Expense` | parent | утверждаемая управленческая классификация материальных затрат |
| `Ferum Contractor Settlement` | parent | утверждаемый/оплаченный расчёт с Supplier за период |

После clean install приложение содержит 31 custom DocType. В стандартных документах установлены два узких Custom Field: `Sales Invoice-ferum_service_project` и `Purchase Invoice-ferum_service_project`, оба Link → `Ferum Service Project`. Собственных Invoice, Payment, GL или Payment Ledger DocType нет.

## Project Finance Summary

Summary хранит производные project/company/customer/manager/currency, contract amount, recognized revenue, invoiced, paid, outstanding, overdue AR, material/contractor/other/total cost, profit и profitability. Obligation и billing-cycle dimensions хранятся как JSON-проекции; canonical source payload имеет SHA-256 fingerprint и server timestamp.

Прямые insert/update/delete запрещены controller-ом, кроме внутреннего writer context rebuild. Один Service Project имеет не более одной строки Summary. GET API возвращают source trace, differences stored-vs-current и portfolio rollup; POST API перестраивают один или все доступные проекты.

Правила расчёта:

- только submitted standard Invoice и Payment Entry участвуют в trace;
- recognized revenue = сумма `Sales Invoice.base_net_total`, кроме `is_opening=Yes`;
- invoiced = `base_grand_total`, кроме opening Invoice;
- outstanding = стандартный outstanding Sales Invoice в base currency;
- paid = весь invoice gross, включая opening, минус outstanding;
- overdue = положительный outstanding Invoice с прошедшим due date;
- submitted Purchase Invoice попадает ровно в Material, Contractor или Other;
- утверждённая management-запись без Purchase Invoice добавляет base net/approved amount; при наличии PI сумма берётся из submitted PI и не дублируется;
- profit = recognized revenue − total cost; profitability пересчитывается из агрегированных profit/revenue;
- расчёт fail-closed, если валюта Service Project отличается от default currency Company; portfolio группируется по Company/currency.

## Material Expense и Contractor Settlement

Material Expense имеет FSM `Draft → Approved / Cancelled`, `Approved → Cancelled`. Контекст Project/Object/Obligation/Visit/Request выводится и проверяется сервером. Связанный Purchase Invoice должен быть submitted, относиться к тому же проекту и не иметь второй признанной классификации. Сущность не пишет Stock Ledger и не подменяет Stock Entry.

Contractor Settlement имеет FSM `Draft → Approved / Cancelled`, `Approved → Settled / Cancelled`. Он хранит Supplier, project/object/obligation, период, planned/approved/base amount, optional Purchase Invoice и Payment Entry, paid/payable. `Settled` требует submitted Pay/Supplier Payment Entry и полного покрытия approved amount. Это management settlement, а не operational Contractor Assignment CA-08.

Физический unique claim key и server guard не позволяют одному Purchase Invoice одновременно быть material и contractor cost. Отмена признанного PI блокируется, пока связанная management-классификация не отменена.

## Standard accounting boundary

Hooks на submit/cancel Sales Invoice, Purchase Invoice и Payment Entry ставят after-commit rebuild затронутых Service Project. Purchase Invoice validation проверяет Company проекта. Rebuild только читает стандартные accounting documents и записывает custom Summary; корректирующие GL entries не создаются.

## Не закрыто этой схемой

- VAT-specific breakdown/positive tax-row acceptance и отдельный tool/rent bucket;
- conversion/aggregation проектов не в Company currency;
- legacy migration comparison и автоматическое исправление расхождений;
- contractor operational assignment/personnel readiness CA-08;
- async worker/load/race qualification, Finance UAT, sign-off и production deployment.
