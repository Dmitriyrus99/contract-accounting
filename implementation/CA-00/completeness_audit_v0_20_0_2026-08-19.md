# Аудит полноты v0.20.0 перед продолжением разработки

**Дата:** 2026-08-19
**Объект:** dirty working tree `0.20.0`, branch
`agent/release-foundation-v0.19.0`, установленный isolated site
`ca01.localhost`.
**Вердикт:** `CROSS-PROJECT LEAK RECORDED / REMEDIATION IN PROGRESS / WHOLE-GRAPH
RBAC, RC, RELEASE AND HUMAN UAT NOT READY`.

Аудит выполнен до продолжения feature-разработки, чтобы отличить наличие
DocType/API/tests от полноты воспроизводимого и безопасного продукта. Он не
повышает automation evidence до UAT, legal, security, finance, performance,
restore, deployment или production sign-off.

## 1. Проверенная поверхность

| Область | Фактическая проверка | Результат |
| --- | --- | --- |
| Source tree | 452 файла; DocType/controllers/hooks/install/patches/API/UI/tests/CI/docs | inventory выполнен |
| Модель | 62 DocType, 1 068 полей, 312 Link, 24 Dynamic Link, 16 Table | структурные ссылки целы |
| Runtime schema | source/runtime имена DocType `62/62`; runtime DocField count `1 068` | совпадает после migrate |
| Child/link contract | нет отсутствующих custom Link/Table targets, orphan child DocType или Dynamic Link без options-field | PASS структуры, не бизнес-семантики |
| Roles | 14 versioned ролей из `role.json`; все присутствуют на runtime | PASS наличия |
| Requirements | 557 строк; 248 уникальных атомарных evidence refs, все файлы/строки существуют | PASS ссылочной целостности |
| API | 113 whitelisted endpoints; HTTP method, mutation и прямое test-name покрытие | gaps ниже |
| Tests | 21 standalone + 20 Frappe test files; 0 JS tests; 0 Playwright specs; coverage measurement отсутствует | неполное доказательство |
| UI/config | Page/Workspace/Workflow/Report/Print Format/Notification/translations/form/list assets | gaps ниже |
| Install/release | hooks, fixtures, reference seed, patches, package metadata, hosted CI | gaps ниже |
| Runtime safety | count/metadata-only запросы без чтения номеров, ФИО, файлов или site secrets | выполнено |

Пять скрытых required-полей без default (`idempotency_key`, snapshots/hash)
проверены как server-derived и сами по себе дефектом не считаются. В 62 JSON
не найдено duplicate fieldname, broken field_order, invalid Select default,
invalid title/search field или parent без permissions.

## 2. Критический blocker: project scope не наследуется связанными DocType

`permission_query_conditions` и `has_permission` ограничивают назначенными
проектами только `Ferum Service Project`. Frappe не переносит это ограничение
автоматически на документы, содержащие Link `service_project`.

Runtime proof на существующих synthetic-only записях:

| Synthetic role | Parent project | Связанный документ | Факт |
| --- | --- | --- | --- |
| `fr06-auth-engineer@example.test` | `Ferum Service Project/FSP-2026-00001`: read=false | `Ferum Service Request/FSR-2026-000001`: read=true | **FAIL** |
| `fr06-auth-office@example.test` | `Ferum Service Project/FSP-2026-00002`: read=false | `Ferum Project Document/FPD-2026-000002`: read=true | **FAIL** |

У Инженера есть read DocPerm ещё на 15+ unhooked operational DocType, включая
Finding, Inspection, Visit, Material Expense, Photo Evidence, Process Evidence,
Project Process/Stage/Step и Stage Gate. У Офис-менеджера unhooked
`Ferum Project Document` дополнительно создаёт риск доступа к связанному File.
File guard защищает Credential и удаление принятого evidence, но не реализует
общий project-scope read guard для Project Document/Photo/Billing files.

Следствие: прежний CA-15 `permission-safe` относится к проверенным projection
API/Page и самому Service Project, но не ко всему прямому Desk/List/Form/API/
export графу. Human UAT и реальные пользователи запрещены до исправления и
negative cross-project acceptance по каждой роли/сущности/file/export route.

