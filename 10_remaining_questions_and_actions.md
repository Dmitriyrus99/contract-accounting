# 10. Последовательный план завершения первого production-выпуска

**Статус на 2026-08-19:** `NOT READY FOR PRODUCTION`.

**Цель:** дать один исполнимый порядок от принятого пакета решений до готовой и введённой в эксплуатацию системы.

**Термин «первый этап»:** в этом документе означает первый production-выпуск с полным обязательным scope из [Release Decisions v1](11_release_decisions_v1.md), `DP-03`. Это шире исторического технического MVP `CA-00…CA-07`.

**Code anchor:** approved completion baseline — `7145d87` / `0.16.2`; наблюдаемая текущая дельта — `5249e00` / `0.16.3`. Baseline не заменяется дельтой.

**Правило исполнения:** следующий шаг начинается только после выполнения gate предыдущего шага либо после явно утверждённого waiver. `APPROVED` решение не подменяет CODE, test, legal, UAT или deployment evidence.

## 1. Краткий маршрут

| № | Результат шага | Статус | Основной владелец |
| ---: | --- | --- | --- |
| 1 | Пакет решений и ADR зафиксированы | `DONE` | Product Owner + Architect |
| 2 | Baseline v0.16.2 заморожен tag/manifest | `PARTIAL — LOCAL+REMOTE TAG PASS / LIVE+RESTORE OPEN` | Release Manager |
| 3 | Legacy inventory `0` real records, backup и N/A migration act | `TECHNICAL PASS / SIGNATURE+OFF-HOST OPEN` | Data Owner |
| 4 | Capability/traceability delta первого выпуска | `DONE — 557/557 MATRIX + FR-01…18` | Architect + QA Lead |
| 5 | Единый CI и release evidence profile | `PARTIAL — LOCAL STATIC+BENCH PASS / HOSTED RUN OPEN` | Tech Lead |
| 6 | Production calendar policy реализована и проверена | `PARTIAL — ENGINEERING PASS / OPERATIONS GATES OPEN` | Backend + Operations |
| 7 | Scheduler, reminders, escalation и digest завершены | `PARTIAL — LOCAL E2E PASS / PRODUCTION DELIVERY GATES OPEN` | Backend + Operations |
| 8 | Legal/privacy пакет для Contractor Worker подписан | `DECISIONS FILLED / ALL NAMED SIGN-OFFS CONFIRMED VIA PRODUCT OWNER ATTESTATION` | Legal/Privacy |
| 9 | Contractor Worker/Credential/readiness завершены | `WAITING STEP 8` | Backend + Security |
| 10 | Evidence Policy и mandatory-photo gates завершены | `OPEN` | Process Owner + Backend |
| 11 | External Dependency flow завершён | `OPEN` | Backend + Project Operations |
| 12 | Service Request remaining/paid flows завершены | `PARTIAL v0.16.3` | Backend + Product |
| 13 | Счёт/акт/УПД/счёт-фактура PDF/DOCX завершены | `OPEN` | Finance + Legal + Backend |
| 14 | Материалы, инструмент, reports и process content закрыты | `OPEN` | Product + Process Owners |
| 15 | Полная RBAC/security матрица получает PASS | `OPEN` | Security + QA |
| 16 | Production-equivalent Staging готов | `OPEN` | Release + Operations |
| 17 | Performance/load/race qualification получает PASS | `OPEN` | Performance QA + SRE |
| 18 | Business/finance/legal/security UAT получает PASS | `OPEN` | QA Lead + Product Owner |
| 19 | Backup/restore/rollback/cutover rehearsal получает PASS | `OPEN` | Release + DBA |
| 20 | Immutable RC и все release approvals подписаны | `OPEN` | Release Manager |
| 21 | Production deployment и smoke/health подтверждены | `OPEN` | Release + Operations |
| 22 | Hypercare, post-release review и legacy retirement закрыты | `OPEN` | Product + Operations |

