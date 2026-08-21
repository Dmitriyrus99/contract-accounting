# FR-04 — scheduler, reminders, escalation and digest v0.19.0

**Статус:** `ENGINEERING BOUNDARY PASS / FAIL-CLOSED ACTIVATION / OPERATIONS AND EXTERNAL DELIVERY GATES OPEN`.

## Решение

FR-04 публикует события поверх primary deadline sources из CA-09 и не создаёт второй SSOT срока. `Ferum Notification Delivery` хранит только immutable identity/payload и состояние транспорта; source deadline остаётся в исходном документе и, где применимо, в append-only `Ferum Deadline Calculation`.

Scheduler по умолчанию выключен. `Ferum Notification Settings` активируется только POST-командой System Manager с причиной и новым `activated_at`; события до watermark не рассылаются. Повторная активация создаёт новый watermark и не запускает историческую рассылку за период отключения.

## DP-06 timing

| Событие | Получатели | Каналы |
|---|---|---|
| `MINUS_3` | ответственный + Project Manager | individual in-app + email digest |
| `MINUS_1` | ответственный + Project Manager | in-app + email |
| `DUE_0800` | ответственный + Project Manager | in-app + email |
| `OVERDUE` | ответственный + Project Manager + роль `Владелец процесса` | in-app + email |
| `OVERDUE_PLUS_1` | роль `Генеральный директор` | in-app + email |
| после `OVERDUE_PLUS_1` | ответственные и руководители | in-app/email digest ежедневно в 09:00 календарной timezone |

Если фиксированный `MINUS_3` уже не предшествует immutable trigger, срок считается коротким без отдельного owner-defined порога: неприменимые `−3/−1/due-08` заменяются `SHORT_50`, `SHORT_80` и `BREACH`. Это алгоритмическая проверка применимости утверждённых порогов, а не новая бизнес-классификация.

Cron вызывает delivery и digest каждые 15 минут. Digest публикуется только внутри `09:00–09:14` timezone назначенного Company/Contract Calendar, поэтому site timezone не подменяет договорную timezone.

## Idempotency и транспорт

- correlation key включает source key, due datetime, threshold, recipient, policy version и daily occurrence date;
- delivery key дополнительно включает channel и является физическим именем/unique key;
- изменение due date создаёт новый correlation key; простой retry не создаёт новый delivery;
- in-app создаёт стандартный `Notification Log`;
- email создаёт delayed стандартный `Email Queue` с детерминированным Message-ID;
- digest membership хранится typed child rows и совпадает с immutable payload hash;
- recipient обязан иметь read permission одновременно на Service Project и source document;
- closed/cancelled/terminal sources исключаются timeline projection до создания delivery.

## Retry и dead-letter

Email delivery получает состояния `Pending → Processing → Queued → Sent`. Ошибка queue/backend переводит запись в `Retry` с задержками 5/30/120 минут; после configured maximum attempts — в `Dead Letter`. Ручной повтор разрешён только System Manager POST-командой с причиной. Переходы, identity, payload, digest items и удаление защищены server-side.

## Открытая граница

Не закрыты production activation, approved outgoing Email Account, SMTP provider receipt/bounce, scheduler heartbeat/worker supervision, representative-volume concurrency, browser/RBAC/Operations UAT и sign-off. Локальный delayed Email Queue доказывает постановку в стандартный транспорт, но не внешнюю доставку письма адресату.
