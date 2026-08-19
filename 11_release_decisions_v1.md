# 11. Пакет утверждённых решений для первого production-выпуска

**Статус документа:** `APPROVED DECISION BASELINE / EVIDENCE PENDING`.

**Версия:** `Release Decisions v1` от 2026-08-19.

**Основание:** пакет из 17 решений, переданный владельцем 2026-08-19. Этот документ является нормализованной фиксацией пакета для разработки, qualification и выпуска. Исходный текст пакета не изменяется.

**Правило приоритета:** при расхождении с discovery-гипотезами, прежним опросником или старыми плановыми формулировками действует настоящий пакет. TARGET и 557 `req_id` сохраняют силу в части, не противоречащей утверждённой границе первого выпуска.

**Граница статуса:** `APPROVED` означает, что решение принято. Это не означает, что CODE реализован, тест пройден, юридическое заключение получено, backup восстановлен, UAT подписан или production развёрнут.

## 1. Сводный реестр

| ID | Решение | Статус решения | Обязательное доказательство |
| --- | --- | --- | --- |
| `DP-01` | `contract_accounting` — единственная целевая система; `ferum_custom` отсутствует в новом runtime | `APPROVED` | ADR, installed-app list, collision scan |
| `DP-02` | Legacy business data не переносятся; production создаётся с чистой базой | `APPROVED / MG-CA-001 N/A` | подписанный inventory `0`, контрольный backup, N/A act |
| `DP-03` | Утверждена граница первого рабочего выпуска | `APPROVED` | Release Scope v1, capability matrix, DoD |
| `DP-04` | Completion baseline — `7145d87` / `0.16.2` от 2026-08-18 | `APPROVED / BASELINE EVIDENCE REQUIRED` | annotated tag, manifest, hashes, clean-tree evidence |
| `DP-05` | Утверждена calendar policy Europe/Moscow, 08:00–19:00 | `APPROVED / CONFIGURATION TEST REQUIRED` | fixture/export, boundary tests |
| `DP-06` | Утверждены in-app/email reminders, escalation и digest | `APPROVED / E2E REQUIRED` | notification matrix, scheduler/E2E evidence |
| `DP-07` | Утверждён минимальный объём ПДн подрядчика | `APPROVED / LEGAL EVIDENCE REQUIRED` | legal-basis и retention matrices, legal sign-off |
| `DP-08` | Утверждены contractor-required и readiness rules | `APPROVED / READINESS TEST REQUIRED` | requirement matrix, readiness UAT |
| `DP-09` | Утверждена Evidence Policy для обязательных фото | `APPROVED / POLICY TEST REQUIRED` | policy fixture, positive/negative tests |
| `DP-10` | Ожидание заказчика — отдельная External Dependency/typed BPM запись | `APPROVED / E2E REQUIRED` | send→wait→overdue→receive→resume |
| `DP-11` | Утверждены обязательные поля заявки и successor flows | `APPROVED / E2E REQUIRED` | Remaining Work и Paid Follow-up E2E |
| `DP-12` | Первый выпуск формирует счёт, акт, УПД, счёт-фактуру, PDF и DOCX | `APPROVED / ACCOUNTING UAT REQUIRED` | templates, numbering, delivery and signed-scan UAT |
| `DP-13` | Import Batch не входит в первый выпуск и отключён | `APPROVED / MG-CA-023 N/A FOR RELEASE` | disabled entrypoints, permissions и negative test |
| `DP-14` | Утверждена RBAC-модель первого выпуска | `APPROVED / RBAC EVIDENCE REQUIRED` | UI/API/report/print/export/private-file tests |
| `DP-15` | Утверждён production qualification envelope | `APPROVED / PERFORMANCE TEST REQUIRED` | report, dataset manifest, environment manifest |
| `DP-16` | Утверждены UAT-сценарии и принимающие | `APPROVED / UAT SIGN-OFF REQUIRED` | protocol, record IDs, evidence, signatures |
| `DP-17` | Утверждены среды, release, backup, rollback и support rules | `APPROVED / DEPLOYMENT EVIDENCE REQUIRED` | runbooks, restore/rollback, smoke, production sign-off |

## 2. Архитектура и данные

### DP-01. Business replacement / technical standalone

