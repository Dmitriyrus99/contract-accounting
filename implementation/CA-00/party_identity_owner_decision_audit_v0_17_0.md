# Party Identity owner decision audit v0.17.0

**Status:** `EVIDENCE GATE OPEN`

**Scope:** audit-only clarification for `OQ-CA-017`; no ADR, release decision, business document, schema or code change.

**Purpose:** make the approved Party Identity ownership decision directly usable for later architecture and implementation work without re-asking the owner about already approved DP/OQ/ADR facts.

## Sources checked

| Source | Relevant fact |
| --- | --- |
| [../../00_INDEX.md](../../00_INDEX.md) | Current status baseline says owner architecture/scope questions are approved; remaining work is CODE/configuration/legal/RBAC/performance/UAT/restore/deployment gates. |
| [../../08_open_questions.md](../../08_open_questions.md), `OQ-CA-017` | `APPROVED`: Customer/Supplier/Company remain domain master SSOT; Party Identity is linkage/reconciliation layer. |
| [ADR-CA-0001-erpnext-custom-party-boundary.md](ADR-CA-0001-erpnext-custom-party-boundary.md) | Accepted TARGET boundary: Party Identity owns identifiers, links, duplicate/reconciliation state and provenance; it is not an accounting-document party and not a replacement for Customer/Supplier/Company. |
| [../../05_target_model.md](../../05_target_model.md) | Target model keeps Party Identity as reconciliation layer, with Master Data Steward CRUD and Legal/Accounting approval/read roles. |
| [master_data_boundary_v0_17_0.md](master_data_boundary_v0_17_0.md) | Implementation boundary records standard ERPNext master reuse, no business-field copy, unique links, conflict detection, no ambiguous auto-merge. |
| [runtime_evidence_v0_17_0_2026-08-19.md](runtime_evidence_v0_17_0_2026-08-19.md) | Automation evidence exists for targeted Party Identity acceptance and full app run, but manual/release gates remain open. |

## Resolved facts

| Area | Confirmed fact |
| --- | --- |
| Master ownership | `Customer`, `Supplier` and `Company` remain ERPNext domain master SSOT. |
| Party Identity ownership | `Ferum Party Identity` owns cross-master identifiers, links, duplicate/reconciliation state and provenance. |
| Accounting document party | Financial documents continue to link to Customer/Supplier/Company, not Party Identity. |
| Synchronization | Default bidirectional business-field sync is forbidden. Differences require explicit reconciliation workflow or an approved one-way field rule. |
| Merge safety | Ambiguous organizations must not be auto-merged. Same identifiers can create duplicate-review candidates, not silent merges. |
| Historical identity | Party Identity may preserve identity/provenance across changing requisites, but must not overwrite ERPNext master business fields by default. |

## Scenario check

| Scenario | Decision impact |
| --- | --- |
| One organization is both Customer and Supplier | One Party Identity may link both ERPNext masters, but each master remains authoritative for its ERPNext role. |
| Several legal entities in one group | Each legal entity needs its own Party Identity when legal identifiers differ; group structure can be represented through `head_party`/branch links, not by merging legal entities. |
| Company is our legal entity | `Company` remains the ERPNext master for own legal entity; Party Identity may link it for cross-master reconciliation and provenance. |
| Requisites change without losing historical identity | Party Identity can retain provenance and tax-registration history; business-field changes still belong to the relevant ERPNext master or approved field rule. |
| Duplicate counterparty | Duplicate detection/review belongs to Party Identity; resolution is explicit and must not silently merge Customer/Supplier/Company records. |
| Individual / individual entrepreneur | Existing Party Identity `party_type` supports individual-style party categories; allowed use still depends on approved privacy/RBAC/legal gates before production use. |
| Existing documents keep Customer/Supplier links | Existing and future accounting documents keep their Customer/Supplier/Company links; Party Identity is additive linkage/reconciliation metadata. |

## Unresolved decision

No new owner decision is required for `OQ-CA-017` itself. The owner decision is already approved.

The unresolved work is evidence and operating policy, not ownership:

| Gate | Why it remains open |
| --- | --- |
| Data-owner review | Business owner must accept duplicate/reconciliation operating rules on representative data. |
| Browser UAT | Role behavior and read-only link behavior must be verified in UI. |
| Race/load qualification | Idempotent link and conflict handling need concurrency/performance evidence. |
| Workflow/Communication acceptance | Explicit reconciliation workflow and evidence trail must be accepted before relying on it operationally. |
| Restore/cutover | Production migration/rollback evidence remains outside this audit. |

## Recommended owner decision

Use the existing approved decision as final owner guidance:

`Customer`, `Supplier` and `Company` own business master data. `Ferum Party Identity` owns cross-master identity, identifiers, links, duplicate/reconciliation state and provenance only. It must not become a second Customer/Supplier/Company master, must not be used as the accounting-document party, and must not perform arbitrary bidirectional business-field sync.

## Consequences

1. Architecture should model Party Identity as an additive reconciliation boundary, not as replacement master data.
2. Implementation should keep authoritative accounting and role-specific business fields on ERPNext masters.
3. Any automatic create/link behavior must be idempotent, conflict-aware and test-backed.
4. Duplicate handling must remain review-based until an explicit owner-approved merge policy exists.
5. Traceability should cite `OQ-CA-017`, `ADR-CA-0001` and this audit when Party Identity behavior is touched.
6. Release readiness must stay blocked by evidence gates until UAT, concurrency, workflow, restore and cutover proofs are complete.

## Required follow-up artifacts

| Artifact | Owner | Status |
| --- | --- | --- |
| Party Identity duplicate/reconciliation operating checklist | Product Owner + Master Data Steward | `EVIDENCE GATE OPEN` |
| Browser UAT evidence for master-link edit/read roles | QA + Security reviewer | `EVIDENCE GATE OPEN` |
| Race/load evidence for idempotent link and conflict cases | Engineer | `EVIDENCE GATE OPEN` |
| Reconciliation workflow/Communication acceptance protocol | Product Owner + Legal/Accounting | `EVIDENCE GATE OPEN` |
| Migration/restore/cutover evidence, if Party Identity data is migrated | Release Engineer | `EVIDENCE GATE OPEN` |

## Final status

`EVIDENCE GATE OPEN`

Ownership is resolved by approved `OQ-CA-017` and accepted `ADR-CA-0001`. Implementation and release qualification remain gated by evidence.
