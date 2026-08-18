# CA-05 schema evidence — v0.6.0

**Статус:** `STATIC + BENCH RUNTIME VERIFIED AT 0c8546d`.

**Дата:** 2026-08-18.

## Физическая модель

| DocType | Тип | Назначение |
| --- | --- | --- |
| `Ferum Project Document` | parent | единая реестровая карточка документа проекта |
| `Ferum Document Link` | child | typed relation к разрешённой сущности того же Service Project |
| `Ferum Project Document Event` | parent, insert-only | неизменяемое событие одного status-измерения |

После clean install приложение содержит 24 custom DocType. `Ferum Contract`, второй binary store и отдельная сущность «бумажный файл» отсутствуют.

## Идентичность и provenance

Обязательны `document_type`, `document_number`, `document_date`, `version`, `source_doctype/source_name`. Source ограничен allowlist, обязан существовать и быть доступен на чтение; `service_project`, optional `project_object` и `service_object` выводятся сервером из source. Legacy Contract link отсутствует.

Точный document type enum: `Contract / Technical Specification / Estimate / Procurement Documentation / Supplementary Agreement / Act / Invoice / UPD / Guarantee / Correspondence / Other`.

Сервер формирует SHA-256 `version_key` по Service Project, типу, номеру, дате, версии и issuer. На `version_key` установлен unique constraint. Source/context/identity после insert неизменяемы. Validity period проверяется сервером.

`file` — Link на стандартный Frappe `File`; `content_hash` только копирует серверный hash этого File. Файл можно добавить только typed digital command. Billing и related Dynamic Links ограничены allowlist и отклоняются, если target не раскрывает проверяемый Service Project context.

## Три независимых status-измерения

Карточка:

```text
Draft → Active | Cancelled
Active → Superseded | Archived | Cancelled
```

Digital Copy:

```text
Missing → Uploaded | Not Required
Uploaded → Verified | Signed | Rejected
Rejected → Uploaded
Verified → Signed | Superseded
Signed → Superseded
```

Original:

```text
Not Requested → Requested | Not Required
Requested → In Transit | Received
In Transit → Received
Received → Archived
```

Одна команда меняет ровно одно измерение. `Verified/Signed`, `Received/Archived` и оба `Not Required` требуют evidence; `Not Required` дополнительно требует нормативное основание. Received/Archived получают server actor/time, Archived — обязательное storage location. Active/Archived карточка требует Verified/Signed digital copy либо Received/Archived original.

## Атомарность, аудит и удаление

Три mutating API endpoint объявлены POST-only. Команда ставит private savepoint, блокирует карточку `FOR UPDATE`, проверяет роль и write permission, сохраняет одно status-измерение и insert-only event с correlation ID/snapshot. Ошибка карточки или event откатывает весь command.

Event нельзя создать через обычный CRUD, изменить или удалить. File `on_trash` hook блокирует удаление любого event evidence и binary, если копия Verified/Signed/Superseded, original Received/Archived или карточка Archived. Саму карточку можно удалить только до первого перехода и при отсутствии events.

## Не закрыто этой схемой

- Billing Artifact/Output и standard invoice adapters — CA-06/07; до установки project-context adapter связь fail-closed;
- BPM Process/Step/Gate typed links — CA-11;
- legacy candidate projection/deduplication не запускались из-за утверждённого reset/recreate тестовых данных;
- concurrent load/race test, UAT, legal/operations sign-off и production deployment не выполнялись.
