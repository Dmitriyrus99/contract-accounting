# Legacy business-data disposition and MG-CA-001 N/A protocol

**Status:** `LIVE INVENTORY + LOCAL CONTROL BACKUP PASS / TEST-ONLY OWNER DECISION RECORDED / DATA OWNER SIGNATURE + OFF-HOST RETENTION OPEN`.

**Decision source:** [Release Decisions v1](../../11_release_decisions_v1.md), `DP-02`.

**Purpose:** prove that legacy contains no real business records that must be migrated, create one recoverable control backup, and close `MG-CA-001` as `N/A` without reading or publishing sensitive record contents.

## 1. Current evidence boundary

The owner decision states that legacy records are test-only. This is an approved disposition, not yet signed inventory evidence.

| Field | Value |
| --- | --- |
| Legacy environment identifier | Docker Compose project `ferum-vstand`; existing site volume `ferum-vstand_sites` |
| Legacy site | owner-facing `ferum.localhost` → internal Bench site `dev.localhost`, confirmed by owner |
| Data Owner | `UNKNOWN — signature required` |
| Inventory executor/reviewer | Codex execution; Data Owner review/signature still required |
| Inventory timestamp / timezone | `2026-08-19`, completed before backup at `11:18:17+03:00` / `Europe/Moscow` |
| Real business records | `0` per approved `DP-02`; aggregate database is non-empty and classified test-only; formal Data Owner signature remains open |
| Control backup | PASS — local DB/public/private/config backup, exit `0`; non-secret artifact hashes recorded below |
| `MG-CA-001` | `N/A BY APPROVED DECISION / TECHNICAL EVIDENCE PASS / FORMAL SIGN-OFF OPEN` |

No business-row value, filename, attachment content, PII or secret configuration was opened or printed. Execution used metadata identifiers and aggregate `COUNT` operations only.

### 1.1. Execution attempt — 2026-08-19

- Owner-confirmed target: `ferum.localhost`.
- WSL search: no `sites/ferum.localhost` under the available native Bench or Windows-mounted Bench/Desktop tree.
- Docker search: no `ferum.localhost` directory or backup path in any local volume; existing `ferum-vstand` sites are `ci.localhost`, `dev.localhost`, `w2t12.localhost`, `w2t12b.localhost`; existing `ferum-performance` sites are two explicitly named verification sites.
- Read-only `bench list-apps` on those alternate sites confirmed `frappe`, `erpnext`, `ferum_custom`; it did not establish that any of them is the owner-confirmed legacy target.
- No substitute site was selected, no new site was created, and no database/file inventory or backup was run.
- The nine Ferum base containers started for discovery were stopped after inspection and returned to their prior stopped state; unrelated Docker/MCP containers were not changed.
- No secret configuration, credential, PII, business record value, attachment name or attachment content was read.

### 1.2. Confirmed execution — `ferum.localhost` → `dev.localhost`

- The owner confirmed that `dev.localhost` is the internal name of `ferum.localhost`.
- Existing containers were started without recreate/build/migrate; MariaDB reached `healthy`.
- `bench --site dev.localhost list-apps` returned `frappe 15.115.0`, `erpnext 15.117.0`, `ferum_custom 0.0.1`; `contract_accounting` is absent.
- Mounted `ferum_custom` source is clean at commit `5e7be092788832e91dfb70175c64c46cc94ef5ae`.
- Aggregate inventory completed without selecting names or field values. The site contains a substantial test dataset, not an empty database.
- Full compressed backup completed with exit code `0`; details and hashes are in section 6.
- The five base containers started for this execution were stopped afterward. A separate read-only volume mount confirmed that all four backup artifacts persisted and that the three recorded non-secret hashes were unchanged.

## 2. Safe execution rules

1. Run only against the explicitly confirmed legacy test environment.
2. Do not open or print `site_config.json`, environment variables, credentials, file contents, PII, document text, invoices or attachments.
3. Capture aggregate counts and configuration identifiers only.
4. Record total rows and Data Owner classification `TEST / REAL / MIXED / UNKNOWN`.
5. If any category is `REAL`, `MIXED` or `UNKNOWN`, stop: `MG-CA-001` cannot be N/A and clean-start disposition returns to change control.
6. Do not delete, migrate, transform or archive records in this inventory step.
7. Backup artifact contents and secret configuration must not be committed to this repository.

