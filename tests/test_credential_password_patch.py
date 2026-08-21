from __future__ import annotations

import unittest

from contract_accounting.patches.v0_20_0.migrate_credential_number_to_password import (
    CredentialPasswordMigrationError,
    migrate_rows,
)


class TestCredentialPasswordPatch(unittest.TestCase):
    def setUp(self) -> None:
        self.secrets: dict[str, str] = {}
        self.legacy: dict[str, str | None] = {}
        self.masks: dict[str, str | None] = {}

    def migrate(self, rows: list[tuple[str, str | None, str]]):
        self.legacy.update({name: value for name, value, _status in rows})
        return migrate_rows(
            rows,
            read_secret=self.secrets.get,
            write_secret=self.secrets.__setitem__,
            remove_secret=lambda name: self.secrets.pop(name, None),
            clear_legacy=lambda name: self.legacy.__setitem__(name, None),
            write_mask=self.masks.__setitem__,
        )

    def test_plaintext_is_encrypted_verified_masked_and_cleared(self) -> None:
        counts = self.migrate([("ROW-1", "LEGACY-12345678", "Active")])
        self.assertEqual(counts.migrated, 1)
        self.assertEqual(self.secrets["ROW-1"], "LEGACY-12345678")
        self.assertEqual(self.masks["ROW-1"], "••••5678")
        self.assertIsNone(self.legacy["ROW-1"])
        self.assertNotIn("LEGACY-12345678", repr(counts))

    def test_second_run_is_idempotent_and_count_only(self) -> None:
        self.secrets["ROW-1"] = "LEGACY-12345678"
        counts = self.migrate([("ROW-1", None, "Active")])
        self.assertEqual(counts.migrated, 0)
        self.assertEqual(counts.verified_existing, 1)
        self.assertEqual(self.masks["ROW-1"], "••••5678")
        self.assertEqual(
            set(counts.__dict__),
            {"examined", "migrated", "verified_existing", "metadata_purged"},
        )

    def test_password_placeholder_with_encrypted_secret_uses_existing_path(self) -> None:
        self.secrets["ROW-1"] = "ENCRYPTED-12345678"
        counts = self.migrate([("ROW-1", "******************", "Active")])
        self.assertEqual(counts.migrated, 0)
        self.assertEqual(counts.verified_existing, 1)
        self.assertIsNone(self.legacy["ROW-1"])
        self.assertEqual(self.masks["ROW-1"], "••••5678")

    def test_password_placeholder_without_encrypted_secret_fails_closed(self) -> None:
        with self.assertRaises(CredentialPasswordMigrationError) as raised:
            self.migrate([("ROW-1", "********", "Active")])
        self.assertEqual(self.legacy["ROW-1"], "********")
        self.assertIn("placeholder", str(raised.exception).lower())

    def test_conflicting_encrypted_value_fails_before_plaintext_clear(self) -> None:
        self.secrets["ROW-1"] = "DIFFERENT-SECRET"
        with self.assertRaises(CredentialPasswordMigrationError) as raised:
            self.migrate([("ROW-1", "LEGACY-12345678", "Active")])
        self.assertEqual(self.legacy["ROW-1"], "LEGACY-12345678")
        self.assertNotIn("LEGACY-12345678", str(raised.exception))
        self.assertNotIn("DIFFERENT-SECRET", str(raised.exception))

    def test_metadata_only_rows_purge_plaintext_encrypted_value_and_mask(self) -> None:
        self.secrets["ROW-1"] = "LEGACY-12345678"
        self.masks["ROW-1"] = "••••5678"
        counts = self.migrate([("ROW-1", "LEGACY-12345678", "Metadata Only")])
        self.assertEqual(counts.metadata_purged, 1)
        self.assertNotIn("ROW-1", self.secrets)
        self.assertIsNone(self.legacy["ROW-1"])
        self.assertIsNone(self.masks["ROW-1"])


if __name__ == "__main__":
    unittest.main()
