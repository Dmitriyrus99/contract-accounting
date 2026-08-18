# CA migration evidence template

Использовать отдельную копию для каждого patch/reconciliation/cutover. Пустое поле означает `NOT EVIDENCED`, а не PASS.

## 1. Identity

- Increment / change ID:
- Repository / branch:
- Pre-change commit SHA:
- Post-change commit SHA:
- Clean tree evidence:
- Tracked diff SHA-256:
- Untracked files: `0` / приложенный manifest:
- Frappe / ERPNext / MariaDB versions:
- Site/environment identifier без hostname, credentials и PII:
- Executor / reviewer / timestamp / timezone:

## 2. Scope and boundaries

- Normative REQ / owner decisions:
- Exact schema/config/data scope:
- Explicitly excluded scope:
- ERPNext SSOT affected:
- Custom SSOT/read-model affected:
- Secrets/PII handling:

## 3. Preconditions

- Backup identifier and hash:
- Installed-app and patch inventory:
- Schema/index snapshot:
- Workflow/Custom Field/roles/Scheduled Job Type snapshot:
- Required manual approvals:
- Open blockers:

## 4. Dry-run

- Exact read-only command:
- Exit code:
- `scanned`:
- `created`:
- `updated`:
- `skipped`:
- `conflict`:
- Error-log artifact/hash:
- Ambiguous records routed to manual review:
- Second dry-run result / idempotency delta:

## 5. Apply

- Exact mutating command approved by:
- Start/end timestamps:
- Exit code:
- Applied patch rows:
- Before/after schema hashes:
- `scanned/created/updated/skipped/conflict`:
- Retry/restart behavior:

## 6. Verification

- Positive tests and raw output artifact:
- Negative/duplicate tests and observed reject:
- Permission tests, including API/report/export paths:
- Forward/reverse link integrity:
- Orphan/duplicate counts:
- Financial reconciliation and proof of no custom GL mutation:
- File/legal artifact before/after hashes:
- UAT/legal/privacy/DB gates with named approver:

## 7. Rollback rehearsal

- Exact rollback command:
- What rollback may remove or revert:
- What rollback must preserve:
- Start/end timestamps and exit code:
- Restored schema/config hashes:
- Preserved legal files/business evidence hashes:
- Residual differences and approved exceptions:
- Re-apply result after rollback:

## 8. Final verdict

- `PASS` / `FAIL` / `NOT EVIDENCED`:
- Reviewer independent from generator:
- Remaining manual gates with owner/status:
- Release capability statement:
- Links to immutable evidence artifacts:
