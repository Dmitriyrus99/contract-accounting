# 03. Фактическая AS-IS модель

**Цель документа:** реконструировать текущую модель данных и поведение CODE, не подменяя их спецификацией.

**Дата:** 2026-08-17.

**Источник истины:** текущий незакоммиченный working tree Claude-ветки `b1fcaac`; Codex-ветка `c97c34a` используется только как сравнительный исторический baseline.

**Как проверить:** повторно разобрать JSON в каталоге `doctype`, fixture `workflow.json` и зарегистрированные hooks; статические тесты перечислены как наличие, а не как PASS. Ссылка `JSON#fieldname` указывает на DocField; `JSON#name` в schema-таблицах — явно допустимый anchor верхнеуровневого свойства `name`, а не поле документа.

## Снимок

В Claude working tree найдено 54 DocType JSON; в чистой Codex-ветке — 46. В Claude присутствуют восемь дополнительных схем, перечисленных в [01_source_inventory.md](01_source_inventory.md). Working tree до начала discovery уже содержал W2-изменения; поэтому AS-IS ниже означает именно состояние файлов на дату анализа, а не только commit HEAD.

## Сущности и ключевые поля

В столбце `Non-layout` считаются только business fields; `Section Break`, `Column Break`, `Tab Break` исключены. Общее число элементов `fields`, включая layout, приведено в следующем полном field extraction как `non-layout/total`.