## 2. Подробная последовательность

### Шаг 1. Зафиксировать решения и архитектурную границу

**Выполнено в текущем изменении:**

- создан [Release Decisions v1](11_release_decisions_v1.md);
- создан [ADR-CA-0002](implementation/CA-00/ADR-CA-0002-business-replacement-technical-standalone.md);
- зафиксировано: `contract_accounting` replaces `ferum_custom`, clean database, no shared runtime/schema;
- первый release scope отделён от deferred capabilities;
- owner questions превращены в проверяемые gates.

**Gate:** документы доступны из README/INDEX/roadmap и не противоречат друг другу.

### Шаг 2. Заморозить утверждённый baseline

1. Проверить, что commit `7145d872d45442117d5c114ce4c04c0c8f61d77b` существует и соответствует version `0.16.2`.
2. Annotated tag `completion-baseline-v0.16.2` создан и опубликован; remote tag object `ccb4b73823618b325be60fdf6cbfad163115681d`, peeled target `7145d872d45442117d5c114ce4c04c0c8f61d77b`.
3. Снять clean-tree evidence именно для baseline commit, не для текущего dirty documentation tree.
4. Создать `baseline_manifest_2026-08-18.md`: versions, apps, patches, sanitized config, schema, DocType, Custom Field, Workflow, roles, permissions, scheduled jobs, fixtures и hashes.
5. Записать `5249e00` / `0.16.3` как первую post-baseline delta.

**Текущий evidence:** local+remote tag → `7145d87`, manifest/schema snapshot и clean `136/136` standalone PASS. **Остаточный gate:** baseline-exact live installed-app/config/schema inventory и restore evidence.

### Шаг 3. Закрыть legacy data disposition

Execution/sign-off protocol: [legacy_data_disposition_2026-08-19.md](implementation/CA-00/legacy_data_disposition_2026-08-19.md).

Владелец подтвердил mapping `ferum.localhost` → внутренний Bench site `dev.localhost`. На существующем `ferum-vstand` выполнены count-only inventory и полный сжатый backup: база не пустая, но все категории классифицированы как TEST по `DP-02`; реальных записей для переноса — `0`. Технический evidence зафиксирован в протоколе. Остались формальная подпись Data Owner и защищённая off-host копия с назначенным владельцем хранения.

1. На legacy site выполнить read-only inventory business DocType и files.
2. Data Owner подписывает, что реальных business records — `0`.
3. Создать полный технический backup database/public/private files, проверить его наличие и hash без раскрытия secrets.
4. Оформить `legacy business data migration = NOT REQUIRED` и `MG-CA-001=N/A`.
5. Запретить migration scripts/copy legacy database в новый production.

**Gate:** signed inventory, backup record и N/A act. Если найден хотя бы один реальный record, остановить clean-start path и открыть formal change decision.

### Шаг 4. Получить честную capability delta

1. Пересчитать 557 `req_id` относительно текущего рабочего tree: Implemented / Partial / Absent / Deferred / N/A.
2. Для каждой обязательной capability `DP-03` указать CODE path, automated test, runtime evidence, manual gate и owner.
3. Deferred portal/Import/1С/ЭДО/КЭП/XML/Telegram capabilities пометить `OUT OF RELEASE` и определить negative acceptance.
4. Сформировать Release Scope v1 capability matrix и sprint backlog только из обязательной delta.
5. Проверить отдельно materials/tool custody и все классы обязательных reports: они не должны потеряться за крупными CA-инкрементами.

**Gate:** нет необоснованных `Partial/Absent` и нет mandatory capability без owner/acceptance.

**Результат 2026-08-19:** [Release Scope v1](12_release_scope_v1.md), [557-row matrix](12_release_scope_matrix_v1.csv) и [FR-01…18 backlog](13_first_release_backlog_v1.md) созданы. Все mandatory rows имеют owner, automated acceptance, current evidence reference и manual gate. Шаг 4 закрыт как planning/evidence gate; product/manual gates не повышены до PASS.

