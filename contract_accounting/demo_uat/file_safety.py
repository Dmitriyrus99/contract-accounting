"""Crash-visible, exact-path recovery snapshots for demo/UAT File operations."""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any, Iterable, Mapping

from contract_accounting.demo_uat.runtime import DemoUATRuntimeError

_RECOVERY_DIRECTORY = ".ca-demo-uat-recovery"


def private_files_root(frappe: Any) -> Path:
    root = Path(frappe.get_site_path("private", "files")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def exact_private_path(frappe: Any, file_name: str) -> Path:
    path = (private_files_root(frappe) / file_name).resolve()
    _require_private_path(frappe, path)
    return path


class FileRecoverySet:
    """Keep original bytes until the surrounding database commit is certain."""

    def __init__(self, frappe: Any, paths: Iterable[Path], *, operation: str) -> None:
        self.frappe = frappe
        self.root = private_files_root(frappe)
        self.directory = (self.root / _RECOVERY_DIRECTORY / uuid.uuid4().hex).resolve()
        _require_private_path(frappe, self.directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.snapshots: dict[Path, dict[str, Any]] = {}
        self.operation = operation
        for path in sorted({Path(value).resolve() for value in paths}, key=str):
            self._capture(path)
        self._write_metadata()

    def track_file_documents(self, names: Iterable[str]) -> None:
        """Record actual Frappe paths and the bytes produced by this operation."""

        for name in sorted({str(value) for value in names if value}):
            if not self.frappe.db.exists("File", name):
                continue
            document = self.frappe.get_doc("File", name)
            path = Path(document.get_full_path()).resolve()
            _require_private_path(self.frappe, path)
            if path not in self.snapshots:
                # The path was selected only after the File write. It was not
                # one of the pre-operation deterministic candidates and is
                # therefore treated as newly created, never as preexisting.
                self.snapshots[path] = {
                    "path": path,
                    "existed": False,
                    "sha256": None,
                    "quarantine_path": None,
                    "created_sha256": None,
                }
            if not path.is_file():
                raise DemoUATRuntimeError(f"demo File path is missing before commit: {name}")
            self.snapshots[path]["created_sha256"] = _sha256(path.read_bytes())
        self._write_metadata()

    def restore(self) -> None:
        """Restore pre-operation paths without overwriting concurrent bytes."""

        failures: list[str] = []
        for path, snapshot in sorted(self.snapshots.items(), key=lambda item: str(item[0])):
            _require_private_path(self.frappe, path)
            if snapshot["existed"]:
                quarantine_path = Path(snapshot["quarantine_path"])
                content = quarantine_path.read_bytes()
                if _sha256(content) != snapshot["sha256"]:
                    failures.append(f"quarantine hash drift: {path.name}")
                    continue
                if path.exists() and _sha256(path.read_bytes()) != snapshot["sha256"]:
                    failures.append(f"concurrent path drift: {path.name}")
                    continue
                if not path.exists():
                    path.write_bytes(content)
                if _sha256(path.read_bytes()) != snapshot["sha256"]:
                    failures.append(f"restore hash mismatch: {path.name}")
            elif path.exists():
                created_sha256 = snapshot.get("created_sha256")
                if not created_sha256 or _sha256(path.read_bytes()) != created_sha256:
                    failures.append(f"unexpected bytes at new path: {path.name}")
                    continue
                path.unlink()
        if failures:
            raise DemoUATRuntimeError(
                "demo File recovery incomplete; quarantine retained at "
                f"{self.directory}: {failures}"
            )

    def discard(self) -> None:
        """Delete only this operation's exact recovery files after verification."""

        if not self.directory.exists():
            return
        for path in sorted(self.directory.iterdir(), key=lambda item: item.name):
            resolved = path.resolve()
            _require_private_path(self.frappe, resolved)
            if not resolved.is_file():
                raise DemoUATRuntimeError(
                    f"unexpected non-file in demo recovery directory: {resolved}"
                )
            resolved.unlink()
        self.directory.rmdir()
        parent = self.directory.parent
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()

    def _capture(self, path: Path) -> None:
        _require_private_path(self.frappe, path)
        if path in self.snapshots:
            return
        snapshot: dict[str, Any] = {
            "path": path,
            "existed": path.is_file(),
            "sha256": None,
            "quarantine_path": None,
            "created_sha256": None,
        }
        if snapshot["existed"]:
            content = path.read_bytes()
            snapshot["sha256"] = _sha256(content)
            quarantine_path = self.directory / f"{len(self.snapshots):04d}-{snapshot['sha256']}.bin"
            quarantine_path.write_bytes(content)
            snapshot["quarantine_path"] = quarantine_path.resolve()
        self.snapshots[path] = snapshot

    def _write_metadata(self) -> None:
        metadata = {
            "schema": "contract-accounting/demo-uat-file-recovery/v1",
            "operation": self.operation,
            "paths": [
                {
                    "relative_path": str(path.relative_to(self.root)),
                    "existed": bool(snapshot["existed"]),
                    "sha256": snapshot["sha256"],
                    "created_sha256": snapshot.get("created_sha256"),
                    "quarantine_file": (
                        Path(snapshot["quarantine_path"]).name
                        if snapshot.get("quarantine_path")
                        else None
                    ),
                }
                for path, snapshot in sorted(self.snapshots.items(), key=lambda item: str(item[0]))
            ],
        }
        (self.directory / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )


def _require_private_path(frappe: Any, path: Path) -> None:
    root = Path(frappe.get_site_path("private", "files")).resolve()
    resolved = path.resolve()
    if resolved == root or not resolved.is_relative_to(root):
        raise DemoUATRuntimeError(
            f"demo File recovery refuses path outside private files: {resolved}"
        )


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def describe_quarantine(recovery: FileRecoverySet) -> str:
    return str(recovery.directory)


def snapshot_rows(values: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize Frappe row mappings for exact rollback comparisons."""

    return {str(key): value for key, value in values.items()}