- `contract_accounting` является отдельным самостоятельным Frappe-приложением и функционально заменяет `ferum_custom`.
- Новый сайт содержит только утверждённые версии Frappe, ERPNext и `contract_accounting`; любое дополнительное приложение требует отдельного решения.
- `ferum_custom` не устанавливается, не является dependency и не предоставляет код, hooks, patches, fixtures, Custom Fields, custom DocType, schema, database или runtime integration.
- `Company`, `Customer`, `Supplier`, `Sales Invoice`, `Payment Entry`, `Account` и другие стандартные сущности остаются собственностью ERPNext.
- Все собственные доменные сущности принадлежат `contract_accounting`.
- Развитие `ferum_custom` прекращается. Legacy-среда сохраняется только для контрольной проверки и затем архивируется или удаляется по `DP-02` и `DP-17`.

Архитектурная фиксация: [ADR-CA-0002](implementation/CA-00/ADR-CA-0002-business-replacement-technical-standalone.md).

### DP-02. Clean production без migration business data

- Действующая legacy-система признана содержащей только тестовые записи.
- Договоры, проекты, стороны, заявки, документы, файлы, счета, оплаты, статусы, audit events, тестовые users/roles и legacy links не переносятся.
- Копирование старой базы в production запрещено.
- Начальные production-данные создаются заново через UI либо контролируемый setup/import только для утверждённых справочников.
- До удаления legacy-среды обязателен один полный технический backup database/public/private files. Backup хранится до подписания успешного запуска.
- `MG-CA-001` закрывается как `N/A` только после подписанного inventory с количеством реальных записей `0`. Если это условие не подтвердится, решение автоматически возвращается на change control; silent migration запрещена.

**Evidence update 2026-08-19:** owner mapping `ferum.localhost` → internal `dev.localhost` подтверждён; aggregate inventory и local full backup completed with exit `0`. База содержит тестовый dataset, а не ноль строк; `DP-02` фиксирует `0` real business records requiring migration. Formal Data Owner signature и approved off-host retention остаются OPEN.

## 3. Граница первого выпуска

### DP-03. Обязательные capabilities

В первый production-выпуск входят:

1. ERPNext master data: Company, Customer, Supplier/Contractor, Contact, Address и утверждённая Party Identity linkage.
2. Service Project как единый договор; объекты, systems, scope, obligations, launch stages, amendment/security/financial plan по применимости, dual lifecycle, Suspend/Resume.
3. Maintenance Schedule/Visit, Inspection, Finding/Defect, plan/fact, deadlines, overdue и базовый BPM.
4. Service Request: routing, SLA/due date, project/object/system, remaining work, paid follow-up и evidence согласия.
5. Photo Evidence с policy, review и контролируемыми исключениями.
6. Contractor Assignment, минимальный Contractor Worker, qualifications/credentials и readiness; без кабинета подрядчика.
7. Project Document: digital copy, paper-original custody, delivery/receipt, immutable evidence и отдельный signed scan.
8. Standard Sales Invoice/Payment Entry, partial payment, receivables, project profitability, immutable Billing Basis и Billing Output.
9. Генерация счёта, акта, УПД и счёта-фактуры в PDF/DOCX с реквизитами, логотипом, печатью, подписью и signed-scan storage.
10. Упрощённые материальные расходы, выдача/возврат инструмента и контроль инструмента на руках.
11. In-app/email reminders и deadline escalation.
12. Операционные, документарные, финансовые, contractor-readiness и tool-custody reports.
13. Roles/permissions, audit, backup/restore, deployment runbook, monitoring, performance qualification и UAT.

Не входят и не блокируют выпуск: клиентский портал, кабинет подрядчика, Import Batch, 1С, банковские интеграции, ЭДО, КЭП, XML УПД/счёта-фактуры, Telegram, offline, GPS, QR/штрихкоды, расширенный BI, payroll automation, рейтинги и сложные внешние интеграции.

### DP-04. Completion baseline

Утверждённая исходная точка:

| Поле | Значение |
| --- | --- |
| Repository | `contract-accounting` |
| Branch | `main` |
| Commit | `7145d872d45442117d5c114ce4c04c0c8f61d77b` |
| Application version | `0.16.2` |
| Baseline date | `2026-08-18` |
| Требуемый tag | `completion-baseline-v0.16.2` |

Наблюдаемая 2026-08-19 текущая дельта — commit `5249e00849c96cb25fd0f13c5017fbf844db5f3d`, version `0.16.3`. Она не заменяет baseline и должна учитываться как отдельное изменение после него.

