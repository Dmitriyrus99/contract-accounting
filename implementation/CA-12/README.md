# CA-12 — seven-stage Launch and Inspection core

**Статус:** `CA-12 PARTIAL — SEVEN-STAGE LAUNCH + INSPECTION CORE v0.13.0 BENCH VERIFIED; PERSONNEL READINESS BLOCKED BY MG-CA-015`.

Инкремент добавляет Published reference graph `FERUM-LAUNCH` v1: семь отдельных стадий и 25 шагов от Initiation до Launch Readiness. Повторный migrate проверяет exact graph и не создаёт Project Process или исторические Completed/Not Applicable steps. Launch assessment остаётся read-only; генерация instance выполняется только явной командой с exact token `CONFIRM_NO_HISTORY_BACKFILL`.

Новый parent `Ferum Inspection` хранит frozen template/version и inventory snapshots, checklist по системам/компонентам, команду, evidence, outcome и структурированный report snapshot. Completion транзакционно создаёт draft `Ferum Project Document`, независимые `Ferum Finding(category=Defect|Observation)` и `Ferum Photo Evidence`, сохраняя исходный item context. Manager approval и customer Sent/Approved/Rejected не смешиваются.

Validated Process Evidence типа `Inspection` принимает только `Approved Ferum Inspection`, связанный с тем же Process Step. Финальный Passed/Overridden Launch gate закрывает process и переводит `Ferum Service Project` из `Launching` в `Active` только через CA-01 lifecycle с audit event.

Schema contract: [schema_v0_13_0.md](schema_v0_13_0.md).

Runtime evidence: [runtime_evidence_v0_13_0_2026-08-18.md](runtime_evidence_v0_13_0_2026-08-18.md).

Implementation traceability: [traceability_v0_13_0.md](traceability_v0_13_0.md).

## Подтверждённые проверки

- standalone unit/schema suite: `123 tests`, `OK`;
- exact `FERUM-LAUNCH` v1 graph: 7 stages, 25 steps, repeated migrate idempotency PASS;
- targeted CA-12 Frappe suite: `4/4`, `OK`;
- foreground full-app Frappe suite: `63/63`, `OK` with `--skip-test-records`;
- после migrate: ровно 47 Contract Accounting DocType, включая `Ferum Inspection` и два child DocType;
- PEP 517 wheel v0.13.0: PASS;
- scoped Ruff: PASS; repository-wide 33-item `E4,E7,E9,F,I` debt остаётся OPEN.

## Открытая граница

Personnel/Credential positive gate остаётся fail-closed до MG-CA-015; `Completed` и `Not Applicable` для `PERSONNEL_READY` запрещены. Не реализованы automatic award trigger, отдельный child Inspection Project Process, автоматические физические акт/дефектная ведомость и Additional Work, полный отраслевой каталог ветвлений/документов, пилоты B2G/B2B/subcontract, post-launch Billing/ТО/Requests activation (CA-13), UI, representative-volume performance/load/race, clean reinstall, UAT/sign-off и production deployment.
