# CA-00 — журнал исполнения baseline freeze

**Статус:** `HISTORICAL DISCOVERY BASELINE RECORDED / COMPLETION BASELINE EVIDENCE OPEN`

**Последнее обновление:** 2026-08-19

**Основание:** [06_roadmap.md](../../06_roadmap.md), `CA-00`; [08_open_questions.md](../../08_open_questions.md), OQ-CA-016 и MG-CA-016.

**Supersession:** [Release Decisions v1](../../11_release_decisions_v1.md), `DP-04`, утверждает completion baseline репозитория `contract-accounting` — `7145d87` / `0.16.2`. [Baseline manifest](baseline_manifest_2026-08-18.md), local/remote annotated tag, schema snapshot and clean `136/136` standalone evidence recorded 2026-08-19; live inventory/restore remain OPEN. Настоящий W2/`ferum_custom` раздел сохраняется только как discovery provenance. Текущий `5249e00` / `0.16.3` — post-baseline delta.

## Результат текущего шага

Отдельный repository baseline аналитического проекта опубликован в `Dmitriyrus99/contract-accounting`: commit `33befac`, tag `discovery-baseline-2026-08-18`. Он фиксирует discovery/CA-00 пакет и не подменяет code-bearing baseline приложения Frappe. Clean post-W2 кандидат приложения найден на `63634f5`, но его remote sync остаётся вне этого репозитория и не выполнялся.

| Кандидат | Branch / HEAD | Состояние | Вердикт |
| --- | --- | --- | --- |
| running `ferum-vstand-backend-1:/home/frappe/frappe-bench/apps/ferum_custom` | `w2-objects-core` / `63634f5c5191fdac566add7a69d56ee59bedcb24` | clean; ahead of origin by 16 | актуальный post-W2 baseline candidate; tag/push/rehearsal ещё не выполнены |
| `Вспомогательные/Claude ferum_custom/apps/ferum_custom` | `w2-objects-core` / `b1fcaac5d75a67f8b1ab8af6bdb9049cbe02d354` | 37 modified + 9 untracked | устаревший pre-merge W2 snapshot, не baseline |
| `Вспомогательные/Codex ferum_custom` | `codex/final-qualification` / `c97c34ac63bade8b4c999f46ddbb52e7fe838db5` | clean | более старый неполный snapshot, не baseline |
| `C:/Users/Dmitr/OneDrive/Desktop/МойПроект/frappe-bench` | Git metadata отсутствует | в корне найден только каталог `apps`; runnable site не подтверждён | не является воспроизводимым checkout |

Текущий fingerprint актуального `ferum-vstand` checkout:

- tracked binary diff SHA-256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty diff);
- modified files: `0`;
- untracked files: `0`;
- staged changes: отсутствуют;
- discovery baseline tag создан в отдельном проектном репозитории; code-bearing tag приложения не создавался.

W2 runtime/DB и clean-tree gates подтверждены ниже, но code-bearing tag/remote-sync и полный restore ещё не закрыты. Поэтому MG-CA-016 в целом остаётся OPEN.

Устаревший локальный Claude snapshot был статически приведён к `pre-commit` PASS точечными type-only правками; те же исправления уже присутствуют в истории актуального стенда (`W2-T12`, `docs/plan/09_task_breakdown.md`). Локальный snapshot не повышается до baseline.

## W2 readiness

### W2-T12

В dirty tree уже присутствуют:

- server-side неизменяемость `Ferum Project Object.contract` по REQ-DATA-120;
- `services/scope_rule_isolation.py` с производными User Permission по договору;
- регистрации project/link/contract hooks;
- `tests/test_scope_rule_isolation.py` с 16 permission-сценариями.

В рамках этого шага устранены 24 ошибки `mypy` в восьми файлах устаревшей локальной копии без изменения бизнес-правил. На актуальном стенде выполнены runtime-тесты:

| Проверка | Результат | Ограничение |
| --- | --- | --- |
| `git diff --check` | PASS | статическая проверка tracked diff |
| `python3 -m compileall -q ferum_custom` | PASS | не импортирует Frappe runtime и не проверяет DB |
| `pre-commit run --files …` | PASS | trailing whitespace, EOF, merge markers, large files, private keys, ruff, ruff-format и full-package mypy |
| `bench --site w2t12b.localhost run-tests --app ferum_custom --module ferum_custom.tests.test_scope_rule_isolation` | PASS: 17 tests, 7.799s | актуальный post-W2 стенд |
| `bench --site w2t12b.localhost run-tests --app ferum_custom --module ferum_custom.ferum_custom.doctype.ferum_project_object.test_ferum_project_object` | PASS: 31 tests, 4.510s | включает REQ-DATA-120 |

Fail-open край ПМ без единой проектной/договорной User Permission не является незакрытой догадкой: OQ-226 принят владельцем 2026-08-17 вариантом (а) как временное следствие до блока OQ-223, а актуальный модуль содержит два теста фактического поведения. W2-T12 подтверждён как `permission-tested`; TARGET CA-01 обязан устранить переходную модель, а не молча переинтерпретировать этот W2 акт.