Baseline manifest обязан содержать commit/tag, clean status, версии Frappe/ERPNext/app/Python/Node/MariaDB/Redis/Bench, installed apps, patches, sanitized non-secret site configuration, schema/DocType/Custom Field/Workflow/Role/permission/Scheduled Job/fixture snapshots и hash evidence-пакета.

**Evidence update 2026-08-19:** [baseline manifest](implementation/CA-00/baseline_manifest_2026-08-18.md), local+remote annotated tag, verified 53-row schema snapshot and clean `136/136` standalone run are recorded. Baseline-exact live inventory and restore remain OPEN.

## 4. Рабочие политики

### DP-05. Календарь

- Timezone: `Europe/Moscow`.
- Company calendar: официальный российский производственный календарь конкретного года.
- Рабочее окно: `08:00–19:00`.
- Приоритет: Contract Calendar → Company Calendar.
- Нерабочая due date переносится на следующий рабочий день в `19:00`.
- Событие после 19:00 начинается в 08:00 следующего рабочего дня; до 08:00 — в 08:00 текущего рабочего дня, если он рабочий; в нерабочий день — в 08:00 следующего рабочего дня.
- Contract Calendar применяется только при явной договорной норме, версионируется и не пересчитывает прошлые сроки автоматически.
- Ручной пересчёт требует полномочия, причины и audit event.
- Calculation snapshot сохраняет timezone, calendar ID/revision/hash, source datetime, cut-off, result и algorithm version.

### DP-06. Уведомления

| Порог | Получатели | Канал |
| --- | --- | --- |
| −3 рабочих дня | ответственный + Project Manager | in-app + email digest |
| −1 рабочий день | ответственный + Project Manager | in-app + отдельный email |
| 08:00 due date | ответственный + Project Manager | in-app + email |
| наступление overdue | ответственный + Project Manager + process owner | in-app + email |
| +1 рабочий день overdue | Генеральный директор | in-app + email |
| далее до закрытия | ответственные и руководители | digest ежедневно в 09:00 |

Для короткого срока используются пороги 50%, 80% и breach. Одно уведомление допускается на threshold/recipient/correlation key; повтор — только после изменения due date или escalation level. Closed/cancelled records исключаются.

### DP-07. Минимальный Contractor Worker

Разрешены только Ф.И.О., Supplier, рабочая роль, рабочие контакты, внутренний ID, qualification/credential type, number, issuer, issue/expiry date, validity, Project/Assignment link и необходимый private attachment.

В первом выпуске запрещены паспорт и его scan, адрес, birth data, СНИЛС, личный ИНН, банковские, медицинские, биометрические, семейные и иные нецелевые данные.

| Роль | Разрешённый доступ к Contractor Worker |
| --- | --- |
| Personnel Data Manager | полный утверждённый объём |
| Генеральный директор | полный доступ с аудитом |
| Project Manager | Ф.И.О., Supplier, рабочий contact, readiness и credential expiry |
| Service Engineer | только необходимые данные назначенных коллег |
| Office Manager | минимальные рабочие contacts |
| Accountant | только сведения, необходимые для расчётов |
| System Manager | technical break-glass с audit |
| Customer / другой Contractor | доступа нет |

До production data обязательны field registry, purpose/legal-basis/source/consent mapping, retention matrix, block/delete/anonymize rules, export policy, permissions и письменное legal/privacy approval. До этого используются только синтетические данные, а positive Personnel Ready остаётся fail-closed.

### DP-08. Contractor readiness

- `execution_mode`: Internal / Contractor / Mixed; `requires_contractor` может ужесточать правило.
- Ready требует active Supplier, effective Assignment, project/object/scope/period, нужного количества workers, действующих credentials, обязательных документов, site-access rules, отсутствия expired mandatory records и подтверждения Project Manager.
- Pricing не входит в readiness и хранится отдельно.
- Not Ready блокирует работу. Законные/договорные mandatory credentials не имеют override.

### DP-09. Evidence Policy

Минимум: planned maintenance — 2 фото; Inspection — 2; repair/replacement — before+after; Finding — 1 defect photo; resolution — after; emergency visit — 2; remote/document work — 0, если договор не требует.

Обязательны project/object/system/source/category/author/uploaded-at/captured-at-if-known/comment/review status. Завершение блокируется до принятия минимума Project Manager. Исключение требует разрешённой причины, manager approval, alternative evidence и audit event. GPS и отдельный фотоотчёт к акту не входят.