### Шаг 5. Зафиксировать единый quality/CI profile

1. Утвердить repository-wide Ruff/format/type profile.
2. Включить standalone tests, Frappe tests, JSON/JS validation, build, traceability validation, secret scan и `git diff --check`.
3. Настроить CI на каждый commit/PR.
4. Сохранять exact command, exit code, versions и final summary.

**Gate:** один clean CI run на текущей post-baseline ветке; skipped gates перечислены явно.

**Результат 2026-08-19:** [Quality/CI Profile v1](14_quality_profile_v1.md) и hosted [static-quality workflow](.github/workflows/static-quality.yml) созданы. Local profile: standalone `161/161`, Ruff/mypy/schema/package checks и checksum-синхронизированный disposable Bench migrate/build/full `89/89 OK`. Опубликованы feature commit `6a93a63` и workflow-trigger head `9f2cce9`; hosted [run 32261790230](implementation/CA-00/hosted_ci_evidence_v0_19_0_2026-08-19.md) завершился terminal `success`. Шаг остаётся PARTIAL только до выбора protected/self-hosted Bench status и повторения static+Bench на одном RC; UAT/release gates не проверялись.

### Промежуточный пакет FR-02. Закрыть ERPNext master-data boundary

1. Использовать standard Customer/Supplier/Company как SSOT и добавить только identity/reconciliation linkage.
2. Перевести Service Object на standard Address/Contact с same-Customer guard.
3. Перевести Material Expense на standard Warehouse с same-Company/non-group guard.
4. Зафиксировать semantic negative acceptance для Project/Task/Issue/Asset и не создавать вторые custom SSOT.
5. Сохранить Workflow/Communication как open до отдельного positive acceptance.

**Результат 2026-08-19:** рабочий tree `0.17.0` реализует Party Identity typed linkage, Address/Contact/Warehouse boundary и policy evidence; local static `147/147`, targeted Party Identity `7/7`, full Bench `79/79 OK`. [Решение](implementation/CA-00/master_data_boundary_v0_17_0.md) и [runtime evidence](implementation/CA-00/runtime_evidence_v0_17_0_2026-08-19.md) записаны. Engineering core закрыт, но owner/browser/race/load UAT и Workflow/Communication остаются OPEN; это не release PASS.

### Шаг 6. Реализовать production calendar

1. Добавить version-controlled Company calendar/holiday fixture для применимого года и Contract Calendar override.
2. Реализовать 08:00/19:00 cut-offs, next-working-day перенос и calendar/business-day rules.
3. Сохранять immutable calculation snapshot.
4. Ограничить manual recalculation ролью, reason и audit.
5. Проверить before/after hours, weekend/holiday, shortened day, contract override и old calculation after calendar revision.

**Gate:** configuration evidence и automated boundary suite PASS; hard-coded временный calendar отсутствует.

**Результат 2026-08-19:** рабочий tree `0.18.0` содержит source-controlled `RU-5D-2026-v1` с официальным основанием, hash и runtime counts `247/118/4`; Company/Contract precedence, cut-offs, holiday/weekend/shortened day, immutable history, typed signature/customer-response sources и manual recalculation проверены targeted `4/4+3/3` и full Bench `83/83`. [Design](implementation/CA-09/production_calendar_v0_18_0.md) и [runtime evidence](implementation/CA-09/runtime_evidence_v0_18_0_2026-08-19.md) записаны. Engineering gate PASS; site assignment, annual revision procedure, Operations/browser/performance/race UAT остаются OPEN, поэтому это не release PASS.

### Шаг 7. Завершить scheduler и уведомления

