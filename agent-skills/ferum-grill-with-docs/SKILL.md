---
name: ferum-grill-with-docs
description: A ferum-specific skill profile adaptation for contract_accounting. This skill adds required process checks and project-specific constraints.
---

# ferum-grill-with-docs

## Purpose
Проводить инженерный разбор требования через профильные источники, а не через догадки.

## Scope
1) Новое требование/изменение
2) Читать релевантный source из `11_release_decisions_v1.md`
3) Читать ADR по затронутой области
4) Проверить связанные артефакты в `implementation/CA-*` и `08_open_questions.md`
5) Прозрачно зафиксировать неясности

## Workflow
1) Выделить требования по DP/OQ/REQ-ID.
2) Проверить, не конфликтуют ли они с ADR.
3) Построить дерево вопросов только по блокирующим зонам.
4) Сформировать что делаем в рамках scope.
5) Сформировать что НЕ делаем в текущем scope.
6) Сформировать какой proof нужен.
7) Сформировать какой owner вопрос остается открытым.
8) Продолжать реализацию без нового owner confirmation, если утверждённый DP/OQ/ADR уже покрывает решение.
9) Требовать owner confirmation только если нужен change control или отсутствует утверждённое решение.

## Contract-specific rule
`docs/agent_context` in this project replaced by discovery artifacts (`00_INDEX.md`, `08_open_questions.md`, `implementation/*`).

## Anti-patterns
1) Не подменять DP/ADR.
2) Не перебирать все возможные требования, если они не затронуты задачей.
3) Не превращать профильный срез в новый "источник истины".