| DocType | Тип | Non-layout | Ключевые поля | Link/Table | Controller file | Локальные test-файлы | Источник |
| --- | --- | ---: | --- | --- | ---: | ---: | --- |
| Ferum Advance Allocation Assistant | parent | 7 | company:Link→Company; customer:Link→Customer; payment_entry:Link→Payment Entry; status:Select→Draft/Preview Ready/Confirmed/Applied/Rejected; preview_json:JSON; confirmed_by:Link→User; confirmed_at:Datetime | company→Company; customer→Customer; payment_entry→Payment Entry; confirmed_by→User | True | 0 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_advance_allocation_assistant/ferum_advance_allocation_assistant.json#name |
| Ferum Advance Allocation Log | parent | 7 | assistant:Link→Ferum Advance Allocation Assistant; payment_entry:Link→Payment Entry; invoice:Link→Sales Invoice; allocated_amount:Currency; actor:Link→User; timestamp:Datetime; metadata_json:JSON | assistant→Ferum Advance Allocation Assistant; payment_entry→Payment Entry; invoice→Sales Invoice; actor→User | True | 0 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_advance_allocation_log/ferum_advance_allocation_log.json#name |
| Ferum Approval Delegation | parent | 6 | delegator:Link→User; delegate:Link→User; approval_scope:Select→Incoming Invoice/Contract Amendment/Project Completion Exception/Contractor Settlement/Advance Allocation/Tool Exception/Contract/All; valid_from:Date; valid_until:Date; status:Select→Active/Revoked/Expired | delegator→User; delegate→User | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_approval_delegation/ferum_approval_delegation.json#name |
| Ferum Audit Log | parent | 7 | event_type:Data; source_doctype:Link→DocType; source_name:Data; actor:Link→User; timestamp:Datetime; reason:Small Text; metadata_json:JSON | source_doctype→DocType; actor→User | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_audit_log/ferum_audit_log.json#name |
| Ferum Billing Artifact | parent | 11 | billing_output:Link→Ferum Billing Output; artifact_type:Select→Generated/Signed Scan/Other; generation_mode:Select→/Preview/Final; generation_job:Link→Ferum Document Generation Job; file:Attach; version:Int; is_signed:Check; is_current:Check; supersedes_artifact:Link→Ferum Billing Artifact; snapshot_schema_version:Int; created_at:Datetime | billing_output→Ferum Billing Output; generation_job→Ferum Document Generation Job; supersedes_artifact→Ferum Billing Artifact | True | 0 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_billing_artifact/ferum_billing_artifact.json#name |
| Ferum Billing Event | parent | 8 | billing_output:Link→Ferum Billing Output; event_type:Select→Created/Generated/Issued/Signed/Superseded/Cancelled/Corrected; related_invoice:Link→Sales Invoice; related_output:Link→Ferum Billing Output; timestamp:Datetime; actor:Link→User; reason:Data; metadata_json:JSON | billing_output→Ferum Billing Output; related_invoice→Sales Invoice; related_output→Ferum Billing Output; actor→User | True | 0 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_billing_event/ferum_billing_event.json#name |
| Ferum Billing Output | parent | 18 | company:Link→Company; service_project:Link→Ferum Service Project; sales_invoice:Link→Sales Invoice; output_type:Select→Invoice Print/Act/UPD/Invoice Factura/Correction; upd_status:Select→/1/2; basis_service_request:Link→Ferum Service Request; document_date:Date; status:Select→Draft/Generated/Issued/Signed/Superseded/Cancelled; final_artifact_status:Select→Not Started/Pending/Ready/Failed/Obsolete; document_number:Data; signer_name:Data; signer_position:Data | company→Company; service_project→Ferum Service Project; sales_invoice→Sales Invoice; basis_service_request→Ferum Service Request; supersedes→Ferum Billing Output; superseded_by→Ferum Billing Output | True | 0 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_billing_output/ferum_billing_output.json#name |
| Ferum Checklist Template | parent | 5 | template_name:Data; system_type:Select→/APS/SOUE/Smoke Control/Internal Fire Water/Gas Suppression/Water Suppression/Powder Suppression/ACS/CCTV/Intrusion Alarm/Monitoring/Other; work_type:Select→/Initial Survey/Scheduled Maintenance/Preventive Maintenance/Current Repair/Emergency Response/Operation/Monitoring/Testing/Documentation/Additional Works; status:Select→Active/Disabled; items:Table→Ferum Checklist Template Item | items→Ferum Checklist Template Item | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_checklist_template/ferum_checklist_template.json#name |
| Ferum Checklist Template Item | child | 4 | question:Data; response_type:Select→/Yes/No/Value/Text; is_required:Check; sort_order:Int |  | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_checklist_template_item/ferum_checklist_template_item.json#name |
| Ferum Company Document Settings | parent | 11 | company:Link→Company; kpp:Data; document_prefix:Data; default_bank_account:Link→Bank Account; default_letterhead:Link→Letter Head; invoice_print_format:Link→Print Format; act_print_format:Link→Print Format; upd_print_format:Link→Print Format; invoice_factura_print_format:Link→Print Format; signers:Table→Ferum Company Signer; tax_accounts:Table→Ferum Company Tax Account | company→Company; default_bank_account→Bank Account; default_letterhead→Letter Head; invoice_print_format→Print Format; act_print_format→Print Format; upd_print_format→Print Format; invoice_factura_print_format→Print Format; signers→Ferum Company Signer; tax_accounts→Ferum Company Tax Account | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_company_document_settings/ferum_company_document_settings.json#name |
| Ferum Company Signer | child | 7 | signer_name:Data; position:Data; basis:Data; valid_from:Date; valid_until:Date; is_default:Check; signature_file:Attach |  | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_company_signer/ferum_company_signer.json#name |
| Ferum Company Tax Account | child | 3 | account_head:Link→Account; purpose:Select→Output VAT; enabled:Check | account_head→Account | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_company_tax_account/ferum_company_tax_account.json#name |
| Ferum Contract | parent | 31 | company:Link→Company; contract_direction:Select→Incoming/Outgoing/Other; contract_type:Select→Service Contract/Supply Contract/Subcontract/Framework Agreement/Offer Invoice/Bank Agreement/Loan Agreement/Other; party_identity:Link→Ferum Party Identity; customer:Link→Customer; supplier:Link→Supplier; contract_number:Data; contract_date:Date; effective_from:Date; effective_to:Date; currency:Link→Currency; contract_amount_with_vat:Currency→currency | company→Company; party_identity→Ferum Party Identity; customer→Customer; supplier→Supplier; currency→Currency | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract/ferum_contract.json#name |
| Ferum Contract Amendment | parent | 14 | service_project:Link→Ferum Service Project; amendment_number:Data; amendment_date:Date; effective_date:Date; approval_status:Select→Draft/Under Review/Approved/Applied/Rejected; currency:Link→Currency; amount_delta_with_vat:Currency→currency; new_contract_amount_with_vat:Currency→currency; new_end_date:Date; scope_changed:Check; stages_changed:Check; security_changed:Check | service_project→Ferum Service Project; currency→Currency | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract_amendment/ferum_contract_amendment.json#name |
| Ferum Contract Execution Stage | parent | 21 | service_project:Link→Ferum Service Project; stage_number:Int; external_stage_id:Data; execution_status:Select→Planned/Active/Awaiting Acceptance/Accepted/Superseded/Cancelled; financial_status:Select→Not Invoiced/Invoiced/Partially Paid/Paid/Overdue; is_current:Check; execution_start_date:Date; execution_end_date:Date; service_period_start:Date; service_period_end:Date; acceptance_due_date:Date; payment_due_date:Date | service_project→Ferum Service Project; currency→Currency; supersedes→Ferum Contract Execution Stage; superseded_by→Ferum Contract Execution Stage | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract_execution_stage/ferum_contract_execution_stage.json#name |
| Ferum Contract Financial Plan Row | child | 10 | fiscal_year:Link→Fiscal Year; funding_source:Data; planned_amount_with_vat:Currency→currency; currency:Link→Currency; base_amount_with_vat:Currency; planning_basis:Select→Contract/Procurement Notice/Amendment/Manual Plan; is_verified:Check; source_reference:Data; contract_amendment:Link→Ferum Contract Amendment; comment:Small Text | fiscal_year→Fiscal Year; currency→Currency; contract_amendment→Ferum Contract Amendment | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract_financial_plan_row/ferum_contract_financial_plan_row.json#name |
| Ferum Contract Security | parent | 20 | service_project:Link→Ferum Service Project; security_type:Select→Performance Security/Warranty Obligations/Advance Return Security/Other; security_method:Select→Independent Guarantee/Cash Deposit/Other; status:Select→Draft/Required/Provided/Active/Replacement Required/Replaced/Release Due/Released/Returned/Expired/Cancelled; required_percent:Percent; basis_amount:Currency→currency; required_amount:Currency→currency; actual_amount:Currency→currency; currency:Link→Currency; conversion_rate:Float; base_amount_with_vat:Currency; valid_from:Date | service_project→Ferum Service Project; currency→Currency; contract_amendment→Ferum Contract Amendment | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract_security/ferum_contract_security.json#name |
| Ferum Contractor Settlement | parent | 13 | supplier:Link→Supplier; service_project:Link→Ferum Service Project; project_object:Link→Ferum Project Object; project_scope:Link→Ferum Project Scope; currency:Link→Currency; conversion_rate:Float; planned_amount:Currency→currency; approved_amount:Currency→currency; base_amount:Currency→currency; purchase_invoice:Link→Purchase Invoice; payment_entry:Link→Payment Entry; status:Select→Draft/Approved/Settled/Cancelled | supplier→Supplier; service_project→Ferum Service Project; project_object→Ferum Project Object; project_scope→Ferum Project Scope; currency→Currency; purchase_invoice→Purchase Invoice; payment_entry→Payment Entry | True | 0 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contractor_settlement/ferum_contractor_settlement.json#name |
| Ferum Customer Tax Profile | parent | 7 | customer:Link→Customer; kpp:Data; tax_address:Small Text; branch_name:Data; is_primary:Check; status:Select→Active/Disabled; external_reference:Data | customer→Customer | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_customer_tax_profile/ferum_customer_tax_profile.json#name |
| Ferum Customer Unit | parent | 9 | customer:Link→Customer; unit_name:Data; unit_code:Data; parent_unit:Link→Ferum Customer Unit; address:Small Text; primary_contact:Link→Contact; region:Data; status:Select→Active/Disabled; comment:Small Text | customer→Customer; parent_unit→Ferum Customer Unit; primary_contact→Contact | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_customer_unit/ferum_customer_unit.json#name |
| Ferum Document Generation Job | parent | 10 | billing_output:Link→Ferum Billing Output; mode:Select→Preview/Final; status:Select→Queued/Running/Done/Failed/Obsolete; attempt_no:Int; previous_job:Link→Ferum Document Generation Job; error:Small Text; retry_count:Int; generated_file:Link→File; started_at:Datetime; finished_at:Datetime | billing_output→Ferum Billing Output; previous_job→Ferum Document Generation Job; generated_file→File | True | 0 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_document_generation_job/ferum_document_generation_job.json#name |
| Ferum External Object Reference | parent | 11 | source_system:Data; source_object_type:Data; external_guid:Data; payload_hash:Data; source_modified_at:Datetime; target_doctype:Link→DocType; target_document:Dynamic Link→target_doctype; import_batch:Link→Ferum Import Batch; sync_status:Select→/Matched/Created/Updated/Skipped/Conflict; first_imported_at:Datetime; last_imported_at:Datetime | target_doctype→DocType; target_document→target_doctype; import_batch→Ferum Import Batch | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_external_object_reference/ferum_external_object_reference.json#name |
| Ferum File Access Policy | parent | 7 | source_doctype:Link→DocType; source_name:Data; access_scope:Select→Role/User; role:Link→Role; user:Link→User; permission_type:Select→Read/Download; is_active:Check | source_doctype→DocType; role→Role; user→User | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_file_access_policy/ferum_file_access_policy.json#name |
| Ferum File Lock | parent | 8 | file:Link→File; lock_type:Select→Signed Artifact/Accepted Evidence/Paid Incoming Invoice/Legal Archive/Other; is_active:Check; source_doctype:Link→DocType; source_name:Data; locked_at:Datetime; locked_by:Link→User; reason:Small Text | file→File; source_doctype→DocType; locked_by→User | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_file_lock/ferum_file_lock.json#name |
| Ferum Import Batch | parent | 20 | source_system:Select→1C EnterpriseData; source_file_name:Data; source_file_hash:Data; source_format:Data; source_format_version:Data; source_created_at:Datetime; company:Link→Company; period_from:Date; period_to:Date; import_mode:Select→Dry Run/Import; status:Select→Draft/Running/Completed/Completed With Issues/Failed/Cancelled; total_objects:Int | company→Company; initiated_by→User | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_import_batch/ferum_import_batch.json#name |
| Ferum Import Issue | parent | 11 | import_batch:Link→Ferum Import Batch; source_object_type:Data; external_guid:Data; severity:Select→/Info/Warning/Error; issue_code:Data; message:Small Text; source_fragment:Small Text; resolution_status:Select→Open/Resolved/Ignored; resolution_action:Small Text; resolved_by:Link→User; resolved_at:Datetime | import_batch→Ferum Import Batch; resolved_by→User | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_import_issue/ferum_import_issue.json#name |
| Ferum Incoming Invoice | parent | 26 | company:Link→Company; cost_target_type:Select→Service Project/Cost Center; service_project:Link→Ferum Service Project; cost_center:Link→Cost Center; cost_target_display:Data; cost_month:Date; payment_form:Select→Cash/Non-Cash; vat_mode:Select→VAT/No VAT; purchase_tax_template:Link→Purchase Taxes and Charges Template; counterparty_name:Data; supplier:Link→Supplier; amount_with_vat:Currency→currency | company→Company; service_project→Ferum Service Project; cost_center→Cost Center; purchase_tax_template→Purchase Taxes and Charges Template; supplier→Supplier; currency→Currency; purchase_invoice→Purchase Invoice; material_expense→Ferum Material Expense | True | 2 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_incoming_invoice/ferum_incoming_invoice.json#name |
| Ferum Incoming Invoice Payment Allocation | parent | 9 | incoming_invoice:Link→Ferum Incoming Invoice; payment_entry:Link→Payment Entry; allocated_amount:Currency→currency; currency:Link→Currency; conversion_rate:Float; allocated_base_amount:Currency→currency; reverses_allocation:Link→Ferum Incoming Invoice Payment Allocation; source_purchase_invoice:Link→Purchase Invoice; reason:Small Text | incoming_invoice→Ferum Incoming Invoice; payment_entry→Payment Entry; currency→Currency; reverses_allocation→Ferum Incoming Invoice Payment Allocation; source_purchase_invoice→Purchase Invoice | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_incoming_invoice_payment_allocation/ferum_incoming_invoice_payment_allocation.json#name |
| Ferum Legal Number Counter | parent | 4 | company:Link→Company; series_type:Select→invoice/act/upd/contract; fiscal_year:Link→Fiscal Year; next_number:Int | company→Company; fiscal_year→Fiscal Year | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_legal_number_counter/ferum_legal_number_counter.json#name |
| Ferum Maintenance Schedule | parent | 10 | service_project:Link→Ferum Service Project; project_object:Link→Ferum Project Object; project_scope:Link→Ferum Project Scope; frequency_type:Select→Monthly/Quarterly/Semiannual/Annual/Custom; start_date:Date; end_date:Date; custom_dates:Small Text; holiday_list:Link→Holiday List; status:Select→Active/Ended; superseded_by_rule:Link→Ferum Project Scope | service_project→Ferum Service Project; project_object→Ferum Project Object; project_scope→Ferum Project Scope; holiday_list→Holiday List; superseded_by_rule→Ferum Project Scope | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_maintenance_schedule/ferum_maintenance_schedule.json#name |
| Ferum Maintenance Visit | parent | 23 | service_project:Link→Ferum Service Project; project_object:Link→Ferum Project Object; project_scope:Link→Ferum Project Scope; service_object:Link→Ferum Service Object; object_system:Link→Ferum Object System; contract:Link→Ferum Contract; work_type:Select→Initial Survey/Scheduled Maintenance/Preventive Maintenance/Current Repair/Emergency Response/Operation/Monitoring/Testing/Documentation/Additional Works; schedule:Link→Ferum Maintenance Schedule; visit_origin:Select→Generated/Manual; period_key:Data; scheduled_date:Date; assigned_engineer:Link→User | service_project→Ferum Service Project; project_object→Ferum Project Object; project_scope→Ferum Project Scope; service_object→Ferum Service Object; object_system→Ferum Object System; contract→Ferum Contract; schedule→Ferum Maintenance Schedule; assigned_engineer→User; contractor→Supplier; checklist→Ferum Visit Checklist Item; reviewed_by→User | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_maintenance_visit/ferum_maintenance_visit.json#name |
| Ferum Material Expense | parent | 17 | service_project:Link→Ferum Service Project; project_object:Link→Ferum Project Object; service_request:Link→Ferum Service Request; maintenance_visit:Link→Ferum Maintenance Visit; item:Link→Item; uom:Link→UOM; qty:Float; supplier:Link→Supplier; amount_with_vat:Currency→currency; currency:Link→Currency; conversion_rate:Float; base_amount_with_vat:Currency→currency | service_project→Ferum Service Project; project_object→Ferum Project Object; service_request→Ferum Service Request; maintenance_visit→Ferum Maintenance Visit; item→Item; uom→UOM; supplier→Supplier; currency→Currency; purchase_invoice→Purchase Invoice; stock_entry→Stock Entry | True | 0 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_material_expense/ferum_material_expense.json#name |
| Ferum Notification Log | parent | 9 | event_type:Data; channel:Select→Desk/Email/Telegram; recipient:Data; source_doctype:Link→DocType; source_name:Data; status:Select→Queued/Sent/Failed; attempt_count:Int; last_error:Small Text; sent_at:Datetime | source_doctype→DocType | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_notification_log/ferum_notification_log.json#name |
| Ferum Object System | parent | 8 | service_object:Link→Ferum Service Object; system_type:Select→APS/SOUE/Smoke Control/Internal Fire Water/Gas Suppression/Water Suppression/Powder Suppression/ACS/CCTV/Intrusion Alarm/Monitoring/Other; system_name:Data; manufacturer:Data; model:Data; commissioned_on:Date; status:Select→Active/Decommissioned; comment:Small Text | service_object→Ferum Service Object | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_object_system/ferum_object_system.json#name |
| Ferum Opening Payable | parent | 17 | company:Link→Company; supplier:Link→Supplier; party_identity:Link→Ferum Party Identity; contract:Link→Ferum Contract; service_project:Link→Ferum Service Project; legacy_document_number:Data; legacy_document_date:Date; posting_date:Date; due_date:Date; currency:Link→Currency; amount_without_vat:Currency→currency; vat_amount:Currency→currency | company→Company; supplier→Supplier; party_identity→Ferum Party Identity; contract→Ferum Contract; service_project→Ferum Service Project; currency→Currency; generated_purchase_invoice→Purchase Invoice | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_opening_payable/ferum_opening_payable.json#name |
| Ferum Opening Receivable | parent | 12 | company:Link→Company; customer:Link→Customer; customer_tax_profile:Link→Ferum Customer Tax Profile; service_project:Link→Ferum Service Project; legacy_document_number:Data; posting_date:Date; due_date:Date; amount_with_vat:Currency→currency; currency:Link→Currency; dedup_key:Data; generated_sales_invoice:Link→Sales Invoice; status:Select→Draft/Created/Failed | company→Company; customer→Customer; customer_tax_profile→Ferum Customer Tax Profile; service_project→Ferum Service Project; currency→Currency; generated_sales_invoice→Sales Invoice | True | 0 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_opening_receivable/ferum_opening_receivable.json#name |
| Ferum Party Identity | parent | 22 | party_type:Select→Legal Entity/Individual Entrepreneur/Self-Employed/Individual/Government Body/Foreign Entity; full_name:Data; short_name:Data; inn:Data; ogrn:Data; ogrnip:Data; registration_country:Link→Country; is_customer:Check; is_supplier:Check; is_contractor:Check; is_self_employed:Check; is_own_company:Check | registration_country→Country; customer→Customer; supplier→Supplier; company→Company; head_party→Ferum Party Identity; tax_registrations→Ferum Party Tax Registration; possible_duplicate_of→Ferum Party Identity | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_party_identity/ferum_party_identity.json#name |
| Ferum Party Tax Registration | child | 6 | kpp:Data; branch_name:Data; is_primary:Check; valid_from:Date; valid_until:Date; tax_address:Small Text |  | True | 0 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_party_tax_registration/ferum_party_tax_registration.json#name |
| Ferum Photo Evidence | parent | 18 | maintenance_visit:Link→Ferum Maintenance Visit; service_request:Link→Ferum Service Request; category:Select→Before/After/Defect/General; file:Attach; captured_at:Datetime; uploaded_at:Datetime; uploaded_by:Link→User; is_uploaded_from_mobile:Check; is_excluded:Check; exclusion_reason:Data; review_status:Select→Pending/Accepted/Rejected; reviewed_by:Link→User | maintenance_visit→Ferum Maintenance Visit; service_request→Ferum Service Request; uploaded_by→User; reviewed_by→User | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_photo_evidence/ferum_photo_evidence.json#name |
| Ferum Project Completion Exception | parent | 8 | service_project:Link→Ferum Service Project; exception_type:Select→Tool Lost/Tool Written Off/Tool Transferred/Maintenance Cancelled by Customer/Request Administratively Closed/AR Left for Collection/Documents Closed with Discrepancy/Access Denied/Other; reason:Small Text; status:Select→Requested/Approved/Rejected/Expired; approved_by:Link→User; approved_at:Datetime; valid_until:Date; review_status:Small Text | service_project→Ferum Service Project; approved_by→User | True | 0 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_completion_exception/ferum_project_completion_exception.json#name |
| Ferum Project Contract Link | parent | 7 | service_project:Link→Ferum Service Project; contract:Link→Ferum Contract; link_role:Select→Primary Customer Contract/Customer Amendment/Subcontract/Supply Contract/Security Agreement/Other; is_active:Check; valid_from:Date; valid_until:Date; comment:Small Text | service_project→Ferum Service Project; contract→Ferum Contract | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_contract_link/ferum_project_contract_link.json#name |
| Ferum Project Finance Summary | parent | 14 | company:Link→Company; service_project:Link→Ferum Service Project; contract_amount_with_vat:Currency; recognized_revenue_without_vat:Currency; invoiced_with_vat:Currency; paid_with_vat:Currency; outstanding_with_vat:Currency; overdue_ar_with_vat:Currency; material_cost_without_vat:Currency; contractor_cost_without_vat:Currency; other_cost_without_vat:Currency; profit_without_vat:Currency | company→Company; service_project→Ferum Service Project | True | 0 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_finance_summary/ferum_project_finance_summary.json#name |
| Ferum Project Object | parent | 13 | contract:Link→Ferum Contract; service_project:Link→Ferum Service Project; service_object:Link→Ferum Service Object; customer_unit:Link→Ferum Customer Unit; effective_from:Date; effective_to:Date; added_by:Link→Ferum Contract Amendment; removed_by:Link→Ferum Contract Amendment; responsible_engineer:Link→User; contractor:Link→Supplier; customer_contact:Link→Contact; maintenance_required:Check | contract→Ferum Contract; service_project→Ferum Service Project; service_object→Ferum Service Object; customer_unit→Ferum Customer Unit; added_by→Ferum Contract Amendment; removed_by→Ferum Contract Amendment; responsible_engineer→User; contractor→Supplier; customer_contact→Contact | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_object/ferum_project_object.json#name |
| Ferum Project Scope | parent | 29 | contract:Link→Ferum Contract; contract_object:Link→Ferum Project Object; service_project:Link→Ferum Service Project; object_system:Link→Ferum Object System; work_type:Select→Initial Survey/Scheduled Maintenance/Preventive Maintenance/Current Repair/Emergency Response/Operation/Monitoring/Testing/Documentation/Additional Works; maintenance_frequency:Select→/Monthly/Quarterly/Semiannual/Annual/Custom; reaction_time_hours:Int; resolution_time_hours:Int; photo_required:Check; required_photo_count:Int; report_required:Check; journal_required:Check | contract→Ferum Contract; contract_object→Ferum Project Object; service_project→Ferum Service Project; object_system→Ferum Object System; checklist_template→Ferum Checklist Template; added_by→Ferum Contract Amendment; removed_by→Ferum Contract Amendment; holiday_list→Holiday List | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_scope/ferum_project_scope.json#name |
| Ferum Reconciliation Log | parent | 7 | reconciliation_type:Data; source_scope:Small Text; difference_amount:Currency; status:Select→Open/Resolved; details_json:JSON; created_at:Datetime; resolved_at:Datetime |  | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_reconciliation_log/ferum_reconciliation_log.json#name |
| Ferum Service Object | parent | 9 | object_name:Data; customer:Link→Customer; customer_unit:Link→Ferum Customer Unit; address:Small Text; region:Data; access_conditions:Small Text; main_contact:Link→Contact; status:Select→Active/Disabled; comment:Small Text | customer→Customer; customer_unit→Ferum Customer Unit; main_contact→Contact | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_object/ferum_service_object.json#name |
| Ferum Service Project | parent | 40 | project_name:Data; company:Link→Company; customer:Link→Customer; customer_tax_profile:Link→Ferum Customer Tax Profile; primary_customer_unit:Link→Ferum Customer Unit; project_manager:Link→User; project_lead:Link→User; project_status:Select→Launch/Execution/Suspended/Completed/Archived; problem_flag:Check; contract_number:Data; contract_date:Date; start_date:Date | company→Company; customer→Customer; customer_tax_profile→Ferum Customer Tax Profile; primary_customer_unit→Ferum Customer Unit; project_manager→User; project_lead→User; currency→Currency; financial_plan→Ferum Contract Financial Plan Row | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_project/ferum_service_project.json#name |
| Ferum Service Project Line | parent | 9 | service_project:Link→Ferum Service Project; item:Link→Item; description:Small Text; qty:Float; uom:Link→UOM; rate:Currency; amount:Currency; project_object:Link→Ferum Project Object; project_scope:Link→Ferum Project Scope | service_project→Ferum Service Project; item→Item; uom→UOM; project_object→Ferum Project Object; project_scope→Ferum Project Scope | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_project_line/ferum_service_project_line.json#name |
| Ferum Service Request | parent | 19 | request_type:Select→Emergency/Defect/Additional Work/Purchase Request/Internal Task/Document Task; priority:Select→Low/Medium/High/Critical; service_project:Link→Ferum Service Project; project_object:Link→Ferum Project Object; project_scope:Link→Ferum Project Scope; object_system:Link→Ferum Object System; service_object:Link→Ferum Service Object; subject:Data; description:Text; request_datetime:Datetime; due_datetime:Datetime; completed_on:Datetime | service_project→Ferum Service Project; project_object→Ferum Project Object; project_scope→Ferum Project Scope; object_system→Ferum Object System; service_object→Ferum Service Object; assigned_engineer→User; contractor→Supplier; maintenance_visit→Ferum Maintenance Visit; sales_invoice→Sales Invoice | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_request/ferum_service_request.json#name |
| Ferum Settings | parent | 19 | default_reaction_sla_hours:Int; default_resolution_sla_hours:Int; sla_approaching_hours_before:Int; sla_holiday_list:Link→Holiday List; sla_holiday_rule_effective_from:Datetime; maintenance_comment_required:Check; default_photo_policy:Select; visit_generation_horizon_days:Int; maintenance_source_schedule:Check; maintenance_rules_transfer_run_at:Datetime; maintenance_source_switched_at:Datetime; billing_output_deadline_days:Int | sla_holiday_list→Holiday List | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_settings/ferum_settings.json#name |
| Ferum Tool | parent | 8 | tool_code:Data; item:Link→Item; tool_name:Data; serial_number:Data; status:Select→Available/Issued/Lost/Written Off/Repair; current_holder_type:Select→/Employee/Supplier/Warehouse; current_holder:Dynamic Link→current_holder_type; current_project:Link→Ferum Service Project | item→Item; current_holder→current_holder_type; current_project→Ferum Service Project | True | 0 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_tool/ferum_tool.json#name |
| Ferum Tool Exception | parent | 8 | tool:Link→Ferum Tool; service_project:Link→Ferum Service Project; exception_type:Select→Lost/Write Off/Damage/Other; opened_at:Datetime; status:Select→Open/Approved/Closed/Rejected; approved_by:Link→User; closed_at:Datetime; resolution:Small Text | tool→Ferum Tool; service_project→Ferum Service Project; approved_by→User | True | 0 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_tool_exception/ferum_tool_exception.json#name |
| Ferum Tool Movement | parent | 12 | tool:Link→Ferum Tool; movement_type:Select→Issue/Return/Transfer/Lost/Found/Write Off/Adjustment; movement_datetime:Datetime; status:Select→Done/Cancelled; from_holder_type:Select→Employee/Supplier/Warehouse; from_holder:Dynamic Link→from_holder_type; to_holder_type:Select→Employee/Supplier/Warehouse; to_holder:Dynamic Link→to_holder_type; service_project:Link→Ferum Service Project; project_object:Link→Ferum Project Object; reason:Small Text; document:Attach | tool→Ferum Tool; from_holder→from_holder_type; to_holder→to_holder_type; service_project→Ferum Service Project; project_object→Ferum Project Object | True | 0 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_tool_movement/ferum_tool_movement.json#name |
| Ferum Visit Checklist Item | child | 7 | question:Data; response_type:Select→/Yes/No/Value/Text; response_value:Data; is_ok:Check; is_required:Check; comment:Data; photo:Link→Ferum Photo Evidence | photo→Ferum Photo Evidence | True | 1 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_visit_checklist_item/ferum_visit_checklist_item.json#name |

`Controller file=True` означает только наличие одноимённого `.py`; это не утверждение о наличии собственных правил. Например, child controllers могут быть минимальными, а валидация выполняется родителем.

## Полное typed field extraction

Легенда: `R` — `reqd=1`, `RO` — `read_only=1`, `D=value` — непустой default. Для Link/Dynamic Link/Table/Currency после `→` показаны `options`; Select-options здесь не дублируются и читаются по schema anchor, а status-like Select полностью сведены ниже. Таблица включает все non-layout fields; layout учитывается только в знаменателе.