## 3. Environment identity

Fill before database access:

| Check | Result | Evidence reference |
| --- | --- | --- |
| Environment/site owner confirms exact target | PASS | owner message: `site: ferum.localhost` |
| Environment is legacy `ferum_custom`, not new `contract_accounting` Staging/Production | PASS | owner mapping + `list-apps`; existing `ferum-vstand` site |
| Installed-app list captured | PASS | `frappe 15.115.0`, `erpnext 15.117.0`, `ferum_custom 0.0.1` |
| `contract_accounting` not used as source of legacy business records | PASS | absent from installed-app list |
| Backup destination and retention owner approved | PARTIAL | local volume destination exists; off-host location and retention owner remain open |
| Read-only inventory command approved | PASS | execution of approved package; aggregate counts only |

## 4. Aggregate business inventory

Do not copy record names or field values into this artifact.

| Category | Representative DocType / storage | Total count | Data Owner classification | Notes/evidence |
| --- | --- | ---: | --- | --- |
| Contracts and projects | Ferum Contract, Ferum Service Project, Project | 343 | TEST — `DP-02`; signature open | `1 + 341 + 1` |
| Contract/project links | Ferum Project Contract Link and related link rows | 1 | TEST — `DP-02`; signature open | aggregate count |
| Objects, systems and scope | project/service objects, object systems, scope | 0 | TEST — `DP-02`; signature open | all representative custom tables zero |
| Customers and contacts | Customer, Contact, Address, Ferum Customer Tax Profile | 33 | TEST — `DP-02`; signature open | `11 + 21 + 0 + 1` |
| Suppliers/contractors/personnel | Supplier and Ferum Contractor Settlement | 10 | TEST — `DP-02`; signature open | `10 + 0`; user count recorded separately |
| Requests and findings | Ferum Service Request and available request/defect sources | 0 | TEST — `DP-02`; signature open | aggregate count |
| Maintenance and visits | schedules, visits, checklist rows | 0 | TEST — `DP-02`; signature open | aggregate count |
| Documents and files | generation jobs, billing artifacts and File rows | 6 | TEST — `DP-02`; signature open | `4 + 0 + 2`; physical-file counts are zero |
| Sales invoices | Sales Invoice | 120 | TEST — `DP-02`; signature open | all-site aggregate |
| Purchase invoices/costs | Purchase Invoice and Ferum Material Expense | 11 | TEST — `DP-02`; signature open | `11 + 0`; opening balances listed below |
| Payments | Payment Entry | 7 | TEST — `DP-02`; signature open | all-site aggregate |
| Audit/status history | Ferum Audit Log, Notification Log, Reconciliation Log | 4 | TEST — `DP-02`; signature open | `1 + 2 + 1` |
| Users and business roles | non-system User + Ferum role assignment rows | 18 | TEST — `DP-02`; signature open | `14 + 4`; not an additive person count |
| Import/integration batches | Ferum Import Batch, Import Issue, External Object Reference | 0 | TEST — `DP-02`; signature open | aggregate count |
| Other business-bearing custom DocType | non-zero rows detailed in section 4.1 | 2,411 total custom rows | TEST — `DP-02`; signature open | 2,409 parent + 2 child rows; overlaps category rows above |

### 4.1. Non-zero custom DocType counts

Zero-count custom DocType are covered by the 55-DocType metadata inventory but omitted from this compact table.

| DocType | Count |
| --- | ---: |
| Ferum Audit Log | 1 |
| Ferum Billing Event | 4 |
| Ferum Billing Output | 4 |
| Ferum Company Document Settings | 1 |
| Ferum Company Signer | 1 |
| Ferum Company Tax Account | 1 |
| Ferum Contract | 1 |
| Ferum Customer Tax Profile | 1 |
| Ferum Document Generation Job | 4 |
| Ferum Legal Number Counter | 1,760 |
| Ferum Notification Log | 2 |
| Ferum Opening Payable | 10 |
| Ferum Opening Receivable | 230 |
| Ferum Project Contract Link | 1 |
| Ferum Project Finance Summary | 48 |
| Ferum Reconciliation Log | 1 |
| Ferum Service Project | 341 |