## 3. Post-audit remediation status

Аудит зафиксировал исходный leak; его исторический FAIL не стирается. На
текущем dirty `v0.20.0` получено локальное remediation evidence:
static `205/205 PASS`, targeted project-graph runtime `4/4 OK`, launch-template
`5/5 OK`, billing-template `3/3 OK` and full disposable Bench `179/179 OK` on
isolated `ca01.localhost` (`3767.802s`). Эти результаты не повышаются до
blanket browser acceptance, human UAT, hosted CI on the current change-set, RC
или release PASS. Credential-specific/browser evidence, записанное до
обнаружения leak, остаётся provenance, но superseded для whole-graph claims.

Demo/UAT productization всё ещё отсутствует/реализуется. Human UAT blocked до
complete negative acceptance и fresh-site reproducibility evidence.

## 4. Воспроизводимость данных и остаток synthetic UAT

Source-controlled данные сейчас состоят из:

- одного Frappe fixture `fixtures/role.json` с 14 ролями;
- versioned производственного календаря;
- двух reference Process Template, создаваемых install hooks.

Нет canonical business dataset, manifest, idempotent demo installer, scoped
reset и verifier для цепочки Company → Customer → Project → Object/System →
Process/Work → Document/Billing/Payment → Personnel/Assignment.

На `ca01.localhost` после browser UAT остаются 2 synthetic Worker и 2 synthetic
Credential, созданные пользователем `fr06-auth-data@example.test`. Все 12
synthetic users отключены, Privacy/Notification settings disabled, но site не
является пустым. Эти записи не удалялись в рамках текущего read-only аудита.

Это подтверждает необходимость manifest-based reset/verifier: отключение
пользователей и policy не равно восстановлению исходного состояния site.

## 5. UI, конфигурация и эксплуатационная целостность

В source и в runtime для модуля нет:

- Workspace;
- standard Workflow;
- Report;
- Print Format;
- standard Frappe Notification;
- Module Onboarding;
- translations.

Есть 5 custom Page и один form JS. Из 1 068 labels только `launch_tab` содержит
русский label; 1 067 labels — English-only. Browser evidence также зафиксировал
site timezone `Asia/Kolkata`, тогда как целевой контур требует совместного
решения о `Europe/Moscow`.

Отсутствие конкретного standard artifact может быть допустимой архитектурой
(например, custom scheduler вместо Notification), но для каждого типа нужно
одно из двух: source-controlled реализация либо подписанное N/A с проверенной
альтернативой. Сейчас такой полный register отсутствует.

## 6. API, HTTP и тестовые пробелы

Три read endpoint выполняют audit write, оставаясь whitelisted без POST-only
restriction:

- `get_personnel_credential`;
- `download_credential_attachment`;
- `get_supplier_qualification_summary`.

Это нарушает safe/idempotent семантику GET и оставляет side effect без
POST/CSRF boundary. Нужен POST для audited access либо отдельный POST access
ticket с последующим download.

Нет прямого упоминания в tests у 13/113 endpoint names:

1. `attach_billing_output_to_cycle`;
2. `cancel_billing_cycle`;
3. `recalculate_customer_response_deadline`;
4. `recalculate_all_finance_summaries`;
5. `record_customer_inspection_status`;
6. `cancel_inspection`;
7. `get_notification_status`;
8. `get_privacy_policy_status`;
9. `revoke_break_glass`;
10. `request_legal_hold_release`;
11. `approve_legal_hold_release`;
12. `execute_privacy_retention`;
13. `override_stage_gate`.

Это proxy, а не доказательство полного отсутствия indirect coverage, но для
retention, legal-hold release, gate override и cancellation прямое positive/
negative/race/idempotency evidence обязательно.

Прямое имя DocType отсутствует во всех tests для `Ferum Calendar Assignment`,
`Ferum Privacy Break Glass`, `Ferum Privacy Legal Hold` и child
`Ferum Document Link`. Большинство DocType тестируется через 20 агрегированных
Frappe suites, но 34 non-child DocType не имеют собственного test module.

