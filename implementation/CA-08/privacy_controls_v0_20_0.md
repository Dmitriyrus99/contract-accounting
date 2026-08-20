# FR-06 — protected personnel data and readiness v0.20.0

**Статус:** `CODE/STATIC/SERVER-RBAC/DISPOSABLE BENCH PASS / UAT PENDING`
**Дата:** `2026-08-19`
**Policy:** `FR05-PD-01 v1.0`
**Policy SHA-256:** `19220c689d94046ec24f03ffdf6b00c2cfb33c7749f7d8c59a98398856a4e893`

Этот change-set реализует техническую часть решений
[FR-05](legal_privacy_package_fr05_v1.md). Он не активирует production PII и
сам по себе не переводит `MG-CA-015` в `PASS`.

## 1. Activation boundary

`Ferum Privacy Settings` — fail-closed Single DocType. По умолчанию:

- `enabled=0`;
- `activation_mode=Disabled`;
- policy reference/hash должны совпадать с подписанным FR-05.

Режимы разделены:

- `Synthetic Test` доступен только на developer site и требует точное
  подтверждение `CONFIRM_SYNTHETIC_TEST_DATA_ONLY`; basis синтетических записей
  обязан начинаться с `TEST-`;
- `Production` требует роль Product Owner, точное отдельное подтверждение
  `CONFIRM_FR05_PD01_PRODUCTION_PII_AUTHORIZED`, approval reference и reason.

В этом change-set production activation не выполнялась.

## 2. Worker and Credential lifecycle

`Ferum Contractor Worker`:

- удалены `valid_from`, `valid_to`, `consent_document`, `identity_document` и
  прежний boolean-like `privacy_gate`;
- добавлены `privacy_basis_reference`, versioned policy reference/hash,
  подтверждение рабочего Contact, audit/retention fields;
- ID генерируется как `CW-<supplier-code>-<sequence>`;
- FSM: `Inactive → Active/Archived`, `Active → Inactive/Archived`,
  `Archived → Inactive` только с reason;
- прямые create/update/delete запрещены, используются typed POST commands.

`Ferum Personnel Credential`:

- holder allowlist: `Employee` и `Ferum Contractor Worker`;
- credential type allowlist соответствует FR-05;
- number и private file находятся на отдельном permlevel и исключены из
  стандартных export/print permissions;
- attachment — private `File`, только PDF/JPEG/PNG до 10 MB; до `Clean`
  malware result он не участвует в проверке и не скачивается;
- source и applicability подтверждают разные пользователи; `Verified` возникает
  только после обеих отметок;
- FSM: `Draft → Verified/Rejected`, `Verified → Expired/Revoked`;
- Verified credential после `expires_on` автоматически переводится в `Expired`
  планировщиком; live readiness не ждёт scheduler и сразу считает его истёкшим;
- выдаётся masked projection `••••<last4>`; единичное скачивание выполняет
  typed streaming endpoint с reason и audit, public URL не создаётся.

## 3. Row and file permissions

- Data Manager, DPO и Product Owner читают утверждённый полный набор;
- Project Manager/Verifier видят только project-scoped base data и masked number;
- Engineer видит только project-scoped base data без credential number, File и export;
- Office Manager имеет Data Owner/full-context read в утверждённой границе;
- Security имеет malware/audit metadata и scanner command, но не постоянный Worker/Credential/File content read;
- Accountant, Tender Specialist, Contractor и внешние пользователи не получают
  Worker/Credential DocPerm; Tender Specialist использует отдельную audited
  Supplier-level сводку только с агрегированными count по credential type;
- `System Manager` не имеет постоянного business read: доступ возможен только к
  exact target через активный break-glass;
- credential `File` запрещён для прямого read/delete; download/delete выполняют
  typed audited commands.

## 4. Personnel readiness

Assignment хранит versioned JSON allowlist required credential types и live
projection:

`Policy Inactive / Not Required / Missing Worker / Missing Credential /
Pending Verification / Expired / Ready`.

Positive `Ready` требует:

1. активную policy с точным hash;
2. Active Worker того же Supplier либо Employee;
3. каждый required credential type;
4. обе независимые verification marks;
5. неистёкший и неотозванный Credential;
6. актуальное Project Manager confirmation, привязанное к fingerprint evidence.

Изменение credential автоматически делает старый fingerprint непригодным при
следующей live evaluation. `PERSONNEL_READY=Completed` вызывает live assertion;
`Not Applicable` разрешён только при отсутствии contractor requirement,
Contractor Assignment и credential requirements.

## 5. Break-glass and legal hold

Break-glass:

- exact DocType/name/action (`Read`, `Preview`, `Download`);
- ticket, reason и срок от 1 до 240 минут;
- обычный requester: Security + DPO;
- requester с Security role: Product Owner + DPO;
- requester не одобряет собственный запрос;
- automatic expiry каждые 15 минут, immutable privacy audit.

Legal hold:

- exact Worker/Credential/File target, reason и future review date;
- activation и release требуют Legal + Product Owner;
- active hold блокирует соответствующую retention action, не расширяя read
  permissions.

## 6. Retention

Команда всегда начинается с deterministic dry-run plan. Выполнение требует
отдельный exact confirmation для Synthetic Test или Production mode.

- Worker Contact: удалить после 90 дней;
- credential File: удалить после 1 года;
- Worker: архивировать и обезличить после 3 лет;
- Credential: удалить number/issuer и оставить минимальную metadata после 3 лет;
- open Assignment и active legal hold блокируют действие.

Автоматическое destructive retention по scheduler не включено. Scheduler только
завершает истёкшие break-glass grants.

## 7. Verification boundary

### Historical verification baseline — superseded for current qualification

На изолированном `ca01.localhost` выполнены repeated migrate/build, static
`166/166`, targeted privacy `5/5` и full Frappe `94/94 OK`. Server acceptance
покрывает cross-role/API/report/export, project scope, masked/no-number
projections, Clean/Rejected, private streamed download, PDF/JPEG/PNG allowlist,
size/public/type denial и сохранность binary при запрещённом delete. Реальный
browser smoke подтвердил login UI и anonymous redirect protected Desk URL.

До отдельного evidence остаются:

- authenticated browser matrix по реальным ролям;
- actual malware scanner integration/quarantine и download response UAT;
- HR, DPO и Security UAT/sign-off;
- race/load, backup/restore/rollback;
- отдельное Product Owner production-PII permission.
