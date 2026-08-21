"""Standalone checks for the immutable FR-05 policy rules."""

from __future__ import annotations

import unittest
from datetime import date, datetime

from contract_accounting.domain.privacy import (
    POLICY_HASH,
    POLICY_REFERENCE,
    PrivacyRuleError,
    break_glass_expiry,
    credential_readiness,
    mask_credential_number,
    retention_due,
    validate_break_glass_minutes,
    validate_policy_stamp,
)


class PrivacyPolicyTest(unittest.TestCase):
    def test_policy_stamp_and_mask_are_exact(self) -> None:
        validate_policy_stamp(POLICY_REFERENCE, POLICY_HASH)
        with self.assertRaises(PrivacyRuleError):
            validate_policy_stamp(POLICY_REFERENCE, "altered")
        self.assertEqual(mask_credential_number("AB-123456"), "••••3456")
        self.assertEqual(mask_credential_number("7"), "••••7")
        self.assertIsNone(mask_credential_number(None))

    def test_credential_readiness_is_fail_closed(self) -> None:
        today = date(2026, 8, 19)
        self.assertEqual(
            credential_readiness(
                status="Verified",
                data_owner_verified=True,
                applicability_verified=True,
                expires_on=date(2026, 8, 20),
                no_expiry=False,
                as_of=today,
            ),
            "Ready",
        )
        self.assertEqual(
            credential_readiness(
                status="Verified",
                data_owner_verified=True,
                applicability_verified=False,
                expires_on=None,
                no_expiry=True,
                as_of=today,
            ),
            "Pending Verification",
        )
        self.assertEqual(
            credential_readiness(
                status="Verified",
                data_owner_verified=True,
                applicability_verified=True,
                expires_on=date(2026, 8, 18),
                no_expiry=False,
                as_of=today,
            ),
            "Expired",
        )

    def test_break_glass_and_retention_boundaries(self) -> None:
        activated = datetime(2026, 8, 19, 10, 0)
        self.assertEqual(break_glass_expiry(activated, 240), datetime(2026, 8, 19, 14, 0))
        with self.assertRaises(PrivacyRuleError):
            validate_break_glass_minutes(241)
        due = retention_due(base_date=date(2023, 8, 21), as_of=date(2026, 8, 19))
        self.assertTrue(due.contact)
        self.assertTrue(due.attachment)
        self.assertFalse(due.metadata)
        leap = retention_due(base_date=date(2024, 2, 29), as_of=date(2025, 2, 28))
        self.assertTrue(leap.attachment)
        self.assertFalse(leap.metadata)


if __name__ == "__main__":
    unittest.main()