1. Настроить scheduler events/workers для recurring maintenance, billing/process instances и deadline scans.
2. Реализовать thresholds −3d, −1d, due 08:00, overdue, +1d director escalation и daily 09:00 digest.
3. Добавить correlation key, idempotency, retry/dead-letter и audit.
4. Исключить closed/cancelled и duplicate notifications.
5. Проверить in-app и email delivery на production-shaped mail configuration.

**Gate:** E2E `deadline→reminder→overdue→escalation→close` PASS, повторный job не создаёт дубликаты.

**Результат 2026-08-19:** working tree `0.19.0` реализует fail-closed activation watermark, все DP-06 thresholds, short-SLA fallback, timezone-aware 09:00 digest, permission-filtered `Notification Log`/delayed `Email Queue`, immutable correlation/payload, retry/dead-letter и typed manual retry. Targeted `6/6` и full Bench `89/89 OK`; closed source не рассылается, повтор не создаёт duplicates, settings после теста `enabled=0`. [Design](implementation/CA-09/notification_delivery_v0_19_0.md) и [runtime evidence](implementation/CA-09/runtime_evidence_v0_19_0_2026-08-19.md) записаны. Шаг остаётся PARTIAL до production activation, external SMTP receipt/bounce, scheduler heartbeat, Operations/RBAC/load UAT и sign-off.

### Шаг 8. Получить legal/privacy approval

1. Утвердить Contractor Worker field registry в минимальном объёме `DP-07`.
2. Для каждой категории определить purpose, legal basis, source, consent applicability, retention start/period, block/delete/anonymize rule.
3. Утвердить role/permlevel, export/delete и private attachment policy.
4. Утвердить break-glass procedure и audit.
5. Получить письменное заключение Legal/Privacy/Security.

**Gate:** `MG-CA-015 PASS`. До него production PII и production positive Personnel Ready запрещены; synthetic runtime допускается только на изолированном контуре.

**Результат 2026-08-21:** [FR-05 legal/privacy package v1](implementation/CA-08/legal_privacy_package_fr05_v1.md) заполнен; Product Owner подписал пакет и аттестовал все названные подтверждения, без предоставленных номеров актов. FR-06 v0.20.0 реализован в [зафиксированной архитектуре](implementation/CA-08/privacy_controls_v0_20_0.md), прошёл [static + disposable Bench gate](implementation/CA-08/verification_evidence_v0_20_0_2026-08-19.md) и [authenticated synthetic browser evidence](implementation/CA-08/authenticated_browser_uat_v0_20_0_2026-08-19.md). Browser evidence сохраняет historical 12-role matrix как provenance, а current accepted slice даёт full-stack Engineer own/foreign Form ACL, own-only List, foreign direct `403`, and `socket.io` polling `200`. Текущий зависимый gate: совместно утвердить Workspace, list columns/filters, form grouping/labels/options и timezone. До actual scanner integration, human HR/DPO/Security UAT и отдельного production-PII permission `MG-CA-015` остаётся PARTIAL и production PII запрещены.

### Шаг 9. Завершить contractor personnel и readiness

1. Реализовать protected Contractor Worker и Credential lifecycle без запрещённых полей.
2. Реализовать Internal/Contractor/Mixed и explicit `requires_contractor`.
3. Проверять active Supplier, effective Assignment, project/object/scope/period, worker count, credentials, documents и access rules.
4. Автоматически снимать Ready при expiry.
5. Реализовать только допустимые override; mandatory legal/contract credential override запрещён.
6. Проверить row-level access, private files, export/delete/retention и audit.

**Gate:** UAT `Not Ready→Ready→Expired` и negative permission suite PASS.

### Шаг 10. Внедрить Evidence Policy

1. Создать versioned Evidence Policy по виду работы с минимумами `DP-09`.
2. Связать policy с Visit/Inspection/Request/Finding и Contract override.
3. Блокировать completion до manager-accepted evidence.
4. Реализовать контролируемое исключение: reason, alternative evidence, approval, audit.
5. Исключить GPS и отдельный фотоотчёт к акту из first release.

**Gate:** positive/negative completion tests и exception audit PASS.

