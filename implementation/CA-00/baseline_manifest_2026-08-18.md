# Completion baseline manifest — v0.16.2

**Baseline date:** 2026-08-18.

**Manifest assembled:** 2026-08-19.

**Status:** `PARTIAL PASS — LOCAL/REMOTE ANNOTATED TAG + SOURCE/SCHEMA SNAPSHOT + CLEAN BASELINE TEST VERIFIED; LIVE INSTALLED-APP SNAPSHOT, RESTORE AND RELEASE GATES OPEN`.

**Decision source:** [Release Decisions v1](../../11_release_decisions_v1.md), `DP-04`.

**Secret boundary:** no `site_config.json`, environment variables, passwords, tokens, private keys, database credentials or secret values were read or copied into this manifest.

## 1. Immutable code anchor

| Field | Value | Status |
| --- | --- | --- |
| Repository | `contract-accounting` | RECORDED |
| Branch at decision | `main` | RECORDED |
| Baseline commit | `7145d872d45442117d5c114ce4c04c0c8f61d77b` | PASS |
| Commit subject | `fix(ca15): extend operations role boundary` | PASS |
| Commit timestamp | `2026-08-18T17:17:49+03:00` | PASS |
| Git tree | `300a0dee3e785e0d257419610cb35c23017b6b85` | PASS |
| Application version | `0.16.2` in `pyproject.toml` and `contract_accounting/__init__.py` | PASS |
| Local annotated tag | `completion-baseline-v0.16.2` | PASS |
| Tag object | `ccb4b73823618b325be60fdf6cbfad163115681d` | PASS |
| Peeled tag target | `7145d872d45442117d5c114ce4c04c0c8f61d77b` | PASS |
| Remote annotated tag | `completion-baseline-v0.16.2`; object `ccb4b73823618b325be60fdf6cbfad163115681d`; peeled target `7145d872d45442117d5c114ce4c04c0c8f61d77b` | PASS — pushed and independently read from `origin` at `2026-08-19T11:07:21+03:00` |
| Current `origin/main` | `5249e00849c96cb25fd0f13c5017fbf844db5f3d` / `0.16.3` | post-baseline delta |

The current `0.16.3` commit does not replace or move the baseline tag.

## 2. Source-tree fingerprint

| Measure | Value |
| --- | --- |
| Git tree entries | `339` |
| SHA-256 of canonical `git ls-tree -r --full-tree 7145d87` listing | `d2fe1b4c699866e2d7882db16d95d4cadcea861935190e82b52bb0b76c152b63` |
| DocType schema JSON | `48` |
| standard Page JSON | `5` |
| JavaScript files | `8` |
| application patch modules | `0` |
| `patches.txt` | empty `pre_model_sync` and `post_model_sync` sections |

Derived source-schema snapshot: [baseline_schema_snapshot_v0_16_2.csv](baseline_schema_snapshot_v0_16_2.csv).

| Snapshot check | Value |
| --- | --- |
| Rows | `53` = `48 DocType + 5 Page` |
| Git blob mismatches | `0` |
| CSV SHA-256 | `8a71c0f9c151c35978c598940019eca424e327b1b37606f395fb803d6a6f2f4d` |

## 3. Runtime/toolchain versions

The values below are from the preserved disposable `ca01.localhost` qualification evidence for the same Frappe/ERPNext bench. They are not a production-environment certification.

| Component | Recorded version / commit | Evidence state |
| --- | --- | --- |
| Frappe | `15.118.0` / `9b8d265b27a1dfb11c7aef21a533a127e14a0a5a` | recorded runtime evidence |
| ERPNext | `15.119.2` / `d707cb1e0e808fa6699d29a2bbaf9310983e94ac` | recorded runtime evidence |
| `contract_accounting` | `0.16.2` / `7145d87` | baseline Git object |
| Bench Python | `3.11.14` | recorded CA-15 evidence |
| System Python used in earlier setup | `3.12.3` | recorded/current tool observation; not Bench env |
| MariaDB client/server family | `10.11.14` | recorded/current tool observation |
| Redis | `7.0.15` | recorded/current tool observation |
| Node.js | `22.23.1` | recorded/current tool observation |
| Yarn | `1.22.22` | recorded/current tool observation |
| Bench package version | not separately captured | OPEN |