### DP-10. External Dependency

Ожидание customer response хранится отдельной структурированной записью/typed BPM step: project, source record, Customer/contact, sent item/channel/time/evidence, expected result, internal owner, due date/calendar, status, received time/evidence.

Base status — Waiting External, overdue ортогонален. SLA pause допускается только по policy/contract. Устный звонок не является достаточным evidence юридически значимого согласия.

### DP-11. Service Request

Обязательны subject, description, Customer, Service Project, object, system, type, source, received time, requester/contact, priority, owner, SLA/due date, status, obligation link, billable flags и evidence.

Частичное выполнение фиксирует completed/remaining scope и reason, затем создаёт successor `Remaining Work` с predecessor/successor links. Дополнительная платная работа создаётся как `Paid Follow-up` и требует scope, out-of-scope reason, estimate, commercial basis, customer approval evidence и внутреннего коммерческого approval. Устное согласие не включает работу в Billing Basis.

### DP-12. Формируемые документы

- Источник accounting data — standard Sales Invoice; оплат — Payment Entry; выполненных работ — immutable Billing Basis.
- Счёт — первичный billing-документ; один акт связан с одним счётом и создаётся дополнительно.
- УПД и счёт-фактура входят; XML/ЭДО/КЭП/1С не входят.
- Company/Customer дают реквизиты, effective-dated signer registry — подписанта, versioned Print Format — шаблон, approved Company/fiscal-year naming series — номер.
- Сохраняются template version, generated-file hash и отдельный signed scan.
- Delivery evidence хранит channel, time, recipient/sender, outgoing number, exact file/hash, Message-ID/receipt/tracking evidence и receipt/signature status.

### DP-13. Import Batch

Capability должна быть скрыта из Workspace/menu, не иметь user permissions, active API/entrypoint/job и заявленного production support; feature flag — disabled. Включение возможно только новым change decision и повторным открытием `MG-CA-023`.

## 5. Приёмка и выпуск

### DP-14. RBAC

Внутренние роли первого выпуска: Генеральный директор, Project Manager, Office Manager, Service Engineer, Chief Accountant/Accounts User, Personnel Data Manager, System Manager и emergency-only Administrator. Client/Contractor interactive access отсутствует.

| Роль | Основные права | Запреты/ограничения |
| --- | --- | --- |
| Генеральный директор | все business records, approvals, reports, finance, controlled export | не изменяет immutable events и submitted accounting records напрямую |
| Project Manager | projects, objects, obligations, schedules, requests, visits, photos, contractors, documents, project finance summary | не проводит GL, не меняет submitted invoices и signed documents |
| Office Manager | Customer/Contact, Project Document, original custody, delivery, print | нет margin/GL/protected contractor PII |
| Service Engineer | назначенные objects/requests/visits/checklists/comments/photos | нет contract prices, finance, foreign projects, mass export |
| Chief Accountant / Accounts User | Sales Invoice, Payment Entry, Billing Output, act/UPD/invoice-factura, finance reports | не меняет technical evidence/result |
| Personnel Data Manager | Contractor Worker, credentials, retention/export/delete | нет finance/accounting rights |
| System Manager | configuration, migration, diagnostics | business/PII только break-glass с audit |
| Administrator | emergency technical access | не ordinary working account |
| Client / Contractor | interactive access отсутствует | portals deferred |

Доступ ограничивается Company/Project/Assignment; read/write/approve/print/export разделяются. Export не следует из read. UI, API, List/Report, Print, Export и private files обязаны применять одинаковые ограничения. PII/financial export и break-glass журналируются.

### DP-15. Qualification envelope

| Метрика | Приёмка |
| --- | ---: |
| Named / simultaneous / load users | 25 / 12 / 20 |
| Service Projects / objects | 1 000 / 5 000 |
| requests-visits-inspections | 50 000 |
| documents/photos | 100 000 |
| child/evidence rows | 500 000 |
| export | 10 000 rows |
| simultaneous scheduler jobs | 20 |
| form/list p95 | ≤ 2.5 s |
| save/transition p95 | ≤ 3 s |
| operational report p95 | ≤ 5 s |
| director dashboard p95 | ≤ 8 s |
| 10 000-row export | ≤ 60 s |
| recompute 10 000 deadlines | ≤ 10 min |
| error rate | < 0.1% |

