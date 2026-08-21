# 06. Roadmap внедрения системы учёта договоров

**Цель документа:** управлять завершением первого production-выпуска `contract_accounting`: сохранить техническую декомпозицию `CA-00…CA-15`, но вести оставшуюся работу от утверждённых release decisions к одному проверяемому RC, production launch и post-release completion.

**Дата исходного анализа:** 2026-08-17. **Release decisions синхронизированы:** 2026-08-19. **Текущие qualification evidence синхронизированы:** 2026-08-20.

**Источник истины:** release boundary и operating policies — [Release Decisions v1](11_release_decisions_v1.md); последовательность закрытия — [10_remaining_questions_and_actions.md](10_remaining_questions_and_actions.md); TARGET — `Structure of the contract accounting system.md`; требования и их назначение инкрементам — [04_coverage_matrix.csv](04_coverage_matrix.csv) и [07_traceability.csv](07_traceability.csv); discovery AS-IS — [03_asis_model.md](03_asis_model.md); прежние owner decisions и история manual gates — [08_open_questions.md](08_open_questions.md).

**Как проверить:** импортировать [07_traceability.csv](07_traceability.csv), сгруппировать строки по `increment` и сопоставить диапазоны ниже; для каждого инкремента выполнить критерии и сохранить машинные/ручные доказательства; утверждённое решение не считать реализацией, а MG-CA gate — PASS без указанного evidence. Итоговую проверку отразить в [09_verification_report.md](09_verification_report.md).

## 1. Текущий статус и стратегия завершения первого выпуска

`contract_accounting` утверждён как business replacement и technical standalone; новый production не устанавливает `ferum_custom` и не переносит его business data. Архитектурная граница зафиксирована в [ADR-CA-0002](implementation/CA-00/ADR-CA-0002-business-replacement-technical-standalone.md).

Утверждённый completion baseline — commit `7145d87`, version `0.16.2` от 2026-08-18. Текущий `v0.20.0` остаётся local review candidate и не заменяет baseline или RC. Local/remote annotated tag, source/schema manifest и clean `136/136` standalone evidence созданы; baseline-exact live inventory и restore остаются OPEN.

### 1.1. Status overview

| Область | Состояние на 2026-08-20 | Вывод |
| --- | --- | --- |
| Decisions | 17/17 release decisions `APPROVED` | owner-question discovery завершён |
| `CA-01…CA-07` | core code bench-verified | release/UAT/legal/performance gates не закрыты |
| `CA-08…CA-15` | `PARTIAL` | обязательная product delta остаётся |
| `CA-00` completion baseline | partial evidence PASS | local+remote tag/manifest/schema/standalone PASS; live inventory/restore OPEN |
| Legacy migration | technical inventory/backup PASS; `MG-CA-001 N/A` по решению | 0 real records confirmed by `DP-02`; formal Data Owner signature + off-host retention remain OPEN |
| Release Scope v1 | planning/evidence gate PASS | 557/557 rows; 554 mandatory, из них 280 Implemented / 274 Partial / 0 Absent |
| Quality/CI profile | current published review-candidate automation PASS; RC/manual qualification incomplete | historical `161/161`/Bench `89/89`, earlier dirty-tree Bench `127/127`, and hosted run `32261790230` are retained as provenance; current published draft-PR head `2e27643` has hosted `static-quality` PASS via run `32470646882`, while the same final-tree review candidate has static `212/212 PASS`, targeted Inspection `5/5 PASS`, exact-source Bench gate `179/179 OK` on isolated `ca01.localhost`, pinned repo-local browser runtime contract (`playwright-core 1.62.1`) with generated runtime forced into `.gitignore`, and verified `main`/`v*` GitHub protection; browser/human UAT, restore, performance and production gates remain OPEN |
| `FR-02` master-data boundary | core CODE/schema/runtime PASS; manual gates OPEN | Party Identity + Address/Contact/Warehouse + Project/Task/Issue/Asset policy; Workflow/Communication, owner/browser/race/load acceptance OPEN |
| `FR-03` production calendar | engineering/schema/runtime PASS; manual gates OPEN | official 2026 fixture, Company/Contract precedence, signature/customer-response sources, `83/83`; Operations/browser/performance OPEN |
| `FR-04` notification delivery | engineering/local E2E PASS; manual transport gates OPEN | DP-06 thresholds, calendar-timezone digest, in-app/Email Queue, idempotency, retry/dead-letter; SMTP receipt/worker/RBAC/load OPEN |
| `FR-05` contractor privacy/legal | decisions FILLED; ALL NAMED SIGN-OFFS CONFIRMED | owners, field registry, purpose/basis/retention, RBAC/export/private-file/break-glass утверждены; подтверждения Legal/Privacy/DPO, Security и Data Owner/HR аттестованы Product Owner без предоставленных номеров актов; FR-06 implementation/tests и production-PII permission остаются до `MG-CA-015 PASS` |
| `FR-06` protected Worker/Credential/readiness | automated remediation, full-stack synthetic Engineer ACL and full disposable Bench verified; release `NOT READY` | current final-tree static `212/212 PASS`; targeted Inspection `5/5 PASS`; latest scoped privacy runtime is policy `9/9`, alias/retention `24/24`, File boundaries `3/3`, residue `0`; current exact-source Bench gate `179/179 OK`; own/foreign Engineer symmetric Form ACL, own-only List, foreign direct `403`, and full-stack `socket.io` polling `200` PASS on pinned repo-local browser runtime (`playwright-core 1.62.1`); latest post-browser exact reset `79 → 0` with stable Comment/Deleted Document/Version audit hashes; Workspace visibility remains an owner-review blocker, human UAT has not run |
| Import Batch | out of first release | disabled/negative evidence обязательно |
| Release / RC status | `NOT READY FOR PRODUCTION / RC NOT READY` | automated suites and structural demo verification do not replace authenticated browser/human UAT, restore/rollback, performance/race/load, clean Staging, production approval or deployment evidence |

### 1.2. Roadmap view

| Горизонт | Цель | Основные результаты | Gate |
| --- | --- | --- | --- |
| **Now — controlled UAT qualification** | завершить проверку воспроизводимого synthetic-контура без повышения release status | Product Owner UI review, full-stack synthetic browser rerun, фиксация дефектов и повторная проверка | Workspace/UI review remains `OPEN BLOCKER`; full-stack synthetic evidence is fixed only in a narrow automated scope; human UAT is not allowed until Product Owner approval |
| **Next — product closure** | закрыть обязательный release scope и ручные gates | human role UAT, scanner/SMTP/scheduler checks, Evidence Policy, External Dependency, documents, materials/tools/reports | обязательная capability matrix подтверждена не только CODE, но и применимыми UAT/evidence gates |
| **Qualification** | доказать production fitness | полная RBAC, clean Staging, load/race, UAT, restore/rollback/cutover | все technical/manual gates PASS на одном RC |
| **Release** | ввести систему в эксплуатацию | immutable RC, production smoke/health, monitoring/backup, 10-day hypercare | production и post-release sign-off |

Точные календарные даты не назначаются до появления owner/capacity plan; roadmap фиксирует зависимости и gates, а не обещает неподтверждённые сроки.

Порядок исполнения строится по следующим правилам:

- `contract_accounting` разворачивается clean; coexistence/shared schema с `ferum_custom` запрещены;
- standard `Customer`, `Supplier`, `Company`, accounting documents, `GL Entry` и infrastructure DocType остаются ERPNext SSOT;
- legacy business migration и Import Batch не входят в first release, но их N/A/disabled state должен быть доказан;
- новый product CODE снимает fail-closed gate только после соответствующего configuration/legal decision;
- автоматические тесты не заменяют UAT, legal/privacy, finance, restore, security или deployment evidence.

## 2. Сводный план инкрементов

Таблица ниже сохраняет архитектурную декомпозицию 557 требований и историю реализации. Это component map, а не текущая последовательность выпуска; актуальный порядок работ задан [отдельным планом](10_remaining_questions_and_actions.md).

