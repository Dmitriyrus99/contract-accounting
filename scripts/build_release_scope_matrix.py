"""Build the Release Scope v1 requirement matrix from versioned evidence.

The discovery CSV files remain immutable historical inputs.  This generator
matches each of the 557 target requirement IDs only to explicit rows in the
CA-01...CA-15 implementation traceability files.  Missing evidence is kept
fail-closed as Absent; it is never inferred from filenames or broad increment
status claims.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "07_traceability.csv"
OUTPUT = ROOT / "12_release_scope_matrix_v1.csv"

REQ_RE = re.compile(r"^TCA-([AB])-(\d{2})-(\d{2})$")
FULL_ITEM_RE = re.compile(r"TCA-([AB])-(\d{2})-(\d{2})(?:…(?:TCA-[AB]-\d{2}-)?(\d{2}))?")
CHAPTER_WILDCARD_RE = re.compile(r"TCA-([AB])-(\d{2})(?:…(\d{2}))?-\*")
SHORT_ITEM_RE = re.compile(r"^(\d{2})(?:…(\d{2}))?$")

OUT_OF_RELEASE = {
    "TCA-B-38-04": (
        "DP-03 defers 1C integrations; retain a negative acceptance that no "
        "ERPNext-to-1C adapter, route, job or credential is enabled."
    )
}

SUPERSEDED = {
    "TCA-A-13-02": "Superseded by approved OQ-CA-003 legal-state enum.",
    "TCA-A-13-04": "Superseded by approved OQ-CA-003 execution-state enum.",
}

MANUAL_GATES = {
    "CA-00": "baseline-exact Staging inventory; credential-safe restore",
    "CA-01": "business/legal UAT; downstream reconciliation; production cutover",
    "CA-02": "calendar/SLA configuration UAT; downstream schedule integration",
    "CA-03": "operations UAT; billing/finding integration; load/race",
    "CA-04": "inspection/photo-policy UAT; contractor boundary",
    "CA-05": "document/legal/operations UAT; signed-file retention",
    "CA-06": "finance/legal document UAT; PDF/DOCX templates; load/race",
    "CA-07": "finance UAT; accounting reconciliation; performance",
    "CA-08": "MG-CA-015 privacy approval; personnel readiness; HR/security UAT",
    "CA-09": "site calendar/annual Operations; notification activation/outgoing transport/RBAC UAT",
    "CA-10": "browser/report/export permission UAT; representative performance",
    "CA-11": "configured process catalog; Generate Process notification event; UAT",
    "CA-12": "MG-CA-015; launch/process UAT; automatic artifacts",
    "CA-13": "scheduler recurrence; positive UPD/SF; finance/legal UAT",
    "CA-14": "complete browser/RBAC/export matrix; pagination/performance",
    "CA-15": "cross-role/export/report UAT; load/race; cutover/rollback",
}


def load_requirements() -> list[dict[str, str]]:
    with SOURCE.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 557:
        raise SystemExit(f"Expected 557 traceability rows, found {len(rows)}")
    ids = [row["req_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise SystemExit("Duplicate req_id in 07_traceability.csv")
    return rows


def expand_selector(selector: str, valid_ids: set[str]) -> set[str]:
    """Expand a Markdown selector such as TCA-A-01-01…18, 21, 25."""

    normalized = selector.replace("`", "").replace("–", "…").strip()
    selected: set[str] = set()

    for match in CHAPTER_WILDCARD_RE.finditer(normalized):
        area = match.group(1)
        first = int(match.group(2))
        last = int(match.group(3) or match.group(2))
        for req_id in valid_ids:
            parsed = REQ_RE.match(req_id)
            if parsed and parsed.group(1) == area and first <= int(parsed.group(2)) <= last:
                selected.add(req_id)

    active_area: str | None = None
    active_chapter: int | None = None
    for part in (item.strip() for item in normalized.split(",")):
        full = FULL_ITEM_RE.search(part)
        if full:
            active_area = full.group(1)
            active_chapter = int(full.group(2))
            first = int(full.group(3))
            last = int(full.group(4) or full.group(3))
        else:
            short = SHORT_ITEM_RE.match(part)
            if not short or active_area is None or active_chapter is None:
                continue
            first = int(short.group(1))
            last = int(short.group(2) or short.group(1))
        for item_number in range(first, last + 1):
            req_id = f"TCA-{active_area}-{active_chapter:02d}-{item_number:02d}"
            if req_id in valid_ids:
                selected.add(req_id)

    return selected


def evidence_status(text: str) -> str:
    upper = text.upper()
    if "SUPERSEDED" in upper:
        return "N/A"
    if "DEFERRED" in upper:
        return "Partial"
    if "PARTIAL" in upper or "BLOCKED" in upper or "FAIL-CLOSED" in upper:
        return "Partial"
    if "OPEN" in upper and not any(
        marker in upper for marker in ("PASS", "IMPLEMENTED", "CODE", "SCHEMA")
    ):
        return "Absent"
    if "PASS" in upper or "IMPLEMENTED" in upper:
        return "Implemented"
    return "Partial"


def collect_evidence(valid_ids: set[str]) -> dict[str, list[dict[str, str]]]:
    evidence: dict[str, list[dict[str, str]]] = defaultdict(list)
    files = sorted((ROOT / "implementation").glob("CA-*/traceability_v*.md"))
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.startswith("|") or "`TCA-" not in line:
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) < 2:
                continue
            selector = cells[0]
            detail = " | ".join(cells[1:]).replace("`", "")
            for req_id in expand_selector(selector, valid_ids):
                evidence[req_id].append(
                    {
                        "status": evidence_status(detail),
                        "ref": f"{relative}:{line_number}",
                        "detail": detail,
                    }
                )
    return evidence


def merged_status(items: list[dict[str, str]]) -> str:
    current_overrides = [item for item in items if "CURRENT OVERRIDE" in item["detail"].upper()]
    if current_overrides:
        items = current_overrides
    statuses = {item["status"] for item in items}
    if "N/A" in statuses:
        return "N/A"
    if "Partial" in statuses:
        return "Partial"
    if "Implemented" in statuses:
        return "Implemented"
    if "Absent" in statuses:
        return "Absent"
    return "Absent"


def compact_details(items: list[dict[str, str]]) -> str:
    unique: list[str] = []
    for item in items:
        detail = re.sub(r"\s+", " ", item["detail"]).strip()
        if detail not in unique:
            unique.append(detail)
    joined = " || ".join(unique)
    return joined[:1200]


def render_matrix() -> tuple[str, Counter[tuple[str, str]]]:
    rows = load_requirements()
    valid_ids = {row["req_id"] for row in rows}
    evidence = collect_evidence(valid_ids)
    output_rows: list[dict[str, str]] = []

    for source in rows:
        req_id = source["req_id"]
        items = evidence.get(req_id, [])
        scope = "Mandatory"
        status = merged_status(items)
        disposition = ""

        if req_id in OUT_OF_RELEASE:
            scope = "Out of Release"
            status = "Deferred"
            disposition = OUT_OF_RELEASE[req_id]
        elif req_id in SUPERSEDED:
            scope = "N/A"
            status = "N/A"
            disposition = SUPERSEDED[req_id]
        elif not items:
            disposition = (
                "No explicit current implementation-traceability row found; "
                "kept Absent fail-closed."
            )

        refs = sorted({item["ref"] for item in items})
        qualification = {
            "Implemented": "AUTOMATION RECORDED / MANUAL GATE OPEN",
            "Partial": "NOT READY — CODE/EVIDENCE DELTA OPEN",
            "Absent": "NOT READY — IMPLEMENTATION EVIDENCE ABSENT",
            "Deferred": "OUT OF RELEASE — NEGATIVE ACCEPTANCE REQUIRED",
            "N/A": "N/A — APPROVED SUPERSESSION",
        }[status]

        output_rows.append(
            {
                "req_id": req_id,
                "release_scope": scope,
                "implementation_status": status,
                "qualification_status": qualification,
                "increment": source["increment"],
                "source_section": source["source_section"],
                "requirement": source["requirement"],
                "target_entity": source["target_entity"],
                "discovery_verdict": source["verdict"],
                "discovery_status": source["status"],
                "current_evidence_ref": "; ".join(refs),
                "current_evidence_summary": compact_details(items),
                "automated_acceptance": source["acceptance_criterion"],
                "manual_gate": MANUAL_GATES[source["increment"]],
                "owner_role": source["owner_role"],
                "disposition_note": disposition,
            }
        )

    fieldnames = list(output_rows[0])
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(output_rows)

    summary = Counter((row["release_scope"], row["implementation_status"]) for row in output_rows)
    return buffer.getvalue(), summary


def build(*, check: bool = False) -> Counter[tuple[str, str]]:
    content, summary = render_matrix()
    if check:
        if not OUTPUT.exists():
            raise SystemExit(f"Missing generated matrix: {OUTPUT}")
        current = OUTPUT.read_text(encoding="utf-8")
        if current != content:
            raise SystemExit(
                "12_release_scope_matrix_v1.csv is stale; run "
                "python scripts/build_release_scope_matrix.py"
            )
    else:
        OUTPUT.write_text(content, encoding="utf-8", newline="")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the versioned matrix differs from the deterministic output.",
    )
    args = parser.parse_args()
    summary = build(check=args.check)
    print(f"RELEASE_SCOPE_MATRIX={OUTPUT.relative_to(ROOT).as_posix()}")
    print("ROWS=557")
    for (scope, status), count in sorted(summary.items()):
        print(f"SUMMARY|{scope}|{status}|{count}")
    print("OK")
