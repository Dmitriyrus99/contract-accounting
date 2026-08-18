# CA-06 — execution-to-billing trace over standard ERPNext accounting

**Статус:** `CA-06 CORE CODE COMPLETE — SCHEMA v0.7.0 BENCH VERIFIED; UAT/PRODUCTION OPEN`.

Инкремент связывает принятую выработку с документарным слоем `Ferum Billing Output`, а затем со штатным submitted `Sales Invoice`. Денежные проводки, `Payment Entry`, `GL Entry` и `Payment Ledger Entry` остаются стандартными ERPNext SSOT: CA-06 не создаёт собственный ledger и не пишет в стандартные регистры.

`Ferum Billing Basis Item` хранит неизменяемый снимок принятых Visit/Service Request, их acceptance provenance, период, сумму и физический active claim. `Ferum Billing Artifact` версионирует generated/signed файлы, а финальные версии проецирует в реестр CA-05. `Ferum Billing Event` — insert-only аудит команд issue/cancel/supersede и артефактов.

Основные команды и selector: [billing.py](../../contract_accounting/api/billing.py).  
Output controller: [ferum_billing_output.py](../../contract_accounting/contract_accounting/doctype/ferum_billing_output/ferum_billing_output.py).  
Sales Invoice guard: [sales_invoice_guard.py](../../contract_accounting/infrastructure/sales_invoice_guard.py).

Схема и invariants: [schema_v0_7_0.md](schema_v0_7_0.md).  
Runtime evidence: [runtime_evidence_v0_7_0_2026-08-18.md](runtime_evidence_v0_7_0_2026-08-18.md).  
Implementation traceability: [traceability_v0_7_0.md](traceability_v0_7_0.md).

## Подтверждённые проверки

- standalone unit/schema suite: `83 tests`, `OK`;
- compileall, JSON parse и `git diff --check`: PASS;
- PEP 517 wheel v0.7.0: PASS;
- ERPNext v15 migrate на окончательном CODE commit: PASS;
- targeted CA-06 Frappe suite: `6/6`, `OK`;
- foreground full-app suite: `35/35`, `OK`;
- controlled uninstall/install/migrate: 28 DocType и custom field Sales Invoice восстановлены;
- post-reinstall full-app suite: `35/35`, `OK`.

## Граница инкремента

Billing Output требует уже submitted стандартный Sales Invoice того же Service Project/company/customer/currency. CA-06 не заменяет Invoice/Payment/GL сущности и не реализует Purchase Invoice. PDF/УПД генератор, ЭДО/КЭП, бухгалтерский UAT, legal/operations sign-off, нагрузочные race-тесты и production deployment не выполнялись.
