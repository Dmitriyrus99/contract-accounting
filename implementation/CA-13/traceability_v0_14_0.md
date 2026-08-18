# CA-13 implementation traceability — v0.14.0

CA-13 содержит 11 exact req-id. Таблица не изменяет исходную `07_traceability.csv` и не присваивает blanket PASS инкременту.

| Requirement | Реализованное CODE/runtime evidence | Вердикт v0.14.0 |
| --- | --- | --- |
| `TCA-B-21-01` | отдельный parent Billing Cycle и отдельный Period Closing Process | CODE/runtime PASS |
| `TCA-B-21-02` | create требует минимум один accepted Visit/Resolved Request exact period | CODE/runtime PASS; automatic trigger OPEN |
| `TCA-B-21-03` | `WORK_COMPLETED`/`EXECUTION_CONFIRMED` требуют accepted-work context и Validated evidence | CODE/runtime PASS; external confirmation automation OPEN |
| `TCA-B-21-04` | `ACT_PREPARED` требует Project Document exact Cycle; Conditional Mandatory/explicit NA | CODE/runtime PASS для Act branch |
| `TCA-B-21-05` | `INVOICE_PREPARED` принимает только submitted Sales Invoice exact Cycle | CODE/runtime PASS |
| `TCA-B-21-06` | `UPD_OR_SF_PREPARED` присутствует как blocking conditional step | PARTIAL: explicit NA runtime PASS; dedicated UPD/SF positive runtime OPEN |
| `TCA-B-21-07` | approval evidence и обязательный `Waiting Approval → Completed` FSM | CODE/runtime PASS |
| `TCA-B-21-08` | `DOCUMENTS_SENT` требует source-linked Outgoing Letter/Project Document | CODE/runtime PASS; transport integration OPEN |
| `TCA-B-21-09` | `CUSTOMER_RECEIPT` требует Project Document того же project и Validated evidence | CODE/runtime PASS; external acknowledgement integration OPEN |
| `TCA-B-21-10` | Payment evidence/trace только submitted standard Payment Entry; outstanding=0 блокирует/разрешает completion | CODE/runtime PASS; no Ferum GL write |
| `TCA-B-21-11` | unique project+period Cycle и immutable Published recurring template | CODE/runtime PASS; scheduler/automatic recurrence OPEN |

## Точно подтверждённые acceptance scenarios

- повтор template installer/migrate сохраняет один Published graph из 1 stage/9 steps и не создаёт Cycle history;
- Cycle не создаётся до accepted work и повтор exact idempotency key возвращает тот же Cycle;
- projection показывает expected=1, accepted=1, unbilled=1 до Output и unbilled=0 после basis claim;
- correction сохраняет оба Output в одном Cycle, старый immutable history и один active claim;
- reverse trace Visit→Cycle и Payment Entry→Cycle возвращает exact ID;
- Approval не завершается в обход Waiting Approval;
- стандартный Payment Entry обнуляет invoice outstanding; Passed Gate/Completed Process разрешают Completed Cycle;
- Open Cycle с просроченным explicit `as_of` попадает в control feed как `Overdue Billing Cycle`;
- Billing Cycle/Output не создают GL Entry.

Не присваивается PASS automatic schedule/recurrence, dedicated positive UPD/SF branch, external delivery/receipt integration, legacy backfill rehearsal, CA-14 My Actions UI, performance/load/race, UAT/sign-off или production deployment.
