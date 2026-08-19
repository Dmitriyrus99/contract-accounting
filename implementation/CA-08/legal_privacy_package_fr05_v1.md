# FR-05 — legal/privacy package for Contractor Worker v1

**Статус:** `PRODUCT OWNER SIGNED / OTHER SIGNATURES PENDING / MG-CA-015 OPEN`
**Дата подготовки:** `2026-08-19`
**Policy reference:** `FR05-PD-01 v1.0`
**Полученный source SHA-256:** `60ca7cd72c2eb37db706d4280c1d4b2bc2da1c56de29f5d08a98eec7ed9f5e86`

Документ фиксирует решения для первого выпуска. Он не является самостоятельным
юридическим заключением и не разрешает production-записи до подписания раздела 8
и реализации FR-06. До этого используются только синтетические данные,
fail-closed controller и запрет positive `PERSONNEL_READY`.

## 0. Назначенные ответственные

| Роль | Ответственный | Зона ответственности |
| --- | --- | --- |
| Legal owner | **Доможакова Алена, юрист** | основания обработки, согласие, договорные условия с Supplier, legal hold |
| Privacy/DPO owner | **Доможакова Алена, юрист** | организация обработки ПДн, обращения субъектов, контроль доступа, удаления и break-glass |
| Security owner | **Хижняк Алексей, исполнительный директор** | правила ИБ, private files, журналы, backup и технический контроль break-glass |
| Data owner / HR | **Андриянова Елизавета, офис-менеджер** | источник, качество, исправление, актуальность и архивирование данных работников подрядчика |
| Product Owner | **Русаков Дмитрий Игоревич, генеральный директор** | утверждение политики, ролей, исключений и допуска данных в production |

Дополнительно:

- **Сыров Артем, руководитель проектов** — `Credential Verifier`: подтверждает,
  что допуск/квалификация соответствует конкретному виду работ;
- **Сабурова Евгения, тендерный специалист** — доступ только к Supplier-level и
  обезличенной информации о наличии квалификаций;
- **Кузнецова Ольга, бухгалтер** — доступа к карточкам работников и credential
  files не имеет; расчёты ведутся по Supplier.

Роли Legal и Privacy/DPO совмещены для текущего масштаба компании, но решения по
двум разделам подписываются отдельно. Privacy/DPO не совмещается с
`System Manager` или Security owner.

## 1. Неизменяемая граница DP-07

В первом выпуске допустимы только:

- Ф.И.О.;
- Supplier;
- рабочая роль;
- рабочий телефон и рабочий email;
- внутренний ID;
- credential type, number, issuer, issue/expiry date и validity;
- Project/Assignment link;
- необходимое private credential attachment.

Паспорт и его scan, адрес, дата/место рождения, СНИЛС, личный ИНН, банковские,
медицинские, биометрические, семейные и иные нецелевые данные запрещены.

## 2. Field registry: Contractor Worker

| Поле | Решение первого выпуска |
| --- | --- |
| `supplier` | required; источник — активный Supplier и действующий договор/Assignment |
| `worker_external_id` | required; генерируется системой как `CW-<supplier-code>-<sequence>`; государственные идентификаторы запрещены |
| `display_name` | required; источник — официальное сообщение Supplier; исправление Андрияновой Елизаветой с audit |
| `position` | короткий справочник рабочих ролей + `Other` |
| `contact` | только рабочие `phone/mobile_no/email_id`; личные контакты без отдельного основания запрещены |
| `status` | `Inactive → Active → Archived`; возврат из `Archived` только через `Inactive` с reason и повторной проверкой |
| `valid_from`, `valid_to` | удалить с Worker; период хранить только в `Ferum Contractor Assignment` |
| `consent_document` | заменить на `privacy_basis_reference`: договор/приложение Supplier либо consent, когда он нужен |
| `identity_document` | удалить из схемы; паспортные файлы запрещены |
| `data_owner` | required; по умолчанию Андриянова Елизавета |
| `privacy_gate` | заменить на versioned `privacy_policy_reference` + hash подписанного FR-05 |
| audit fields | хранить по разделу 4; direct edit запрещён |

## 3. Field registry: Personnel Credential

| Поле | Решение первого выпуска |
| --- | --- |
| `holder_type`, `holder` | только `Employee` или `Ferum Contractor Worker`; доступ разделён |
| `credential_type` | справочник: охрана труда, электробезопасность, высота, профильная квалификация/аттестация, иной обязательный допуск |
| `credential_number` | полный номер видят Data Owner, DPO и verifier; остальным — маска `••••1234`; исключить из global search/export |
| `issued_on`, `expires_on` | обязательность задаётся типом; для бессрочного документа — `no_expiry=1` |
| `issuer` | короткий нормализованный текст |
| `document` | только private attachment утверждённого типа и при заполненном `privacy_basis_reference` |
| `verification_status` | `Draft → Verified/Rejected`; `Verified → Expired/Revoked`; `Expired` устанавливается автоматически |
| `verified_by`, `verified_on` | источник/целостность проверяет Андриянова Елизавета; техническую применимость — Сыров Артем; readiness требует обе отметки |
| `privacy_gate` | versioned policy reference после sign-off |
| audit fields | хранить 3 года; не включать в массовые выгрузки |

