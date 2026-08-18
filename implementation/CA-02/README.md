# CA-02 — Contract Requirement and Contract Obligation

**Статус:** `CA-02 CORE CODE COMPLETE — SCHEMA v0.3.0 BENCH VERIFIED; CA-03 WRITER DELIVERED IN v0.4.0; SLA/MIGRATION GATES PENDING`

Инкремент добавляет явный слой между договором и будущим графиком:

- `Ferum Contract Requirement` сохраняет source reference/clause, typed values, применимость, assessment и ровно одно routing decision;
- `Ferum Contract Obligation` нормализует work/project object/object system/recurrence/deadline/effective period и source Requirement;
- `Ferum Obligation Recurrence Rule` хранит typed recurrence без `eval` и произвольного кода;
- server guards блокируют foreign project/object/system, неверный Requirement route, пересечение active effective versions, silent edit после activation и произвольный Dynamic Link DocType;
- generation preview детерминирован, ограничен horizon, не пишет Schedule/Visit и fail-closed отклоняет конфликтующие правила.

Код: [`ferum_contract_requirement.py`](../../contract_accounting/contract_accounting/doctype/ferum_contract_requirement/ferum_contract_requirement.py), [`ferum_contract_obligation.py`](../../contract_accounting/contract_accounting/doctype/ferum_contract_obligation/ferum_contract_obligation.py), [`obligation.py`](../../contract_accounting/domain/obligation.py).

Схема и границы: [schema_v0_3_0.md](schema_v0_3_0.md).
Runtime evidence: [runtime_evidence_v0_3_0_2026-08-18.md](runtime_evidence_v0_3_0_2026-08-18.md).
Implementation traceability: [traceability_v0_3_0.md](traceability_v0_3_0.md).

## Подтверждённые проверки

- standalone unit/schema suite: `63 tests`, `OK`;
- compileall и `git diff --check`: PASS;
- clean PEP 517 wheel v0.3.0: PASS;
- ERPNext v15 migrate: PASS после исправления реально выявленного MariaDB limit имени индекса;
- foreground Frappe suite: `15/15`, `OK`;
- controlled schema uninstall/install/migrate и повторный suite: `15/15`, `OK`.

## Граница инкремента

`Ferum Project Document` появится в CA-05, поэтому source document пока честно хранится как `Data`, не ложный Link. `work_type` остаётся typed `Data` до согласованного каталога. Preview сам не пишет данные; provenance `Obligation → Schedule/period_key → Visit` и идемпотентный writer реализованы CA-03 v0.4.0. SLA timestamp/calendar engine принадлежит CA-09. Legacy Scope importer не запускался: источники discovery read-only и на disposable site legacy app не установлен; неоднозначный backfill запрещён.