| DocType | Non-layout/total | Все non-layout fields | Источник схемы |
| --- | ---: | --- | --- |
| Ferum Advance Allocation Assistant | 7/9 | `company:Link→Company [R]`; `customer:Link→Customer [R]`; `payment_entry:Link→Payment Entry [R]`; `status:Select [R,RO,D=Draft]`; `preview_json:JSON [RO]`; `confirmed_by:Link→User [RO]`; `confirmed_at:Datetime [RO]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_advance_allocation_assistant/ferum_advance_allocation_assistant.json#name |
| Ferum Advance Allocation Log | 7/7 | `assistant:Link→Ferum Advance Allocation Assistant [R,RO]`; `payment_entry:Link→Payment Entry [R,RO]`; `invoice:Link→Sales Invoice [R,RO]`; `allocated_amount:Currency [R,RO]`; `actor:Link→User [R,RO]`; `timestamp:Datetime [R,RO]`; `metadata_json:JSON [RO]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_advance_allocation_log/ferum_advance_allocation_log.json#name |
| Ferum Approval Delegation | 6/6 | `delegator:Link→User [R]`; `delegate:Link→User [R]`; `approval_scope:Select [R]`; `valid_from:Date [R]`; `valid_until:Date [R]`; `status:Select [R,D=Active]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_approval_delegation/ferum_approval_delegation.json#name |
| Ferum Audit Log | 7/7 | `event_type:Data [R,RO]`; `source_doctype:Link→DocType [R,RO]`; `source_name:Data [R,RO]`; `actor:Link→User [R,RO]`; `timestamp:Datetime [R,RO]`; `reason:Small Text [RO]`; `metadata_json:JSON [RO]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_audit_log/ferum_audit_log.json#name |
| Ferum Billing Artifact | 11/11 | `billing_output:Link→Ferum Billing Output [R]`; `artifact_type:Select [R]`; `generation_mode:Select`; `generation_job:Link→Ferum Document Generation Job`; `file:Attach [R]`; `version:Int [RO]`; `is_signed:Check`; `is_current:Check`; `supersedes_artifact:Link→Ferum Billing Artifact`; `snapshot_schema_version:Int`; `created_at:Datetime [RO]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_billing_artifact/ferum_billing_artifact.json#name |
| Ferum Billing Event | 8/8 | `billing_output:Link→Ferum Billing Output [R,RO]`; `event_type:Select [R,RO]`; `related_invoice:Link→Sales Invoice [RO]`; `related_output:Link→Ferum Billing Output [RO]`; `timestamp:Datetime [R,RO]`; `actor:Link→User [R,RO]`; `reason:Data [RO]`; `metadata_json:JSON [RO]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_billing_event/ferum_billing_event.json#name |
| Ferum Billing Output | 18/22 | `company:Link→Company [R]`; `service_project:Link→Ferum Service Project [R]`; `sales_invoice:Link→Sales Invoice [R]`; `output_type:Select [R]`; `upd_status:Select`; `basis_service_request:Link→Ferum Service Request`; `document_date:Date [R]`; `status:Select [R,D=Draft]`; `final_artifact_status:Select [RO,D=Not Started]`; `document_number:Data [RO]`; `signer_name:Data [RO]`; `signer_position:Data [RO]`; `signer_basis:Data [RO]`; `shipment_date:Date`; `receipt_date:Date`; `printing_context_snapshot:JSON [RO]`; `supersedes:Link→Ferum Billing Output`; `superseded_by:Link→Ferum Billing Output [RO]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_billing_output/ferum_billing_output.json#name |
| Ferum Checklist Template | 5/5 | `template_name:Data [R]`; `system_type:Select`; `work_type:Select`; `status:Select [R]`; `items:Table→Ferum Checklist Template Item` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_checklist_template/ferum_checklist_template.json#name |
| Ferum Checklist Template Item | 4/4 | `question:Data [R]`; `response_type:Select`; `is_required:Check [D=0]`; `sort_order:Int` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_checklist_template_item/ferum_checklist_template_item.json#name |
| Ferum Company Document Settings | 11/15 | `company:Link→Company [R]`; `kpp:Data [R]`; `document_prefix:Data [R]`; `default_bank_account:Link→Bank Account`; `default_letterhead:Link→Letter Head`; `invoice_print_format:Link→Print Format`; `act_print_format:Link→Print Format`; `upd_print_format:Link→Print Format`; `invoice_factura_print_format:Link→Print Format`; `signers:Table→Ferum Company Signer`; `tax_accounts:Table→Ferum Company Tax Account` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_company_document_settings/ferum_company_document_settings.json#name |
| Ferum Company Signer | 7/7 | `signer_name:Data [R]`; `position:Data`; `basis:Data`; `valid_from:Date`; `valid_until:Date`; `is_default:Check [D=0]`; `signature_file:Attach` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_company_signer/ferum_company_signer.json#name |
| Ferum Company Tax Account | 3/3 | `account_head:Link→Account [R]`; `purpose:Select [R,D=Output VAT]`; `enabled:Check [D=1]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_company_tax_account/ferum_company_tax_account.json#name |
| Ferum Contract | 31/37 | `company:Link→Company [R]`; `contract_direction:Select [R]`; `contract_type:Select [R]`; `party_identity:Link→Ferum Party Identity`; `customer:Link→Customer`; `supplier:Link→Supplier`; `contract_number:Data [R]`; `contract_date:Date`; `effective_from:Date`; `effective_to:Date`; `currency:Link→Currency [R,D=RUB]`; `contract_amount_with_vat:Currency→currency`; `amount_without_vat:Currency→currency`; `vat_amount:Currency→currency`; `vat_scheme:Select`; `payment_terms:Small Text`; `payment_due_days:Int`; `billing_frequency:Select`; `procurement_law:Data`; `procurement_number:Data`; `eis_contract_registry_number:Data`; `ikz:Data`; `igk:Data`; `has_quality_guarantee:Check [D=0]`; `quality_guarantee_terms:Small Text`; `status:Select [R,D=Draft]`; `contract_origin:Select [D=Native]`; `contract_number_source:Select [RO,D=Manual]`; `schedule_flag_rule_edited:Check [RO,D=0]`; `external_reference:Data`; `comment:Small Text` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract/ferum_contract.json#name |
| Ferum Contractor Settlement | 13/20 | `supplier:Link→Supplier [R]`; `service_project:Link→Ferum Service Project [R]`; `project_object:Link→Ferum Project Object`; `project_scope:Link→Ferum Project Scope`; `currency:Link→Currency [R,D=RUB]`; `conversion_rate:Float [D=1.0]`; `planned_amount:Currency→currency`; `approved_amount:Currency→currency`; `base_amount:Currency→currency [RO]`; `purchase_invoice:Link→Purchase Invoice`; `payment_entry:Link→Payment Entry`; `status:Select [R,RO,D=Draft]`; `comment:Small Text` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contractor_settlement/ferum_contractor_settlement.json#name |
| Ferum Contract Amendment | 14/17 | `service_project:Link→Ferum Service Project [R]`; `amendment_number:Data [R]`; `amendment_date:Date [R]`; `effective_date:Date [R]`; `approval_status:Select [R,RO,D=Draft]`; `currency:Link→Currency [R,D=RUB]`; `amount_delta_with_vat:Currency→currency`; `new_contract_amount_with_vat:Currency→currency`; `new_end_date:Date`; `scope_changed:Check [D=0]`; `stages_changed:Check [D=0]`; `security_changed:Check [D=0]`; `document:Attach`; `comment:Small Text` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract_amendment/ferum_contract_amendment.json#name |
| Ferum Contract Execution Stage | 21/25 | `service_project:Link→Ferum Service Project [R]`; `stage_number:Int [R]`; `external_stage_id:Data`; `execution_status:Select [R,D=Planned]`; `financial_status:Select [RO,D=Not Invoiced]`; `is_current:Check [D=1]`; `execution_start_date:Date [R]`; `execution_end_date:Date [R]`; `service_period_start:Date`; `service_period_end:Date`; `acceptance_due_date:Date`; `payment_due_date:Date`; `planned_amount_with_vat:Currency→currency`; `currency:Link→Currency [R,D=RUB]`; `conversion_rate:Float [D=1.0]`; `base_amount_with_vat:Currency [RO]`; `external_source:Data`; `external_updated_at:Datetime`; `supersedes:Link→Ferum Contract Execution Stage`; `superseded_by:Link→Ferum Contract Execution Stage [RO]`; `comment:Small Text` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract_execution_stage/ferum_contract_execution_stage.json#name |
| Ferum Contract Financial Plan Row | 10/10 | `fiscal_year:Link→Fiscal Year [R]`; `funding_source:Data`; `planned_amount_with_vat:Currency→currency [R]`; `currency:Link→Currency`; `base_amount_with_vat:Currency`; `planning_basis:Select [R]`; `is_verified:Check [D=0]`; `source_reference:Data`; `contract_amendment:Link→Ferum Contract Amendment`; `comment:Small Text` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract_financial_plan_row/ferum_contract_financial_plan_row.json#name |
| Ferum Contract Security | 20/23 | `service_project:Link→Ferum Service Project [R]`; `security_type:Select [R]`; `security_method:Select [R]`; `status:Select [R,D=Draft]`; `required_percent:Percent`; `basis_amount:Currency→currency`; `required_amount:Currency→currency`; `actual_amount:Currency→currency`; `currency:Link→Currency [D=RUB]`; `conversion_rate:Float`; `base_amount_with_vat:Currency`; `valid_from:Date`; `valid_until:Date`; `return_due_date:Date`; `returned_at:Date`; `bank_or_guarantor:Data`; `external_reference:Data`; `contract_amendment:Link→Ferum Contract Amendment`; `document:Attach`; `comment:Small Text` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract_security/ferum_contract_security.json#name |
| Ferum Customer Tax Profile | 7/7 | `customer:Link→Customer [R]`; `kpp:Data [R]`; `tax_address:Small Text`; `branch_name:Data`; `is_primary:Check [D=0]`; `status:Select [R,D=Active]`; `external_reference:Data` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_customer_tax_profile/ferum_customer_tax_profile.json#name |
| Ferum Customer Unit | 9/9 | `customer:Link→Customer [R]`; `unit_name:Data [R]`; `unit_code:Data`; `parent_unit:Link→Ferum Customer Unit`; `address:Small Text`; `primary_contact:Link→Contact`; `region:Data`; `status:Select [R]`; `comment:Small Text` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_customer_unit/ferum_customer_unit.json#name |
| Ferum Document Generation Job | 10/10 | `billing_output:Link→Ferum Billing Output [R,RO]`; `mode:Select [R,RO]`; `status:Select [R,RO,D=Queued]`; `attempt_no:Int [R,RO]`; `previous_job:Link→Ferum Document Generation Job [RO]`; `error:Small Text [RO]`; `retry_count:Int [RO,D=0]`; `generated_file:Link→File [RO]`; `started_at:Datetime [RO]`; `finished_at:Datetime [RO]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_document_generation_job/ferum_document_generation_job.json#name |
| Ferum External Object Reference | 11/17 | `source_system:Data [R]`; `source_object_type:Data [R]`; `external_guid:Data [R]`; `payload_hash:Data [R]`; `source_modified_at:Datetime`; `target_doctype:Link→DocType`; `target_document:Dynamic Link→target_doctype`; `import_batch:Link→Ferum Import Batch [R]`; `sync_status:Select [R]`; `first_imported_at:Datetime [RO]`; `last_imported_at:Datetime [RO]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_external_object_reference/ferum_external_object_reference.json#name |
| Ferum File Access Policy | 7/7 | `source_doctype:Link→DocType [R]`; `source_name:Data [R]`; `access_scope:Select [R]`; `role:Link→Role`; `user:Link→User`; `permission_type:Select [R]`; `is_active:Check [D=1]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_file_access_policy/ferum_file_access_policy.json#name |
| Ferum File Lock | 8/8 | `file:Link→File [R]`; `lock_type:Select`; `is_active:Check [D=1]`; `source_doctype:Link→DocType`; `source_name:Data`; `locked_at:Datetime [RO]`; `locked_by:Link→User [RO]`; `reason:Small Text` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_file_lock/ferum_file_lock.json#name |
| Ferum Import Batch | 20/28 | `source_system:Select [R]`; `source_file_name:Data [R]`; `source_file_hash:Data [R]`; `source_format:Data`; `source_format_version:Data`; `source_created_at:Datetime`; `company:Link→Company [R]`; `period_from:Date`; `period_to:Date`; `import_mode:Select [R,D=Dry Run]`; `status:Select [R,RO,D=Draft]`; `total_objects:Int [RO,D=0]`; `created_objects:Int [RO,D=0]`; `updated_objects:Int [RO,D=0]`; `skipped_objects:Int [RO,D=0]`; `warning_count:Int [RO,D=0]`; `error_count:Int [RO,D=0]`; `started_at:Datetime [RO]`; `completed_at:Datetime [RO]`; `initiated_by:Link→User [RO]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_import_batch/ferum_import_batch.json#name |
| Ferum Import Issue | 11/16 | `import_batch:Link→Ferum Import Batch [R]`; `source_object_type:Data`; `external_guid:Data`; `severity:Select [R]`; `issue_code:Data [R]`; `message:Small Text [R]`; `source_fragment:Small Text`; `resolution_status:Select [R,D=Open]`; `resolution_action:Small Text`; `resolved_by:Link→User [RO]`; `resolved_at:Datetime [RO]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_import_issue/ferum_import_issue.json#name |
| Ferum Incoming Invoice | 26/36 | `company:Link→Company [R]`; `cost_target_type:Select [R]`; `service_project:Link→Ferum Service Project`; `cost_center:Link→Cost Center`; `cost_target_display:Data [RO]`; `cost_month:Date [R]`; `payment_form:Select [R]`; `vat_mode:Select [R]`; `purchase_tax_template:Link→Purchase Taxes and Charges Template`; `counterparty_name:Data [R]`; `supplier:Link→Supplier`; `amount_with_vat:Currency→currency [R]`; `currency:Link→Currency [R,D=RUB]`; `conversion_rate:Float [D=1.0]`; `base_amount_with_vat:Currency→currency [RO]`; `payment_basis:Small Text [R]`; `payment_due_date:Date [R]`; `recipient_details:Small Text`; `approval_status:Select [R,RO,D=Draft]`; `payment_status:Select [RO]`; `payment_status_reason_code:Data [RO]`; `payment_status_reason:Small Text [RO]`; `rejection_reason:Small Text`; `prepaid_balance_service:Data`; `purchase_invoice:Link→Purchase Invoice`; `material_expense:Link→Ferum Material Expense` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_incoming_invoice/ferum_incoming_invoice.json#name |
| Ferum Incoming Invoice Payment Allocation | 9/9 | `incoming_invoice:Link→Ferum Incoming Invoice [R,RO]`; `payment_entry:Link→Payment Entry [R,RO]`; `allocated_amount:Currency→currency [R,RO]`; `currency:Link→Currency [R,RO,D=RUB]`; `conversion_rate:Float [R,RO,D=1.0]`; `allocated_base_amount:Currency→currency [R,RO]`; `reverses_allocation:Link→Ferum Incoming Invoice Payment Allocation [RO]`; `source_purchase_invoice:Link→Purchase Invoice [RO]`; `reason:Small Text [RO]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_incoming_invoice_payment_allocation/ferum_incoming_invoice_payment_allocation.json#name |
| Ferum Legal Number Counter | 4/4 | `company:Link→Company [R,RO]`; `series_type:Select [R,RO]`; `fiscal_year:Link→Fiscal Year [R,RO]`; `next_number:Int [R,RO,D=1]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_legal_number_counter/ferum_legal_number_counter.json#name |
| Ferum Maintenance Schedule | 10/10 | `service_project:Link→Ferum Service Project [R]`; `project_object:Link→Ferum Project Object [R]`; `project_scope:Link→Ferum Project Scope [R]`; `frequency_type:Select [R]`; `start_date:Date [R]`; `end_date:Date`; `custom_dates:Small Text`; `holiday_list:Link→Holiday List`; `status:Select [R]`; `superseded_by_rule:Link→Ferum Project Scope [RO]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_maintenance_schedule/ferum_maintenance_schedule.json#name |
| Ferum Maintenance Visit | 23/33 | `service_project:Link→Ferum Service Project [R]`; `project_object:Link→Ferum Project Object [R]`; `project_scope:Link→Ferum Project Scope [R]`; `service_object:Link→Ferum Service Object [R]`; `object_system:Link→Ferum Object System [R]`; `contract:Link→Ferum Contract [R]`; `work_type:Select [R]`; `schedule:Link→Ferum Maintenance Schedule`; `visit_origin:Select [R,D=Manual]`; `period_key:Data`; `scheduled_date:Date [R]`; `assigned_engineer:Link→User`; `contractor:Link→Supplier`; `started_at:Datetime`; `completed_at:Datetime`; `visit_report:Small Text`; `checklist:Table→Ferum Visit Checklist Item`; `review_status:Select [R,RO,D=Pending]`; `reviewed_by:Link→User [RO]`; `reviewed_at:Datetime [RO]`; `status:Select [R,RO,D=Planned]`; `cancellation_reason:Small Text`; `comment:Small Text` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_maintenance_visit/ferum_maintenance_visit.json#name |
| Ferum Material Expense | 17/23 | `service_project:Link→Ferum Service Project [R]`; `project_object:Link→Ferum Project Object`; `service_request:Link→Ferum Service Request`; `maintenance_visit:Link→Ferum Maintenance Visit`; `item:Link→Item`; `uom:Link→UOM`; `qty:Float`; `supplier:Link→Supplier`; `amount_with_vat:Currency→currency [R]`; `currency:Link→Currency [R,D=RUB]`; `conversion_rate:Float [D=1.0]`; `base_amount_with_vat:Currency→currency [RO]`; `amount_without_vat:Currency→currency`; `base_amount_without_vat:Currency→currency [RO]`; `purchase_invoice:Link→Purchase Invoice`; `stock_entry:Link→Stock Entry`; `status:Select [R,D=Draft]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_material_expense/ferum_material_expense.json#name |
| Ferum Notification Log | 9/9 | `event_type:Data [R,RO]`; `channel:Select [R,RO]`; `recipient:Data [R,RO]`; `source_doctype:Link→DocType [RO]`; `source_name:Data [RO]`; `status:Select [R,RO,D=Queued]`; `attempt_count:Int [RO,D=0]`; `last_error:Small Text [RO]`; `sent_at:Datetime [RO]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_notification_log/ferum_notification_log.json#name |
| Ferum Object System | 8/8 | `service_object:Link→Ferum Service Object [R]`; `system_type:Select [R]`; `system_name:Data [R]`; `manufacturer:Data`; `model:Data`; `commissioned_on:Date`; `status:Select [R]`; `comment:Small Text` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_object_system/ferum_object_system.json#name |
| Ferum Opening Payable | 17/23 | `company:Link→Company [R]`; `supplier:Link→Supplier [R]`; `party_identity:Link→Ferum Party Identity`; `contract:Link→Ferum Contract`; `service_project:Link→Ferum Service Project`; `legacy_document_number:Data [R]`; `legacy_document_date:Date`; `posting_date:Date [R,D=Today]`; `due_date:Date [R]`; `currency:Link→Currency [R,D=RUB]`; `amount_without_vat:Currency→currency`; `vat_amount:Currency→currency`; `amount_with_vat:Currency→currency [R]`; `dedup_key:Data [R]`; `external_reference:Data`; `generated_purchase_invoice:Link→Purchase Invoice [RO]`; `status:Select [R,RO,D=Draft]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_opening_payable/ferum_opening_payable.json#name |
| Ferum Opening Receivable | 12/18 | `company:Link→Company [R]`; `customer:Link→Customer [R]`; `customer_tax_profile:Link→Ferum Customer Tax Profile`; `service_project:Link→Ferum Service Project`; `legacy_document_number:Data [R]`; `posting_date:Date [R,D=Today]`; `due_date:Date [R]`; `amount_with_vat:Currency→currency [R]`; `currency:Link→Currency [D=RUB]`; `dedup_key:Data [R]`; `generated_sales_invoice:Link→Sales Invoice [RO]`; `status:Select [R,RO,D=Draft]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_opening_receivable/ferum_opening_receivable.json#name |
| Ferum Party Identity | 22/32 | `party_type:Select [R]`; `full_name:Data [R]`; `short_name:Data`; `inn:Data`; `ogrn:Data`; `ogrnip:Data`; `registration_country:Link→Country [D=Russian Federation]`; `is_customer:Check [D=0]`; `is_supplier:Check [D=0]`; `is_contractor:Check [D=0]`; `is_self_employed:Check [D=0]`; `is_own_company:Check [D=0]`; `customer:Link→Customer`; `supplier:Link→Supplier`; `company:Link→Company`; `is_branch:Check [D=0]`; `head_party:Link→Ferum Party Identity`; `status:Select [R,D=Active]`; `external_reference:Data`; `tax_registrations:Table→Ferum Party Tax Registration`; `possible_duplicate_of:Link→Ferum Party Identity`; `duplicate_review_status:Select [D=Not Reviewed]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_party_identity/ferum_party_identity.json#name |
| Ferum Party Tax Registration | 6/6 | `kpp:Data [R]`; `branch_name:Data`; `is_primary:Check [D=0]`; `valid_from:Date`; `valid_until:Date`; `tax_address:Small Text` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_party_tax_registration/ferum_party_tax_registration.json#name |
| Ferum Photo Evidence | 18/26 | `maintenance_visit:Link→Ferum Maintenance Visit`; `service_request:Link→Ferum Service Request`; `category:Select`; `file:Attach [R]`; `captured_at:Datetime`; `uploaded_at:Datetime [RO]`; `uploaded_by:Link→User [RO]`; `is_uploaded_from_mobile:Check`; `is_excluded:Check`; `exclusion_reason:Data`; `review_status:Select [R,D=Pending]`; `reviewed_by:Link→User [RO]`; `reviewed_at:Datetime [RO]`; `client_uuid:Data`; `client_created_at:Datetime`; `device_id:Data`; `upload_session_id:Data`; `sync_status:Select` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_photo_evidence/ferum_photo_evidence.json#name |
| Ferum Project Completion Exception | 8/12 | `service_project:Link→Ferum Service Project [R]`; `exception_type:Select [R]`; `reason:Small Text [R]`; `status:Select [R,RO,D=Requested]`; `approved_by:Link→User [RO]`; `approved_at:Datetime [RO]`; `valid_until:Date`; `review_status:Small Text` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_completion_exception/ferum_project_completion_exception.json#name |
| Ferum Project Contract Link | 7/8 | `service_project:Link→Ferum Service Project [R]`; `contract:Link→Ferum Contract [R]`; `link_role:Select [R]`; `is_active:Check [D=1]`; `valid_from:Date`; `valid_until:Date`; `comment:Small Text` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_contract_link/ferum_project_contract_link.json#name |
| Ferum Project Finance Summary | 14/20 | `company:Link→Company [R,RO]`; `service_project:Link→Ferum Service Project [R,RO]`; `contract_amount_with_vat:Currency [RO]`; `recognized_revenue_without_vat:Currency [RO]`; `invoiced_with_vat:Currency [RO]`; `paid_with_vat:Currency [RO]`; `outstanding_with_vat:Currency [RO]`; `overdue_ar_with_vat:Currency [RO]`; `material_cost_without_vat:Currency [RO]`; `contractor_cost_without_vat:Currency [RO]`; `other_cost_without_vat:Currency [RO]`; `profit_without_vat:Currency [RO]`; `profitability_percent:Percent [RO]`; `last_recalculated_at:Datetime [RO]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_finance_summary/ferum_project_finance_summary.json#name |
| Ferum Project Object | 13/13 | `contract:Link→Ferum Contract [R]`; `service_project:Link→Ferum Service Project`; `service_object:Link→Ferum Service Object [R]`; `customer_unit:Link→Ferum Customer Unit`; `effective_from:Date [R]`; `effective_to:Date`; `added_by:Link→Ferum Contract Amendment`; `removed_by:Link→Ferum Contract Amendment`; `responsible_engineer:Link→User`; `contractor:Link→Supplier`; `customer_contact:Link→Contact`; `maintenance_required:Check [D=1]`; `comment:Small Text` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_object/ferum_project_object.json#name |
| Ferum Project Scope | 29/29 | `contract:Link→Ferum Contract [R]`; `contract_object:Link→Ferum Project Object [R]`; `service_project:Link→Ferum Service Project`; `object_system:Link→Ferum Object System [R]`; `work_type:Select [R]`; `maintenance_frequency:Select`; `reaction_time_hours:Int`; `resolution_time_hours:Int`; `photo_required:Check`; `required_photo_count:Int`; `report_required:Check`; `journal_required:Check`; `emergency_service:Check`; `monitoring_required:Check`; `separate_approval_required:Check`; `warranty_required:Check`; `materials_responsibility:Select`; `material_limit_with_vat:Currency`; `warranty_period_months:Int`; `warranty_terms:Small Text`; `checklist_template:Link→Ferum Checklist Template`; `effective_from:Date [R]`; `effective_to:Date`; `added_by:Link→Ferum Contract Amendment`; `removed_by:Link→Ferum Contract Amendment`; `window_rule:Data`; `custom_dates:Small Text`; `holiday_list:Link→Holiday List`; `comment:Small Text` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_scope/ferum_project_scope.json#name |
| Ferum Reconciliation Log | 7/7 | `reconciliation_type:Data [R,RO]`; `source_scope:Small Text [RO]`; `difference_amount:Currency [RO]`; `status:Select [R,RO,D=Open]`; `details_json:JSON [RO]`; `created_at:Datetime [R,RO,D=Now]`; `resolved_at:Datetime [RO]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_reconciliation_log/ferum_reconciliation_log.json#name |
| Ferum Service Object | 9/9 | `object_name:Data [R]`; `customer:Link→Customer [R]`; `customer_unit:Link→Ferum Customer Unit`; `address:Small Text [R]`; `region:Data`; `access_conditions:Small Text`; `main_contact:Link→Contact`; `status:Select [R]`; `comment:Small Text` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_object/ferum_service_object.json#name |
| Ferum Service Project | 40/47 | `project_name:Data [R]`; `company:Link→Company [R]`; `customer:Link→Customer [R]`; `customer_tax_profile:Link→Ferum Customer Tax Profile`; `primary_customer_unit:Link→Ferum Customer Unit`; `project_manager:Link→User`; `project_lead:Link→User`; `project_status:Select [R,RO,D=Launch]`; `problem_flag:Check [RO,D=0]`; `contract_number:Data [RO]`; `contract_date:Date [RO]`; `start_date:Date [RO]`; `end_date:Date [RO]`; `contract_amount_with_vat:Currency→currency [RO]`; `contract_amount_without_vat:Currency→currency [RO]`; `vat_amount:Currency→currency [RO]`; `currency:Link→Currency [RO]`; `payment_terms:Small Text [RO]`; `payment_due_days:Int [RO]`; `billing_frequency:Select [RO]`; `source_type:Data`; `procurement_number:Data`; `procurement_law:Data`; `procurement_procedure:Data`; `procurement_source_url:Data`; `source_nmc:Currency→currency`; `award_price:Currency→currency`; `price_reduction_percent:Percent`; `bid_security_amount:Currency→currency`; `performance_security_percent:Percent`; `source_customer_inn:Data`; `source_procurement_status:Data`; `source_snapshot_date:Date`; `eis_contract_registry_number:Data [RO]`; `eis_electronic_contract_id:Data`; `igk:Data [RO]`; `source_advance:Data`; `has_quality_guarantee:Check [RO,D=0]`; `quality_guarantee_terms:Small Text [RO]`; `financial_plan:Table→Ferum Contract Financial Plan Row` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_project/ferum_service_project.json#name |
| Ferum Service Project Line | 9/9 | `service_project:Link→Ferum Service Project [R]`; `item:Link→Item`; `description:Small Text [R]`; `qty:Float [R]`; `uom:Link→UOM`; `rate:Currency [R]`; `amount:Currency [RO]`; `project_object:Link→Ferum Project Object`; `project_scope:Link→Ferum Project Scope` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_project_line/ferum_service_project_line.json#name |
| Ferum Service Request | 19/30 | `request_type:Select [R]`; `priority:Select`; `service_project:Link→Ferum Service Project [R]`; `project_object:Link→Ferum Project Object`; `project_scope:Link→Ferum Project Scope`; `object_system:Link→Ferum Object System`; `service_object:Link→Ferum Service Object [RO]`; `subject:Data [R]`; `description:Text`; `request_datetime:Datetime [R,D=Now]`; `due_datetime:Datetime [RO]`; `completed_on:Datetime [RO]`; `assigned_engineer:Link→User`; `contractor:Link→Supplier`; `maintenance_visit:Link→Ferum Maintenance Visit`; `sales_invoice:Link→Sales Invoice`; `status:Select [R,RO,D=Open]`; `resolution:Small Text`; `cancellation_reason:Small Text` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_request/ferum_service_request.json#name |
| Ferum Settings | 19/19 | `default_reaction_sla_hours:Int`; `default_resolution_sla_hours:Int`; `sla_approaching_hours_before:Int [D=2]`; `sla_holiday_list:Link→Holiday List`; `sla_holiday_rule_effective_from:Datetime`; `maintenance_comment_required:Check [D=0]`; `default_photo_policy:Select`; `visit_generation_horizon_days:Int [D=60]`; `maintenance_source_schedule:Check [D=0]`; `maintenance_rules_transfer_run_at:Datetime [RO]`; `maintenance_source_switched_at:Datetime [RO]`; `billing_output_deadline_days:Int [D=10]`; `stuck_job_timeout_minutes:Int [D=30]`; `scheduler_heartbeat_max_age_minutes:Int [D=60]`; `incoming_invoice_due_soon_days:Int [D=3]`; `ar_collection_exception_default_days:Int [D=180]`; `notification_defaults:JSON`; `readiness_policy:JSON`; `delegation_enabled:Check [D=0]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_settings/ferum_settings.json#name |
| Ferum Tool | 8/13 | `tool_code:Data [R]`; `item:Link→Item`; `tool_name:Data [R]`; `serial_number:Data`; `status:Select [R,RO,D=Available]`; `current_holder_type:Select [RO]`; `current_holder:Dynamic Link→current_holder_type [RO]`; `current_project:Link→Ferum Service Project` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_tool/ferum_tool.json#name |
| Ferum Tool Exception | 8/12 | `tool:Link→Ferum Tool [R]`; `service_project:Link→Ferum Service Project [R]`; `exception_type:Select [R]`; `opened_at:Datetime [R,D=Now]`; `status:Select [R,RO,D=Open]`; `approved_by:Link→User [RO]`; `closed_at:Datetime [RO]`; `resolution:Small Text` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_tool_exception/ferum_tool_exception.json#name |
| Ferum Tool Movement | 12/18 | `tool:Link→Ferum Tool [R]`; `movement_type:Select [R]`; `movement_datetime:Datetime [R,D=Now]`; `status:Select [R,D=Done]`; `from_holder_type:Select`; `from_holder:Dynamic Link→from_holder_type`; `to_holder_type:Select`; `to_holder:Dynamic Link→to_holder_type`; `service_project:Link→Ferum Service Project`; `project_object:Link→Ferum Project Object`; `reason:Small Text`; `document:Attach` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_tool_movement/ferum_tool_movement.json#name |
| Ferum Visit Checklist Item | 7/7 | `question:Data [R]`; `response_type:Select`; `response_value:Data`; `is_ok:Check [D=0]`; `is_required:Check [D=0]`; `comment:Data`; `photo:Link→Ferum Photo Evidence` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_visit_checklist_item/ferum_visit_checklist_item.json#name |

