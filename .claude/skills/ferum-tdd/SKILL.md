---
name: ferum-tdd
description: A ferum-specific skill profile adaptation for contract_accounting. This skill adds required process checks and project-specific constraints.
---

# ferum-tdd

## Purpose
Только тестирование наблюдаемого поведения из утвержденных требований и инкрементальная проверка.

## Scope
1) Любой новый или измененный `contract_accounting` код.
2) Привязка к конкретным DP/OQ/REQ-ID.
3) Требования из `implementation/CA-*/traceability_*.md` и quality profile.

## Method
1) Сформировать наблюдаемое поведение из нормы.
2) Найти seam/edge в коде.
3) Реализовать тест сначала (RED), затем логику (GREEN).
4) Добавить negative/обходные сценарии.
5) Проверить evidence и traceability после изменения.

## Contract-specific rule
Ожидаемый результат теста берется только из DP/OQ/ADR/traceability, не из предположений модели.

## Quality gates
1) Для каждого сценария отметить, какой DP/OQ закрывается.
2) Не заменять runtime-assertions отсутствующими unit-упрощениями в core-контуре.
