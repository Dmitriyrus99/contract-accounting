# CA-13 — recurring Billing Cycle core

**Статус:** `CA-13 PARTIAL — RECURRING BILLING CYCLE + PERIOD GATE v0.14.0 BENCH VERIFIED`.

Инкремент добавляет отдельный parent `Ferum Billing Cycle` для одного Service Project и точного периода. Cycle связывает immutable expected-work snapshot, CA-11 Period Closing Process и существующие CA-06 Billing Output/Basis, но не хранит собственный ledger и не пишет GL. Invoice/payment остаются стандартными ERPNext SSOT.

Published reference graph `FERUM-BILLING-CYCLE` v1 содержит одну stage `PERIOD_CLOSING` и девять последовательных blocking milestones: выполненные работы, подтверждение исполнения, акт, invoice, UPD/SF, approval, sending, customer receipt и payment. Conditional Act/UPD applicability закрывается только через explicit `Not Applicable` reason; completion остальных шагов требует source-linked Validated Process Evidence.

Cycle projection показывает expected, accepted, unbilled, claimed-outside-cycle, billed, output/signed, sent/receipt, invoices и submitted Payment Entries. Completion разрешён только после Completed BPM Process/Passed Gate, отсутствия unbilled/foreign claims, Signed active outputs и полной оплаты стандартных invoices.

Schema contract: [schema_v0_14_0.md](schema_v0_14_0.md).

Runtime evidence: [runtime_evidence_v0_14_0_2026-08-18.md](runtime_evidence_v0_14_0_2026-08-18.md).

Implementation traceability: [traceability_v0_14_0.md](traceability_v0_14_0.md).

## Подтверждённые проверки

- standalone unit/schema suite: `128 tests`, `OK`;
- exact `FERUM-BILLING-CYCLE` v1 graph: 1 stage, 9 steps, repeated migrate idempotency PASS;
- targeted CA-13 Frappe suite: `2/2`, `OK`;
- foreground full-app Frappe suite: `65/65`, `OK` with `--skip-test-records`;
- после migrate: ровно 48 Contract Accounting DocType, включая новый parent `Ferum Billing Cycle`;
- PEP 517 wheel v0.14.0: PASS;
- scoped Ruff: PASS; repository-wide 32-item `E4,E7,E9,F,I` debt остаётся OPEN.

## Открытая граница

Не реализованы automatic recurring trigger/scheduler, автоматическое формирование актов/UPD/SF, внешние transport/delivery acknowledgements, production calendar/escalation delivery, My Actions UI (CA-14), runtime backfill rehearsal на legacy output dataset, clean reinstall, representative-volume performance/load/race, UAT/sign-off и production deployment. Explicit backfill CODE работает только для Draft/Generated exact-period groups; Issued/Signed и conflicts остаются manual legal reconciliation.