Проверка не подтвердила подозрение о неявном лимите `frappe.get_all`: в
установленном Frappe 15.118.0 `get_all` принудительно ставит
`limit_page_length=0`, а прямой Python `get_list` без limit не формирует SQL
LIMIT. Этот пункт закрыт для текущей версии, но должен иметь regression test
при обновлении Frappe.

## 7. Install, fixtures, drift и patches

Повторная migrate проверяет versioned calendar полным hash. Для
`FERUM-LAUNCH` и `FERUM-BILLING-CYCLE` существующая валидация неполная:

- launch: stage/step codes и PERSONNEL_READY contract;
- billing: codes, evidence, dependency и blocking.

Не сравниваются полностью title, roles, process/action/step type, rules,
criticality, gate/timeout/failure policy и часть template metadata. Поэтому
ручной runtime drift может пережить migrate без ошибки.

Обе patches идемпотентны по основному результату, но не реализуют утверждённый
roadmap contract dry-run + counters `scanned/created/updated/skipped/conflict`
и reconciliation report. Fresh-site install текущего `0.20.0` не выполнялся.

Пять core DocType имеют delete DocPerm для System Manager без явного
`on_trash/before_delete` policy:

- Ferum Service Project;
- Ferum Service Object;
- Ferum Object System;
- Ferum Contract Execution Stage;
- Ferum Contract Security.

Link integrity уменьшает риск удаления связанных записей, но не определяет
допустимый lifecycle для удаления пустой/ошибочной записи. Требуется явное
решение и negative tests.

## 8. CI, package и release boundary

Hosted GitHub CI запускает только static quality на Python 3.11/Node 22. В нём
нет Frappe/ERPNext/MariaDB/Redis, install-app, migrate, Frappe tests, browser
tests, coverage, build или package-install smoke.

`required_apps = ["erpnext"]` не фиксирует проверенный диапазон Frappe/ERPNext;
runtime сейчас Frappe `15.118.0`, ERPNext `15.119.2`. В project dependencies
нет test dependencies Pillow/pypdf; они не нужны production code, но Frappe
privacy suite зависит от состава Bench environment. Нет LICENSE file при
`app_license = "Proprietary"`, CHANGELOG, SECURITY и CODEOWNERS.

Матрица 557 требований детерминирована и все refs валидны, но её
`Implemented=280` выводится из текста traceability. Это не требование-specific
test coverage и не release readiness. `Partial=274`, manual gates и выявленный
RBAC FAIL сохраняют общий статус NOT READY.

## 9. Обязательная последовательность исправления

1. **Не допускать реальных пользователей.** Privacy остаётся Disabled;
   synthetic users — disabled.
2. **Закрыть project-graph authorization.** Общая server-side policy для всех
   project-linked DocType, Dynamic Link, direct File/download, List/Report/
   export/API; positive own + negative foreign tests по Engineer и Office,
   затем по полной internal role matrix.
3. **Исправить claims/evidence.** CA-15 и release docs не должны называть весь
   graph permission-safe до полного negative acceptance.
4. **Утвердить с Product Owner UI/config register:** Workspace, меню, list
   columns/filters, form groups/fields/options, Russian labels, timezone,
   Workflow/Report/Print/Notification dispositions.
5. **Реализовать canonical demo package:** manifest + typed idempotent seed +
   scoped reset + verifier; reset обязан обнаруживать и убирать только demo
   namespace, включая UAT residue.
6. **Закрыть API/test gaps:** POST semantics для audited reads; прямые tests
   13 endpoint; delete/drift/patch contracts; JS/browser negative routes.
7. **Выполнить отдельно разрешённый fresh-site rehearsal:** install-app →
   migrate → seed twice → verify → reset → verify clean → seed → authenticated
   E2E.
8. Только затем переходить к human UAT, scanner integration, representative
   load/race, restore/rollback, immutable RC, Staging и Production gates.

## 10. Что аудит не утверждает

- Он не доказывает полную корректность всех 557 business semantics.
- Он не является penetration test, load test, legal review или human UAT.
- Runtime metadata check не доказывает fresh-install reproducibility.
- Наличие controller/test/evidence file не считается PASS без соответствующего
  foreground результата и точной проверяемой границы.
- Данные и код в рамках аудита не удалялись и не исправлялись.
