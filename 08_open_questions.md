# 08. Реестр утверждённых решений и открытых вопросов

**Цель документа:** зафиксировать owner decisions, оставшиеся UNKNOWN/BLOCKING и manual evidence gates без молчаливого проектного решения.

**Дата анализа:** 2026-08-17. **Дата owner approval:** 2026-08-18.

**Источник истины:** выявленные противоречия TARGET/SPEC/CODE, расхождения Claude/Codex и последовательные owner decisions заказчика от 2026-08-18, включая отдельные утверждения OQ-CA-003 и OQ-CA-016…023.

**Как проверить:** все 23 OQ должны иметь утверждённое решение; отсутствие runtime/manual evidence отражается не возвратом OQ в UNKNOWN, а отдельным применимым `MG-CA-*` gate. Утверждение архитектуры не подменяет runtime, legal/privacy, migration или configuration evidence. Сверить решения с [05_target_model.md](05_target_model.md), [06_roadmap.md](06_roadmap.md) и [07_traceability.csv](07_traceability.csv).

## Сводка статусов

| Статус | Количество | Идентификаторы |
| --- | ---: | --- |
| `APPROVED` | 23 | OQ-CA-001–023 |
| `OPEN / BLOCKING` | 0 | — |
| `OPEN / UNKNOWN` | 0 | — |

Утверждение не меняет `SPEC/CODE` coverage и не означает реализацию. Оно снимает архитектурную неопределённость только в пределах текста каждой рекомендации.

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

**Статус:** `APPROVED` — архитектура Company timezone + Project/Contract Holiday List override и immutable calculation snapshot; точные production values остаются MG-CA-013.

**Блокирует:** deadline/offset/SLA/escalation.

TARGET различает Calendar/Business Days и относительные сроки, но не определяет приоритет календарей и timezone (`Structure of the contract accounting system.md:L1196-L1251`; `Structure of the contract accounting system.md:L2080-L2104`).

**Варианты:** Company Holiday List/timezone; project override; contract-specific immutable calendar snapshot.

**Рекомендация:** Company timezone + Project/Contract Holiday List override, с snapshot правила и calendar revision на момент расчёта; ручной пересчёт только с audit reason.

Архитектурный приоритет утверждён. Конкретные Company timezone, Holiday List, переносы и cut-off time должны быть зафиксированы configuration evidence MG-CA-013 до запуска deadline engine.

## Подрядчики и персонал

### OQ-CA-014. Contractor Assignment включает pricing или только responsibility?

**Статус:** `APPROVED` — Assignment без pricing SSOT; pricing в terms/settlement.

**Блокирует:** схему assignment/settlement и MVP scope.

Owner decision отделяет assignment от pricing (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/plan/owner_decisions_2026-08-17_target_structure.md:L166-L176`).

**Рекомендация:** Assignment отвечает кто/где/что/когда; pricing — отдельные terms/settlement rows.

### OQ-CA-015. Где хранится worker identity и credentials подрядчика?

**Статус:** `APPROVED` — Employee для staff, protected Contractor Worker для внешних исполнителей; production PII остаётся закрыт до MG-CA-015.

**Блокирует:** production-схему `Ferum Contractor Worker`/`Ferum Personnel Credential`, загрузку персональных данных и включение PERSONNEL READY gate. До решения допустим только schema/privacy spike без production data.

TARGET требует Required Qualification → Worker Credential и gate готовности (`Structure of the contract accounting system.md:L1483-L1533`).

**Варианты:** Employee для всех; Contact/Party worker для подрядчиков; отдельный protected Worker master.

**Рекомендация:** standard Employee только для staff; отдельный минимальный protected Contractor Worker, связанный с Supplier/Contact, для внешних исполнителей; `holder_type + holder` разрешает ровно Employee **или** Contractor Worker; credentials и Project Document доступны по least privilege/retention policy. Паспортные реквизиты включаются только после явного подтверждения правового основания, consent, retention и permission/export policy.

Identity topology утверждена. Правовое основание, consent, retention/access/export policy и перечень допустимых паспортных полей должны быть зафиксированы evidence MG-CA-015 до production data.

## Текущий W2 snapshot

### OQ-CA-016. Какой CODE snapshot официально считать AS-IS baseline?

**Статус:** `APPROVED` — процедура freeze утверждена; фактический commit/diff/schema evidence остаётся MG-CA-016.

**Блокирует:** воспроизводимость discovery и roadmap patches.

Claude `w2-objects-core` имеет pre-existing dirty changes; Codex clean, но старше. W2-V02 для generated key остаётся человеческим gate (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/patches/v0_2/add_unique_key_generated_visit.py:L20-L24`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/plan/09_task_breakdown.md:L480-L515`).

**Рекомендация:** сохранить commit + patch/diff hash и повторить inventory/matrix после W2 merge.

**Уточнение owner decision:** официальный CODE AS-IS baseline — первый clean post-W2 commit со всеми принятыми W2-изменениями до TARGET implementation. Claude dirty tree и более старый Codex snapshot baseline не являются. MG-CA-016 должен доказать SHA, clean tree, diff hash, versions, patches, schema/DocType, Custom Field, Workflow, roles/permissions, Scheduled Job Type и применимые DB/manual gates, включая W2-V02.

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

**Статус:** `APPROVED / RUNTIME NOT EVIDENCED` — capability inactive/not production-proven до MG-CA-023.

Model/FSM есть, orchestrator/API не найден (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_import_batch/ferum_import_batch.py:L87-L206`).

**Решение:** model/FSM не является runtime evidence. Требуется поддерживаемый entrypoint/orchestrator/API/job и успешный E2E; до этого Import Batch не учитывается как реализованная capability или release evidence. При отсутствии entrypoint это incomplete/dead implementation, дальнейшая реализация или удаление требует отдельного target/owner решения.

## Manual evidence и configuration gates после approval

| Gate | Требуемое доказательство | Блокирует |
| --- | --- | --- |
| `MG-CA-001` | disposition каждой legacy N:M/ambiguous Contract↔Service Project строки и подписанный exception report | cutover/retirement legacy Contract |
| `MG-CA-013` | Company timezone, Holiday List priority/override, cut-off, переносы и versioned calendar snapshot fixture | deadline/SLA/escalation engine |
| `MG-CA-015` | legal/privacy approval: основание ПДн, consent, retention, roles/permlevel, export/delete policy и перечень protected fields | production Worker/Credential data и PERSONNEL READY |
| `MG-CA-016` | commit, dirty diff hash, schema snapshot, inventory и повторная matrix verification после W2 merge | официальный AS-IS baseline и migration rehearsal |
| `MG-CA-023` | поддерживаемый runtime entrypoint и E2E `create→start→process→success/failure→retry/rollback/audit` | production/runtime claim для Ferum Import Batch |

Эти gates не являются новыми архитектурными вопросами и не отменяют утверждённые решения. Их нельзя помечать PASS на основании настоящего approval.

## Остаточный порядок закрытия

1. MG-CA-016 — выполнить фактический baseline freeze до разработки и миграционных patches.
2. MG-CA-001 — разобрать N:M exceptions до cutover, если legacy records всё же сохраняются вопреки owner decision о reset/recreate; иначе документированно снять gate как неприменимый.
3. MG-CA-013 и MG-CA-015 — закрыть configuration/legal/privacy evidence перед соответствующими production features.
4. MG-CA-023 — доказать production Import Batch flow либо оставить capability inactive/not production-proven.
5. Выполнить field-level TARGET reconciliation Codex-only fields по OQ-CA-022; это engineering task, не новый owner blocker.