## Статусные поля

| DocType | Поле | Значения | Источник |
| --- | --- | --- | --- |
| Ferum Advance Allocation Assistant | status | Draft → Preview Ready → Confirmed → Applied → Rejected | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_advance_allocation_assistant/ferum_advance_allocation_assistant.json#status |
| Ferum Approval Delegation | status | Active → Revoked → Expired | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_approval_delegation/ferum_approval_delegation.json#status |
| Ferum Billing Output | upd_status |  → 1 → 2 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_billing_output/ferum_billing_output.json#upd_status |
| Ferum Billing Output | status | Draft → Generated → Issued → Signed → Superseded → Cancelled | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_billing_output/ferum_billing_output.json#status |
| Ferum Billing Output | final_artifact_status | Not Started → Pending → Ready → Failed → Obsolete | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_billing_output/ferum_billing_output.json#final_artifact_status |
| Ferum Checklist Template | status | Active → Disabled | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_checklist_template/ferum_checklist_template.json#status |
| Ferum Contract | status | Draft → OnApproval → Approved → Signing → Signed → Active → Suspended → Completed → Terminated → Closed → Cancelled → Archived | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract/ferum_contract.json#status |
| Ferum Contract Amendment | approval_status | Draft → Under Review → Approved → Applied → Rejected | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract_amendment/ferum_contract_amendment.json#approval_status |
| Ferum Contract Execution Stage | execution_status | Planned → Active → Awaiting Acceptance → Accepted → Superseded → Cancelled | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract_execution_stage/ferum_contract_execution_stage.json#execution_status |
| Ferum Contract Execution Stage | financial_status | Not Invoiced → Invoiced → Partially Paid → Paid → Overdue | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract_execution_stage/ferum_contract_execution_stage.json#financial_status |
| Ferum Contract Security | status | Draft → Required → Provided → Active → Replacement Required → Replaced → Release Due → Released → Returned → Expired → Cancelled | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract_security/ferum_contract_security.json#status |
| Ferum Contractor Settlement | status | Draft → Approved → Settled → Cancelled | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contractor_settlement/ferum_contractor_settlement.json#status |
| Ferum Customer Tax Profile | status | Active → Disabled | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_customer_tax_profile/ferum_customer_tax_profile.json#status |
| Ferum Customer Unit | status | Active → Disabled | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_customer_unit/ferum_customer_unit.json#status |
| Ferum Document Generation Job | status | Queued → Running → Done → Failed → Obsolete | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_document_generation_job/ferum_document_generation_job.json#status |
| Ferum External Object Reference | sync_status |  → Matched → Created → Updated → Skipped → Conflict | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_external_object_reference/ferum_external_object_reference.json#sync_status |
| Ferum Import Batch | status | Draft → Running → Completed → Completed With Issues → Failed → Cancelled | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_import_batch/ferum_import_batch.json#status |
| Ferum Import Issue | resolution_status | Open → Resolved → Ignored | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_import_issue/ferum_import_issue.json#resolution_status |
| Ferum Incoming Invoice | approval_status | Draft → Submitted for Approval → Approved → Rejected → Cancelled → Settled via Prepaid Balance | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_incoming_invoice/ferum_incoming_invoice.json#approval_status |
| Ferum Incoming Invoice | payment_status | Unpaid → Partially Paid → Paid → Error → Not Applicable | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_incoming_invoice/ferum_incoming_invoice.json#payment_status |
| Ferum Maintenance Schedule | status | Active → Ended | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_maintenance_schedule/ferum_maintenance_schedule.json#status |
| Ferum Maintenance Visit | review_status | Pending → Accepted → Rework | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_maintenance_visit/ferum_maintenance_visit.json#review_status |
| Ferum Maintenance Visit | status | Planned → Assigned → In Progress → Submitted for Review → Accepted → Rework → Cancelled | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_maintenance_visit/ferum_maintenance_visit.json#status |
| Ferum Material Expense | status | Draft → Approved → Cancelled | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_material_expense/ferum_material_expense.json#status |
| Ferum Notification Log | status | Queued → Sent → Failed | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_notification_log/ferum_notification_log.json#status |
| Ferum Object System | status | Active → Decommissioned | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_object_system/ferum_object_system.json#status |
| Ferum Opening Payable | status | Draft → Created → Failed | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_opening_payable/ferum_opening_payable.json#status |
| Ferum Opening Receivable | status | Draft → Created → Failed | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_opening_receivable/ferum_opening_receivable.json#status |
| Ferum Party Identity | status | Active → Disabled | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_party_identity/ferum_party_identity.json#status |
| Ferum Party Identity | duplicate_review_status | Not Reviewed → Confirmed Duplicate → Confirmed Distinct | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_party_identity/ferum_party_identity.json#duplicate_review_status |
| Ferum Photo Evidence | review_status | Pending → Accepted → Rejected | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_photo_evidence/ferum_photo_evidence.json#review_status |
| Ferum Photo Evidence | sync_status | `UNKNOWN`: options отсутствуют; JSON description ссылается на OQ-10 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_photo_evidence/ferum_photo_evidence.json#sync_status |
| Ferum Project Completion Exception | status | Requested → Approved → Rejected → Expired | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_completion_exception/ferum_project_completion_exception.json#status |
| Ferum Reconciliation Log | status | Open → Resolved | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_reconciliation_log/ferum_reconciliation_log.json#status |
| Ferum Service Object | status | Active → Disabled | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_object/ferum_service_object.json#status |
| Ferum Service Project | project_status | Launch → Execution → Suspended → Completed → Archived | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_project/ferum_service_project.json#project_status |
| Ferum Service Request | status | Open → Assigned → In Progress → Resolved → Closed → Cancelled | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_request/ferum_service_request.json#status |
| Ferum Tool | status | Available → Issued → Lost → Written Off → Repair | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_tool/ferum_tool.json#status |
| Ferum Tool Exception | status | Open → Approved → Closed → Rejected | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_tool_exception/ferum_tool_exception.json#status |
| Ferum Tool Movement | status | Done → Cancelled | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_tool_movement/ferum_tool_movement.json#status |

