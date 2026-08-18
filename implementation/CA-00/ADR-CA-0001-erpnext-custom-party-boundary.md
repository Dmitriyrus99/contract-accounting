# ADR-CA-0001. Граница ERPNext/custom и владение Party Identity

- **Статус:** `Accepted for TARGET`; implementation delta — `PENDING CA-01/CA-15`
- **Дата решения:** 2026-08-18
- **Основание:** OQ-CA-001, OQ-CA-002, OQ-CA-017 и OQ-CA-018 в [08_open_questions.md](../../08_open_questions.md)

## Контекст

CA-00 должен зафиксировать границу источников истины до изменения schema и данных. Текущий CODE и утверждённый TARGET различаются: dirty W2 реализует юридический SSOT в `Ferum Contract`, а TARGET переводит юридический и execution root в один `Ferum Service Project`. Это различие является migration delta для CA-01, а не основанием смешивать две модели в baseline.

## Решение

| Область | Авторитетный источник | Роль custom layer |
| --- | --- | --- |
| Customer/Supplier/Company | стандартные ERPNext masters | ссылки, reconciliation и domain extensions без второго master |
| Cross-master identity | `Ferum Party Identity` только для identifiers, linkage, duplicate/reconciliation state и provenance | не сторона бухгалтерского документа и не замена Customer/Supplier/Company |
| Исполняемый договор в TARGET | `Ferum Service Project` | единый legal + execution root после контролируемого CA-01 cutover |
| Legacy `Ferum Contract`/Project Contract Link | migration provenance | read-only до cutover, затем retirement/archive по отдельному gate |
| Sales/Purchase Invoice, Payment Entry, Account, GL Entry | ERPNext | custom слой читает, связывает и строит rebuildable read-model; не пишет альтернативный ledger или correction GL |
| File/Communication/Assignment/ToDo | стандартная инфраструктура | domain metadata/projection без дублирования physical file или task SSOT |
| Налоговые Account mappings | ERPNext Account + `Ferum Company Tax Account` configuration | purposes `Output VAT` и `Input VAT`; не налоговый ledger |

Для `Ferum Party Identity` действуют дополнительные инварианты:

1. Create/link идемпотентен.
2. Неоднозначные организации автоматически не объединяются.
3. Произвольная двусторонняя синхронизация business fields запрещена.
4. Расхождение разрешается explicit reconciliation workflow или отдельно утверждённым односторонним field rule.
5. Финансовые документы продолжают ссылаться на Customer/Supplier/Company, а не на Party Identity.

## Последствия

- CA-01 обязан явно перевести schema links на Service Project root и доказать отсутствие второго Contract SSOT.
- CA-07/CA-15 обязаны статически и runtime доказать отсутствие custom GL writers.
- Party Identity reconciliation получает отдельные idempotency/no-ambiguous-merge тесты.
- Этот ADR не является доказательством cutover, live schema или миграции; соответствующие MG gates остаются OPEN.
