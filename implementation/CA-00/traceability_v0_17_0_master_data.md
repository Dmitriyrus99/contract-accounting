# Traceability addendum — ERPNext master-data boundary v0.17.0

Маркер `CURRENT OVERRIDE` означает, что строка задаёт текущее состояние требования и заменяет только более раннюю implementation-status оценку; исторические evidence-файлы остаются неизменными.

| Requirement | Current evidence |
|---|---|
| `TCA-A-17-04` | CURRENT OVERRIDE — IMPLEMENTED/PASS; Service Object.address является Link на standard Address, same-Customer Dynamic Link проверен positive/negative Bench acceptance; supersedes v0.16.3 evidence |
| `TCA-A-17-10` | CURRENT OVERRIDE — IMPLEMENTED/PASS; Material Expense использует standard Warehouse Link, non-group/same-Company guards проверены Bench acceptance; supersedes v0.16.3 evidence |
| `TCA-A-17-18` | CURRENT OVERRIDE — IMPLEMENTED/PASS; standard Project отклонён как contract root после semantic-match review, прямой schema Link и custom Ferum Project отсутствуют; supersedes v0.16.3 evidence |
| `TCA-A-17-19` | CURRENT OVERRIDE — IMPLEMENTED/PASS; standard Task отклонён как process-step SSOT, standard ToDo остаётся delivery projection, custom Ferum Task отсутствует; supersedes v0.16.3 evidence |
| `TCA-A-17-20` | CURRENT OVERRIDE — IMPLEMENTED/PASS; standard Issue не подменяет разные typed lifecycles Service Request/Finding, custom Ferum Issue отсутствует; supersedes v0.16.3 evidence |
| `TCA-A-17-21` | CURRENT OVERRIDE — IMPLEMENTED/PASS; customer-owned Service Object отделён от company-owned standard Asset accounting, custom Ferum Asset отсутствует; supersedes v0.16.3 evidence |

`TCA-A-17-15` (Workflow) и `TCA-A-17-17` (Communication) намеренно остаются `Partial`: этот increment не предоставляет требуемого positive acceptance.
