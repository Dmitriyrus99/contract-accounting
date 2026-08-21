# Contract accounting discovery — индекс

**Цель документа:** дать руководителю краткое резюме и навигацию по discovery, release decisions, реализации и плану завершения.

**Дата анализа:** 2026-08-17. **Owner decisions:** 2026-08-18. **Release decisions:** 2026-08-19.

**Источник истины:** release topology/scope/policies — [Release Decisions v1](11_release_decisions_v1.md); TARGET — `Structure of the contract accounting system.md`; discovery SPEC/CODE — прежние snapshots; completion CODE baseline — `contract-accounting` `7145d87` / `0.16.2`; текущая committed branch head — `500cdaf` / `0.19.0`, проверенный незакоммиченный FR-06 working tree — `0.20.0`.

**Как проверить:** для дальнейшей работы начать с [Release Decisions v1](11_release_decisions_v1.md), [roadmap](06_roadmap.md) и [последовательного плана](10_remaining_questions_and_actions.md); discovery facts проверять через inventory/AS-IS/coverage artifacts.

## Резюме для руководителя

Проанализировано 1651 доступных файлов. Фактически найдено 54 DocType в Claude-ветке и 46 в более старой чистой Codex-ветке; восемь DocType существуют только в Claude. Базовая SPEC — v6.2.21, 6946 строк, SHA-256 `58872EE75E37B68D86F2CBF06B6A4C2B3CA0D6DB87D37B4A6A13372CB7176E6D`; её registry содержит 305 требований: 300 MUST + 5 SHOULD (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/spec/ferum_custom_spec_v6_2_21.md:L1-L9`).

Discovery AS-IS имел сильное ядро: юридический `Ferum Contract`, execution project/link, effective-dated objects/scope, генерацию ТО, Visit/Request/evidence, billing output/artifacts, стандартный ERPNext accounting SSOT и Finance Summary read-model. Его W2 snapshot и gaps остаются историческим evidence; completion work теперь ведётся в самостоятельном `contract_accounting`.

TARGET разложен на 557 атомарных требований во всех 20 доменных и 39 процессных разделах: A — 261, B — 296. Вердикты: 139 OK, 19 Gap-Code, 395 Gap-Both, 4 Conflict. Главные разрывы — отсутствие Contract Obligation, Finding/Defect, Inspection, Project Document с двойным статусом оригинала/скана, Contractor Assignment/credentials и всего универсального BPM Template/Stage/Step/Gate/Evidence слоя.

Ключевой discovery-конфликт «Service Project или отдельный Contract» закрыт: `Ferum Service Project` — единый юридический/execution SSOT, а [ADR-CA-0002](implementation/CA-00/ADR-CA-0002-business-replacement-technical-standalone.md) запрещает shared runtime/schema с `ferum_custom`. Legacy N:M data не мигрируются; `MG-CA-001=N/A` подтверждается zero-record inventory и backup.

**Текущий первый исполнимый шаг:** инженерные инкременты и их локальные PASS не объявляются готовым продуктом. Для текущего local `v0.20.0` change-set на Friday, August 21, 2026 подтверждены final-tree static `209/209 PASS`, targeted Inspection `5/5 PASS`, scoped privacy runtime, source-controlled demo lifecycle, exact-source Bench gate `179/179 OK` on isolated `ca01.localhost` (`3693.178s`), full-stack synthetic Engineer browser slice with `socket.io` polling `200`, protection for `main`, and active tag ruleset blocking `refs/tags/v*`. Historical hosted `static-quality` PASS на draft PR head `2865400` сохранён как provenance; hosted CI for the current local change-set remained open at this evidence point. Post-run synthetic DB/File/recovery residue был проверен и очищен только от доказанных zero-DB test-only blobs; финальный postcheck по demo/credential/download/recovery категориям — `0`. Это техническая квалификация review candidate, а не RC/release readiness: Workspace review, actual scanner, human HR/DPO/Security UAT, restore/rollback, performance/race/load, clean Staging, production approval/deployment and separate production-PII permission остаются открытыми.

Заказчик утвердил 23 discovery owner questions и 17 release decisions. Архитектура/scope больше не требуют опроса владельца; остаются CODE/configuration/legal/RBAC/performance/UAT/restore/deployment gates. Migration legacy business data и Import Batch не блокируют first release, но требуют N/A/negative evidence.

## Навигация

| Артефакт | Назначение |
| --- | --- |
| [01_source_inventory.md](01_source_inventory.md) / [CSV](01_source_inventory.csv) | все источники и 54/46 DocType |
| [02_knowledge_base.md](02_knowledge_base.md) | выжимка по 13 областям |
| [03_asis_model.md](03_asis_model.md) | фактическая модель, статусы, rules, ERPNext, ER |
| [04_gap_analysis.md](04_gap_analysis.md) | top-15, конфликты, дельта |
| [04_coverage_matrix.csv](04_coverage_matrix.csv) | 557 атомарных TARGET-требований |
| [05_target_model.md](05_target_model.md) | TO-BE DocType, dual status, BPM, ER, UX |
| [06_roadmap.md](06_roadmap.md) | актуальные волны завершения, инкременты, зависимости, риски |
| [07_traceability.csv](07_traceability.csv) | requirement → AS-IS → TO-BE → increment → acceptance |
| [08_open_questions.md](08_open_questions.md) | 23 APPROVED решения и отдельные manual/runtime gates |
| [09_verification_report.md](09_verification_report.md) | самопроверка Definition of Done |
| [10_remaining_questions_and_actions.md](10_remaining_questions_and_actions.md) | отдельный последовательный план из 22 шагов до complete |
| [11_release_decisions_v1.md](11_release_decisions_v1.md) | утверждённые DP-01…17, Release Scope v1 и Definition of Done |
| [12_release_scope_v1.md](12_release_scope_v1.md) / [557-row CSV](12_release_scope_matrix_v1.csv) | текущая mandatory/partial/absent/deferred capability delta |
| [13_first_release_backlog_v1.md](13_first_release_backlog_v1.md) | dependency-ordered backlog `FR-01…18` |
| [14_quality_profile_v1.md](14_quality_profile_v1.md) | единый static/Bench CI-профиль, команды и границы PASS |
| [15_first_stage_completion_sequence.md](15_first_stage_completion_sequence.md) | текущая короткая последовательность от FR-06 runtime до production/hypercare |
| [implementation/CA-00/demo_uat_productization_plan_v1.md](implementation/CA-00/demo_uat_productization_plan_v1.md) | обязательный воспроизводимый demo/UAT package и fresh-site gate до human UAT |
| [implementation/CA-00/README.md](implementation/CA-00/README.md) | фактический preflight CA-00, W2 readiness и MG-CA-016 gates |
| [implementation/CA-00/ADR-CA-0001-erpnext-custom-party-boundary.md](implementation/CA-00/ADR-CA-0001-erpnext-custom-party-boundary.md) | утверждённая граница ERPNext/custom и Party Identity |
| [implementation/CA-00/ADR-CA-0002-business-replacement-technical-standalone.md](implementation/CA-00/ADR-CA-0002-business-replacement-technical-standalone.md) | `contract_accounting` replaces `ferum_custom` без shared runtime/schema/data |
| [implementation/CA-00/baseline_manifest_2026-08-18.md](implementation/CA-00/baseline_manifest_2026-08-18.md) | completion baseline `7145d87 / 0.16.2`, versions, local tag, gates и evidence boundary |
| [implementation/CA-00/baseline_schema_snapshot_v0_16_2.csv](implementation/CA-00/baseline_schema_snapshot_v0_16_2.csv) | 48 DocType + 5 Page с проверенными baseline Git blob IDs |
| [implementation/CA-00/legacy_data_disposition_2026-08-19.md](implementation/CA-00/legacy_data_disposition_2026-08-19.md) | fail-closed protocol для signed zero-record inventory, backup и `MG-CA-001=N/A` |
| [implementation/CA-00/quality_evidence_v0_16_3_2026-08-19.md](implementation/CA-00/quality_evidence_v0_16_3_2026-08-19.md) | local static PASS и disposable Bench `71/71 OK`; remote CI/UAT/release open |
| [implementation/CA-00/hosted_ci_evidence_v0_19_0_2026-08-19.md](implementation/CA-00/hosted_ci_evidence_v0_19_0_2026-08-19.md) | terminal GitHub Actions `static-quality` PASS на head `9f2cce9` |
| [implementation/CA-00/master_data_boundary_v0_17_0.md](implementation/CA-00/master_data_boundary_v0_17_0.md) | standard ERPNext master reuse, Party Identity и Project/Task/Issue/Asset semantic boundary |
| [implementation/CA-00/traceability_v0_17_0_master_data.md](implementation/CA-00/traceability_v0_17_0_master_data.md) | current overrides для шести закрытых `TCA-A-17-*` требований |
| [implementation/CA-00/runtime_evidence_v0_17_0_2026-08-19.md](implementation/CA-00/runtime_evidence_v0_17_0_2026-08-19.md) | v0.17.0 static `147/147`, migrate/build и final Bench `79/79 OK`; manual/release gates open |
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
| [implementation/CA-08/legal_privacy_package_fr05_v1.md](implementation/CA-08/legal_privacy_package_fr05_v1.md) | FR-05 filled decisions; all named sign-offs confirmed via Product Owner attestation, FR-06 и MG-CA-015 OPEN |
| [implementation/CA-08/privacy_controls_v0_20_0.md](implementation/CA-08/privacy_controls_v0_20_0.md) | FR-06 activation, Worker/Credential, RBAC, readiness, break-glass/legal hold/retention design |
| [implementation/CA-08/verification_evidence_v0_20_0_2026-08-19.md](implementation/CA-08/verification_evidence_v0_20_0_2026-08-19.md) | v0.20.0 final-tree static `209/209`, targeted Inspection `5/5`, scoped privacy runtime, full disposable Bench `179/179 OK` and narrow full-stack Engineer browser ACL PASS; human UAT PENDING, RC/release NOT READY |
| [implementation/CA-08/authenticated_browser_uat_v0_20_0_2026-08-19.md](implementation/CA-08/authenticated_browser_uat_v0_20_0_2026-08-19.md) | 12-role synthetic browser matrix, исправления Office/masked form и Product Owner UI checklist |
| [implementation/CA-09/README.md](implementation/CA-09/README.md) | current CA-09/FR-03 status, derived timeline и production calendar boundary |
| [implementation/CA-09/projection_v0_10_0.md](implementation/CA-09/projection_v0_10_0.md) | normalized row/source adapters и fail-closed classification contract |
| [implementation/CA-09/runtime_evidence_v0_10_0_2026-08-18.md](implementation/CA-09/runtime_evidence_v0_10_0_2026-08-18.md) | exact v0.10.0 versions, 50/50 runtime и 35-DocType inventory |
| [implementation/CA-09/traceability_v0_10_0.md](implementation/CA-09/traceability_v0_10_0.md) | CODE/runtime mapping TCA-A-14 с явными signature/customer-response gaps |
| [implementation/CA-09/production_calendar_v0_18_0.md](implementation/CA-09/production_calendar_v0_18_0.md) | DP-05 calendar design, precedence, source fields и immutable calculation contract |
| [implementation/CA-09/runtime_evidence_v0_18_0_2026-08-19.md](implementation/CA-09/runtime_evidence_v0_18_0_2026-08-19.md) | v0.18.0 migrate/build, targeted `4+3`, full `83/83` и open manual gates |
| [implementation/CA-09/traceability_v0_18_0_calendar.md](implementation/CA-09/traceability_v0_18_0_calendar.md) | current override для `TCA-A-14-09/13` без blanket release PASS |
| [implementation/CA-09/notification_delivery_v0_19_0.md](implementation/CA-09/notification_delivery_v0_19_0.md) | DP-06 thresholds, fail-closed activation, digest, transport и retry/dead-letter contract |
| [implementation/CA-09/runtime_evidence_v0_19_0_2026-08-19.md](implementation/CA-09/runtime_evidence_v0_19_0_2026-08-19.md) | v0.19.0 targeted/full runtime, timezone boundary и open production delivery gates |
| [implementation/CA-09/traceability_v0_19_0_notifications.md](implementation/CA-09/traceability_v0_19_0_notifications.md) | current partial overrides для delivery delta без blanket PASS |
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
| [implementation/CA-15/service_request_disposition_v0_16_3_2026-08-18.md](implementation/CA-15/service_request_disposition_v0_16_3_2026-08-18.md) | v0.16.3 Service Request disposition core, patch и runtime evidence |
| [implementation/CA-15/traceability_v0_16_3.md](implementation/CA-15/traceability_v0_16_3.md) | v0.16.3 request-field/successor/approval traceability addendum |

## Baseline и граница текущего статуса

- TARGET: 2458 строк, SHA-256 `0354D424F623753973101C2B8D30B6BC54FB0351572EF9269DBF60167B7617AC`.
- SPEC: Claude v6.2.21; рабочая и versioned-копии побайтно совпадают.
- CODE discovery snapshots `b1fcaac`/`c97c34a` сохраняются только как historical evidence.
- Completion baseline: `7145d87` / `0.16.2` от 2026-08-18; local+remote annotated tag, manifest/schema hashes и clean `136/136` standalone run — PASS; baseline-exact live inventory и restore — OPEN.
- Current committed branch head: `500cdaf` / `0.19.0`; evaluated uncommitted working tree: `0.20.0`.
- OWNER: OQ-CA-001…023 и DP-01…17 утверждены; manual/runtime/legal/release gates не закрыты owner approval.
- Текущая работа не читала secrets/record contents; выполнила count-only legacy inventory и local backup, но не restore, UAT или deployment gates.
