---
name: ferum-architecture-survey
description: Perform architecture surveys for contract_accounting and convert findings into OQ/CH proposals, not blind refactors.
---

# ferum-architecture-survey

## Purpose
Проводить architectural survey без прямого рефакторингового импульса.

## Scope
1) permissions: поиск отклонений и влияние на ограничения.
2) lifecycle: поиск отклонений и влияние на ограничения.
3) privacy/PII: поиск отклонений и влияние на ограничения.
4) performance gates: поиск отклонений и влияние на ограничения.
5) dependency boundaries: поиск отклонений и влияние на ограничения.
6) Сопоставление с DP/ADR и OQ.

## Method
1) Найти deviation и проверить его влияние.
2) Сравнить с ACCEPTED ADR.
3) Если конфликт есть — вынести в OQ/CH предложение.
4) Если конфликтов нет — оформить recommendations only.

## Contract-specific rule
Architecture-scan не является триггером мгновенного рефакторинга; обязательна OQ/CH-дорожная постановка.
