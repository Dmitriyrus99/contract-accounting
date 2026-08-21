# 14. Quality/CI Profile v1

**Статус на 2026-08-21:** `CONFIGURED / PUBLISHED REVIEW CANDIDATE v0.20.0 / HOSTED STATIC CI PASS / STATIC 212/212 PASS / EXACT-SOURCE BENCH 179/179 OK / FULL-STACK SYNTHETIC ENGINEER SLICE PASS / HUMAN UAT, RC AND RELEASE NOT READY`.

**Назначение:** один воспроизводимый профиль технических проверок первого выпуска. Профиль не подменяет RBAC/browser UAT, performance/load/race, restore, legal/finance/security approval, Staging или Production deployment.

## 1. Зафиксированный профиль

| Контур | Проверка | Реализация | Текущий evidence |
| --- | --- | --- | --- |
| Traceability | детерминированная сборка и сверка 557-row Release Scope | [generator](scripts/build_release_scope_matrix.py), `--check` | PASS: 557 unique IDs, exact distribution |
| Python correctness | `E4/E7/E9/F/I` на `contract_accounting`, `tests`, `scripts` | [ruff.toml](ruff.toml), Ruff `0.16.3` | PASS; 31 прежняя ошибка устранена |
| Python format | существующий долг не растёт | [.quality/ruff_format_baseline.json](.quality/ruff_format_baseline.json) | PASS ratchet; current 94 / reviewed baseline 121, removed 27, новые нарушения запрещены |
| Type safety | pure domain/application и quality scripts | [pyproject.toml](pyproject.toml), mypy `1.20.2`, Python target `3.11` | PASS: 17 modules |
| Static/runtime-independent tests | schema, domain policies и quality-wrapper guards | `python -m unittest discover -s tests -v` | current final-tree local review candidate `v0.20.0`: PASS `212/212`; earlier `161/161` is historical baseline |
| Static assets | compileall, JSON parse, JS syntax, local Markdown links | [quality gate](scripts/quality_gate.py) | PASS в составе current static `212/212` profile |
| Secret boundary | только Git-visible text; ignored env/site/private/backups не читаются | [quality gate](scripts/quality_gate.py) | PASS в составе current static profile; findings 0 |
| Package | isolated sdist + wheel build | `build==1.5.0` | PASS: `0.20.0` sdist/wheel |
| Hosted static CI | pull request, push to `main`/`agent/**`, manual dispatch после появления workflow на default branch | [static-quality workflow](.github/workflows/static-quality.yml) | current published draft-PR head `2e27643` PASS via run `32470646882`; historical PASS: draft PR head `2865400` via runs `32425117645` and `32425141660`, plus [run 32261790230](implementation/CA-00/hosted_ci_evidence_v0_19_0_2026-08-19.md) on head `9f2cce9` |
| Bench runtime | installed apps, migrate, asset build, full app tests | [Bench gate](scripts/bench_quality_gate.py) | current exact-source disposable gate: `179/179 OK` on `ca01.localhost`; not RC/UAT PASS and not hosted evidence |
| Synthetic browser ACL | real Desk/List/Form/direct URL for owned/foreign Engineer users | [browser evidence](implementation/CA-08/authenticated_browser_uat_v0_20_0_2026-08-19.md) | symmetric Form ACL, own-only List and foreign direct `403` PASS; automated synthetic slice only |
| Demo reset | exact registry ownership, derived-row cleanup and idempotent reset | [verification evidence](implementation/CA-08/verification_evidence_v0_20_0_2026-08-19.md) | latest post-browser `delete_count=79`, repeat `0`; stable audit sets: Comment `159`, Deleted Document `340`, Version `91` |
| Privacy/retention | policy/alias/retention targeted runtime and residue checks | [verification evidence](implementation/CA-08/verification_evidence_v0_20_0_2026-08-19.md) | latest scoped: policy `9/9`, alias/retention `24/24`, File boundaries `3/3`; DB/path/ledger residue `0`; included in full disposable Bench `179/179 OK` |
| Browser runtime contract | repo-local browser dependency and harness import boundary | [quality gate](scripts/quality_gate.py) + `tests/test_demo_uat_browser_runtime_contract.py` | `playwright-core 1.62.1` pinned in repo, harness imports repo dependency only, no fallback to generated `output/.../node_modules`, and generated runtime path is required in `.gitignore` |
| Inspection runtime | targeted Inspection module | Bench on isolated `ca01.localhost` | `5/5 PASS`; narrow evidence only |
| Demo lifecycle runtime | full Demo module | Bench on isolated `ca01.localhost` | current exact-source Bench gate includes demo lifecycle and completed `179/179 OK`; prior 34-test failures are superseded diagnostics |

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

Bench gate намеренно использует `--skip-test-records`. В текущем ERPNext `15.119.2` автоматический upstream test-record traversal обращается к удалённому `Payment Gateway` и падает до выполнения тестов приложения. Исторический профиль давал `89/89 OK`, а более поздний dirty-tree baseline — `127/127 OK`; оба предшествуют текущему расширенному набору. Current exact-source disposable gate: `python scripts/bench_quality_gate.py --bench-root /home/rus/contract-accounting-bench --source-root <checkout> --site ca01.localhost --non-production-confirmation "I CONFIRM THIS IS A DISPOSABLE NON-PRODUCTION SITE"` → full app tests `179/179 OK`, final `OK`, `BENCH_QUALITY_GATE=PASS`. Wrapper проверяет transcript: маркер `FAILED` отклоняется даже при ошибочном exit code 0 от Bench, а PASS требует финальный `OK`. Запуск без точного source root и non-production confirmation теперь fail-closed и не маскируется.

## 3. Правила изменения

- Версии quality dependencies изменяются отдельным reviewable change-set.
- Форматный baseline может только уменьшаться. Добавление файла в baseline требует отдельного waiver с причиной и владельцем.
- Static CI PASS не повышается до Bench, UAT или release PASS.
- Bench PASS считается относящимся к tree только при checksum-equivalent app sync либо immutable commit/tag.
- The current `v0.20.0` local review candidate has static `212/212`, exact-source disposable Bench `179/179 OK`, and a pinned repo-local browser runtime contract, but these still do not constitute blanket browser acceptance, human UAT, RC or release PASS.
- Workspace visibility remains an `OPEN BLOCKER` until Product Owner review. The authenticated full-stack synthetic Engineer slice now has `socket.io` polling `200`, but this still is not blanket browser acceptance or human UAT.
- Remote CI получает PASS только после фактического GitHub Actions run; наличие YAML не является run evidence.

## 4. Открытые ворота FR-01

1. `DONE`: current `v0.20.0` change-set зафиксирован в разрешённой feature branch `agent/release-hardening-v0.20.0`, опубликован и открыт draft PR `#1`.
2. `PARTIAL`: current draft PR already has terminal hosted `static-quality` PASS on immutable published head `2e27643` via run `32470646882`; для любого следующего нового change-set hosted CI должен быть зафиксирован повторно после публикации нового SHA.
3. `OPEN`: Bench gate пока остаётся локальным signed/runtime evidence; как защищённый external/self-hosted status для RC он ещё не подключён.
4. `OPEN`: Для RC повторить/закрепить static+Bench профили на одном immutable RC SHA; затем отдельно выполнить RBAC browser acceptance, load/race, UAT, restore и deployment gates.
