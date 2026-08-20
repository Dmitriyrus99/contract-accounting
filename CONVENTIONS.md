# CONVENTIONS — contract-accounting

## 1) Source and code style
1) Имена DocType, permissions и doctype fields — в соответствии с текущим кодом и traceability.
2) Серверный код в основном уровне `contract_accounting/` и `scheduler/`, публичные утилиты через API-договариваемые модули.
3) Прямые DB-запросы только при наличии архитектурного смысла и валидации прав.

## 2) Security and data model
1) ERPNext masters (`Company`, `Customer`, `Supplier`, `Account`, `Item`, `Stock`, `Currency`) используются как SSOT, где это утверждено DP-01/ADR-CA-0001.
2) Любые операции с PII следуют DP-07, FR-05/FR-06 и текущим open questions.
3) Private-file и экспорт имеют отдельные ограничения от UI/API-права.

## 3) Release readiness policy
1) Не считать PASS без выполнения соответствующих DP/ADR-гейтов и owner sign-off.
2) Любые изменения в финально важном path фиксировать в completion-пакете и traceability.
