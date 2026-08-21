# FR-06 v0.20.0 verification evidence — 2026-08-19

**Текущий итог на 2026-08-21:** `PUBLISHED REVIEW CANDIDATE / HOSTED STATIC CI PASS / FINAL-TREE STATIC 212/212 PASS / TARGETED INSPECTION 5/5 PASS / FULL DISPOSABLE BENCH 179/179 OK / LATEST SCOPED PRIVACY 9+24+3 OK / FULL-STACK AUTHENTICATED SYNTHETIC ENGINEER ACL PASS / PINNED REPO-LOCAL BROWSER RUNTIME CONTRACT / LATEST POST-BROWSER RESET 79→0 WITH STABLE AUDIT HASHES / POST-RUN SYNTHETIC RESIDUE 0 / WORKSPACE REVIEW, HUMAN UAT, RC AND RELEASE NOT READY`.

Исторические credential-specific server/file/Bench/browser результаты ниже
сохранены как provenance. После обнаруженного cross-project leak они
**superseded только для утверждений о полном project graph, blanket RBAC, RC
или release readiness**; они не удаляются и не считаются human UAT.

## Зафиксированная граница

- version: `0.20.0`;
- policy: `FR05-PD-01 v1.0`;
- policy SHA-256:
  `19220c689d94046ec24f03ffdf6b00c2cfb33c7749f7d8c59a98398856a4e893`;
- disposable Bench: `/home/rus/contract-accounting-bench`, site `ca01.localhost`;
- Frappe `15.118.0`, ERPNext `15.119.2`, `contract_accounting 0.20.0`;
- отдельные MariaDB `127.0.0.1:3317` и Redis `127.0.0.1:11000/13000`;
- production privacy settings не активировались;
- `ferum.localhost`, `dev.localhost`, production data и credentials не использовались.

## Historical static quality transcript excerpt

Команда `python scripts/quality_gate.py` завершилась terminal
`STATIC_QUALITY_GATE=PASS`:

```text
RELEASE_SCOPE=PASS|ROWS=557|MANDATORY=554|ABSENT=0
Ruff: PASS
FORMAT_RATCHET=PASS
JSON_PARSE=PASS|FILES=73
JAVASCRIPT_SYNTAX=PASS|FILES=8
SECRET_SCAN=PASS|FILES=443
MARKDOWN_LINKS=PASS|LINKS=493
mypy: Success: no issues found in 17 source files
wheel: contract_accounting-0.20.0-py3-none-any.whl
STATIC_QUALITY_GATE=PASS
RUNTIME_UAT_DEPLOYMENT_GATES=NOT_EVALUATED
```

Excerpt намеренно не повторяет superseded standalone total; current static
результат зафиксирован ниже как `212/212 PASS`.

`git diff --check` также завершён без ошибок.

## Disposable Bench runtime

После отдельного разрешения Product Owner выполнена только synthetic
квалификация `ca01.localhost`:

1. Текущий working tree синхронизирован в
   `/home/rus/contract-accounting-runtime-source`; app-link Bench указывает
   именно на этот каталог.
2. Первый и повторный `bench --site ca01.localhost migrate`: terminal `PASS`,
   включая model sync, Dashboards и `after_migrate`.
3. `bench build --app contract_accounting`: terminal `PASS`.
4. Runtime inventory: `62` DocType модуля Contract Accounting; source inventory:
   `62` DocType JSON.
5. Targeted FR-06:
   `contract_accounting.contract_accounting.doctype.ferum_privacy_settings.test_ferum_privacy_policy`
   → `Ran 5 tests in 66.319s`, final `OK`. В составе: project-scoped
   positive/negative access, masked/no-number projection, report/export denial,
   exact-target break-glass, Clean/Rejected, private PDF/JPEG/PNG до 10 MB,
   public/forbidden/oversized rejection, typed download и pre-unlink File guard.
6. Исторический полный protocol на прежнем credential-specific tree:
   `bench --site ca01.localhost run-tests --app contract_accounting --skip-test-records`
   → `Ran 94 tests in 494.244s`, final `OK` и wrapper `FULL_FRAPPE: OK`.
   Этот результат не является доказательством текущего dirty tree после
   remediation и не сертифицирует whole-project-graph authorization.
