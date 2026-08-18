# Contract accounting discovery — индекс

**Цель документа:** дать руководителю краткое резюме и навигацию по аналитическому пакету.

**Дата анализа:** 2026-08-17. **Owner decisions синхронизированы:** 2026-08-18.

**Источник истины:** TARGET — `Structure of the contract accounting system.md`; SPEC baseline — Claude `ferum_custom_spec_v6_2_21.md`; CODE — текущий Claude working tree `w2-objects-core` на `b1fcaac`; owner decisions от 2026-08-18 — [08_open_questions.md](08_open_questions.md).

**Как проверить:** начать с [01_source_inventory.md](01_source_inventory.md), затем сверить AS-IS в [03_asis_model.md](03_asis_model.md) и атомарные вердикты в [04_coverage_matrix.csv](04_coverage_matrix.csv).

## Резюме для руководителя

Проанализировано 1651 доступных файлов. Фактически найдено 54 DocType в Claude-ветке и 46 в более старой чистой Codex-ветке; восемь DocType существуют только в Claude. Базовая SPEC — v6.2.21, 6946 строк, SHA-256 `58872EE75E37B68D86F2CBF06B6A4C2B3CA0D6DB87D37B4A6A13372CB7176E6D`; её registry содержит 305 требований: 300 MUST + 5 SHOULD (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/spec/ferum_custom_spec_v6_2_21.md:L1-L9`).

AS-IS уже имеет сильное ядро: юридический `Ferum Contract`, execution project/link, effective-dated objects/scope, генерацию ТО, Visit/Request/evidence, billing output/artifacts, стандартный ERPNext accounting SSOT и Finance Summary read-model. Но текущий W2 находится в dirty working tree и ещё требует фиксации baseline и DB verification (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/plan/09_task_breakdown.md:L480-L515`).

TARGET разложен на 557 атомарных требований во всех 20 доменных и 39 процессных разделах: A — 261, B — 296. Вердикты: 139 OK, 19 Gap-Code, 395 Gap-Both, 4 Conflict. Главные разрывы — отсутствие Contract Obligation, Finding/Defect, Inspection, Project Document с двойным статусом оригинала/скана, Contractor Assignment/credentials и всего универсального BPM Template/Stage/Step/Gate/Evidence слоя.

