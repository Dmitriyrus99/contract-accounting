# CA-00 — журнал исполнения baseline freeze

**Статус:** `OPEN / NOT FROZEN`

**Последнее обновление:** 2026-08-18T05:45:31+03:00

**Основание:** [06_roadmap.md](../../06_roadmap.md), `CA-00`; [08_open_questions.md](../../08_open_questions.md), OQ-CA-016 и MG-CA-016.

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

## MG-CA-016 gates

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

## Следующий исполнимый шаг

1. Повторить inventory на следующем code-bearing baseline и приложить hashes к release evidence.
2. Повторить [rollback rehearsal](rollback_rehearsal_2026-08-18.md) с безопасно предоставленным DB-root credential и закрыть MG-CA-016.
3. Продолжить CA-01 Frappe adapter/schema только с явным сохранением открытого MG-CA-016 в release gates.

Чистая Python domain policy CA-01 ведётся в отдельном репозитории и не изменяет AS-IS приложение или БД. Frappe schema/cutover не считаются разрешёнными или выполненными до закрытия соответствующих migration/rollback gates.
