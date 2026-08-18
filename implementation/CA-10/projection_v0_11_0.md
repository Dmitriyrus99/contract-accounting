# CA-10 projection contract — v0.11.0

**Статус:** `READ-ONLY SOURCE PROJECTION BENCH VERIFIED AT 19d9124; NO SECOND SSOT`.

## API

| Endpoint | Назначение | Авторизация |
| --- | --- | --- |
| `get_contract_360(service_project, as_of=None)` | карточка одного доступного Service Project | Frappe read permission на проект и каждую дочернюю запись |
| `get_director_control_center(company=None, project_manager=None, as_of=None, pagination)` | портфель только с actionable exceptions | `Генеральный директор`, `Руководитель проектов` или `System Manager`; затем обычные project permissions |

`as_of` — явная дата классификации. Без неё time-based rules не вычисляются и API возвращает `time_rules=disabled_pending_MG-CA-013`.

## Contract 360 widgets

| Widget | Primary sources |
| --- | --- |
| identity/status | `Ferum Service Project` |
| requirements/obligations | `Ferum Contract Requirement`, `Ferum Contract Obligation` |
| objects/systems | `Ferum Project Object`, `Ferum Object System` |
| maintenance plan/fact | `Ferum Maintenance Schedule`, `Ferum Maintenance Visit` |
| requests/findings | `Ferum Service Request`, `Ferum Finding` |
| documents/billing | `Ferum Project Document`, `Ferum Billing Output` |
| contractors | `Ferum Contractor Assignment` |
| deadlines | CA-09 non-persistent source timeline |
| finance/AR/margin | stored `Ferum Project Finance Summary`; permitted submitted `Sales Invoice` rows |

Каждая source row получает `source_doctype`, `source_name` и `drilldown={doctype,name}`. `source_fingerprint` исключает только технический `generated_at`: неизменные источники дают одинаковый fingerprint, изменение источника — новый fingerprint.

## Exception contract

Нормализованное исключение содержит `rule`, `title`, `severity`, `service_project`, `source_doctype`, `source_name`, optional `source_field`, `owner`, `age_days`, optional `due_at/details`, computed `source_key` и `drilldown`. Пустой source или неизвестная severity отклоняются pure domain rule.

Реализованы rules:

- Active work при legal status не `In Force`;
- contract expiry в пределах 30 дней при явном `as_of`;
- active obligation без schedule и active project object без system inventory;
- completed visit с pending review; accepted visit без Billing Basis;
- critical Finding без decision; открытый Defect старше 30 дней;
- issued Act/UPD без signed status;
- overdue Maintenance, Bank Guarantee, Invoice и ожидаемый original document из CA-09 timeline;
- overdue AR, negative margin и unpaid submitted Sales Invoice — только для finance-authorized role.

Director Control Center возвращает project cards, status matrix, KPI by rule/severity и один отсортированный exception list с точным drill-down.

## Permission и finance boundary

- Finance snapshot только читает сохранённый CA-07 summary и не вызывает recalculation.
- Не-финансовая роль получает `finance={access: restricted, status: hidden, unpaid_invoices: []}`.
- Для неё не строятся AR/margin/unpaid exceptions и не возвращаются monetary fields через identity/widgets.
- Доступ к стандартным Sales Invoice дополнительно ограничен Frappe read permission.
- API не пишет DocType, cache, ledger или primary sources.

## Не создаётся и не утверждается

- Contract 360/Exception DocType или параллельная таблица фактов;
- собственный финансовый расчёт;
- persisted risk/overdue status;
- вывод срока из неструктурированного текста;
- автоматическое толкование отсутствующего фото без утверждённого evidence policy;
- BPM blocked/stage-gate rules до CA-11.
