---
name: ferum-code-review
description: Perform multi-axis review for contract_accounting balancing normative, architectural, quality, and evidence checks.
---

# ferum-code-review

## Purpose
Проводить многоосевую ревизию реализации: норма, архитектура, качество, evidence.

## Axes
1) Normative compliance: `11_release_decisions_v1.md`, `ADR-*`, `12_release_scope_v1.md`.
2) Architecture compliance: ADR + `06_roadmap.md` + existing traceability.
3) Implementation quality: tests, readability, safety.
4) Evidence readiness: evidence URLs/attachments + gate alignment.

## Rule
Не объединять implement и review в одной цепочке по умолчанию.
Если в задаче требуется независимая точка контроля, отметить это отдельным статусом.

## Output template
1) Список критических блокеров.
2) Список medium risks.
3) Sufficient evidence по каждому changed DP/OQ.
4) Рекомендации к закрытию.
