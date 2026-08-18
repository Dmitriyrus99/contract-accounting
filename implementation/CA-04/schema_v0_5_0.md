# CA-04 schema evidence — v0.5.0

**Статус:** `STATIC + BENCH RUNTIME VERIFIED AT 5bc0bc9`.

**Дата:** 2026-08-18.

## Физическая модель

| DocType | Тип | Назначение |
| --- | --- | --- |
| `Ferum Finding` | parent | самостоятельный обнаруженный факт с confirmation/resolution lifecycle |
| `Ferum Finding Execution Link` | child | idempotent provenance на разрешённое исполнение |
| `Ferum Photo Evidence` | parent | source-bound фотофиксация, review и hash стандартного File |

После clean install приложение содержит 21 custom DocType. Отдельного `Ferum Defect` и второго File/Work Order SSOT нет.

## Finding provenance и lifecycle

`source_doctype/source_name` — Dynamic Link с server allowlist `Ferum Maintenance Visit` и будущий `Ferum Inspection`. Source обязан существовать и быть доступен на чтение. Service Project, Project Object, Service Object и Object System выводятся из source, сохраняются в `detected_context_snapshot` и становятся неизменяемыми вместе с found actor/time.

Категория обязательна и ограничена точным набором `Observation / Defect / Nonconformity / Risk`. Confirmation FSM: `Pending → Confirmed|Rejected`. Resolution FSM: `Open → In Resolution|Resolved|Rejected`, `In Resolution → Resolved`, `Resolved → In Resolution|Closed`.

Confirmed требует decision (`Fix Under Contract / Additional Work / Notify Customer / Monitor`), responsible и due date. Resolved/Closed требует resolution class/text, server actor/time и generic File evidence либо Accepted `Ferum Photo Evidence`. Closed/Rejected полностью immutable; confirmed classification также immutable.

## Execution links и отчёт

Child link хранит Dynamic Link, relation type и обязательный source event key. Физические unique keys:

- `(parent, source_event_key)`;
- `(parent, target_doctype, target_name)`.

Текущий target allowlist содержит только `Ferum Service Request`. API блокирует Finding `FOR UPDATE`, повторный event key возвращает ту же связь, а foreign project/object/system и неразрешённый DocType отклоняются. Явная команда создания Service Request выводит контекст из Finding и не изменяет source snapshot.

Read-only exception report вычисляет, а не хранит как stale status, флаги `open_critical`, `overdue` и `without_decision`.

## Photo Evidence

`Ferum Photo Evidence` разрешает source Visit/Service Request/Finding и будущий Inspection. Контекст выводится из source. Поле `file` — Link на стандартный `File`; controller требует, чтобы File был физически прикреплён к source, и копирует его `content_hash` в read-only поле.

Review FSM: `Pending → Accepted|Rejected`, `Rejected → Pending`. Review actor/time выставляются сервером; Accepted запись immutable и может удовлетворить Finding resolution/close evidence gate.

## Не закрыто этой схемой

- фактический Inspection source и auto-generation Findings/Photo Evidence — CA-12;
- approved work-order adapter — OPEN до отдельного owner/CA-00 решения;
- assigned-contractor/customer portal row-level permissions — CA-08;
- legacy Service Request candidate report/manual conversion — не запускались, legacy data на disposable site отсутствуют;
- UAT, legal/operations sign-off, production deployment и concurrent load test не выполнялись.
