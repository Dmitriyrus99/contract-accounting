# 09. Отчёт верификации аналитического пакета

**Цель документа:** зафиксировать воспроизводимую самопроверку discovery-пакета, результаты Definition of Done, устранённые дефекты артефактов и границы доказательств.

**Дата анализа:** 2026-08-17. **Owner decisions синхронизированы:** 2026-08-18.

**Источник истины:** критерии исходного задания; TARGET — `Structure of the contract accounting system.md`; состав источников — [01_source_inventory.csv](01_source_inventory.csv); атомарные требования — [04_coverage_matrix.csv](04_coverage_matrix.csv); owner decisions/open gates — [08_open_questions.md](08_open_questions.md); поставка и приёмка — [07_traceability.csv](07_traceability.csv).

**Как проверить:** из корня `Codex 170826` повторить secret-safe обход с жёсткими исключениями, импортировать CSV RFC 4180 parser, разрешить ссылки относительно корня, выполнить статический Mermaid/Markdown audit и сопоставить результат с числами и SHA-256 ниже.

## 1. Итог

Все 12 требуемых артефактов присутствуют. Повторный обход нашёл тот же exact set из 1651 файлов: missing 0, stale 0, metadata mismatch 0. Матрица и трассировка содержат одинаковые 557 атомарных `req_id`, покрывают A-01…A-20 и B-01…B-39, не имеют дубликатов, пропусков внутри разделов или пустых обязательных ячеек.

Статус: **PASS для статической целостности аналитического пакета с перечисленными ниже runtime-ограничениями**. Это не означает готовность CODE, прохождение Frappe-тестов, миграций, permission tests, UAT, legal/privacy approval или deployment gates.

## 2. Контрольные числа

| Проверка | Результат |
| --- | --- |
| Файлы inventory / повторный обход | 1651 / 1651; missing 0; stale 0; metadata mismatch 0; duplicate path 0 |
| DocType Claude / Codex / union | 54 / 46 / 54; Claude-only 8 |
| Coverage requirements | 557: A — 261, B — 296 |
| Разделы TARGET | 59 из 59: A-01…A-20, B-01…B-39 |
| SPEC status | Covered 158; Partial 159; Absent 236; Contradicts 4 |
| CODE status | Implemented 150; Partial 145; Absent 262 |
| Verdict | OK 139; Gap-Code 19; Gap-Both 395; Conflict 4 |
| Severity | Critical 340; Major 78; Minor 139 |
| Priority / effort | Must 535; Should 22 / S 67; M 97; L 209; XL 184 |
| Trace status | Covered 150; Partial 145; Planned 262 |
| Пустые ячейки / неверные enum / formula mismatch | 0 / 0 / 0 |
| Дубликаты `req_id` / разница ID matrix↔trace | 0 / 0; порядок совпадает |
| Проверенные в пакете ссылки `:Lx-Ly` / ошибки | 1540 occurrences / 0 |
| Проверенные ссылки `.json#fieldname` / ошибки | 691 occurrences / 0 |
| Markdown heading/list/fence/opening defects | 0 / 0 / 0 / 0 |
| Неразрешимые относительные Markdown-ссылки | 0 |
| Mermaid blocks / static defects | 3 / 0 |
| Decision register | APPROVED 23; OPEN/BLOCKING 0; OPEN/UNKNOWN 0; manual/runtime gates 5 |
| UTF-8 BOM / bare LF в трёх CSV | отсутствует / отсутствует |

## 3. Контрольные суммы

| Файл | SHA-256 |
| --- | --- |
| TARGET | `0354d424f623753973101c2b8d30b6bc54fb0351572ef9269dbf60167b7617ac` |
| SPEC `v6.2.21` | `58872ee75e37b68d86f2cbf06b6a4c2b3ca0d6db87d37b4a6a13372cb7176e6d` |
| `01_source_inventory.csv` | `454058343f51e99abdc953628575da87817bbb9582e64f52ee6be7329359762e` |
| `04_coverage_matrix.csv` | `523c9df823e6f8a2da24de6dc396c66bd75b4e6a138f72f5eddc0f4cf0e3b0eb` |
| `07_traceability.csv` | `c87a9dab4bc1f0199b894e902ceb5c8a5d7190021a03f98d63a2ed721adfe984` |

