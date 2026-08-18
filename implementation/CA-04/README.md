# CA-04 — Independent Finding and reviewed photo evidence

**Статус:** `CA-04 CORE CODE COMPLETE — SCHEMA v0.5.0 BENCH VERIFIED; INSPECTION/CONTRACTOR GATES PENDING`

Инкремент вводит один физический `Ferum Finding` для Observation/Defect/Nonconformity/Risk. Отдельный `Ferum Defect` не создаётся. Finding хранит неизменяемую provenance на Visit, собственные confirmation/resolution lifecycle и optional idempotent links на исполнение; заявка не возникает автоматически.

Специализированный `Ferum Photo Evidence` хранит source context, review и hash, но бинарный файл остаётся стандартным Frappe `File` SSOT.

Основные команды и exception report: [`findings.py`](../../contract_accounting/api/findings.py).
Finding controller: [`ferum_finding.py`](../../contract_accounting/contract_accounting/doctype/ferum_finding/ferum_finding.py).
Photo Evidence controller: [`ferum_photo_evidence.py`](../../contract_accounting/contract_accounting/doctype/ferum_photo_evidence/ferum_photo_evidence.py).

Схема и invariants: [schema_v0_5_0.md](schema_v0_5_0.md).
Runtime evidence: [runtime_evidence_v0_5_0_2026-08-18.md](runtime_evidence_v0_5_0_2026-08-18.md).
Implementation traceability: [traceability_v0_5_0.md](traceability_v0_5_0.md).

## Подтверждённые проверки

- standalone unit/schema suite: `72 tests`, `OK`;
- compileall, JSON parse и `git diff --check`: PASS;
- PEP 517 wheel v0.5.0: PASS;
- ERPNext v15 migrate: PASS;
- foreground Frappe suite: `24/24`, `OK`;
- controlled uninstall/install/migrate для 21 DocType и повторный suite: `24/24`, `OK`.

## Граница инкремента

`Ferum Inspection` разрешён архитектурным source allowlist, но fail-closed отклоняется, пока CA-12 не установит сам DocType. Execution target сейчас только `Ferum Service Request`: work-order adapter не одобрен. Contractor role не получает доступ к Finding/Photo Evidence; положительная модель «видит только собственные assignments» остаётся CA-08. Автопреобразование legacy Service Request в Finding отсутствует.
