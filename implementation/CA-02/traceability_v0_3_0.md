# CA-02 implementation traceability — v0.3.0

Этот файл не переписывает discovery verdicts в `04_coverage_matrix.csv`/`07_traceability.csv`; он фиксирует только фактически созданный CODE и оставшиеся downstream gates.

| Requirement | CODE/runtime evidence | Вердикт инкремента |
| --- | --- | --- |
| `TCA-A-04-01` | Requirement → Obligation явным Link; same-project/routing guards | CODE + runtime PASS |
| `TCA-A-04-02` | обязательный `work_type`, immutable после activation | CODE + runtime PASS; catalog Link deferred |
| `TCA-A-04-03` | обязательный Project Object и membership interval | CODE + runtime PASS |
| `TCA-A-04-04` | typed recurrence child + pure deterministic preview | CODE + unit/runtime PASS |
| `TCA-A-04-05` | `deadline_rule` JSON + `sla_policy_reference` | schema PASS; timestamp/Holiday engine CA-09 OPEN |
| `TCA-A-04-06` | обязательный Object System и same-Service-Object guard | CODE + runtime PASS |
| `TCA-A-04-07` | preview будущих period keys без записи | PARTIAL; Schedule writer/provenance CA-03 OPEN |
| `TCA-A-04-08` | не реализуется preview-функцией | Visit generation CA-03 OPEN |
| `TCA-A-18-03` | физический parent `Ferum Contract Obligation` | schema + migrate + reinstall PASS |

Дополнительно проверены Requirement assessment FSM/routing, active-version overlap, immutable identity, reverse links и отсутствие второго Contract SSOT.

Legacy Scope migration не запускалась: owner decision разрешает reset/recreate непродукционных records, а combined legacy app отсутствует на disposable site. До любого production backfill обязателен отдельный preview/review/reconciliation gate; ambiguous source rows автоматически не связываются.
