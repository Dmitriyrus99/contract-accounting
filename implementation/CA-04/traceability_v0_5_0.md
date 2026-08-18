# CA-04 implementation traceability — v0.5.0

Файл фиксирует фактический CODE/runtime результат и не переписывает discovery CSV.

| Requirement | CODE/runtime evidence | Вердикт инкремента |
| --- | --- | --- |
| `TCA-A-07-01` | один parent `Ferum Finding`, обязательная category; `Ferum Defect` отсутствует | CODE + runtime PASS |
| `TCA-A-07-02…03` | независимые Finding confirmation/resolution FSM; Service Request и Visit остаются отдельными DocType/ID | CODE + runtime PASS |
| `TCA-A-07-04` | immutable Dynamic Link source на Maintenance Visit с reverse-queryable tuple | CODE + runtime PASS; Inspection CA-12 OPEN |
| `TCA-A-07-05` | обязательные title/description, immutable после confirmation | schema/runtime PASS |
| `TCA-A-07-06` | точный decision enum: contract fix/additional work/customer notification/monitoring | schema/runtime PASS |
| `TCA-A-07-07` | idempotent child Dynamic Link на Service Request; source не меняется | CODE + runtime PASS; work-order adapter OPEN |
| `TCA-A-07-08` | resolution class/text/evidence/server actor/time и immutable close | CODE + runtime PASS |
| `TCA-A-18-06…08` | CA-03 Schedule/Visit/Service Request regression scenarios | runtime PASS |
| `TCA-A-18-09` | physical Finding/category Defect без отдельного Defect | schema/runtime PASS |
| `TCA-A-18-10` | physical Photo Evidence с source, File hash, review actor/time и immutability | schema/runtime PASS; contractor row-level CA-08 OPEN |

Дополнительно подтверждены physical unique keys execution links, exception report и отсутствие автоматической Service Request creation.

Contractor не получает Finding/Photo Evidence permissions в текущем role fixture, поэтому доступ к чужим проектам не открыт. Положительная проверка «contractor видит только собственное назначение» остаётся CA-08 и не считается выполненной CA-04.
