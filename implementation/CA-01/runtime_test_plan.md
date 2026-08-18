# CA-01 bench runtime test plan

**Статус:** `EXECUTED / PASS 8 OF 8 ON 2026-08-18`

Этот протокол предназначен только для нового отдельного ERPNext v15 test site приложения `contract_accounting`. Использование существующего `ferum_custom` repository/site как целевого проекта запрещено решением владельца от 2026-08-18.

## Preconditions

- отдельный bench/virtual environment в WSL;
- Frappe/ERPNext v15;
- новый disposable test site без production data;
- app получен из `Dmitriyrus99/contract-accounting` на зафиксированном commit;
- credentials предоставляются runtime‑механизмом и не читаются/не печатаются агентом;
- до install зафиксированы commit SHA, clean tree, app/framework versions и site apps list без секретов.

## Mutating setup gate

Команды выполнены только на отдельном disposable site после разрешения владельца:

```bash
bench get-app <local-or-git-contract-accounting-source>
bench --site <new-ca-test-site> install-app contract_accounting
```

Install должен создать только clean TARGET schema; business-record backfill и mapping старого `Contract.status` отсутствуют.

## Runtime tests

```bash
bench --site <new-ca-test-site> run-tests \
  --app contract_accounting \
  --module contract_accounting.contract_accounting.doctype.ferum_service_project.test_ferum_service_project
```

Versioned suite проверяет:

1. default Draft + Not Started;
2. запрет non-default lifecycle при insert;
3. запрет прямой правки lifecycle fields;
4. server transition и immutable audit update/delete guards;
5. Cancelled + Stopped и два события с одним correlation id;
6. rollback state при ошибке audit insert;
7. Suspend/Resume из Launching и Active без изменения legal status;
8. физический unique `(company, contract_number, contract_date)`.

## Post-test evidence

Зафиксировать:

- exact commit SHA и wheel hash;
- Frappe/ERPNext/Python/MariaDB versions;
- installed app version и Patch Log для `contract_accounting`;
- DocType/DocField/DocPerm/index inventory;
- одну foreground test command, exit code, test count и финальный verdict;
- controlled schema/config rollback result;
- skipped UAT/legal/finance gates отдельно от automation result.

До появления этих данных CA-01 остаётся `IN PROGRESS`, даже если versioned runtime tests присутствуют в repository.

Данные текущего прогона: [runtime_evidence_2026-08-18.md](runtime_evidence_2026-08-18.md). CA-01 остаётся `IN PROGRESS` из-за cross-module links и ручных gates, но core runtime gate закрыт.
