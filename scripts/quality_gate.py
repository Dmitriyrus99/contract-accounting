"""Cross-platform static quality gate for the first release.

This gate deliberately does not claim Frappe/Bench runtime qualification, UAT,
production restore, legal/finance approval, or deployment.  Those remain
separate release gates with their own runtime evidence.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
FORMAT_BASELINE = ROOT / ".quality" / "ruff_format_baseline.json"
PYTHON_TARGETS = ("contract_accounting", "tests", "scripts")

EXPECTED_SCOPE = Counter(
    {
        ("Mandatory", "Implemented"): 280,
        ("Mandatory", "Partial"): 274,
        ("Mandatory", "Absent"): 0,
        ("N/A", "N/A"): 2,
        ("Out of Release", "Deferred"): 1,
    }
)

PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.IGNORECASE)
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(?:password|passwd|api[_-]?key|access[_-]?token|secret)\b"
    r"\s*[:=]\s*[\"']([^\"'\r\n]{8,})[\"']"
)
SAFE_SECRET_MARKERS = (
    "${",
    "<",
    "changeme",
    "dummy",
    "example",
    "not-a-secret",
    "placeholder",
    "redacted",
    "test",
)
MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


class GateError(RuntimeError):
    """One deterministic quality assertion failed."""


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print(f"$ {' '.join(command)}", flush=True)
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=capture,
    )
    if result.returncode:
        if capture:
            sys.stdout.write(result.stdout)
            sys.stderr.write(result.stderr)
        raise GateError(f"Command failed with exit code {result.returncode}")
    return result


def relative_path(filename: str) -> str:
    path = Path(filename)
    if path.is_absolute():
        path = path.relative_to(ROOT)
    return path.as_posix()


def ruff_format_debt() -> set[str]:
    command = [
        "ruff",
        "format",
        "--check",
        "--output-format",
        "json",
        *PYTHON_TARGETS,
    ]
    print(f"$ {' '.join(command)}", flush=True)
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    if result.returncode not in {0, 1}:
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise GateError(f"Ruff format inspection failed with exit code {result.returncode}")
    try:
        diagnostics = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise GateError("Ruff did not return valid JSON diagnostics") from exc
    return {relative_path(item["filename"]) for item in diagnostics}


def write_format_baseline() -> None:
    debt = sorted(ruff_format_debt())
    FORMAT_BASELINE.parent.mkdir(parents=True, exist_ok=True)
    FORMAT_BASELINE.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "policy": "Existing files may leave the set; no file may enter it.",
                "unformatted_files": debt,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"FORMAT_BASELINE_WRITTEN={FORMAT_BASELINE.relative_to(ROOT).as_posix()}")
    print(f"FORMAT_BASELINE_FILES={len(debt)}")


def check_format_ratchet() -> None:
    if not FORMAT_BASELINE.exists():
        raise GateError(f"Missing format baseline: {FORMAT_BASELINE.relative_to(ROOT)}")
    baseline_data = json.loads(FORMAT_BASELINE.read_text(encoding="utf-8"))
    baseline = set(baseline_data["unformatted_files"])
    current = ruff_format_debt()
    new_debt = sorted(current - baseline)
    if new_debt:
        raise GateError("New Ruff format debt: " + ", ".join(new_debt))
    print(f"FORMAT_DEBT_CURRENT={len(current)}")
    print(f"FORMAT_DEBT_REMOVED={len(baseline - current)}")
    print("FORMAT_RATCHET=PASS")


def check_release_scope() -> None:
    source_path = ROOT / "07_traceability.csv"
    matrix_path = ROOT / "12_release_scope_matrix_v1.csv"
    with source_path.open(encoding="utf-8-sig", newline="") as handle:
        source = list(csv.DictReader(handle))
    with matrix_path.open(encoding="utf-8", newline="") as handle:
        matrix = list(csv.DictReader(handle))

    source_ids = [row["req_id"] for row in source]
    matrix_ids = [row["req_id"] for row in matrix]
    if len(source_ids) != 557 or len(set(source_ids)) != 557:
        raise GateError("07_traceability.csv must contain 557 unique requirement IDs")
    if len(matrix_ids) != 557 or len(set(matrix_ids)) != 557:
        raise GateError("12_release_scope_matrix_v1.csv must contain 557 unique requirement IDs")
    if set(source_ids) != set(matrix_ids):
        raise GateError("Release-scope IDs differ from the immutable traceability source")

    distribution = Counter((row["release_scope"], row["implementation_status"]) for row in matrix)
    if distribution != EXPECTED_SCOPE:
        raise GateError(f"Unexpected release-scope distribution: {dict(distribution)}")

    required_fields = (
        "automated_acceptance",
        "current_evidence_ref",
        "manual_gate",
        "owner_role",
    )
    incomplete = [
        row["req_id"]
        for row in matrix
        if row["release_scope"] == "Mandatory"
        and any(not row[field].strip() for field in required_fields)
    ]
    if incomplete:
        raise GateError("Mandatory scope has incomplete control fields: " + ", ".join(incomplete))
    print("RELEASE_SCOPE=PASS|ROWS=557|MANDATORY=554|ABSENT=0")


def project_files(suffix: str) -> list[Path]:
    excluded = {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "output"}
    return sorted(
        path
        for path in ROOT.rglob(f"*{suffix}")
        if not excluded.intersection(path.relative_to(ROOT).parts)
    )


def check_json_and_javascript() -> None:
    json_files = project_files(".json")
    for path in json_files:
        json.loads(path.read_text(encoding="utf-8"))
    print(f"JSON_PARSE=PASS|FILES={len(json_files)}")

    javascript_files = project_files(".js")
    if javascript_files and not shutil.which("node"):
        raise GateError("Node.js is required to validate JavaScript syntax")
    for path in javascript_files:
        run(["node", "--check", str(path.relative_to(ROOT))])
    print(f"JAVASCRIPT_SYNTAX=PASS|FILES={len(javascript_files)}")


def git_visible_files() -> list[Path]:
    result = run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        capture=True,
    )
    return [ROOT / item for item in result.stdout.split("\0") if item]


def check_secrets() -> None:
    text_suffixes = {
        ".cfg",
        ".csv",
        ".ini",
        ".js",
        ".json",
        ".md",
        ".py",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }
    findings: list[str] = []
    scanned = 0
    for path in git_visible_files():
        if path.suffix.lower() not in text_suffixes or not path.is_file():
            continue
        scanned += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        if PRIVATE_KEY_RE.search(text):
            findings.append(f"{path.relative_to(ROOT)}: private-key header")
        for match in SECRET_ASSIGNMENT_RE.finditer(text):
            value = match.group(1).lower()
            if not any(marker in value for marker in SAFE_SECRET_MARKERS):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{path.relative_to(ROOT)}:{line}: possible literal secret")
    if findings:
        raise GateError("Secret scan findings:\n" + "\n".join(findings))
    print(f"SECRET_SCAN=PASS|FILES={scanned}")


def check_markdown_links() -> None:
    broken: list[str] = []
    checked = 0
    for document in project_files(".md"):
        text = document.read_text(encoding="utf-8", errors="replace")
        for match in MARKDOWN_LINK_RE.finditer(text):
            raw = match.group(1).strip()
            if raw.startswith("<") and raw.endswith(">"):
                raw = raw[1:-1]
            target = raw.split(" ", 1)[0].split("#", 1)[0]
            if not target or re.match(r"^(?:https?|mailto):", target, re.IGNORECASE):
                continue
            target_path = (document.parent / unquote(target)).resolve()
            checked += 1
            if not target_path.exists():
                line = text.count("\n", 0, match.start()) + 1
                broken.append(f"{document.relative_to(ROOT)}:{line} -> {target}")
    if broken:
        raise GateError("Broken local Markdown links:\n" + "\n".join(broken))
    print(f"MARKDOWN_LINKS=PASS|LINKS={checked}")


def run_gate() -> None:
    run([sys.executable, "scripts/build_release_scope_matrix.py", "--check"])
    check_release_scope()
    run(["ruff", "check", *PYTHON_TARGETS])
    check_format_ratchet()
    run([sys.executable, "-m", "compileall", "-q", *PYTHON_TARGETS])
    check_json_and_javascript()
    check_secrets()
    check_markdown_links()
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    run([sys.executable, "-m", "mypy"])
    run([sys.executable, "-m", "build"])
    print("STATIC_QUALITY_GATE=PASS")
    print("RUNTIME_UAT_DEPLOYMENT_GATES=NOT_EVALUATED")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write-format-baseline",
        action="store_true",
        help="Regenerate the reviewed legacy Ruff-format debt baseline.",
    )
    args = parser.parse_args()
    if args.write_format_baseline:
        write_format_baseline()
        return
    run_gate()


if __name__ == "__main__":
    try:
        main()
    except (GateError, KeyError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"STATIC_QUALITY_GATE=FAIL|{exc}", file=sys.stderr)
        raise SystemExit(1) from exc
