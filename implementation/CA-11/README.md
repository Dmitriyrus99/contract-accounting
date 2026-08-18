# CA-11 — versioned BPM core

**Статус:** `CA-11 PARTIAL — VERSIONED BPM CORE v0.12.0 BENCH VERIFIED; 169 REQUIREMENTS NOT ALL CLOSED`.

Инкремент реализует утверждённую OQ-CA-010 parent-топологию: отдельные `Ferum Process Template`, `Ferum Stage Template`, `Ferum Step Template`, `Ferum Project Process`, `Ferum Project Stage`, `Ferum Project Process Step`, `Ferum Stage Gate`, `Ferum Process Evidence` и `Ferum Process Event`. Ни один из узлов не заменён child table или универсальной задачей.

Published template graph неизменяем. Новый generation key создаёт frozen instance snapshot; повтор того же ключа возвращает тот же Project Process. Process Step остаётся процессным SSOT, а персональная работа проецируется в стандартный `ToDo` и закрывается вместе с terminal step.

Condition/activation/exit rules используют небольшой JSON Logic allowlist без `eval`/`exec`, с разрешёнными namespace `project`, `requirement`, `step`, `gate`. Неизвестный operator/field и отсутствующий context блокируют вычисление.

Completion требует `Validated` evidence точного template type. Stage Gate проверяет все blocking steps и запрещает завершение stage при `Failed`. `Not Applicable`, `Waiting External`, `Blocked` и `Cancelled` требуют явной причины по typed transition rules. `Overdue` не входит в persisted base status и вычисляется read-only projection только при explicit `as_of`.

Schema contract: [schema_v0_12_0.md](schema_v0_12_0.md).

Runtime evidence: [runtime_evidence_v0_12_0_2026-08-18.md](runtime_evidence_v0_12_0_2026-08-18.md).

Implementation traceability: [traceability_v0_12_0.md](traceability_v0_12_0.md).

## Подтверждённые проверки

- standalone unit/schema suite: `117 tests`, `OK`;
- safe JSON Logic, base FSM, derived overdue и pure gate rules: PASS;
- migrate v0.11.0 → v0.12.0: PASS;
- targeted CA-11 Frappe suite: `5/5`, `OK`;
- затронутые CA-09/10 suites: `3/3` и `4/4`, `OK`;
- foreground full-app Frappe suite: `59/59`, `OK`;
- после migrate: ровно 44 Contract Accounting DocType, включая 9 новых BPM parent DocType;
- PEP 517 wheel v0.12.0: PASS;
- scoped Ruff: PASS; repository-wide 32-item baseline debt остаётся OPEN.

## Открытая граница

CA-11 содержит core engine, но не объявляет закрытыми все 169 назначенных req-id. Не реализованы эталонный семистадийный launch template/Inspection (CA-12), Billing Cycle process (CA-13), My Actions UI (CA-14), automatic external-event ingestion, scheduler/notification delivery, Department Head/Director escalation delivery, production calendar selection MG-CA-013, role-to-user resolver, ad-hoc individual-step command, representative-volume load/race, clean reinstall, UAT/sign-off и production deployment.
