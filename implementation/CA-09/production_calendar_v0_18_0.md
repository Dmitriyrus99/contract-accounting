# Production calendar boundary v0.18.0

Дата: 2026-08-19. Решение реализует утверждённый `DP-05`, не создавая второй editable Deadline SSOT.

## Модель

- `Ferum Calendar Revision` — неизменяемая опубликованная годовая конфигурация; child `Ferum Calendar Day` хранит только исключения к пятидневной неделе.
- `Ferum Calendar Assignment` — append-preserving назначение Company или явного Contract override. Contract требует текст договорной нормы и Project Document evidence; выбор выполняется `Contract → Company`.
- `Ferum Deadline Calculation` — append-only снимок source datetime, normalized 08:00 anchor, rule, calendar ID/revision/hash, cut-off, результата и `dp05-v1`; ручной пересчёт требует роли, причины и ссылки `supersedes`.
- Первичный срок подписания остаётся в `Ferum Project Document.signature_due_at`; срок ответа заказчика — в отдельном `Ferum External Dependency.due_at`. Timeline только читает эти источники.

## Fixture 2026

`contract_accounting/setup/calendar_fixtures/ru_5d_2026_v1.json` фиксирует `Europe/Moscow`, окно `08:00–19:00`, 18 праздничных/перенесённых дат и четыре сокращённых дня. Runtime verification подтверждает 247 рабочих, 118 нерабочих и 4 сокращённых дня; SHA-256 канонической календарной конфигурации — `56691dc76841c9ef33550cec0539c82010f1e1277055c5f2ffdfec029744d917`.

Нормативное основание: [постановление Правительства РФ от 24.09.2025 № 1466](https://publication.pravo.gov.ru/document/0001202509240023). Контрольная раскладка пятидневной недели и четырёх сокращённых дней сверена с [производственным календарём 2026](https://www.consultant.ru/law/ref/calendar/proizvodstvennye/).

## Fail-closed правила

- отсутствующее назначение на год, hash mismatch, выход за valid range или неизвестная timezone блокируют расчёт;
- событие до 08:00 нормализуется к 08:00 текущего рабочего дня, после cut-off и в нерабочий день — к 08:00 следующего рабочего дня;
- нерабочая due date переносится вперёд, сокращённый день ограничивает due фактическим окончанием рабочего окна;
- опубликованная revision, assignment history и calculation event не удаляются и не переписываются;
- новая revision не пересчитывает старые сроки автоматически.
