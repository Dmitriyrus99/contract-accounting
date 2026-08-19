# Contract Accounting

Discovery, target architecture and implementation evidence for the Ferum contract-accounting project.

Start with [Release Decisions v1](11_release_decisions_v1.md) and [00_INDEX.md](00_INDEX.md). The implementation work begins under [`implementation/`](implementation/).
The updated roadmap is [06_roadmap.md](06_roadmap.md); the exact ordered closure plan is [10_remaining_questions_and_actions.md](10_remaining_questions_and_actions.md).

Current delivery state:

- owner decisions OQ-CA-001…023 are approved;
- release decisions DP-01…17 are approved; `contract_accounting` is the standalone replacement, legacy business migration and Import Batch are out of first-release scope, and evidence gates remain open;
- completion baseline is `7145d87` / `0.16.2`; local and remote annotated tag, manifest, verified schema snapshot and clean `136/136` standalone run are recorded, while live-site inventory/restore remain open; HEAD `5249e00` / `0.16.3` remains the traceable post-baseline commit and the evaluated, not-yet-committed working tree is `0.19.0`;
- Release Scope v1 preserves all 557 requirement IDs: 280 mandatory Implemented, 274 mandatory Partial, 0 mandatory Absent, 2 N/A and 1 Out-of-Release Deferred; the ordered closure backlog is `FR-01…18`;
- Quality/CI Profile v1 is configured: current standalone suite is `161/161`; checksum-synced disposable Bench `0.19.0` is PASS for migrate, app build and `89/89` Frappe tests; hosted CI has not run and release/UAT gates remain open;
- FR-02 master-data core is implemented: Party Identity is a guarded reconciliation layer over standard Customer/Supplier/Company, Service Object reuses Address/Contact, Material Expense reuses Warehouse, and Project/Task/Issue/Asset semantic non-application is recorded; owner/browser/race/load and Workflow/Communication gates remain open;
- CA-00 preflight, boundary ADR and live inventory are recorded;
- a separate private GitHub repository and immutable discovery baseline tag are published;
- CA-01 schema v0.2.0, dual-status lifecycle, direct contract/object links, 11 runtime tests and expanded schema rollback/reinstall are verified at `23b0dff`;
- CA-02 schema v0.3.0 adds Requirement/Obligation/typed recurrence, deterministic preview and effective/context guards; 15 runtime tests plus schema rollback/reinstall are verified at `b52f61b`;
- CA-03 schema v0.4.0 adds idempotent Schedule/Visit generation, explicit cancellation replacement, reviewed File evidence, acceptance and standalone Service Request; 19 runtime tests plus schema rollback/reinstall are verified at `d85488b`;
- CA-04 schema v0.5.0 adds one independent Finding with Defect category, immutable Visit provenance, confirmation/resolution gates, idempotent Service Request links and reviewed Photo Evidence over standard File; 24 runtime tests plus 21-DocType rollback/reinstall are verified at `5bc0bc9`;
- CA-05 schema v0.6.0 adds the universal Project Document registry, independent digital-copy/original custody, immutable transition events and accepted-File deletion guards; 29 runtime tests plus 24-DocType rollback/reinstall are verified at `0c8546d`;
- CA-06 schema v0.7.0 adds immutable accepted-work Billing Basis, versioned Billing Output/Artifact/Event, CA-05 document projection and a narrow adapter to standard Sales Invoice without custom ledger writes; 35 runtime tests plus 28-DocType clean reinstall are verified at `5b2d79a`;
- CA-07 schema v0.8.0 adds a rebuildable Finance Summary over standard Sales/Purchase Invoice and Payment Entry, guarded Material Expense/Contractor Settlement classification, reconciliation and Company-currency portfolio rollup; 41 runtime tests plus 31-DocType clean reinstall are verified at `f7217f3`;
- CA-08 schema v0.9.0 adds effective-dated Contractor Assignment, separate Commercial Terms/margin, Assignment links to Settlement/Material and Supplier-isolated contractor read; 47 runtime tests plus 35-DocType clean reinstall are verified at `9af7a67`, while Worker/Credential records and PERSONNEL READY remain hard-blocked by MG-CA-015;
- FR-05 legal/privacy package v1 now has named owners and filled Worker/Credential field, purpose/basis/retention, RBAC/export/private-file/break-glass decisions; Product Owner signed on 2026-08-19, while four independent signatures and FR-06 implementation remain OPEN before `MG-CA-015 PASS`;
- CA-09 v0.10.0 added a non-persistent, source-linked deadline timeline; v0.18.0 added the official 2026 calendar and missing signature/customer-response sources; v0.19.0 adds fail-closed DP-06 in-app/Email Queue delivery, timezone-aware digest, idempotency and retry/dead-letter. Full runtime is `89/89`; production transport/Operations gates and full External Dependency lifecycle FR-08 remain open;
- CA-10 v0.11.0 adds permission-safe, non-persistent Contract 360 and Director exception projections with exact primary-source drilldowns and stored CA-07 finance snapshots; 54 runtime tests are verified at `19d9124`, while UI/UAT, representative-volume performance, BPM sources and the required-photo policy remain open;
- CA-11 v0.12.0 adds nine separate parent BPM DocTypes, immutable published template versions, idempotent project generation, safe JSON Logic, evidence-backed step completion, Stage Gates, derived overdue and standard ToDo projection; 59 runtime tests are verified at `b474d74`, while the 169 assigned req-id remain only partially covered pending configured processes, automation, MG-CA-013 and UAT;
- CA-12 v0.13.0 adds an exact seven-stage/25-step Launch graph and a guarded Inspection lifecycle with frozen snapshots, report/Finding/photo outputs, separate manager/customer approval and audited final Launching→Active transition; 63 runtime tests are verified at `5fbb9a3`, while MG-CA-015, automatic document/Additional Work outputs, scenario pilots, CA-13 and UAT remain open;
- CA-13 v0.14.0 adds one recurring Billing Cycle per exact project period, a published 9-milestone Period Closing process, ERPNext-owned invoice/payment trace, correction history, an evidence-backed completion gate and overdue control feed; 65 runtime tests are verified at `c6e591b`, while automatic recurrence, external delivery, positive UPD/SF, backfill rehearsal, CA-14 and UAT remain open;
- CA-14 v0.15.0 adds permission-safe read-only My Actions/Project Launches Desk pages and a Service Project Launch tab, canonical Process Step/ToDo de-duplication, deterministic due ordering, exact stage/step progress and failed-gate blockers; 67 runtime tests are verified at `48e1502`, while explicit contractor-required/counterparty semantics, MG-CA-015, browser/cross-role UAT, performance and deployment remain open;
- CA-15 v0.16.0 adds a read-only nine-segment end-to-end trace, seven cross-cutting dimensions, project-scoped orphan/scope integrity diagnostics and the named Contract 360, Operations and Director Control Desk Pages; v0.16.1 verifies manager/director browser access and corrects director source visibility; v0.16.2 adds project-scoped Engineer/Office Manager access and verifies Engineer/Accountant/Office Manager/Project Lead Operations in a real browser; v0.16.3 adds the Service Request disposition core; export/report, performance, release and cutover gates remain open;
- runtime W2 evidence was inspected on the available test stand;
- full backup restore rehearsal remains open because `bench restore` required an interactive DB-root credential that was not read or exposed.

No secrets, site configuration values or production data are stored in this repository.

Reproduce the static profile with `python scripts/quality_gate.py`; see [Quality/CI Profile v1](14_quality_profile_v1.md) for the explicit Bench command and evidence boundary.