| Инкремент | Название и результат | Закрываемые `req_id` | Зависимости | MVP | Оценка |
| --- | --- | --- | --- | --- | --- |
| `CA-00` | Baseline, границы ERPNext и миграционная готовность | `TCA-A-17-01…TCA-A-17-21` | — | Да | M |
| `CA-01` | Service Project как Contract root, объекты и двойные статусы | `TCA-A-01-01…TCA-A-01-25`; `TCA-A-02-01…TCA-A-02-13`; `TCA-A-03-01…TCA-A-03-12`; `TCA-A-13-01…TCA-A-13-06`; `TCA-A-18-01…02`; `TCA-A-18-04…05` | `CA-00`; утверждённый OQ-CA-003; MG-CA-016 для cutover | Да | XL |
| `CA-02` | Contract Requirement/Obligation для ответа «что, где, когда» | `TCA-A-04-01…TCA-A-04-08`; `TCA-A-18-03` | `CA-01` | Да | L |
| `CA-03` | Сквозной plan→fact и обратная трассировка | `TCA-A-05-01…TCA-A-05-09`; `TCA-A-06-01…TCA-A-06-16` | `CA-02` | Да | XL |
| `CA-04` | Самостоятельный Finding с категорией Defect | `TCA-A-07-01…TCA-A-07-08`; `TCA-A-18-06…TCA-A-18-10` | `CA-00`; интеграция с `CA-03` | Да | M |
| `CA-05` | Project Document и раздельные статусы копии/оригинала | `TCA-A-08-01…TCA-A-08-13`; `TCA-A-18-11`; `TCA-B-25-01…TCA-B-25-04` | `CA-01` | Да | L |
| `CA-06` | Исполнение→Billing Basis→акт/УПД→Sales Invoice | `TCA-A-09-01…TCA-A-09-08`; `TCA-A-10-01…TCA-A-10-03`; `TCA-A-18-15…TCA-A-18-16` | `CA-03`, `CA-05` | Да | XL |
| `CA-07` | Оплата, ДЗ, затраты и маржа из ERPNext SSOT | `TCA-A-11-01…TCA-A-11-15`; `TCA-A-18-14`; `TCA-A-18-17` | `CA-06` | Да | M |
| `CA-08` | Contractor Assignment и готовность исполнителей | `TCA-A-12-01…TCA-A-12-10`; `TCA-A-18-12…TCA-A-18-13` | `CA-01`, `CA-02`; MG-CA-015 для production Worker/Credential/readiness | После MVP | L |
| `CA-09` | Derived timeline контрольных сроков | `TCA-A-14-01…TCA-A-14-13` | `CA-01`, `CA-03`, `CA-05`, `CA-06`; MG-CA-013 до production calculation | После MVP | M |
| `CA-10` | Contract 360° и центр исключений | `TCA-A-15-01…TCA-A-15-08`; `TCA-A-16-01…TCA-A-16-19` | `CA-07`, `CA-09` | После MVP | L |
| `CA-11` | BPM Core: Requirement→Template→Process→Step→Evidence→Gate | `TCA-B-01…12-*`; `TCA-B-20-*`; `TCA-B-24-*`; `TCA-B-26…30-*`; `TCA-B-33…35-*`; `TCA-B-37…39-*` (169 точных ID в CSV) | `CA-02`, `CA-05` | После MVP | XL |
| `CA-12` | Семистадийный запуск, персонал и Inspection | `TCA-B-13…19-*`; `TCA-B-22…23-*` (84 точных ID в CSV) | `CA-04`, `CA-05`, `CA-08`, `CA-11` | После MVP | XL |
| `CA-13` | Первое закрытие периода и Billing Cycle Gate | `TCA-B-21-01…TCA-B-21-11` | `CA-06`, `CA-11`, `CA-12` | После MVP | L |
| `CA-14` | «Мои действия» и «Запуск проектов» | `TCA-B-31-01…TCA-B-31-05`; `TCA-B-32-01…TCA-B-32-09` | `CA-10`, `CA-11`, `CA-12` | После MVP | L |
| `CA-15` | Интеграционное укрепление и end-to-end trace | `TCA-A-19-01…TCA-A-19-23`; `TCA-A-20-01…TCA-A-20-14`; `TCA-B-36-01…TCA-B-36-14` | `CA-01…CA-14`; DP-13 disabled/negative evidence для Import Batch | Финальный gate | XL |

Диапазоны воспроизводят назначение всех 557 строк в [07_traceability.csv](07_traceability.csv); для длинных BPM-групп таблица использует wildcard по полностью перечисленным разделам, а точный перечень всех `req_id` хранится в CSV. Изменение состава инкрементов требует синхронного изменения этого CSV. На текущем дереве `CA-01…CA-07` имеют bench-verified core, `CA-08…CA-15` остаются partial, а `CA-00` требует completion-baseline evidence.

## 3. Граф зависимостей

```mermaid
flowchart LR
  CA00["CA-00 Baseline"] --> CA01["CA-01 Contract root"]
  CA00 --> CA04["CA-04 Finding(category=Defect)"]
  CA01 --> CA02["CA-02 Obligations"]
  CA01 --> CA05["CA-05 Project Document"]
  CA02 --> CA03["CA-03 Plan to Fact"]
  CA03 --> CA06["CA-06 Billing Basis"]
  CA05 --> CA06
  CA06 --> CA07["CA-07 Finance"]
  CA01 --> CA08["CA-08 Contractor Assignment"]
  CA02 --> CA08
  CA01 --> CA09["CA-09 Deadline Timeline"]
  CA03 --> CA09
  CA05 --> CA09
  CA06 --> CA09
  CA07 --> CA10["CA-10 Contract 360"]
  CA09 --> CA10
  CA02 --> CA11["CA-11 BPM Core"]
  CA05 --> CA11
  CA04 --> CA12["CA-12 Project Launch"]
  CA05 --> CA12
  CA08 --> CA12
  CA11 --> CA12
  CA06 --> CA13["CA-13 Billing Cycle"]
  CA11 --> CA13
  CA12 --> CA13
  CA10 --> CA14["CA-14 Workspaces"]
  CA11 --> CA14
  CA12 --> CA14
  CA01 --> CA15["CA-15 E2E Integration"]
  CA04 --> CA15
  CA07 --> CA15
  CA08 --> CA15
  CA09 --> CA15
  CA13 --> CA15
  CA14 --> CA15
```

