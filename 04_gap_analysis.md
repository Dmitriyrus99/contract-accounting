# 04. Гэп-анализ TARGET ↔ SPEC ↔ CODE

**Цель документа:** объяснить воспроизводимые разрывы между TARGET, Claude SPEC v6.2.21 и текущим Claude working tree. Атомарные проверяемые точки находятся в [04_coverage_matrix.csv](04_coverage_matrix.csv).

**Дата анализа:** 2026-08-17. **Owner decisions синхронизированы:** 2026-08-18.

**Источник истины для желаемого состояния:** TARGET — `Structure of the contract accounting system.md`. SPEC и CODE являются анализируемым AS-IS и не могут добавлять требования в TARGET.

**Как проверить:** применить правила ниже к каждой строке матрицы, открыть полный `spec_ref`/`code_ref` и сверить отрицательные результаты с [01_source_inventory.csv](01_source_inventory.csv).

## Сводка матрицы

Матрица содержит **557** независимо проверяемых требований: часть A — **261**, часть B — **296**. Представлены все **59** разделов TARGET. Вердикты: **Conflict 4**, **Gap-Both 395**, **Gap-Code 19**, **OK 139**. SPEC: **Absent 236**, **Contradicts 4**, **Covered 158**, **Partial 159**. CODE: **Absent 262**, **Implemented 150**, **Partial 145**. Приоритеты: **Must 535**, **Should 22**.

## Owner decision update 2026-08-18

Заказчик утвердил все 23 OQ из [08_open_questions.md](08_open_questions.md). Это снимает owner-level архитектурную неопределённость, но **не меняет** SPEC/CODE/verdict матрицы: решения не означают implementation/runtime PASS. Остаются применимые manual/configuration/runtime gates MG-CA-001/013/015/016/023 и field-level reconciliation OQ-CA-022.

## Детерминированные правила

1. `Contradicts` в SPEC всегда даёт `Conflict`.
2. `Covered + Implemented` даёт `OK`.
3. `Covered + Partial/Absent` даёт `Gap-Code`.
4. `Partial/Absent` в SPEC без прямого противоречия даёт `Gap-Both`, независимо от CODE.
5. `Partial` означает, что ссылка доказывает только названную часть требования.
6. `Absent` сопровождается `—`; наличие тестового файла не считается PASS, тесты в discovery не запускались.

## Топ-15 разрывов TARGET

