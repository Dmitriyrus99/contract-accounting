"""Prevent direct private-file access or deletion outside typed FR-06 flows."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Final

import frappe
from frappe import _
from frappe.utils import cint

from contract_accounting.infrastructure.contractor_permissions import (
    CONTRACTOR_ROLE,
    allowed_suppliers,
)
from contract_accounting.infrastructure.operations_permissions import (
    project_visibility_condition,
    scoped_project_roles,
)
from contract_accounting.infrastructure.privacy_target_lock import (
    lock_file_content_hash_aliases,
    lock_privacy_target,
)
from contract_accounting.infrastructure.project_graph_permissions import (
    DIRECT_PROJECT_DOCTYPES,
)

RETENTION_FILE_DELETE_FLAG: Final[str] = "contract_accounting_retention_file_delete"
PENDING_SOURCE_FLAG: Final[str] = "contract_accounting_pending_file_sources"
PROTECTED_ALIAS_FIELDS: Final[tuple[str, ...]] = ("content_hash", "file_url", "is_private")


def write_file(
    file_or_name: Any,
    content: bytes | str | None = None,
    content_type: str | None = None,
    is_private: int = 0,
) -> Any:
    """Guard both Frappe file-writing APIs before public bytes reach disk."""

    if hasattr(file_or_name, "save_file_on_filesystem"):
        file_doc = file_or_name
        payload = file_doc.get("_content") or file_doc.get("content")
        private = cint(file_doc.is_private)
        content_hash = _guard_new_file_content(payload, private)
        source_url = _local_file_url(file_doc.get("file_url"))
        result = file_doc.save_file_on_filesystem()
        _finish_pending_source(source_url, content_hash, _local_file_url(file_doc.file_url))
        return result

    private = cint(is_private)
    content_hash = _guard_new_file_content(content, private)
    result = _write_new_file_exclusive(str(file_or_name), content, private)
    _pending_sources().add((content_hash, _local_file_url(result["file_url"])))
    return result


def _guard_new_file_content(content: bytes | str | None, is_private: int) -> str:
    """Serialize public and private content paths before bytes are written."""

    if not content:
        return ""
    from frappe.core.doctype.file.utils import get_content_hash

    content_hash = get_content_hash(content)
    credential = _credential_for_identity(content_hash, "")
    if credential:
        lock_privacy_target("Ferum Personnel Credential", credential)
    lock_file_content_hash_aliases(content_hash)
    if is_private:
        return str(content_hash)
    # FOR UPDATE is intentional: after waiting for a competing transaction it
    # performs a current read instead of reusing an older repeatable-read view.
    if _credential_for_identity(content_hash, "", for_update=True):
        frappe.throw(
            _("Public File alias для Credential content запрещён."),
            frappe.PermissionError,
        )
    return str(content_hash)


def _write_new_file_exclusive(
    filename: str,
    content: bytes | str | None,
    is_private: int,
) -> dict[str, str]:
    """Create the manager source path atomically instead of overwriting a race."""

    if not filename or Path(filename).name != filename or content is None:
        frappe.throw(_("File source path недействителен."))
    root = Path(
        frappe.get_site_path("private", "files")
        if is_private
        else frappe.get_site_path("public", "files")
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = (root / filename).resolve()
    if path.parent != root:
        frappe.throw(_("File source path вышел за пределы site."))
    payload = content.encode() if isinstance(content, str) else content
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        frappe.throw(_("File source path уже занят; повторите upload."), frappe.DuplicateEntryError)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise
    frappe.db.after_rollback.add(lambda: path.unlink(missing_ok=True))
    prefix = "/private/files/" if is_private else "/files/"
    return {"file_name": filename, "file_url": f"{prefix}{filename}"}


def _pending_sources() -> set[tuple[str, str]]:
    sources = frappe.flags.get(PENDING_SOURCE_FLAG)
    if sources is None:
        sources = set()
        frappe.flags[PENDING_SOURCE_FLAG] = sources
    return sources


def _finish_pending_source(source_url: str, content_hash: str, canonical_url: str) -> None:
    identity = (str(content_hash or ""), str(source_url or ""))
    if identity not in _pending_sources():
        return
    _pending_sources().discard(identity)
    if not source_url or source_url == canonical_url:
        return
    owners = frappe.db.sql(
        "select name from `tabFile` where file_url = %s or thumbnail_url = %s order by name for update",
        (source_url, source_url),
    )
    if owners:
        return
    source = _local_file_path(source_url)
    canonical = _local_file_path(canonical_url)
    if not source.is_file() or not canonical.is_file():
        frappe.throw(_("File source/canonical path отсутствует после write."))
    if _md5(source) != content_hash or _md5(canonical) != content_hash:
        frappe.throw(_("File source/canonical bytes не совпадают с content hash."))
    source.unlink()


def _local_file_path(file_url: str) -> Path:
    normalized = _local_file_url(file_url)
    if normalized.startswith("/private/files/"):
        root = Path(frappe.get_site_path("private", "files")).resolve()
    elif normalized.startswith("/files/"):
        root = Path(frappe.get_site_path("public", "files")).resolve()
    else:
        frappe.throw(_("File path не является локальным site path."))
    path = (root / Path(normalized).name).resolve()
    if path.parent != root:
        frappe.throw(_("File path вышел за пределы site."))
    return path


def _md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)  # nosec B324
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def has_permission(
    doc: Any,
    ptype: str | None = None,
    user: str | None = None,
    debug: bool = False,
) -> bool | None:
    credential = _credential_for_file(doc.name)
    user = user or frappe.session.user
    if credential:
        # Credential binaries are never exposed through native File surfaces.
        # The typed download command performs policy, malware, exact-target,
        # reason and audit checks before reading the bytes itself.
        return False
    linked_records = _project_file_records(doc.name)
    if not linked_records:
        return None
    parent_ptype = "read" if ptype in {None, "read", "select", "report"} else "write"
    if any(
        frappe.has_permission(doctype, parent_ptype, doc=name, user=user)
        for doctype, name in linked_records
    ):
        # Do not grant File access by ourselves. Returning None keeps Frappe's
        # standard File/attachment policy active after the project boundary.
        return None
    return False


def get_permission_query_conditions(user: str | None = None) -> str:
    """Hide credential metadata and enforce parent row ACL in File lists/exports."""

    user = user or frappe.session.user
    credential_hidden = (
        "not exists (select 1 from `tabFerum Personnel Credential` credential "
        "join `tabFile` credential_file on credential_file.name = credential.document "
        "where credential_file.name = `tabFile`.`name` or "
        "(ifnull(credential_file.content_hash, '') != '' and "
        "credential_file.content_hash = `tabFile`.content_hash) or "
        "(credential_file.file_url like '/files/%%' or "
        "credential_file.file_url like '/private/files/%%') and "
        "credential_file.file_url = `tabFile`.file_url) and "
        "ifnull(`tabFile`.`attached_to_doctype`, '') not in "
        "('Ferum Personnel Credential', 'Ferum Contractor Worker')"
    )
    if CONTRACTOR_ROLE in frappe.get_roles(user):
        suppliers = allowed_suppliers(user)
        if suppliers:
            escaped = ", ".join(frappe.db.escape(value) for value in suppliers)
            contractor_attachment = (
                "ifnull(`tabFile`.`attached_to_doctype`, '') != "
                "'Ferum Contractor Assignment' or exists (select 1 "
                "from `tabFerum Contractor Assignment` contractor_assignment "
                "where contractor_assignment.name = `tabFile`.`attached_to_name` "
                f"and contractor_assignment.supplier in ({escaped}))"
            )
        else:
            contractor_attachment = (
                "ifnull(`tabFile`.`attached_to_doctype`, '') != 'Ferum Contractor Assignment'"
            )
        credential_hidden = f"({credential_hidden}) and ({contractor_attachment})"
    roles = scoped_project_roles(user)
    if not roles:
        return credential_hidden

    visibility = {
        "document": project_visibility_condition(
            "project_document.service_project", user=user, roles=roles
        ),
        "photo": project_visibility_condition(
            "photo_evidence.service_project", user=user, roles=roles
        ),
        "step": project_visibility_condition(
            "process_step.service_project", user=user, roles=roles
        ),
        "billing": project_visibility_condition(
            "billing_artifact.service_project", user=user, roles=roles
        ),
    }
    typed_references = (
        "exists (select 1 from `tabFerum Project Document` project_document "
        "where project_document.file = `tabFile`.`name`) or "
        "exists (select 1 from `tabFerum Project Document Event` document_event "
        "where document_event.evidence_file = `tabFile`.`name`) or "
        "exists (select 1 from `tabFerum Photo Evidence` photo_evidence "
        "where photo_evidence.file = `tabFile`.`name`) or "
        "exists (select 1 from `tabFerum Process Evidence` process_evidence "
        "where process_evidence.evidence_file = `tabFile`.`name`) or "
        "exists (select 1 from `tabFerum Billing Artifact` billing_artifact "
        "where billing_artifact.file = `tabFile`.`name`)"
    )
    visible_typed_references = (
        "exists (select 1 from `tabFerum Project Document` project_document "
        f"where project_document.file = `tabFile`.`name` and {visibility['document']}) or "
        "exists (select 1 from `tabFerum Project Document Event` document_event "
        "join `tabFerum Project Document` project_document "
        "on project_document.name = document_event.project_document "
        f"where document_event.evidence_file = `tabFile`.`name` and {visibility['document']}) or "
        "exists (select 1 from `tabFerum Photo Evidence` photo_evidence "
        f"where photo_evidence.file = `tabFile`.`name` and {visibility['photo']}) or "
        "exists (select 1 from `tabFerum Process Evidence` process_evidence "
        "join `tabFerum Project Process Step` process_step "
        "on process_step.name = process_evidence.process_step "
        f"where process_evidence.evidence_file = `tabFile`.`name` and {visibility['step']}) or "
        "exists (select 1 from `tabFerum Billing Artifact` billing_artifact "
        f"where billing_artifact.file = `tabFile`.`name` and {visibility['billing']})"
    )
    generic_reference, visible_generic_reference = _generic_project_attachments(user, roles)
    references = f"({typed_references}) or ({generic_reference})"
    visible_references = f"({visible_typed_references}) or ({visible_generic_reference})"
    return f"({credential_hidden}) and (not ({references}) or ({visible_references}))"


def prevent_credential_file_delete(doc: Any, method: str | None = None) -> None:
    if _credential_for_file(doc.name) and not frappe.flags.get(RETENTION_FILE_DELETE_FLAG):
        frappe.throw(
            _("Credential File удаляется только утверждённой retention command."),
            frappe.PermissionError,
        )


def validate_credential_alias_set(doc: Any, method: str | None = None) -> None:
    """Reject a Credential whose blob already has a public/native alias."""

    if not doc.document:
        return
    identity = frappe.db.get_value(
        "File",
        doc.document,
        ("content_hash", "file_url"),
        as_dict=True,
    )
    if not identity or not identity.content_hash:
        frappe.throw(_("Credential attachment File не найден или не имеет content hash."))
    lock_file_content_hash_aliases(
        str(identity.content_hash),
        canonical_file=str(doc.document),
        file_url=str(identity.file_url or ""),
    )
    # Use a locking/current read after the shared File lock. A plain consistent
    # read could otherwise miss the public alias committed while this request
    # was blocked on the canonical File row.
    aliases = credential_file_aliases(doc.document, for_update=True)
    if not aliases:
        frappe.throw(_("Credential attachment File не найден."))
    if any(
        not cint(row.is_private) or not str(row.file_url or "").startswith("/private/files/")
        for row in aliases
    ):
        frappe.throw(
            _("Credential attachment и все content-hash aliases должны быть private."),
            frappe.PermissionError,
        )
    if any(str(row.thumbnail_url or "").strip() for row in aliases):
        frappe.throw(
            _("Credential attachment не должен иметь public thumbnail derivative."),
            frappe.PermissionError,
        )


def preflight_new_file_alias(doc: Any) -> None:
    """Serialize every local alias before Frappe writes/reuses its path."""

    content = doc.get("_content") or doc.get("content")
    content_hash = str(doc.get("content_hash") or "")
    if content and not content_hash:
        from frappe.core.doctype.file.utils import get_content_hash

        content_hash = str(get_content_hash(content))
    file_url = _local_file_url(doc.get("file_url"))
    if not content_hash and not file_url:
        return
    credential = _credential_for_identity(content_hash, file_url)
    if credential:
        lock_privacy_target("Ferum Personnel Credential", credential)
    lock_file_content_hash_aliases(content_hash, file_url=file_url)
    current_credential = _credential_for_identity(content_hash, file_url, for_update=True)
    if credential and current_credential != credential:
        frappe.throw(
            _("Credential private alias source исчез во время создания."),
            frappe.PermissionError,
        )

    if file_url and not content:
        exact_owner = any(
            str(row.file_url or "") == file_url
            for row in _file_identity_rows(content_hash, file_url, for_update=True)
        )
        pending_source = (content_hash, file_url) in _pending_sources()
        if _local_file_path(file_url).is_file() and not exact_owner and not pending_source:
            frappe.throw(
                _("Unowned local File source path запрещён."),
                frappe.PermissionError,
            )

    if not cint(doc.is_private):
        if current_credential:
            frappe.throw(
                _("Public File alias для Credential content запрещён."),
                frappe.PermissionError,
            )
        return

    if credential and not content and file_url:
        current_aliases = _file_identity_rows(content_hash, file_url, for_update=True)
        if not current_aliases or not any(
            str(row.file_url or "") == file_url
            and frappe.get_doc("File", row.name).exists_on_disk()
            for row in current_aliases
        ):
            frappe.throw(
                _("Credential private alias source исчез во время создания."),
                frappe.PermissionError,
            )


def validate_credential_file_alias(doc: Any) -> None:
    """Keep every alias private and freeze the hash/path privacy boundary."""

    stored = None
    if doc.name and frappe.db.exists("File", doc.name):
        stored = frappe.db.get_value(
            "File",
            doc.name,
            PROTECTED_ALIAS_FIELDS,
            as_dict=True,
        )
    credential = _credential_for_file(doc.name) if stored else None
    if credential:
        lock_privacy_target("Ferum Personnel Credential", credential)
        credential = _credential_for_file(doc.name)
    if (
        credential
        and stored
        and any(doc.get(field) != stored.get(field) for field in PROTECTED_ALIAS_FIELDS)
    ):
        frappe.throw(
            _("Credential File alias hash/path/privacy immutable."),
            frappe.PermissionError,
        )

    credential = credential or _credential_for_identity(
        str(doc.content_hash or ""),
        _local_file_url(doc.file_url),
    )
    if credential:
        lock_privacy_target("Ferum Personnel Credential", credential)
        if _credential_for_identity(
            str(doc.content_hash or ""),
            _local_file_url(doc.file_url),
        ) and (
            not cint(doc.is_private) or not str(doc.file_url or "").startswith("/private/files/")
        ):
            frappe.throw(
                _("Credential File aliases должны оставаться private."),
                frappe.PermissionError,
            )


def _credential_for_file(file_name: str) -> str | None:
    if not file_name:
        return None
    rows = frappe.db.sql(
        """
        select credential.name
          from `tabFerum Personnel Credential` credential
          join `tabFile` credential_file on credential_file.name = credential.document
          join `tabFile` candidate on candidate.name = %s
         where (
                candidate.name = credential_file.name
                or (
                    ifnull(candidate.content_hash, '') != ''
                    and candidate.content_hash = credential_file.content_hash
                )
                or (
                    (
                        credential_file.file_url like '/files/%%'
                        or credential_file.file_url like '/private/files/%%'
                    )
                    and candidate.file_url = credential_file.file_url
                )
           )
         order by credential.name
         limit 1
        """,
        (file_name,),
    )
    return str(rows[0][0]) if rows else None


def is_credential_file_alias(file_name: str) -> bool:
    """Return whether an exact/hash File belongs to any Credential blob."""

    return bool(_credential_for_file(file_name))


def _credential_for_identity(
    content_hash: str,
    file_url: str,
    *,
    for_update: bool = False,
) -> str | None:
    normalized_hash = str(content_hash or "").strip()
    normalized_url = _local_file_url(file_url)
    conditions: list[str] = []
    parameters: list[str] = []
    if normalized_hash:
        conditions.append("credential_file.content_hash = %s")
        parameters.append(normalized_hash)
    if normalized_url:
        conditions.append("credential_file.file_url = %s")
        parameters.append(normalized_url)
    if not conditions:
        return None
    lock_clause = " for update" if for_update else ""
    rows = frappe.db.sql(
        f"""
        select credential.name
          from `tabFerum Personnel Credential` credential
          join `tabFile` credential_file on credential_file.name = credential.document
         where ({" or ".join(conditions)})
         order by credential.name
         limit 1
         {lock_clause}
        """,  # nosec: predicates are closed constants; all values are parameters.
        tuple(parameters),
    )
    return str(rows[0][0]) if rows else None


def credential_file_aliases(
    file_name: str,
    *,
    for_update: bool = False,
) -> tuple[Any, ...]:
    """Return the complete exact/hash alias set, independent of privacy state."""

    if not file_name:
        return ()
    lock_clause = " for update" if for_update else ""
    return tuple(
        frappe.db.sql(
            f"""
            select alias.name, alias.content_hash, alias.file_url, alias.is_private,
                   alias.thumbnail_url, alias.attached_to_doctype, alias.attached_to_name
              from `tabFile` credential_file
              join `tabFile` alias
                on alias.name = credential_file.name
                or (
                    ifnull(credential_file.content_hash, '') != ''
                    and alias.content_hash = credential_file.content_hash
                )
                or (
                    (
                        credential_file.file_url like '/files/%%'
                        or credential_file.file_url like '/private/files/%%'
                    )
                    and alias.file_url = credential_file.file_url
                )
             where credential_file.name = %s
             order by alias.name
             {lock_clause}
            """,  # nosec: lock_clause is selected from a closed constant above.
            (file_name,),
            as_dict=True,
        )
    )


def _file_identity_rows(
    content_hash: str,
    file_url: str,
    *,
    for_update: bool = False,
) -> tuple[Any, ...]:
    normalized_hash = str(content_hash or "").strip()
    normalized_url = _local_file_url(file_url)
    conditions: list[str] = []
    parameters: list[str] = []
    if normalized_hash:
        conditions.append("content_hash = %s")
        parameters.append(normalized_hash)
    if normalized_url:
        conditions.append("file_url = %s")
        parameters.append(normalized_url)
    if not conditions:
        return ()
    lock_clause = " for update" if for_update else ""
    return tuple(
        frappe.db.sql(
            f"""
            select name, content_hash, file_url, is_private
              from `tabFile`
             where ({" or ".join(conditions)})
             order by name
             {lock_clause}
            """,  # nosec: predicates are closed constants; all values are parameters.
            tuple(parameters),
            as_dict=True,
        )
    )


def _local_file_url(file_url: Any) -> str:
    normalized = str(file_url or "").strip()
    return normalized if normalized.startswith(("/files/", "/private/files/")) else ""


def _project_file_records(file_name: str) -> tuple[tuple[str, str], ...]:
    references: list[tuple[str, str]] = []
    for doctype, fieldname in (
        ("Ferum Project Document", "file"),
        ("Ferum Project Document Event", "evidence_file"),
        ("Ferum Photo Evidence", "file"),
        ("Ferum Process Evidence", "evidence_file"),
        ("Ferum Billing Artifact", "file"),
    ):
        if not frappe.db.table_exists(doctype):
            continue
        references.extend(
            (doctype, str(name))
            for name in frappe.get_all(
                doctype,
                filters={fieldname: file_name},
                pluck="name",
                ignore_permissions=True,
            )
        )
    return tuple(references)


def _generic_project_attachments(user: str, roles: set[str]) -> tuple[str, str]:
    direct = sorted(DIRECT_PROJECT_DOCTYPES | {"Ferum Service Project"})
    indirect = (
        "Ferum Object System",
        "Ferum Process Evidence",
        "Ferum Project Document Event",
        "Ferum Service Object",
    )
    doctypes = direct + list(indirect)
    attached_doctypes = ", ".join(frappe.db.escape(doctype) for doctype in doctypes)
    reference = f"`tabFile`.`attached_to_doctype` in ({attached_doctypes})"
    visible: list[str] = []
    for doctype in direct:
        project_expression = (
            "attached_parent.name"
            if doctype == "Ferum Service Project"
            else "attached_parent.service_project"
        )
        condition = project_visibility_condition(project_expression, user=user, roles=roles)
        visible.append(
            f"(`tabFile`.`attached_to_doctype` = {frappe.db.escape(doctype)} and "
            f"exists (select 1 from `tab{doctype}` attached_parent "
            "where attached_parent.name = `tabFile`.`attached_to_name` "
            f"and {condition}))"
        )

    service_object_visibility = project_visibility_condition(
        "project_object.service_project", user=user, roles=roles
    )
    visible.extend(
        [
            "(`tabFile`.`attached_to_doctype` = 'Ferum Service Object' and "
            "exists (select 1 from `tabFerum Service Object` attached_parent "
            "join `tabFerum Project Object` project_object "
            "on project_object.service_object = attached_parent.name "
            "where attached_parent.name = `tabFile`.`attached_to_name` "
            f"and {service_object_visibility}))",
            "(`tabFile`.`attached_to_doctype` = 'Ferum Object System' and "
            "exists (select 1 from `tabFerum Object System` attached_parent "
            "join `tabFerum Project Object` project_object "
            "on project_object.service_object = attached_parent.service_object "
            "where attached_parent.name = `tabFile`.`attached_to_name` "
            f"and {service_object_visibility}))",
        ]
    )
    step_visibility = project_visibility_condition(
        "process_step.service_project", user=user, roles=roles
    )
    document_visibility = project_visibility_condition(
        "project_document.service_project", user=user, roles=roles
    )
    visible.extend(
        [
            "(`tabFile`.`attached_to_doctype` = 'Ferum Process Evidence' and "
            "exists (select 1 from `tabFerum Process Evidence` attached_parent "
            "join `tabFerum Project Process Step` process_step "
            "on process_step.name = attached_parent.process_step "
            "where attached_parent.name = `tabFile`.`attached_to_name` "
            f"and {step_visibility}))",
            "(`tabFile`.`attached_to_doctype` = 'Ferum Project Document Event' and "
            "exists (select 1 from `tabFerum Project Document Event` attached_parent "
            "join `tabFerum Project Document` project_document "
            "on project_document.name = attached_parent.project_document "
            "where attached_parent.name = `tabFile`.`attached_to_name` "
            f"and {document_visibility}))",
        ]
    )
    return reference, " or ".join(visible)
