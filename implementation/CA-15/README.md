# CA-15 — интеграционное укрепление и end-to-end trace

**Статус:** `CA-15 PARTIAL — READ-ONLY E2E TRACE + PROJECT INTEGRITY + MANAGER/DIRECTOR DESK-PAGE SLICE v0.16.1 VERIFIED`.

Инкремент объединяет ранее реализованные доменные контуры в одну permission-safe read projection. `get_end_to_end_trace` отвечает девятью сегментами «почему → где → когда → кто → что сделано → чем подтверждено → что выставлено → что оплачено → сколько заработали» и семью сквозными измерениями: подрядчики, материалы, затраты, документы, коммуникации, сроки и аудит. Каждая возвращённая строка содержит source DocType/name и drill-down; новый cache/trace/ledger SSOT не создавался.

`get_project_integrity_report` выполняет read-only project-scoped dry-run по typed и Dynamic Link связям, выдаёт stable issue key для missing/orphan/project-scope mismatch и не исправляет данные автоматически. Endpoint доступен только System Manager, Генеральному директору и Руководителю проектов; обычный Менеджер проектов может читать разрешённую E2E-проекцию, но finance/payment/margin остаются скрытыми.

Добавлены standard Desk Pages:

- `ferum-contract-360` — «Контракт 360°»;
- `ferum-operations` — «Операционная работа»;
- `ferum-director-control` — «Центр контроля директора».

Projection/integrity contract: [projection_v0_16_0.md](projection_v0_16_0.md).

Field-level OQ-CA-022 review: [field_disposition_v0_16_0.md](field_disposition_v0_16_0.md).

Runtime evidence: [runtime_evidence_v0_16_0_2026-08-18.md](runtime_evidence_v0_16_0_2026-08-18.md).

Implementation traceability: [traceability_v0_16_0.md](traceability_v0_16_0.md); browser/permission addendum: [traceability_v0_16_1.md](traceability_v0_16_1.md).

Browser/role evidence and v0.16.1 permission correction: [browser_uat_v0_16_1_2026-08-18.md](browser_uat_v0_16_1_2026-08-18.md).

## Подтверждённые проверки

- standalone unit/schema suite: `136/136`, `OK`;
- targeted final CA-15 Frappe suite: `2/2`, `OK`;
- foreground full-app Frappe suite: `69/69`, `OK` with `--skip-test-records`;
- repeated migrate: PASS; три standard Page установлены;
- `bench build --app contract_accounting`: PASS после установки user-owned Node.js/Yarn toolchain;
- v0.16.1 migrate after director read/report DocPerm correction: PASS;
- manager/director real-browser role slice for all three named Pages: PASS;
- five-request local browser smoke for E2E API: median `110 ms`, max `427 ms`; not representative-volume evidence;
- PEP 517 wheel v0.16.1: PASS (`305,538` bytes);
- scoped Ruff/compileall/JSON/JS syntax/diff-check: PASS;
- все 557 `07_traceability.csv` rows уникальны и имеют acceptance criterion + owner.

## Открытая граница

CA-15 не получает blanket PASS. Выполнен только manager/director browser slice; не выполнены остальные browser/cross-role/export/report сценарии, representative-volume performance/load/race, scheduler/retry/idempotency в production topology, migration dry-run/cutover/rollback rehearsal, backfill provenance и legal retention/archive. OQ-CA-022 disposition выполнен как review, но несколько `KEEP`/generic-target flows ещё не реализованы. Import Batch остаётся `INACTIVE / NOT PRODUCTION-PROVEN` до MG-CA-023 и не входит в release capabilities. Production deployment и sign-off не выполнялись.
