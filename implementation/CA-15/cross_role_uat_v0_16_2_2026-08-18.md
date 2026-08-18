# CA-15 v0.16.2 Operations cross-role UAT — 2026-08-18

**Вердикт:** `PASS FOR ENGINEER / ACCOUNTANT / OFFICE MANAGER / PROJECT LEAD OPERATIONS SLICE; CA-15 REMAINS PARTIAL`.

Реальный headless Chrome через Playwright проверил standard Page `ferum-operations` на disposable Frappe/ERPNext v15 site `ca01.localhost`. Использованы отдельные временные System User с одной business role; после UAT пользователи отключены. Проверочный проект `FSP-2026-00001` содержал назначенный Engineer Service Request и по одному owned Project Document для Accountant и Office Manager.

## Что изменено

- Page «Операционная работа» разрешена System Manager, Владельцу процесса, Руководителю проектов, Менеджеру проектов, Инженеру, Бухгалтеру и Офис-менеджеру;
- `get_operations_capabilities` возвращает server-authoritative `launch_control`; клиент не вызывает запрещённый Launch API для non-launch roles;
- Engineer и Office Manager получили только base-level `read/report` на Service Project, без create/write/delete/export и без higher-permlevel полей;
- project-level query/has-permission boundary разрешает Engineer только проекты с его Object/Request/Visit/Process Step или незанятым role-step, Office Manager — с owned Project Document/Process Step; неизвестная роль получает `1=0`;
- Contractor не добавлен в Page: portal UAT и positive credential gate MG-CA-015 остаются блокирующими.

## Ролевая матрица

| Роль | Operations | Launch card/API | Дополнительная граница | Вердикт |
| --- | --- | --- | --- | --- |
| Инженер | `Мои действия = 1` для назначенного Request | `Restricted`; runtime Launch API = PermissionError | чужой Service Project не читается; Director Control = Not permitted | PASS |
| Бухгалтер | `Мои действия = 1` для owned Project Document | `Restricted` | Contract 360° Page доступна | PASS для Page slice |
| Офис-менеджер | `Мои действия = 1` для owned Project Document | `Restricted` | Contract 360° = Not permitted | PASS |
| Руководитель проектов | Operations доступна; отдельная My Actions очередь пуста на fixture | Launch/Blocked KPI доступны | Director Control доступен, `Projects = 1` | PASS |

Скриншоты:

- [Engineer Operations](../../output/playwright/ca15-v0.16.2-engineer-operations.png);
- [Accountant Operations](../../output/playwright/ca15-v0.16.2-accountant-operations.png);
- [Office Manager Operations](../../output/playwright/ca15-v0.16.2-office-operations.png);
- [Project Lead Operations](../../output/playwright/ca15-v0.16.2-project-lead-operations.png);
- [Project Lead Director Control](../../output/playwright/ca15-v0.16.2-project-lead-director-control.png).

## Квалификация final tree

- repeated `bench --site ca01.localhost migrate`: PASS;
- targeted Workspaces Frappe suite: `2/2`, `OK`;
- standalone suite: `136/136`, `OK`;
- full-app Frappe suite with `--skip-test-records`: `69/69`, `OK`, `334.096 s`;
- `bench build --app contract_accounting`: PASS, esbuild `340.252 ms`;
- PEP 517 wheel: `contract_accounting-0.16.2-py3-none-any.whl`, `307,455` bytes;
- scoped Ruff, Page JSON parse, JS syntax and `git diff --check`: PASS.

Доступные Pages не дали product JavaScript exceptions. Повторяющиеся Socket.IO polling 404 относятся к прямому `bench serve` без reverse proxy; deliberate negative Page checks дают ожидаемый 403/Not permitted.

## Открытая граница

Не проверены Contractor/customer portal, Lawyer/Process Owner/System Manager browser slices, API export/report matrix, confidential-document scenarios, representative-volume performance/load/race, scheduler/retry topology, migration/cutover/rollback rehearsal, legal retention/sign-off и production deployment. Contractor workspace остаётся `BLOCKED_PENDING_PORTAL_UAT_AND_MG-CA-015`; blanket acceptance не присваивается.
