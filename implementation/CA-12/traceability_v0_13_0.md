# CA-12 grouped implementation traceability — v0.13.0

CA-12 содержит 84 exact req-id. Таблица группирует их по исходным секциям CSV; она не заменяет построчную `07_traceability.csv` и не присваивает blanket PASS группе.

| Requirement group | Count | Реализованное CODE/runtime evidence | Вердикт v0.13.0 |
| --- | ---: | --- | --- |
| `TCA-B-13-*` | 8 | Initiation stage: contract draft, technical specification, requirements, responsibility и blocking gate | PARTIAL: reference graph/core PASS; award trigger и детальные reviews OPEN |
| `TCA-B-14-*` | 9 | Customer Contact: official channel, contacts, initial meeting | PARTIAL: stage/evidence types PASS; welcome/first-call/incumbent и exact outcome catalog OPEN |
| `TCA-B-15-*` | 9 | Execution Scheme: model approval, subcontracting decision, contractor documents | PARTIAL: branch-capable graph PASS; exact six-mode enum/conditional branches OPEN |
| `TCA-B-16-*` | 13 | Personnel Readiness stage и explicit hard gate | BLOCKED/PARTIAL: обход запрещён; Worker/Credential/Passport positive path ожидает MG-CA-015 |
| `TCA-B-17-*` | 13 | Mobilization: access letter, order, project docs, contact card, schedule, journals, initial package | PARTIAL: graph PASS; полный prepared/sent/received/approved/signed/delivery lifecycle OPEN |
| `TCA-B-18-*` | 5 | Inspection parent, system/component checklist, frozen inventory и Launch Inspection step | PARTIAL/CORE PASS: отдельный автоматически создаваемый child Project Process OPEN |
| `TCA-B-19-*` | 8 | photo, Finding Defect/Observation, structured report, manager approval и customer flow | PARTIAL/CORE PASS: автоматические act/defect-statement files и Additional Work OPEN |
| `TCA-B-22-*` | 11 | seven blocking stages, final gate, Launch Process completion и audited Launching→Active | PARTIAL: core blocking/lifecycle PASS; полный prerequisite catalog и CA-13 Billing readiness OPEN |
| `TCA-B-23-*` | 8 | exact seven stage codes/order и no-history migration policy | PARTIAL: graph/runtime PASS; post-launch maintenance/billing/request activation OPEN |

Итого: `8 + 9 + 9 + 13 + 13 + 5 + 8 + 11 + 8 = 84` exact req-id.

## Точно подтверждённые acceptance scenarios

- repeated migrate сохраняет один exact Published `FERUM-LAUNCH` v1 graph из 7 stages/25 steps и не создаёт project history;
- read-only assessment не пишет process; explicit token создаёт один idempotent Launch instance;
- `PERSONNEL_READY` отклоняет и Completed, и Not Applicable до MG-CA-015;
- Ready Inspection step создаёт один Inspection; start требует frozen inventory;
- completion создаёт report Project Document, Defect Finding и Photo Evidence без потери checklist context;
- Approved Inspection становится Validated Process Evidence только для exact Process Step;
- Passed gates проводят процесс до финала; final Launch stage переводит Service Project `Launching → Active` через lifecycle audit.

Не присваивается PASS personnel/credentials, award trigger, automatic project history, Additional Work, automatic act/defect statement, B2G/B2B/subcontract pilots, post-launch operational processes, performance/load/race, UAT/sign-off или production deployment.
