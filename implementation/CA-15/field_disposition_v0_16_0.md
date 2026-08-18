# OQ-CA-022 field-level TARGET disposition — v0.16.0

**Вердикт review:** `COMPLETE AS ENGINEERING DISPOSITION; IMPLEMENTATION PARTIAL`.

Источник divergence — historical Codex `Ferum Service Request` (`Вспомогательные/Codex ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_request/ferum_service_request.json:L64-L221`). Ни отсутствие поля в Claude, ни наличие в Codex не являются самостоятельным TARGET-решением.

| Codex field | Disposition | TARGET owner/замена | v0.16.0 state |
| --- | --- | --- | --- |
| `project_scope` | `REPLACE` | `contract_obligation` Link | IMPLEMENTED |
| `subject` | `KEEP` | обязательный Data request title | IMPLEMENTED v0.16.3 — server validation + honest review-marker backfill |
| `description` | `KEEP` | обязательный Text request description | IMPLEMENTED v0.16.3 — server validation + honest review-marker backfill |
| `due_datetime` | `REPLACE` | `reaction_due` + `resolution_due` | IMPLEMENTED; calendar semantics зависят от MG-CA-013 |
| `maintenance_visit` | `REPLACE` | source provenance (`source_type` + typed source target) | PARTIAL v0.16.3 — Finding/Maintenance Visit typed Dynamic Link implemented; Internal/Other owner OPEN |
| `sales_invoice` | `DERIVE` | reverse trace Billing Basis/Output → Sales Invoice | IMPLEMENTED как read projection; прямой Request-owned invoice link запрещён |
| `source_request` | `KEEP` | read-only self Link на исходную заявку | IMPLEMENTED v0.16.3 — service-owned successor command/context validation |
| `remaining_request` | `DERIVE` | reverse lookup по `source_request + successor_kind` | IMPLEMENTED v0.16.3 — reverse API, mirror не создан |
| `successor_kind` | `KEEP` | Select `Paid Work / Remaining` | PARTIAL v0.16.3 — commands/idempotent repeat implemented; parallel race/load qualification OPEN |
| `exception_key` | `KEEP` | unique service-owned idempotency key | IMPLEMENTED v0.16.3 — deterministic key + DB uniqueness; production backfill не требуется для новых successors |
| `customer_approval_evidence` | `MOVE TO GENERIC TARGET ENTITY/EVIDENCE` | `Ferum Project Document` source=Request + standard `File` | PARTIAL v0.16.3 — exact-file command/transition gate runtime verified; cross-role/legal UAT OPEN |
| `access_denied_reason` | `MOVE TO GENERIC TARGET ENTITY/EVIDENCE` | immutable `Ferum Process Event`/audit event source=Request | Generic schema IMPLEMENTED; request-specific event command OPEN |
| `completed_on` | `REPLACE` | `actual_end` | IMPLEMENTED |
| `sla_status` | `DERIVE` | deadline timeline base timestamps + derived overdue/approaching state | PARTIAL; persisted `Overdue` flag не вводится, MG-CA-013 OPEN |
| `sla_warning` | `DERIVE` | deadline warning/escalation projection | PARTIAL; notification delivery/UAT OPEN |

Current TARGET evidence: Service Request schema/controller и commands (`contract_accounting/contract_accounting/doctype/ferum_service_request/ferum_service_request.json`; `contract_accounting/contract_accounting/doctype/ferum_service_request/ferum_service_request.py`; `contract_accounting/api/requests.py`); generic Project Document provenance/File (`contract_accounting/contract_accounting/doctype/ferum_project_document/ferum_project_document.json`); generic Process Event provenance (`contract_accounting/contract_accounting/doctype/ferum_process_event/ferum_process_event.json`).

Этот документ запрещает silently dropping Codex-only fields. `KEEP` со state OPEN является backlog requirement, а не доказательством реализации. Перед migration cutover нужны schema/API, exact source mapping, idempotent backfill и rollback evidence.
