# CA-15 browser/permission traceability addendum — v0.16.1

Этот addendum уточняет только доказательства manager/director browser slice и не изменяет 51 normative req-id в `07_traceability.csv`.

| Requirement group | v0.16.1 evidence | Вердикт |
| --- | --- | --- |
| `TCA-A-19-03…11` | Director получает read/report-only доступ к 18 operational source/context DocType; System/Object/Request exact records подтверждены API runtime и браузером | PARTIAL PASS для director fixture; полный edge/role portfolio OPEN |
| `TCA-A-19-17…23` | Director trace видит deadline/audit/finance dimensions; manager finance redaction сохранена | PARTIAL PASS; остальные роли, communications и representative volume OPEN |
| `TCA-A-20-03…11` | Manager и Director получают одинаковые разрешённые operational source rows; директор дополнительно видит margin summary; exact drill-down System и Request проверен | PARTIAL browser/runtime PASS; complete business pilot OPEN |
| `TCA-A-20-12` | Contract 360° открыт manager/director; директорский false-zero defect воспроизведён и устранён без permission bypass | PASS для двух ролей; lawyer/accountant/other role UAT OPEN |
| `TCA-A-20-13` | Operations открыт manager и прямой URL отклонён для director | PASS для manager/director boundary; engineer/contractor/accountant UAT OPEN |
| `TCA-A-20-14` | Director Control открыт director и прямой URL отклонён для manager | PASS для manager/director boundary; RP и representative exceptions UAT OPEN |
| `TCA-B-36-13…14` | Director margin source видим; manager payment/margin остаются `restricted` | PARTIAL PASS; accounting reconciliation/export/report sign-off OPEN |

Evidence: [browser_uat_v0_16_1_2026-08-18.md](browser_uat_v0_16_1_2026-08-18.md). Полная исходная карта CA-15 остаётся в [traceability_v0_16_0.md](traceability_v0_16_0.md).