Ключевой архитектурный конфликт: TARGET формулирует Service Project как договор, а AS-IS разделяет юридический Contract и execution Project (`Structure of the contract accounting system.md:L44-L85`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/adr/ADR-0003-service-project-vs-legal-contract.md:L52-L69`). OQ-CA-001 утверждён: `Ferum Service Project` — единый юридический и execution SSOT; `Ferum Contract` и `Ferum Project Contract Link` — только read-only migration provenance до контролируемого cutover. Это решение не устраняет CODE gap и не закрывает N:M data exceptions.

**Рекомендуемый первый инкремент:** `CA-00 Baseline Freeze`, затем `CA-01 Service Project Contract Core & Dual Status`. OQ-CA-003 закрыт owner decision от 2026-08-18: утверждены clean TARGET legal/execution FSM без переноса тестового 12-state status. До cutover остаются MG-CA-016 и W2-V02; MG-CA-001 применим только при сохранении legacy records вместо утверждённого reset/recreate. После этого MVP строится цепочкой Requirement/Obligation → Schedule → Visit/Evidence → Billing Basis/Output → Sales Invoice → Payment Entry.

Заказчик утвердил все 23 owner questions, включая dual-status/Suspend-Resume, Party Identity, VAT, validation-report classification, Codex-only field policy и fail-closed Import Batch classification. Открытых OQ нет; отдельно требуются применимые MG-CA-001/013/015/016/023 evidence. Полный реестр — [08_open_questions.md](08_open_questions.md).

## Навигация

| Артефакт | Назначение |
| --- | --- |
| [01_source_inventory.md](01_source_inventory.md) / [CSV](01_source_inventory.csv) | все источники и 54/46 DocType |
| [02_knowledge_base.md](02_knowledge_base.md) | выжимка по 13 областям |
| [03_asis_model.md](03_asis_model.md) | фактическая модель, статусы, rules, ERPNext, ER |
| [04_gap_analysis.md](04_gap_analysis.md) | top-15, конфликты, дельта |
| [04_coverage_matrix.csv](04_coverage_matrix.csv) | 557 атомарных TARGET-требований |
| [05_target_model.md](05_target_model.md) | TO-BE DocType, dual status, BPM, ER, UX |
| [06_roadmap.md](06_roadmap.md) | инкременты, MVP, зависимости, риски |
| [07_traceability.csv](07_traceability.csv) | requirement → AS-IS → TO-BE → increment → acceptance |
| [08_open_questions.md](08_open_questions.md) | 23 APPROVED решения и отдельные manual/runtime gates |
| [09_verification_report.md](09_verification_report.md) | самопроверка Definition of Done |
| [implementation/CA-00/README.md](implementation/CA-00/README.md) | фактический preflight CA-00, W2 readiness и MG-CA-016 gates |
| [implementation/CA-00/ADR-CA-0001-erpnext-custom-party-boundary.md](implementation/CA-00/ADR-CA-0001-erpnext-custom-party-boundary.md) | утверждённая граница ERPNext/custom и Party Identity |
| [implementation/CA-00/live_inventory_w2t12b_2026-08-18.md](implementation/CA-00/live_inventory_w2t12b_2026-08-18.md) | live schema/patch/workflow/role/scheduler inventory post-W2 стенда |
| [implementation/CA-00/migration_evidence_template.md](implementation/CA-00/migration_evidence_template.md) | обязательный формат migration/rollback evidence |
| [implementation/CA-00/rollback_rehearsal_2026-08-18.md](implementation/CA-00/rollback_rehearsal_2026-08-18.md) | backup + compensating rollback evidence; full restore gate остаётся OPEN |
| [implementation/CA-01/README.md](implementation/CA-01/README.md) | dual-status domain policy, границы и unit evidence первого инкремента CA-01 |
| [implementation/CA-01/schema_v0_1_0.md](implementation/CA-01/schema_v0_1_0.md) | Frappe schema/adapter v0.1.0, permissions, static evidence и незакрытые runtime gates |
| [implementation/CA-01/schema_v0_2_0.md](implementation/CA-01/schema_v0_2_0.md) | Direct Service Project links, Amendment/Stage/Security/Financial Plan и Object hierarchy |
| [implementation/CA-01/runtime_evidence_v0_2_0_2026-08-18.md](implementation/CA-01/runtime_evidence_v0_2_0_2026-08-18.md) | Exact v0.2.0 bench versions, 11/11 runtime, physical schema и rollback/reinstall |
| [implementation/CA-01/traceability_v0_2_0.md](implementation/CA-01/traceability_v0_2_0.md) | CODE/runtime mapping CA-01 без подмены исходной SPEC/TARGET traceability |
| [implementation/CA-01/runtime_test_plan.md](implementation/CA-01/runtime_test_plan.md) | отдельный bench/site protocol и versioned runtime acceptance suite |
| [implementation/CA-02/README.md](implementation/CA-02/README.md) | CA-02 Requirement/Obligation core, границы CA-03/05/09/11 и фактические gates |
| [implementation/CA-02/schema_v0_3_0.md](implementation/CA-02/schema_v0_3_0.md) | физическая schema Requirement/Obligation/Recurrence, FSM и integrity guards |
| [implementation/CA-02/runtime_evidence_v0_3_0_2026-08-18.md](implementation/CA-02/runtime_evidence_v0_3_0_2026-08-18.md) | exact v0.3.0 versions, 15/15 runtime и rollback/reinstall |
| [implementation/CA-02/traceability_v0_3_0.md](implementation/CA-02/traceability_v0_3_0.md) | CODE/runtime mapping CA-02 с явными downstream OPEN |
| [implementation/CA-03/README.md](implementation/CA-03/README.md) | CA-03 plan→fact core, generation/replacement/review/acceptance и границы billing/Finding |
| [implementation/CA-03/schema_v0_4_0.md](implementation/CA-03/schema_v0_4_0.md) | Schedule/Visit/Service Request physical schema и server invariants |
| [implementation/CA-03/runtime_evidence_v0_4_0_2026-08-18.md](implementation/CA-03/runtime_evidence_v0_4_0_2026-08-18.md) | exact v0.4.0 versions, 19/19 runtime и rollback/reinstall |
| [implementation/CA-03/traceability_v0_4_0.md](implementation/CA-03/traceability_v0_4_0.md) | CODE/runtime mapping CA-03 с явными CA-04/06/07/08 OPEN |
| [implementation/CA-04/README.md](implementation/CA-04/README.md) | единый Finding/Defect-category lifecycle, execution links, photo evidence и открытые CA-08/12 gates |
| [implementation/CA-04/schema_v0_5_0.md](implementation/CA-04/schema_v0_5_0.md) | Finding/Execution Link/Photo Evidence physical schema и server invariants |
| [implementation/CA-04/runtime_evidence_v0_5_0_2026-08-18.md](implementation/CA-04/runtime_evidence_v0_5_0_2026-08-18.md) | exact v0.5.0 versions, 24/24 runtime и rollback/reinstall 21 DocType |
| [implementation/CA-04/traceability_v0_5_0.md](implementation/CA-04/traceability_v0_5_0.md) | CODE/runtime mapping CA-04 без подмены CA-08/12 gates |
| [implementation/CA-05/README.md](implementation/CA-05/README.md) | реестр Project Document, независимые digital/original статусы и границы CA-06/11 |
| [implementation/CA-05/schema_v0_6_0.md](implementation/CA-05/schema_v0_6_0.md) | физическая schema Project Document/Document Link/Event и server invariants |
| [implementation/CA-05/runtime_evidence_v0_6_0_2026-08-18.md](implementation/CA-05/runtime_evidence_v0_6_0_2026-08-18.md) | exact v0.6.0 versions, 29/29 runtime и rollback/reinstall 24 DocType |
| [implementation/CA-05/traceability_v0_6_0.md](implementation/CA-05/traceability_v0_6_0.md) | CODE/runtime mapping CA-05 с явными downstream integration gates |
| [implementation/CA-06/README.md](implementation/CA-06/README.md) | execution-to-billing trace, immutable Basis и граница стандартного ERPNext accounting |
| [implementation/CA-06/schema_v0_7_0.md](implementation/CA-06/schema_v0_7_0.md) | физическая schema Billing Output/Basis/Artifact/Event и Sales Invoice adapter |
| [implementation/CA-06/runtime_evidence_v0_7_0_2026-08-18.md](implementation/CA-06/runtime_evidence_v0_7_0_2026-08-18.md) | exact v0.7.0 versions, 35/35 runtime и clean reinstall 28 DocType |
| [implementation/CA-06/traceability_v0_7_0.md](implementation/CA-06/traceability_v0_7_0.md) | CODE/runtime mapping CA-06 без подмены UAT/production gates |
| [implementation/CA-07/README.md](implementation/CA-07/README.md) | rebuildable finance read-model, guarded cost classification и standard accounting boundary |
| [implementation/CA-07/schema_v0_8_0.md](implementation/CA-07/schema_v0_8_0.md) | физическая schema Finance Summary/Material Expense/Contractor Settlement и PI adapter |
| [implementation/CA-07/runtime_evidence_v0_8_0_2026-08-18.md](implementation/CA-07/runtime_evidence_v0_8_0_2026-08-18.md) | exact v0.8.0 versions, 41/41 runtime и clean reinstall 31 DocType |
| [implementation/CA-07/traceability_v0_8_0.md](implementation/CA-07/traceability_v0_8_0.md) | CODE/runtime mapping CA-07 с явными VAT/tool-rent/UAT OPEN |
| [implementation/CA-08/README.md](implementation/CA-08/README.md) | Assignment/commercial separation, Supplier isolation и hard-blocked personnel boundary |
| [implementation/CA-08/schema_v0_9_0.md](implementation/CA-08/schema_v0_9_0.md) | физическая Assignment/Terms schema и fail-closed Worker/Credential privacy spike |
| [implementation/CA-08/runtime_evidence_v0_9_0_2026-08-18.md](implementation/CA-08/runtime_evidence_v0_9_0_2026-08-18.md) | exact v0.9.0 versions, 47/47 runtime и clean reinstall 35 DocType |
| [implementation/CA-08/traceability_v0_9_0.md](implementation/CA-08/traceability_v0_9_0.md) | CODE/runtime mapping CA-08 с явным MG-CA-015/PERSONNEL READY OPEN |
| [implementation/CA-09/README.md](implementation/CA-09/README.md) | derived source timeline, explicit calendar snapshot и MG-CA-013 boundary |
| [implementation/CA-09/projection_v0_10_0.md](implementation/CA-09/projection_v0_10_0.md) | normalized row/source adapters и fail-closed classification contract |
| [implementation/CA-09/runtime_evidence_v0_10_0_2026-08-18.md](implementation/CA-09/runtime_evidence_v0_10_0_2026-08-18.md) | exact v0.10.0 versions, 50/50 runtime и 35-DocType inventory |
| [implementation/CA-09/traceability_v0_10_0.md](implementation/CA-09/traceability_v0_10_0.md) | CODE/runtime mapping TCA-A-14 с явными signature/customer-response gaps |
| [implementation/CA-10/README.md](implementation/CA-10/README.md) | permission-safe Contract 360/Director projections и открытые UI/performance/policy gates |
| [implementation/CA-10/projection_v0_11_0.md](implementation/CA-10/projection_v0_11_0.md) | widgets, exception rules, source drilldowns и finance redaction contract |
| [implementation/CA-10/runtime_evidence_v0_11_0_2026-08-18.md](implementation/CA-10/runtime_evidence_v0_11_0_2026-08-18.md) | exact v0.11.0 versions, migrate, 54/54 runtime и 35-DocType inventory |
| [implementation/CA-10/traceability_v0_11_0.md](implementation/CA-10/traceability_v0_11_0.md) | CODE/runtime mapping TCA-A-15/16 без подмены OPEN gates |
| [implementation/CA-11/README.md](implementation/CA-11/README.md) | versioned BPM core, parent topology и честная граница 169 req-id |
| [implementation/CA-11/schema_v0_12_0.md](implementation/CA-11/schema_v0_12_0.md) | physical Template/Instance/Evidence/Gate/Event schema и typed commands |
| [implementation/CA-11/runtime_evidence_v0_12_0_2026-08-18.md](implementation/CA-11/runtime_evidence_v0_12_0_2026-08-18.md) | exact v0.12.0 versions, migrate, 59/59 runtime и 44-DocType inventory |
| [implementation/CA-11/traceability_v0_12_0.md](implementation/CA-11/traceability_v0_12_0.md) | grouped CODE/runtime mapping 169 CA-11 req-id без blanket PASS |
| [implementation/CA-12/README.md](implementation/CA-12/README.md) | reference seven-stage Launch graph, Inspection core и честная граница 84 req-id |
| [implementation/CA-12/schema_v0_13_0.md](implementation/CA-12/schema_v0_13_0.md) | 7-stage/25-step graph, Inspection physical schema и typed lifecycle |
| [implementation/CA-12/runtime_evidence_v0_13_0_2026-08-18.md](implementation/CA-12/runtime_evidence_v0_13_0_2026-08-18.md) | exact v0.13.0 versions, repeated migrate, 63/63 runtime и 47-DocType inventory |
| [implementation/CA-12/traceability_v0_13_0.md](implementation/CA-12/traceability_v0_13_0.md) | grouped CODE/runtime mapping 84 CA-12 req-id без blanket PASS |
| [implementation/CA-13/README.md](implementation/CA-13/README.md) | recurring Billing Cycle core, period gate и честная граница 11 req-id |
| [implementation/CA-13/schema_v0_14_0.md](implementation/CA-13/schema_v0_14_0.md) | Cycle physical schema, 9-step process, projection и backfill contract |
| [implementation/CA-13/runtime_evidence_v0_14_0_2026-08-18.md](implementation/CA-13/runtime_evidence_v0_14_0_2026-08-18.md) | exact v0.14.0 versions, repeated migrate, 65/65 runtime и 48-DocType inventory |
| [implementation/CA-13/traceability_v0_14_0.md](implementation/CA-13/traceability_v0_14_0.md) | CODE/runtime mapping 11 CA-13 req-id без blanket PASS |
| [implementation/CA-14/README.md](implementation/CA-14/README.md) | permission-safe My Actions/Project Launches UI и честные открытые границы |
| [implementation/CA-14/projection_v0_15_0.md](implementation/CA-14/projection_v0_15_0.md) | SSOT/de-duplication/sorting/Launch flag projection contract |
| [implementation/CA-14/runtime_evidence_v0_15_0_2026-08-18.md](implementation/CA-14/runtime_evidence_v0_15_0_2026-08-18.md) | exact v0.15.0 versions, repeated migrate, 67/67 runtime и defect trail |
| [implementation/CA-14/traceability_v0_15_0.md](implementation/CA-14/traceability_v0_15_0.md) | CODE/runtime mapping 14 CA-14 req-id без blanket PASS |
| [implementation/CA-15/README.md](implementation/CA-15/README.md) | read-only E2E/integrity contour, named Desk Pages и честные release gaps |
| [implementation/CA-15/projection_v0_16_0.md](implementation/CA-15/projection_v0_16_0.md) | nine-segment trace, cross-cutting dimensions, permission и integrity contract |
| [implementation/CA-15/field_disposition_v0_16_0.md](implementation/CA-15/field_disposition_v0_16_0.md) | OQ-CA-022 field-level KEEP/REPLACE/DERIVE/MOVE decisions и OPEN implementation rows |
| [implementation/CA-15/runtime_evidence_v0_16_0_2026-08-18.md](implementation/CA-15/runtime_evidence_v0_16_0_2026-08-18.md) | exact v0.16.0 versions, migrate/build, 69/69 runtime и tooling defect trail |
| [implementation/CA-15/traceability_v0_16_0.md](implementation/CA-15/traceability_v0_16_0.md) | grouped CODE/runtime mapping 51 CA-15 req-id без blanket PASS |
| [implementation/CA-15/browser_uat_v0_16_1_2026-08-18.md](implementation/CA-15/browser_uat_v0_16_1_2026-08-18.md) | manager/director browser role slice, director DocPerm defect fix и честная performance/open-gate граница |
| [implementation/CA-15/traceability_v0_16_1.md](implementation/CA-15/traceability_v0_16_1.md) | v0.16.1 manager/director browser и read-only source permission addendum |
| [implementation/CA-15/cross_role_uat_v0_16_2_2026-08-18.md](implementation/CA-15/cross_role_uat_v0_16_2_2026-08-18.md) | Engineer/Accountant/Office Manager/Project Lead Operations browser UAT и project-scoped permission boundary |
| [implementation/CA-15/traceability_v0_16_2.md](implementation/CA-15/traceability_v0_16_2.md) | v0.16.2 Operations cross-role traceability addendum без blanket PASS |

## Принятый baseline

- TARGET: 2458 строк, SHA-256 `0354D424F623753973101C2B8D30B6BC54FB0351572EF9269DBF60167B7617AC`.
- SPEC: Claude v6.2.21; рабочая и versioned-копии побайтно совпадают.
- CODE discovery snapshot: dirty Claude working tree на `b1fcaac`; Codex `c97c34a` — historical conflict evidence. Официальный AS-IS baseline ещё не frozen: OQ-CA-016 требует первый clean post-W2 commit и закрытый MG-CA-016.
- OWNER: все 23 OQ утверждены 2026-08-18; OPEN/BLOCKING и OPEN/UNKNOWN = 0. Manual/runtime gates не закрыты owner approval.
- Проверки реализации CA-00: targeted pre-commit (включая full-package mypy), `compileall` и `git diff --check` — PASS; bench/runtime/DB/permission tests не исполнялись и остаются отдельными gates.
- Live-site metadata, базы и секреты не читались.