CSV-хэши относятся к поставленной версии. Любое изменение требования, решения или критерия приёмки требует повторного вычисления и обновления этого отчёта.

## 4. Definition of Done

| Критерий | Статус | Доказательство проверки |
| --- | --- | --- |
| TARGET прочитан целиком; A-01…A-20 и B-01…B-39 представлены | PASS | TARGET: 2458 строк и зафиксированный SHA-256; parser matrix нашёл 59 разделов, missing 0 |
| Все DocType проинвентаризированы и классифицированы | PASS | Claude 54 и Codex 46; [01_source_inventory.md](01_source_inventory.md) содержит schema inventory, а раздел 2 [05_target_model.md](05_target_model.md) назначает действие всем 54 Claude DocType |
| Обе реализации исследованы; конфликты имеют источник истины | PASS | [04_gap_analysis.md](04_gap_analysis.md) отделяет TARGET, SPEC и CODE, содержит conflict registry и delta к прежнему анализу |
| Каждое утверждение AS-IS имеет проверяемую ссылку | PASS | Citation audit AS-IS документов плюс resolver: 1540 line-reference и 691 JSON-anchor occurrences, invalid 0; owner decisions и недоказанные runtime/manual факты разделены в [08_open_questions.md](08_open_questions.md) |
| Matrix атомарна и не имеет пустых verdict/severity/priority | PASS | 557 последовательных ID; duplicate 0; required empty 0; enum/formula mismatch 0 |
| Новые обязательные сущности перечислены и обоснованы | PASS | Obligation, Finding, Project Document, Contractor Assignment/Worker/Credential, Requirement, BPM Template/Stage/Step, Project Process/Stage/Step, Gate, Evidence и Inspection определены в [05_target_model.md](05_target_model.md) |
| Двойная статусная модель и матрицы переходов определены | PASS | OQ-CA-003 утверждает exact legal/execution enum, transition и cross-state matrices; исходное расхождение с TARGET/SPEC/CODE сохранено как traceable owner change-set, legacy `project_status` не считается целевым полем |
| Process Step покрывает сроки, conditions, evidence, gates, Waiting External, timeout, escalation, Not Applicable | PASS | Поля, enum, transition matrix и вычисление дат описаны в [05_target_model.md](05_target_model.md); OQ-CA-012 утверждает base status + derived Overdue |
| MVP определён и обоснован | PASS | MVP — `CA-00…CA-07`; сквозной критерий plan → fact → act → invoice → payment → margin находится в [06_roadmap.md](06_roadmap.md) |
| AS-IS и TO-BE Mermaid синтаксически валидны | PASS (static) | AS-IS: 82 declarations / 208 relations; TO-BE: 43 / 67; roadmap: 35 edges; undeclared node и invalid edge 0 |
| CSV парсятся; строки согласованы | PASS | Inventory 1651, matrix 557, traceability 557; matrix/trace имеют одинаковые ID, requirement, target_entity и verdict; acceptance structure defects 0 |
| Все owner/open решения находятся в `08_open_questions.md` | PASS | Все 23 OQ помечены APPROVED; OPEN=0; MG-CA-001/013/015/016/023 отделяют approval от manual/configuration/runtime evidence |
| Существующие файлы вне output не менялись и не удалялись | PASS | Exact inventory set/metadata совпал; Claude checkout остался `b1fcaac`, branch `w2-objects-core`, 46 предсуществовавших status entries; Codex — `c97c34a`, `codex/final-qualification`, clean |
| Отчёт содержит результат всего checklist | PASS | Настоящий раздел покрывает каждый пункт Definition of Done |

## 5. Методика машинной проверки

1. Выполнен повторный recursive walk `<ROOT>` с исключением `.git`, caches, `*venv*`, `node_modules`, `site-packages`, `dist`, `build`, временных каталогов и `contract-accounting`; exact path/size/UTC mtime сравнивались с inventory.

2. Три CSV импортированы как RFC 4180 UTF-8 без BOM; проверены headers, число строк/колонок, CRLF, уникальность и непрерывность `req_id`, обязательные поля, enum, детерминированная формула verdict и синхронность matrix↔trace.

3. Каждая распознанная ссылка `путь:Lx-Ly` проверена на существование файла и границы строк. Каждый `.json#fieldname` проверен JSON parser по top-level properties и `fields[].fieldname`.