7. Реальный browser smoke подтвердил anonymous redirect protected Desk URL.
8. После отдельного разрешения выполнен authenticated browser UAT с двенадцатью
   временными synthetic-only ролями. Подтверждены project/foreign isolation,
   Data Owner/DPO/Product Owner full context, Security control-only boundary,
   отрицательные Accountant/Tender/Contractor роли и System Manager direct-URL
   denial без break-glass.
9. Browser UAT обнаружил два дефекта: Office Manager не попадал в row-level
   Credential hooks; PM/Verifier API mask не отображалась в Desk form. Hooks
   исправлены; добавлены read-only `credential_number_masked` permlevel 2 и
   идемпотентный post-model-sync backfill. Разрешённый повторный migrate PASS.
10. Browser retest: Office видит оба Credentials/full/File link; PM и Verifier
    видят только `••••5678`, не видят full/File; Engineer не видит full/mask/File.
    Targeted privacy regression повторён: `5/5 OK`.
11. Отдельного personnel/privacy Workspace нет; labels/options смешаны, а Desk
    показывает `Asia/Kolkata`. Эти настройки намеренно не изменялись без
    совместного Product Owner review. Матрица и checklist находятся в
    [authenticated browser evidence](authenticated_browser_uat_v0_20_0_2026-08-19.md).
12. Исторический first full-suite после browser UAT был намеренно отклонён: активная synthetic
    policy и две UAT Credential записи загрязнили три assumptions старых CA-08
    тестов. После teardown и замены global-zero assertion на baseline-delta
    targeted Assignment `6/6 OK`, финальный полный suite:
   `Ran 94 tests in 541.664s`, terminal `OK`. Этот исторический результат
   superseded для whole-graph claims.
13. Teardown: `privacy_enabled=false`, все 12 synthetic users `enabled=0`,
    временный password file и fixture module удалены. Disposable services
   остановлены; порты `3317/11000/13000/8000` не слушают.

## Current post-leak remediation evidence — 2026-08-21

На текущем dirty `v0.20.0` после обнаружения cross-project leak приняты
следующие ограниченные локальные результаты:

- final-tree static quality: `212/212 PASS`;
- targeted Inspection: `5/5 PASS`;
- full disposable Frappe app suite on isolated `ca01.localhost`: full app tests `179/179 OK`, final `OK`;
- targeted project-graph runtime: `4/4 OK`;
- launch-template runtime: `5/5 OK`;
- billing-template runtime: `3/3 OK`;
- source-controlled demo installer/reset/verifier: structural install/verify
  complete;
- latest scoped privacy runtime: policy `9/9`, alias/retention `24/24`, File boundaries `3/3` OK; included in the full disposable `179/179 OK` run;
  DB/path/ledger residue `0`;
- repo-local browser runtime contract: `playwright-core 1.62.1` pinned in `package.json`/`package-lock.json`; browser harness imports repo dependency only, no longer depends on generated `output/.../node_modules`, and generated runtime path is required in `.gitignore`;
- authenticated synthetic browser: own/foreign Engineer symmetric Form ACL,
  own-only List, foreign direct `403`, and full-stack `socket.io` polling `200`
  — PASS;
- latest post-browser dataset exact reset: `delete_count=79`, immediate repeat `0`;
- independent before/after audit sets remained exact: Comment `159` /
  `b9d32dc17c2ab6553df0d1d4a777988b4345e55726099790ce33b93c98b6bc8f`,
  Deleted Document `340` /
  `34fd6a9d165891f1a3224a631c51a597335ad2c85c6a036af953269013fb3291`,
  Version `91` /
  `bec2d1a60e893f98c0fa78a558231f39d7ec5c33b0f8b0a758497303ce398e79`;
- Activity Log lifecycle ownership regressions: `2/2 OK` за `129.608s`.
- Post-run residue check: DB demo File rows `0`, DB credential/download File rows `0`, Privacy Event rows `0`, FS demo fixture matches `0`, FS credential/download synthetic matches `0`, recovery `.ca-demo-uat-recovery` / `.pending` / `.committed` / `.error` directories `0`. Cleanup before final postcheck removed only proven zero-DB synthetic test artifacts: 38 credential/download blobs and two metadata-only demo recovery jobs.

