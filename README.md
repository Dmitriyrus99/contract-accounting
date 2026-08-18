# Contract Accounting

Discovery, target architecture and implementation evidence for the Ferum contract-accounting project.

Start with [00_INDEX.md](00_INDEX.md). The implementation work begins under [`implementation/`](implementation/).

Current delivery state:

- owner decisions OQ-CA-001…023 are approved;
- CA-00 preflight, boundary ADR and live inventory are recorded;
- a separate private GitHub repository and immutable discovery baseline tag are published;
- CA-01 dual-status domain policy is implemented with unit tests; Frappe integration remains pending;
- runtime W2 evidence was inspected on the available test stand;
- full backup restore rehearsal remains open because `bench restore` required an interactive DB-root credential that was not read or exposed.

No secrets, site configuration values or production data are stored in this repository.
