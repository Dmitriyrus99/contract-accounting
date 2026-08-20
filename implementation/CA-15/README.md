# CA-15 — интеграционное укрепление и end-to-end trace

**Статус:** `CA-15 PARTIAL — READ-ONLY E2E TRACE + PROJECT INTEGRITY + OPERATIONS CROSS-ROLE + SERVICE REQUEST DISPOSITION CORE v0.16.3 VERIFIED`.

**Boundary correction — 2026-08-19:** последующий
[completeness audit](../CA-00/completeness_audit_v0_20_0_2026-08-19.md)
подтвердил runtime FAIL прямого cross-project доступа: scoped Engineer не
читает foreign Service Project, но читает связанный Service Request; scoped
Office Manager аналогично читает foreign Project Document. Термин
`permission-safe` ниже относится только к проверенным projection API/Page и
самому Service Project, а не к каждому direct Desk/List/Form/API/export/File
пути графа. CA-15 остаётся PARTIAL и получает обязательный row-policy stop-gate.

**Release scope update — 2026-08-19:** [Release Decisions v1](../../11_release_decisions_v1.md) исключает Client/Contractor interactive portals и Import Batch из first release. Их отсутствие требует negative evidence, но portal implementation/UAT и production Import Batch E2E больше не являются first-release blockers. Internal role, export/report, performance, scheduler, legal, restore, UAT и deployment gates остаются обязательными.

Инкремент объединяет ранее реализованные доменные контуры в одну permission-safe read projection. `get_end_to_end_trace` отвечает девятью сегментами «почему → где → когда → кто → что сделано → чем подтверждено → что выставлено → что оплачено → сколько заработали» и семью сквозными измерениями: подрядчики, материалы, затраты, документы, коммуникации, сроки и аудит. Каждая возвращённая строка содержит source DocType/name и drill-down; новый cache/trace/ledger SSOT не создавался.

`get_project_integrity_report` выполняет read-only project-scoped dry-run по typed и Dynamic Link связям, выдаёт stable issue key для missing/orphan/project-scope mismatch и не исправляет данные автоматически. Endpoint доступен только System Manager, Генеральному директору и Руководителю проектов; обычный Менеджер проектов может читать разрешённую E2E-проекцию, но finance/payment/margin остаются скрытыми.

Добавлены standard Desk Pages:

- `ferum-contract-360` — «Контракт 360°»;
- `ferum-operations` — «Операционная работа»;
- `ferum-director-control` — «Центр контроля директора».

Projection/integrity contract: [projection_v0_16_0.md](projection_v0_16_0.md).

Field-level OQ-CA-022 review: [field_disposition_v0_16_0.md](field_disposition_v0_16_0.md).

Runtime evidence: [runtime_evidence_v0_16_0_2026-08-18.md](runtime_evidence_v0_16_0_2026-08-18.md).

Implementation traceability: [traceability_v0_16_0.md](traceability_v0_16_0.md); browser/permission addenda: [traceability_v0_16_1.md](traceability_v0_16_1.md), [traceability_v0_16_2.md](traceability_v0_16_2.md).

Browser/role evidence and v0.16.1 permission correction: [browser_uat_v0_16_1_2026-08-18.md](browser_uat_v0_16_1_2026-08-18.md).

Operations cross-role evidence and v0.16.2 project boundary: [cross_role_uat_v0_16_2_2026-08-18.md](cross_role_uat_v0_16_2_2026-08-18.md).

Service Request disposition core and v0.16.3 evidence: [service_request_disposition_v0_16_3_2026-08-18.md](service_request_disposition_v0_16_3_2026-08-18.md); [traceability_v0_16_3.md](traceability_v0_16_3.md).

## Подтверждённые проверки

- standalone unit/schema suite: `138/138`, `OK`;
- targeted final CA-15 Frappe suite: `2/2`, `OK`;
- foreground full-app Frappe suite: `71/71`, `OK` with `--skip-test-records`;
- repeated migrate: PASS; три standard Page установлены;
- `bench build --app contract_accounting`: PASS после установки user-owned Node.js/Yarn toolchain;
- v0.16.1 migrate after director read/report DocPerm correction: PASS;
- manager/director real-browser role slice for all three named Pages: PASS;
- v0.16.2 Engineer/Accountant/Office Manager/Project Lead Operations browser slice: PASS;
- Engineer own-project positive / foreign-project negative and Launch API denial: PASS;
- five-request local browser smoke for E2E API: median `110 ms`, max `427 ms`; not representative-volume evidence;
- PEP 517 wheel v0.16.3: PASS (`315,467` bytes);
- scoped Ruff/compileall/JSON/JS syntax/diff-check: PASS;
- все 557 `07_traceability.csv` rows уникальны и имеют acceptance criterion + owner.

## Открытая граница

CA-15 не получает blanket PASS. Выполнены manager/director и Operations Engineer/Accountant/Office Manager/Project Lead browser slices; Service Request core disposition v0.16.3 bench-verified. Прямой project-graph authorization сейчас FAIL для как минимум Service Request/Engineer и Project Document/Office Manager; нужны общая row policy и полная negative entity/file/export matrix. Не выполнены Lawyer/Process Owner/System Manager, новые Request commands cross-role/browser UAT, API export/report и остальные internal cross-role сценарии, representative-volume performance/load/race, scheduler/retry/idempotency в production topology, clean-environment cutover/rollback rehearsal и legal retention/archive. Для OQ-CA-022 остаются Internal/Other typed owner, access-denied Process Event command и ручные/production gates. Client/Contractor interactive portals отсутствуют по scope; Import Batch должен оставаться disabled и пройти negative evidence. Production deployment и sign-off не выполнялись.
