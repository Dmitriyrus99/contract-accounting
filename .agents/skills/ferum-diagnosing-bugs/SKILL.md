---
name: ferum-diagnosing-bugs
description: Diagnose bugs in contract_accounting using evidence-first triage aligned with DP/OQ/ADR.
---

# ferum-diagnosing-bugs

## Purpose
Локализовать дефект с опорой на evidence и архитектурные ограничения DP/ADR.

## Method
1) Зафиксировать наблюдаемый симптом и минимальный repro.
2) Сопоставить с трассируемыми требованиями.
3) Вычислить корень причины в domain / query / permission / scheduler / workflow.
4) Предложить только минимально достаточный fix under scope.
5) Назначить rollback risk и gate влияния.

## Contract-specific rule
Любой багфикс требует регрессионного доказательства и отмечается как CH/OQ dependency.

## Anti-patterns
1) Вводить speculative fixes без привязки к конкретному DP/OQ.
2) Пытаться "пофиксить весь модуль" без evidence на проблему.
