# 13. First-release engineering backlog v1

**Source:** [Release Scope v1](12_release_scope_v1.md) and its [557-row matrix](12_release_scope_matrix_v1.csv).

**Rule:** order follows technical and human dependencies. No calendar promise is made until team capacity and owners are assigned.

| Order | ID | Work package | Priority | Size | Dependency | Acceptance result | Owner |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | `FR-01` | Unified quality/CI profile | P0 | M | current `0.19.0` working tree | deterministic standalone/schema/traceability/secret/diff/build jobs with exact versions and artifacts | Tech Lead |
| 2 | `FR-02` | ERPNext master-data boundary closure | P0 | M | `FR-01` | standard Address/Contact/Party linkage decided and tested; Warehouse/Workflow/Project/Task/Issue/Asset policy has positive/negative acceptance | Architect + Product Owner |
| 3 | `FR-03` | Production calendar and missing deadline sources | P0 | L | `FR-01`, `MG-CA-013` configuration | versioned Moscow/company/contract calendar; `TCA-A-14-09/13` sources; cut-offs and immutable snapshots PASS | Backend + Operations |
| 4 | `FR-04` | Scheduler, reminders, escalation and digest | P0 | L | `FR-03` | −3d/−1d/due/overdue/+1d/daily digest delivered in-app/email once per correlation key with retry/dead-letter | Backend + Operations |
| 5 | `FR-05` | Contractor privacy/legal package | P0 | M | named Legal/Privacy owner | signed purpose/legal basis/retention/permlevel/export/delete/audit matrix closes `MG-CA-015` | Legal/Privacy |
| 6 | `FR-06` | Contractor Worker/Credential/readiness | P0 | L | `FR-05`, `FR-01` | positive/expired/missing/mismatched credentials, Supplier/Employee isolation and readiness gate PASS | Backend + Security + HR |
| 7 | `FR-07` | Evidence Policy and mandatory photo | P0 | L | `FR-01` | versioned applicability, accepted evidence types, review, exception reason/approver and immutable audit PASS | Process Owner + Backend |
| 8 | `FR-08` | Waiting External / External Dependency flow | P0 | M | `FR-03`, `FR-04` | counterparty, request/expected/received dates, reminder/escalation, timeout action and resume are structured and idempotent | Project Operations + Backend |
| 9 | `FR-09` | Service Request release closure | P0 | M | `FR-03`, `FR-07`, `FR-08` | routing/SLA, remaining/paid successor, exact approval evidence, browser/cross-role and legal retention UAT PASS | Product Owner + Project Operations |
| 10 | `FR-10` | Invoice/Act/UPD/SF PDF/DOCX package | P0 | XL | `FR-01`, finance/legal templates | approved numbering/requisites/logo/seal/signature templates, render tests, one Act per Invoice, signed-scan storage and accounting UAT PASS | Finance + Legal + Backend |
| 11 | `FR-11` | Materials and tool custody | P0 | L | `FR-01`, warehouse process owner | material cost classification plus Tool issue/return/on-hand/exceptions and report PASS | Warehouse/Operations + Backend |
| 12 | `FR-12` | Mandatory report catalog | P0 | XL | `FR-03…11` source models | all DP-03 reports have role-safe UI/API/export, drill-down, empty/error states and representative-volume target | Product Owner + QA + Security |
| 13 | `FR-13` | Complete RBAC/security matrix | P0 | XL | stable `FR-02…12` APIs/reports | UI/API/report/print/export/private-file positive and negative suite for every first-release role | Security + QA |
| 14 | `FR-14` | Clean production-equivalent Staging | P0 | L | `FR-01…13` | Frappe+ERPNext+`contract_accounting` only; migrate/build/scheduler/email/print/monitoring smoke PASS | Release + Operations |
| 15 | `FR-15` | Load/race/performance qualification | P0 | L | `FR-14` | approved dataset/envelope, p95/error targets, no duplicates/loss/permission bypass | Performance QA + SRE |
| 16 | `FR-16` | Business/finance/legal/security UAT | P0 | XL | `FR-14`, fixes from `FR-15` | all signed representative scenarios PASS; no Sev-1/2 | QA Lead + Product Owner |
| 17 | `FR-17` | Restore/rollback/cutover rehearsal | P0 | L | immutable RC after `FR-16` | database/public/private/config restore, RPO/RTO, rollback and cutover sequence evidenced | Release + DBA |
| 18 | `FR-18` | Production launch and hypercare | P0 | L | all prior gates + approvals | observed deployment/smoke/monitoring/backup, then 10-workday hypercare exit and legacy retirement decision | Release + Operations + Product |