4. Markdown проверен на обязательный opening block, пустую строку после heading и перед первым list item, баланс fences и существование относительных ссылок.

5. Mermaid проверен статически: directive, fences, entity declarations, relationship endpoints и flowchart edges. Внешний `mmdc` render не выполнялся, поэтому PNG/SVG validation не заявляется.

6. Схемы Claude повторно сопоставлены с 54 строками AS-IS field extraction; TO-BE section 2 проверен на упоминание каждого из 54 DocType. Git status обоих checkout проверен через WSL до и после работы.

## 6. Найденные и устранённые дефекты артефактов

| Дефект | Исправление | Повторная проверка |
| --- | --- | --- |
| Первая матрица объединяла несколько независимых норм в 211 строк | TARGET повторно декомпозирован до 557 атомарных требований с непрерывными ID и детерминированными verdict | 59 sections; sequence/formula/duplicate audit — PASS |
| Knowledge base и AS-IS не полностью раскрывали 54 schemas, hooks/scheduler/permission hooks и ERPNext links | Добавлены 54/54 typed schemas, 40 status fields, runtime hooks и 111 standard/dynamic links; наличие теста отделено от test result | Schema/link/citation audit — PASS |
| TO-BE сохранял отдельный `Ferum Contract` как постоянный SSOT вопреки корню TARGET | `Ferum Service Project` закреплён единым legal/execution root; Contract/Link — read-only migration provenance, N:M — quarantine | Root terminology, target_entity и migration acceptance audit — PASS |
| Для части существующих DocType отсутствовало явное TO-BE действие | Раздел 2 расширен до всех 54 Claude DocType с action, links, field types, naming и roles | 54/54 name coverage — PASS |
| Finding/Defect, BPM topology, Gate cardinality и Overdue трактовались по-разному | Утверждены один `Ferum Finding(category=Defect)`, parent BPM topology, reverse multiple gates и base status + derived Overdue | Model/roadmap/trace/decision cross-audit — PASS |
| ER ошибочно делал альтернативные sources/holders одновременно обязательными | Visit/Inspection, Employee/Contractor Worker, template/requirement/event переведены в optional cardinality с server-side XOR/exactly-one invariants | Mermaid declaration/cardinality audit — PASS |
| Contractor Worker, credentials и passport privacy не имели полноценного delivery gate | Утверждена Worker/Credential topology; protected production data и PERSONNEL READY блокирует отдельный MG-CA-015 evidence gate | Roadmap/trace/privacy cross-audit — PASS |
| Owner approval мог быть ошибочно истолкован как implementation/runtime PASS | Утверждены 23 OQ; 5 manual/configuration/runtime gates оставлены без PASS, Import Batch — RUNTIME NOT EVIDENCED | Decision/status/count/gate audit — PASS |
| Traceability содержала формально структурированные, но непредметные acceptance templates | Уточнены cardinality, Amendment, MVP granularity, photo evidence, Inspection emissions, BPM fields, personnel gate, technology neutrality и derived Overdue; убраны ложные обязательные links | 557 критериев содержат precondition/action/expected; cross-artifact audit — PASS |
| Payment Entry и несколько target fields ссылались на неверную физическую модель | Использован standard Payment Entry Reference; `execution_status`, `supplier`, `project_object`, точные BPM fields и migration-only Contract provenance синхронизированы | Target entity matrix↔trace mismatch 0 |

## 7. Ограничения и честный статус

В discovery не запускались Frappe/ERPNext tests, `bench migrate`, database reconciliation, permission tests, UAT, legal/privacy review или deployment. Owner approval от 2026-08-18 утверждает архитектурные рекомендации, но не является CODE, test, migration, legal/privacy или MG evidence. Наличие test-файла означает только `test present`, а не PASS.

Mermaid прошёл статическую проверку, но не был отрендерен внешним CLI. Перед публикацией диаграмм нужен `mmdc` render в CI или эквивалентном воспроизводимом окружении.

Claude CODE был dirty до начала анализа. Поэтому [03_asis_model.md](03_asis_model.md) описывает наблюдавшийся working tree, а не утверждённый release baseline. `CA-00` обязан зафиксировать commit/diff/schema snapshot и закрыть W2/DB/manual evidence до разработки.
