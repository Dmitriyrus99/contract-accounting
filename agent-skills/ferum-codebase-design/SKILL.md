---
name: ferum-codebase-design
description: Design architecture changes for contract_accounting through ADR/roadmap gates before implementation.
---

# ferum-codebase-design

## Purpose
Предлагать архитектурные решения через ADR и roadmap, без избыточного упрощения.

## Workflow
1) Считать границы из `06_roadmap.md`, `12_release_scope_v1.md`, ADR.
2) Проверить зависимые точки интеграции в `12_release_scope_matrix_v1.csv` и `08_open_questions.md`.
3) Разработать design альтернативы с рисками, стоимостью и влиянием gates.
4) Зафиксировать, что нельзя затронуть scope первого релиза.

## Contract-specific rule
Если решение меняет boundary DP/ADR, сначала формировать change-control предложение, а не code patch.

## Output
1) Концептуальная схема с trade-off.
2) Список affected DP/OQ/REQ.
3) Рекомендуемый путь внедрения в очередности закрытия.