`CA-04` и минимальное ядро `CA-05` допускают параллельную реализацию после baseline; технический порядок «Finding(category=Defect) → Project Document → BPM» не меняет зависимость MVP от Service Project/Obligation/plan-fact (`Structure of the contract accounting system.md:L350-L397`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/plan/owner_decisions_2026-08-17_target_structure.md:L224-L242`).

## 4. Технический MVP-контур (не граница первого production-выпуска)

### 4.1. Состав MVP

Исторический technical MVP `CA-00…CA-07` даёт data spine «что/когда/где» и цепочку ниже. Он не является достаточным release scope: утверждённый первый production-выпуск дополнительно включает обязательные capabilities `CA-08…CA-15` и `DP-03`.

```text
Contract → Contract Obligation → Schedule/Planned Visit → Accepted Fact
→ immutable Billing Basis → Act/UPD + Sales Invoice → Payment Entry
→ Project Finance Summary
```

В MVP входят:

- единый `Ferum Service Project` как договорный root с независимыми `legal_status` и `execution_status`;

- объекты и системы договора;

- нормализованное обязательство с работой, местом, периодичностью, окном срока и effective dates;

- генерация планового события и его фактическое закрытие с evidence;

- `Ferum Finding(category=Defect)` для результата «обнаружено, но ещё не заявка и не выполненная работа»;

- единый реестр документов с раздельными статусами цифровой копии и бумажного оригинала;

- immutable snapshot оснований акта/УПД;

- стандартные Sales Invoice/Payment Entry/GL как бухгалтерский SSOT и кастомный Finance Summary как rebuildable read-model.

Полный BPM-конструктор, семистадийный launch, N:M contractor assignment, derived deadline center и финальные workspaces не являются условием первого MVP, но не должны блокироваться его моделью данных.

### 4.2. Сквозной критерий MVP

На тестовом договоре с двумя объектами и двумя системами система должна:

1. Показать обязательство «какая работа, на каком объекте/системе, в каком периоде и до какой даты».

2. Сгенерировать ровно одно плановое событие периода и сохранить обратную ссылку на обязательство.

3. Зафиксировать фактический визит, исполнителя, дату, checklist/evidence и решение приёмки.

4. Отдельно зарегистрировать обнаруженный `Ferum Finding(category=Defect)` и, при необходимости, создать связанную Service Request без потери исходного факта.

5. Подобрать только принятые и ещё не актированные работы, зафиксировать их в неизменяемом Billing Basis и сформировать акт/УПД.

6. Связать closing document со стандартным submitted Sales Invoice, затем со submitted Payment Entry.

7. Показать в Finance Summary начислено, оплачено, outstanding/overdue AR, затраты и маржу без прямой записи кастомного кода в GL.

8. Пройти от любой точки цепочки назад до договора/обязательства и вперёд до оплаты и маржи; разрыв ссылки является дефектом приёмки.

## 5. Инкременты

### CA-00. Baseline, ERPNext boundary и миграционная готовность

**Цель:** превратить утверждённый completion baseline в воспроизводимую исходную точку и зафиксировать standalone/ERPNext границы до qualification и release.

**AS-IS:** прежний W2/`ferum_custom` baseline сохраняется только как discovery provenance. Для завершения первого выпуска утверждён новый code-bearing baseline репозитория `contract-accounting`: `7145d87` / `0.16.2`; текущее `0.16.3` является отдельной дельтой.

**Owner decision:** `DP-04` утверждает точный baseline и требуемый tag `completion-baseline-v0.16.2`. Решение не создаёт evidence: SHA, tag, remote sync, clean-tree proof, versions, installed apps, schema/configuration и hashes должны войти в baseline manifest.

**Состав:**

- annotated tag утверждённого commit `7145d87` без переназначения baseline;

- inventory installed apps, live schema, patches, Workflow, Custom Field, roles/permissions и Scheduled Job Type без чтения секретов;

- ADR по границе ERPNext/custom и Party Identity ownership;

- sanitized configuration/dataset manifest, hashes, rollback/restore rehearsal и обязательный формат release evidence;

- фиксация ручных gates: DB, UAT, legal и permission review.

**Миграция:** legacy business data не переносятся. Production создаётся clean. `MG-CA-001=N/A` требует signed zero-record inventory и контрольный backup до retirement legacy environment.

**Критерии приёмки:**

- baseline commit/tag, app/dependency versions, installed apps, schema/configuration и patches зафиксированы в manifest;

- `0.16.3` и последующие изменения представлены как traceable post-baseline commits;

- documented boundary подтверждает отсутствие кастомной записи в GL и повторного master/accounting SSOT;

- restore/rollback rehearsal восстанавливает clean environment и approved configuration; legacy test records не являются release data;

- все незакрытые ручные gates имеют owner и статус, а не ложный PASS.

**Оценка:** M.

### CA-01. Service Project как Contract root, объекты и двойные статусы

**Цель:** привести модель к TARGET: один `Ferum Service Project` является одним исполняемым договором, хранит юридические условия и оба независимых legal/execution lifecycle.

**AS-IS:** принят двухфазный переход через `Ferum Contract` и `Ferum Project Contract Link`; договорные поля проекта пока остаются зеркалами, а перенос SSOT отложен во вторую фазу (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/adr/ADR-0003-service-project-vs-legal-contract.md:L50-L69`). Amendment/Execution Stage/Security ещё project-centric, например Amendment хранит `service_project` (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract_amendment/ferum_contract_amendment.json#service_project`).

**OQ-CA-003 — `APPROVED`, 2026-08-18:** legal FSM = Draft, On Approval, Approved, Signing, Signed, In Force, Cancelled, Terminated, Expired; execution FSM = Not Started, Launching, Active, Suspended, Completed, Stopped. Cancelled/Terminated/Expired и Completed/Stopped terminal; `Active` разрешён только при In Force; `Suspended→Completed` запрещён. OQ-CA-020 уточняет Resume: возврат только в сохранённый `suspended_from_status` Launching/Active. `Closed`/`Archived` вынесены из FSM. Полные matrices/audit rules зафиксированы в [05_target_model.md](05_target_model.md#4-двойная-статусная-модель-договора) и [08_open_questions.md](08_open_questions.md#oq-ca-003-какова-целевая-dual-status-fsm-договора). Legacy status migration не требуется.

**Статус реализации, 2026-08-18:** CA-01 CODE/schema v0.2.0 закрыт: contract root, dual FSM, typed audit, Amendment/Stage/Security/Financial Plan, Service Project→Project Object→Service Object→Object System, fail-closed integrity и controlled schema rollback/reinstall подтверждены на отдельном ERPNext v15 site: [runtime evidence](implementation/CA-01/runtime_evidence_v0_2_0_2026-08-18.md). Full backup restore, downstream Project Document/Scope/Billing/AR и ручные UAT/legal/finance gates остаются открыты и не маскируются статусом CA-01.

**Состав:**

- реализовать утверждённую OQ-CA-001/002 целевую топологию: один `Ferum Service Project` является Contract root, а ссылки Amendment, Stage, Security и других зависимых сущностей направлены на него; перенос существующих тестовых Contract↔Project записей не требуется;

- добавить `legal_status` и `execution_status` в `Ferum Service Project` по утверждённому OQ-CA-003 с server-side transition matrix, терминальными состояниями и взаимными ограничениями lifecycle;

- реализовать юридические поля и перевести schema-связи Amendment, Stage, Security и financial plan на `Ferum Service Project`;

- сохранить Service Project→Object→Object System navigation и проверить целостность новых прямых/reverse links без retention тестовых legacy records;

- ввести audit events для каждого нового статусного перехода, включая обязательные reason/evidence для досрочного отказа или прекращения договора.

- реализовать server-side Suspend/Resume исполнения по OQ-CA-020: хранить `suspended_from_status`, reason/actor/effective date/evidence; Resume возвращает только в прежний Launching/Active, terminal execution не возобновляется обычной командой.

**Миграция/patches:** тестовые legacy business records, исторический `Contract.status` и тестовая audit/status history не переносятся. TARGET fields, связи и конфигурация вводятся как clean schema; тестовые записи сбрасываются либо создаются заново. Для архитектурного cutover остаются обязательными schema/link reconciliation, проверка ссылочной целостности и управляемое переключение новой бизнес-логики; patch для mapping/backfill/dual-write старой status model не создаётся.

**Критерии приёмки:**

- каждый заново созданный тестовый Service Project имеет ровно один однозначный набор юридических условий и не зависит от `Ferum Contract` как второго SSOT;

- все допустимые legal/execution переходы проходят, все недопустимые блокируются сервером;

- direct edit `execution_status` не обходит FSM; Suspend/Resume имеет positive/negative tests для Launching и Active и не изменяет legal status;

- Cancelled/Terminated вместе с требуемым execution transition сохраняются атомарно; при ошибке обе оси остаются неизменными, а связанные audit events имеют общий correlation id;

- Cancelled/Terminated/Expired запрещают новое исполнение, но не скрывают незакрытую ДЗ, документы и историю исполнения; несостоявшийся договор переходит из Draft/On Approval/Approved/Signing только в Cancelled с обязательными reason/date/actor/comment/evidence по policy, а `Draft→Terminated` запрещён;

- Amendment меняет только effective-dated future/current state и сохраняет историю до/после;

- reset/recreate тестового набора не оставляет orphan links, а schema/configuration deployment и его controlled rollback повторяемы; обратного преобразования dual statuses в старый `Contract.status` нет.

**Оценка:** XL.

### CA-02. Contract Requirement и Contract Obligation

**Цель:** создать явный слой между договором и графиком, отвечающий на «что сделать, где, с какой периодичностью и когда».

**Статус реализации, 2026-08-18:** CA-02 core CODE/schema v0.3.0 реализован и подтверждён на отдельном ERPNext v15 site: Requirement assessment/routing, Contract Obligation, typed recurrence, effective-version/foreign-context guards, deterministic no-write preview, migrate и controlled schema reinstall — [runtime evidence](implementation/CA-02/runtime_evidence_v0_3_0_2026-08-18.md). Schedule/Visit writer для `TCA-A-04-07…08` теперь реализован следующим инкрементом CA-03 v0.4.0; SLA/Holiday timestamp engine (CA-09), Project Document Link (CA-05), one-time Process Step writer (CA-11) и legacy combined-app migration gate остаются открыты. Исторический точный статус v0.3.0 — [implementation traceability](implementation/CA-02/traceability_v0_3_0.md).

**AS-IS:** `Ferum Project Scope` содержит правило работ/периодичности, а генератор создаёт визиты из Scope/Schedule, но отдельного `Ferum Contract Obligation` нет (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_scope/ferum_project_scope.json#work_type`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/services/maintenance_visit_generation.py:L527-L638`; `contract-accounting/03_asis_model.md:L326-L328`). Requirement, одноразовый Process Step и повторяющийся Scope нормативно разделены (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/plan/owner_decisions_2026-08-17_target_structure.md:L74-L94`).

**Состав:**

- `Ferum Contract Requirement` с источником, цитатой/ссылкой, применимостью и решением маршрутизации;

- `Ferum Contract Obligation` с единым `service_project`, Project Object, Object System, work type, frequency/deadline rule, effective dates, criticality и source requirement;

- правила один requirement→одноразовый step либо recurring obligation без дублирования;

- reverse trace Service Project/Requirement/Obligation/Scope/Schedule.

**Миграция/patches:** построить draft obligations из активных effective-dated Scope только при однозначных Service Project/Object System/work type; legacy Contract используется лишь как read-only migration provenance, неоднозначные строки направляются на review. Уникальность active obligation защитить сервером и, после DB-пробы, условным ключом.

**Критерии приёмки:**

- каждое active recurring Scope имеет ровно одно применимое обязательство либо документированное исключение;

- обязательство однозначно отвечает на work/object/system/frequency/deadline/effective period;

- изменение существенных условий создаёт новую effective version, не переписывает прошлое;

- generation preview показывает будущие периоды без создания дублей;

- повторный migration/generation прогон идемпотентен.

**Оценка:** L.

### CA-03. Сквозной plan→fact

**Цель:** связать Obligation→Schedule/Planned Event→Maintenance Visit и Service Request с доказательствами и обратной трассировкой.

**Статус реализации, 2026-08-18:** CA-03 core CODE/schema v0.4.0 реализован и подтверждён на отдельном ERPNext v15 site: unique Obligation/period Schedule, idempotent Schedule+primary Visit generation, explicit cancelled replacement, planned/actual split, checklist/private File evidence, PM review/acceptance, immutable accepted fact, самостоятельный Service Request и reverse trace — [runtime evidence](implementation/CA-03/runtime_evidence_v0_4_0_2026-08-18.md). Act/Invoice/Payment chain (`TCA-A-05-06…08`) остаётся CA-06/07, Finding link — CA-04, assigned-contractor/portal scoping — CA-08; [implementation traceability](implementation/CA-03/traceability_v0_4_0.md) не подменяет эти OPEN gates.

**AS-IS:** генератор уже поддерживает period/frequency/Holiday List и idempotency по `contract/object_system/work_type/period_key`; Visit и Service Request имеют отдельные FSM и evidence/SLA gates (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/services/maintenance_visit_generation.py:L131-L168`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/services/maintenance_visit_generation.py:L527-L638`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_maintenance_visit/ferum_maintenance_visit.py:L111-L163`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_maintenance_visit/ferum_maintenance_visit.py:L442-L529`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_request/ferum_service_request.py:L312-L420`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_request/ferum_service_request.py:L450-L557`).

**Состав:**

- добавить обязательную provenance-связь планового исполнения с Obligation и period key;

- разделить planned date/window и actual start/finish;

- нормировать assignee/contractor, report, checklist, photo/evidence и acceptance;

- обеспечить reverse navigation от факта к плану, obligation, object/system и contract;

- сохранить внеплановую Service Request отдельным путём.

**Миграция/patches:** backfill obligation по существующему contract/object_system/work_type/effective period; неоднозначные визиты не связывать автоматически. Не нарушать `idx_generated_visit_uniq`; до cutover выполнить W2-V02 и duplicate rehearsal.

**Критерии приёмки:**

- одно обязательство генерирует ровно одно плановое событие на period key;

- cancelled generated visit не создаёт молча второй generated fact; повторное покрытие выполняется нормативным сценарием;

- Accepted visit невозможен без обязательных checklist/evidence/review;

- Service Request остаётся самостоятельным внеплановым фактом;

- end-to-end query возвращает plan/fact deviation и полный reverse trace.

**Оценка:** XL.

### CA-04. Finding с категорией Defect

**Цель:** отделить обнаруженное замечание от заявки и выполненной работы.

**AS-IS:** отдельного Finding/Defect нет; `Service Request.request_type` содержит лишь тип заявки (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_request/ferum_service_request.json#request_type`; `contract-accounting/03_asis_model.md:L326-L329`). По утверждённому OQ-CA-005 целевая модель использует самостоятельный `Ferum Finding` с `category=Observation/Defect/Nonconformity/Risk`, альтернативным source Visit/Inspection, object/system, severity, evidence, resolution и optional execution link на Service Request/утверждённый work-order adapter; отдельный Defect не вводится (`Structure of the contract accounting system.md:L350-L397`; [05_target_model.md](05_target_model.md#30-решение-findingdefect)).

**Состав:** Finding lifecycle, category/severity, detected context snapshot, photos/files, confirmation/resolution class, owner, due/closed dates и links to generated Service Request.

**Миграция/patches:** не преобразовывать существующие Service Request в Finding автоматически. Разрешён только candidate report по request type/text с ручным подтверждением категории Defect; provenance исходной записи обязательна.

**Критерии приёмки:**

- Finding создаётся из Visit/Inspection без автоматического создания заявки;

- создание связанной Service Request не меняет исходные данные Finding;

- close запрещён без resolution, evidence и обязательных дат;

- отчёт показывает open critical, overdue и без решения;

- permissions исключают доступ подрядчика к чужим проектам.

**Результат реализации v0.5.0 — 2026-08-18:** `CA-04 CORE CODE COMPLETE / BENCH VERIFIED`. Реализованы один physical `Ferum Finding` без Defect DocType, обязательная category, immutable Visit provenance/context snapshot, confirmation/resolution FSM, idempotent Service Request execution links, explicit request creation, derived exception report и `Ferum Photo Evidence` с review/hash стандартного File. Migrate и clean reinstall 21 DocType прошли; standalone suite `72/72`, полный Frappe suite до и после reinstall `24/24`. Inspection source остаётся fail-closed до CA-12; contractor role сейчас не получает доступа, а положительная own-assignment row-level модель остаётся CA-08; work-order adapter не разрешён. Legacy Service Request автоматически не преобразуются, candidate conversion не запускался из-за отсутствия legacy records на disposable site. Evidence: [implementation/CA-04/README.md](implementation/CA-04/README.md), [runtime evidence](implementation/CA-04/runtime_evidence_v0_5_0_2026-08-18.md), [traceability](implementation/CA-04/traceability_v0_5_0.md).

**Оценка:** M.

### CA-05. Project Document и оригиналы

**Цель:** дать единый реестр договорных/проектных документов и раздельный контроль цифровой копии и бумажного оригинала.

**AS-IS:** billing-файлы версионируются `Ferum Billing Artifact`, но универсального Project Document и `original_status`/`digital_copy_status` нет (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_billing_artifact/ferum_billing_artifact.json#artifact_type`; `contract-accounting/03_asis_model.md:L326-L330`). Project Document должен ссылаться на billing artifact, а не копировать его SSOT (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/plan/owner_decisions_2026-08-17_target_structure.md:L121-L134`).

**Состав:** Project Document, document type, Service Project/Object links, number/date/version/validity, source, files/related entity, `digital_copy_status`, `original_status`, shipment/tracking and status transition rules.

**Миграция/patches:** создать ссылки-представления для Billing Artifact и кандидаты из attached File. Не присваивать `Received/Archived` бумажному оригиналу без доказательства; неизвестные случаи — migration issue/manual review. Deduplication по source doctype/name/version/file hash.

**Критерии приёмки:**

- цифровая копия и оригинал изменяются независимо по серверной матрице;

- `Not Required` требует нормативного основания, а `Received/Archived` — evidence/stamp;

- один billing artifact не дублируется вторым физическим файлом;

- file access/lock предотвращает удаление accepted/signed/legal archive evidence;

- документ доступен из единого Service Project, Project Object и связанного процесса; legacy Contract остаётся только provenance до cutover.

**Оценка:** L.

### CA-06. Billing Basis, акт и счёт

**Цель:** доказуемо связать исполнение с актом/УПД и стандартным Sales Invoice.

**AS-IS:** Billing Output имеет только одиночный `basis_service_request`; Output/Artifact/Event уже реализуют lifecycle, versioning и immutable audit (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_billing_output/ferum_billing_output.json#basis_service_request`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_billing_output/ferum_billing_output.py:L162-L387`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_billing_artifact/ferum_billing_artifact.py:L98-L267`). Принята гибридная модель derived selection + immutable `Billing Basis Item[]` snapshot (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/plan/owner_decisions_2026-08-17_target_structure.md:L146-L164`).

**Состав:** derived candidate selector, Billing Basis child rows для Visit/Request/other accepted result и period key, immutable snapshot on issue, unbilled accepted work report, supersede/correction lifecycle, link to submitted Sales Invoice.

**Миграция/patches:** для Draft/Generated outputs basis можно восстановить и проверить. Для Issued/Signed — только однозначный backfill; конфликт уходит в legal review, существующий snapshot/артефакт не переписывается. При изменении print snapshot schema увеличить версию и сохранить совместимость старых snapshots.

**Критерии приёмки:**

- selector предлагает только accepted, применимые и ещё не включённые в active closing document результаты;

- Issued/Signed output имеет непустой immutable basis snapshot;

- один execution result не попадает в два активных closing documents;

- correction/supersede сохраняет историю старого и нового basis;

- отчёт «принято, но не актировано» сходится с basis rows;

- Sales Invoice и Payment Entry остаются стандартными ERPNext документами.

**Оценка:** XL.

### CA-07. Финансы, оплата и маржа

**Цель:** завершить MVP до оплаты и экономического результата без второй бухгалтерии.

**AS-IS:** `Ferum Project Finance Summary` уже является service-managed read-model на Sales/Purchase Invoice, Payment Entry и подтверждённых затратах; кастомный CODE не пишет прямые GL entries (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/services/project_finance_summary.py:L403-L701`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/hooks.py:L359-L403`).

**Состав:** добавить obligation/billing-cycle dimensions в read-model, выверить recognized/invoiced/paid/outstanding/overdue/cost/margin, reconciliation alerts и портфельные rollup по Company/Customer/manager поверх единого `Ferum Service Project`-договора.

**Миграция/patches:** полный rebuild, before/after comparison с submitted ERPNext documents, отдельный список расхождений; никаких корректирующих GL проводок миграционным patch.

**Критерии приёмки:**

- paid и outstanding сходятся со стандартными submitted Invoice/Payment Entry на контрольной выборке;

- opening balances учитываются по нормативу без двойного revenue;

- один Purchase Invoice не заявлен одновременно как material и contractor cost;

- портфельный rollup равен сумме Service Project с документированными правилами валюты и не создаёт второго Contract-root;

- rebuild повторяем и не изменяет бухгалтерские документы/GL.

**Результат реализации v0.8.0 — 2026-08-18:** `CA-07 CORE CODE COMPLETE / BENCH VERIFIED`. Реализованы service-managed `Ferum Project Finance Summary`, standard Sales/Purchase Invoice adapters, Payment Entry trace, opening-balance rule, guarded `Ferum Material Expense`/`Ferum Contractor Settlement`, exact PI classification, reconciliation и Company-currency portfolio rollup. Migrate и clean reinstall 31 DocType прошли; standalone suite `89/89`, полный Frappe suite до и после reinstall `41/41`. Положительный VAT tax-row сценарий и отдельная tool/rent аналитика остаются PARTIAL; legacy comparison, async worker/load/race, Finance UAT/sign-off и production deployment не выполнялись. Evidence: [implementation/CA-07/README.md](implementation/CA-07/README.md), [runtime evidence](implementation/CA-07/runtime_evidence_v0_8_0_2026-08-18.md), [traceability](implementation/CA-07/traceability_v0_8_0.md).

**Оценка:** M.

### CA-08. Contractor Assignment и готовность исполнителей

**Цель:** отделить операционное назначение подрядчика от цены и settlement.

**AS-IS:** contractor portal изолирует записи по Supplier/User Permission, но `Ferum Contractor Assignment` отсутствует; `Ferum Contractor Settlement` хранит только расчётную связь Supplier/Project/Scope (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/services/contractor_portal_isolation.py:L134-L268`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contractor_settlement/ferum_contractor_settlement.json#supplier`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contractor_settlement/ferum_contractor_settlement.json#project_scope`; `contract-accounting/03_asis_model.md:L326-L331`). Целевая размерность — Service Project×Object×System×Work Type×Period с отдельными коммерческими условиями (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/plan/owner_decisions_2026-08-17_target_structure.md:L166-L176`).

**Owner decision:** OQ-CA-015 утверждает Employee для staff, protected Contractor Worker для внешних исполнителей и holder allowlist/XOR.

**Входной gate:** MG-CA-015 должен предоставить правовое основание, consent, retention, protected-field allowlist и матрицу доступа/export/delete. До его закрытия допустим только schema/privacy spike без production Worker/Credential data и без включения PERSONNEL READY gate.

**Состав:** effective-dated Assignment; новый защищённый `Ferum Contractor Worker` и единый `Ferum Personnel Credential` с allowlist Employee/Contractor Worker; contractor/personnel links, scope/territory, responsibility, status и expiry; optional pricing/settlement reference без обязательной цены. Production protected fields включаются только после MG-CA-015 и не выдаются в supplier portal.

**Миграция/patches:** кандидаты из прямых contractor links на Visit/Request создаются только при непротиворечивом диапазоне; конфликтующие Supplier/period — manual review. Worker, квалификации и паспортные сведения не восстанавливать из свободного текста; внешнего работника создавать только из однозначного Supplier-scoped identifier, иначе оставлять migration candidate.

**Критерии приёмки:**

- на одну работу можно назначить разных подрядчиков по объекту/системе/периоду без overlap-конфликта;

- Assignment создаётся до согласования цены;

- недействующая квалификация блокирует readiness gate, но не стирает историческое назначение;

- один и тот же readiness gate одинаково проверяет Employee и Contractor Worker, а protected passport fields недоступны подрядчику и обычным проектным ролям;

- settlement и margin показывают assignment/commercial basis раздельно;

- portal permission tests доказывают Supplier isolation.

**Результат реализации v0.9.0 — 2026-08-18:** `CA-08 PARTIAL / ASSIGNMENT-COMMERCIAL CORE BENCH VERIFIED`. Реализованы effective-dated Assignment, Internal/Contractor XOR schema, object/system/work-type scope, overlap guard, отдельные Commercial Terms с derived margin, связи Settlement/Material и Supplier-isolated contractor read. Worker/Credential установлены только как fail-closed schema/privacy spike: records/API/readiness заблокированы, паспортных полей нет, `PERSONNEL READY` не включён. Migrate и clean reinstall 35 DocType прошли; standalone suite `96/96`, полный Frappe suite до и после reinstall `47/47`. Employee positive runtime, cross-entity portal access, legacy migration, load/race, HR/privacy/legal UAT/sign-off и production deployment остаются OPEN; MG-CA-015 не закрыт. Evidence: [implementation/CA-08/README.md](implementation/CA-08/README.md), [runtime evidence](implementation/CA-08/runtime_evidence_v0_9_0_2026-08-18.md), [traceability](implementation/CA-08/traceability_v0_9_0.md).

**Продолжение v0.20.0 — актуализировано 2026-08-21:** `LOCAL AUTOMATED REMEDIATION QUALIFIED / EXACT-SOURCE BENCH 179/179 OK / FULL-STACK SYNTHETIC ENGINEER SLICE PASS / PUBLISHED-HEAD HOSTED CI PASS / RC NOT READY`. Реализованы separate Synthetic/Production activation watermark, typed Worker/Credential FSM, exact policy hash, dual verification, full/masked/no-number field-level projections, pre-unlink guarded private File, live readiness fingerprint и `PERSONNEL_READY`, exact-target audited support read, joint legal hold и dry-run-first retention. После обнаруженного cross-project leak remediation и отрицательные проверки включены в current final-tree static `212/212 PASS`; targeted Inspection завершён `5/5 PASS`; latest scoped privacy runtime дал policy `9/9`, alias/retention `24/24`, File boundaries `3/3`, DB/path/ledger residue `0`. Более ранний full Bench `127/127 OK` предшествует расширению regression-набора и сохранён только как historical provenance; current published tree `2e27643` прошёл exact-source `bench_quality_gate.py` on isolated `ca01.localhost` и дал full app tests `179/179 OK` in `3577.580s`. Source-controlled idempotent synthetic demo installer/reset/verifier установлен и runtime-qualified в составе текущего Bench. Source-controlled browser qualification harness теперь жёстко привязан к repo-local `playwright-core 1.62.1`, runtime contract покрыт в static `212/212`, а generated runtime path принудительно исключён через `.gitignore`. Historical hosted `static-quality` PASS on draft PR head `2865400` сохранён как provenance; current published draft-PR head `2e27643` has hosted `static-quality` PASS via run `32470646882`. Authenticated synthetic browser rerun на том же published head подтвердил symmetric own/foreign Engineer Form ACL, own-only List, foreign direct `403`, and full-stack `socket.io` polling `200`; это automated synthetic evidence, не human UAT и не blanket browser acceptance. Browser teardown первоначально выявил registry-user `Activity Log`, а последующий exact no-registry detector — 72 исторических derived rows; узкая fail-closed ownership remediation принята. Latest post-browser reset удалил `79` exact owned/derived rows, повторный reset — `0`; контрольные наборы до/после совпали: Comment `159` / `b9d32dc17c2ab6553df0d1d4a777988b4345e55726099790ce33b93c98b6bc8f`, Deleted Document `340` / `34fd6a9d165891f1a3224a631c51a597335ad2c85c6a036af953269013fb3291`, Version `91` / `bec2d1a60e893f98c0fa78a558231f39d7ec5c33b0f8b0a758497303ce398e79`. Post-run synthetic DB/File/recovery residue был проверен; zero-DB synthetic test blobs and stale metadata-only demo recovery jobs were removed by exact path proof, final checked demo/credential/download/recovery categories — `0`. Workspace visibility остаётся `OPEN BLOCKER` до Product Owner review. Actual scanner integration, race/load, human HR/DPO/Security UAT, restore/rollback, clean Staging и production activation не выполнены либо не утверждены; `MG-CA-015` остаётся PARTIAL. Evidence: [design](implementation/CA-08/privacy_controls_v0_20_0.md), [verification evidence](implementation/CA-08/verification_evidence_v0_20_0_2026-08-19.md), [authenticated synthetic browser UAT](implementation/CA-08/authenticated_browser_uat_v0_20_0_2026-08-19.md).

**Оценка:** L.

### CA-09. Derived deadline timeline

**Цель:** объединить контрольные даты договора без преждевременного создания ещё одного SSOT.

**AS-IS:** сроки распределены между Contract/Security, SLA, billing, payment due и документами. Принято сначала создать read-only `Contract Deadline View / Timeline`, а BPM должен владеть собственными warning/due/escalation dates (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/plan/owner_decisions_2026-08-17_target_structure.md:L178-L187`).

**Owner decision:** OQ-CA-013 утверждает Company timezone, Project/Contract Holiday List override и immutable snapshot calendar revision; точные production values/cut-off должны быть доказаны MG-CA-013.

**Состав:** адаптеры источников дат, normalized kind/source/owner/date/status/severity, due-soon/overdue rules, links to source, notification/escalation projection и Contract 360 API.

**Миграция/patches:** данные не копируются; создаются indexes/materialized cache только при измеренной необходимости. `Ferum Contract Milestone` не создавать без отдельного подтверждённого use case.

**Критерии приёмки:**

- каждая строка timeline имеет первичный source doctype/name и не редактируется как отдельный факт;

- Contract expiry, security, SLA, billing, payment, document и BPM dates попадают в нормализованный view;

- изменение source отражается после rebuild без orphan/duplicate;

- overdue/warning вычисляются по утверждённому precedence и зафиксированному MG-CA-013 calendar/holiday fixture;

- query latency укладывается в согласованный бюджет на репрезентативном объёме.

**Результат реализации v0.10.0 — 2026-08-18:** `CA-09 PARTIAL / SOURCE TIMELINE BENCH VERIFIED`. Реализованы read-only normalized projection с точным `source_doctype/name/field`, source fingerprint и adapters Contract, Maintenance, Request, Stage acceptance/billing/payment, Security/Bank Guarantee, Project Document, Finding и submitted Sales Invoice; отдельный `Ferum Deadline/Milestone` не создан. Pure calendar engine требует явный immutable timezone/revision/holiday/cut-off snapshot и fail-closed отклоняет неизвестный trigger/config. Без `as_of` классификация выключена, а production warning/escalation остаётся `disabled_pending_MG-CA-013`. Migrate сохранил 35 DocType; standalone suite `100/100`, targeted Frappe `3/3`, полный suite `50/50`. Signature/customer-response/general-warranty source fields, BPM dates, representative-volume latency, notification delivery, UAT/sign-off и production deployment остаются OPEN; MG-CA-013 не закрыт. Evidence: [implementation/CA-09/README.md](implementation/CA-09/README.md), [runtime evidence](implementation/CA-09/runtime_evidence_v0_10_0_2026-08-18.md), [traceability](implementation/CA-09/traceability_v0_10_0.md).

**Продолжение v0.18.0 — 2026-08-19:** `FR-03 ENGINEERING BOUNDARY PASS / MANUAL GATES OPEN`. Добавлены immutable Calendar Revision/Assignment/Calculation, source-controlled официальный календарь РФ 2026 (`247/118/4`, `Europe/Moscow`, `08:00–19:00`), Contract→Company precedence, signature deadline в Project Document и structured Customer Response source в External Dependency. Targeted `4/4+3/3`, полный Frappe suite `83/83`; mandatory `Absent` уменьшены `2→0`. Scheduler/notification delivery (FR-04), полный External Dependency flow (FR-08), annual Operations procedure, performance/race, UAT/sign-off и deployment остаются OPEN. Evidence: [design](implementation/CA-09/production_calendar_v0_18_0.md), [runtime](implementation/CA-09/runtime_evidence_v0_18_0_2026-08-19.md), [traceability](implementation/CA-09/traceability_v0_18_0_calendar.md).

**Продолжение v0.19.0 — 2026-08-19:** `FR-04 ENGINEERING/LOCAL E2E PASS / PRODUCTION DELIVERY GATES OPEN`. Добавлены fail-closed activation watermark, DP-06 `−3/−1/due/overdue/+1`, short `50/80/breach`, permission-filtered in-app/Email Queue, calendar-timezone daily digest, deterministic correlation/delivery keys, retry/dead-letter и typed manual retry. Targeted `6/6`, полный Frappe suite `89/89`; после тестов settings принудительно оставлены disabled. Production activation, external SMTP receipt/bounce, scheduler worker heartbeat, browser/RBAC/load UAT, sign-off и deployment остаются OPEN. Evidence: [design](implementation/CA-09/notification_delivery_v0_19_0.md), [runtime](implementation/CA-09/runtime_evidence_v0_19_0_2026-08-19.md), [traceability](implementation/CA-09/traceability_v0_19_0_notifications.md).

**Оценка:** M.

### CA-10. Contract 360° и exception center

**Цель:** дать руководителю целостную read-only картину договора и отклонений без дублирования SSOT.

**AS-IS:** финансовые данные уже доступны из Finance Summary, но единого Contract 360/Director Control Center нет. Приняты три представления и правило вести каждый агрегат к первичной записи (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/plan/owner_decisions_2026-08-17_target_structure.md:L189-L213`).

**Состав:** Service Project «Контракт 360°», widgets objects/systems, obligations, plan/fact, findings/defects, documents, deadlines, billing, AR, costs/margin, contractors; director exceptions с owner, age, severity и drill-down.

**Миграция/patches:** отсутствует; только read-model/cache. Денежные поля сохраняют permlevel и role restrictions.

**Критерии приёмки:**

- каждое число/исключение имеет drill-down к первичным данным;

- карточка не выполняет самостоятельные финансовые расчёты;

- директор видит overdue, blocked, missing evidence, unsigned/unreceived documents, AR и margin anomalies;

- роли без финансового доступа не получают суммы через API/export/cache;

- агрегаты проходят reconciliation с source reports.

**Результат реализации v0.11.0 — 2026-08-18:** `CA-10 PARTIAL / CONTRACT 360 + EXCEPTION CORE BENCH VERIFIED`. Реализованы permission-aware read-only `get_contract_360` и Director Control Center без нового DocType/cache: widgets строятся из primary records CA-01…09 и имеют exact drill-down; finance читает сохранённый CA-07 Summary без самостоятельного расчёта; non-finance redaction и отсутствие monetary/margin leakage подтверждены runtime. Migrate сохранил 35 DocType; standalone suite `104/104`, targeted Frappe `4/4`, полный suite `54/54`. Отдельная required-photo policy отсутствует и не изобретается; BPM blocked/stage-gate sources ожидают CA-11; MG-CA-013, UI/export, representative-volume performance, UAT/sign-off и production deployment остаются OPEN. Evidence: [implementation/CA-10/README.md](implementation/CA-10/README.md), [runtime evidence](implementation/CA-10/runtime_evidence_v0_11_0_2026-08-18.md), [traceability](implementation/CA-10/traceability_v0_11_0.md).

**Оценка:** L.

### CA-11. BPM Core

**Цель:** реализовать versioned универсальный процессный слой, не создавая второй task manager.

**AS-IS:** запуск проекта моделируется hard-coded API, а Process Template/Stage/Step, Contract Requirement, Process Evidence и Stage Gate отсутствуют (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/api/projects.py:L265-L342`; `contract-accounting/03_asis_model.md:L326-L336`). Утверждённые OQ-CA-010/011 фиксируют отдельные parent DocType Template/Stage/Step, Project Process/Stage/Process Step, Stage Gate/Evidence и JSON Logic allowlist/no eval; переход к child topology возможен только новым ADR с обновлением модели и трассировки (`Structure of the contract accounting system.md:L1001-L1069`; [05_target_model.md](05_target_model.md#3-новые-doctype)).

**Owner decision:** OQ-CA-012 утверждает persisted base `status` + derived `is_overdue/overdue_since/display_status`; отдельный persisted `Overdue` не вводится.

**Состав:**

- versioned `Ferum Process Template`, `Ferum Stage Template` и `Ferum Step Template` как parent DocType;

- `Ferum Project Process`, `Ferum Project Stage` и `Ferum Project Process Step` как parent instances;

- Requirement assessment, applicable template selection и idempotent generator;

- `deadline_type`, trigger/offset/unit/calendar, condition/activation, responsible role/assignee;

- criticality/blocking, evidence types, Waiting External/timeout action, warning/escalation;

- статусы и переходы, включая Blocked и Not Applicable с обязательной причиной;

- Process Evidence и Stage Gate evaluator;

- integration adapters к Assignment/ToDo, Communication, File, ERP documents и payments.

**Миграция/patches:** опубликованные template versions immutable. Новые проекты получают актуальную версию; открытые проекты — preview + explicit owner confirmation. Hard-coded historical steps не объявляются Completed без evidence.

**Критерии приёмки:**

- изменение шаблона создаёт новую версию и не меняет активный instance;

- один и тот же generation request не создаёт второй process/step;

- relative deadline корректно вычисляется от trigger event с выбранным calendar;

- Waiting External запускает warning/timeout action; timeout не завершает шаг без нормативного основания;

- Not Applicable невозможен без причины, Completed — без требуемого evidence;

- один незакрытый blocking condition даёт failed Gate и запрещает следующий stage;

- персональная работа отображается через стандартный Assignment/ToDo, а Process Step остаётся процессным SSOT;

- permission/audit/negative transition tests покрывают все статусы.

**Результат реализации v0.12.0 — 2026-08-18:** `CA-11 PARTIAL / VERSIONED BPM CORE BENCH VERIFIED`. Реализованы девять утверждённых parent DocType Template/Stage/Step, Project Process/Stage/Step, Stage Gate, Process Evidence и append-only Process Event; Published graph immutable, generation idempotent по exact key, safe JSON Logic использует allowlist/no eval, relative deadline требует explicit immutable calendar snapshot, Process Step остаётся SSOT при standard ToDo projection, completion требует Validated evidence, Failed Gate блокирует следующую stage, а Overdue вычисляется поверх base status. BPM сроки и blocked/failed exceptions подключены к CA-09/10 read-model. Migrate расширил схему с 35 до 44 DocType; standalone suite `117/117`, targeted CA-11 `5/5`, полный Frappe suite `59/59`. Все 169 req-id не объявляются закрытыми: configured launch/Inspection/Billing Cycle processes, automatic external events/scheduler/notifications/escalation delivery, role resolver, ad-hoc steps, MG-CA-013, performance, UAT/sign-off и production deployment остаются OPEN. Evidence: [implementation/CA-11/README.md](implementation/CA-11/README.md), [runtime evidence](implementation/CA-11/runtime_evidence_v0_12_0_2026-08-18.md), [traceability](implementation/CA-11/traceability_v0_12_0.md).

**Оценка:** XL.

### CA-12. Семистадийный запуск и Inspection

**Цель:** настроить эталонный launch-процесс от инициации до готовности к первому закрытию периода.

**AS-IS:** отдельного `Ferum Inspection` и lifecycle первичного обследования нет; Checklist Template является лишь шаблоном вопросов (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_checklist_template/ferum_checklist_template.py:L1-L16`; `contract-accounting/03_asis_model.md:L326-L337`).

**Состав:** template стадий Initiation, Customer Contact, Execution Scheme, Personnel Readiness, Mobilization, Initial Inspection, Launch Readiness; Inspection snapshot/report/outcome; generation `Ferum Finding(category=Defect)`/Additional Work; после MG-CA-015 — personnel/contractor/document gates для Employee и Contractor Worker; evidence packs.

**Миграция/patches:** существующие active projects получают launch assessment, но история не генерируется автоматически. Completed/NA status разрешён только после ручного/evidence-backed mapping. Existing checklist results связываются с Inspection только однозначным patch.

**Критерии приёмки:**

- применимые стадии/шаги генерируются из Contract Requirement и template version;

- personnel gate не проходит без Assignment, действующих credentials и обязательных документов ни для Employee, ни для Contractor Worker;

- Inspection хранит состояние объекта/систем, evidence, outcome и дату snapshot;

- `Ferum Finding(category=Defect)`/Additional Work создаются из Inspection без потери исходного результата и повторный event не создаёт дубль;

- launch readiness не наступает при одном failed blocking gate;

- пилот проходит на B2G, B2B и subcontract сценариях с документированными различиями.

**Результат реализации v0.13.0 — 2026-08-18:** `CA-12 PARTIAL / SEVEN-STAGE LAUNCH + INSPECTION CORE BENCH VERIFIED`. Реализованы idempotent Published `FERUM-LAUNCH` v1 из 7 stages/25 steps без автоматической генерации истории, explicit confirmed generation, отдельный `Ferum Inspection` с frozen template/inventory/report snapshots, checklist/team/evidence, независимыми manager/customer lifecycle, Project Document report, Finding/Photo outputs и exact Approved-Inspection Process Evidence. Финальный Passed Launch gate переводит project `Launching→Active` через CA-01 lifecycle audit. Migrate расширил схему с 44 до 47 DocType; standalone suite `123/123`, targeted CA-12 `4/4`, полный Frappe suite `63/63`. Все 84 req-id не объявляются закрытыми: Personnel/Credential positive gate остаётся заблокирован MG-CA-015; automatic award trigger, child Inspection process, automatic act/defect statement/Additional Work, B2G/B2B/subcontract pilots, CA-13 operational activation, performance, UAT/sign-off и production deployment остаются OPEN. Evidence: [implementation/CA-12/README.md](implementation/CA-12/README.md), [runtime evidence](implementation/CA-12/runtime_evidence_v0_13_0_2026-08-18.md), [traceability](implementation/CA-12/traceability_v0_13_0.md).

**Оценка:** XL.

### CA-13. Первое закрытие периода и Billing Cycle

**Цель:** завершить стадию запуска проверяемой готовностью первого закрывающего комплекта.

**AS-IS:** Billing Output связан с invoice/request, но самостоятельного Billing Cycle Gate нет (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_billing_output/ferum_billing_output.json#sales_invoice`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_billing_output/ferum_billing_output.json#basis_service_request`; `contract-accounting/03_asis_model.md:L326-L338`).

**Состав:** Billing Cycle, period, expected/accepted work, billing basis readiness, document set, issue/sign/send/original receipt/payment milestones и stage gate.

**Миграция/patches:** backfill cycles из execution periods и active billing outputs только при однозначном period key. Issued/Signed output не менять; conflicts — manual legal reconciliation.

**Критерии приёмки:**

- цикл показывает expected, accepted, unbilled, billed, signed, sent и paid state;

- Gate первого периода закрывается только при выполнении применимых blocking условий;

- cycle→basis→output→invoice→payment имеет двустороннюю трассировку;

- correction/supersede не теряет историю цикла;

- overdue action попадает в My Actions/Director Center.

**Результат реализации v0.14.0 — 2026-08-18:** `CA-13 PARTIAL / RECURRING BILLING CYCLE + PERIOD GATE BENCH VERIFIED`. Реализованы отдельный `Ferum Billing Cycle`, exact Published `FERUM-BILLING-CYCLE` v1 из 1 stage/9 blocking milestones, immutable expected-work snapshot, read-only expected/accepted/unbilled/billed/signed/sent/receipt/paid projection, Cycle→Basis→Output→Sales Invoice→Payment Entry trace и reverse resolver, correction inheritance, evidence-backed Passed Gate/Completed Cycle и overdue source в CA-09/10. Cycle не хранит ledger и не пишет GL. Explicit backfill допускает только Draft/Generated exact-period groups; Issued/Signed блокируются для manual legal reconciliation. Repeated migrate расширил схему с 47 до 48 DocType; standalone suite `128/128`, targeted CA-13 `2/2`, полный Frappe suite `65/65`. Automatic recurrence/scheduler, dedicated positive UPD/SF branch, external delivery/receipt, runtime legacy backfill rehearsal, CA-14 UI, performance, UAT/sign-off и production deployment остаются OPEN. Evidence: [implementation/CA-13/README.md](implementation/CA-13/README.md), [runtime evidence](implementation/CA-13/runtime_evidence_v0_14_0_2026-08-18.md), [traceability](implementation/CA-13/traceability_v0_14_0.md).

**Оценка:** L.

### CA-14. «Мои действия» и «Запуск проектов»

**Цель:** превратить процессные и операционные источники в управляемые рабочие очереди.

**AS-IS:** портал имеет отдельные выборки заявок/визитов/settlements, но не единый My Actions/Launch Projects workspace (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/api/portal.py:L764-L805`). Целевые источники и сортировка определены owner decision (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/plan/owner_decisions_2026-08-17_target_structure.md:L196-L204`).

**Состав:** Project Launch UI, My Actions, Launch Projects, фильтры overdue/today/upcoming/blocked/waiting external, bulk-safe navigation, role views и drill-down.

**Миграция/patches:** отсутствует; построение поверх BPM Step, Assignment/ToDo, Request, Visit, approvals и documents. Cache не становится SSOT.

**Критерии приёмки:**

- одна операция не дублируется как независимые задачи из Step и ToDo;

- пользователь видит только свои/делегированные действия и разрешённые проекты;

- priority ordering воспроизводимо сортирует overdue→today→upcoming и отдельно blocked/waiting;

- Launch Projects показывает failed gate и конкретные blocking conditions;

- deep links ведут к process/source/evidence без потери фильтра/контекста.

**Результат реализации v0.15.0 — 2026-08-18:** `CA-14 PARTIAL / PERMISSION-SAFE WORK QUEUES + LAUNCH UI BENCH VERIFIED`. Реализованы standard Desk Page «Мои действия»/«Запуск проектов», вкладка Service Project «Запуск», read-only projections без нового task/cache SSOT, canonical Step+ToDo de-duplication, actionable-only queue, stable overdue→today→upcoming ordering, stage/step progress, failed Gate criteria и source drill-down. Runtime подтверждены 7 stages/25 steps, explicit overdue ordering, 4 active actions вместо 25 future Planned, user isolation и MG-CA-015 blocker. Repeated migrate PASS; standalone `132/132`, targeted CA-14 `2/2`, полный Frappe suite `67/67`. Explicit contractor-required/counterparty semantics, positive credentials, browser/cross-role UAT, performance/load/race, notification delivery и production deployment остаются OPEN. Evidence: [implementation/CA-14/README.md](implementation/CA-14/README.md), [runtime evidence](implementation/CA-14/runtime_evidence_v0_15_0_2026-08-18.md), [traceability](implementation/CA-14/traceability_v0_15_0.md).

**Оценка:** L.

### CA-15. Интеграционное укрепление и сквозная трассировка

**Цель:** доказать, что целевая модель образует одну систему, а не набор несвязанных DocType.

**AS-IS:** Finance Summary уже агрегирует стандартные invoices/payments, а Audit/File Lock дают сервисный контроль, но полная TARGET-цепочка отсутствует (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/services/project_finance_summary.py:L403-L701`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_audit_log/ferum_audit_log.py:L14-L47`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_file_lock/ferum_file_lock.py:L16-L66`).

**Состав:** target ER conformance, cross-module permissions, audit/events, reconciliation, performance/indexes, migration closure, end-to-end dashboards и acceptance pack; field-level disposition Codex-only fields по OQ-CA-022; Import Batch runtime claim только после MG-CA-023.

**Миграция/patches:** orphan/duplicate reports, backfill provenance, controlled cutover feature flags, rollback scripts, archive старых зеркал только после retention/legal approval. Удаление данных не входит без отдельного разрешения.

**Критерии приёмки:**

- система отвечает на цепочку «почему возникло → где → когда → кто → что сделано → чем подтверждено → что выставлено → что оплачено → сколько заработали»;

- каждая ссылка проходит forward/reverse integrity check, orphan count равен нулю либо имеет утверждённый exception;

- permission matrix закрывает internal roles, Company/Project/Assignment, API/export/report/print/private-file boundaries; Client/Contractor interactive access имеет negative evidence отсутствия;

- scheduler/retry/idempotency tests не создают дубликаты;

- Import Batch скрыт, не имеет user permission/API/job и проходит negative access test; `MG-CA-023=N/A FOR RELEASE`;

- миграционный dry-run, cutover rehearsal и rollback имеют отдельные evidence artifacts;

- все 557 `req_id` имеют acceptance criterion и owner в [07_traceability.csv](07_traceability.csv), а оставшиеся вопросы и MG gates — в [08_open_questions.md](08_open_questions.md).

**Результат реализации v0.16.0 — 2026-08-18:** `CA-15 PARTIAL / READ-ONLY E2E TRACE + PROJECT INTEGRITY + NAMED DESK PAGES BENCH VERIFIED`. Реализованы permission-safe девятисегментная цепочка why→margin, семь сквозных dimensions, stable source fingerprint/drill-down, restricted read-only project integrity dry-run для typed/Dynamic Link edges и standard Desk Pages «Контракт 360°»/«Операционная работа»/«Центр контроля директора». OQ-CA-022 получил field-level disposition без silent drop; OPEN implementation rows сохранены. Import Batch явно inactive pending MG-CA-023. Repeated migrate и app build PASS; standalone `135/135`, targeted CA-15 `2/2`, полный Frappe suite `69/69`. Portfolio/legacy reconciliation, browser/cross-role/export/report UAT, performance/load/race, scheduler/retry topology, migration dry-run/cutover/rollback, archive/legal sign-off и production deployment остаются OPEN. Evidence: [implementation/CA-15/README.md](implementation/CA-15/README.md), [runtime evidence](implementation/CA-15/runtime_evidence_v0_16_0_2026-08-18.md), [traceability](implementation/CA-15/traceability_v0_16_0.md), [OQ-CA-022 disposition](implementation/CA-15/field_disposition_v0_16_0.md).

**Продолжение v0.16.1 — 2026-08-18:** реальный Playwright UAT manager/director slice подтвердил три standard Desk Pages, exact drill-down и симметричные page role boundaries. UAT обнаружил ложные нули директорской проекции из-за отсутствующих source DocPerm; исправление добавляет директору только `read/report` на 18 operational source/context DocType и подтверждено повторным browser UAT, static permission contract и Frappe regression. Локальный five-request E2E smoke: median `110 ms`, max `427 ms`; это не representative-volume gate. Standalone `136/136`, targeted CA-15 `2/2`, targeted Contract 360 `4/4`, final-tree full Frappe `69/69`; repeated migrate и PEP 517 wheel v0.16.1 PASS. Остальные роли/API-export-report, load/race, migration rehearsal и production/sign-off остаются OPEN. Evidence: [browser/role UAT v0.16.1](implementation/CA-15/browser_uat_v0_16_1_2026-08-18.md), [traceability addendum](implementation/CA-15/traceability_v0_16_1.md).

**Продолжение v0.16.2 — 2026-08-18:** Operations Page расширена на утверждённую внутреннюю аудиторию Engineer/Accountant/Office Manager/Project Lead с server-authoritative Launch capability: non-launch клиент больше не вызывает запрещённый Launch API. Engineer и Office Manager получили только base `read/report` Service Project с project-scoped query/has-permission boundary; own/foreign project и write denial проверены runtime. Реальный Playwright UAT подтвердил по одному assigned/owned действию для Engineer/Accountant/Office Manager, `Restricted` Launch card для них, полноценные Launch KPI и Director Control для Project Lead, а также negative direct-URL boundaries. Contractor намеренно не включён до portal UAT и MG-CA-015. Repeated migrate/build PASS; standalone `136/136`, targeted Workspaces `2/2`, final-tree full Frappe `69/69` за `334.096 s`, wheel v0.16.2 PASS. API export/report, оставшиеся роли, load/race, migration rehearsal и production/sign-off остаются OPEN. Evidence: [Operations cross-role UAT v0.16.2](implementation/CA-15/cross_role_uat_v0_16_2_2026-08-18.md), [traceability addendum](implementation/CA-15/traceability_v0_16_2.md).

**Продолжение v0.16.3 — 2026-08-18:** реализован однозначный core OQ-CA-022/RA-09 для Service Request: обязательные subject/description, fail-closed typed provenance Finding/Maintenance Visit, service-owned Paid Work/Remaining successors с deterministic identity/DB uniqueness, reverse projection без remaining mirror и exact standard File → Project Document customer approval gate для Additional Work. Post-model-sync patch сохраняет факты, маркирует отсутствующий legacy-текст для review и блокирует недоказанный typed source. Первый и повторный migrate, app build и wheel PASS; standalone `138/138`, targeted affected suites `23/23`, final-tree full Frappe `71/71` за `278.587 s`. Это не blanket PASS: Internal/Other typed owner, access-denied Process Event command, параллельный race/load test, browser/cross-role/legal UAT, production migration rehearsal и deployment остаются OPEN. Evidence: [Service Request disposition v0.16.3](implementation/CA-15/service_request_disposition_v0_16_3_2026-08-18.md), [traceability addendum](implementation/CA-15/traceability_v0_16_3.md).

**Оценка:** XL.

## 6. Миграционная стратегия и обязательные patches

| Этап | Patch/reconciliation | Fail-closed правило | Rollback/контроль |
| --- | --- | --- | --- |
| `CA-00` | Tag/manifest `7145d87`, installed-app/schema/config inventory и legacy zero-record act | Baseline decision не является evidence; секреты не включаются | Clean-environment backup + restore/rollback rehearsal |
| `CA-01` | TARGET legal fields, утверждённая dual-status schema/configuration и перевод связей на Service Project root; тестовые записи reset/recreate | Только переходы и cross-state пары OQ-CA-003; legacy `Contract.status` и audit history не переносятся | Controlled rollback только schema/configuration, feature flag, новой логики и новых связей; обратного mapping в 12-state model нет |
| `CA-02` | Scope→Obligation candidates | Создавать только при однозначных Contract/Object/System/effective dates | Idempotency key + candidate report |
| `CA-03` | Visit/Schedule→Obligation provenance | Не нарушать generated-visit unique key; неоднозначные facts в review | Revert links, не удаляя факты |
| `CA-04` | Request→Finding(category=Defect) candidate report | Никакой автоматической семантической конверсии текста | Delete only unconfirmed generated Finding candidates |
| `CA-05` | File/Billing Artifact→Project Document references | Не присваивать статус бумажного оригинала без evidence | Удалить projection/link, не физический File/Artifact |
| `CA-06` | Billing Basis backfill | Issued/Signed basis не переписывать при неоднозначности | Supersede/correction, не in-place rewrite |
| `CA-07` | Full Finance Summary rebuild | Никогда не создавать correction GL Entry из migration patch | Rebuild from ERPNext source documents |
| `CA-08` | Contractor link→Assignment/Contractor Worker candidates | Не изобретать Worker identity, passport, qualification/price/effective period | Candidate rollback с сохранением source links; protected identity data не создаются |
| `CA-09` | Derived deadline projection | Timeline не редактируется и не становится SSOT | Drop/rebuild cache/view |
| `CA-11` | Existing project process preview | Не отмечать исторические steps Completed/NA без evidence/reason | Disable generated instance, сохранить audit |
| `CA-12` | Existing launch/inspection assessment | Не реконструировать обследование по checklist без однозначной связи | Manual review, source checklist неизменен |
| `CA-13` | Billing Cycle period backfill | Issued/Signed outputs не менять | Remove cycle link/projection, preserve legal document |
| `CA-15` | Provenance/orphan cleanup | Физическое удаление вне scope без отдельного approval | Feature-flag rollback + retained mirrors |

Каждый действительно необходимый data patch должен поддерживать dry-run, идемпотентный повторный запуск, счётчики `scanned/created/updated/skipped/conflict`, журнал ошибок без секретов и отдельный rollback/reconciliation report. Это правило не требует создавать patch для сохранения или переноса тестовых legacy status/history records.

## 7. Архитектурные риски

| Риск | Вероятность / влияние | Последствие | Митигация | Owner |
| --- | --- | --- | --- | --- |
| Не завершён перевод schema-связей на единый Service Project root | Высокая / критическое | Второй Contract SSOT или orphan links после cutover | `CA-01` ADR, schema/link inventory, integrity tests и запрет новых ссылок на retired root | Product Owner + Architect |
| Obligation дублирует Project Scope | Средняя / критическое | Два генератора одного ТО | Закрепить Requirement→Step либо Obligation→Scope; единый period/idempotency key | Domain Architect |
| BPM становится вторым task manager | Средняя / высокое | Дубли поручений и статусов | Process Step — process SSOT, Assignment/ToDo — персональная доставка | BPM Architect |
| Project Document дублирует Billing Artifact | Средняя / высокое | Несовпадающие версии юридического файла | Reference/projection, один physical file lifecycle | Document Owner |
| Deadline engine становится новым SSOT | Средняя / высокое | Расхождение дат с бизнес-документами | Только derived timeline; Milestone после отдельного use case | Architect |
| Party Identity reconciliation реализован как скрытый второй master | Средняя / высокое | Расхождение Customer/Supplier/Company и ошибочный auto-merge | OQ-CA-017: standard masters — SSOT; explicit reconciliation, field-specific one-way rules и idempotent no-ambiguous-merge tests | MDM Owner |
| Финансовый слой начинает писать GL | Низкая / критическое | Вторая бухгалтерия и неверная отчётность | ERPNext documents/GL — SSOT, кастомный слой read-model | Finance Owner |
| Gate подменяет server authorization | Средняя / критическое | Обход бизнес-переходов | Gate управляет стадией, controller отдельно валидирует документ | Security Architect |

## 8. Миграционные риски

| Риск | Вероятность / влияние | Митигация | Проверяемое доказательство |
| --- | --- | --- | --- |
| Completion baseline не имеет annotated tag/полного manifest | Высокая / критическое | Зафиксировать `7145d87` без замены на текущий `0.16.3` | Tag + remote SHA + manifest + hashes |
| Реализация отклоняется от утверждённой dual-status FSM | Средняя / критическое | Генерировать server policy/tests из versioned OQ-CA-003 matrix; запрещать UI-only transitions | Exact enum/matrix check + positive/negative server transition tests |
| Дубли Scope/Obligation/Visit | Средняя / критическое | Conditional unique key, dry-run duplicate report | Negative DB test + idempotent second run |
| Неизвестный статус бумажного оригинала | Высокая / высокое | Не ставить Received/Archived без evidence | Manual review report, zero inferred receipts |
| Backfill basis юридически выпущенного документа | Средняя / критическое | Только однозначный snapshot; legal review иначе | Issued/Signed hash unchanged |
| Потеря effective history | Средняя / критическое | Versioned rows, no in-place overwrite | Before/after temporal query tests |
| Drift Finance Summary после cutover | Средняя / высокое | Full rebuild и reconciliation по ERPNext | Difference report с утверждённым threshold |
| Permission leakage через report/API/cache | Средняя / критическое | Permission query tests на каждом read path | Negative tests для customer/contractor/non-finance |
| Existing projects получают ложный Completed process | Высокая / высокое | Preview/owner confirmation/evidence-backed mapping | Zero auto-completed steps without evidence |
| Rollback удаляет юридические артефакты | Низкая / критическое | Rollback только links/projections, не File/Billing Artifact | Hash/count до и после rollback |
| Import Batch ошибочно экспонируется несмотря на исключение из release | Средняя / высокое | Скрыть menu/permissions/API/job, оставить feature disabled | Negative access/entrypoint/job evidence, `MG-CA-023=N/A FOR RELEASE` |

## 9. Организационные риски

| Риск | Последствие | Митигация | Owner |
| --- | --- | --- | --- |
| Утверждённые FSM, Party Identity или VAT boundaries меняются без decision log | Неконтролируемый drift и противоречивая бизнес-логика | Versioned decision log; изменения только новым owner decision | Product Owner + Finance Owner |
| Юристы не определили статусы оригинала и evidence акта | Нельзя принять `CA-05/CA-06` | Legal workshop на реальных документах, утверждённая status/evidence matrix | Legal Owner |
| Операции не ведут Object/System/Scope качественно | Obligation и plan-fact недостоверны | Data stewardship, completeness dashboard, пилотные договоры | Operations Owner |
| Квалификации персонала не имеют владельца/реестра | Personnel Gate формален | Назначить HR/HSE owner, регламент обновления и expiry alerts | HR/HSE Owner |
| Внутренние владельцы не готовы поддерживать assignment/credential data | Readiness становится формальным либо устаревает | Pilot на representative projects, stewardship и регламент expiry | Contractor Manager |
| Автотесты ошибочно принимаются за UAT/legal PASS | Ложная готовность релиза | Раздельные evidence gates и запрет синтетического approval | Release Manager |
| Исторический MVP ошибочно принимают за готовый first release | Пропускаются обязательные подрядчики, BPM, документы, RBAC и qualification | Release scope определяется `DP-03`, а не только `CA-00…CA-07` | Steering Committee |
| Нет владельца exception backlog | Просрочки видимы, но не устраняются | SLA/owner/escalation для каждого класса исключений | Operations Director |

## 10. Волны завершения и release gates

| Волна | Шаги | Выходной результат | Gate перехода |
| --- | --- | --- | --- |
| 0. Decisions | `1` | Release Decisions v1 и standalone ADR | документы согласованы и связаны |
| 1. Freeze and truth | `2…5` | baseline/tag/manifest, legacy N/A, current capability delta, CI profile | воспроизводимый source+evidence baseline |
| 2. Mandatory product closure | `6…14` | calendar, automation, contractor/evidence/request/document/report scope | mandatory matrix без `Absent`, legal gate закрыт |
| 3. Qualification | `15…19` | RBAC, Staging, load/race, UAT, restore/rollback/cutover | все применимые gates PASS на одном tree |
| 4. Release | `20…21` | immutable RC и наблюдённый production launch | approvals + smoke/health/monitoring/backup |
| 5. Completion | `22` | hypercare exit, post-release review, legacy disposition | project completion sign-off |

Полная последовательность, owners и exit criteria находятся в [10_remaining_questions_and_actions.md](10_remaining_questions_and_actions.md), а текущая компактная последовательность — в [15_first_stage_completion_sequence.md](15_first_stage_completion_sequence.md). Completion tag, legacy technical inventory/backup, [Release Scope v1](12_release_scope_v1.md), local [Quality/CI Profile v1](14_quality_profile_v1.md), historical [hosted static PASS](implementation/CA-00/hosted_ci_evidence_v0_19_0_2026-08-19.md) и engineering core `FR-02/03/04` выполнены только в своей доказанной границе. Аудит полноты выявил отсутствие воспроизводимого demo/UAT dataset и cross-project authorization defect; remediation подтверждена current final-tree static `212/212 PASS`, targeted Inspection `5/5 PASS`, scoped runtime-наборами, exact-source Bench gate `179/179 OK`, current full-stack synthetic Engineer slice with `socket.io` polling `200`, pinned repo-local browser runtime contract, and verified GitHub protection for `main` plus blocked `v*` tags. Historical hosted `static-quality` PASS on draft PR head `2865400` сохранён как provenance; the draft PR has hosted `static-quality` PASS on an immutable published head, while any later local edits require a fresh hosted run. Release Scope при этом остаётся 557/557 строк: 554 обязательных, из них 280 `Implemented` и 274 `Partial`. Current authenticated synthetic browser evidence подтверждает только Engineer own/foreign Form/List/direct-URL/full-stack slice; Workspace visibility и human UAT остаются OPEN вместе с restore/rollback, performance/race/load, clean Staging и production deployment. Поэтому общий статус не повышается: `NOT READY FOR PRODUCTION / RC NOT READY`.
