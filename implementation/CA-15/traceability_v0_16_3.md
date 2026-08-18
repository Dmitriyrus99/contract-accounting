# CA-15 traceability addendum — v0.16.3

| TARGET/OQ item | Реализация | Автоматическое доказательство | Остаточная граница |
| --- | --- | --- | --- |
| OQ-CA-022 `subject`, `description` | Required schema + controller validation + honest backfill marker | static schema contract; runtime missing/valid text cases; full Frappe suite | Manual review legacy marker rows before cutover |
| Typed Finding/Maintenance provenance | `source_doctype` + Dynamic Link `source_name`; type/existence/context checks | runtime positive/negative provenance; integration edge contract | `Internal`/`Other` typed owner UNKNOWN |
| Paid Work successor | POST typed command; row lock; service-owned metadata; two DB unique constraints | runtime first-create + idempotent repeat; forged metadata blocked by controller contract | Parallel race/load topology not executed |
| Partial completion | POST atomic Remaining creation + source close | runtime Resolved/Partially Completed flow and repeated call | Business/legal UAT OPEN |
| `remaining_request` disposition | reverse `get_request_successors`; no source mirror | runtime reverse result; schema/API static contract | Browser UAT OPEN |
| Customer approval evidence | exact attached standard File → confidential Project Document | runtime exact-file rejection, creation/reuse and transition gate | Customer/legal role UAT and retention OPEN |
| Finding → Request compatibility | Finding command writes subject/description + typed source | Finding runtime `5/5`; full suite | None within implemented mapping |
| Migration safety | post-model-sync patch, exact source existence, fail-closed conflict | first migrate + repeated migrate PASS; static patch contract | Production dataset rehearsal/rollback OPEN |
| Regression/build | version `0.16.3` | standalone `138/138`; full Frappe `71/71`; build/wheel PASS | Production deployment OPEN |

Этот addendum подтверждает реализацию только перечисленных CODE-контрактов. Он не превращает автоматические тесты в UAT, legal/finance acceptance или release sign-off.