## Execution status — 2026-08-19

| Package | Current status | Remaining exit condition |
|---|---|---|
| `FR-01` | `PARTIAL`: current final-tree static `212/212 PASS`; exact-source disposable Bench gate `179/179 OK`; the draft PR has hosted `static-quality` PASS on an immutable published head; `main` protection and blocked `v*` tags verified | RC-specific gates remain: browser/human/restore/performance/Staging/production; не RC/release PASS |
| `FR-02` | `PARTIAL`: core CODE/schema/runtime PASS | Architect/Product Owner review, browser/role and race/load acceptance; Workflow/Communication stay open |
| `FR-03` | `PARTIAL`: engineering/schema/runtime boundary PASS | site-specific Operations/browser UAT, annual revision operations and performance/race; не release PASS |
| `FR-04` | `PARTIAL`: scheduler/delivery engineering and local E2E PASS | production activation, outgoing transport/receipt, worker heartbeat, Operations/RBAC/load UAT; не release PASS |
| `FR-05` | `DECISIONS FILLED / ALL NAMED SIGN-OFFS CONFIRMED` | human sign-off закрыт через аттестацию Product Owner; реализовать и проверить FR-06, затем получить отдельное production-PII permission до `MG-CA-015 PASS` |
| `FR-06` | `v0.20.0 CODE / FINAL-TREE STATIC 212/212 PASS / TARGETED INSPECTION 5/5 PASS / EXACT-SOURCE BENCH 179/179 OK / FULL-STACK SYNTHETIC ENGINEER SLICE PASS / LATEST PUBLISHED PR HEAD HOSTED CI PASS / UAT PENDING` | Workspace review, actual scanner integration, HR/DPO/Security UAT and production-PII permission |

## Immediate execution slice

`FR-01` имеет current final-tree static `212/212 PASS`; targeted Inspection на isolated `ca01.localhost` завершён `5/5 PASS`; current local tree прошёл exact-source Bench gate `179/179 OK`, а GitHub protection для `main` и blocked `v*` tags подтверждены. Historical hosted `static-quality` PASS на draft PR head `2865400` сохранён как provenance; current published draft-PR head `e924856` has hosted `static-quality` PASS via runs `32476386503` and `32476389650`. Это всё ещё не RC qualification: browser/human/restore/performance/Staging gates открыты. FR-05 human sign-off закрыт через аттестацию Product Owner. FR-06 v0.20.0 имеет CODE, scoped server/privacy automation, exact-source Bench evidence, source-controlled pinned browser runtime contract и узкий authenticated full-stack synthetic Engineer ACL slice, но не blanket browser/UAT PASS. Positive readiness ещё требует Workspace review, actual scanner integration и HR/DPO/Security UAT; production PII — отдельного разрешения. Независимый `FR-07` может проектироваться параллельно, но `FR-10…13` нельзя откладывать до конца: они определяют форму UAT и dataset для Staging.

Следующий зависимый шаг: завершить Workspace review и actual scanner integration UAT, затем HR/DPO/Security UAT и отдельное разрешение на production PII. Protected hosted status уже получен в текущей доказанной границе на immutable published PR head; любые более поздние local edits требуют нового run. RC не повышается до закрытия всех отдельных gates.