## 4. Purpose, basis and retention matrix

Сроки ниже являются утверждаемой внутренней политикой первого выпуска. При
`legal hold` удаление приостанавливается только для конкретно перечисленных
записей и файлов.

| Категория | Цель и основание | Источник | Согласие | Срок | Действие после срока |
| --- | --- | --- | --- | --- | --- |
| Ф.И.О. и рабочая роль | назначение и контроль исполнения работ; минимально необходимая обработка | официальный представитель Supplier | отдельно не требуется при документированном основании передачи; иначе запись не активируется | 3 года после последнего Assignment/договора | `Archived`, затем заменить Ф.И.О. на internal ID |
| Supplier и internal ID | подтверждение связи работника с подрядчиком | Supplier master + система | отдельно не требуется | 3 года | удалить Supplier link; сохранить обезличенный ID в audit |
| Рабочий Contact | оперативная связь | официальный представитель Supplier | корпоративный контакт — без отдельного согласия; личный контакт без отдельного основания не хранить | 90 дней после последнего Assignment | заблокировать и удалить |
| Assignment context | подтверждение project/object/scope/period | Project Manager/Data Owner | отдельно не требуется | 3 года после завершения Assignment/Project | обезличить worker reference |
| Credential metadata | проверка квалификации и допуска | Supplier/документ/Verifier | отдельно не требуется при документированном основании | 3 года после последнего релевантного Assignment или expiry | удалить number/issuer; сохранить type, результат и даты |
| Credential attachment | evidence допуска, только если копия действительно нужна | официальный представитель Supplier | при отсутствии достаточного основания файл не загружается; при необходимости используется отдельное подтверждение/consent | 1 год после последнего релевантного Assignment или expiry | удалить файл; metadata и hash хранить до конца 3-летнего срока |
| Verification/audit metadata | доказательство проверки и расследование доступа | system/users | не требуется | 3 года после события | удалить либо необратимо обезличить |

### Источник и исправление

1. Основной источник — официальный представитель Supplier.
2. Данные принимаются через официальный email, письмо, договорное приложение или
   утверждённую форму.
3. Работник сообщает об ошибке через Supplier либо Privacy/DPO.
4. Андриянова Елизавета проверяет источник и вносит исправление.
5. Старое/новое значение, основание, автор и время фиксируются в audit.

### Legal hold

- вводят Доможакова Алена и Русаков Дмитрий Игоревич совместно;
- обязательны причина, перечень записей/файлов и дата следующего review;
- legal hold не расширяет права просмотра;
- после снятия применяется обычное правило retention;
- удалённые active-файлы выводятся из backup по штатной ротации, целевой срок —
  не более 90 дней.

## 5. Role, export and attachment matrix

### 5.1. Доступ ролей

| Роль / сотрудник | Доступ | Export/download |
| --- | --- | --- |
| Personnel Data Manager — **Андриянова Елизавета** | все поля DP-07; create/update/archive; подготовка credential к проверке | единичный export/download; массовый — только с approval DPO |
| Privacy/DPO — **Доможакова Алена** | все поля, audit, basis, retention; block/delete review | download только с reason; массовый export запрещён |
| Product Owner — **Русаков Дмитрий Игоревич** | полный read; approve policy, exception и legal hold | download/export только с reason; массовый — совместно с DPO |
| Security owner — **Хижняк Алексей** | security metadata, malware status и access logs; business content по умолчанию скрыт | содержимое файлов только через break-glass |
| Project Manager / Verifier — **Сыров Артем** | workers своих проектов: Ф.И.О., Supplier, роль, рабочий Contact, readiness, credential type/status/expiry | number masked; attachment только для конкретной проверки с reason; массовый export запрещён |
| Tender Specialist — **Сабурова Евгения** | Supplier-level и обезличенный признак наличия квалификаций | Ф.И.О., контакты, номера и файлы запрещены |
| Office Manager — **Андриянова Елизавета** | как Data Owner — полный утверждённый набор; в обычной координации — Ф.И.О., Supplier, Contact, status | attachments только для ведения карточки; массовый export запрещён |
| Accountant — **Кузнецова Ольга** | доступа к Worker/Credential нет | нет |
| Service Engineer | только назначенные коллеги: Ф.И.О., Supplier, роль, рабочий телефон, readiness | нет номера, файла и export |
| System Manager | постоянного business-доступа нет | только break-glass |
| Customer / другой Contractor | доступа нет | нет |

Ограничения должны одинаково работать для UI, API, report, print, search,
data export и private-file URL.

