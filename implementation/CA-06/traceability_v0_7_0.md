# CA-06 implementation traceability — v0.7.0

Файл фиксирует фактический CODE/runtime результат и не переписывает discovery CSV.

| Requirement | CODE/runtime evidence | Вердикт инкремента |
| --- | --- | --- |
| `TCA-A-09-01` | Output требует Link на submitted стандартный `Sales Invoice`; invoice остаётся accounting SSOT | CODE/runtime PASS |
| `TCA-A-09-02` | собственный Payment DocType/API отсутствует; стандартный `Payment Entry` не изменяется | schema/CODE PASS |
| `TCA-A-09-03` | CA-06 не пишет в `GL Entry`/`Payment Ledger Entry`; runtime сравнивает количество строк до/после Output | CODE/runtime PASS |
| `TCA-A-09-04` | parent `Ferum Billing Output` с project/period/type/lifecycle/invoice/basis | schema/runtime PASS |
| `TCA-A-09-05…08` | точный enum `Invoice Print / Act / UPD / Invoice Factura`; Correction — controlled supersession output | schema/runtime PASS |
| `TCA-A-10-01` | selector + immutable child rows дают точное множество accepted applicable unclaimed sources | CODE/runtime PASS |
| `TCA-A-10-02` | trace API раскрывает Output → basis source → Invoice → Artifact → Project Document/Event | CODE/runtime PASS |
| `TCA-A-10-03` | `get_unbilled_accepted_work` возвращает accepted Visit/Request без active claim | CODE/runtime PASS |
| `TCA-A-18-15` | физический `Ferum Billing Output` установлен clean install | runtime PASS |
| `TCA-A-18-16` | физический versioned `Ferum Billing Artifact` установлен clean install | runtime PASS |
| `OQ-CA-008` | child basis row хранит source, acceptance snapshot/hash, amount/period и reversible claim; supersede сохраняет old/new trace | CODE/runtime PASS |

Дополнительно runtime подтверждает unique active claim, неизменяемость issued basis, Final/Signed projection в CA-05, File deletion guard, insert-only event, блокировку отмены связанного Invoice и отсутствие custom ledger writes.

Не присваивается PASS для печатных/ЭДО артефактов, бухгалтерского UAT, legal sign-off, race/load или production deployment.
