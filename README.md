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
- runtime W2 evidence was inspected on the available test stand;
- full backup restore rehearsal remains open because `bench restore` required an interactive DB-root credential that was not read or exposed.

No secrets, site configuration values or production data are stored in this repository.
