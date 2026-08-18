# CA-15 implementation traceability — v0.16.0

CA-15 содержит 51 exact req-id: `TCA-A-19-01…23`, `TCA-A-20-01…14`, `TCA-B-36-01…14`. Таблица не изменяет исходную `07_traceability.csv` и не присваивает blanket PASS.

| Requirement group | Реализованное CODE/runtime evidence | Вердикт v0.16.0 |
| --- | --- | --- |
| `TCA-A-19-01…02` | Service Project identity возвращает exact Customer/Company root | CODE/runtime PASS |
| `TCA-A-19-03…11` | assignments/amendments/obligations/documents/object/system/visit/request/finding входят в trace и typed integrity graph | PARTIAL: positive Request/System + orphan runtime; полный edge fixture/portfolio scan OPEN |
| `TCA-A-19-12…16` | Photo/Document, Billing Output/Sales Invoice и finance/payment reverse sources входят в permission-safe trace | CODE + regression runtime PASS; complete Act/evidence scenario UAT OPEN |
| `TCA-A-19-17…23` | семь explicit cross-cutting dimensions с finance redaction и audit sources | CODE/runtime shape PASS; communications/notification/performance UAT OPEN |
| `TCA-A-20-01…02` | Service Project остаётся root, CA-15 является read projection без container/cache SSOT | CODE/static/runtime PASS |
| `TCA-A-20-03…11` | exact nine-segment why→margin response, stable fingerprint и source drill-down | CODE/runtime PASS для representative Request/System/role fixture; complete business E2E pilot OPEN |
| `TCA-A-20-12` | standard Page `ferum-contract-360`, compiled asset | metadata/build PASS; browser UAT OPEN |
| `TCA-A-20-13` | standard Page `ferum-operations`, links existing source work queues | metadata/build PASS; browser UAT OPEN |
| `TCA-A-20-14` | standard Page `ferum-director-control`, director role list and control-center API | metadata/build PASS; browser UAT OPEN |
| `TCA-B-36-01` | no new Contract SSOT; migration-only legacy source policy remains | POLICY PASS; MG-CA-001/016 migration evidence OPEN |
| `TCA-B-36-02…12` | direct and dynamic project graph edges scanned read-only with stable issue keys | PARTIAL: project-scoped runtime PASS; portfolio/reconciliation/cutover OPEN |
| `TCA-B-36-13…14` | Billing/Finance sources reuse CA-06/07 projection and exact permission redaction | CODE/regression runtime PASS; production accounting reconciliation/sign-off OPEN |

## Acceptance evidence

- all 557 traceability rows have unique ID, acceptance criterion and owner;
- exact nine E2E segments and seven cross-cutting dimensions are machine-tested;
- foreign finance data is redacted through the existing CA-07 role predicate;
- project integrity scan is restricted, read-only and stable on repeated orphan detection;
- three named workspaces are installed and their JavaScript compiles;
- full 69-test regression remains green.

## Не закрыто

Нет blanket доказательства нулевых orphan по production/legacy data, complete customer/contractor/PM/finance/director API-export-report matrix, browser UAT, load/race benchmark, scheduler/retry topology, migration rehearsal/rollback, archive/legal approval или deployment. Import Batch не входит в capabilities до MG-CA-023. OQ-CA-022 disposition выполнен, но rows `KEEP/OPEN` требуют отдельной реализации.
