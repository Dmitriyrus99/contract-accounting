# 08. Реестр discovery-решений и evidence gates

**Цель документа:** сохранить историю 23 discovery owner decisions и синхронизировать их evidence gates с утверждённым первым production-выпуском.

**Дата анализа:** 2026-08-17. **Дата owner approval:** 2026-08-18. **Release package supersession:** 2026-08-19.

**Источник истины:** для истории discovery — настоящий реестр; для release topology, scope, exact baseline, calendar, PII, RBAC, NFR, UAT и deployment — [Release Decisions v1](11_release_decisions_v1.md). При расхождении release package имеет приоритет.

**Как проверить:** все 23 OQ должны иметь утверждённое решение; отсутствие runtime/manual evidence отражается не возвратом OQ в UNKNOWN, а отдельным применимым `MG-CA-*` gate. `MG-CA-001` и `MG-CA-023` сняты с functional scope первого выпуска, но требуют N/A/negative evidence. Сверить с [Release Decisions v1](11_release_decisions_v1.md), [06_roadmap.md](06_roadmap.md) и [последовательным планом](10_remaining_questions_and_actions.md).

## Сводка статусов

| Статус | Количество | Идентификаторы |
| --- | ---: | --- |
| `APPROVED` | 23 | OQ-CA-001–023 |
| `OPEN / BLOCKING` | 0 | — |
| `OPEN / UNKNOWN` | 0 | — |

Утверждение не меняет `SPEC/CODE` coverage и не означает реализацию. Release package дополнительно закрыл topology/scope/NFR вопросы; остаток — implementation, configuration, legal/privacy, UAT и release evidence.

## Архитектура договора

### OQ-CA-001. Как разобрать legacy cardinality Contract ↔ Service Project при переходе к TARGET?

**Статус:** `APPROVED` — owner decision 2026-08-18; рекомендация ниже нормативна.

**Блокирует:** cutover единого корня, direct links Amendment/Security/Stage и миграцию неоднозначных записей; нормативную TO-BE ER не меняет.

TARGET говорит «один Service Project = один договор» (`Structure of the contract accounting system.md:L44-L85`). Accepted ADR и последующий owner act Р-1 сохраняют `Ferum Contract` отдельно и связывают его с project, причём сам act прямо говорит, что нормой не является до change-set (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/adr/ADR-0003-service-project-vs-legal-contract.md:L52-L69`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/plan/owner_decisions_2026-08-17_target_structure.md:L1-L9`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/plan/owner_decisions_2026-08-17_target_structure.md:L19-L31`). OQ-225 указывает, что машинного запрета «один договор — один project» нет (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/plan/07_open_questions.md:L1988-L2014`).

**Рекомендация:** следовать TARGET — один `Ferum Service Project` = один исполняемый договор; переносить legacy Contract автоматически только при однозначном 1:1 mapping. N:M вынести в exception report для ручного split/merge; сохранение отдельного Contract-root возможно только как формально утверждённое изменение TARGET.

### OQ-CA-002. Переносятся ли Amendment, Execution Stage, Security и Financial Plan на direct Service Project Link?

**Статус:** `APPROVED` — owner decision 2026-08-18; рекомендация ниже нормативна.

**Блокирует:** юридическую историю целевого единого договора и retirement legacy Contract.

