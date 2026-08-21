# Последовательность завершения первого этапа

**Состояние на 2026-08-21:** engineering foundation `v0.20.0` — local review
candidate, не RC. Current accepted technical evidence: static `211/211 PASS`,
targeted Inspection `5/5 PASS`, scoped privacy runtime, source-controlled
synthetic demo installer/reset/verifier, exact-source Bench gate `179/179 OK`
on isolated `ca01.localhost` (`3711.997s`), historical hosted `static-quality`
PASS on draft PR head `2865400`, verified `main` protection, and active tag
ruleset blocking `refs/tags/v*`. This is still not an immutable RC
qualification. Authenticated synthetic browser slice подтвердил symmetric
own/foreign Engineer Form ACL, own-only List, foreign direct `403`, and
full-stack `socket.io` polling `200`; это automated result, не human UAT.
Workspace visibility остаётся `OPEN BLOCKER` до review с Product Owner. Из
554 обязательных требований 280 имеют статус `Implemented`, а 274 — `Partial`;
этот planning verdict не является приёмкой. Human UAT,
restore/rollback, performance/race/load, clean Staging, production approval и
deployment остаются OPEN. Общий статус — `NOT READY FOR PRODUCTION / RC NOT
READY`.

Шаги выполняются по порядку зависимостей. `PASS` автоматизации не заменяет UAT,
approval, production activation или deployment.

| № | Действие | Владелец | Доказательство/exit | Что открывает |
| ---: | --- | --- | --- | --- |
| 1 — ВЫПОЛНЕНО | Разрешить и выполнить `bench migrate` v0.20.0 на изолированном `ca01.localhost`; повторить migrate | Product Owner + Backend | два terminal PASS; runtime/source DocType `62/62`; production sites не затронуты | FR-06 runtime tests |
| 2 — HISTORICAL, SUPERSEDED FOR WHOLE GRAPH | Исторически выполнены targeted FR-06 и full Frappe suite; evidence не удаляется | Backend/QA | `5/5` и `94/94 OK` относятся к прежнему credential-specific tree и не сертифицируют текущий project graph или RC | только историческая техническая трассируемость |
| 3 — HISTORICAL SYNTHETIC BROWSER EVIDENCE | Исторически проверены credential roles/API/report/export/search/private-file | Security + QA | matrix retained; Office full-context и PM/Verifier mask defects были исправлены, но matrix superseded для whole-graph claim; это не human UAT | только credential-specific provenance |
| 3A0 — LOCAL AUTOMATION QUALIFIED / MANUAL GATES OPEN | Исправить и отрицательно проверить row-level project scope для каждого связанного DocType, direct List/Form/API/report/export и File | Security + Backend + QA | scoped targeted runtime PASS; full disposable Bench `179/179 OK`; автоматизация не закрывает browser/human UAT | Product Owner UI review без release promotion |
| 3A — OPEN BLOCKER / OWNER APPROVAL REQUIRED | Совместно с Product Owner утвердить canonical end-to-end demo/UAT scenario, Workspace visibility, list columns/filters, form grouping/labels/options и timezone `Europe/Moscow` | Product Owner + Product/QA | Workspace видимость и UI checklist утверждены; до этого реальные пользователи не допускаются | утверждённая поверхность human UAT |
| 3B — LIFECYCLE VERIFIED | Поддерживать source-controlled idempotent synthetic demo installer/reset/verifier без секретов | Backend + QA | structural verify PASS; exact browser dataset reset PASS `delete_count=74`, повтор `0`; Comment/Deleted Document/Version до/после совпали по count и SHA-256; latest scoped privacy runtime: policy `9/9`, alias/retention `24/24`, File boundaries `3/3`, DB/path/ledger residue `0`; included in full disposable Bench `179/179 OK` | controlled browser rehearsal без residue |
| 3C — AUTOMATED SYNTHETIC SLICE PASS / FULL-STACK PASS | На разрешённом isolated site выполнить install-app → migrate → seed → verify → authenticated synthetic browser E2E | Release + QA | own/foreign Engineer symmetric Form ACL, own-only List, foreign direct `403`, and full-stack `socket.io` polling `200` PASS; это не human UAT | после утверждения 3A — допуск реальных пользователей |
| 4 — TEST ADAPTER PASS / INTEGRATION OPEN | Подключить scanner test adapter и проверить quarantine, Clean/Rejected, streamed download и audit | Security + Backend | synthetic Clean/Rejected, PDF/JPEG/PNG ≤10 MB, private stream PASS; public/direct read, forbidden type/size and protected delete FAIL; actual scanner integration ещё требуется | attachment gate |
| 5 — ЗАБЛОКИРОВАН УТВЕРЖДЕНИЕМ 3A И 3C | Провести HR/DPO/Security UAT: Worker/Credential FSM, dual verification, readiness, expiry/revoke, retention dry-run, legal hold и break-glass | Андриянова Елизавета + Доможакова Алена + Хижняк Алексей | UAT протокол, Sev1/Sev2=0, подписанные результаты | FR-06 UAT PASS |
| 6 | Записать предоставленные номера/оригиналы внутренних актов, если компания использует их в документообороте | Legal + Product Owner | ссылки/номера без изменения уже утверждённой policy | полнота audit package; не подменяет UAT |
| 7 | Закрыть RC-specific protected Bench gate: повторить immutable commit/tag/manifest, fresh-site install, build, migration rehearsal на отдельном RC SHA | Release Manager + QA | immutable RC evidence | Staging deploy |
| 8 | Завершить FR-02/03/04 manual gates: owner/browser/race review, scheduler heartbeat, SMTP receipt/bounce, Operations sign-off | Operations + QA + Product | отдельные PASS-протоколы | end-to-end operational readiness |
| 9 | Реализовать и проверить FR-07 Evidence Policy, затем FR-08 external dependencies и FR-09 management projections | Product + Backend | acceptance по backlog и traceability | полный функциональный контур этапа |
| 10 | Выполнить FR-10…FR-13: legacy rehearsal, Staging dataset, cross-role UAT, performance/race, backup/restore/rollback, monitoring | Release + Operations + QA | 100% critical PASS, restore/rollback PASS, observability active | production decision |
| 11 | Product Owner отдельно разрешает production PII с approval reference; без этого Privacy Settings остаётся Disabled | Русаков Дмитрий Игоревич | отдельный production-data approval | production activation FR-06 |
| 12 | Провести production cutover по runbook, smoke/health, scheduler/queue/backup monitoring | Release + Operations | terminal deploy success и production smoke PASS | запуск системы |
| 13 | Hypercare 10 рабочих дней, устранение критических дефектов, post-release review и закрытие legacy disposition | Product + Operations + QA | Sev1/Sev2=0, KPI/alerts стабильны, итоговый sign-off | готовая система и завершённый этап |

## Использованное разрешение

Product Owner предоставил отдельное разрешение:

```text
разрешаю bench migrate на изолированном ca01.localhost
```

Разрешение использовано только для `ca01.localhost`; migrate, structural
install/verify, scoped authenticated full-stack synthetic browser ACL и reset lifecycle
выполнены в synthetic-only границе. Это не human UAT; Workspace review остаётся
OPEN. Разрешение не включало
`ferum.localhost`, `dev.localhost`, production PII, commit/push нового v0.20.0
change-set или deployment.
