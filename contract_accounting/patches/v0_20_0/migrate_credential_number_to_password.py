"""Move legacy plaintext credential numbers into Frappe encrypted Password storage."""

from __future__ import annotations

import hmac
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from typing import Any, Final

from contract_accounting.domain.privacy import mask_credential_number

CREDENTIAL_DOCTYPE: Final[str] = "Ferum Personnel Credential"
SECRET_FIELD: Final[str] = "credential_number"
METADATA_ONLY: Final[str] = "Metadata Only"


class CredentialPasswordMigrationError(RuntimeError):
    """Fail-closed error whose message never contains a credential value or record name."""


@dataclass(frozen=True)
class MigrationCounts:
    examined: int = 0
    migrated: int = 0
    verified_existing: int = 0
    metadata_purged: int = 0


def migrate_rows(
    rows: Iterable[tuple[str, str | None, str]],
    *,
    read_secret: Callable[[str], str | None],
    write_secret: Callable[[str, str], None],
    remove_secret: Callable[[str], None],
    clear_legacy: Callable[[str], None],
    write_mask: Callable[[str, str | None], None],
) -> MigrationCounts:
    """Migrate rows without returning, formatting or logging any secret values."""

    counts = MigrationCounts()
    for name, plaintext, retention_status in rows:
        counts = MigrationCounts(
            examined=counts.examined + 1,
            migrated=counts.migrated,
            verified_existing=counts.verified_existing,
            metadata_purged=counts.metadata_purged,
        )
        try:
            if retention_status == METADATA_ONLY:
                remove_secret(name)
                clear_legacy(name)
                write_mask(name, None)
                counts = MigrationCounts(
                    examined=counts.examined,
                    migrated=counts.migrated,
                    verified_existing=counts.verified_existing,
                    metadata_purged=counts.metadata_purged + 1,
                )
                continue

            encrypted = read_secret(name)
            placeholder = _is_password_placeholder(plaintext)
            legacy_plaintext = None if placeholder else plaintext
            if placeholder and encrypted is None:
                raise CredentialPasswordMigrationError(
                    "Password placeholder has no encrypted credential secret."
                )
            if legacy_plaintext:
                if encrypted is None:
                    write_secret(name, legacy_plaintext)
                    counts = MigrationCounts(
                        examined=counts.examined,
                        migrated=counts.migrated + 1,
                        verified_existing=counts.verified_existing,
                        metadata_purged=counts.metadata_purged,
                    )
                elif not _same_secret(encrypted, legacy_plaintext):
                    raise CredentialPasswordMigrationError(
                        "Credential password migration conflict; transaction must roll back."
                    )
            elif encrypted is None:
                raise CredentialPasswordMigrationError(
                    "Active credential has neither legacy nor encrypted number."
                )

            verified = read_secret(name)
            if verified is None or (
                legacy_plaintext and not _same_secret(verified, legacy_plaintext)
            ):
                raise CredentialPasswordMigrationError(
                    "Credential password migration verification failed."
                )
            write_mask(name, mask_credential_number(verified))
            clear_legacy(name)
            if not legacy_plaintext:
                counts = MigrationCounts(
                    examined=counts.examined,
                    migrated=counts.migrated,
                    verified_existing=counts.verified_existing + 1,
                    metadata_purged=counts.metadata_purged,
                )
        except CredentialPasswordMigrationError:
            raise
        except Exception:
            raise CredentialPasswordMigrationError(
                "Credential password migration failed without emitting sensitive values."
            ) from None
    return counts


def execute() -> dict[str, int]:
    """Run idempotently and return counts only; Frappe ignores the patch return value."""

    import frappe
    from frappe.utils.password import (
        get_decrypted_password,
        remove_encrypted_password,
        set_encrypted_password,
    )

    rows = frappe.db.sql(
        """
        select name, credential_number, retention_status
        from `tabFerum Personnel Credential`
        order by name
        """,
        as_list=True,
    )

    def read_secret(name: str) -> str | None:
        return get_decrypted_password(
            CREDENTIAL_DOCTYPE,
            name,
            SECRET_FIELD,
            raise_exception=False,
        )

    def clear_legacy(name: str) -> None:
        frappe.db.sql(
            """update `tabFerum Personnel Credential`
               set credential_number = null
               where name = %s""",
            (name,),
        )

    def write_mask(name: str, value: str | None) -> None:
        frappe.db.set_value(
            CREDENTIAL_DOCTYPE,
            name,
            "credential_number_masked",
            value,
            update_modified=False,
        )

    counts = migrate_rows(
        (
            (str(name), plaintext, str(retention_status or ""))
            for name, plaintext, retention_status in rows
        ),
        read_secret=read_secret,
        write_secret=lambda name, value: set_encrypted_password(
            CREDENTIAL_DOCTYPE, name, value, SECRET_FIELD
        ),
        remove_secret=lambda name: remove_encrypted_password(
            CREDENTIAL_DOCTYPE, name, SECRET_FIELD
        ),
        clear_legacy=clear_legacy,
        write_mask=write_mask,
    )
    _verify_database_state(frappe, read_secret)
    return {key: int(value) for key, value in asdict(counts).items()}


def _verify_database_state(frappe: Any, read_secret: Callable[[str], str | None]) -> None:
    legacy_count = int(
        frappe.db.sql(
            """select count(*) from `tabFerum Personnel Credential`
               where credential_number is not null and credential_number != ''"""
        )[0][0]
    )
    if legacy_count:
        raise CredentialPasswordMigrationError(
            f"Credential password migration left legacy rows: {legacy_count}."
        )

    rows = frappe.db.sql(
        """select name, credential_number_masked, retention_status
           from `tabFerum Personnel Credential`
           order by name""",
        as_list=True,
    )
    invalid_active = 0
    invalid_metadata = 0
    for name, masked, retention_status in rows:
        try:
            encrypted = read_secret(str(name))
        except Exception:
            encrypted = None
        if retention_status == METADATA_ONLY:
            if encrypted or masked:
                invalid_metadata += 1
        elif not encrypted or masked != mask_credential_number(encrypted):
            invalid_active += 1
    if invalid_active or invalid_metadata:
        raise CredentialPasswordMigrationError(
            "Credential password post-verification failed: "
            f"active={invalid_active}, metadata={invalid_metadata}."
        )


def _same_secret(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def _is_password_placeholder(value: str | None) -> bool:
    return bool(value) and set(str(value)) == {"*"}
