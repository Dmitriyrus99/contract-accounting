# CA-11 physical schema and command contract — v0.12.0

**Статус:** `PARENT BPM TOPOLOGY + TYPED COMMANDS BENCH VERIFIED AT b474d74`.

## Parent DocType

| DocType | Назначение | Ключевой invariant |
| --- | --- | --- |
| `Ferum Process Template` | version root | unique `(code, version)`; Published immutable |
| `Ferum Stage Template` | ordered stage definition | unique `(process_template, stage_code)`; parent must be Draft to mutate |
| `Ferum Step Template` | action/deadline/evidence/rules | unique `(stage_template, step_code)`; dependency graph validated at publish |
| `Ferum Project Process` | frozen project instance | unique `generation_key`; typed writer only |
| `Ferum Project Stage` | stage snapshot | unique `(project_process, stage_code)`; typed writer only |
| `Ferum Project Process Step` | one-time process action SSOT | unique `instance_key`; direct mutation/delete denied |
| `Ferum Stage Gate` | persisted gate evaluation | unique `(project_stage, gate_code)`; evaluator/override only |
| `Ferum Process Evidence` | evidence provenance | unique `evidence_key`; validated/rejected provenance immutable |
| `Ferum Process Event` | append-only trace/trigger event | unique `idempotency_key`; update/delete denied |

Все девять сущностей — parent DocType. Child optimization не применялась; отдельный ADR не создавался.

## Template → instance

1. Draft template graph проверяет safe rules, stage/step presence, unknown dependencies и cycles.
2. `publish_process_template` ставит Published и замораживает root/stages/steps.
3. `generate_project_process` требует Published template, explicit generation key/reason/requirement revision и applicable scope.
4. Template/stage/step fields сериализуются в immutable JSON snapshots.
5. Повтор того же generation key и context возвращает существующий process; reuse в другом context отклоняется.
6. Первый stage становится Active, следующие Planned. Steps без dependencies первого stage становятся Ready.

`Approved One-time Requirement` policy выбирает только `Approved + Applicable + One-time Process Step` требования и применяет безопасный `requirement_match_rule`. Dedicated positive runtime fixture для этой ветки остаётся открытым.

## Deadline boundary

`None`, `Absolute` и `Relative` поддерживаются. Relative generation требует explicit trigger и immutable calendar snapshot: timezone, revision, holidays, weekends, cut-off и policy. Pure engine вычисляет due/warning/escalation и hash; в Frappe Datetime сохраняется site-local wall time, а timezone/revision остаются в calculation hash.

Без explicit inputs generation fail-closed. Автоматический Company calendar/scheduler не выбирается до MG-CA-013.

## Step FSM

Persisted base statuses:

`Planned`, `Ready`, `In Progress`, `Waiting External`, `Waiting Approval`, `Blocked`, `Completed`, `Not Applicable`, `Cancelled`.

`Overdue` отсутствует в Select options. `get_step_projection(as_of)` возвращает derived `is_overdue`, `overdue_since`, `display_status`; без `as_of` классификация отключена.

- Not Applicable требует `not_applicable_reason`;
- Waiting External, Blocked и Cancelled требуют reason;
- dependencies должны быть Completed/Not Applicable до Ready/In Progress;
- condition rule должен быть true до Ready/In Progress;
- Completed требует Validated evidence точного completion type;
- step с approver завершается только из Waiting Approval ролью approver;
- terminal transition закрывает standard ToDo.

## Evidence и Gate

Evidence types: `Document`, `File`, `Email`, `Outgoing Letter`, `Incoming Letter`, `Call Record`, `Meeting Record`, `Photo`, `Approval`, `ERP Document`, `Payment`, `Inspection`, `Manual Confirmation`. Source DocType ограничен type-specific allowlist; snapshot, actor/time и SHA-256 обязательны. `Inspection` зарезервирован для CA-12 и не создаётся без существующего primary source.

Gate `All Blocking Steps` проходит только когда каждый blocking step Completed либо evidenced Not Applicable. Stage exit JSON Logic добавляет отдельный criterion. Failed gate запрещает `complete_project_stage`. Override разрешён только RP/System Manager, с reason и Validated Process Evidence того же process.

## Integration adapters

- standard `ToDo` отражает персональную работу; Process Step остаётся SSOT;
- Process Step due dates включены в CA-09 source timeline;
- process/step/gate widgets и Blocked/Failed/Overdue exceptions включены в CA-10 read-model;
- Process Evidence только ссылается на primary documents/communications/payments и не меняет их lifecycle/ledger.