### Шаг 11. Завершить ожидание заказчика

1. Реализовать External Dependency либо утверждённый typed BPM-step.
2. Хранить sent item/channel/time/evidence, expected result, contact, owner, due/calendar и received evidence.
3. Сделать Waiting External base state и overdue отдельным derived state.
4. Приостанавливать SLA только по явной policy/contract.
5. Не принимать устный звонок как legal approval evidence.

**Gate:** E2E `send→waiting→overdue→receive→resume` PASS.

### Шаг 12. Завершить Service Request disposition

1. Сверить v0.16.3 с `DP-11` и закрыть оставшиеся Internal/Other source semantics.
2. Довести обязательные subject/description/customer/project/object/system/source/SLA/billable/evidence fields.
3. Проверить idempotent Remaining Work successor с completed/remaining scope и reason.
4. Проверить Paid Follow-up с estimate, commercial basis, customer evidence и internal approval.
5. Добавить concurrency/race и cross-role/browser cases.

**Gate:** оба E2E PASS; устное согласие не попадает в Billing Basis; duplicate successor невозможен.

### Шаг 13. Завершить contract-to-cash документы

1. Утвердить шаблоны счёта, акта, УПД и счёта-фактуры с Finance/Legal.
2. Реализовать PDF и DOCX, effective signer, Company/fiscal-year naming series, logo/stamp/signature settings.
3. Сохранить template version и generated-file hash; signed scan хранить отдельно.
4. Проверить правило «invoice primary, one act per invoice».
5. Реализовать delivery evidence и receipt/signature status.
6. Связать Billing Basis → Output/Document → Sales Invoice → Payment Entry → partial/outstanding.

**Gate:** finance/legal UAT связки `Invoice→Act/UPD/SF→Delivery→Signed Scan→Payment` PASS.

### Шаг 14. Закрыть остальные обязательные product capabilities

1. Проверить и завершить material expense flow.
2. Реализовать выдачу/возврат инструмента и report «инструмент на руках».
3. Настроить process/BPM content для пяти representative projects, не ограничиваясь demo templates.
4. Завершить обязательные reports: contracts/problems, overdue obligations, maintenance without photos, requests, unsigned documents, unpaid invoices, profitability, contractor readiness и tools.
5. Проверить Suspend/Resume/Terminated, Inspection outputs, paper-original state и partial payments.

**Gate:** capability matrix шага 4 не содержит mandatory `Absent`; process owners приняли content.

### Шаг 15. Выполнить полную RBAC/security qualification

1. Зафиксировать role matrix `DP-14` и Company/Project/Assignment scoping.
2. Проверить create/read/write/approve/print/export раздельно.
3. Выполнить UI/API/List/Report/Print/Export/private-file tests.
4. Добавить cross-company, cross-project, unassigned engineer, PII, finance, immutable-event и submitted-accounting negative cases.
5. Проверить System Manager break-glass и запрет ordinary use Administrator.
6. Проверить отсутствие interactive Client/Contractor и Import Batch access.

**Gate:** Security sign-off; ни одного permission bypass; финансовые/PII exports аудитируются.

### Шаг 16. Собрать production-equivalent Staging

1. Развернуть чистые Development, Staging и будущий Production contour.
2. На Staging установить только approved Frappe/ERPNext/`contract_accounting` versions.
3. Доказать отсутствие `ferum_custom` и schema/hooks/fixture collisions.
4. Выполнить fresh install, repeated migrate, build и clean reinstall.
5. Настроить production-equivalent workers, scheduler, email, permissions, Print Formats и database engine.
6. Загрузить только synthetic/reference qualification dataset.

**Gate:** environment manifest, installed-app list, collision scan и staging smoke PASS.

### Шаг 17. Выполнить performance/load/race qualification

