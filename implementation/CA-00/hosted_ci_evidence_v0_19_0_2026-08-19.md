# Hosted CI evidence — v0.19.0 release foundation

Дата: 2026-08-19. Вердикт: `HOSTED STATIC QUALITY PASS`.

## Immutable execution

- repository: `Dmitriyrus99/contract-accounting`;
- branch: `agent/release-foundation-v0.19.0`;
- feature commit: `6a93a639c666cfc96ffc86d467bdd4078d1d1f0a`;
- tested head: `9f2cce989c16c132f61f2d462e6758a520ebd460`;
- event: `push`;
- workflow/run: [static-quality #32261790230](https://github.com/Dmitriyrus99/contract-accounting/actions/runs/32261790230);
- job: `static-quality`, ID `96096531092`;
- terminal conclusion: `success`, duration `18s`.

Tested head отличается от feature commit только расширением push-trigger workflow на
`agent/**`; application code и release package находятся в feature commit.

## Terminal steps

1. checkout — PASS;
2. Python 3.11 / Node.js setup — PASS;
3. pinned CI dependencies — PASS;
4. `git diff --check` для exact commit delta — PASS;
5. `python scripts/quality_gate.py` — PASS;
6. job completion — PASS.

Локальный counterpart того же профиля подтверждал release-scope `557/554` с
`Absent=0`, standalone `161/161`, Ruff/format ratchet, JSON/JS/Markdown,
secret scan, mypy и package build. Hosted job является независимым Linux run,
а не выводом из локального результата.

## Неблокирующее предупреждение

GitHub runner сообщил, что runtime Node.js 20 для используемых версий
`actions/checkout`, `actions/setup-node` и `actions/setup-python` deprecated и
принудительно запускается на Node.js 24. Job завершился `success`; обновление
major versions Actions требует отдельного reviewable dependency change.

## Граница evidence

Этот PASS закрывает terminal hosted static gate FR-01 для указанного SHA. Он не
подменяет local Bench `89/89`, protected/self-hosted Bench status, RBAC/browser
UAT, load/race/performance, legal/finance/security approvals, restore,
Staging/Production deployment или release sign-off.