Ключевое расхождение с TARGET: `Ferum Contract` имеет одно смешанное поле `status` из 12 значений, а `Ferum Service Project` — отдельный `project_status` `Launch/Execution/Suspended/Completed/Archived`; пары `legal_status + execution_status` нет.

## Frappe Workflow

| Workflow | DocType | State field | States | Переходов | Источник |
| --- | --- | --- | --- | ---: | --- |
| Ferum Contract Amendment Approval | Ferum Contract Amendment | approval_status | Draft → Under Review → Approved → Applied → Rejected | 5 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/fixtures/workflow.json:L1-L161 |
| Ferum Incoming Invoice Approval | Ferum Incoming Invoice | approval_status | Draft → Submitted for Approval → Approved → Rejected → Cancelled → Settled via Prepaid Balance | 13 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/fixtures/workflow.json:L162-L443 |
| Ferum Service Request Lifecycle | Ferum Service Request | status | Open → Assigned → In Progress → Resolved → Closed → Cancelled | 13 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/fixtures/workflow.json:L444-L725 |
| Ferum Maintenance Visit Lifecycle | Ferum Maintenance Visit | status | Planned → Assigned → In Progress → Submitted for Review → Accepted → Rework → Cancelled | 17 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/fixtures/workflow.json:L726-L1075 |
| Ferum Advance Allocation Assistant Confirmation | Ferum Advance Allocation Assistant | status | Draft → Preview Ready → Confirmed → Applied → Rejected | 6 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/fixtures/workflow.json:L1076-L1250 |
| Ferum Contractor Settlement Lifecycle | Ferum Contractor Settlement | status | Draft → Approved → Settled → Cancelled | 8 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/fixtures/workflow.json:L1251-L1435 |
| Ferum Tool Exception Lifecycle | Ferum Tool Exception | status | Open → Approved → Closed → Rejected | 6 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/fixtures/workflow.json:L1436-L1594 |
| Ferum Project Completion Exception Lifecycle | Ferum Project Completion Exception | status | Requested → Approved → Rejected → Expired | 3 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/fixtures/workflow.json:L1595-L1714 |
| Ferum Contract Lifecycle | Ferum Contract | status | Draft → OnApproval → Approved → Signing → Signed → Active → Suspended → Completed → Terminated → Closed → Cancelled → Archived | 32 | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/fixtures/workflow.json:L1715-L2339 |

Workflow являются прикладными FSM конкретных DocType. Универсального версионируемого Process/Stage/Step слоя в CODE нет; readiness/start/completion проекта жёстко реализованы API-гейтами (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/api/projects.py:L265-L342`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/api/projects.py:L396-L473`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/api/projects.py:L531-L840`).

## Фактические бизнес-правила

* `Ferum Contract` валидирует направление/сторону, даты и суммы, замораживает юридические условия после выдачи номера/активации и требует изменения через Amendment (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract/ferum_contract.py:L302-L423`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract/ferum_contract.py:L459-L553`).

* Primary Project Contract Link уникален и согласует `company/customer`; исполняемый primary link нельзя удалить или деактивировать (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_contract_link/ferum_project_contract_link.py:L88-L200`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_contract_link/ferum_project_contract_link.py:L217-L312`).

* Project Object и Project Scope — append-only/effective-dated; даты ограничены договором, дубли/перекрытия запрещены, изменение замороженного состава требует Amendment (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_object/ferum_project_object.py:L54-L74`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_object/ferum_project_object.py:L123-L276`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_scope/ferum_project_scope.py:L181-L526`).

* Генератор ТО поддерживает Schedule/Scope source transition, периодичность, custom dates и Holiday List; Scope-путь идемпотентен по `contract/object_system/work_type/period_key` (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/services/maintenance_visit_generation.py:L131-L168`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/services/maintenance_visit_generation.py:L527-L638`).

* Visit и Service Request имеют отдельные FSM/гейты: evidence/checklist/review для визита; SLA, Holiday List и approval evidence для заявки (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_maintenance_visit/ferum_maintenance_visit.py:L111-L163`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_maintenance_visit/ferum_maintenance_visit.py:L442-L529`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_request/ferum_service_request.py:L312-L420`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_request/ferum_service_request.py:L450-L557`).

* Billing Output проверяет Sales Invoice и жизненный цикл; Billing Artifact версионирует/защищает файл; Billing Event — immutable append-only журнал (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_billing_output/ferum_billing_output.py:L162-L387`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_billing_artifact/ferum_billing_artifact.py:L98-L267`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_billing_event/ferum_billing_event.py:L19-L50`).

* Project Finance Summary — сервисный read-model на базе стандартных Sales/Purchase Invoice и Payment Entry плюс подтверждённых затрат; прямых GL-проводок CODE не создаёт (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/services/project_finance_summary.py:L403-L701`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/hooks.py:L359-L403`).

* Audit/Notification/Reconciliation logs и File Lock сервисно управляются и защищены от пользовательского удаления/произвольных переходов (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_audit_log/ferum_audit_log.py:L14-L47`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_notification_log/ferum_notification_log.py:L40-L95`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_file_lock/ferum_file_lock.py:L16-L66`).

## Зарегистрированные hooks и фоновые задачи

Ниже перечислена фактическая регистрация в `hooks.py`; наличие регистрации не означает, что job или event был выполнен в discovery.

### Install, migrate, fixtures и Jinja

| Hook | Регистрация | Источник |
| --- | --- | --- |
| `after_install` | `ferum_custom.install.after_install` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/hooks.py:L14-L15 |
| `before_migrate` | `ferum_custom.install.apply_ch15_unique_keys` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/hooks.py:L22-L27 |
| `fixtures` | Roles, Workspace, Workflow и прочие filtered fixtures | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/hooks.py:L30-L60 |
| `jinja.methods` | `ferum_custom.services.print_context.get_printing_context` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/hooks.py:L445-L450 |

### `doc_events`

| DocType | Events / handlers | Источник |
| --- | --- | --- |
| Company | `after_insert` numbering; `before_rename`/`after_rename` guards | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/hooks.py:L299-L314 |
| Fiscal Year | `after_insert` legal numbering | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/hooks.py:L315-L317 |
| File | `validate` privacy; `on_trash` lock guard | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/hooks.py:L318-L322 |
| Ferum Service Project | `after_insert`, `on_update`, `on_trash`: project/scope permission sync | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/hooks.py:L323-L340 |
| Employee | `after_insert`, `on_update`: Company User Permission | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/hooks.py:L341-L345 |
| Contact | `after_insert`, `on_update`: customer/contractor portal permissions | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/hooks.py:L346-L358 |
| Payment Entry | `validate` internal transfer; `on_submit/on_cancel` finance/allocation | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/hooks.py:L359-L370 |
| Ferum Incoming Invoice | `on_update` notifications | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/hooks.py:L371-L374 |
| Sales Invoice | `validate`, `before_cancel`, `on_submit`, `on_cancel` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/hooks.py:L375-L387 |
| Purchase Invoice | `validate`, `before_update_after_submit`, `on_submit`, `on_cancel` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/hooks.py:L388-L403 |
| Ferum Material Expense | `validate` project-vs-invoice | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/hooks.py:L404-L410 |
| Ferum Contractor Settlement | `validate` project-vs-invoice | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/hooks.py:L411-L415 |
| Ferum Contract | `on_update` mirrors; `on_trash` scope permissions | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/hooks.py:L416-L425 |
| Ferum Project Contract Link | `after_insert`, `on_update`, `on_trash`, `after_delete` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/hooks.py:L426-L443 |

### Scheduler

| Период | Зарегистрированные handlers | Источник |
| --- | --- | --- |
| daily (14) | legal counters; delegation expiry; company/customer/contractor User Permissions; incoming invoice notifications/reconciliation; maintenance generation/overdue; billing deadline/generation reconciliation; finance reconciliation; completion-exception expiry; contract mirrors | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/hooks.py:L452-L484 |
| hourly (4) | service request SLA; photo evidence lock; billing artifact lock; job monitoring | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/hooks.py:L485-L503 |

### Permission hooks

`permission_query_conditions` зарегистрированы для Approval Delegation, Service Project, Contract, Incoming Invoice, Service Request, Maintenance Visit, Photo Evidence, Billing Output, Contractor Settlement, Tool, Tool Movement и File (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/hooks.py:L514-L563`). `has_permission` зарегистрирован ровно для того же набора из 12 DocType; составные Service Project/Request/Visit guards сведены в `permission_composition` (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/hooks.py:L564-L590`).

### Server Script

**CODE status: ABSENT BY REPRODUCIBLE SCAN.** Поиск `rg -n -i "server script|server_script" ferum_custom ci scripts -g '!**/__pycache__/**' -g '!**/*.pyc'` по Claude app вернул 0 совпадений. Это доказывает отсутствие зарегистрированного в source tree Server Script/fixture, но не проверяет записи Server Script в произвольной внешней БД.

## Интеграция со стандартным ERPNext

| Контур | Стандартный SSOT/механизм | Кастомная роль | Доказательство |
| --- | --- | --- | --- |
| Учёт и оплаты | Sales Invoice, Purchase Invoice, Payment Entry, GL | Finance Summary, intake/allocation/read-model | `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/setup/accounting_dimensions.py:L1-L67`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/services/project_finance_summary.py:L403-L701` |
| Измерение проекта | ERPNext Accounting Dimension | Ferum Service Project | `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/setup/accounting_dimensions.py:L1-L67` |
| Праздники | Holiday List | Генерация ТО и SLA | `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/services/maintenance_visit_generation.py:L233-L242`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_request/ferum_service_request.py:L396-L420` |
| Master data | Company, Customer, Supplier, Contact, User, Currency, Item, UOM | Party Identity/Tax/Unit мосты | полная edge-таблица ниже |
| Файлы/коммуникации | File, Communication | locks, evidence, artifacts | `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/setup/custom_fields.py:L20-L94`; полная edge-таблица ниже |

