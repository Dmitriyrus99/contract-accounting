# CA-05 implementation traceability — v0.6.0

Файл фиксирует фактический CODE/runtime результат и не переписывает discovery CSV.

| Requirement | CODE/runtime evidence | Вердикт инкремента |
| --- | --- | --- |
| `TCA-A-08-01` | parent `Ferum Project Document`, naming `FPD-.YYYY.-.######` | schema/runtime PASS |
| `TCA-A-08-02…03` | обязательный Select и точный enum 11 типов из TARGET | schema PASS |
| `TCA-A-08-04…08` | number/date/version/status/validity typed fields, identity freeze и unique version key | schema/runtime PASS |
| `TCA-A-08-09` | Link на стандартный `File`, server-derived content hash, deletion guard | CODE/runtime PASS |
| `TCA-A-08-10` | immutable allowlisted Dynamic Link source с derived project context | CODE/runtime PASS |
| `TCA-A-08-11` | прямой `service_project` root; legacy Contract link отсутствует | schema/runtime PASS |
| `TCA-A-08-12` | optional Project Object и derived Service Object с membership check | schema/runtime PASS |
| `TCA-A-08-13` | optional allowlisted billing Dynamic Link, one-File rule и fail-closed project adapter | CODE PASS; CA-06 integration runtime OPEN |
| `TCA-A-18-11` | физический Project Document/Event/Link установлен clean install | runtime PASS |
| `TCA-B-25-01…03` | digital/original поля и независимые server transition matrices | schema/runtime PASS |
| `TCA-B-25-04` | Original содержит и runtime проходит Requested → Received → Archived | schema/runtime PASS |

Дополнительно runtime подтверждает обязательные basis/evidence для `Not Required`, server stamps/storage для original custody, immutable audit events, блокировку удаления принятого File, запрет активации без принятой формы и fail-closed foreign/unscoped links.

Не присваивается PASS для CA-06 billing chain, CA-11 BPM links, legacy migration, UAT или production deployment.