Дополнительно обязательны отсутствие loss/duplicates/permission bypass, non-blocking file upload и отсутствие duplicate scheduler notifications на production-equivalent staging.

### DP-16. UAT

| Сценарий | Принимающий |
| --- | --- |
| Customer → Service Project → contract lifecycle | Генеральный директор + Project Manager |
| objects, obligations, scope и launch | Project Manager |
| calendar, deadlines, overdue, notifications | Project Manager + Operations |
| Maintenance Visit, Inspection, Finding | Project Manager + Service Engineer |
| photo evidence и exceptions | Project Manager |
| request, remaining и paid work | Project Manager + Генеральный директор |
| Contractor Assignment и readiness | Project Manager + Personnel Data Manager |
| Project Document и paper original | Office Manager |
| invoice, act, UPD, invoice-factura | Chief Accountant |
| payment, partial payment, receivables | Chief Accountant + Генеральный директор |
| permissions, API, reports, print, export | Security + role owners |
| director dashboard | Генеральный директор |
| backup, restore, deploy, rollback | Release Manager + Operations |

Минимум пять representative Service Project: multi-object planned maintenance; emergency request/repair; paid additional work; contractor+credentials; billing with act/UPD/invoice-factura and partial payment.

Отдельно проверяются Suspended/Resume, Terminated, overdue, foreign-role denial, document without original, defect without required photo и expired credential.

Все critical scenarios должны иметь PASS; Sev1/Sev2 отсутствуют; Sev3 имеют approved workaround и due date; fixes retested; по каждому сценарию сохранены record IDs, evidence и подпись принимающего; общий UAT Sign-off подписан.

### DP-17. Deployment и поддержка

- Изолированные Development, Staging и Production. Staging production-equivalent по versions, configuration, workers, scheduler, email, permissions, Print Formats и database engine.
- Launch sequence: 19:00 configuration freeze → backup → release tag → migrate/build → smoke → roles/scheduler/email/print checks → control E2E → users at 08:00 next working day.
- RPO/RTO: 4/4 hours. Backup каждые 4 часа, daily full, off-host copy, age monitoring и restore test до production.
- Rollback triggers: migration/integrity/login/permission/numbering/legal-document/scheduler/notification/critical-E2E/performance failure.
- После появления production records destructive restore требует отдельной data-loss assessment; иначе forward fix/reconciliation предпочтительны.
- Monitoring: availability, HTTP/app errors, workers/scheduler/jobs, MariaDB, Redis, disk, backup age, email, SSL и response time.
- Hypercare — 10 рабочих дней; единый support channel, Release Manager, Operations owner, Product Owner, incident log и post-release review.

| Severity | Пример | Внутренняя реакция |
| --- | --- | --- |
| P1 | unavailable, data loss, permission breach | немедленная эскалация |
| P2 | не работает key process/document | в течение рабочего часа |
| P3 | существует workaround | следующий рабочий день |
| P4 | improvement | backlog planning |

## 6. Definition of Done первого выпуска

Система получает статус `READY FOR PRODUCTION` только когда одновременно:

1. `DP-01…DP-17` не изменены либо имеют approved change record.
2. Baseline/tag/manifest и текущая delta воспроизводимы.
3. Signed legacy inventory подтверждает `0` business records; backup legacy создан; `MG-CA-001=N/A` оформлен.
4. Все обязательные capabilities `DP-03` имеют CODE/configuration evidence; deferred capabilities недоступны и проходят negative checks.
5. Legal/privacy, RBAC, performance, full UAT, clean install/upgrade, backup/restore, rollback и staging gates имеют PASS на одном immutable RC.
6. Нет Sev1/Sev2; принятые Sev3 задокументированы.
7. Finance, Legal/Privacy, Security, QA, Operations, Product Owner и Release Manager подписали свои gates.
8. Production deployment наблюдён успешным; smoke/health evidence и URL/endpoint status сохранены.

Статус `COMPLETE` допускается после production sign-off и завершения обязательного post-release review; автоматические тесты сами по себе этого статуса не дают.

## 7. Change control

Изменение architecture topology, clean-data decision, first-release scope, calendar, PII fields, RBAC, NFR, UAT или release policy оформляется новой версией decision package. Нельзя молча редактировать эту версию так, чтобы новый смысл выглядел ранее утверждённым.