Frappe's recorded warning that MariaDB 10.11 is newer than its displayed tested boundary 10.8 remains an explicit qualification risk; this manifest does not certify that version combination for production.

## 4. Installed applications and standalone boundary

Expected and previously recorded disposable-site topology:

1. `frappe`;
2. `erpnext`;
3. `contract_accounting`.

Source-level boundary at baseline:

- `required_apps = ["erpnext"]`;
- no `ferum_custom` dependency, hook import, fixture dependency or shared schema is declared;
- [ADR-CA-0002](ADR-CA-0002-business-replacement-technical-standalone.md) requires `ferum_custom` to be absent on Staging/Production.

Evidence distinction:

| Evidence | Result |
| --- | --- |
| Preserved separate-site install evidence | Frappe + ERPNext + `contract_accounting` recorded; `ferum_custom` not used |
| Current `bench version` | `contract_accounting 0.16.3`, ERPNext `15.119.2`, Frappe `15.118.0` |
| Current `bench --site ca01.localhost list-apps` | NOT RUN TO COMPLETION: MariaDB `127.0.0.1:3317` refused connection because disposable DB service is stopped |
| Baseline-exact `list-apps` output | OPEN |

No services were started to close this read-only manifest step. Exact installed-app evidence must be repeated on a running approved Staging site.

## 5. Application configuration snapshot

### Hooks and standard-document integration

- install/migrate hooks: `after_install`, `before_migrate`, `after_migrate`;
- `File.on_trash` guards locked Project Document files;
- Sales Invoice, Purchase Invoice and Payment Entry hooks maintain project-context/finance projections without custom GL writes;
- permission query and `has_permission` hooks exist for Service Project and Contractor Assignment;
- `scheduler_events` is absent at baseline and remains a product gap, not a hidden configured job.

Git blobs:

| File | Git blob SHA-1 |
| --- | --- |
| `contract_accounting/hooks.py` | `08654f4d85bea3a170c6a904ed61231ffcbdf25a` |
| `contract_accounting/fixtures/role.json` | `78e7f5b5806ce4b7aadc5328f92217f0aac97783` |
| `contract_accounting/setup/custom_fields.py` | `ca1a9859211604e29245be3c42e991c48f992cb7` |
| `contract_accounting/patches.txt` | `8a2400ba623db7a98f1353d2eaaaa1f30dc7a7f7` |

### Fixtures and roles

Version-controlled fixture: `Role`.

Recorded roles:

1. Владелец процесса;
2. Генеральный директор;
3. Руководитель проектов;
4. Менеджер проектов;
5. Юрист;
6. Бухгалтер;
7. Инженер;
8. Офис-менеджер;
9. Подрядчик (`desk_access=0`).

Role presence does not prove complete RBAC. Full UI/API/report/print/export/private-file qualification remains open.

### Custom Fields

Two version-controlled ERPNext Custom Fields are installed idempotently:

| Target DocType | Field | Type / options |
| --- | --- | --- |
| Sales Invoice | `ferum_service_project` | Link → Ferum Service Project |
| Purchase Invoice | `ferum_service_project` | Link → Ferum Service Project |

### Workflows and scheduled jobs

| Item | Baseline source result | Interpretation |
| --- | --- | --- |
| Version-controlled Workflow fixture | none | no Workflow fixture claim |
| `scheduler_events` | absent | scheduler/notification topology OPEN |
| Version-controlled Scheduled Job Type fixture | none | live Staging inventory required |
| Reference process content | launch and billing-cycle templates created idempotently in install/migrate hooks | configuration content, not UAT |

## 6. Baseline validation evidence

### Fresh verification performed 2026-08-19

A detached temporary worktree at exact commit `7145d87` was created under the Windows temporary directory, path-validated, tested and removed.

| Check | Result |
| --- | --- |
| `git status --porcelain=v1` | empty / CLEAN |
| `git diff --check` | PASS |
| `py -m unittest discover -s tests` | `136/136 OK` |
| temporary worktree cleanup | PASS |

