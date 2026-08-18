# CA-00 live inventory — w2t12b.localhost

**Снято:** 2026-08-18, read-only DB/schema commands.

**Checkout:** `w2-objects-core` / `63634f5c5191fdac566add7a69d56ee59bedcb24`; clean tree, empty diff SHA-256 `e3b0c442…b855`; branch ahead of origin by 16.

**Версии:** Frappe `15.115.0`, ERPNext `15.117.0`, ferum_custom `0.0.1`, MariaDB `10.6.27-MariaDB-ubu2204`.

Содержимое `site_config.json`, environment variables, credentials и другие секреты не читались.

## Snapshot hashes

Hashes рассчитаны MariaDB `SHA2(GROUP_CONCAT(... ORDER BY ...), 256)` с `group_concat_max_len=16777216`. Они воспроизводимы приведёнными категориями, но должны быть сняты повторно после clean baseline freeze.

| Категория | Count | SHA-256 |
| --- | ---: | --- |
| Ferum Custom DocType | 54 | `4290bd674b2930172c6010114c5637112ada519a2bb614d0b92356b523ca6efd` |
| DocField этих DocType | 828 | `9c0dae4596b66f5298150599ae475b751152c8f37b325e7cf7a97777ecf7955d` |
| live Custom Field | 69 | `71006b232f44c8627c12ecea136b09f5bb3ae0f7adae7d123e01f709fda19f07` |
| applied ferum_custom patches | 21 | `9ae7d60bc6f69d9f019c627be29f3077402db2c174ad3d4ecd8a20b85e79df54` |
| active/inactive Ferum Workflows | 9 | `82deacfa67cd7656db6df101124234c83995c7026929b5d24b8d40f443e67610` |
| Custom DocPerm rows | 16 | `aeb3532674cfaa3759184f580db9757e5ae4323110e76883f1231d67c277427d` |
| ferum_custom Scheduled Job Type | 18 | `5ca7d4355b696905633bcd6fecc9b67ed07497f5223a302a2320d328c79d5fb2` |

## Applied patches

Все 21 строки имеют `skipped = 0`:

```text
ferum_custom.patches.v0_1.setup_custom_fields_and_tax_templates
ferum_custom.patches.v0_2.add_accounting_dimension_service_project
ferum_custom.patches.v0_2.add_unique_key_billing_artifact_current
ferum_custom.patches.v0_2.add_unique_key_billing_output_active_act
ferum_custom.patches.v0_2.add_unique_key_billing_output_upd1_factura
ferum_custom.patches.v0_2.add_unique_key_contract_object_active
ferum_custom.patches.v0_2.add_unique_key_customer_tax_profile_primary
ferum_custom.patches.v0_2.add_unique_key_generated_visit
ferum_custom.patches.v0_2.add_unique_key_project_contract_link_primary
ferum_custom.patches.v0_2.add_unique_key_project_finance_summary
ferum_custom.patches.v0_2.add_unique_key_project_object_active
ferum_custom.patches.v0_2.add_unique_key_scope_rule_active
ferum_custom.patches.v0_2.backfill_contract_number_source
ferum_custom.patches.v0_2.backfill_contract_origin
ferum_custom.patches.v0_2.backfill_visit_snapshots
ferum_custom.patches.v0_2.clear_ghost_currency_mirrors
ferum_custom.patches.v0_2.install_deferred_custom_fields_e2
ferum_custom.patches.v0_2.migrate_contract_ssot_from_projects
ferum_custom.patches.v0_2.migrate_project_objects_to_contract
ferum_custom.patches.v0_2.migrate_scope_rules_to_effective_model
ferum_custom.patches.v0_2.seed_contract_number_counters
```

## Workflows

Все девять имеют `is_active = 1`:

