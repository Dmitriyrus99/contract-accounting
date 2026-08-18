# CA-09 implementation traceability — v0.10.0

Файл фиксирует CODE/runtime coverage, не переписывает discovery CSV и не закрывает MG-CA-013.

| Requirement | CODE/runtime evidence | Вердикт инкремента |
| --- | --- | --- |
| `TCA-A-14-01` | единый read-only projection + pure snapshot calculator; editable `Ferum Deadline` намеренно не создан по approved roadmap | PARTIAL: projection PASS, production engine OPEN |
| `TCA-A-14-02` | Service Project `effective_from` → Contract Start | CODE/runtime PASS при наличии source date |
| `TCA-A-14-03` | Service Project `effective_to` → Contract Expiry | CODE/runtime PASS при наличии source date |
| `TCA-A-14-04` | Maintenance Schedule `due_date` | CODE/runtime PASS |
| `TCA-A-14-05` | Service Request reaction/resolution dates | PARTIAL: company reaction/resolution PASS |
| `TCA-A-14-06` | Execution Stage `acceptance_due_date` → Acceptance Due | CODE/runtime PASS |
| `TCA-A-14-07` | Execution Stage `billing_due_date` → Billing Issue Due | CODE/runtime PASS |
| `TCA-A-14-08` | Stage `payment_due_date` и submitted Sales Invoice `due_date` | CODE/runtime PASS |
| `TCA-A-14-09` | структурированного первичного signature deadline нет | OPEN; date не изобретается |
| `TCA-A-14-10` | Contract Security reminder/validity/return dates | CODE/runtime PASS |
| `TCA-A-14-11` | `security_method=Independent Guarantee` нормализуется как Bank Guarantee Expiry | CODE/runtime PASS |
| `TCA-A-14-12` | Warranty Obligations Security expiry поддержан; `quality_guarantee_terms` остаётся текстом | PARTIAL |
| `TCA-A-14-13` | reaction_due не переименован в customer response: иной business meaning | OPEN; нужен primary source field |
| `OQ-CA-013 / MG-CA-013` | explicit immutable calendar snapshot и deterministic hash протестированы; production values отсутствуют, automatic classification disabled | FAIL-CLOSED PARTIAL; gate OPEN |

Дополнительно projection включает Project Document expiry/original expected и Finding resolution due. Это source-linked read model, а не расширение требований новым SSOT.

Не присваивается PASS scheduler/notification delivery, BPM dates CA-11, production warning/escalation, representative-volume latency, UAT/sign-off или deployment.
