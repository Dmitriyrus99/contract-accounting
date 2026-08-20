# Воспроизводимый demo/UAT-контур — productization plan v1

**Статус на 2026-08-20:** `STRUCTURAL PRODUCTIZATION AND EXACT RESET VERIFIED / WORKSPACE AND FULL-STACK RERUN OPEN / HUMAN UAT NOT RUN / RC NOT READY`.

## 1. Корректная оценка текущего состояния

Кодовая база содержит много реализованных и локально проверенных инкрементов,
но это не равно готовому внедряемому продукту. После первоначального аудита
создан source-controlled synthetic demo installer/reset/verifier и проверен его
точный lifecycle на изолированном `ca01.localhost`. Это доказывает structural
install/verify и безопасный synthetic cleanup в проверенной границе, но не
доказывает готовность Workspace/Workflow/Print/Report/Notification, human UAT,
restore/performance, production cutover или release.

Фактически source-controlled сейчас:

- один Frappe fixture `contract_accounting/fixtures/role.json` с 14 ролями,
  экспортируемый через `hooks.py`;
- официальный versioned source производственного календаря;
- test builders, которые создают изолированные test records через `setUp()`;
- пакет [`contract_accounting/demo_uat`](../../contract_accounting/demo_uat/README.md)
  со stable manifest, bootstrap, installer, verifier, ownership registry и
  fail-closed exact reset.

Demo manifest покрывает связанный synthetic сценарий:

`Company/Customer/Supplier → два изолированных Service Project → Service
Object/Object System → Requirement/Obligation/Schedule/Visit →
Inspection/Finding/Service Request → Process/Stage/Step/Evidence/Gate → Project
Document/File/Material/Billing Cycle → Worker/Credential/Assignment →
Users/Roles/User Permission`.

Production-grade invoice/payment records и их accounting reconciliation этот
synthetic manifest не заявляет; соответствующий end-to-end gate остаётся OPEN.

Финальный exact reset удалил `74` owned/derived rows, повторный reset — `0`.
Независимые audit sets до/после совпали по count и SHA-256: Comment `159` /
`b9d32dc17c2ab6553df0d1d4a777988b4345e55726099790ce33b93c98b6bc8f`,
Deleted Document `340` /
`34fd6a9d165891f1a3224a631c51a597335ad2c85c6a036af953269013fb3291`,
Version `91` /
`bec2d1a60e893f98c0fa78a558231f39d7ec5c33b0f8b0a758497303ce398e79`.
Earlier targeted aggregate `20/20 + 3/3 + policy 8/8` is superseded. Latest
scoped runtime is policy `9/9`, alias/retention `24/24`, File boundaries `3/3`,
DB/path/ledger residue `0`; final-tree whole-app qualification remains open.

Матрица Release Scope также не позволяет говорить «почти готово»:
`280/557 Mandatory = Implemented`, `274/557 Mandatory = Partial`.

## 2. Что создано и поддерживается

Транзакционные demo/UAT данные не помещены без разбора в стандартный Frappe
`fixtures` export. Создан отдельный source-controlled пакет
`contract_accounting.demo_uat`:

1. `manifest_v1.json` — стабильные external IDs, связи, ожидаемые fingerprints
   и scenario assertions.
2. `installer.py` — идемпотентная synthetic-only установка на явно разрешённый
   developer/UAT site с точным confirmation token.
3. `reset.py` — fail-closed сброс exact registry-owned и доказуемо derived
   объектов; внешние/исторические ссылки блокируют удаление.
4. `verifier.py` — read-only проверка количества, связности, ролей, User Permission,
   Workflow/Workspace/Print/Report/Notification prerequisites и сценариев.
5. `README.md` — канонические install/reset/verify commands и ожидаемый
   итог без паролей/секретов.

Synthetic users создаются только при запуске, получают случайный временный
пароль вне repository и удаляются exact reset вместе с доказуемо owned/derived
данными; временный password file удаляется после users. `role.json` остаётся
fixture конфигурации, а demo business records создаются typed/idempotent
installer.

## 3. Минимальный canonical scenario для утверждения

Рекомендуемая структура v1:

| Контекст | Минимум | Назначение |
| --- | ---: | --- |
| Company | 1 | рабочая организация и календарь |
| Customer/Project/Object/System | 2 изолированных набора | own/foreign RBAC и cross-project denial |
| Contract requirements/obligations | happy + blocked | плановый и fail-closed путь |
| Process/Stages/Steps/ToDo | один Published graph + instance | launch/work queue/gate |
| Maintenance/Inspection/Finding | по одному сквозному примеру | факт, evidence, defect/additional work |
| Project Documents/Files | signed/private/rejected examples | registry, evidence и delete guards |
| Billing Cycle/Output/Invoice/Payment | paid + unpaid/blocked branches | документарный и accounting trace |
| Supplier/Workers/Credentials/Assignments | scoped + foreign + expired | personnel readiness и RBAC |
| Users/roles/User Permission | все критические роли | browser matrix и negative direct URL |
| Notifications | due/overdue/dead-letter examples | in-app/email-queue/retry |

Точные business values, обязательные виды допусков, документы и happy/negative
ветви должны быть подтверждены Product Owner; их нельзя выводить только из
существующих unit test builders.

## 4. Обязательные acceptance gates

0. Сквозная project-scope authorization должна быть закрыта для direct List/
   Form/API/report/export/File по полной internal role matrix. Текущий
   authenticated synthetic результат подтверждает только симметричный Engineer
   slice: own Form/List PASS, foreign direct URL `403` PASS.
1. Fresh empty site создан отдельным разрешением.
2. `install-app` и `migrate` проходят без ручного DB редактирования.
3. `DONE`: installer/verifier структурно проверены; manifest bindings и
   fingerprints валидируются read-only verifier.
4. `DONE`: exact reset удаляет только owned/derived synthetic records,
   восстанавливает prior policy state без drift и повторяется с результатом `0`.
5. `DONE` в structural границе: critical links и expected counts подтверждены
   verifier; это не browser/human acceptance.
6. Workspace, lists, forms, translations, timezone, Workflow, Print Formats,
   reports и notifications проверены через browser.
7. Канонические end-to-end happy и negative paths повторяются из runbook.
8. После этого, но не раньше, выполняется human HR/DPO/Security UAT.
9. Отдельно выполняются representative-volume race/load, backup/restore,
   migration/cutover/rollback и production activation gates.

## 5. Изменение приоритета roadmap

### Now

- Совместно утвердить Workspace visibility, lists/forms/translations/timezone и
  canonical UI checklist; Workspace остаётся `OPEN BLOCKER`.
- Повторить synthetic browser run на полном Frappe stack: `socket.io 404` под
  `bench serve` зафиксирован как environment limitation, не realtime PASS.
- Сохранить exact installer/reset/verifier и privacy/retention regressions в RC
  qualification.

### Next

- Исправить Workspace/forms/lists/translations/workflows/reports/prints по
  результатам совместного Product Owner review.
- Подключить actual scanner adapter и повторить attachment flow.
- После owner review и full-stack synthetic rerun отдельно допустить human UAT.

### Later

- Human UAT реальными владельцами ролей.
- Staging, representative volume, race/load, restore/rollback, cutover.
- Отдельное production-PII approval и production deployment.

## 6. Что отложено этой перестановкой

Human UAT и любые утверждения о release readiness остаются отложены, несмотря
на воспроизводимый structural demo/UAT package. Их блокируют Product Owner UI
review, Workspace visibility, full-stack realtime rerun и отдельные manual/
operational gates. Новые изолированные feature-инкременты не должны вытеснять
эту последовательность.
