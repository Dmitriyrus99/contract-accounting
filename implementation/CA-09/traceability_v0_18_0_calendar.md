# Traceability addendum — production calendar and missing deadline sources v0.18.0

Маркер `CURRENT OVERRIDE` задаёт только текущее implementation evidence. Исторические оценки v0.10.0 остаются неизменными.

| Requirement | Current evidence |
|---|---|
| `TCA-A-14-09` | CURRENT OVERRIDE — IMPLEMENTED/PASS; Project Document хранит typed `signature_due_at` и ссылку на append-only calculation; Company/Contract precedence, direct-mutation guard, idempotency и manual recalculation подтверждены Bench |
| `TCA-A-14-13` | CURRENT OVERRIDE — IMPLEMENTED/PASS; отдельный `Ferum External Dependency` хранит Customer/contact, sent item/channel/time/File evidence, expected result, owner, due/calendar snapshot/status; customer-response timeline подтверждён Bench |

`MG-CA-013` закрыт для configuration/code boundary: source-controlled `RU-5D-2026-v1`, `Europe/Moscow`, `08:00–19:00`, exact `247/118/4`, calendar hash `56691dc76841c9ef33550cec0539c82010f1e1277055c5f2ffdfec029744d917`, Contract→Company precedence и immutable calculation history проверены. Site-specific Company assignment, будущие годовые revisions и Operations UAT остаются эксплуатационными gates.

FR-04 scheduler/delivery, полный FR-08 External Dependency lifecycle, representative-volume performance, browser/RBAC UAT и production deployment этим addendum не закрываются.
