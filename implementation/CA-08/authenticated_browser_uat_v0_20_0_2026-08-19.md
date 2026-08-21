# FR-06 authenticated browser UAT v0.20.0 — synthetic-only

**Статус на 2026-08-21:** `CURRENT SCOPED AUTOMATED FULL-STACK SYNTHETIC ENGINEER ACL PASS / WORKSPACE REVIEW OPEN / HUMAN UAT NOT RUN / RC NOT READY`.

Документ сохраняет историческую Worker/Credential matrix и отдельно фиксирует
current remediation rerun на source-controlled synthetic dataset. Ни один из
результатов не подтверждает blanket whole-project-graph RBAC, human UAT, RC или
release readiness. Current server/reset evidence ведётся в
[verification evidence](verification_evidence_v0_20_0_2026-08-19.md).

## 1. Разрешённая и фактическая граница

- Контур: только изолированный `ca01.localhost`.
- Данные: только синтетические Worker/Credential/Project/Assignment/File.
- Учётные записи: двенадцать временных `@example.test` пользователей с
  отдельно сгенерированным временным паролем; пароль не записывался в
  repository и не выводился в протокол.
- Реальные пользователи, production PII, `ferum.localhost` и `dev.localhost`
  не использовались.
- Проверка выполнялась через настоящий Frappe Desk login и формы/списки, а не
  только через server API.

## 2. Current remediation browser rerun — 2026-08-21

| Проверка | Фактический результат | Статус/граница |
| --- | --- | --- |
| Own Engineer → own List/Form | список содержит только own dataset; own form открывается | PASS |
| Own Engineer → foreign Form | прямой URL возвращает `403` | PASS |
| Foreign Engineer → foreign List/Form | список содержит только foreign dataset; foreign form открывается | PASS |
| Foreign Engineer → own Form | прямой URL возвращает `403` | PASS |
| Симметрия ACL | обе Engineer identity имеют одинаковое правило own-positive/foreign-negative | PASS, scoped automated synthetic evidence |
| Workspace visibility | целевой personnel/privacy Workspace не доступен как утверждённая рабочая поверхность | `OPEN BLOCKER` до совместного Product Owner review |
| Realtime transport | full-stack `socket.io` polling на `:9000` вернул только `200` для обеих Engineer identity | PASS, scoped automated synthetic evidence |

Это authenticated automated synthetic browser evidence. Оно не является human
UAT или sign-off названных реальных пользователей. Historical `socket.io 404`
при прямом `bench serve` superseded: текущий запуск включал полный
websocket/socket.io stack и зафиксировал polling `200`.

Browser teardown сначала был заблокирован двумя `Activity Log`, связанными с
registry-owned synthetic Engineer users. Последующий exact no-registry detector
доказуемо классифицировал 72 исторических derived rows: 67 Comment (65
deterministic + 2 Activity cluster), 4 Deleted Document для Notification
Settings и 1 Version для Company. После fail-closed ownership remediation:

- dry-run получил `blockers=[]` и включил exact Activity Log в deletion plan;
- реальный reset завершился `RESET_COMPLETE_NOT_A_UAT_RESULT`,
  `delete_count=74`;
- повторный reset завершился `delete_count=0`;
- positive browser-like cleanup и negative historical/mismatched Activity Log
  blocker прошли targeted Bench: `2/2 OK` за `129.608s`;
- независимые audit sets до/после совпали: Comment `159` /
  `b9d32dc17c2ab6553df0d1d4a777988b4345e55726099790ce33b93c98b6bc8f`,
  Deleted Document `340` /
  `34fd6a9d165891f1a3224a631c51a597335ad2c85c6a036af953269013fb3291`,
  Version `91` /
  `bec2d1a60e893f98c0fa78a558231f39d7ec5c33b0f8b0a758497303ce398e79`.

Temporary password file удалён только после удаления synthetic users; реальные
credentials и production data не использовались.

Historical post-teardown targeted set дал `20/20 + 3/3 + policy 8/8 OK` и
superseded для current qualification scoped-наборами policy `9/9`,
alias/retention `24/24`, File boundaries `3/3`. Ни один из этих наборов не
является browser или human UAT evidence.

## 3. Историческая credential-specific ролевая browser-матрица

| Роль | Список/контекст | Номер и файл в форме | Результат |
| --- | --- | --- | --- |
| Менеджер персональных данных | оба synthetic Worker и Credential | полный номер; ссылка private File | PASS |
| Ответственный за ПДн | полный контекст; Legal Hold доступен | полный номер; ссылка private File | PASS |
| Генеральный директор | полный контекст | полный номер; ссылка private File | PASS |
| Офис-менеджер | полный контекст | полный номер; ссылка private File | PASS после исправления |
| Руководитель проектов | только собственный проект; foreign direct URL запрещён | только `••••5678`; File скрыт | PASS после исправления |
| Проверяющий допуски | только назначенный проект; foreign direct URL запрещён | только `••••5678`; File скрыт | PASS после исправления |
| Инженер | только назначенный проект | номер и File полностью скрыты | PASS |
| Ответственный за ИБ | Worker/Credential закрыты; Privacy Event, Break Glass и Settings доступны | не применимо | PASS |
| Бухгалтер | Worker/Credential закрыты | не применимо | PASS |
| Тендерный специалист | персональные списки закрыты; aggregate API проверяется отдельно | не применимо | PASS |
| Подрядчик | Worker/Credential закрыты | не применимо | PASS |
| System Manager без break-glass | списки пусты, прямой URL записи запрещён; Break Glass/Settings доступны | не применимо | PASS по access boundary |