### W2-V02

`W2-V02` — `EXECUTED PASS`, исполнен владельцем 2026-08-17. Immutable protocol находится в актуальном repo: `docs/reports/w2_v02_protocol_2026-08-17.md`. Подтверждены MariaDB 10.6.27, полные `VARCHAR(422)`/`VARCHAR(563)` generated columns, `UNIQUE` indexes без prefix (`SUB_PART = NULL`), позитивные вставки и четыре ожидаемых DB rejects 1062. Текущая read-only инспекция сайта `w2t12b.localhost` повторно показала обе формулы и оба индекса.

Live inventory зафиксирован в [live_inventory_w2t12b_2026-08-18.md](live_inventory_w2t12b_2026-08-18.md).

## Completion baseline gates — DP-04 / MG-CA-016

| Gate | Status | Evidence |
| --- | --- | --- |
| exact commit/version | PASS | `7145d87` / `0.16.2` |
| local annotated tag | PASS | `completion-baseline-v0.16.2` → `7145d87` |
| remote tag sync | PASS | annotated tag object `ccb4b73823618b325be60fdf6cbfad163115681d`; remote peeled target `7145d872d45442117d5c114ce4c04c0c8f61d77b` |
| source/schema fingerprint | PASS | [manifest](baseline_manifest_2026-08-18.md), [53-row snapshot](baseline_schema_snapshot_v0_16_2.csv), checksum sidecar |
| clean baseline test | PASS | detached worktree clean, diff-check PASS, `136/136 OK` |
| baseline-exact live apps/config/schema | OPEN | disposable DB stopped; no secret config read |
| full restore | OPEN | credential-safe rehearsal required |
| Release Scope v1 | PASS | [557-row matrix](../../12_release_scope_matrix_v1.csv), [summary](../../12_release_scope_v1.md), [backlog](../../13_first_release_backlog_v1.md) |
| local quality profile | HISTORICAL v0.19.0 PASS | committed baseline static `161/161` + disposable Bench `89/89`; historical, not v0.20.0 current-tree qualification; [v0.19.0 evidence](../CA-09/runtime_evidence_v0_19_0_2026-08-19.md) |
| `FR-02` master-data core | PASS (automation) | [boundary](master_data_boundary_v0_17_0.md), [traceability](traceability_v0_17_0_master_data.md); owner/browser/race gates OPEN |
| hosted CI on latest published PR head | PASS | see the draft PR checks for the exact immutable SHA and run URLs; any later local edits require a fresh run |

Legacy `MG-CA-001=N/A` execution/sign-off protocol: [legacy_data_disposition_2026-08-19.md](legacy_data_disposition_2026-08-19.md). Count-only inventory and local full backup PASS; Data Owner signature, off-host retention and separate restore gate remain OPEN.

## Historical W2 MG-CA-016 gates

| Gate | Owner | Статус | Evidence для закрытия |
| --- | --- | --- | --- |
| clean post-W2 SHA | Release Manager | READY | `63634f5c5191fdac566add7a69d56ee59bedcb24`, clean tree, empty diff hash |
| discovery repository baseline | Release Manager | PASS | `contract-accounting` commit `33befac`, tag `discovery-baseline-2026-08-18` |
| code-bearing baseline tag + remote sync | Release Manager | OPEN | approved application tag name, push result and remote SHA |
| W2-T12 permission suite | Security reviewer | PASS | 17 permission tests + 31 Project Object tests; prior independent acceptance recorded in repo |
| W2-V02 physical keys | DB owner | PASS | owner-executed immutable protocol + current read-only schema inspection |
| live metadata inventory | Release Engineer | RECORDED | [live inventory](live_inventory_w2t12b_2026-08-18.md); повторить на frozen baseline |
| baseline dataset/configuration | Product Owner + Release Engineer | OPEN | versioned fixture/config manifest без секретов |
| rollback rehearsal | Release Engineer | PARTIAL | backup и compensating rollback PASS; full `bench restore` остановлен на credential prompt — [протокол](rollback_rehearsal_2026-08-18.md) |
| ERPNext/custom + Party Identity boundary | Architect | RECORDED | [ADR-CA-0001](ADR-CA-0001-erpnext-custom-party-boundary.md) |
| Party Identity owner decision audit | Architect | EVIDENCE GATE OPEN | [audit](party_identity_owner_decision_audit_v0_17_0.md) |

## Следующий исполнимый шаг

1. Зафиксировать/push текущий change-set только после отдельного разрешения и получить terminal hosted `static-quality` PASS.
2. На работающем approved Staging повторить installed apps/schema/Workflow/Role/Scheduled Job inventory без чтения secret values.
3. Повторить [rollback rehearsal](rollback_rehearsal_2026-08-18.md) с безопасно предоставленным DB-root credential.
4. Продолжить closure по `FR-05` legal/privacy package; закрыть ручные gates `FR-02/03/04` параллельно.

Чистая Python domain policy CA-01 ведётся в отдельном репозитории и не изменяет AS-IS приложение или БД. Frappe schema/cutover не считаются разрешёнными или выполненными до закрытия соответствующих migration/rollback gates.
