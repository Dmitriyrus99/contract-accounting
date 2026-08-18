# CA-07 implementation traceability — v0.8.0

Файл фиксирует фактический CODE/runtime результат и не переписывает discovery CSV. `PASS` ниже означает только проверенный технический инкремент; UAT/sign-off отмечены отдельно.

| Requirement | CODE/runtime evidence | Вердикт инкремента |
| --- | --- | --- |
| `TCA-A-11-01` | Summary выводит `contract_amount_with_vat` из единственного `Ferum Service Project`; runtime использует 120000 | CODE/runtime PASS |
| `TCA-A-11-02` | net/gross поля разделены и берутся из ERPNext, но положительный VAT tax-row сценарий не выполнен | PARTIAL — Finance UAT OPEN |
| `TCA-A-11-03` | recognized revenue берётся из submitted SI `base_net_total`; opening исключается | CODE/runtime PASS |
| `TCA-A-11-04` | Approved/Settled Contractor Settlement или классифицированный PI формирует contractor cost | CODE/runtime PASS |
| `TCA-A-11-05` | Approved Material Expense или классифицированный PI формирует material cost без double count | CODE/runtime PASS |
| `TCA-A-11-06` | неклассифицированный PI попадает в Other; отдельной размерности tool/rent нет | PARTIAL — target classification OPEN |
| `TCA-A-11-07` | submitted неклассифицированный PI формирует `other_cost_without_vat` | CODE/runtime PASS |
| `TCA-A-11-08` | runtime: 120000 revenue − 76000 costs = 44000 profit | CODE/runtime PASS |
| `TCA-A-11-09` | Summary mutation/delete заблокированы; full rebuild и fingerprint повторяемы | CODE/runtime PASS |
| `TCA-A-11-10` | submitted Sales Invoice — источник revenue/invoiced/AR; cancelled исключается | CODE/runtime PASS |
| `TCA-A-11-11` | стандартный Payment Entry меняет Invoice outstanding и присутствует в source trace | CODE/runtime PASS |
| `TCA-A-11-12` | submitted Purchase Invoice — источник base cost и Other fallback | CODE/runtime PASS |
| `TCA-A-11-13` | физический Material Expense с guarded approval участвует в read-model | CODE/runtime PASS |
| `TCA-A-11-14` | физический Contractor Settlement с guarded approval/settlement участвует в read-model | CODE/runtime PASS |
| `TCA-A-11-15` | profitability = aggregate profit / recognized revenue; runtime 36.666667% | CODE/runtime PASS |
| `TCA-A-18-14` | `Ferum Material Expense` установлен clean install и проходит positive/negative runtime | schema/runtime PASS |
| `TCA-A-18-17` | `Ferum Project Finance Summary` установлен clean install, read-only и rebuildable | schema/runtime PASS |

Дополнительно runtime подтверждает opening AR без повторной выручки, exact one-of Material/Contractor/Other для PI, cancel guard/release, stale-summary reconciliation, Company/currency portfolio sum и отсутствие изменений количества Invoice/GL при повторном rebuild.

Не присваивается PASS для VAT tax-row UAT, отдельной tool/rent аналитики, legacy production reconciliation, async worker/load/race, Finance/Legal sign-off или production deployment.
