# CA-14 work-queue and Launch projection contract — v0.15.0

**Статус:** `READ-ONLY PROJECTIONS BENCH VERIFIED AT 48e1502`.

## SSOT boundary

| Представление | Источники | Запрещённое дублирование |
| --- | --- | --- |
| My Actions | Process Step, own standard ToDo, assigned Service Request/Maintenance Visit, owned Project Document | отдельный Ferum Task/queue/cache DocType не создаётся |
| Project Launches | Service Project, Launch Process/Stage/Step/Gate, Requirement assessment, Contractor Assignment | progress/flags/blockers не сохраняются в Service Project |
| Service Project Launch tab | тот же exact `get_project_launch_view` | клиент не рассчитывает отдельное состояние процесса |

Process Step имеет `source_rank=0` и побеждает его ToDo delivery row. Все ToDo того же source объединяются в `delivery_todos`; canonical key равен `source_doctype:source_name`. `Planned`, terminal и недоступные source/project records не попадают в My Actions.

## My Actions classification

`classify_action` независимо возвращает:

- `time_bucket`: Overdue, Today, Upcoming или Unscheduled;
- `state_bucket`: Blocked, Waiting External, Waiting Approval или Actionable;
- `is_overdue`, stable `time_rank/state_rank`.

Stable ordering: time rank → state rank → due timestamp → Service Project → canonical source key. Explicit `as_of` используется в тестах и API для воспроизводимой классификации; в Desk по умолчанию применяется site-local `now_datetime`.

API всегда использует текущего session user. Кандидаты выбираются только по own ToDo/source owner/responsible user либо unassigned responsible role, после чего отдельно проверяются read permission исходного документа и Service Project. Произвольный `user` parameter отсутствует.

## Launch projection

В очередь входят readable Service Project со статусами Approved/Signing/Signed/In Force и Not Started/Launching. Для каждого проекта возвращаются:

- identity/status/project manager и exact Service Project drill-down;
- Requirement Assessment readiness;
- один latest Launch Process;
- ordered stages, progress, раскрываемые steps/status/due/warning/escalation;
- Stage Gate status и parsed failed criteria;
- flags overdue, blocked, missing contractor, waiting customer, missing credentials;
- concrete blocking conditions с source drill-down.

Generation CTA считается eligible только при Published `FERUM-LAUNCH` v1, завершённом Requirement Assessment, допустимой dual-status pair и отсутствии Launch Process. CA-14 UI не создаёт process автоматически и не реконструирует history.

## Честная семантика исключений

- `blocked`: Failed Gate, Blocked Step или незавершённый Requirement Assessment;
- `missing_contractor`: открыт `EXEC_CONTRACTOR_DOCS`, но Approved Contractor Assignment не найден; это «not confirmed», потому что отдельного `contractor_required` SSOT пока нет;
- `waiting_customer`: Waiting External только для customer/mobilization/customer-send codes reference graph;
- `missing_credentials`: открыт `PERSONNEL_READY`; condition всегда содержит `MG-CA-015`, пока production personnel evidence запрещено.

Эти flags — derived read model. Они не изменяют Process Step, Gate, Assignment или Service Project.

## Navigation

Каждая action/stage/step/gate/project row содержит exact DocType/name route и return context с route/filter values. Desk сохраняет context в `sessionStorage` перед переходом; browser/UAT сохранения состояния при back navigation остаётся отдельным manual gate.
