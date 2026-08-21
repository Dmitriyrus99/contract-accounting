# CA-09 — derived deadline timeline

**Статус:** `CA-09 / FR-03 / FR-04 PARTIAL — CALENDAR + NOTIFICATION DELIVERY ENGINEERING v0.19.0 BENCH VERIFIED; PRODUCTION OPERATIONS И FR-08 GATES OPEN`.

Инкремент не создаёт `Ferum Deadline` или `Ferum Contract Milestone` и не копирует контрольные даты в новый SSOT. Read-only API [deadlines.py](../../contract_accounting/api/deadlines.py) собирает нормализованные строки непосредственно из Service Project, Maintenance Schedule, Service Request, Execution Stage, Contract Security, Project Document, Finding и submitted Sales Invoice. Каждая строка содержит `source_doctype`, `source_name`, `source_field`, стабильный `source_key`, owner, исходный status и дату; повторный вызов полностью перестраивает projection.

Pure domain engine [deadline.py](../../contract_accounting/domain/deadline.py) рассчитывает due/warning/escalation timestamps только при явных trigger, timezone, calendar revision, Holiday List snapshot, cut-off policy и offsets. Неизвестный trigger или timezone отклоняется. Calculation hash зависит от полного immutable input/result snapshot.

В исходном v0.10.0 production configuration `MG-CA-013` отсутствовала: обычный API возвращал source dates без Company-calendar readiness, а warning/escalation projection оставалась выключенной. Эта историческая граница сохранена в [projection v0.10.0](projection_v0_10_0.md), [runtime evidence v0.10.0](runtime_evidence_v0_10_0_2026-08-18.md) и [traceability v0.10.0](traceability_v0_10_0.md).

Продолжение v0.18.0 добавляет source-controlled `RU-5D-2026-v1`, Company/Contract assignment precedence, immutable Calendar Calculation history, signature deadline в Project Document и structured Customer Response source в External Dependency. Code/configuration часть `MG-CA-013` подтверждена; site-specific assignment, annual Operations procedure и manual qualification остаются OPEN.

Продолжение v0.19.0 добавляет fail-closed notification activation, все DP-06 thresholds, calendar-timezone digest, standard Notification Log/Email Queue, deterministic idempotency, retry/dead-letter и terminal-source exclusion. Production activation и внешний SMTP receipt не выполнялись.

- Design и граница: [production_calendar_v0_18_0.md](production_calendar_v0_18_0.md).
- Runtime evidence: [runtime_evidence_v0_18_0_2026-08-19.md](runtime_evidence_v0_18_0_2026-08-19.md).
- Current traceability override: [traceability_v0_18_0_calendar.md](traceability_v0_18_0_calendar.md).
- Notification delivery design: [notification_delivery_v0_19_0.md](notification_delivery_v0_19_0.md).
- Notification runtime evidence: [runtime_evidence_v0_19_0_2026-08-19.md](runtime_evidence_v0_19_0_2026-08-19.md).
- Notification traceability: [traceability_v0_19_0_notifications.md](traceability_v0_19_0_notifications.md).

## Подтверждённые проверки v0.18.0

- source-controlled fixture: `247 working / 118 non-working / 4 shortened`, deterministic hash;
- targeted calendar acceptance `4/4 OK` и existing timeline regression `3/3 OK`;
- повторный migrate, app build и foreground full-app suite `83/83 OK`;
- runtime inventory: 55 DocType, включая Calendar Revision/Assignment/Calculation и External Dependency;
- обязательные строки release matrix `TCA-A-14-09/13` переведены из `Absent` в `Implemented`; общий mandatory `Absent=0`.

## Подтверждённые проверки v0.19.0

- standalone/schema `161/161 OK`, targeted FR-04 `6/6 OK`, full Frappe `89/89 OK`;
- runtime inventory: 58 DocType;
- real local `Notification Log` и delayed `Email Queue`, deterministic Message-ID и queue reconciliation;
- overdue/+1 director escalation, daily 09:00 digest, closed exclusion, retry/dead-letter и typed retry;
- notification settings после acceptance оставлены `enabled=0`.

## Открытая граница

Не закрыты фактическое назначение календаря и notification activation на approved site, ежегодное обновление revision, outgoing Email Account/SMTP receipt/bounce, scheduler worker heartbeat, полный lifecycle External Dependency FR-08, общий warranty deadline вне Security, representative-volume latency/race, browser/RBAC UAT, sign-off и production deployment. Значения из текста или неструктурированных условий не угадываются.