1. Создать dataset manifest: 1 000 projects, 5 000 objects, 50 000 operational records, 100 000 files/docs, 500 000 child/evidence rows.
2. Проверить 20 concurrent users, 20 scheduler jobs и 10 000-row export.
3. Измерить все p95/limits `DP-15`.
4. Провести races: successor creation, schedule generation, billing, deadline recompute, notification retry, assignment expiry и finance rebuild.
5. Проверить error rate <0.1%, no loss/duplicates/permission bypass.

**Gate:** signed performance report PASS на production-equivalent Staging.

### Шаг 18. Выполнить полный UAT

1. Подготовить пять representative Service Project из `DP-16`.
2. Назначить принимающего каждому business/security/operations scenario.
3. Выполнить все critical flows, включая отрицательные и exceptional cases.
4. Сохранять record IDs, screenshots/files/log evidence, expected/actual result и подпись.
5. Исправить дефекты и повторить затронутые сценарии.

**Gate:** 100% critical PASS, Sev1/Sev2 = 0, accepted Sev3 documented, общий UAT Sign-off подписан.

### Шаг 19. Отрепетировать backup, restore, rollback и cutover

1. Проверить database/public/private/config/release-manifest backups и off-host copy.
2. Выполнить полный restore test без чтения/публикации secret values.
3. Отрепетировать failed migration, permission breach и failed E2E rollback triggers.
4. Проверить RPO/RTO 4h/4h и backup-age alerting.
5. Выполнить cutover rehearsal: 19:00 freeze → backup → tag → migrate/build → smoke → E2E → 08:00 open.
6. Зафиксировать after-real-data policy: destructive restore только после data-loss assessment.

**Gate:** restore/rollback/cutover reports PASS и подписаны Release/DBA/Operations.

### Шаг 20. Собрать immutable Release Candidate

1. Зафиксировать RC commit/tag, changelog, wheel/source hashes и dependency/SBOM record.
2. Привязать CI, Frappe, browser, RBAC, performance, UAT, restore и staging logs к одному final tree.
3. Убедиться, что deferred capabilities скрыты и negative-tested.
4. Получить подписи Product, QA, Security, Finance, Legal/Privacy, Operations и Release.
5. Зафиксировать go/no-go и rollback authority.

**Gate:** ни один обязательный release gate не OPEN; RC immutable.

### Шаг 21. Выпустить Production

1. Выполнить утверждённый runbook в окне `DP-17`.
2. Наблюдать успешный migrate/build/service start.
3. Выполнить smoke: login, roles, scheduler, email, print, key E2E и monitoring.
4. Сохранить production URL/endpoint health evidence без secrets.
5. Открыть пользователям только после go decision.

**Gate:** production sign-off, smoke/health PASS, monitoring/backup active. До наблюдаемого успешного результата deployment нельзя объявлять завершённым.

### Шаг 22. Завершить hypercare и legacy retirement

1. Вести десять рабочих дней усиленного сопровождения и incident log.
2. Применять P1–P4 response rules из `DP-17`.
3. Провести post-release review и закрыть обязательные corrective actions.
4. После успешного акта запуска и проверки backup архивировать либо удалить legacy environment отдельной утверждённой операцией.
5. Перевести deferred capabilities в roadmap последующих выпусков.

**Gate:** hypercare exit signed; unresolved P1/P2 отсутствуют; legacy disposition documented.

## 3. Финальный критерий

Статус `READY FOR PRODUCTION` появляется после шага 20. Статус `PRODUCTION LIVE` — после шага 21. Статус первого выпуска `COMPLETE` — только после шага 22.

Текущая работа опубликовала completion tag и выполнила разрешённые legacy `list-apps`, aggregate inventory и local control backup. Для v0.20.0 отдельно выполнены repeated migrate/build, server RBAC/private-file acceptance и synthetic Frappe `94/94 OK` только на disposable `ca01.localhost`; это не подтверждает authenticated browser/scanner UAT, restore, performance, Staging или Production deployment и не повышает release до PASS.
