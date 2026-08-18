# CA-10 implementation traceability — v0.11.0

Файл фиксирует CODE/runtime coverage и не переписывает discovery CSV. `PASS` ниже относится только к реализованному read-model scope; UAT, UI, performance и production остаются отдельными gates.

| Requirement | CODE/runtime evidence | Вердикт инкремента |
| --- | --- | --- |
| `TCA-A-15-01` | overdue Maintenance из CA-09 timeline при explicit `as_of`, exact source drilldown | CODE/runtime PASS |
| `TCA-A-15-02` | отдельной структурированной policy «required photo» нет; accepted work без Billing Basis и pending review выявляются, но не подменяют это требование | OPEN/PARTIAL |
| `TCA-A-15-03` | completed Visit с `review_status=Pending` | CODE/runtime PASS |
| `TCA-A-15-04` | Service Project `effective_to` в 30-дневном окне | CODE/runtime PASS при explicit `as_of` |
| `TCA-A-15-05` | issued Act/UPD без signed/final state; overdue expected original из Project Document timeline | CODE/runtime PASS для структурированных sources |
| `TCA-A-15-06` | overdue AR из stored Finance Summary; unpaid submitted Sales Invoice при source permission | CODE/runtime PASS; finance role only |
| `TCA-A-15-07` | overdue `Bank Guarantee Expiry` из CA-09 Contract Security adapter | CODE/runtime PASS при explicit `as_of` |
| `TCA-A-15-08` | open `Ferum Finding(category=Defect)` старше 30 дней, exact source rule | CODE PASS; dedicated runtime fixture OPEN |
| `TCA-A-16-01` | Service Project identity and direct drilldown | CODE/runtime PASS |
| `TCA-A-16-02` | customer/company/project manager/status identity | CODE/runtime PASS |
| `TCA-A-16-03` | contract amount доступен только через finance summary/finance role, не через public identity | CODE/runtime PASS for permission boundary |
| `TCA-A-16-04` | legal/execution status pair и Director status matrix | CODE/runtime PASS |
| `TCA-A-16-05` | Project Object source rows | CODE/runtime PASS |
| `TCA-A-16-06` | Object System source rows | CODE/runtime PASS |
| `TCA-A-16-07` | Contract Requirement source rows | CODE/runtime PASS |
| `TCA-A-16-08` | Contract Obligation source rows | CODE/runtime PASS |
| `TCA-A-16-09` | Maintenance Schedule/Visit plan-fact counts and rows | CODE/runtime PASS |
| `TCA-A-16-10` | open Service Request count/rows | CODE/runtime PASS |
| `TCA-A-16-11` | open Finding count/rows | CODE/runtime PASS |
| `TCA-A-16-12` | Billing Output rows + stored finance recognized revenue | CODE/runtime PASS; finance role restriction preserved |
| `TCA-A-16-13` | stored Finance Summary invoiced amount | CODE/runtime PASS; no recalculation |
| `TCA-A-16-14` | stored paid/outstanding/overdue AR | CODE/runtime PASS; no recalculation |
| `TCA-A-16-15` | stored material/contractor/other/total costs | CODE/runtime PASS; finance role only |
| `TCA-A-16-16` | stored profit/profitability and negative-margin exception | CODE/runtime PASS; redaction tested |
| `TCA-A-16-17` | Project Document rows and original/validity exceptions | CODE/runtime PASS for existing structured fields |
| `TCA-A-16-18` | embedded CA-09 source-linked deadlines | CODE/runtime PASS; MG-CA-013 remains OPEN |
| `TCA-A-16-19` | every widget row/exception has source identity and drilldown | CODE/runtime PASS |

Дополнительные source-quality rules (active legal mismatch, obligation without schedule, object without systems, critical Finding without decision, accepted work without Billing Basis) поддерживают intervention view, но не записывают новые business facts.

Не присваивается PASS UI/export, BPM blocked/stage gates CA-11, representative-volume performance, load/race, UAT/sign-off или production deployment.
