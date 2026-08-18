# CA-09 — derived deadline timeline

**Статус:** `CA-09 PARTIAL — SOURCE TIMELINE v0.10.0 BENCH VERIFIED; PRODUCTION CALENDAR BLOCKED BY MG-CA-013`.

Инкремент не создаёт `Ferum Deadline` или `Ferum Contract Milestone` и не копирует контрольные даты в новый SSOT. Read-only API [deadlines.py](../../contract_accounting/api/deadlines.py) собирает нормализованные строки непосредственно из Service Project, Maintenance Schedule, Service Request, Execution Stage, Contract Security, Project Document, Finding и submitted Sales Invoice. Каждая строка содержит `source_doctype`, `source_name`, `source_field`, стабильный `source_key`, owner, исходный status и дату; повторный вызов полностью перестраивает projection.

Pure domain engine [deadline.py](../../contract_accounting/domain/deadline.py) рассчитывает due/warning/escalation timestamps только при явных trigger, timezone, calendar revision, Holiday List snapshot, cut-off policy и offsets. Неизвестный trigger или timezone отклоняется. Calculation hash зависит от полного immutable input/result snapshot.

Production configuration MG-CA-013 отсутствует. Поэтому обычный API возвращает source dates с `is_overdue=null` и `severity=Unclassified`; absolute overdue включается только при явном `as_of` и не выдаётся за Company-calendar readiness. Warning/escalation projection остаётся `disabled_pending_MG-CA-013`.

Projection contract: [projection_v0_10_0.md](projection_v0_10_0.md).

Runtime evidence: [runtime_evidence_v0_10_0_2026-08-18.md](runtime_evidence_v0_10_0_2026-08-18.md).

Implementation traceability: [traceability_v0_10_0.md](traceability_v0_10_0.md).

## Подтверждённые проверки

- standalone unit/schema suite: `100 tests`, `OK`;
- pure calendar fixture: explicit IANA timezone, holiday skip, Calendar/Business Days, cut-off, warning/escalation и deterministic hash;
- compileall, parse 36 JSON и `git diff --check`: PASS;
- Ruff для CA-09-owned modules: PASS; repository-wide 33-item baseline debt остаётся OPEN;
- PEP 517 wheel v0.10.0: PASS;
- ERPNext v15 migrate v0.9.0 → v0.10.0: PASS;
- targeted CA-09 Frappe suite: `3/3`, `OK`;
- foreground full-app suite: `50/50`, `OK`;
- после migrate сохранены 35 DocType; `Ferum Deadline` отсутствует.

## Открытая граница

Не закрыты production Company timezone/Holiday List/cut-off/revision fixture, automatic warning/escalation, structured signature deadline, customer-response deadline, общий warranty deadline вне Security, BPM dates CA-11, representative-volume latency, scheduler/notification delivery, UAT/sign-off и production deployment. Значения из текста или неструктурированных условий не угадываются.