В entity table выше перечислены все **208** Link/Dynamic Link/Table fields. Mermaid ниже содержит все fixed-target custom и ERPNext relations; Dynamic Link дополнительно раскрыты в таблице. Следующая таблица является полным перечнем **111** standard/dynamic edges, которые нельзя терять при чтении только custom ER.

| Source DocType | Standard или dynamic edges | Schema evidence |
| --- | --- | --- |
| Ferum Advance Allocation Assistant | `company:Link→Company [REQ]`; `customer:Link→Customer [REQ]`; `payment_entry:Link→Payment Entry [REQ]`; `confirmed_by:Link→User [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_advance_allocation_assistant/ferum_advance_allocation_assistant.json#name |
| Ferum Advance Allocation Log | `payment_entry:Link→Payment Entry [REQ]`; `invoice:Link→Sales Invoice [REQ]`; `actor:Link→User [REQ]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_advance_allocation_log/ferum_advance_allocation_log.json#name |
| Ferum Approval Delegation | `delegator:Link→User [REQ]`; `delegate:Link→User [REQ]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_approval_delegation/ferum_approval_delegation.json#name |
| Ferum Audit Log | `source_doctype:Link→DocType [REQ]`; `actor:Link→User [REQ]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_audit_log/ferum_audit_log.json#name |
| Ferum Billing Event | `related_invoice:Link→Sales Invoice [MAY]`; `actor:Link→User [REQ]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_billing_event/ferum_billing_event.json#name |
| Ferum Billing Output | `company:Link→Company [REQ]`; `sales_invoice:Link→Sales Invoice [REQ]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_billing_output/ferum_billing_output.json#name |
| Ferum Company Document Settings | `company:Link→Company [REQ]`; `default_bank_account:Link→Bank Account [MAY]`; `default_letterhead:Link→Letter Head [MAY]`; `invoice_print_format:Link→Print Format [MAY]`; `act_print_format:Link→Print Format [MAY]`; `upd_print_format:Link→Print Format [MAY]`; `invoice_factura_print_format:Link→Print Format [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_company_document_settings/ferum_company_document_settings.json#name |
| Ferum Company Tax Account | `account_head:Link→Account [REQ]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_company_tax_account/ferum_company_tax_account.json#name |
| Ferum Contract | `company:Link→Company [REQ]`; `customer:Link→Customer [MAY]`; `supplier:Link→Supplier [MAY]`; `currency:Link→Currency [REQ]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract/ferum_contract.json#name |
| Ferum Contractor Settlement | `supplier:Link→Supplier [REQ]`; `currency:Link→Currency [REQ]`; `purchase_invoice:Link→Purchase Invoice [MAY]`; `payment_entry:Link→Payment Entry [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contractor_settlement/ferum_contractor_settlement.json#name |
| Ferum Contract Amendment | `currency:Link→Currency [REQ]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract_amendment/ferum_contract_amendment.json#name |
| Ferum Contract Execution Stage | `currency:Link→Currency [REQ]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract_execution_stage/ferum_contract_execution_stage.json#name |
| Ferum Contract Financial Plan Row | `fiscal_year:Link→Fiscal Year [REQ]`; `currency:Link→Currency [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract_financial_plan_row/ferum_contract_financial_plan_row.json#name |
| Ferum Contract Security | `currency:Link→Currency [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_contract_security/ferum_contract_security.json#name |
| Ferum Customer Tax Profile | `customer:Link→Customer [REQ]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_customer_tax_profile/ferum_customer_tax_profile.json#name |
| Ferum Customer Unit | `customer:Link→Customer [REQ]`; `primary_contact:Link→Contact [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_customer_unit/ferum_customer_unit.json#name |
| Ferum Document Generation Job | `generated_file:Link→File [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_document_generation_job/ferum_document_generation_job.json#name |
| Ferum External Object Reference | `target_doctype:Link→DocType [MAY]`; `target_document:Dynamic Link→target_doctype [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_external_object_reference/ferum_external_object_reference.json#name |
| Ferum File Access Policy | `source_doctype:Link→DocType [REQ]`; `role:Link→Role [MAY]`; `user:Link→User [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_file_access_policy/ferum_file_access_policy.json#name |
| Ferum File Lock | `file:Link→File [REQ]`; `source_doctype:Link→DocType [MAY]`; `locked_by:Link→User [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_file_lock/ferum_file_lock.json#name |
| Ferum Import Batch | `company:Link→Company [REQ]`; `initiated_by:Link→User [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_import_batch/ferum_import_batch.json#name |
| Ferum Import Issue | `resolved_by:Link→User [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_import_issue/ferum_import_issue.json#name |
| Ferum Incoming Invoice | `company:Link→Company [REQ]`; `cost_center:Link→Cost Center [MAY]`; `purchase_tax_template:Link→Purchase Taxes and Charges Template [MAY]`; `supplier:Link→Supplier [MAY]`; `currency:Link→Currency [REQ]`; `purchase_invoice:Link→Purchase Invoice [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_incoming_invoice/ferum_incoming_invoice.json#name |
| Ferum Incoming Invoice Payment Allocation | `payment_entry:Link→Payment Entry [REQ]`; `currency:Link→Currency [REQ]`; `source_purchase_invoice:Link→Purchase Invoice [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_incoming_invoice_payment_allocation/ferum_incoming_invoice_payment_allocation.json#name |
| Ferum Legal Number Counter | `company:Link→Company [REQ]`; `fiscal_year:Link→Fiscal Year [REQ]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_legal_number_counter/ferum_legal_number_counter.json#name |
| Ferum Maintenance Schedule | `holiday_list:Link→Holiday List [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_maintenance_schedule/ferum_maintenance_schedule.json#name |
| Ferum Maintenance Visit | `assigned_engineer:Link→User [MAY]`; `contractor:Link→Supplier [MAY]`; `reviewed_by:Link→User [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_maintenance_visit/ferum_maintenance_visit.json#name |
| Ferum Material Expense | `item:Link→Item [MAY]`; `uom:Link→UOM [MAY]`; `supplier:Link→Supplier [MAY]`; `currency:Link→Currency [REQ]`; `purchase_invoice:Link→Purchase Invoice [MAY]`; `stock_entry:Link→Stock Entry [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_material_expense/ferum_material_expense.json#name |
| Ferum Notification Log | `source_doctype:Link→DocType [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_notification_log/ferum_notification_log.json#name |
| Ferum Opening Payable | `company:Link→Company [REQ]`; `supplier:Link→Supplier [REQ]`; `currency:Link→Currency [REQ]`; `generated_purchase_invoice:Link→Purchase Invoice [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_opening_payable/ferum_opening_payable.json#name |
| Ferum Opening Receivable | `company:Link→Company [REQ]`; `customer:Link→Customer [REQ]`; `currency:Link→Currency [MAY]`; `generated_sales_invoice:Link→Sales Invoice [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_opening_receivable/ferum_opening_receivable.json#name |
| Ferum Party Identity | `registration_country:Link→Country [MAY]`; `customer:Link→Customer [MAY]`; `supplier:Link→Supplier [MAY]`; `company:Link→Company [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_party_identity/ferum_party_identity.json#name |
| Ferum Photo Evidence | `uploaded_by:Link→User [MAY]`; `reviewed_by:Link→User [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_photo_evidence/ferum_photo_evidence.json#name |
| Ferum Project Completion Exception | `approved_by:Link→User [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_completion_exception/ferum_project_completion_exception.json#name |
| Ferum Project Finance Summary | `company:Link→Company [REQ]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_finance_summary/ferum_project_finance_summary.json#name |
| Ferum Project Object | `responsible_engineer:Link→User [MAY]`; `contractor:Link→Supplier [MAY]`; `customer_contact:Link→Contact [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_object/ferum_project_object.json#name |
| Ferum Project Scope | `holiday_list:Link→Holiday List [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_project_scope/ferum_project_scope.json#name |
| Ferum Service Object | `customer:Link→Customer [REQ]`; `main_contact:Link→Contact [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_object/ferum_service_object.json#name |
| Ferum Service Project | `company:Link→Company [REQ]`; `customer:Link→Customer [REQ]`; `project_manager:Link→User [MAY]`; `project_lead:Link→User [MAY]`; `currency:Link→Currency [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_project/ferum_service_project.json#name |
| Ferum Service Project Line | `item:Link→Item [MAY]`; `uom:Link→UOM [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_project_line/ferum_service_project_line.json#name |
| Ferum Service Request | `assigned_engineer:Link→User [MAY]`; `contractor:Link→Supplier [MAY]`; `sales_invoice:Link→Sales Invoice [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_service_request/ferum_service_request.json#name |
| Ferum Settings | `sla_holiday_list:Link→Holiday List [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_settings/ferum_settings.json#name |
| Ferum Tool | `item:Link→Item [MAY]`; `current_holder:Dynamic Link→current_holder_type [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_tool/ferum_tool.json#name |
| Ferum Tool Exception | `approved_by:Link→User [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_tool_exception/ferum_tool_exception.json#name |
| Ferum Tool Movement | `from_holder:Dynamic Link→from_holder_type [MAY]`; `to_holder:Dynamic Link→to_holder_type [MAY]` | Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/ferum_custom/doctype/ferum_tool_movement/ferum_tool_movement.json#name |

## AS-IS ER

Диаграмма объявляет 54 custom, 24 standard ERPNext/Frappe и 4 dynamic-selector nodes в многострочном Mermaid-формате. Для Link `||` означает `reqd=1`, `o|` — optional; Table направлен parent→child. Узлы `DYNAMIC_*` обозначают selector field, а не реальный DocType.

```mermaid
erDiagram
    ACCOUNT {
        string name
    }
    BANK_ACCOUNT {
        string name
    }
    COMPANY {
        string name
    }
    CONTACT {
        string name
    }
    COST_CENTER {
        string name
    }
    COUNTRY {
        string name
    }
    CURRENCY {
        string name
    }
    CUSTOMER {
        string name
    }
    DOCTYPE {
        string name
    }
    DYNAMIC_FERUM_EXTERNAL_OBJECT_REFERENCE_TARGET_DOCUMENT {
        string selector
    }
    DYNAMIC_FERUM_TOOL_CURRENT_HOLDER {
        string selector
    }
    DYNAMIC_FERUM_TOOL_MOVEMENT_FROM_HOLDER {
        string selector
    }
    DYNAMIC_FERUM_TOOL_MOVEMENT_TO_HOLDER {
        string selector
    }
    FERUM_ADVANCE_ALLOCATION_ASSISTANT {
        string name
    }
    FERUM_ADVANCE_ALLOCATION_LOG {
        string name
    }
    FERUM_APPROVAL_DELEGATION {
        string name
    }
    FERUM_AUDIT_LOG {
        string name
    }
    FERUM_BILLING_ARTIFACT {
        string name
    }
    FERUM_BILLING_EVENT {
        string name
    }
    FERUM_BILLING_OUTPUT {
        string name
    }
    FERUM_CHECKLIST_TEMPLATE {
        string name
    }
    FERUM_CHECKLIST_TEMPLATE_ITEM {
        string name
    }
    FERUM_COMPANY_DOCUMENT_SETTINGS {
        string name
    }
    FERUM_COMPANY_SIGNER {
        string name
    }
    FERUM_COMPANY_TAX_ACCOUNT {
        string name
    }
    FERUM_CONTRACT {
        string name
    }
    FERUM_CONTRACT_AMENDMENT {
        string name
    }
    FERUM_CONTRACT_EXECUTION_STAGE {
        string name
    }
    FERUM_CONTRACT_FINANCIAL_PLAN_ROW {
        string name
    }
    FERUM_CONTRACT_SECURITY {
        string name
    }
    FERUM_CONTRACTOR_SETTLEMENT {
        string name
    }
    FERUM_CUSTOMER_TAX_PROFILE {
        string name
    }
    FERUM_CUSTOMER_UNIT {
        string name
    }
    FERUM_DOCUMENT_GENERATION_JOB {
        string name
    }
    FERUM_EXTERNAL_OBJECT_REFERENCE {
        string name
    }
    FERUM_FILE_ACCESS_POLICY {
        string name
    }
    FERUM_FILE_LOCK {
        string name
    }
    FERUM_IMPORT_BATCH {
        string name
    }
    FERUM_IMPORT_ISSUE {
        string name
    }
    FERUM_INCOMING_INVOICE {
        string name
    }
    FERUM_INCOMING_INVOICE_PAYMENT_ALLOCATION {
        string name
    }
    FERUM_LEGAL_NUMBER_COUNTER {
        string name
    }
    FERUM_MAINTENANCE_SCHEDULE {
        string name
    }
    FERUM_MAINTENANCE_VISIT {
        string name
    }
    FERUM_MATERIAL_EXPENSE {
        string name
    }
    FERUM_NOTIFICATION_LOG {
        string name
    }
    FERUM_OBJECT_SYSTEM {
        string name
    }
    FERUM_OPENING_PAYABLE {
        string name
    }
    FERUM_OPENING_RECEIVABLE {
        string name
    }
    FERUM_PARTY_IDENTITY {
        string name
    }
    FERUM_PARTY_TAX_REGISTRATION {
        string name
    }
    FERUM_PHOTO_EVIDENCE {
        string name
    }
    FERUM_PROJECT_COMPLETION_EXCEPTION {
        string name
    }
    FERUM_PROJECT_CONTRACT_LINK {
        string name
    }
    FERUM_PROJECT_FINANCE_SUMMARY {
        string name
    }
    FERUM_PROJECT_OBJECT {
        string name
    }
    FERUM_PROJECT_SCOPE {
        string name
    }
    FERUM_RECONCILIATION_LOG {
        string name
    }
    FERUM_SERVICE_OBJECT {
        string name
    }
    FERUM_SERVICE_PROJECT {
        string name
    }
    FERUM_SERVICE_PROJECT_LINE {
        string name
    }
    FERUM_SERVICE_REQUEST {
        string name
    }
    FERUM_SETTINGS {
        string name
    }
    FERUM_TOOL {
        string name
    }
    FERUM_TOOL_EXCEPTION {
        string name
    }
    FERUM_TOOL_MOVEMENT {
        string name
    }
    FERUM_VISIT_CHECKLIST_ITEM {
        string name
    }
    FILE {
        string name
    }
    FISCAL_YEAR {
        string name
    }
    HOLIDAY_LIST {
        string name
    }
    ITEM {
        string name
    }
    LETTER_HEAD {
        string name
    }
    PAYMENT_ENTRY {
        string name
    }
    PRINT_FORMAT {
        string name
    }
    PURCHASE_INVOICE {
        string name
    }
    PURCHASE_TAXES_AND_CHARGES_TEMPLATE {
        string name
    }
    ROLE {
        string name
    }
    SALES_INVOICE {
        string name
    }
    STOCK_ENTRY {
        string name
    }
    SUPPLIER {
        string name
    }
    UOM {
        string name
    }
    USER {
        string name
    }
    COMPANY ||--o{ FERUM_ADVANCE_ALLOCATION_ASSISTANT : "company (Link)"
    CUSTOMER ||--o{ FERUM_ADVANCE_ALLOCATION_ASSISTANT : "customer (Link)"
    PAYMENT_ENTRY ||--o{ FERUM_ADVANCE_ALLOCATION_ASSISTANT : "payment_entry (Link)"
    USER o|--o{ FERUM_ADVANCE_ALLOCATION_ASSISTANT : "confirmed_by (Link)"
    FERUM_ADVANCE_ALLOCATION_ASSISTANT ||--o{ FERUM_ADVANCE_ALLOCATION_LOG : "assistant (Link)"
    PAYMENT_ENTRY ||--o{ FERUM_ADVANCE_ALLOCATION_LOG : "payment_entry (Link)"
    SALES_INVOICE ||--o{ FERUM_ADVANCE_ALLOCATION_LOG : "invoice (Link)"
    USER ||--o{ FERUM_ADVANCE_ALLOCATION_LOG : "actor (Link)"
    USER ||--o{ FERUM_APPROVAL_DELEGATION : "delegator (Link)"
    USER ||--o{ FERUM_APPROVAL_DELEGATION : "delegate (Link)"
    DOCTYPE ||--o{ FERUM_AUDIT_LOG : "source_doctype (Link)"
    USER ||--o{ FERUM_AUDIT_LOG : "actor (Link)"
    FERUM_BILLING_OUTPUT ||--o{ FERUM_BILLING_ARTIFACT : "billing_output (Link)"
    FERUM_DOCUMENT_GENERATION_JOB o|--o{ FERUM_BILLING_ARTIFACT : "generation_job (Link)"
    FERUM_BILLING_ARTIFACT o|--o{ FERUM_BILLING_ARTIFACT : "supersedes_artifact (Link)"
    FERUM_BILLING_OUTPUT ||--o{ FERUM_BILLING_EVENT : "billing_output (Link)"
    SALES_INVOICE o|--o{ FERUM_BILLING_EVENT : "related_invoice (Link)"
    FERUM_BILLING_OUTPUT o|--o{ FERUM_BILLING_EVENT : "related_output (Link)"
    USER ||--o{ FERUM_BILLING_EVENT : "actor (Link)"
    COMPANY ||--o{ FERUM_BILLING_OUTPUT : "company (Link)"
    FERUM_SERVICE_PROJECT ||--o{ FERUM_BILLING_OUTPUT : "service_project (Link)"
    SALES_INVOICE ||--o{ FERUM_BILLING_OUTPUT : "sales_invoice (Link)"
    FERUM_SERVICE_REQUEST o|--o{ FERUM_BILLING_OUTPUT : "basis_service_request (Link)"
    FERUM_BILLING_OUTPUT o|--o{ FERUM_BILLING_OUTPUT : "supersedes (Link)"
    FERUM_BILLING_OUTPUT o|--o{ FERUM_BILLING_OUTPUT : "superseded_by (Link)"
    FERUM_CHECKLIST_TEMPLATE ||--o{ FERUM_CHECKLIST_TEMPLATE_ITEM : "items (Table)"
    COMPANY ||--o{ FERUM_COMPANY_DOCUMENT_SETTINGS : "company (Link)"
    BANK_ACCOUNT o|--o{ FERUM_COMPANY_DOCUMENT_SETTINGS : "default_bank_account (Link)"
    LETTER_HEAD o|--o{ FERUM_COMPANY_DOCUMENT_SETTINGS : "default_letterhead (Link)"
    PRINT_FORMAT o|--o{ FERUM_COMPANY_DOCUMENT_SETTINGS : "invoice_print_format (Link)"
    PRINT_FORMAT o|--o{ FERUM_COMPANY_DOCUMENT_SETTINGS : "act_print_format (Link)"
    PRINT_FORMAT o|--o{ FERUM_COMPANY_DOCUMENT_SETTINGS : "upd_print_format (Link)"
    PRINT_FORMAT o|--o{ FERUM_COMPANY_DOCUMENT_SETTINGS : "invoice_factura_print_format (Link)"
    FERUM_COMPANY_DOCUMENT_SETTINGS ||--o{ FERUM_COMPANY_SIGNER : "signers (Table)"
    FERUM_COMPANY_DOCUMENT_SETTINGS ||--o{ FERUM_COMPANY_TAX_ACCOUNT : "tax_accounts (Table)"
    ACCOUNT ||--o{ FERUM_COMPANY_TAX_ACCOUNT : "account_head (Link)"
    COMPANY ||--o{ FERUM_CONTRACT : "company (Link)"
    FERUM_PARTY_IDENTITY o|--o{ FERUM_CONTRACT : "party_identity (Link)"
    CUSTOMER o|--o{ FERUM_CONTRACT : "customer (Link)"
    SUPPLIER o|--o{ FERUM_CONTRACT : "supplier (Link)"
    CURRENCY ||--o{ FERUM_CONTRACT : "currency (Link)"
    FERUM_SERVICE_PROJECT ||--o{ FERUM_CONTRACT_AMENDMENT : "service_project (Link)"
    CURRENCY ||--o{ FERUM_CONTRACT_AMENDMENT : "currency (Link)"
    FERUM_SERVICE_PROJECT ||--o{ FERUM_CONTRACT_EXECUTION_STAGE : "service_project (Link)"
    CURRENCY ||--o{ FERUM_CONTRACT_EXECUTION_STAGE : "currency (Link)"
    FERUM_CONTRACT_EXECUTION_STAGE o|--o{ FERUM_CONTRACT_EXECUTION_STAGE : "supersedes (Link)"
    FERUM_CONTRACT_EXECUTION_STAGE o|--o{ FERUM_CONTRACT_EXECUTION_STAGE : "superseded_by (Link)"
    FISCAL_YEAR ||--o{ FERUM_CONTRACT_FINANCIAL_PLAN_ROW : "fiscal_year (Link)"
    CURRENCY o|--o{ FERUM_CONTRACT_FINANCIAL_PLAN_ROW : "currency (Link)"
    FERUM_CONTRACT_AMENDMENT o|--o{ FERUM_CONTRACT_FINANCIAL_PLAN_ROW : "contract_amendment (Link)"
    FERUM_SERVICE_PROJECT ||--o{ FERUM_CONTRACT_SECURITY : "service_project (Link)"
    CURRENCY o|--o{ FERUM_CONTRACT_SECURITY : "currency (Link)"
    FERUM_CONTRACT_AMENDMENT o|--o{ FERUM_CONTRACT_SECURITY : "contract_amendment (Link)"
    SUPPLIER ||--o{ FERUM_CONTRACTOR_SETTLEMENT : "supplier (Link)"
    FERUM_SERVICE_PROJECT ||--o{ FERUM_CONTRACTOR_SETTLEMENT : "service_project (Link)"
    FERUM_PROJECT_OBJECT o|--o{ FERUM_CONTRACTOR_SETTLEMENT : "project_object (Link)"
    FERUM_PROJECT_SCOPE o|--o{ FERUM_CONTRACTOR_SETTLEMENT : "project_scope (Link)"
    CURRENCY ||--o{ FERUM_CONTRACTOR_SETTLEMENT : "currency (Link)"
    PURCHASE_INVOICE o|--o{ FERUM_CONTRACTOR_SETTLEMENT : "purchase_invoice (Link)"
    PAYMENT_ENTRY o|--o{ FERUM_CONTRACTOR_SETTLEMENT : "payment_entry (Link)"
    CUSTOMER ||--o{ FERUM_CUSTOMER_TAX_PROFILE : "customer (Link)"
    CUSTOMER ||--o{ FERUM_CUSTOMER_UNIT : "customer (Link)"
    FERUM_CUSTOMER_UNIT o|--o{ FERUM_CUSTOMER_UNIT : "parent_unit (Link)"
    CONTACT o|--o{ FERUM_CUSTOMER_UNIT : "primary_contact (Link)"
    FERUM_BILLING_OUTPUT ||--o{ FERUM_DOCUMENT_GENERATION_JOB : "billing_output (Link)"
    FERUM_DOCUMENT_GENERATION_JOB o|--o{ FERUM_DOCUMENT_GENERATION_JOB : "previous_job (Link)"
    FILE o|--o{ FERUM_DOCUMENT_GENERATION_JOB : "generated_file (Link)"
    DOCTYPE o|--o{ FERUM_EXTERNAL_OBJECT_REFERENCE : "target_doctype (Link)"
    DYNAMIC_FERUM_EXTERNAL_OBJECT_REFERENCE_TARGET_DOCUMENT o|--o{ FERUM_EXTERNAL_OBJECT_REFERENCE : "target_document (Dynamic via target_doctype)"
    FERUM_IMPORT_BATCH ||--o{ FERUM_EXTERNAL_OBJECT_REFERENCE : "import_batch (Link)"
    DOCTYPE ||--o{ FERUM_FILE_ACCESS_POLICY : "source_doctype (Link)"
    ROLE o|--o{ FERUM_FILE_ACCESS_POLICY : "role (Link)"
    USER o|--o{ FERUM_FILE_ACCESS_POLICY : "user (Link)"
    FILE ||--o{ FERUM_FILE_LOCK : "file (Link)"
    DOCTYPE o|--o{ FERUM_FILE_LOCK : "source_doctype (Link)"
    USER o|--o{ FERUM_FILE_LOCK : "locked_by (Link)"
    COMPANY ||--o{ FERUM_IMPORT_BATCH : "company (Link)"
    USER o|--o{ FERUM_IMPORT_BATCH : "initiated_by (Link)"
    FERUM_IMPORT_BATCH ||--o{ FERUM_IMPORT_ISSUE : "import_batch (Link)"
    USER o|--o{ FERUM_IMPORT_ISSUE : "resolved_by (Link)"
    COMPANY ||--o{ FERUM_INCOMING_INVOICE : "company (Link)"
    FERUM_SERVICE_PROJECT o|--o{ FERUM_INCOMING_INVOICE : "service_project (Link)"
    COST_CENTER o|--o{ FERUM_INCOMING_INVOICE : "cost_center (Link)"
    PURCHASE_TAXES_AND_CHARGES_TEMPLATE o|--o{ FERUM_INCOMING_INVOICE : "purchase_tax_template (Link)"
    SUPPLIER o|--o{ FERUM_INCOMING_INVOICE : "supplier (Link)"
    CURRENCY ||--o{ FERUM_INCOMING_INVOICE : "currency (Link)"
    PURCHASE_INVOICE o|--o{ FERUM_INCOMING_INVOICE : "purchase_invoice (Link)"
    FERUM_MATERIAL_EXPENSE o|--o{ FERUM_INCOMING_INVOICE : "material_expense (Link)"
    FERUM_INCOMING_INVOICE ||--o{ FERUM_INCOMING_INVOICE_PAYMENT_ALLOCATION : "incoming_invoice (Link)"
    PAYMENT_ENTRY ||--o{ FERUM_INCOMING_INVOICE_PAYMENT_ALLOCATION : "payment_entry (Link)"
    CURRENCY ||--o{ FERUM_INCOMING_INVOICE_PAYMENT_ALLOCATION : "currency (Link)"
    FERUM_INCOMING_INVOICE_PAYMENT_ALLOCATION o|--o{ FERUM_INCOMING_INVOICE_PAYMENT_ALLOCATION : "reverses_allocation (Link)"
    PURCHASE_INVOICE o|--o{ FERUM_INCOMING_INVOICE_PAYMENT_ALLOCATION : "source_purchase_invoice (Link)"
    COMPANY ||--o{ FERUM_LEGAL_NUMBER_COUNTER : "company (Link)"
    FISCAL_YEAR ||--o{ FERUM_LEGAL_NUMBER_COUNTER : "fiscal_year (Link)"
    FERUM_SERVICE_PROJECT ||--o{ FERUM_MAINTENANCE_SCHEDULE : "service_project (Link)"
    FERUM_PROJECT_OBJECT ||--o{ FERUM_MAINTENANCE_SCHEDULE : "project_object (Link)"
    FERUM_PROJECT_SCOPE ||--o{ FERUM_MAINTENANCE_SCHEDULE : "project_scope (Link)"
    HOLIDAY_LIST o|--o{ FERUM_MAINTENANCE_SCHEDULE : "holiday_list (Link)"
    FERUM_PROJECT_SCOPE o|--o{ FERUM_MAINTENANCE_SCHEDULE : "superseded_by_rule (Link)"
    FERUM_SERVICE_PROJECT ||--o{ FERUM_MAINTENANCE_VISIT : "service_project (Link)"
    FERUM_PROJECT_OBJECT ||--o{ FERUM_MAINTENANCE_VISIT : "project_object (Link)"
    FERUM_PROJECT_SCOPE ||--o{ FERUM_MAINTENANCE_VISIT : "project_scope (Link)"
    FERUM_SERVICE_OBJECT ||--o{ FERUM_MAINTENANCE_VISIT : "service_object (Link)"
    FERUM_OBJECT_SYSTEM ||--o{ FERUM_MAINTENANCE_VISIT : "object_system (Link)"
    FERUM_CONTRACT ||--o{ FERUM_MAINTENANCE_VISIT : "contract (Link)"
    FERUM_MAINTENANCE_SCHEDULE o|--o{ FERUM_MAINTENANCE_VISIT : "schedule (Link)"
    USER o|--o{ FERUM_MAINTENANCE_VISIT : "assigned_engineer (Link)"
    SUPPLIER o|--o{ FERUM_MAINTENANCE_VISIT : "contractor (Link)"
    FERUM_MAINTENANCE_VISIT ||--o{ FERUM_VISIT_CHECKLIST_ITEM : "checklist (Table)"
    USER o|--o{ FERUM_MAINTENANCE_VISIT : "reviewed_by (Link)"
    FERUM_SERVICE_PROJECT ||--o{ FERUM_MATERIAL_EXPENSE : "service_project (Link)"
    FERUM_PROJECT_OBJECT o|--o{ FERUM_MATERIAL_EXPENSE : "project_object (Link)"
    FERUM_SERVICE_REQUEST o|--o{ FERUM_MATERIAL_EXPENSE : "service_request (Link)"
    FERUM_MAINTENANCE_VISIT o|--o{ FERUM_MATERIAL_EXPENSE : "maintenance_visit (Link)"
    ITEM o|--o{ FERUM_MATERIAL_EXPENSE : "item (Link)"
    UOM o|--o{ FERUM_MATERIAL_EXPENSE : "uom (Link)"
    SUPPLIER o|--o{ FERUM_MATERIAL_EXPENSE : "supplier (Link)"
    CURRENCY ||--o{ FERUM_MATERIAL_EXPENSE : "currency (Link)"
    PURCHASE_INVOICE o|--o{ FERUM_MATERIAL_EXPENSE : "purchase_invoice (Link)"
    STOCK_ENTRY o|--o{ FERUM_MATERIAL_EXPENSE : "stock_entry (Link)"
    DOCTYPE o|--o{ FERUM_NOTIFICATION_LOG : "source_doctype (Link)"
    FERUM_SERVICE_OBJECT ||--o{ FERUM_OBJECT_SYSTEM : "service_object (Link)"
    COMPANY ||--o{ FERUM_OPENING_PAYABLE : "company (Link)"
    SUPPLIER ||--o{ FERUM_OPENING_PAYABLE : "supplier (Link)"
    FERUM_PARTY_IDENTITY o|--o{ FERUM_OPENING_PAYABLE : "party_identity (Link)"
    FERUM_CONTRACT o|--o{ FERUM_OPENING_PAYABLE : "contract (Link)"
    FERUM_SERVICE_PROJECT o|--o{ FERUM_OPENING_PAYABLE : "service_project (Link)"
    CURRENCY ||--o{ FERUM_OPENING_PAYABLE : "currency (Link)"
    PURCHASE_INVOICE o|--o{ FERUM_OPENING_PAYABLE : "generated_purchase_invoice (Link)"
    COMPANY ||--o{ FERUM_OPENING_RECEIVABLE : "company (Link)"
    CUSTOMER ||--o{ FERUM_OPENING_RECEIVABLE : "customer (Link)"
    FERUM_CUSTOMER_TAX_PROFILE o|--o{ FERUM_OPENING_RECEIVABLE : "customer_tax_profile (Link)"
    FERUM_SERVICE_PROJECT o|--o{ FERUM_OPENING_RECEIVABLE : "service_project (Link)"
    CURRENCY o|--o{ FERUM_OPENING_RECEIVABLE : "currency (Link)"
    SALES_INVOICE o|--o{ FERUM_OPENING_RECEIVABLE : "generated_sales_invoice (Link)"
    COUNTRY o|--o{ FERUM_PARTY_IDENTITY : "registration_country (Link)"
    CUSTOMER o|--o{ FERUM_PARTY_IDENTITY : "customer (Link)"
    SUPPLIER o|--o{ FERUM_PARTY_IDENTITY : "supplier (Link)"
    COMPANY o|--o{ FERUM_PARTY_IDENTITY : "company (Link)"
    FERUM_PARTY_IDENTITY o|--o{ FERUM_PARTY_IDENTITY : "head_party (Link)"
    FERUM_PARTY_IDENTITY ||--o{ FERUM_PARTY_TAX_REGISTRATION : "tax_registrations (Table)"
    FERUM_PARTY_IDENTITY o|--o{ FERUM_PARTY_IDENTITY : "possible_duplicate_of (Link)"
    FERUM_MAINTENANCE_VISIT o|--o{ FERUM_PHOTO_EVIDENCE : "maintenance_visit (Link)"
    FERUM_SERVICE_REQUEST o|--o{ FERUM_PHOTO_EVIDENCE : "service_request (Link)"
    USER o|--o{ FERUM_PHOTO_EVIDENCE : "uploaded_by (Link)"
    USER o|--o{ FERUM_PHOTO_EVIDENCE : "reviewed_by (Link)"
    FERUM_SERVICE_PROJECT ||--o{ FERUM_PROJECT_COMPLETION_EXCEPTION : "service_project (Link)"
    USER o|--o{ FERUM_PROJECT_COMPLETION_EXCEPTION : "approved_by (Link)"
    FERUM_SERVICE_PROJECT ||--o{ FERUM_PROJECT_CONTRACT_LINK : "service_project (Link)"
    FERUM_CONTRACT ||--o{ FERUM_PROJECT_CONTRACT_LINK : "contract (Link)"
    COMPANY ||--o{ FERUM_PROJECT_FINANCE_SUMMARY : "company (Link)"
    FERUM_SERVICE_PROJECT ||--o{ FERUM_PROJECT_FINANCE_SUMMARY : "service_project (Link)"
    FERUM_CONTRACT ||--o{ FERUM_PROJECT_OBJECT : "contract (Link)"
    FERUM_SERVICE_PROJECT o|--o{ FERUM_PROJECT_OBJECT : "service_project (Link)"
    FERUM_SERVICE_OBJECT ||--o{ FERUM_PROJECT_OBJECT : "service_object (Link)"
    FERUM_CUSTOMER_UNIT o|--o{ FERUM_PROJECT_OBJECT : "customer_unit (Link)"
    FERUM_CONTRACT_AMENDMENT o|--o{ FERUM_PROJECT_OBJECT : "added_by (Link)"
    FERUM_CONTRACT_AMENDMENT o|--o{ FERUM_PROJECT_OBJECT : "removed_by (Link)"
    USER o|--o{ FERUM_PROJECT_OBJECT : "responsible_engineer (Link)"
    SUPPLIER o|--o{ FERUM_PROJECT_OBJECT : "contractor (Link)"
    CONTACT o|--o{ FERUM_PROJECT_OBJECT : "customer_contact (Link)"
    FERUM_CONTRACT ||--o{ FERUM_PROJECT_SCOPE : "contract (Link)"
    FERUM_PROJECT_OBJECT ||--o{ FERUM_PROJECT_SCOPE : "contract_object (Link)"
    FERUM_SERVICE_PROJECT o|--o{ FERUM_PROJECT_SCOPE : "service_project (Link)"
    FERUM_OBJECT_SYSTEM ||--o{ FERUM_PROJECT_SCOPE : "object_system (Link)"
    FERUM_CHECKLIST_TEMPLATE o|--o{ FERUM_PROJECT_SCOPE : "checklist_template (Link)"
    FERUM_CONTRACT_AMENDMENT o|--o{ FERUM_PROJECT_SCOPE : "added_by (Link)"
    FERUM_CONTRACT_AMENDMENT o|--o{ FERUM_PROJECT_SCOPE : "removed_by (Link)"
    HOLIDAY_LIST o|--o{ FERUM_PROJECT_SCOPE : "holiday_list (Link)"
    CUSTOMER ||--o{ FERUM_SERVICE_OBJECT : "customer (Link)"
    FERUM_CUSTOMER_UNIT o|--o{ FERUM_SERVICE_OBJECT : "customer_unit (Link)"
    CONTACT o|--o{ FERUM_SERVICE_OBJECT : "main_contact (Link)"
    COMPANY ||--o{ FERUM_SERVICE_PROJECT : "company (Link)"
    CUSTOMER ||--o{ FERUM_SERVICE_PROJECT : "customer (Link)"
    FERUM_CUSTOMER_TAX_PROFILE o|--o{ FERUM_SERVICE_PROJECT : "customer_tax_profile (Link)"
    FERUM_CUSTOMER_UNIT o|--o{ FERUM_SERVICE_PROJECT : "primary_customer_unit (Link)"
    USER o|--o{ FERUM_SERVICE_PROJECT : "project_manager (Link)"
    USER o|--o{ FERUM_SERVICE_PROJECT : "project_lead (Link)"
    CURRENCY o|--o{ FERUM_SERVICE_PROJECT : "currency (Link)"
    FERUM_SERVICE_PROJECT ||--o{ FERUM_CONTRACT_FINANCIAL_PLAN_ROW : "financial_plan (Table)"
    FERUM_SERVICE_PROJECT ||--o{ FERUM_SERVICE_PROJECT_LINE : "service_project (Link)"
    ITEM o|--o{ FERUM_SERVICE_PROJECT_LINE : "item (Link)"
    UOM o|--o{ FERUM_SERVICE_PROJECT_LINE : "uom (Link)"
    FERUM_PROJECT_OBJECT o|--o{ FERUM_SERVICE_PROJECT_LINE : "project_object (Link)"
    FERUM_PROJECT_SCOPE o|--o{ FERUM_SERVICE_PROJECT_LINE : "project_scope (Link)"
    FERUM_SERVICE_PROJECT ||--o{ FERUM_SERVICE_REQUEST : "service_project (Link)"
    FERUM_PROJECT_OBJECT o|--o{ FERUM_SERVICE_REQUEST : "project_object (Link)"
    FERUM_PROJECT_SCOPE o|--o{ FERUM_SERVICE_REQUEST : "project_scope (Link)"
    FERUM_OBJECT_SYSTEM o|--o{ FERUM_SERVICE_REQUEST : "object_system (Link)"
    FERUM_SERVICE_OBJECT o|--o{ FERUM_SERVICE_REQUEST : "service_object (Link)"
    USER o|--o{ FERUM_SERVICE_REQUEST : "assigned_engineer (Link)"
    SUPPLIER o|--o{ FERUM_SERVICE_REQUEST : "contractor (Link)"
    FERUM_MAINTENANCE_VISIT o|--o{ FERUM_SERVICE_REQUEST : "maintenance_visit (Link)"
    SALES_INVOICE o|--o{ FERUM_SERVICE_REQUEST : "sales_invoice (Link)"
    HOLIDAY_LIST o|--o{ FERUM_SETTINGS : "sla_holiday_list (Link)"
    ITEM o|--o{ FERUM_TOOL : "item (Link)"
    DYNAMIC_FERUM_TOOL_CURRENT_HOLDER o|--o{ FERUM_TOOL : "current_holder (Dynamic via current_holder_type)"
    FERUM_SERVICE_PROJECT o|--o{ FERUM_TOOL : "current_project (Link)"
    FERUM_TOOL ||--o{ FERUM_TOOL_EXCEPTION : "tool (Link)"
    FERUM_SERVICE_PROJECT ||--o{ FERUM_TOOL_EXCEPTION : "service_project (Link)"
    USER o|--o{ FERUM_TOOL_EXCEPTION : "approved_by (Link)"
    FERUM_TOOL ||--o{ FERUM_TOOL_MOVEMENT : "tool (Link)"
    DYNAMIC_FERUM_TOOL_MOVEMENT_FROM_HOLDER o|--o{ FERUM_TOOL_MOVEMENT : "from_holder (Dynamic via from_holder_type)"
    DYNAMIC_FERUM_TOOL_MOVEMENT_TO_HOLDER o|--o{ FERUM_TOOL_MOVEMENT : "to_holder (Dynamic via to_holder_type)"
    FERUM_SERVICE_PROJECT o|--o{ FERUM_TOOL_MOVEMENT : "service_project (Link)"
    FERUM_PROJECT_OBJECT o|--o{ FERUM_TOOL_MOVEMENT : "project_object (Link)"
    FERUM_PHOTO_EVIDENCE o|--o{ FERUM_VISIT_CHECKLIST_ITEM : "photo (Link)"
```

## Тестовое покрытие

В entity table столбец `Локальные test-файлы` отражает только co-located `test*.py` внутри каталога DocType. Он не равен общему coverage. Таблица ниже связывает каждый предметный набор DocType с обнаруженными central suites. Это **static mapping / PRESENT / NOT RUN**, а не доказательство прохождения каждой ветки.

| Область | DocType / поведение | Static candidate suites | Статус discovery |
| --- | --- | --- | --- |
| 1. Договор | Ferum Service Project; Ferum Contract; Ferum Project Contract Link; Ferum Contract Amendment; Ferum Contract Execution Stage; Ferum Contract Security; Ferum Contract Financial Plan Row | `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_contract_numbering_and_lifecycle.py:L1-L40`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_contract_mirrors.py:L193-L231`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_workflows.py:L1-L40` | PRESENT / NOT RUN |
| 2. Объекты/scope | Ferum Service Object; Ferum Project Object; Ferum Object System; Ferum Project Scope; Ferum External Object Reference | `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_scope_rule_isolation.py:L1-L40`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_scope_rule_migration.py:L1-L40`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_import_masking.py:L1-L40` | PRESENT / NOT RUN |
| 3. План | Ferum Maintenance Schedule; Ferum Service Project Line | `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_maintenance_visit_generation.py:L67-L120`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_data_model.py:L1-L40` | PRESENT / NOT RUN |
| 4. Факт | Ferum Maintenance Visit; Ferum Service Request; Ferum Visit Checklist Item; Ferum Checklist Template; Ferum Checklist Template Item; Ferum Photo Evidence | `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_maintenance_visit_generation.py:L67-L120`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_service_request_sla.py:L1-L40`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_photo_evidence_lock.py:L1-L40` | PRESENT / NOT RUN |
| 5. Документы | Ferum Document Generation Job; Ferum Billing Output; Ferum Billing Artifact; Ferum Billing Event; Ferum Company Document Settings; Ferum Company Signer; Ferum Legal Number Counter | `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_billing.py:L214-L260`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_print_and_numbering.py:L1-L40`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_job_monitoring.py:L1-L40` | PRESENT / NOT RUN |
| 6. Финансы | Ferum Project Finance Summary; Ferum Incoming Invoice; Ferum Incoming Invoice Payment Allocation; Ferum Advance Allocation Assistant; Ferum Advance Allocation Log; Ferum Opening Receivable; Ferum Opening Payable; Ferum Material Expense; Ferum Contractor Settlement; Ferum Reconciliation Log | `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_finance.py:L377-L430`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_advance_allocation.py:L1-L40`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_opening_receivable.py:L1-L50`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_opening_payable.py:L1-L40`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_material_expense.py:L1-L40`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_contractor_settlement.py:L1-L40` | PRESENT / NOT RUN |
| 7. Подрядчики/tools | Ferum Contractor Settlement; Ferum Tool; Ferum Tool Movement; Ferum Tool Exception | `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_contractor_settlement.py:L1-L40`; `Вспомательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_tools.py:L1-L40`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_permissions.py:L2917-L2950` | PRESENT / NOT RUN |
| 8. Fixed process | readiness/start/completion APIs; nine Workflow fixtures | `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_projects_api.py:L1-L40`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_workflow_state_fixtures.py:L1-L40`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_workflows.py:L1-L40` | PRESENT / NOT RUN; generic BPM absent as named layer |
| 9. Party/tax | Ferum Customer Unit; Ferum Customer Tax Profile; Ferum Party Identity; Ferum Party Tax Registration; Ferum Company Tax Account | `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_data_model.py:L1-L40`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_print_and_numbering.py:L1-L40` | PARTIAL STATIC MAPPING / NOT RUN |
| 10. Служебный | Ferum Audit Log; Ferum Notification Log; Ferum File Access Policy; Ferum File Lock; Ferum Approval Delegation; Ferum Settings; Ferum Import Batch; Ferum Import Issue; Ferum Project Completion Exception | `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_file_security.py:L1-L40`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_delegation_expiry_service.py:L1-L40`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_import_masking.py:L1-L40`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_workflows.py:L1-L40` | PRESENT / NOT RUN |
| 11. Governance/security | roles, permissions, static policy boundaries | `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_static_validators.py:L1-L40`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_roles_fixtures.py:L1-L40`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_system_manager_no_bypass.py:L1-L40` | PRESENT / NOT RUN |
| 12. Spec/trace | data model/API contract/static trace assertions | `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_api_contracts.py:L1-L40`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_data_model.py:L1-L40` | PRESENT / NOT RUN; registry planned status отдельно |
| 13. E2E/status | cross-domain scenario/rehearsal | `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_e2e_scenario.py:L1-L50`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/e9_rehearsal_checks.py:L1-L50` | PRESENT / NOT RUN |

Наиболее крупные suites статически покрывают Contract mirrors, Maintenance generator, billing и finance (`Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_contract_mirrors.py:L193-L781`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_maintenance_visit_generation.py:L67-L800`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_billing.py:L214-L1230`; `Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom/tests/test_finance.py:L377-L1012`). В рамках discovery тесты не запускались.

## Отсутствующие целевые узлы

Отрицательный вывод основан не на SPEC, а на exhaustive 54-schema inventory выше и воспроизводимом CODE-only scan. Выполненный шаблон:

```powershell
$patterns = @(
  'Ferum Contract Obligation', 'Ferum Finding', 'Ferum Defect',
  'Ferum Project Document', 'Ferum Contractor Assignment',
  'Ferum Contract Requirement', 'Ferum Process Template',
  'Ferum Stage Template', 'Ferum Step Template', 'Ferum Project Process',
  'Ferum Project Stage', 'Ferum Project Process Step', 'Ferum Stage Gate',
  'Ferum Process Evidence', 'Ferum Inspection'
)
foreach ($pattern in $patterns) {
  rg -n -F --glob '*.json' --glob '*.py' --glob '!tests/**' $pattern `
    'Вспомогательные/Claude ferum_custom/apps/ferum_custom/ferum_custom'
}
```

Каждый из 15 exact-name patterns вернул **0** совпадений. Это доказывает отсутствие названных target nodes в JSON/Python CODE snapshot; это не доказывает отсутствие любого частичного поведения с другим именем.

| TARGET node | CODE verdict | Первичное/воспроизводимое evidence |
| --- | --- | --- |
| Ferum Contract Obligation | Absent as named node | 54-schema table + exact-name scan = 0 |
| Ferum Finding / Ferum Defect | Absent as named nodes | exact-name scans = 0; `Defect` остаётся значением Select в Request/Photo |
| Ferum Project Document | Absent as named node | exact-name scan = 0; billing entities не являются generic document register |
| Ferum Contractor Assignment | Absent as named node | exact-name scan = 0; Supplier links в Visit/Request — surrogate |
| Ferum Contract Requirement | Absent as named node | exact-name scan = 0 |
| Ferum Process Template / Stage Template / Step Template | Absent as named nodes | три exact-name scan = 0 |
| Ferum Project Process / Project Stage / Project Process Step | Absent as named nodes | три exact-name scan = 0 |
| Ferum Stage Gate | Absent as named node | exact-name scan = 0; fixed API gates существуют отдельно |
| Ferum Process Evidence | Absent as named node | exact-name scan = 0 |
| Ferum Inspection | Absent as named node | exact-name scan = 0 |
| Generic Deadline/Event Engine | `UNKNOWN` как обобщённая capability; отсутствует как named DocType | exact node list не содержит такого DocType; отдельные SLA/scheduler/event rules существуют и перечислены выше |