Сейчас они project-centric (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract_amendment/ferum_contract_amendment.json#service_project`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract_security/ferum_contract_security.json#service_project`). Amendment apply отказывает при primary contract более чем одного project (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/services/contract_amendment_apply.py:L78-L147`).

**Рекомендация:** direct `service_project` обязателен как Link на единый договор; legacy `contract` сохраняется только как read-only migration provenance до retirement.

### OQ-CA-003. Какова целевая dual-status FSM договора?

**Статус:** `APPROVED` — owner decision 2026-08-18; legacy/test status migration не требуется.

**Снимает блокировку:** проектирование TARGET Workflow, permissions, reports, automation и audit новых переходов. Реализация и runtime tests остаются отдельными gates.

CODE имеет Draft/OnApproval/Approved/Signing/Signed/Active/Suspended/Completed/Terminated/Closed/Cancelled/Archived (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract/ferum_contract.json#status`); исходный TARGET требует отдельные legal/execution и содержит иной рекомендуемый enum (`Structure of the contract accounting system.md:L582-L629`). Решение ниже является явным owner-approved TARGET change-set; исходные SPEC/CODE/TARGET evidence не переписываются.

**Утверждённое решение:**

- `legal_status`: `Draft`, `On Approval`, `Approved`, `Signing`, `Signed`, `In Force`, `Cancelled`, `Terminated`, `Expired`;
- legal transitions: `Draft→On Approval/Cancelled`; `On Approval→Draft/Approved/Cancelled`; `Approved→Draft/Signing/Cancelled`; `Signing→Approved/Signed/Cancelled`; `Signed→In Force/Terminated`; `In Force→Terminated/Expired`; `Cancelled`, `Terminated`, `Expired` terminal;
- `execution_status`: `Not Started`, `Launching`, `Active`, `Suspended`, `Completed`, `Stopped`;
- execution transitions: `Not Started→Launching/Stopped`; `Launching→Active/Suspended/Stopped`; `Active→Suspended/Completed/Stopped`; `Suspended→Launching/Active/Stopped`, причём Resume возвращает только в сохранённый `suspended_from_status`; `Completed` и `Stopped` terminal;
- допустимые пары: Draft/On Approval/Approved/Signing→Not Started; Signed→Not Started/Launching/Suspended, причём Suspended только из Launching; In Force→Not Started/Launching/Active/Suspended/Completed; Cancelled→Stopped; Terminated→Stopped либо в документированном исключении Completed; Expired→Completed/Stopped;
- `Active` разрешён только при `legal_status=In Force`; `Suspended→Completed` запрещён; новые работы запрещены при Cancelled/Terminated/Expired, но billing, документы, AR, payments, finance reconciliation и audit продолжаются;
- Cancelled означает несостоявшийся договор, Terminated — досрочное прекращение уже заключённого; для Cancelled/Terminated/Stopped обязательны reason и immutable audit, для Terminated также termination date/basis/related document по применимой политике;
- каждый переход пишет immutable event: service_project, dimension, from/to, actor/time, reason и evidence; административная коррекция терминального статуса — отдельная контролируемая операция, не workflow transition;
- связанный переход двух осей выполняется атомарной server-side командой; два audit events получают общий correlation id, промежуточная недопустимая пара не сохраняется;
- `Closed` и `Archived` исключены из обеих FSM; архивирование хранится в `is_archived/archived_at/archived_by`, closeout при необходимости — derived state;
- legacy/test `Contract.status` и тестовая audit history не мигрируются, записи допускается reset/recreate.

## Obligations и execution

### OQ-CA-004. Является ли Project Scope Contract Obligation или правилом дочернего уровня?

**Статус:** `APPROVED` — owner decision 2026-08-18; рекомендация ниже нормативна.

**Блокирует:** Requirement→Obligation→Schedule и migration W2.

Scope содержит work/frequency/SLA/evidence (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_scope/ferum_project_scope.json#work_type`), но TARGET отделяет recurring Obligation (`Structure of the contract accounting system.md:L188-L228`; `Structure of the contract accounting system.md:L2240-L2286`). Owner act Р-4, не ставший нормой, напротив называет Project Scope повторяющимся договорным обязательством (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/plan/owner_decisions_2026-08-17_target_structure.md:L85-L94`).

**Рекомендация:** Obligation — юридико-операционный root; Scope — effective-dated техническое правило obligation.

### OQ-CA-005. Finding и Defect — два DocType или одна сущность с подтверждением?

**Статус:** `APPROVED` — один `Ferum Finding`, включая `category=Defect`; отдельный Defect не вводится.

**Блокирует:** Inspection, Request creation, KPI старых дефектов и billing дополнительных работ.

TARGET допускает Finding/Defect, но подчёркивает отличие от заявки/работы (`Structure of the contract accounting system.md:L350-L397`). CODE имеет только Service Request type Defect (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_request/ferum_service_request.json#request_type`). Owner act Р-6 выбирает отдельный `Ferum Defect`, но сам act не является нормой до change-set (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/plan/owner_decisions_2026-08-17_target_structure.md:L1-L9`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/plan/owner_decisions_2026-08-17_target_structure.md:L107-L119`).

**Варианты:** один `Ferum Finding` с категорией/подтверждением дефекта; либо отдельные Finding и Defect с неизменяемой связью происхождения.

**Рекомендация:** принять модель [05_target_model.md](05_target_model.md#30-решение-findingdefect): один parent `Ferum Finding`, `category=Defect` и отдельный confirmation/resolution lifecycle. Отдельный Defect вводить только если владелец подтвердит различную юридическую неизменяемость двух записей; тогда одновременно изменить roadmap и traceability.

### OQ-CA-006. Inspection заменяет Visit Checklist или является самостоятельным документом?

**Статус:** `APPROVED` — самостоятельный Inspection со snapshot checklist.

**Блокирует:** initial survey process и миграцию checklist evidence.

TARGET выделяет `Ferum Inspection` с собственным checklist и выходами Finding/Defect/report (`Structure of the contract accounting system.md:L1582-L1656`); CODE имеет template/checklist visit, но отдельного Inspection DocType нет (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_checklist_template/ferum_checklist_template.json#name`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_maintenance_visit/ferum_maintenance_visit.json#checklist`).

**Варианты:** самостоятельный Inspection со snapshot checklist; либо subtype Maintenance Visit.

**Рекомендация:** самостоятельный Inspection с snapshot checklist; Maintenance Visit может ссылаться на Inspection, но не заменяет его.

## Документы и billing

### OQ-CA-007. Каков канонический lifecycle Project Document и бумажного оригинала?

**Статус:** `APPROVED` — независимые digital/original statuses и immutable events/evidence.

**Блокирует:** `digital_copy_status`, `original_status`, file locks, gates и director KPI.

CODE знает Signed Scan и shipment/receipt, но не двойной status (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_billing_artifact/ferum_billing_artifact.json#artifact_type`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_billing_output/ferum_billing_output.json#shipment_date`). TARGET требует независимый учёт (`Structure of the contract accounting system.md:L1920-L1946`).

**Варианты:** независимые `digital_copy_status`/`original_status` в Project Document; либо отдельные lifecycle records для каждой материальной формы.

**Рекомендация:** два независимых Select в Project Document плюс неизменяемые events/evidence; физический File остаётся standard Frappe File, бумажный оригинал не моделируется фиктивным файлом.

### OQ-CA-008. Что является immutable Billing Basis snapshot?

**Статус:** `APPROVED` — child snapshot rows по рекомендации ниже.

**Блокирует:** доказательство «какие работы вошли в акт» и unbilled work.

Сейчас Output имеет один `basis_service_request` (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_billing_output/ferum_billing_output.json#basis_service_request`). Owner decision предлагает derived selection + immutable Billing Basis Item (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/plan/owner_decisions_2026-08-17_target_structure.md:L146-L164`).

**Рекомендация:** child rows с source_doctype/name, accepted snapshot/hash, amount/period и reversal/supersession.

### OQ-CA-009. Разрешено ли менять коммерческие Service Project Line без Amendment?

**Статус:** `APPROVED` — только Amendment-generated effective-dated replacement.

**Блокирует:** contractual pricing и invoice basis.

OQ-222 фиксирует текущую возможность и перенос решения на Billing W2+ (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/plan/07_open_questions.md:L2022-L2030`).

**Варианты:** запрет правок после `legal_status=Signed/In Force`; либо versioned line с effective dates; либо только Amendment-generated replacement rows.

**Рекомендация:** Amendment-generated effective-dated replacement; исходная строка не редактируется и остаётся в audit chain.

## BPM и deadlines

### OQ-CA-010. Какие BPM элементы parent, child или typed step?

**Статус:** `APPROVED` — физическая parent-модель из 05; оптимизация только новым ADR.

**Блокирует:** физический каталог DocType, permissions, version snapshots и производительность.

Owner decision разрешает минимизацию физических DocType, а TARGET перечисляет логические Template/Stage/Step и instance-узлы без обязательного запрета отдельных DocType (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/plan/owner_decisions_2026-08-17_target_structure.md:L96-L105`; `Structure of the contract accounting system.md:L1001-L1069`; `Structure of the contract accounting system.md:L2322-L2354`).

**Варианты:** отдельные parent DocType для всех логических узлов; либо child Stage/Template Step и typed Gate при доказанной эквивалентности audit/permissions/versioning.

**Рекомендация:** ратифицировать физическую модель [05_target_model.md](05_target_model.md#3-новые-doctype): отдельные parent Template/Stage/Step, Project Process/Stage/Process Step и Stage Gate, Evidence parent. Child optimization допускается только отдельным ADR до реализации CA-11.

### OQ-CA-011. Какой язык условий используется для condition/activation/gates?

**Статус:** `APPROVED` — JSON Logic allowlist, versioned schema, no eval.

**Блокирует:** безопасность и детерминизм.

TARGET требует `condition` и `activation_rule`, но не задаёт безопасный язык выражений (`Structure of the contract accounting system.md:L1293-L1322`).

**Варианты:** ограниченный JSON Logic; declarative rule rows; Python expressions запрещены.

**Рекомендация:** JSON Logic с allowlist полей/операторов, versioned schema и no eval.

### OQ-CA-012. Overdue — самостоятельный status или вычисляемый флаг?

**Статус:** `APPROVED` — persisted base status + derived overdue attributes/display status.

**Блокирует:** возможность одновременно показать Waiting External/Blocked и overdue.

TARGET перечисляет Overdue как status (`Structure of the contract accounting system.md:L2049-L2079`), но operational semantics требуют ортогональности.

**Варианты:** persisted `status=Overdue`; либо base status + derived overdue attributes/display status.

**Рекомендация:** модель [05_target_model.md](05_target_model.md#52-нормированные-перечисления): base `status` + `is_overdue/overdue_since`, UI `display_status=Overdue`. Это сохраняет одновременно Waiting External/Blocked и просрочку, но требует ратификации как уточнение TARGET.

### OQ-CA-013. Какие календарь и часовой пояс нормативны?

**Статус:** `APPROVED / CONFIGURATION TEST REQUIRED` — `Europe/Moscow`, Company calendar РФ, `08:00–19:00`, Contract→Company priority и immutable calculation snapshot.

**Блокирует:** deadline/offset/SLA/escalation.

TARGET различает Calendar/Business Days и относительные сроки, но не определяет приоритет календарей и timezone (`Structure of the contract accounting system.md:L1196-L1251`; `Structure of the contract accounting system.md:L2080-L2104`).

**Варианты:** Company Holiday List/timezone; project override; contract-specific immutable calendar snapshot.

**Решение release package:** применяются правила `DP-05`: before/after-hours cut-off, next-working-day перенос, versioned contract override и audit manual recalculation. `MG-CA-013` configuration/code evidence закрыт в working tree `0.18.0`: официальный fixture 2026, hash, exact `247/118/4`, targeted `4/4+3/3`, full Bench `83/83`. Site-specific assignment, Operations/browser/performance UAT остаются gates, а не новым owner choice.

## Подрядчики и персонал

### OQ-CA-014. Contractor Assignment включает pricing или только responsibility?

**Статус:** `APPROVED` — Assignment без pricing SSOT; pricing в terms/settlement.

**Блокирует:** схему assignment/settlement и MVP scope.

Owner decision отделяет assignment от pricing (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/plan/owner_decisions_2026-08-17_target_structure.md:L166-L176`).

**Рекомендация:** Assignment отвечает кто/где/что/когда; pricing — отдельные terms/settlement rows.

### OQ-CA-015. Где хранится worker identity и credentials подрядчика?

**Статус:** `APPROVED — MINIMAL PII SCOPE / LEGAL EVIDENCE REQUIRED` — Employee для staff, protected Contractor Worker для внешних исполнителей.

**Блокирует:** production-схему `Ferum Contractor Worker`/`Ferum Personnel Credential`, загрузку персональных данных и включение PERSONNEL READY gate. До решения допустим только schema/privacy spike без production data.

TARGET требует Required Qualification → Worker Credential и gate готовности (`Structure of the contract accounting system.md:L1483-L1533`).

**Варианты:** Employee для всех; Contact/Party worker для подрядчиков; отдельный protected Worker master.

**Решение release package:** standard Employee только для staff; отдельный минимальный protected Contractor Worker для внешних исполнителей. Разрешены только рабочая идентификация/контакты и qualification/credential data из `DP-07`. Паспорт, scan паспорта, адрес, birth data, СНИЛС, личный ИНН, банковские, медицинские и биометрические данные в первом выпуске запрещены.

До production data обязательны legal-basis/retention/access/export/delete matrices и письменное approval `MG-CA-015`. До этого используются только synthetic data; synthetic positive PERSONNEL READY проверен на disposable site, а production activation остаётся fail-closed.

## Baseline history

### OQ-CA-016. Какой CODE snapshot официально считать AS-IS baseline?

**Статус:** `APPROVED / BASELINE EVIDENCE REQUIRED`.

**Блокирует:** воспроизводимость completion work и release evidence.

W2/`ferum_custom` snapshots остаются provenance discovery и не являются completion baseline самостоятельного приложения.

**Решение release package:** официальный completion baseline — repository `contract-accounting`, branch `main`, commit `7145d87`, version `0.16.2`, date 2026-08-18; требуемый tag — `completion-baseline-v0.16.2`. Текущий `5249e00` / `0.16.3` — post-baseline delta. `MG-CA-016` закрывается tag/remote SHA, clean-tree proof, exact versions, installed apps, patches, sanitized config, schema/DocType, Custom Field, Workflow, roles/permissions, Scheduled Job Type, fixtures и hashes.

## Master data, governance, runtime

### OQ-CA-017. Кто владеет Party Identity vs Customer/Supplier/Company?

**Статус:** `APPROVED` — Customer/Supplier/Company остаются domain master SSOT; Party Identity является linkage/reconciliation layer.

**Блокирует:** sync/duplicate/reconciliation, но не MVP obligations.

CODE содержит links и duplicate review, автоматического create/sync не найдено (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_party_identity/ferum_party_identity.py:L100-L281`).

**Решение:** `Ferum Party Identity` владеет cross-master identifiers, links, duplicate/reconciliation state и provenance, но не заменяет ERPNext masters. Произвольный bidirectional sync business fields запрещён; расхождения разрешаются explicit reconciliation workflow либо отдельно утверждённым односторонним field rule. Create/link идемпотентен, неоднозначные организации автоматически не объединяются.

### OQ-CA-018. Нужен ли Input VAT в Company Tax Account?

**Статус:** `APPROVED` — поддерживать `Output VAT` и `Input VAT` как configuration purposes.

Claude оставляет только Output VAT, Codex допускает Input VAT (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_company_tax_account/ferum_company_tax_account.json#purpose`; `Вспомогательные/Codex ferum_custom/ferum_custom/ferum_custom/doctype/ferum_company_tax_account/ferum_company_tax_account.json#purpose`).

**Решение:** Company Tax Account — mapping к standard ERPNext Account, не ledger. Sales/Purchase Invoice, Payment Entry, Accounts и GL остаются accounting/tax SSOT; альтернативный налоговый учёт и correction GL Entries из custom app запрещены.

### OQ-CA-019. Была ли замена Dynamic Link на Data для source_name осознанной?

**Статус:** `APPROVED` — Dynamic Link для active policy/lock; guarded Data + immutable snapshot только для append-only log.

**Влияет:** ссылочная целостность Audit/Notification/File Policy/Lock.

Claude использует `source_name:Data`, Codex — Dynamic Link в ряде служебных схем (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_audit_log/ferum_audit_log.json#source_name`; `Вспомогательные/Codex ferum_custom/ferum_custom/ferum_custom/doctype/ferum_audit_log/ferum_audit_log.json#source_name`).

**Варианты:** Dynamic Link; Data + server-side existence guard; immutable snapshot без FK для удаляемых источников.

**Рекомендация:** Dynamic Link для активных policy/lock записей; Data + immutable source snapshot допустим только для append-only audit/notification log.

### OQ-CA-020. Должен ли Service Project.Suspended иметь production suspend/resume actions?

**Статус:** `APPROVED` — production server-side Suspend/Resume для `execution_status` обязательны.

Schema содержит status, но действия не найдены; прямое редактирование запрещено (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_project/ferum_service_project.json#project_status`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_project/ferum_service_project.py:L184-L210`).

**Решение:** Suspend из разрешённого non-terminal state сохраняет reason, actor, timestamp/effective date, optional evidence, `suspended_from_status` и audit. Resume возвращает в допустимый предыдущий `Launching` либо `Active`; `Completed`/`Stopped` обычным Resume не возобновляются, legal status автоматически не меняется. Direct field edit в обход FSM запрещён.

### OQ-CA-021. Является ли edition_validation_report_v6_2_21 официальным validation report?

**Статус:** `APPROVED — NO` — текущий файл candidate/historical artifact, не authoritative validation PASS.

Файл находится в корне workspace, а ожидаемого `docs/spec/*_validation_report.md` нет (`Вспомогательные/Claude ferum_custom/edition_validation_report_v6_2_21.md:L11-L22`).

**Решение:** official report требует specification version/hash, validation date, CODE baseline commit, scope, verdict, exclusions, report hash, canonical location и approval. Существующий файл можно promote после проверки content/provenance; до promotion authoritative PASS запрещён.

### OQ-CA-022. Какие Codex-only request/evidence fields были отменены намеренно?

**Статус:** `APPROVED` — отсутствие поля в Claude не доказывает намеренную отмену.

Codex содержит `customer_approval_evidence`, successor/remaining и SLA flags, которых нет в Claude (`Вспомогательные/Codex ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_request/ferum_service_request.json#customer_approval_evidence`).

**Решение:** Codex-only fields остаются implementation divergence до field-level TARGET review. Для каждого требуется traceable `KEEP`, `REPLACE`, `DERIVE`, `MOVE TO GENERIC TARGET ENTITY/EVIDENCE` либо `DROP`; намеренное удаление допустимо только с decision/provenance evidence. Это engineering task, не owner blocker.

**Engineering disposition v0.16.0 — 2026-08-18:** field-level review выполнен без silent drop; решения и незакрытые implementation rows зафиксированы в [implementation/CA-15/field_disposition_v0_16_0.md](implementation/CA-15/field_disposition_v0_16_0.md). Review не является migration/cutover evidence.

### OQ-CA-023. Запускается ли Import Batch в runtime?

**Статус:** `APPROVED — NOT IN FIRST RELEASE / MG-CA-023 N/A FOR RELEASE`.

Model/FSM есть, orchestrator/API не найден (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_import_batch/ferum_import_batch.py:L87-L206`).

**Решение release package:** Import Batch скрывается из Workspace/menu, не получает user permissions и active API/entrypoint/job, остаётся disabled и не заявляется capability первого выпуска. Negative access evidence закрывает release gate; включение в будущем требует нового решения и повторного открытия MG-CA-023.

## Manual evidence и configuration gates после approval

| Gate | Требуемое доказательство | Блокирует |
| --- | --- | --- |
| `MG-CA-001` | signed inventory: real business records `0`; полный контрольный backup; N/A act | retirement legacy environment; business migration не входит |
| `MG-CA-013` | `CODE/CONFIG PASS`; site assignment и Operations UAT OPEN — [calendar evidence](implementation/CA-09/runtime_evidence_v0_18_0_2026-08-19.md), [delivery evidence](implementation/CA-09/runtime_evidence_v0_19_0_2026-08-19.md) | production activation scheduler/SLA delivery и FR-08 |
| `MG-CA-015` | FR-05 human sign-off подтверждён; FR-06 v0.20.0 CODE/final-tree STATIC `212/212 PASS`/exact-source Bench `179/179 OK`; latest immutable published PR head `51d50aa8e079479513302b87fc6794e48b3a42ce` has hosted `static-quality` PASS; browser/RBAC/private-file/scanner/HR-DPO-Security UAT и отдельное production-PII permission OPEN | production Worker/Credential data и release-qualified PERSONNEL READY |
| `MG-CA-016` | tag/remote SHA `7145d87`, exact versions, installed apps, schema/config/permissions/fixture manifest и hashes | официальный completion baseline и release reproducibility |
| `MG-CA-023` | disabled feature/menu/permission/API/job и negative access test | N/A for first release; future enablement reopens gate |

Эти gates не являются новыми архитектурными вопросами и не отменяют утверждённые решения. Их нельзя помечать PASS на основании настоящего approval.

## Остаточный порядок закрытия

1. MG-CA-016 — tag/manifest утверждённого baseline `7145d87`.
2. MG-CA-001 — signed zero-record inventory, backup и N/A act.
3. MG-CA-013 — site assignment и Operations/browser/performance qualification поверх versioned calendar PASS.
4. MG-CA-015 — legal/privacy evidence до production Worker/Credential/Personnel Ready.
5. MG-CA-023 — disabled/negative evidence для first release.
6. Выполнить оставшуюся CODE/UAT/release последовательность из [10_remaining_questions_and_actions.md](10_remaining_questions_and_actions.md).
