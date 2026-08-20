# Contract Accounting demo/UAT v1

The v1 manifest declares a deterministic, no-PII first-stage domain graph in
two isolated projects (`own` and `foreign`). It contains 50 owned domain
records: 25 per project, 24 DocTypes, all 20 ACL surfaces audited by
`project_graph_permissions.py`, period-closing process/evidence, documentary
billing, contractor assignment/material expense, personnel credential/privacy,
and private binary-evidence references.

Its technical status is `FULL_SYNTHETIC_GRAPH_MANUAL_UAT_REQUIRED`. That is a
structural scope statement, not UAT, release, accounting, or deployment PASS.

## Deterministic prerequisites

Run Bench only from the Bench root and only against an active `*.localhost`
site. The manifest never reads `site_config.json` and contains no password,
email address, phone, passport, SNILS, or production identifier.

The installer requires 12 explicit bindings:

- existing Company, Customer, Currency, and two Customer-linked Address rows;
- two distinct User rows with the `Инженер` role;
- two synthetic Supplier rows (`own` and `foreign`);
- the canonical published `FERUM-BILLING-CYCLE` v1 Process Template, its
  `PERIOD_CLOSING` Stage Template, and its `WORK_COMPLETED` Step Template.

The installer-owned synthetic bootstrap is the only source for those bindings.
It cannot be executed standalone because only the installer owns a full
database-and-file rollback boundary.
The three template rows are validated source-controlled reference data, not
demo-owned data.

Two bootstrap-owned private `File` fixtures are also declared in
`business_graph.binary_fixtures`. Their UTF-8 bytes, deterministic File names,
attachment targets, and SHA-256 hashes are part of the canonical manifest.
They are prerequisites, not manifest entities, so the domain ownership registry
does not misrepresent binary ownership.

## Entry points

Every command requires the exact token in `manifest_v1.json`. Install and real
reset additionally require active Frappe user `Administrator`.

The canonical smoke sequence has no caller-supplied bindings:

```bash
bench --site ca01.localhost execute contract_accounting.demo_uat.installer.install \
  --kwargs '{"confirmation_token":"INSTALL_CONTRACT_ACCOUNTING_DEMO_UAT_V1"}'

bench --site ca01.localhost execute contract_accounting.demo_uat.verifier.verify \
  --kwargs '{"confirmation_token":"VERIFY_CONTRACT_ACCOUNTING_DEMO_UAT_V1"}'

# Safe default: returns the reverse plan and deletes nothing.
bench --site ca01.localhost execute contract_accounting.demo_uat.reset.reset \
  --kwargs '{"confirmation_token":"RESET_CONTRACT_ACCOUNTING_DEMO_UAT_V1"}'

# Destructive only for registry-owned demo records.
bench --site ca01.localhost execute contract_accounting.demo_uat.reset.reset \
  --kwargs '{"confirmation_token":"RESET_CONTRACT_ACCOUNTING_DEMO_UAT_V1","dry_run":False}'

# Idempotency smoke: must return delete_count=0 and leave no owned residue.
bench --site ca01.localhost execute contract_accounting.demo_uat.reset.reset \
  --kwargs '{"confirmation_token":"RESET_CONTRACT_ACCOUNTING_DEMO_UAT_V1","dry_run":False}'
```

## Graph and scenario contract

Each project contains the complete 20-surface ACL graph plus its requirement,
worker, credential, Billing Cycle, and second documentary-billing Project
Document. All `$ref` links stay within one project. Shared ERPNext masters and
published templates are bindings and are never owned or deleted by this package.

Billing scope is deliberately documentary. The manifest creates only an open
synthetic Billing Cycle and draft Act/UPD-style Project Document. It creates or
submits no Sales Invoice or Purchase Invoice, writes no GL Entry, reconciles no
payment, and makes no accounting-posting claim.

Worker activation, credential verification, assignment approval, credential
revocation, readiness recomputation, and fail-closed assignment suspension are
listed as typed lifecycle scenarios. Their terminal state must be exercised
through the guarded product commands during UAT; direct field mutation is not
accepted as lifecycle evidence.

## Fail-closed guarantees

- The loader accepts the manifest only when its canonical SHA-256 matches.
- Runtime preflight validates bindings, roles, pages, DocTypes, fields, Link
  targets, Select options, and `Europe/Moscow` before the first domain insert.
- Installation remains create-or-validate; deterministic-name drift and
  registry drift abort instead of updating data.
- Verification rejects non-demo inbound Link or Dynamic Link references.
- Reset defaults to dry-run, deletes in reverse manifest order, removes the
  unattached ownership registry last, and uses one transaction.
- Structural status is always `*_MANUAL_UAT_REQUIRED`, never `PASS` or `READY`.

## Qualification boundary

The manifest intentionally limits `unsupported` to four external gates:
human UAT/sign-off, production activation/deployment, representative
performance/race/load, and backup/restore/rollback/disaster recovery.

Binary materialization and guarded typed lifecycle dispatch are integration
requirements, not silently waived scope. Until a foreground Bench install and
verify command completes on a fresh local site, this repository change proves
only the standalone manifest contract. Browser role checks, customer approval,
legal/finance acceptance, production activation, performance, and restore
rehearsal remain separate evidence gates.