Browser-проверка подтверждает историческое отображение/скрытие ссылки на
Credential-вложение, но не подменяет server download/stream test, интеграцию
фактического malware scanner или full project-graph acceptance.

## 4. Обнаруженные и исправленные дефекты

1. `Офис-менеджер` имел утверждённый DocPerm и data-owner API, но отсутствовал
   в row-level Credential permission hooks. Условие выровнено с Worker;
   browser retest показывает обе записи, полный номер и разрешённую ссылку.
2. PM/Verifier API возвращал маску, но стандартная Desk form не имела поля для
   неё. Добавлена производная read-only проекция `credential_number_masked` на
   отдельном permlevel 2 только для PM/Manager/Verifier. Инженер маску не
   получает. Идемпотентный post-model-sync patch заполняет маску существующих
   записей без вывода полных номеров.

После исправлений `bench migrate` на `ca01.localhost` завершился успешно,
targeted privacy suite исторически повторён: `5/5 OK`. Этот credential-specific
результат superseded для whole-project-graph claim.

## 5. UI-факты, требующие совместного решения с Product Owner

### 5.1 Workspace

Отдельного source-controlled Workspace для personnel/privacy сейчас нет.
Пользователь попадает в общий ERPNext Home, а имеющиеся custom Pages относятся
к Contract 360, Director Control, My Actions, Operations и Project Launches.

Предложение для согласования: Workspace **«Персонал и допуски»** с тремя
role-filtered блоками:

1. Работа: Workers, Credentials, Contractor Assignments, readiness.
2. Контроль: Privacy Events, Break Glass, Legal Holds.
3. Настройки: Privacy Settings только для разрешённых контрольных ролей.

### 5.2 Списки

Предлагаемый минимальный состав до human UAT:

| Список | Колонки | Быстрые фильтры |
| --- | --- | --- |
| Contractor Worker | имя, Supplier, должность, статус, data owner | Supplier, статус, data owner |
| Personnel Credential | holder, тип допуска, статус, срок/без срока, доступная по роли маска | holder, тип, статус, истекает до |
| Contractor Assignment | проект, объект, исполнитель, вид работ, период, статус readiness | проект, объект, Supplier, период, readiness |
| Privacy Event | время, actor, событие, target, result | actor, событие, target type, период |

Полный номер и private File не предлагаются как колонки списка.

### 5.3 Формы и значения

Предлагаемая группировка Credential form:

1. Владелец и тип допуска.
2. Номер по роли: full / masked / hidden.
3. Срок действия и выдавшая организация.
4. Private File и malware lifecycle.
5. Source/applicability verification.
6. Privacy basis/policy и retention.

Сейчас labels/options смешивают русский и английский. Рекомендуется сохранить
стабильные английские значения в БД и добавить русские UI-переводы, например:

| Техническое значение | Предлагаемая надпись |
| --- | --- |
| Electrical Safety | Электробезопасность |
| Occupational Safety | Охрана труда |
| Work at Height | Работы на высоте |
| Professional Qualification | Профессиональная квалификация |
| Other Mandatory | Иной обязательный допуск |
| Draft / Verified / Rejected / Expired / Revoked | Черновик / Проверено / Отклонено / Истекло / Отозвано |
| Pending / Clean / Rejected | Ожидает проверки / Безопасно / Отклонено |

### 5.4 Site settings

Desk показывает timezone `Asia/Kolkata`, тогда как утверждённая рабочая зона —
`Europe/Moscow`. Настройка в этом прогоне намеренно не изменялась: это должно
быть явно подтверждено Product Owner перед human UAT.

## 6. Решения Product Owner до реальных пользователей

Нужно последовательно подтвердить:

1. Утвердить существующие canonical end-to-end demo/UAT scenario и stable manifest.
2. Устранить и совместно принять blocker видимости Workspace «Персонал и допуски».
3. Колонки и быстрые фильтры четырёх списков.
4. Группировку полей форм и русские labels.
5. Предложенную таблицу переводов при сохранении технических enum в БД.
6. Переключение timezone UAT-site на `Europe/Moscow`.
7. После owner review — порядок human UAT:
   Data Owner/HR → DPO/Legal → Security → совместный sign-off.

До этих решений и закрытия Workspace blocker реальные
пользователи из ранее названного списка не подключаются. Source-controlled
demo lifecycle структурно и reset-проверен, но human UAT не выполнялся;
production privacy settings и production PII остаются запрещены.
