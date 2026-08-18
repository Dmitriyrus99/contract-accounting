# Contract Accounting

Discovery, target architecture and implementation evidence for the Ferum contract-accounting project.

Start with [00_INDEX.md](00_INDEX.md). The implementation work begins under [`implementation/`](implementation/).

Current delivery state:

- owner decisions OQ-CA-001…023 are approved;
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
- CA-09 v0.10.0 adds a non-persistent, source-linked deadline timeline and an explicit immutable-calendar calculator; 50 runtime tests are verified at `a08b709`, while automatic warning/escalation and production calendar selection remain hard-blocked by MG-CA-013;
- runtime W2 evidence was inspected on the available test stand;
- full backup restore rehearsal remains open because `bench restore` required an interactive DB-root credential that was not read or exposed.

No secrets, site configuration values or production data are stored in this repository.