```text
Ferum Advance Allocation Assistant Confirmation -> Ferum Advance Allocation Assistant
Ferum Contract Amendment Approval -> Ferum Contract Amendment
Ferum Contract Lifecycle -> Ferum Contract
Ferum Contractor Settlement Lifecycle -> Ferum Contractor Settlement
Ferum Incoming Invoice Approval -> Ferum Incoming Invoice
Ferum Maintenance Visit Lifecycle -> Ferum Maintenance Visit
Ferum Project Completion Exception Lifecycle -> Ferum Project Completion Exception
Ferum Service Request Lifecycle -> Ferum Service Request
Ferum Tool Exception Lifecycle -> Ferum Tool Exception
```

## Roles

Канонические 10 business roles и две technical roles существуют и не disabled. Desk access выключен только у portal roles `Заказчик`/`Подрядчик` и технической `Ferum Approval Delegate Candidate`.

```text
Бухгалтер; Генеральный директор; Заказчик; Инженер; Менеджер проектов;
Офис-менеджер; Подрядчик; Руководитель проектов; Тендерный специалист; Юрист;
System Manager; Ferum Approval Delegate Candidate
```

## Scheduled jobs

Найдено 18 методов `ferum_custom.*`, все `stopped = 0`: 14 Daily и 4 Hourly.

```text
Daily  ferum_custom.services.delegation_expiry_service.expire_due_delegations
Daily  ferum_custom.setup.contractor_user_permissions_setup.daily_ensure_contractor_user_permissions
Daily  ferum_custom.setup.customer_user_permissions_setup.daily_ensure_customer_user_permissions
Daily  ferum_custom.setup.user_permissions_setup.daily_ensure_company_user_permissions
Hourly ferum_custom.tasks.billing_artifact_lock.run
Daily  ferum_custom.tasks.billing_deadline_check.scan
Daily  ferum_custom.tasks.billing_generation_reconciliation.reconcile
Daily  ferum_custom.tasks.contract_mirror_sync.nightly_contract_mirrors
Daily  ferum_custom.tasks.finance_reconciliation.nightly_finance
Daily  ferum_custom.tasks.incoming_invoice_notifications.scan
Daily  ferum_custom.tasks.incoming_invoice_reconciliation.reconcile
Hourly ferum_custom.tasks.job_monitoring.run
Daily  ferum_custom.tasks.legal_numbering.ensure_counters
Daily  ferum_custom.tasks.maintenance_visit_generation.generate
Daily  ferum_custom.tasks.maintenance_visit_overdue.mark
Hourly ferum_custom.tasks.photo_evidence_lock.run
Daily  ferum_custom.tasks.project_completion_exception_expiry.expire
Hourly ferum_custom.tasks.service_request_sla.scan
```

## W2 physical keys

```text
tabFerum Project Scope
  active_scope_rule_uniq_key varchar(422) STORED GENERATED
  formula: CASE WHEN effective_to IS NULL
           THEN CONCAT(contract,'|',object_system,'|',work_type) ELSE NULL END
  idx_scope_rule_active_uniq: UNIQUE, SUB_PART = NULL

tabFerum Maintenance Visit
  active_generated_visit_uniq_key varchar(563) STORED GENERATED
  formula: CASE WHEN visit_origin='Generated' AND status<>'Cancelled'
           THEN CONCAT(contract,'|',object_system,'|',work_type,'|',period_key) ELSE NULL END
  idx_generated_visit_uniq: UNIQUE, SUB_PART = NULL
```

Owner-executed positive/negative evidence находится в immutable repo protocol `docs/reports/w2_v02_protocol_2026-08-17.md`; текущая инспекция не переименовывается в новый человеческий V-gate.

## Runtime checks during CA-00

```text
test_scope_rule_isolation: 17 tests, OK, 7.799s
test_ferum_project_object: 31 tests, OK, 4.510s
```

## Ограничения

- Checkout clean и является post-W2 baseline candidate, но tag/remote sync ещё не выполнены.
- Custom Field inventory зафиксирован count/hash; полный перечень 69 строк остаётся воспроизводимым live query и должен быть экспортирован в final immutable release evidence после freeze.
- Rollback rehearsal не выполнялся.
- UAT/legal/privacy approval этим inventory не подтверждаются.
