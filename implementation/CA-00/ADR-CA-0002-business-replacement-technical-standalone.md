# ADR-CA-0002 — business replacement / technical standalone

**Статус:** `APPROVED`.

**Дата решения:** 2026-08-19.

**Владельцы решения:** Product Owner, Solution Architect, Release Manager.

**Источник:** [Release Decisions v1](../../11_release_decisions_v1.md), `DP-01` и `DP-02`.

## Контекст

`ferum_custom` и новое `contract_accounting` не должны одновременно владеть одинаковыми custom DocType, hooks, fixtures, patches или runtime behavior. Legacy business data признаны тестовыми и не требуют переноса. Поэтому coexistence, merge и shared-schema создают риск двойного SSOT без бизнес-необходимости.

## Решение

`contract_accounting` функционально заменяет `ferum_custom`, но технически остаётся самостоятельным Frappe-приложением.

Новый Staging/Production:

- создаётся в чистом изолированном окружении;
- содержит Frappe, ERPNext и `contract_accounting` утверждённых версий;
- не устанавливает `ferum_custom`;
- не использует его code, hooks, patches, fixtures, Custom Fields, custom DocType, database или runtime integration;
- оставляет ERPNext владельцем стандартных master/accounting entities;
- оставляет `contract_accounting` владельцем всех custom domain entities.

Business records из legacy не мигрируются. Initial production data вводятся заново; legacy database copy запрещена.

## Последствия

Положительные:

- один owner custom schema и runtime behavior;
- исключены collision/install-order и hidden dependency risks;
- clean install/restore/release можно квалифицировать независимо;
- MG-CA-001 становится N/A после доказательства `0` real business records.

Обязательные работы:

- получить installed-app list нового сайта и collision report;
- зафиксировать baseline/tag/manifest;
- подписать legacy inventory и создать контрольный backup;
- держать `ferum_custom` read-only до production sign-off;
- после sign-off архивировать или удалить legacy environment отдельной контролируемой операцией.

## Отклонённые варианты

- **Merge into `ferum_custom`:** сохраняет старое schema ownership и противоречит решению о самостоятельной целевой системе.
- **Coexistence:** создаёт двойной runtime/SSOT и не имеет утверждённого use case.
- **Shared database/schema:** не обеспечивает независимый rollback и collision-free deployment.

## Критерии подтверждения

ADR фиксирует архитектурное решение, но не закрывает deployment gate. Техническое подтверждение требует:

1. `bench --site <site> list-apps` без `ferum_custom`.
2. Inventory custom DocType/Custom Field/hooks/patches/fixtures без конфликтующего owner.
3. Fresh install и repeated migrate `contract_accounting` на approved Frappe/ERPNext versions.
4. Signed legacy inventory, backup и `MG-CA-001=N/A` act.
5. Staging/production evidence по [Release Decisions v1](../../11_release_decisions_v1.md), `DP-17`.