Classification rule:

- `TEST` — Data Owner explicitly confirms all rows are synthetic/training/disposable;
- `REAL` — at least one record represents actual customer, contract, work, document, invoice, payment or person;
- `MIXED` — test and real records coexist;
- `UNKNOWN` — owner cannot prove classification.

Only `TEST` for every populated category allows `real business records = 0`.

## 5. File and attachment inventory

Capture counts only:

| Item | Count | Classification | Evidence |
| --- | ---: | --- | --- |
| public File rows | 2 | TEST — `DP-02`; signature open | aggregate `File.is_private=0` |
| private File rows | 0 | TEST — `DP-02`; signature open | aggregate `File.is_private=1` |
| physical public files | 0 | TEST — `DP-02`; signature open | filesystem count only |
| physical private files | 0 | TEST — `DP-02`; signature open | filesystem count only |
| orphan File rows/files | NOT EVALUATED | OPEN | would require reading filename/URL mappings; not needed for migration disposition |

No file content, filename containing PII, hash of secret configuration or attachment preview is stored here.

## 6. Control backup

Required backup scope:

- database;
- public files;
- private files;
- site configuration backup handled securely outside this repository;
- application/commit/version manifest.

| Evidence field | Value |
| --- | --- |
| Approved backup command/runbook | `bench --site dev.localhost backup --with-files --compress` |
| Start/end timestamp | `2026-08-19 11:18:17–11:18:19 +03:00` |
| Exit code | `0`; Frappe: `successfully completed with files` |
| Database artifact identifier/path | `sites/dev.localhost/private/backups/20260819_111817-dev_localhost-database.sql.gz` |
| Public files artifact identifier/path | `sites/dev.localhost/private/backups/20260819_111817-dev_localhost-files.tgz` |
| Private files artifact identifier/path | `sites/dev.localhost/private/backups/20260819_111817-dev_localhost-private-files.tgz` |
| Non-secret artifact sizes | DB `1,590,457` bytes; public `135` bytes; private `136` bytes; config backup present `222` bytes |
| SHA-256 of database/public/private backup artifacts | DB `54529dcb537de6a55225360bf7c6096dad129955eb7eafd234b814fd3a4f1e56`; public `eb7e42bf048db70e05c9606c34a3e2d5af443846bdee3e1a492f9388d551ed75`; private `1e6fa12e03476c8fd99abc0f2c8d29f7fcab00adcb144d91b73bf0ca554f56de` |
| Secret configuration boundary | config backup exists at the same timestamp; content and hash intentionally not read or recorded |
| Off-host/retention location owner | OPEN — current artifacts are in local Docker site volume |
| Retain until | successful production launch sign-off |
| Restore test reference | OPEN — separate release gate |

Backup files and secret configuration must remain outside Git.

## 7. N/A act

Complete only after all inventory rows are classified `TEST` and backup evidence exists.

```text
Decision: legacy business data migration = NOT REQUIRED
Real business records requiring migration: 0
Legacy database copy into production: PROHIBITED
Initial production data: recreate through approved UI/setup/reference import
MG-CA-001: N/A BY APPROVED DP-02; FORMAL SIGN-OFF PENDING
Control backup: 20260819_111817-dev_localhost-*; hashes recorded in section 6
Legacy retention: read-only until successful production launch sign-off
Data Owner: <name / signature / date>
Product Owner: <name / signature / date>
Release Manager: <name / signature / date>
```

## 8. Fail-closed verdict

Current verdict: `TECHNICAL INVENTORY + LOCAL CONTROL BACKUP PASS / MG-CA-001 N/A BY DECISION / FORMAL DATA OWNER SIGNATURE + OFF-HOST RETENTION OPEN`.

The owner-confirmed site mapping was executed against the existing legacy environment. Aggregate counts and a local full backup are evidenced, and `DP-02` classifies all legacy records as test-only. The gate is not promoted to fully signed `N/A PASS` until a named Data Owner signs the classification and an approved retention owner/location protects an off-host copy. Restore testing remains a separate release gate and was not inferred from backup success.
