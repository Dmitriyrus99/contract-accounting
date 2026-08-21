---
name: ferum-domain-modeling
description: A ferum-specific skill profile adaptation for contract_accounting. This skill adds required process checks and project-specific constraints.
---

# ferum-domain-modeling

## Purpose
Обновлять предметную модель только в рамках утвержденных границ, без создания альтернативной терминологии.

## Scope
1) `03_asis_model.md`, `05_target_model.md`, релевантные ADR и FR-решения.
2) `implementation/CA-*/traceability_*.md`.
3) Ключевые Doctype/Workflows в `contract_accounting/`.

## Workflow
1) Проверить существующий термин из источников DP/ADR.
2) Сопоставить его с кодовой моделью.
3) Указать, где отклонение уже нормировано, а где требует решения.
4) Зафиксировать изменения только в документах traceability/implementation plan.

## Contract-specific rule
Любой новый термин без отражения в 00_INDEX и acceptance-пакете считается draft и не должен влиять на API-соглашения.

## Output
1) Ясный словарь изменений.
2) Список обязательных проверок для domain invariants.