### 5.2. Credential attachments

Разрешены только PDF, JPEG и PNG не более 10 МБ. Архивы, Office-файлы,
паспорта, медицинские и банковские документы запрещены.

| Параметр | Решение |
| --- | --- |
| Storage | private storage; публичная ссылка запрещена |
| Malware scan | обязателен до доступности файла; без scanner — metadata only |
| Preview | только тем же ролям, что download |
| Download | Андриянова Елизавета и Сыров Артем для проверки; Доможакова Алена и Русаков Дмитрий Игоревич — только с reason |
| Project Manager вне проверки | видит наличие файла и verification result, но не скачивает |
| Audit | actor, time, reason, record и file hash |
| Export bundle | запрещён |
| Backup | защищённый backup; доступ эксплуатации только через break-glass |
| Retention | 1 год, затем удалить файл и сохранить metadata/hash |
| Legal hold | только по разделу 4 |

## 6. Break-glass

1. Requester — `System Manager`/инженер поддержки; обязательны ticket, reason,
   exact records/actions и срок.
2. Совместно одобряют **Хижняк Алексей** и **Доможакова Алена**.
3. Если requester — Хижняк Алексей, вместо него одобряет
   **Русаков Дмитрий Игоревич** совместно с Доможаковой Аленой.
4. Доступ по умолчанию read-only, только к указанным records.
5. Максимальный срок — 4 часа; затем автоматический revoke.
6. Массовый export, DB dump и выгрузка всех private files запрещены.
7. Audit фиксирует request, approve/reject, read, preview, download, export attempt
   и revoke.
8. Review выполняют Доможакова Алена и Андриянова Елизавета не позднее следующего
   рабочего дня.

## 7. Закрытые ответы простыми словами

| № | Решение | Владелец |
| ---: | --- | --- |
| 1 | Использовать только минимальные данные для назначения и проверки допуска. | Legal + Privacy |
| 2 | Не требовать consent для каждой карточки; требовать подтверждённое основание передачи Supplier. Отдельное подтверждение нужно для исключений и спорных файлов. | Доможакова Алена |
| 3 | Данные предоставляет Supplier; исправляет Андриянова Елизавета под контролем DPO. | Андриянова Елизавета + Доможакова Алена |
| 4 | Metadata — 3 года; Contact — 90 дней; credential file — 1 год; audit — 3 года. | Legal + Privacy + Data Owner |
| 5 | Сначала block/archive, затем delete/anonymize; legal hold — исключение. | Доможакова Алена |
| 6 | Exact role matrix утверждена разделом 5. | Русаков Дмитрий Игоревич |
| 7 | Только необходимые PDF/JPEG/PNG до 10 МБ, private storage, malware scan и audit. | Хижняк Алексей + Андриянова Елизавета |
| 8 | Break-glass одобряют Security + DPO, максимум 4 часа. | Хижняк Алексей + Доможакова Алена |
| 9 | Подписанты назначены разделом 8. | Русаков Дмитрий Игоревич |

## 8. Sign-off record

| Роль | Ф.И.О./должность | Решение | Дата | Документ/акт |
| --- | --- | --- | --- | --- |
| Legal owner | **Доможакова Алена, юрист** | `PENDING SIGNATURE` | — | заключение FR-05 `[номер]` |
| Privacy/DPO owner | **Доможакова Алена, юрист** | `PENDING SIGNATURE` | — | приказ о назначении ответственного за ПДн `[номер]` |
| Security owner | **Хижняк Алексей, исполнительный директор** | `PENDING SIGNATURE` | — | приказ о зоне ответственности ИБ `[номер]` |
| Data owner / HR | **Андриянова Елизавета, офис-менеджер** | `PENDING SIGNATURE` | — | приказ о владельце данных `[номер]` |
| Product Owner | **Русаков Дмитрий Игоревич, генеральный директор** | `APPROVED / SIGNED` | `2026-08-19` | подтверждение в текущей задаче Codex; immutable evidence — commit этого change-set |

Подтверждение Product Owner утверждает пакет решений и его строку sign-off. Оно не заменяет отдельные подписи Legal owner, Privacy/DPO owner, Security owner и Data owner / HR; их строки остаются `PENDING SIGNATURE`.

## 9. FR-06 change-set

1. удалить `identity_document`;
2. убрать `valid_from/valid_to` из Worker;
3. заменить `consent_document` на `privacy_basis_reference`;
4. заменить boolean `privacy_gate` на policy version + hash;
5. реализовать field permissions, masking и project boundaries;
6. реализовать file allowlist, malware scan, private URL и download audit;
7. реализовать retention, anonymization/delete и legal hold;
8. реализовать dual-approval break-glass;
9. провести positive/negative UI/API/report/export/private-file tests.

`MG-CA-015 PASS` допускается только после подписания всех строк раздела 8, реализации FR-06,
успешных тестов и отдельного разрешения Product Owner на production data.
