# CA-08 implementation traceability — v0.9.0

Файл фиксирует CODE/runtime результат и не переписывает discovery CSV. MG-CA-015 остаётся OPEN, поэтому personnel readiness не получает PASS.

| Requirement | CODE/runtime evidence | Вердикт инкремента |
| --- | --- | --- |
| `TCA-A-12-01` | отдельный physical `Ferum Contractor Assignment`, typed create/FSM и runtime positive/negative | CODE/runtime PASS |
| `TCA-A-12-02` | required Link `service_project`, context и contract-term validation | CODE/runtime PASS |
| `TCA-A-12-03` | Contractor mode требует Supplier; Supplier mismatch отклоняется | CODE/runtime PASS |
| `TCA-A-12-04` | required Project Object того же Service Project | CODE/runtime PASS |
| `TCA-A-12-05` | optional Object System проверяется против Service Object; system-scoped runtime выполнен | CODE/runtime PASS |
| `TCA-A-12-06` | required typed work-type Data участвует в immutable scope/overlap dimension | CODE/runtime PASS |
| `TCA-A-12-07` | schema/XOR различает Internal Employee и Contractor Supplier; runtime подтверждает Contractor и negative XOR, но Employee positive не выполнен | PARTIAL |
| `TCA-A-12-08` | separate Commercial Terms хранит client price | CODE/runtime PASS |
| `TCA-A-12-09` | separate Terms хранит contractor cost; Settlement ссылается на Assignment/Approved Terms | CODE/runtime PASS |
| `TCA-A-12-10` | derived Terms margin: runtime 100000 − 60000 = 40000, 40% | CODE/runtime PASS |
| `TCA-A-18-12` | physical Assignment установлен clean install, overlap/context/permission scenarios проходят | schema/runtime PASS |
| `TCA-A-18-13` | approved target interpretation: `Ferum Contractor Settlement` + standard `Payment Entry`, второго Payment DocType нет | CODE/runtime PASS; no duplicate accounting |
| `OQ-CA-014` | Assignment не содержит price/cost; pricing только Terms/Settlement | CODE/runtime PASS |
| `OQ-CA-015 / MG-CA-015` | Worker/Credential schema установлена, records/API/readiness hard-disabled, passport fields absent | FAIL-CLOSED PARTIAL; gate OPEN |

Runtime дополнительно подтверждает разные Supplier на одной scope/period, rejection overlap одного Supplier, позднее связывание Terms, Assignment→Settlement/Material trace и Supplier User Permission isolation.

Не присваивается PASS требованиям CA-12/B-16 о credentials/readiness, Employee/Worker parity, PERSONNEL READY, production PII, cross-entity contractor portal, migration/load/UAT/sign-off или deployment.
