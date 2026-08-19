# ERPNext master-data boundary — v0.17.0

Дата фиксации: 2026-08-19. Статус: `IMPLEMENTED / AUTOMATION PASS / MANUAL GATES OPEN`.

Этот документ конкретизирует принятый `ADR-CA-0001`: стандартные ERPNext masters остаются SSOT, а custom-модель допустима только для договорной семантики, которой нет в standard document. Он не означает UAT, production readiness или deployment.

## 1. Переиспользуемые standard masters

| Область | SSOT | Custom-граница | Проверенный инвариант |
|---|---|---|---|
| Контрагент | `Customer`, `Supplier`, `Company` | `Ferum Party Identity` хранит identity/reconciliation и ссылки, но не копирует business fields | typed POST-команда, row locks, idempotency, unique DB links, ambiguous merge запрещён |
| Адрес и контакт | `Address`, `Contact` | `Ferum Service Object` хранит только Link | Address/Contact обязаны иметь Dynamic Link на того же Customer |
| Налоговая регистрация | `Address` | child `Ferum Party Tax Registration` хранит KPP/период/branch context | KPP = 9 цифр, один primary, период непротиворечив |
| Склад | `Warehouse` | `Ferum Material Expense` хранит только Link | разрешён non-group Warehouse той же Company |
| Номенклатура и складской факт | `Item`, `UOM`, `Stock Entry` | management classification без второго stock ledger | существующие CA-07 guards сохраняются |

`Ferum Party Identity` не является вторым Customer/Supplier/Company. Она решает только сквозную идентичность, ИНН/КПП, филиальность, provenance и review возможных дублей. Link-поля read-only в UI и меняются только `link_party_identity`; одинаковый ИНН создаёт review candidate, но никогда не запускает auto-merge. Provenance и external reference после фиксации неизменяемы.

## 2. Проверка семантического соответствия

| Standard DocType | Решение первого релиза | Причина и отрицательная приёмка |
|---|---|---|
| `Project` | Не использовать как договорный root | `Ferum Service Project` одновременно несёт legal/execution lifecycle, договорную идентичность, обязательства, amendments и billing provenance. В schema нет Link на standard Project и нет custom-копии `Ferum Project`. Standard Project допустим позже только как явно отделённая delivery projection. |
| `Task` | Не использовать как process-step SSOT | Versioned template, stage gate, evidence rules и derived overdue не совпадают с Task. `Ferum Project Process Step` — semantic SSOT; standard `ToDo` уже используется как delivery projection. Custom `Ferum Task` отсутствует. |
| `Issue` | Не подменять им Service Request/Finding | Request и Finding имеют разные typed provenance, confirmation, successor, billing и evidence lifecycles. Standard Issue допустим только как явно типизированный intake/source. Custom `Ferum Issue` отсутствует. |
| `Asset` | Не использовать для customer-owned Service Object | ERPNext Asset — учёт актива компании; Service Object описывает объект обслуживания клиента и его системы. Standard Asset применяется только к собственным активам компании, когда возникает соответствующий accounting use case. Custom `Ferum Asset` отсутствует. |
| `Workflow` | `PARTIAL`, не закрыто этим increment | Server FSM остаётся семантическим authority; доказанной standard Workflow configuration для разрешённых переходов пока нет. Требуется отдельная acceptance/configuration работа. |
| `Communication` | `PARTIAL`, не закрыто этим increment | Communication разрешён как source/evidence, но positive delivery/scheduler/notification acceptance относится к следующему шагу. |

## 3. Реализованные guards

- exact typed linkage input; Frappe user defaults не могут неявно добавить Company;
- database uniqueness для Customer/Supplier/Company links и server-side conflict detection;
- row locks и rollback-to-savepoint для linkage;
- прямое редактирование master links и удаление связанной Party Identity запрещены;
- INN/KPP/branch-cycle/date guards;
- standard Address/Contact ownership check по Dynamic Link;
- standard Warehouse company/group check;
- отсутствие вторых SSOT для Customer, Supplier, Company, Address, Contact, Warehouse, Project, Task, Issue, Asset, Workflow и Communication проверяется standalone schema test.

## 4. Evidence

- standalone: `tests/test_master_data_schema.py` — 6 checks;
- Bench: `ferum_party_identity/test_ferum_party_identity.py` — 7 checks;
- existing Bench suite с новым Warehouse/Address acceptance — итоговый полный прогон `79/79 OK`;
- полный local static gate — `147/147 OK`, wheel `0.17.0`;
- подробный протокол: `runtime_evidence_v0_17_0_2026-08-19.md`.

Открыто: business/data-owner review модели Party Identity, browser UAT ролей, race/load qualification, standard Workflow/Communication acceptance, restore rehearsal и production cutover.
