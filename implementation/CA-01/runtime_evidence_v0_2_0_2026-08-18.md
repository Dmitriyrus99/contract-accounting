# CA-01 v0.2.0 bench runtime evidence — 2026-08-18

**Вердикт:** `PASS — MIGRATE / 11 RUNTIME TESTS / EXPANDED SCHEMA ROLLBACK-REINSTALL`.

## Зафиксированный вход

- repository/runtime commit: `23b0dff504c0b1956a840c55cb5d2df1c7915a3a`, clean tree;
- app: `contract_accounting 0.2.0`;
- Frappe `15.118.0`, ERPNext `15.119.2`;
- runtime Python `3.12.3`, MariaDB `10.11.14`;
- wheel: `contract_accounting-0.2.0-py3-none-any.whl`;
- wheel SHA-256: `2e00b3f54de44a9d12c59efc3bfe2b5eb87bdd3455277018a29068e3b9a6349c`.

Стенд остаётся тем же отдельным disposable `ca01.localhost` и user-owned MariaDB `127.0.0.1:3317`; `ferum_custom` repository/site и production data не использовались.

## Выполненные gates

- `bench --site ca01.localhost migrate` после добавления v0.2 schema — exit `0`, model sync 10/10 и `after_migrate` выполнены;
- `python -m unittest discover -s tests -v` — `56 tests`, `OK`;
- `python -m compileall -q contract_accounting tests` — PASS;
- `git diff --check` — PASS;
- foreground Frappe suite на final commit — `Ran 11 tests in 24.049s`, `OK`, exit `0`.

Versioned runtime suite подтверждает прежние восемь lifecycle/transaction сценариев и дополнительно:

1. Service Project → Project Object → Service Object → Object System, interval overlap/delete guards и Customer mismatch refusal;
2. direct signed-term edit refusal, structured Amendment, exact transition-role refusal, conflict check, atomic apply и before/after snapshots;
3. Stage/Security/Financial Plan same-project integrity, включая отказ foreign Amendment/Stage.

## Физическая schema

- 10 custom DocType присутствуют;
- 143 DocField;
- 58 DocPerm;
- роль `Инженер` импортирована;
- legacy Contract/Project Contract Link options: 0;
- unique indexes: Service Project identity, Amendment number per project, Stage number per project;
- operational indexes: Amendment project/status, Stage project/status, Project Object project/end and object/end, Security project/status and expiry/status.

## Controlled rollback

На disposable site выполнен `uninstall-app contract_accounting --yes --no-backup`: удалены все 10 DocType/table и Module Def, site apps остались Frappe/ERPNext. Затем `install-app contract_accounting` создал 10/10 DocType заново, а расширенный suite повторно завершился `11/11 OK`.

`--no-backup` относится только к disposable acceptance site. Full backup restore и business-data restore этим прогоном не подтверждены.

## Ограничения evidence

- Frappe предупреждает, что MariaDB 10.11 новее его отображаемой tested boundary 10.8;
- queue port `11000` обслуживается локальным Redis, но background jobs в suite не запускались;
- source document пока Data reference до CA-05, не доказанная Project Document Link;
- workflow UI fixtures не создавались; server transition matrix и role guards проверены непосредственно;
- UAT, legal/finance sign-off и production deployment не выполнялись.
