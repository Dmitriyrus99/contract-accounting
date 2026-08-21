"""DP-06 scheduler, idempotent delivery, retry/dead-letter and daily digest."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Iterator
from zoneinfo import ZoneInfo

import frappe
from frappe.utils import cint, escape_html, get_datetime, get_system_timezone, now_datetime

from contract_accounting.api.deadlines import get_deadline_timeline
from contract_accounting.domain.notification import (
    POLICY_VERSION,
    ThresholdOccurrence,
    delivery_identity,
    threshold_occurrences,
)
from contract_accounting.infrastructure.calendar_registry import resolve_calendar
from contract_accounting.infrastructure.notification_guard import (
    NOTIFICATION_DELIVERY_WRITE_FLAG,
)

RETRY_DELAYS_MINUTES = (5, 30, 120)
PROCESS_OWNER_ROLE = "Владелец процесса"
DIRECTOR_ROLE = "Генеральный директор"


def process_deadline_notifications(now: str | datetime | None = None) -> dict[str, int]:
    """Create all due non-digest deliveries, reconcile queues and attempt work."""

    settings = _enabled_settings()
    if settings is None:
        return {"disabled": 1, "created": 0, "sent": 0, "queued": 0, "errors": 0}
    current = get_datetime(now) if now is not None else now_datetime()
    reconciled = _reconcile_email_queues(current, settings)
    occurrences, errors = _collect_occurrences(current, settings)
    created = 0
    for item in occurrences:
        channels = ["In App"]
        if item["occurrence"].email_mode == "IMMEDIATE":
            channels.append("Email")
        for recipient in item["recipients"]:
            for channel in channels:
                if _ensure_individual_delivery(item, recipient, channel):
                    created += 1
    attempted = _process_pending(current, settings)
    return {
        "disabled": 0,
        "created": created,
        "sent": attempted["sent"] + reconciled["sent"],
        "queued": attempted["queued"],
        "errors": errors + attempted["errors"] + reconciled["errors"],
    }


def process_deadline_digest(now: str | datetime | None = None) -> dict[str, int]:
    """Batch −3/50% reminders and post-escalation daily items by recipient."""

    settings = _enabled_settings()
    if settings is None:
        return {"disabled": 1, "created": 0, "sent": 0, "queued": 0, "errors": 0}
    current = get_datetime(now) if now is not None else now_datetime()
    occurrences, errors = _collect_occurrences(current, settings)
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in occurrences:
        calendar_now = _calendar_local(current, item["calendar"].timezone)
        if calendar_now.hour != 9 or calendar_now.minute >= 15:
            continue
        local_date = calendar_now.date().isoformat()
        occurrence = item["occurrence"]
        if occurrence.email_mode == "DIGEST":
            for recipient in item["recipients"]:
                grouped[(recipient, "Email Digest", local_date)].append(item)
        if occurrence.code == "OVERDUE_PLUS_1":
            daily_recipients = _recipients(item["project"], item["row"], "DAILY")
            daily_item = {**item, "daily_date": local_date}
            for recipient in daily_recipients:
                grouped[(recipient, "In App Digest", local_date)].append(daily_item)
                grouped[(recipient, "Email Digest", local_date)].append(daily_item)
    created = 0
    for (recipient, channel, local_date), items in grouped.items():
        if _ensure_digest_delivery(recipient, channel, items, current, local_date):
            created += 1
    attempted = _process_pending(current, settings)
    return {
        "disabled": 0,
        "created": created,
        "sent": attempted["sent"],
        "queued": attempted["queued"],
        "errors": errors + attempted["errors"],
    }


def _collect_occurrences(current: datetime, settings: Any) -> tuple[list[dict[str, Any]], int]:
    result: list[dict[str, Any]] = []
    errors = 0
    projects = frappe.get_all(
        "Ferum Service Project",
        filters={"is_archived": 0},
        fields=["name", "project_manager"],
        order_by="name asc",
    )
    for project in projects:
        try:
            timeline = get_deadline_timeline(project.name, as_of=current, include_closed=0)
        except Exception as exc:
            errors += 1
            _log_source_error(project.name, None, exc)
            continue
        for row in timeline["rows"]:
            try:
                due_at = get_datetime(row["due_at"])
                resolved = resolve_calendar(project.name, row["due_at"])
                calendar = resolved.calendar
                due_site = _site_naive(due_at.replace(tzinfo=ZoneInfo(calendar.timezone)))
                if due_site > current + timedelta(days=14):
                    continue
                triggered_at = (
                    get_datetime(row["triggered_at"]) if row.get("triggered_at") else None
                )
                for occurrence in threshold_occurrences(
                    due_at=due_at,
                    triggered_at=triggered_at,
                    calendar=calendar,
                ):
                    threshold_at = _site_naive(occurrence.occurs_at)
                    if threshold_at > current or threshold_at < get_datetime(settings.activated_at):
                        continue
                    recipients = _recipients(project, row, occurrence.audience)
                    result.append(
                        {
                            "project": project,
                            "row": row,
                            "occurrence": occurrence,
                            "threshold_at": threshold_at,
                            "recipients": recipients,
                            "calendar": calendar,
                        }
                    )
            except Exception as exc:
                errors += 1
                _log_source_error(project.name, row.get("source_key"), exc)
    return result, errors


def _log_source_error(project: str, source_key: str | None, exc: Exception) -> None:
    frappe.log_error(
        title="Contract Accounting notification source rejected",
        message=(
            f"Project {project}; source {source_key or 'timeline'}: fail-closed evaluation; "
            f"{exc.__class__.__name__}: {str(exc)[:300]}"
        ),
    )


def _recipients(project: Any, row: dict[str, Any], audience: str) -> list[str]:
    candidates: set[str] = set()
    if audience in {"RESPONSIBLE_PM", "RESPONSIBLE_PM_PROCESS", "DAILY"}:
        if row.get("owner"):
            candidates.add(row["owner"])
        if project.project_manager:
            candidates.add(project.project_manager)
        if row.get("owner_role"):
            candidates.update(_users_for_role(row["owner_role"]))
    if audience in {"RESPONSIBLE_PM_PROCESS", "DAILY"}:
        candidates.update(_users_for_role(PROCESS_OWNER_ROLE))
    if audience in {"DIRECTOR", "DAILY"}:
        candidates.update(_users_for_role(DIRECTOR_ROLE))
    recipients = []
    for user in sorted(candidates):
        if not frappe.db.get_value("User", user, "enabled"):
            continue
        if not frappe.has_permission("Ferum Service Project", "read", doc=project.name, user=user):
            continue
        if not frappe.has_permission(
            row["source_doctype"], "read", doc=row["source_name"], user=user
        ):
            continue
        recipients.append(user)
    return recipients


def _users_for_role(role: str) -> set[str]:
    return set(
        frappe.get_all(
            "Has Role",
            filters={"parenttype": "User", "role": role},
            pluck="parent",
        )
    )


def _ensure_individual_delivery(item: dict[str, Any], recipient: str, channel: str) -> bool:
    row = item["row"]
    occurrence: ThresholdOccurrence = item["occurrence"]
    due_at = get_datetime(row["due_at"])
    correlation_key, delivery_key = delivery_identity(
        source_key=row["source_key"],
        due_at=due_at,
        threshold=occurrence.code,
        recipient=recipient,
        channel=channel,
    )
    payload = _individual_payload(item, recipient)
    values = {
        "delivery_key": delivery_key,
        "correlation_key": correlation_key,
        "service_project": item["project"].name,
        "source_doctype": row["source_doctype"],
        "source_name": row["source_name"],
        "source_field": row["source_field"],
        "source_key": row["source_key"],
        "due_at": due_at,
        "threshold": occurrence.code,
        "threshold_at": item["threshold_at"],
        "recipient": recipient,
        "channel": channel,
        **_canonical_payload(payload),
    }
    return _insert_delivery(values)


def _ensure_digest_delivery(
    recipient: str,
    channel: str,
    items: list[dict[str, Any]],
    current: datetime,
    local_date: str,
) -> bool:
    digest_items = []
    for item in items:
        row = item["row"]
        occurrence: ThresholdOccurrence = item["occurrence"]
        threshold = "DAILY_DIGEST" if item.get("daily_date") else occurrence.code
        occurrence_date = item.get("daily_date")
        correlation_key, item_key = delivery_identity(
            source_key=row["source_key"],
            due_at=get_datetime(row["due_at"]),
            threshold=threshold,
            recipient=recipient,
            channel=channel,
            occurrence_date=occurrence_date,
        )
        if frappe.db.exists("Ferum Notification Digest Item", {"item_key": item_key}):
            continue
        digest_items.append(
            {
                "item_key": item_key,
                "correlation_key": correlation_key,
                "service_project": item["project"].name,
                "source_doctype": row["source_doctype"],
                "source_name": row["source_name"],
                "source_field": row["source_field"],
                "threshold": threshold,
                "due_at": get_datetime(row["due_at"]),
                "kind": row["kind"],
            }
        )
    if not digest_items:
        return False
    digest_items.sort(key=lambda value: (str(value["due_at"]), value["item_key"]))
    aggregate_key = hashlib.sha256(
        "|".join(item["item_key"] for item in digest_items).encode("utf-8")
    ).hexdigest()
    correlation_key, delivery_key = delivery_identity(
        source_key=f"digest:{aggregate_key}",
        due_at=current,
        threshold="DIGEST",
        recipient=recipient,
        channel=channel,
        occurrence_date=local_date,
    )
    payload = {
        "title": f"Сводка контрольных сроков: {len(digest_items)}",
        "description": "<br>".join(
            f"{escape_html(item['kind'])}: {escape_html(str(item['due_at']))}"
            for item in digest_items
        ),
        "recipient": recipient,
        "item_count": len(digest_items),
        "item_keys": [item["item_key"] for item in digest_items],
        "policy_version": POLICY_VERSION,
    }
    values = {
        "delivery_key": delivery_key,
        "correlation_key": correlation_key,
        "source_key": f"digest:{aggregate_key}",
        "threshold": "DIGEST",
        "threshold_at": current,
        "recipient": recipient,
        "channel": channel,
        "digest_items": [
            {key: value for key, value in item.items() if key != "kind"} for item in digest_items
        ],
        **_canonical_payload(payload),
    }
    return _insert_delivery(values)


def _individual_payload(item: dict[str, Any], recipient: str) -> dict[str, Any]:
    row = item["row"]
    occurrence: ThresholdOccurrence = item["occurrence"]
    title = f"Контрольный срок: {row['kind']} [{occurrence.code}]"
    return {
        "title": title,
        "description": (
            f"Проект {escape_html(item['project'].name)}, источник "
            f"{escape_html(row['source_doctype'])} {escape_html(row['source_name'])}, "
            f"срок {escape_html(row['due_at'])}."
        ),
        "recipient": recipient,
        "policy_version": POLICY_VERSION,
    }


def _canonical_payload(payload: dict[str, Any]) -> dict[str, str]:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "payload_json": canonical,
        "payload_hash": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "policy_version": POLICY_VERSION,
    }


def _insert_delivery(values: dict[str, Any]) -> bool:
    if frappe.db.exists("Ferum Notification Delivery", values["delivery_key"]):
        return False
    document = frappe.get_doc({"doctype": "Ferum Notification Delivery", **values})
    try:
        with _delivery_write():
            document.insert(ignore_permissions=True)
    except frappe.DuplicateEntryError:
        return False
    return True


def _process_pending(current: datetime, settings: Any) -> dict[str, int]:
    names = frappe.db.sql(
        """
        select name
        from `tabFerum Notification Delivery`
        where status = 'Pending'
           or (status = 'Retry' and (next_retry_at is null or next_retry_at <= %s))
        order by threshold_at asc, name asc
        """,
        current,
        pluck=True,
    )
    result = {"sent": 0, "queued": 0, "errors": 0}
    for name in names:
        outcome = _attempt_delivery(name, current, cint(settings.max_attempts))
        result[outcome] += 1
    return result


def _attempt_delivery(name: str, current: datetime, max_attempts: int) -> str:
    frappe.db.sql(
        "select name from `tabFerum Notification Delivery` where name=%s for update",
        name,
    )
    document = frappe.get_doc("Ferum Notification Delivery", name)
    if document.status not in {"Pending", "Retry"}:
        return "sent" if document.status == "Sent" else "queued"
    with _delivery_write():
        document.status = "Processing"
        document.attempts = cint(document.attempts) + 1
        document.last_attempt_at = current
        document.next_retry_at = None
        document.error_code = None
        document.save(ignore_permissions=True)
    try:
        payload = json.loads(document.payload_json)
        if document.channel in {"In App", "In App Digest"}:
            notification = _create_notification_log(document, payload)
            with _delivery_write():
                document.notification_log = notification.name
                document.status = "Sent"
                document.sent_at = current
                document.save(ignore_permissions=True)
            return "sent"
        queue = _queue_email(document, payload)
        if queue is None or not getattr(queue, "name", None):
            raise RuntimeError("email queue was not created")
        with _delivery_write():
            document.email_queue = queue.name
            document.status = "Queued"
            document.save(ignore_permissions=True)
        return "queued"
    except Exception as exc:
        _record_failure(document, current, max_attempts, exc.__class__.__name__)
        return "errors"


def _create_notification_log(document: Any, payload: dict[str, Any]) -> Any:
    notification = frappe.new_doc("Notification Log")
    notification.for_user = document.recipient
    notification.from_user = "Administrator"
    notification.title = payload["title"]
    notification.subject = payload["title"]
    notification.description = payload["description"]
    notification.email_content = payload["description"]
    if document.source_doctype and document.source_name:
        notification.document_type = document.source_doctype
        notification.document_name = document.source_name
    notification.insert(ignore_permissions=True)
    return notification


def _queue_email(document: Any, payload: dict[str, Any]) -> Any:
    email = frappe.db.get_value("User", document.recipient, "email")
    if not email:
        raise ValueError("recipient email is missing")
    return frappe.sendmail(
        recipients=[email],
        subject=payload["title"],
        message=payload["description"],
        delayed=True,
        queue_separately=False,
        reference_doctype=document.source_doctype,
        reference_name=document.source_name,
        add_unsubscribe_link=0,
        is_notification=True,
        retry=1,
        message_id=f"{document.delivery_key}@contract-accounting.local",
    )


def _reconcile_email_queues(current: datetime, settings: Any) -> dict[str, int]:
    result = {"sent": 0, "errors": 0}
    names = frappe.get_all(
        "Ferum Notification Delivery",
        filters={"status": "Queued"},
        pluck="name",
        order_by="name asc",
    )
    for name in names:
        document = frappe.get_doc("Ferum Notification Delivery", name)
        queue_status = (
            frappe.db.get_value("Email Queue", document.email_queue, "status")
            if document.email_queue
            else None
        )
        if queue_status in {"Sent", "Partially Sent"}:
            with _delivery_write():
                document.status = "Sent"
                document.sent_at = current
                document.save(ignore_permissions=True)
            result["sent"] += 1
        elif queue_status in {None, "Error"}:
            _record_failure(document, current, cint(settings.max_attempts), "EMAIL_QUEUE_ERROR")
            result["errors"] += 1
    return result


def _record_failure(document: Any, current: datetime, max_attempts: int, code: str) -> None:
    with _delivery_write():
        document.error_code = code[:140]
        document.email_queue = None
        if cint(document.attempts) >= max_attempts:
            document.status = "Dead Letter"
            document.next_retry_at = None
        else:
            document.status = "Retry"
            delay = RETRY_DELAYS_MINUTES[
                min(cint(document.attempts) - 1, len(RETRY_DELAYS_MINUTES) - 1)
            ]
            document.next_retry_at = current + timedelta(minutes=delay)
        document.save(ignore_permissions=True)
    frappe.log_error(
        title="Contract Accounting notification delivery failure",
        message=f"Delivery {document.name}; code {code}; attempt {document.attempts}",
    )


def _enabled_settings() -> Any | None:
    settings = frappe.get_single("Ferum Notification Settings")
    if not settings.enabled or not settings.activated_at:
        return None
    return settings


def _site_naive(value: datetime) -> datetime:
    return value.astimezone(ZoneInfo(get_system_timezone())).replace(tzinfo=None)


def _calendar_local(value: datetime, timezone: str) -> datetime:
    site_value = value.replace(tzinfo=ZoneInfo(get_system_timezone()))
    return site_value.astimezone(ZoneInfo(timezone))


@contextmanager
def _delivery_write() -> Iterator[None]:
    previous = frappe.flags.get(NOTIFICATION_DELIVERY_WRITE_FLAG)
    frappe.flags[NOTIFICATION_DELIVERY_WRITE_FLAG] = True
    try:
        yield
    finally:
        frappe.flags[NOTIFICATION_DELIVERY_WRITE_FLAG] = previous
