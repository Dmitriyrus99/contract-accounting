# CA-01 implementation traceability — v0.2.0

Этот файл отражает только подтверждённый CODE/runtime результат и не переписывает исходные формулировки SPEC/TARGET в `07_traceability.csv`.

| Requirement | Результат v0.2.0 | Evidence / граница |
| --- | --- | --- |
| `TCA-A-01-01…18`, `21`, `25` | IMPLEMENTED | единый root, legal/commercial/procurement/security поля, unique identity; original/app links исключены ниже |
| `TCA-A-01-19…20` | DEFERRED | Scope/SLA — CA-02/CA-03 |
| `TCA-A-01-23…24` | DEFERRED | original/appendix Project Document — CA-05 |
| `TCA-A-02-01`, `07…13` | IMPLEMENTED | legal layer + Amendment transition/apply/snapshots |
| `TCA-A-02-02…06` | PARTIAL / DOWNSTREAM | уровни разделены архитектурно; Schedule/Fact/Billing поставляют CA-03/06/07 |
| `TCA-A-03-01…12` | IMPLEMENTED | effective object membership, Service Object и Object System |
| `TCA-A-13-01`, `03`, `05` | IMPLEMENTED | независимые legal/execution axes и допустимые пары |
| `TCA-A-13-02`, `04` | SUPERSEDED BY OQ-CA-003 | CODE использует утверждённые 9 legal + 6 execution values, а не старые source enums |
| `TCA-A-13-06` | DEFERRED | closing documents и AR после expiry — CA-06/07 |
| `TCA-A-18-01…02`, `04…05` | IMPLEMENTED | Service Project, Amendment, Service Object, Object System физически установлены |

Точный runtime verdict и schema counts: [runtime_evidence_v0_2_0_2026-08-18.md](runtime_evidence_v0_2_0_2026-08-18.md).
