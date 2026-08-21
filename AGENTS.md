# AGENTS.md — проектный профиль для `contract_accounting`

## 1) Роль и цель
`AGENTS.md` — обязательная иерархия правил для всех сессий Codex в каталоге `contract-accounting`.

## 2) Источники и приоритеты (в порядке силы)
1) Release решения: `11_release_decisions_v1.md`.
2) ADR из `implementation/CA-00/`: в первую очередь `ADR-CA-0001-erpnext-custom-party-boundary.md`, `ADR-CA-0002-business-replacement-technical-standalone.md`, плюс другие ADR по затронутой области.
3) TARGET/Scope: `00_INDEX.md`, `05_target_model.md`, `06_roadmap.md`, `12_release_scope_v1.md`, `12_release_scope_matrix_v1.csv`, `13_first_release_backlog_v1.md`.
4) Открытые вопросы и вопросы исполнения: `08_open_questions.md`, `10_remaining_questions_and_actions.md`, `15_first_stage_completion_sequence.md`.
5) Quality/DoD evidence: `14_quality_profile_v1.md`, `09_verification_report.md`, соответствующие `implementation/CA-*/` traceability и runtime-лог.
6) Доходящая документация из `implementation/CA-00` и ниже по инкременту задачи.

## 3) Базовая дисциплина работы
1) Перед изменениями прочитать `11_release_decisions_v1.md`.
2) Перед изменениями прочитать `00_INDEX.md` как текущий status baseline.
3) Перед изменениями прочитать релевантные ADR.
4) Перед изменениями прочитать roadmap/backlog (`06_roadmap.md` и/или `13_first_release_backlog_v1.md`).
5) Перед изменениями прочитать релевантный `implementation/CA-*/README.md`.
6) Если меняется код, прочитать соответствующий `implementation/CA-*/traceability_*.md`.
7) При конфликте требований остановить задачу и зафиксировать уточнение вопроса для владельца.
8) При разрыве между нормой и фактом CODE не редактировать норму; корректировать только профильные документы и evidence.

## 4) Что запрещено без отдельного разрешения
1) Менять ADR и уже утвержденные release решения без change request.
2) Реализовывать функционал с открытыми зависимостями MG/DP без их закрытия в рамках задачи.
3) Игнорировать open gates privacy, RBAC, backup и rollback.
4) Предъявлять непроверенные проверки как выполненные.
5) Читать, копировать или передавать live credentials, реальные пароли или приватные секреты.

## 5) Как работать с рисками и неясностями
1) `OWNER BLOCKED` использовать только когда утверждённого DP/OQ/ADR/owner decision нет или требуется change control.
2) `EVIDENCE GATE OPEN` использовать когда решение утверждено, но не закрыты CODE/configuration/legal/RBAC/performance/UAT/restore/deployment proofs.
3) `IMPLEMENTATION BLOCKED` использовать когда approved scope есть, но зависимость в коде, окружении или данных не позволяет выполнить задачу.
4) Требования со статусами `OPEN`, `PARTIAL` или `NOT READY` считаются условными и требуют доказательного этапа.
5) Любую неочевидную предпосылку фиксировать как явное допущение.

## 6) Техдисциплина (код)
1) Соблюдать стандартные границы приложения и минимальные surface changes.
2) При работе с сервером/DB использовать Frappe ORM/Query Builder.
3) `ignore_permissions=True` допускается только с узко описанным approved exception, ссылкой на DP/OQ/ADR/task waiver, минимальным scope, negative permission tests и traceability.
4) Любые изменения безопасности, finance, permissions, migration, restore требуют отдельного evidence-флоу.
5) Обновление трассируемости требуется для каждого требования, чей код меняется.

## 7) Текущая политика сессий и границы
1) Не использовать автоподписывание готовности; финальное подтверждение — отдельная сессия приёмки.
2) Для крупных задач использовать модель: имплементация -> подготовка evidence -> отдельная сессия review -> отдельная сессия acceptance.
3) Не выполнять production/restore действия без явного операционного плана владельца.

## 8) Стандарты окружения
1) Bench/WSL-команды запускать через WSL, если это рабочая практика проекта.
2) Для `contract_accounting` не изменять shared-runtime с `ferum_custom` без ADR и DP подтверждений.
3) Любая работа с конфиденциальной информацией выполняется по минимуму, без раскрытия секретов.

## 9) Обязательные проверки для кодовых задач
1) Сформировать и зафиксировать impacted DP/OQ/ADR и scope in/out.
2) Зафиксировать план evidence и команды проверки.
3) Не объявлять PASS для неполных или неисполненных проверок.
