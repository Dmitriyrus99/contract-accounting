# CA-15 Operations role traceability addendum — v0.16.2

Addendum уточняет только Operations cross-role slice и не изменяет 51 normative req-id в `07_traceability.csv`.

| Requirement group | v0.16.2 evidence | Вердикт |
| --- | --- | --- |
| `TCA-A-19-03…11` | Engineer/Office Manager Service Project read ограничен project assignment/ownership query; positive own и negative foreign project проверены runtime | PARTIAL PASS; полный role/edge portfolio OPEN |
| `TCA-A-20-03…11` | Engineer Request и Accountant/Office Project Document попадают в permission-safe My Actions без нового task SSOT | PARTIAL browser/runtime PASS |
| `TCA-A-20-12` | Accountant открывает Contract 360° Page; Office Manager получает штатный Not permitted | PARTIAL role-boundary PASS; data/confidentiality scenario OPEN |
| `TCA-A-20-13` | Operations Page и conditional Launch card проверены для Engineer, Accountant, Office Manager и Project Lead; non-launch client не вызывает forbidden Launch API | PASS для четырёх ролей; Contractor/Customer/Process Owner OPEN |
| `TCA-A-20-14` | Project Lead открывает Director Control (`Projects = 1`), Engineer получает Not permitted | PARTIAL role-boundary PASS; representative exceptions OPEN |
| `TCA-B-36-13…14` | Accountant Page availability подтверждена, но export/report и finance reconciliation sign-off не выполнялись | PARTIAL; finance acceptance OPEN |

Evidence: [cross_role_uat_v0_16_2_2026-08-18.md](cross_role_uat_v0_16_2_2026-08-18.md). Исходная карта остаётся в [traceability_v0_16_0.md](traceability_v0_16_0.md), предыдущий manager/director slice — в [traceability_v0_16_1.md](traceability_v0_16_1.md).
