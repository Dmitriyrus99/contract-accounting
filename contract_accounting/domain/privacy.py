"""Pure FR-05 privacy policy rules used by the FR-06 application layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Final

POLICY_REFERENCE: Final[str] = "FR05-PD-01 v1.0"
POLICY_HASH: Final[str] = "19220c689d94046ec24f03ffdf6b00c2cfb33c7749f7d8c59a98398856a4e893"

SYNTHETIC_ACTIVATION_CONFIRMATION: Final[str] = "CONFIRM_SYNTHETIC_TEST_DATA_ONLY"
PRODUCTION_ACTIVATION_CONFIRMATION: Final[str] = "CONFIRM_FR05_PD01_PRODUCTION_PII_AUTHORIZED"
SYNTHETIC_RETENTION_CONFIRMATION: Final[str] = "CONFIRM_SYNTHETIC_RETENTION_EXECUTION"
PRODUCTION_RETENTION_CONFIRMATION: Final[str] = "CONFIRM_APPROVED_PRIVACY_RETENTION_EXECUTION"

ALLOWED_HOLDER_TYPES: Final[frozenset[str]] = frozenset({"Employee", "Ferum Contractor Worker"})
ALLOWED_CREDENTIAL_TYPES: Final[frozenset[str]] = frozenset(
    {
        "Electrical Safety",
        "Occupational Safety",
        "Work at Height",
        "Professional Qualification",
        "Other Mandatory",
    }
)
ALLOWED_ATTACHMENT_SUFFIXES: Final[frozenset[str]] = frozenset({".pdf", ".jpg", ".jpeg", ".png"})
MAX_ATTACHMENT_SIZE: Final[int] = 10 * 1024 * 1024
MAX_BREAK_GLASS_MINUTES: Final[int] = 240


class PrivacyRuleError(ValueError):
    """One immutable FR-05 rule was violated."""


def mask_credential_number(value: str | None) -> str | None:
    """Return a stable last-four projection without leaking a short number."""

    if not value:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    return f"••••{normalized[-4:]}"


def validate_policy_stamp(reference: str | None, policy_hash: str | None) -> None:
    if reference != POLICY_REFERENCE or policy_hash != POLICY_HASH:
        raise PrivacyRuleError("Unsupported or altered FR-05 policy stamp")


def validate_break_glass_minutes(value: int) -> int:
    minutes = int(value)
    if not 1 <= minutes <= MAX_BREAK_GLASS_MINUTES:
        raise PrivacyRuleError("Break-glass duration must be between 1 and 240 minutes")
    return minutes


def break_glass_expiry(activated_at: datetime, minutes: int) -> datetime:
    return activated_at + timedelta(minutes=validate_break_glass_minutes(minutes))


def credential_readiness(
    *,
    status: str,
    data_owner_verified: bool,
    applicability_verified: bool,
    expires_on: date | None,
    no_expiry: bool,
    as_of: date,
) -> str:
    """Return the exact readiness projection for one credential."""

    if not no_expiry and expires_on and expires_on < as_of:
        return "Expired"
    if status in {"Expired", "Revoked"}:
        return "Expired"
    if status != "Verified" or not data_owner_verified or not applicability_verified:
        return "Pending Verification"
    return "Ready"


@dataclass(frozen=True)
class RetentionDue:
    contact: bool
    attachment: bool
    metadata: bool


def retention_due(*, base_date: date, as_of: date) -> RetentionDue:
    if as_of < base_date:
        raise PrivacyRuleError("Retention as_of cannot precede its base date")
    return RetentionDue(
        contact=as_of >= base_date + timedelta(days=90),
        attachment=as_of >= _add_years(base_date, 1),
        metadata=as_of >= _add_years(base_date, 3),
    )


def _add_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        return value.replace(year=value.year + years, month=2, day=28)
