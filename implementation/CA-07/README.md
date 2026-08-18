# CA-07 — finance, payment and margin over ERPNext accounting SSOT

**Статус:** `CA-07 CORE CODE COMPLETE — SCHEMA v0.8.0 BENCH VERIFIED; FINANCE UAT/PRODUCTION OPEN`.

Инкремент завершает техническую цепочку MVP до оплаты и экономического результата. `Ferum Project Finance Summary` является удаляемой и полностью перестраиваемой проекцией над submitted `Sales Invoice`, `Purchase Invoice`, их standard outstanding и связанными `Payment Entry`, а также над утверждёнными management-затратами. Единственный contract-root остаётся `Ferum Service Project`.

CA-07 не создаёт собственные Invoice, Payment или ledger DocType и не пишет в `GL Entry`/`Payment Ledger Entry`. Opening Sales Invoice входит в receivable/paid, но исключается из recognized revenue и invoiced revenue. Расчёт допускается только в базовой валюте Company; портфель агрегируется отдельно по Company и currency.

Новые физические сущности:

- `Ferum Project Finance Summary` — read-only service-managed projection с source fingerprint;
- `Ferum Material Expense` — управленческий adjunct к стандартным Purchase Invoice/Stock Entry, не складской регистр;
- `Ferum Contractor Settlement` — расчёт Supplier/project/period, отделённый от будущего operational Assignment CA-08.

Основной rebuild/trace/reconciliation API: [finance.py](../../contract_accounting/api/finance.py).

Purchase Invoice boundary: [purchase_invoice_guard.py](../../contract_accounting/infrastructure/purchase_invoice_guard.py).

Accounting event adapter: [finance_hooks.py](../../contract_accounting/infrastructure/finance_hooks.py).

Схема и правила: [schema_v0_8_0.md](schema_v0_8_0.md).

Runtime evidence: [runtime_evidence_v0_8_0_2026-08-18.md](runtime_evidence_v0_8_0_2026-08-18.md).

Implementation traceability: [traceability_v0_8_0.md](traceability_v0_8_0.md).

## Подтверждённые проверки

- standalone unit/schema suite: `89 tests`, `OK`;
- compileall, parse 32 JSON и `git diff --check`: PASS;
- Ruff для CA-07-owned modules: PASS; repository-wide import debt остаётся OPEN;
- PEP 517 wheel v0.8.0: PASS;
- ERPNext v15 migrate v0.7.0 → v0.8.0: PASS;
- targeted CA-07 Frappe suite: `6/6`, `OK`;
- foreground full-app suite: `41/41`, `OK`;
- controlled uninstall/install/migrate: 31 DocType и оба standard adapter field восстановлены;
- post-reinstall full-app suite: `41/41`, `OK`.

## Граница инкремента

Положительный VAT-сценарий с tax rows, отдельная классификация инструмента/аренды, legacy before/after reconciliation, async worker observation, concurrent race/load, бухгалтерский UAT, Finance/Legal sign-off и production deployment не выполнялись. Поэтому `TCA-A-11-02` и `TCA-A-11-06` остаются частичными, а технический PASS не означает завершение бизнес-приёмки MVP.