Operator correction: the first unit invocation was accidentally issued from the current `0.16.3` worktree and returned `138/138`. It was ignored. The command was immediately repeated after `Push-Location` into the path-validated baseline worktree and returned authoritative `136/136 OK`.

### Preserved v0.16.2 qualification evidence

From [cross-role UAT v0.16.2](../CA-15/cross_role_uat_v0_16_2_2026-08-18.md):

- repeated `bench --site ca01.localhost migrate` — PASS;
- targeted Workspaces Frappe suite — `2/2 OK`;
- standalone suite — `136/136 OK`;
- full-app Frappe suite with `--skip-test-records` — `69/69 OK` in `334.096 s`;
- `bench build --app contract_accounting` — PASS;
- wheel `contract_accounting-0.16.2-py3-none-any.whl` — `307,455` bytes;
- scoped Ruff, Page JSON, JS syntax and diff check — PASS;
- real-browser Engineer/Accountant/Office Manager/Project Lead Operations slice — PASS within its stated role boundary.

These results do not prove API export/report, representative load/race, scheduler/retry topology, legal/privacy, full RBAC, restore/cutover, UAT sign-off or production deployment.

Evidence Git blobs at baseline:

| Evidence file | Git blob SHA-1 |
| --- | --- |
| `implementation/CA-15/cross_role_uat_v0_16_2_2026-08-18.md` | `cefcd5de3c99c7313b08b67a673746b3c354c27e` |
| `implementation/CA-15/browser_uat_v0_16_1_2026-08-18.md` | `bba0da3d34889a02d60bef21e476b75ff7b80cc7` |
| `implementation/CA-15/runtime_evidence_v0_16_0_2026-08-18.md` | `402480c5c6493c70ba0969e777a4e2e0f757694c` |
| `implementation/CA-15/traceability_v0_16_2.md` | `44176796b1f4110b3554eef368e13b76943a68b7` |

## 7. Sanitized configuration boundary

The baseline decision requests a sanitized site configuration. This manifest records only non-secret facts already present in source/evidence:

- disposable site identifier: `ca01.localhost`;
- timezone policy approved separately as `Europe/Moscow` but not yet qualified as live site configuration;
- disposable MariaDB endpoint family `127.0.0.1:3317` and Redis ports were previously recorded in runtime evidence;
- production hostname, credentials, encryption keys, mail credentials and secret configuration are not present.

Because reading `site_config.json` is prohibited, a sanitized live configuration export requires a purpose-built safe command or operator-provided redacted artifact. It remains OPEN.

## 8. Gate ledger

| Gate | Status | Closure evidence |
| --- | --- | --- |
| Baseline commit/version | PASS | exact Git object and version files |
| Local annotated tag | PASS | tag object `ccb4b73823618b325be60fdf6cbfad163115681d` |
| Remote tag sync | PASS | `git push origin refs/tags/completion-baseline-v0.16.2`; remote object `ccb4b73823618b325be60fdf6cbfad163115681d`; remote peeled target equals baseline commit |
| Clean baseline worktree | PASS | temporary detached worktree status empty |
| Source/schema snapshot | PASS | 339-entry fingerprint + 53-row verified CSV |
| Baseline standalone tests | PASS | `136/136 OK` |
| Frappe/migrate/build slice | RECORDED PASS | preserved v0.16.2 disposable-site evidence |
| Baseline-exact live `list-apps` | OPEN | running approved Staging output |
| Sanitized live site configuration | OPEN | safe/redacted non-secret export |
| Live schema/Workflow/Role/Scheduled Job inventory | OPEN | repeat on approved Staging |
| Full backup restore | OPEN | credential-safe restore rehearsal |
| Remote release evidence | OPEN | tag push and immutable release package |

## 9. Verdict

`DP-04` is materially advanced: the exact commit is locally and remotely anchored by the same annotated tag, source/schema are fingerprinted, and the baseline is independently clean with `136/136` standalone tests. `MG-CA-016` is not fully PASS until exact live installed-app/config/schema inventory and restore evidence are obtained.

No production readiness or deployment claim is made.
