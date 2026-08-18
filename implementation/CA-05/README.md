# CA-05 — Project Document registry and independent copy custody

**Статус:** `CA-05 CORE CODE COMPLETE — SCHEMA v0.6.0 BENCH VERIFIED; DOWNSTREAM BILLING/BPM ADAPTERS OPEN`.

Инкремент вводит единый `Ferum Project Document` как реестровую карточку проектного документа. Стандартный Frappe `File` остаётся единственным хранилищем бинарника; бумажный оригинал не моделируется фиктивным файлом. Общий lifecycle карточки, состояние цифровой копии и custody бумажного оригинала — три независимых server-guarded измерения.

Каждый переход создаёт неизменяемый `Ferum Project Document Event` в одной транзакции с карточкой. Принятые/подписанные/архивные файлы и event evidence защищены от удаления. `Ferum Document Link` хранит typed Dynamic Link только на разрешённые сущности того же Service Project.

Основные команды: [documents.py](../../contract_accounting/api/documents.py).  
Controller: [ferum_project_document.py](../../contract_accounting/contract_accounting/doctype/ferum_project_document/ferum_project_document.py).  
File guard: [project_document_file_guard.py](../../contract_accounting/infrastructure/project_document_file_guard.py).

Схема и invariants: [schema_v0_6_0.md](schema_v0_6_0.md).  
Runtime evidence: [runtime_evidence_v0_6_0_2026-08-18.md](runtime_evidence_v0_6_0_2026-08-18.md).  
Implementation traceability: [traceability_v0_6_0.md](traceability_v0_6_0.md).

## Подтверждённые проверки

- standalone unit/schema suite: `77 tests`, `OK`;
- compileall, JSON parse и `git diff --check`: PASS;
- PEP 517 wheel v0.6.0: PASS;
- ERPNext v15 migrate на окончательном CODE commit: PASS;
- foreground Frappe suite: `29/29`, `OK`;
- controlled uninstall/install/migrate для 24 DocType и повторный suite: `29/29`, `OK`.

## Граница инкремента

Связь с Billing Artifact/Output/Sales Invoice/Purchase Invoice fail-closed требует установленный Service Project adapter; без него link не сохраняется. Сам adapter и billing chain относятся к CA-06/07. Process/Step/Gate relations будут добавлены CA-11 после установки их DocType. Legacy-кандидаты не мигрировались: owner утвердил reset/recreate непродукционных тестовых данных. UAT, legal/operations sign-off и production deployment не выполнялись.