Browser evidence является automated synthetic result, не human UAT. Оно не
повышает scoped slice до blanket whole-graph RBAC: Workspace visibility остаётся
`OPEN BLOCKER` до Product Owner review, but historical `socket.io 404` under
`bench serve` is superseded by current full-stack polling `200`. RC и release
остаются `NOT READY`.

## Диагностические результаты, не принятые как PASS

- Первый вызов использовал отсутствующий локальный `./env/bin/bench`; migrate
  не стартовал. Фактический executable `/home/rus/.local/bin/bench` вызван из
  Bench root.
- Ранние расширенные targeted-прогоны обнаружили и исправили четыре
  production-relevant расхождения: project scope старых verifier fixtures,
  invalid synthetic PDF, избыточный scanner response и поздний File `on_trash`
  hook. Последний заменён override класса `File`, чтобы business guards
  выполнялись до физического unlink; принят только финальный `5/5 OK`.
- Первый исторический полный прогон дал `92 tests` и один failure старого CA-12 assertion,
  который безусловно ожидал `MG-CA-015`. Утверждённая архитектура v0.20.0
  разрешает `Not Applicable`, когда contractor/credential requirement
  отсутствует. Regression-test изменён для positive и fail-closed веток;
  regression вошла в тогдашний full-suite baseline; после последующего
  расширения regression-набора требуется новый final-tree full run.
- Полный диагностический запуск без project-standard `--skip-test-records`
  остановился до тестов на отсутствующем `Payment Gateway`; site не содержит
  отдельное Payments app. Он не принят. Первый запуск со штатным флагом потерял
  временно запущенный Redis Queue и также отклонён; после daemonized restart
  queue оставалась `PONG`, а повтор завершился `94/94 OK`.
- WSL Playwright wrapper оказался CRLF-incompatible, а CLI не нашёл Chrome в
  WSL. Новый браузер не устанавливался. In-app browser сначала выполнил
  anonymous smoke, а после отдельного разрешения — authenticated synthetic role
  matrix.
- Historical browser run через `bench serve` получил `socket.io 404`. Он не
  поднимал полный websocket/socket.io stack и сохраняется как environment
  limitation provenance. Current full-stack synthetic Engineer rerun completed
  with `socket.io` polling `200` for both identities and is the accepted
  scoped browser evidence.
- Первый real reset current browser dataset корректно остановился на
  postcondition: четыре structured Shared Comment, созданные bootstrap
  DocShare→User, не входили в deletion plan. Транзакция/physical File rollback
  сохранили dataset. Узкая атрибуция расширена только на exact owned bootstrap
  User target; повторный dry-run включил эти четыре Comment и две lifecycle
  Activity Log. Последующий no-registry detector классифицировал только exact
  historical derived set из 72 rows: 67 Comment (65 deterministic + 2 Activity
  cluster), 4 Deleted Document для Notification Settings и 1 Version для
  Company. После fail-closed ownership remediation latest post-browser reset `79` и
  repeat `0` завершились успешно, а независимые audit counts/hashes не
  изменились.
- Первый повтор targeted suite после browser-fix создал дополнительного User в
  каждом test `setUp` и достиг Frappe `throttle_user_limit`; два теста получили
  setup error, поэтому запуск отклонён. Fixture переведён на переиспользование
  synthetic account и explicit test/import flag; принятый повтор дал `5/5 OK`.
- Frappe email HTML renderer выводит известные CSS parser warnings для upstream
  `#0000001a`; соответствующий email test и полный suite завершились `OK`.

## Не выполнено и не заявляется

Не выполнялись actual malware scanner integration/quarantine,
representative-volume race/load, human HR/DPO/Security UAT, backup/restore,
production activation и deployment. Authenticated browser evidence относится
только к synthetic technical role matrix и не является human sign-off.

Поэтому на текущем tree подтверждён только scoped remediation evidence выше:
`FR-06` blanket whole-graph RBAC, RC и release — `NOT READY`; human UAT not run,
`MG-CA-015 = PARTIAL`, а production PII остаются запрещены до отдельного
разрешения.
