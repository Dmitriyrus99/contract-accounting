# Manual gates checklist v0.20.0

**Status on Friday, August 21, 2026:** `AUTOMATED QUALIFICATION COMPLETE IN ITS PROVEN BOUNDARY / MANUAL, OPERATIONAL AND PRODUCTION GATES OPEN`.

Этот checklist не повышает статус до RC или release. Он фиксирует только то,
что ещё должно быть закрыто **после** локальных static/Bench/browser evidence и
published hosted CI PASS.

## Already proven in the automated boundary

- final-tree static qualification: `212/212 PASS`;
- exact-source disposable Bench gate on isolated `ca01.localhost`:
  `179/179 OK`;
- targeted Inspection runtime: `5/5 PASS`;
- scoped privacy runtime: policy `9/9`, alias/retention `24/24`,
  File boundaries `3/3`, residue `0`;
- source-controlled demo installer/reset/verifier and latest post-browser exact reset `79 → 0`;
- authenticated full-stack synthetic Engineer browser slice:
  own/foreign Form ACL, own-only List, foreign direct `403`,
  full-stack `socket.io` polling `200`;
- pinned repo-local browser runtime `playwright-core 1.62.1`,
  generated browser runtime forced into `.gitignore`;
- protected GitHub release flow for `main` and blocked `v*` tag path;
- published PR head with hosted `static-quality` PASS.

These are **engineering evidence only**. They do not replace Product Owner
approval, human UAT, restore, performance, Staging or production decisions.

## Gate 1 — Product Owner UI and Workspace approval

Owner: Product Owner + Product/QA

Goal:

- approve Workspace visibility;
- approve list columns, filters and sorting;
- approve form grouping, labels, options and translations;
- confirm timezone/user-facing date expectations for `Europe/Moscow`;
- confirm canonical end-to-end demo/UAT scenario before real users are invited.

Required evidence:

- explicit owner sign-off on the exact Workspace and form surface;
- approved checklist/result attached to the project docs or release notes.

Fail-close rule:

- until this gate is closed, real-user human UAT must not start.

## Gate 2 — Actual scanner integration

Owner: Security + Backend + QA

Goal:

- verify the real scanner integration, not only the synthetic adapter;
- confirm quarantine, Clean/Rejected handling, stream/download path,
  error semantics and audit trail under the real integration boundary.

Required evidence:

- terminal runtime proof on the real scanner-backed path;
- explicit negative proof for unsupported type/size/direct read/delete bypasses;
- final documented verdict for scanner-backed FR-06 attachment flow.

Fail-close rule:

- no production PII handling or release-qualified credential flow before this
  gate is closed.

## Gate 3 — Human UAT

Owner: HR + DPO/Privacy + Security + Product Owner

Goal:

- execute agreed real-user scenarios after Gate 1 approval;
- verify role behavior, UI meaning, process understanding and operational fit.

Required evidence:

- named participant list and role coverage;
- explicit pass/fail notes per scenario;
- documented defect list or signed acceptance.

Fail-close rule:

- automated browser evidence is not a substitute for human UAT.

## Gate 4 — Restore / rollback rehearsal

Owner: Release + Ops/Infra

Goal:

- prove that the qualified state can be restored safely;
- prove a rollback decision path before any production promotion.

Required evidence:

- backup/restore rehearsal transcript;
- rollback trigger and rollback execution notes;
- final verdict that restored system equals expected qualified state.

Fail-close rule:

- no RC/release promotion before restore/rollback is proven.

## Gate 5 — Performance / race / load

Owner: Backend + QA + Ops

Goal:

- verify concurrency-sensitive and throughput-sensitive paths beyond unit and
  targeted runtime regression scope.

Required evidence:

- agreed scenario set for race/load/performance;
- terminal results and thresholds;
- explicit sign-off or follow-up defects.

Fail-close rule:

- green local regression tests do not replace this gate.

## Gate 6 — Clean Staging qualification

Owner: Release + QA + Product

Goal:

- prove the app on a clean representative environment after the disposable
  qualification boundary.

Required evidence:

- install/migrate/verify sequence on clean Staging;
- smoke/UAT subset result on Staging;
- documented environment identity and verdict.

Fail-close rule:

- disposable isolated-site evidence is not Staging evidence.

## Gate 7 — Production approval and production-PII permission

Owner: Product Owner + Security + Privacy/DPO + Release

Goal:

- separately authorize production deployment;
- separately authorize production PII handling for Worker/Credential scope.

Required evidence:

- explicit production deployment approval;
- explicit production-PII permission;
- final go/no-go decision with accountable owners.

Fail-close rule:

- `PERSONNEL_READY` in synthetic/runtime qualification does not authorize
  production PII by itself.

## Non-promotion rule

Until **all** gates above are closed with explicit evidence, the overall status
must remain:

`NOT READY FOR PRODUCTION / RC NOT READY`

## Suggested execution order

1. Gate 1 — Product Owner UI and Workspace approval
2. Gate 2 — Actual scanner integration
3. Gate 3 — Human UAT
4. Gate 4 — Restore / rollback rehearsal
5. Gate 5 — Performance / race / load
6. Gate 6 — Clean Staging qualification
7. Gate 7 — Production approval and production-PII permission

This order is conservative on purpose: it minimizes the chance of spending
manual effort on later gates before the user-facing surface and security
boundary are accepted.
