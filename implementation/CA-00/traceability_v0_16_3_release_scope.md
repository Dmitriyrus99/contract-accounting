# CA-00 cross-increment release-scope traceability — v0.16.3

Этот addendum не переписывает историческую `07_traceability.csv`. Он фиксирует только наблюдаемое в текущем tree `5249e00` cross-increment evidence для требований, которые не могли быть закрыты traceability раннего инкремента, и для ERPNext/custom boundary `TCA-A-17-*`.

| Requirement | Current v0.16.3 evidence | Verdict |
| --- | --- | --- |
| `TCA-A-01-22` | `Ferum Service Project.execution_status`, dual-FSM service и CA-01 runtime suite | CODE/runtime PASS |
| `TCA-A-04-08` | CA-03 Schedule writer создаёт idempotent primary Maintenance Visit из Obligation/Schedule | CODE/runtime PASS |
| `TCA-A-05-06` | CA-06 immutable Billing Basis связывает accepted Visit/Request с Billing Output | CODE/runtime PASS |
| `TCA-A-05-07` | CA-06 Billing Output требует submitted standard Sales Invoice exact project/context | CODE/runtime PASS |
| `TCA-A-05-08` | CA-07 finance trace читает standard Payment Entry Reference и invoice outstanding | CODE/runtime PASS |
| `TCA-A-17-01` | Customer остаётся standard Link в Service Object, Billing Output и Finance Summary | CODE/schema/runtime PASS |
| `TCA-A-17-02` | Supplier остаётся standard Link в Assignment, Worker, Material Expense и Settlement | CODE/schema/runtime PASS |
| `TCA-A-17-03` | Company остаётся standard Link и source of default currency | CODE/schema/runtime PASS |
| `TCA-A-17-04` | Service Object хранит Small Text address, а не Link на standard Address | OPEN/PARTIAL: standard Address boundary not implemented |
| `TCA-A-17-05` | Contact остаётся standard Link в Service Object, Project Object и Contractor Worker | CODE/schema PASS |
| `TCA-A-17-06` | Billing Output/Finance Summary используют standard Sales Invoice; custom GL/invoice SSOT не создаётся | CODE/runtime PASS |
| `TCA-A-17-07` | Material/Contractor costs используют standard Purchase Invoice | CODE/runtime PASS |
| `TCA-A-17-08` | Payments читаются только из standard Payment Entry/Reference | CODE/runtime PASS |
| `TCA-A-17-09` | Material Expense использует standard Item Link | CODE/schema PASS |
| `TCA-A-17-10` | Custom Warehouse DocType отсутствует, но explicit Warehouse Link/acceptance отсутствует | OPEN/PARTIAL |
| `TCA-A-17-11` | Material Expense использует standard Stock Entry Link | CODE/schema PASS |
| `TCA-A-17-12` | Internal Assignment и Personnel Credential используют standard Employee | CODE/schema PASS; positive personnel readiness remains MG-CA-015 |
| `TCA-A-17-13` | Actor/responsible/approver fields используют standard User | CODE/schema/runtime PASS |
| `TCA-A-17-14` | Versioned fixtures и process responsibility используют standard Role | CODE/schema/runtime PASS |
| `TCA-A-17-15` | Lifecycle реализован server FSM; standard Workflow reuse не доказан | OPEN/PARTIAL |
| `TCA-A-17-16` | Project Document, Photo/Evidence и Billing Artifact используют standard File с hash guards | CODE/runtime PASS |
| `TCA-A-17-17` | Communication разрешён как process evidence/source и присутствует в templates | PARTIAL: delivery/scheduler/notification acceptance OPEN |
| `TCA-A-17-18` | Custom contractual root не подменён standard Project | PARTIAL policy evidence; semantic-match acceptance OPEN |
| `TCA-A-17-19` | Project Process Step не подменён standard Task | PARTIAL policy evidence; semantic-match acceptance OPEN |
| `TCA-A-17-20` | Service Request/Finding не подменены standard Issue | PARTIAL policy evidence; semantic-match acceptance OPEN |
| `TCA-A-17-21` | Custom asset copy отсутствует | PARTIAL policy evidence; standard Asset applicability acceptance OPEN |

## Граница доказательства

- Этот файл подтверждает CODE/schema/runtime только там, где row содержит `PASS`.
- `OPEN/PARTIAL` и policy-only rows остаются `Partial` в Release Scope v1 matrix.
- Standard Address, Warehouse и Workflow не объявляются реализованными по одному факту отсутствия custom duplicate.
- Manual finance/legal/security/UAT, performance, restore и production gates остаются отдельными.
