# 14. Quality/CI Profile v1

**Статус на 2026-08-19:** `CONFIGURED / LOCAL STATIC+BENCH PASS / HOSTED STATIC PASS / MANUAL RELEASE GATES OPEN`.

**Назначение:** один воспроизводимый профиль технических проверок первого выпуска. Профиль не подменяет RBAC/browser UAT, performance/load/race, restore, legal/finance/security approval, Staging или Production deployment.

## 1. Зафиксированный профиль

| Контур | Проверка | Реализация | Текущий evidence |
| --- | --- | --- | --- |
| Traceability | детерминированная сборка и сверка 557-row Release Scope | [generator](scripts/build_release_scope_matrix.py), `--check` | PASS: 557 unique IDs, exact distribution |
| Python correctness | `E4/E7/E9/F/I` на `contract_accounting`, `tests`, `scripts` | [ruff.toml](ruff.toml), Ruff `0.16.3` | PASS; 31 прежняя ошибка устранена |
| Python format | существующий долг не растёт | [.quality/ruff_format_baseline.json](.quality/ruff_format_baseline.json) | PASS ratchet; current 99 / reviewed baseline 121, removed 22, новые нарушения запрещены |
| Type safety | pure domain/application и quality scripts | [pyproject.toml](pyproject.toml), mypy `1.20.2`, Python target `3.11` | PASS: 15 modules |
| Static/runtime-independent tests | schema, domain policies и quality-wrapper guards | `python -m unittest discover -s tests -v` | PASS: 161/161 |
| Static assets | compileall, JSON parse, JS syntax, local Markdown links | [quality gate](scripts/quality_gate.py) | PASS: 66 JSON, 8 JS, 460 links |
| Secret boundary | только Git-visible text; ignored env/site/private/backups не читаются | [quality gate](scripts/quality_gate.py) | PASS: 414 files, findings 0 |
| Package | isolated sdist + wheel build | `build==1.5.0` | PASS: `0.19.0` sdist/wheel |
| Hosted static CI | pull request, push to `main`/`agent/**`, manual dispatch после появления workflow на default branch | [static-quality workflow](.github/workflows/static-quality.yml) | PASS: [run 32261790230](implementation/CA-00/hosted_ci_evidence_v0_19_0_2026-08-19.md), head `9f2cce9`, 18s |
| Bench runtime | installed apps, migrate, asset build, full app tests | [Bench gate](scripts/bench_quality_gate.py) | local WSL `89/89 OK`; [v0.19.0 evidence](implementation/CA-09/runtime_evidence_v0_19_0_2026-08-19.md) |

Pinned CI dependencies находятся в [requirements-ci.txt](requirements-ci.txt). Hosted workflow использует Python `3.11` и Node.js `22`; локальный static run выполнен на Windows Python `3.14.3`/Node `24.13.1`, а Bench runtime — на Python `3.11.14`/Node `22.23.1`.

## 2. Канонические команды

Из корня repository:

```text
python -m pip install --disable-pip-version-check -r requirements-ci.txt
python scripts/quality_gate.py
git diff --check
```

Из Linux/WSL с явно указанными non-production Bench и site:

```text
python scripts/bench_quality_gate.py \
  --bench-root /home/rus/contract-accounting-bench \
  --site ca01.localhost
```

Bench gate намеренно использует `--skip-test-records`. В текущем ERPNext `15.119.2` автоматический upstream test-record traversal обращается к удалённому `Payment Gateway` и падает до выполнения тестов приложения; test modules `contract_accounting` создают свои изолированные records и дают полный `89/89 OK` с утверждённым флагом. Wrapper проверяет transcript: маркер `FAILED` отклоняется даже при ошибочном exit code 0 от Bench, а PASS требует финальный `OK`. Запуск без флага остаётся диагностическим FAIL и не маскируется.

## 3. Правила изменения

- Версии quality dependencies изменяются отдельным reviewable change-set.
- Форматный baseline может только уменьшаться. Добавление файла в baseline требует отдельного waiver с причиной и владельцем.
- Static CI PASS не повышается до Bench, UAT или release PASS.
- Bench PASS считается относящимся к tree только при checksum-equivalent app sync либо immutable commit/tag.
- Remote CI получает PASS только после фактического GitHub Actions run; наличие YAML не является run evidence.

## 4. Открытые ворота FR-01

1. `DONE`: change-set зафиксирован и опубликован в разрешённой feature branch.
2. `DONE`: terminal hosted `static-quality` PASS на immutable head `9f2cce9`.
3. Подключить Bench gate как защищённый external/self-hosted status либо сохранять подписанный локальный runtime evidence для каждого RC.
4. Для RC повторить static+Bench профили на одном immutable SHA; затем отдельно выполнить RBAC, load/race, UAT, restore и deployment gates.
