# CA-03 implementation traceability — v0.4.0

Файл фиксирует фактический CODE/runtime результат и не переписывает discovery CSV.

| Requirement | CODE/runtime evidence | Вердикт инкремента |
| --- | --- | --- |
| `TCA-A-05-01…03` | Contract root→Obligation→unique Schedule→primary Visit | CODE + runtime PASS |
| `TCA-A-05-04` | Visit child evidence требует Link на физический File | CODE + runtime PASS |
| `TCA-A-05-05` | Completed→PM review gate, reviewed snapshot immutable | CODE + runtime PASS |
| `TCA-A-05-06…08` | Act/Invoice/Payment не создаются CA-03 | CA-06/07 OPEN |
| `TCA-A-05-09` | reverse Obligation/Schedule/Visit + deviation query | PARTIAL PASS; billing reverse chain OPEN |
| `TCA-A-06-01…08` | generated Visit, planned/actual, assignee, checklist, File evidence, comment | schema/runtime PASS |
| `TCA-A-06-09` | CA-04 `Ferum Finding.source` даёт reverse provenance на Visit без изменения факта Visit | CA-04 CODE + runtime PASS |
| `TCA-A-06-10…11` | recommendations/report + PM review FSM | schema/runtime PASS |
| `TCA-A-06-12…16` | самостоятельный Service Request, project/object/system/customer guards | schema/runtime PASS |

Дополнительно подтверждены physical idempotency keys, explicit cancelled replacement, accepted fact immutability и отсутствие второго Contract/accounting SSOT.

Legacy Schedule/Visit backfill не выполнялся: combined legacy app отсутствует на disposable site. Неоднозначные исторические записи нельзя связывать автоматически без отдельного preview/reconciliation gate.