| # | Разрыв | Req ID | Последствие | Severity | Следующий шаг | Доказательство |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | TARGET объединяет договор и Service Project, SPEC разделяет юридический Contract и execution context | TCA-A-01-01 | Архитектура и reset/recreate test data утверждены; остаётся schema/link cutover | Critical | Выполнить CA-00/01 и MG-CA-016; MG-CA-001 только если legacy records сохраняются | `Structure of the contract accounting system.md:L44-L52`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/spec/ferum_custom_spec_v6_2_21.md:L1658-L1667`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/spec/ferum_custom_spec_v6_2_21.md:L2189-L2204` |
| 2 | Точные юридический и execution enum исходного TARGET не совпадают с SPEC/CODE и заменены owner-approved change-set | TCA-A-13-02, TCA-A-13-04 | Реализация должна следовать решению OQ-CA-003, сохраняя явный trace к конфликтующим источникам | Critical | Реализовать exact approved enum/matrices и positive/negative server tests; legacy status migration не выполнять | `Structure of the contract accounting system.md:L582-L626`; [08_open_questions.md](08_open_questions.md#oq-ca-003-какова-целевая-dual-status-fsm-договора); `Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/spec/ferum_custom_spec_v6_2_21.md:L1669-L1685` |
| 3 | Нет Project Document и раздельных статусов цифровой копии/оригинала | TCA-A-08-01…13; TCA-B-25-01…04 | Нет единого документарного реестра и контроля оригиналов | Critical | Реализовать документарное ядро | `Structure of the contract accounting system.md:L398-L435`; `Structure of the contract accounting system.md:L1920-L1943` |
| 4 | Нет Finding/Defect как отдельного операционного факта | TCA-A-07-01…08 | Выявленное смешивается с заявкой и выполнением | Critical | Реализовать Finding lifecycle | `Structure of the contract accounting system.md:L350-L394`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_request/ferum_service_request.json#request_type` |
| 5 | Нет юридически устойчивого набора оснований акта и списка неактированных работ | TCA-A-10-01…03 | Нельзя доказать состав акта и найти неактированное | Critical | Billing Basis snapshot + coverage query | `Structure of the contract accounting system.md:L472-L498`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_billing_output/ferum_billing_output.json#basis_service_request` |
| 6 | Нет Contractor Assignment по проекту×объекту×системе×работе | TCA-A-12-01…10 | Нельзя выразить ответственность и маржу подрядчика | Critical | Отделить Assignment от settlement/pricing | `Structure of the contract accounting system.md:L544-L578`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_object/ferum_project_object.json#contractor` |
| 7 | Нет универсальной Template/Stage/Step instance-модели | TCA-B-02-01…11; TCA-B-03-01…09 | Регламент остаётся hard-coded | Critical | BPM Core с версионностью | `Structure of the contract accounting system.md:L968-L1066`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/api/projects.py:L265-L342` |
| 8 | Нет относительных сроков, событий и условного ветвления BPM | TCA-B-08-01…10; TCA-B-09-01…04; TCA-B-10-01…04 | Нельзя воспроизводимо рассчитывать процесс | Critical | Deadline/Event/Condition engine | `Structure of the contract accounting system.md:L1196-L1322` |
| 9 | Нет Personnel Readiness и Gate PERSONNEL READY | TCA-B-16-01…13 | К работам может попасть неподготовленный персонал | Critical | Credential model + blocking gate | `Structure of the contract accounting system.md:L1483-L1530` |
| 10 | Нет самостоятельного Inspection и автоматических результатов обследования | TCA-B-18-01…05; TCA-B-19-01…08 | Нет checklist, findings, отчёта и согласования | Critical | Inspection lifecycle | `Structure of the contract accounting system.md:L1582-L1653` |
| 11 | Нет Waiting External с timeout_action | TCA-B-20-01…05 | Ожидание заказчика неуправляемо | Critical | External wait state + timeout transition | `Structure of the contract accounting system.md:L1657-L1693` |
| 12 | Нет повторяющегося Billing Cycle | TCA-B-21-01…11 | Закрытие периода не является управляемым процессом | Critical | Billing Process template | `Structure of the contract accounting system.md:L1697-L1732` |
| 13 | Нет generic Stage Gate | TCA-B-26-01…04 | Процент выполнения может скрыть blocking-пробел | Critical | Gate conditions and enforcement | `Structure of the contract accounting system.md:L1947-L1977` |
| 14 | Нет My Actions и Project Launches workspaces | TCA-B-31-01…05; TCA-B-32-01…09 | Исполнители и руководители не видят процессный backlog | Critical | Process workspaces after BPM Core | `Structure of the contract accounting system.md:L2108-L2176` |
| 15 | Нет универсальной формулы Trigger→Stage→Step→Gate→Next Stage и пяти обязательных механизмов | TCA-B-39-01…21 | BPM выродится в закрываемый чек-лист | Critical | Закрепить BPM acceptance criteria | `Structure of the contract accounting system.md:L2400-L2457` |

## Реальные конфликты TARGET ↔ Claude SPEC

| Req ID | TARGET | Claude SPEC/CODE | Решение |
| --- | --- | --- | --- |
| TCA-A-01-01 | Service Project = один исполняемый договор | Contract и Service Project разделены | Owner decision по cardinality и UX-корню |
| TCA-A-13-02 | Исходный TARGET: Draft/Signed/Active/Expired/Terminated/Closed; OQ-CA-003 change-set: Draft/On Approval/Approved/Signing/Signed/In Force/Cancelled/Terminated/Expired | SPEC/CODE и owner-approved enum различаются; legacy mapping не нужен | Exact enum/transition implementation + traceable change-set |
| TCA-A-13-04 | Исходный TARGET: Launch/In Progress/Problem/Closing/Completed/Archive; OQ-CA-003 change-set: Not Started/Launching/Active/Suspended/Completed/Stopped | CODE project_status и оба TARGET-набора различаются | Exact enum/transition implementation + traceable change-set |
| TCA-A-17-04 | Объект использует стандартный Address | SPEC/CODE хранят address как Small Text | Решить миграцию к Address либо ратифицировать отклонение |

Остальные неполные соответствия являются `Gap-Code` или `Gap-Both`, а не конфликтами.

## Отдельный сравнительный реестр Claude ↔ Codex

Эта таблица не влияет на TARGET-вердикты и не увеличивает число `Conflict` в матрице.

| Предмет | Claude baseline | Codex baseline | Рекомендуемый SSOT | Доказательство |
| --- | --- | --- | --- | --- |
| SPEC baseline | v6.2.21, 305 REQ | v6.2.1, 260 REQ | Claude v6.2.21 | `Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/spec/ferum_custom_spec_v6_2_21.md:L1-L9`; `Вспомогательные/Codex ferum_custom/docs/requirements/requirements_catalog.md:L1-L8` |
| Contract root | Ferum Contract + Project Contract Link | project-centric contract fields | Owner decision + TARGET conflict resolution | `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract/ferum_contract.json#contract_number`; `Вспомогательные/Codex ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_project/ferum_service_project.json#contract_number` |
| Project Object | contract/effective dates/amendments | project/start/end/status | Claude after DB verification | `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_object/ferum_project_object.json#effective_from`; `Вспомогательные/Codex ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_object/ferum_project_object.json#start_date` |
| Project Scope SLA | hours/effective-dated/contract object | minutes/start-end/status | Claude after migration verification | `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_scope/ferum_project_scope.json#reaction_time_hours`; `Вспомогательные/Codex ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_scope/ferum_project_scope.json#reaction_time_minutes` |
| Workflow set | девять поставочных workflow | четыре более ранних workflow | Claude CODE | `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/fixtures/workflow.json:L1-L120`; `Вспомогательные/Codex ferum_custom/ferum_custom/fixtures/workflow.json:L1-L150` |

## Дельта к прежнему gap-analysis

Прежний документ остаётся полезным как семитемная декомпозиция и прямо объявляет себя ненормативным: `Вспомогательные/Claude ferum_custom/docs/analysis/gap_analysis_target_contract_structure_2026-08-17.md:L1-L15`.

Текущая версия:

- раскладывает TARGET на 557 независимо проверяемых строк с последовательными TCA-id;
- отделяет факты TARGET от полезных, но отсутствующих в TARGET архитектурных идей;
- использует детерминированное преобразование SPEC/CODE status → verdict;
- признаёт Ferum Project Scope семантическим носителем повторяющихся Contract Obligation: `Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/plan/owner_decisions_2026-08-17_target_structure.md:L85-L94`;
- сохраняет решение минимизировать физические BPM DocType и допускает child tables/type-step: `Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/plan/owner_decisions_2026-08-17_target_structure.md:L96-L105`;
- сохраняет приоритет Project Document до BPM либо в одной волне: `Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/plan/owner_decisions_2026-08-17_target_structure.md:L121-L134`;
- сохраняет Billing Basis как derived selection + immutable snapshot: `Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/plan/owner_decisions_2026-08-17_target_structure.md:L146-L164`;
- отделяет Contractor Assignment от pricing: `Вспомогательные/Claude ferum_custom/apps/ferum_custom/docs/plan/owner_decisions_2026-08-17_target_structure.md:L166-L176`.

## Итог

Матрица является discovery-реестром, а не утверждённой нормой или доказательством выполнения тестов. До разработки необходимо закрыть реальные TARGET↔SPEC конфликты, затем нормировать Project Document/Finding/Billing Basis и BPM Core. `07_traceability.csv` должен синхронизироваться отдельным шагом после принятия новой нумерации TCA.
