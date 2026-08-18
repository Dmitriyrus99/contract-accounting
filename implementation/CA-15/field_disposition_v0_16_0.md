# OQ-CA-022 field-level TARGET disposition — v0.16.0

**Вердикт review:** `COMPLETE AS ENGINEERING DISPOSITION; IMPLEMENTATION PARTIAL`.

Источник divergence — historical Codex `Ferum Service Request` (`Вспомогательные/Codex ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_request/ferum_service_request.json:L64-L221`). Ни отсутствие поля в Claude, ни наличие в Codex не являются самостоятельным TARGET-решением.

| Codex field | Disposition | TARGET owner/замена | v0.16.0 state |
| --- | --- | --- | --- |
| `project_scope` | `REPLACE` | `contract_obligation` Link | IMPLEMENTED |
| `subject` | `KEEP` | будущий обязательный Data request title | OPEN — schema/API/migration не реализованы |
| `description` | `KEEP` | будущий Text request description | OPEN — schema/API/migration не реализованы |
| `due_datetime` | `REPLACE` | `reaction_due` + `resolution_due` | IMPLEMENTED; calendar semantics зависят от MG-CA-013 |
| `maintenance_visit` | `REPLACE` | source provenance (`source_type` + typed source target) | PARTIAL — `source_type/source_reference` есть, typed Dynamic Link ещё OPEN |
| `sales_invoice` | `DERIVE` | reverse trace Billing Basis/Output → Sales Invoice | IMPLEMENTED как read projection; прямой Request-owned invoice link запрещён |
| `source_request` | `KEEP` | read-only self Link на исходную заявку | OPEN — successor service/schema/migration отсутствуют |
| `remaining_request` | `DERIVE` | reverse lookup по `source_request + successor_kind` | OPEN вместе с successor service |
| `successor_kind` | `KEEP` | Select `Paid Work / Remaining` | OPEN — требует target command и concurrency/idempotency tests |
| `exception_key` | `KEEP` | unique service-owned idempotency key | OPEN — требует target command и backfill rule |
| `customer_approval_evidence` | `MOVE TO GENERIC TARGET ENTITY/EVIDENCE` | `Ferum Project Document` source=Request + standard `File` | Generic schema IMPLEMENTED; request-specific approval command/UAT OPEN |
| `access_denied_reason` | `MOVE TO GENERIC TARGET ENTITY/EVIDENCE` | immutable `Ferum Process Event`/audit event source=Request | Generic schema IMPLEMENTED; request-specific event command OPEN |
| `completed_on` | `REPLACE` | `actual_end` | IMPLEMENTED |
| `sla_status` | `DERIVE` | deadline timeline base timestamps + derived overdue/approaching state | PARTIAL; persisted `Overdue` flag не вводится, MG-CA-013 OPEN |
| `sla_warning` | `DERIVE` | deadline warning/escalation projection | PARTIAL; notification delivery/UAT OPEN |

Current TARGET evidence: Service Request `contract_obligation`, source fields, reaction/resolution due, actual_end и evidence (`contract_accounting/contract_accounting/doctype/ferum_service_request/ferum_service_request.json:L20-L35`); generic Project Document provenance/File (`contract_accounting/contract_accounting/doctype/ferum_project_document/ferum_project_document.json:L14-L30`); generic Process Event provenance (`contract_accounting/contract_accounting/doctype/ferum_process_event/ferum_process_event.json:L10-L12`).

Этот документ запрещает silently dropping Codex-only fields. `KEEP` со state OPEN является backlog requirement, а не доказательством реализации. Перед migration cutover нужны schema/API, exact source mapping, idempotent backfill и rollback evidence.
