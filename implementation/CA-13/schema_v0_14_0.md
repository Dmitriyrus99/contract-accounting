# CA-13 physical schema and command contract — v0.14.0

**Статус:** `RECURRING BILLING CYCLE + PERIOD GATE BENCH VERIFIED AT c6e591b`.

## Physical model

| Entity | Назначение | Ключевой invariant |
| --- | --- | --- |
| `Ferum Billing Cycle` | один recurring closing cycle проекта/периода | unique idempotency key и unique `(service_project, period_start, period_end)`; typed lifecycle only |
| `Ferum Project Process` | frozen Period Closing instance | `process_type=Period Closing`; exact reference template/version |
| `Ferum Billing Output.billing_cycle` | двусторонняя связь document set с Cycle | project/period должны совпадать; link controlled; correction наследует Cycle |

Cycle хранит Service Project, Project Process, exact period key `YYYY-MM-DD..YYYY-MM-DD`, explicit due date, immutable expected-work snapshot, completion snapshot и actor/time. Статусы: `Open → Completed|Cancelled`; физическое удаление запрещено.

В Cycle нет debit/credit/paid amount/GL fields. Accepted work пересчитывается из Maintenance Visit и Service Request; Billing Basis остаётся immutable CA-06 snapshot; invoice и outstanding берутся из submitted Sales Invoice; payment trace — из submitted Payment Entry Reference/Payment Entry.

## Reference Process Template

Published `FERUM-BILLING-CYCLE` v1 содержит stage `PERIOD_CLOSING` и 9 step codes:

1. `WORK_COMPLETED`;
2. `EXECUTION_CONFIRMED`;
3. `ACT_PREPARED`;
4. `INVOICE_PREPARED`;
5. `UPD_OR_SF_PREPARED`;
6. `DOCUMENTS_APPROVED`;
7. `DOCUMENTS_SENT`;
8. `CUSTOMER_RECEIPT`;
9. `PAYMENT_RECEIVED`.

Все шаги blocking и последовательны. Act и UPD/SF имеют Conditional Mandatory criticality, но Gate принимает неприменимость только как CA-11 `Not Applicable` с явной причиной. Approval завершается из `Waiting Approval`; Payment evidence принимает только submitted Payment Entry, ссылающийся на invoice того же Cycle.

## Commands и projections

- `create_billing_cycle`: требует Active/Completed project и минимум один accepted result exact period; создаёт frozen Process/Cycle идемпотентно;
- `get_billing_cycle_projection`: read-only expected/accepted/unbilled/billed/documents/payment/milestone/gate state с optional explicit `as_of`;
- `complete_billing_cycle`: проверяет Completed Process, accepted work, zero unbilled/foreign claims, Signed active outputs и fully paid invoices;
- `cancel_billing_cycle`: только Open и без Issued/Signed outputs;
- `resolve_billing_cycles_for_source`: reverse trace для Visit/Request/Output/Sales Invoice/Payment Entry;
- `get_billing_cycle_backfill_assessment`: read-only candidate/conflict report;
- `backfill_billing_cycle_group`: exact confirmation token и только Draft/Generated outputs одного точного периода.

Billing Output `supersede` создаёт Correction в том же Cycle, сохраняет старый Output/Basis/Event history и переносит active basis claim штатным CA-06 способом.

## Deadline/control integration

`Billing Cycle.due_date` включён в rebuildable CA-09 timeline. Классификация overdue включается только при explicit `as_of`; Open overdue Cycle выдаёт source-linked `Overdue Billing Cycle` exception в Contract 360/Director Center. Автоматическая notification/escalation delivery остаётся OPEN.

## Migration boundary

Migrate устанавливает только schema и exact Published template; Cycle history не создаётся. Explicit backfill блокирует любую группу с Issued/Signed/terminal output и не меняет юридический документ. Runtime rehearsal backfill на representative legacy dataset не выполнялся.
