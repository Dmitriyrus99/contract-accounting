# CA-09 / FR-04 traceability addendum — v0.19.0

Эти строки являются current overrides только для указанной delivery delta. Они не изменяют immutable TARGET/SPEC и не закрывают ручные release gates.

| Requirement | Current evidence |
|---|---|
| `TCA-A-14-01` | CURRENT OVERRIDE — PARTIAL / DELIVERY CODE PASS: единый source timeline теперь имеет DP-06 scheduler, deterministic threshold/correlation identity, permission-filtered in-app/Email Queue, timezone-aware digest, retry/dead-letter и terminal-source exclusion; общий warranty source, production activation, external SMTP receipt, performance и UAT остаются OPEN. |
| `TCA-B-33-11` | CURRENT OVERRIDE — PARTIAL / DELIVERY CODE PASS: generated Process Step due_at участвует в едином scheduler/delivery контуре; отдельное событие уведомления непосредственно в Generate Process, configured catalog и Operations UAT остаются OPEN. |
