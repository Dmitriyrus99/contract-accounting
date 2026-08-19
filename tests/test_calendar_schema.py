from __future__ import annotations

import json
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCTYPE_ROOT = ROOT / "contract_accounting" / "contract_accounting" / "doctype"
FIXTURE = ROOT / "contract_accounting" / "setup" / "calendar_fixtures" / "ru_5d_2026_v1.json"


def schema(name: str) -> dict[str, object]:
    return json.loads((DOCTYPE_ROOT / name / f"{name}.json").read_text(encoding="utf-8"))


def fields(document: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        field["fieldname"]: field
        for field in document["fields"]  # type: ignore[index,union-attr]
    }


class TestProductionCalendarSchema(unittest.TestCase):
    def test_official_2026_fixture_has_exact_counts_and_sources(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        exceptions = {row["calendar_date"]: row for row in fixture["days"]}
        current = date(2026, 1, 1)
        working = 0
        nonworking = 0
        while current <= date(2026, 12, 31):
            row = exceptions.get(current.isoformat())
            is_holiday = bool(row and row["day_type"] == "Holiday")
            if not is_holiday and current.weekday() not in {5, 6}:
                working += 1
            else:
                nonworking += 1
            current += timedelta(days=1)
        shortened = sum(row["day_type"] == "Shortened" for row in fixture["days"])
        self.assertEqual((working, nonworking, shortened), (247, 118, 4))
        self.assertEqual(fixture["timezone"], "Europe/Moscow")
        self.assertEqual(fixture["work_start_time"], "08:00:00")
        self.assertEqual(fixture["cutoff_time"], "19:00:00")
        self.assertIn("publication.pravo.gov.ru", fixture["source_url"])
        self.assertIn("1466", fixture["source_document"])

    def test_calendar_revision_and_assignment_are_immutable_typed_models(self) -> None:
        revision = fields(schema("ferum_calendar_revision"))
        assignment = fields(schema("ferum_calendar_assignment"))
        self.assertEqual(revision["days"]["options"], "Ferum Calendar Day")
        self.assertEqual(revision["calendar_hash"]["read_only"], 1)
        self.assertEqual(assignment["calendar_revision"]["read_only"], 1)
        self.assertEqual(assignment["contract_basis"]["read_only"], 1)
        source = (ROOT / "contract_accounting" / "api" / "calendars.py").read_text(encoding="utf-8")
        self.assertGreaterEqual(source.count('@frappe.whitelist(methods=["POST"])'), 4)
        self.assertIn("CALENDAR_ASSIGNMENT_WRITE_FLAG", source)

    def test_signature_and_customer_response_have_primary_source_fields(self) -> None:
        document = fields(schema("ferum_project_document"))
        dependency = fields(schema("ferum_external_dependency"))
        self.assertEqual(document["signature_due_at"]["fieldtype"], "Datetime")
        self.assertEqual(
            document["signature_deadline_calculation"]["options"],
            "Ferum Deadline Calculation",
        )
        self.assertEqual(dependency["due_at"]["fieldtype"], "Datetime")
        self.assertEqual(dependency["customer"]["options"], "Customer")
        self.assertEqual(dependency["contact"]["options"], "Contact")
        self.assertEqual(dependency["sent_evidence"]["options"], "File")

    def test_calculation_event_is_append_only_and_full_snapshot_is_persisted(self) -> None:
        calculation = fields(schema("ferum_deadline_calculation"))
        for fieldname in (
            "calendar_assignment",
            "calendar_revision",
            "calendar_hash",
            "calendar_snapshot_json",
            "algorithm_version",
            "calculation_hash",
            "reason",
            "actor",
        ):
            self.assertEqual(calculation[fieldname]["read_only"], 1)
        controller = (
            DOCTYPE_ROOT / "ferum_deadline_calculation" / "ferum_deadline_calculation.py"
        ).read_text(encoding="utf-8")
        self.assertIn("Deadline Calculation неизменяема", controller)
        self.assertIn("Удаление Deadline Calculation запрещено", controller)


if __name__ == "__main__":
    unittest.main()
