"""Standalone fail-closed contract tests for the full demo/UAT manifest."""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
import re
import unittest
from collections import defaultdict, deque
from pathlib import Path

from contract_accounting.demo_uat import reset as reset_module
from contract_accounting.demo_uat.manifest import (
    INSTALL_CONFIRMATION_TOKEN,
    MANIFEST_PATH,
    RESET_CONFIRMATION_TOKEN,
    VERIFY_CONFIRMATION_TOKEN,
    compute_manifest_sha256,
    expected_count_summary,
    expected_link_rows,
    expected_link_summary,
    load_manifest,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROJECT_GRAPH_POLICY = (
    REPOSITORY_ROOT / "contract_accounting" / "infrastructure" / "project_graph_permissions.py"
)
EXPECTED_BINDINGS = {
    "company": "Company",
    "customer": "Customer",
    "currency": "Currency",
    "own_address": "Address",
    "foreign_address": "Address",
    "own_engineer_user": "User",
    "foreign_engineer_user": "User",
    "own_supplier": "Supplier",
    "foreign_supplier": "Supplier",
    "process_template": "Ferum Process Template",
    "stage_template": "Ferum Stage Template",
    "step_template": "Ferum Step Template",
}
EXPECTED_DOCTYPE_COUNTS = {
    "Ferum Billing Cycle": 2,
    "Ferum Contract Obligation": 2,
    "Ferum Contract Requirement": 2,
    "Ferum Contractor Assignment": 2,
    "Ferum Contractor Worker": 2,
    "Ferum Finding": 2,
    "Ferum Inspection": 2,
    "Ferum Maintenance Schedule": 2,
    "Ferum Maintenance Visit": 2,
    "Ferum Material Expense": 2,
    "Ferum Object System": 2,
    "Ferum Personnel Credential": 2,
    "Ferum Photo Evidence": 2,
    "Ferum Process Evidence": 2,
    "Ferum Project Document": 4,
    "Ferum Project Document Event": 2,
    "Ferum Project Object": 2,
    "Ferum Project Process": 2,
    "Ferum Project Process Step": 2,
    "Ferum Project Stage": 2,
    "Ferum Service Object": 2,
    "Ferum Service Project": 2,
    "Ferum Service Request": 2,
    "Ferum Stage Gate": 2,
}
EXPECTED_UNSUPPORTED_AREAS = {
    "human UAT and sign-off",
    "production activation and deployment",
    "performance race and representative load",
    "backup restore rollback and disaster recovery",
}
EXPECTED_LIFECYCLE_STEPS = [
    "activate contractor worker through privacy command",
    "verify credential through privacy command",
    "approve contractor assignment through assignment command",
    "revoke credential through privacy command",
    "recompute readiness and suspend assignment fail-closed",
]


def _policy_string_set(assignment_name: str) -> set[str]:
    tree = ast.parse(PROJECT_GRAPH_POLICY.read_text(encoding="utf-8"))
    for node in tree.body:
        target = node.target if isinstance(node, ast.AnnAssign) else None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == assignment_name:
            return {
                child.value
                for child in ast.walk(node.value)
                if isinstance(child, ast.Constant) and isinstance(child.value, str)
            }
    raise AssertionError(f"policy assignment not found: {assignment_name}")


class DemoUATManifestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_manifest()
        cls.entities = cls.manifest["entities"]
        cls.by_id = {row["external_id"]: row for row in cls.entities}

    def test_canonical_sha_is_current_and_stable(self) -> None:
        declared = self.manifest["integrity"]["canonical_sha256"]
        self.assertRegex(declared, r"^[0-9a-f]{64}$")
        self.assertEqual(declared, compute_manifest_sha256(self.manifest))
        reparsed = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertEqual(declared, compute_manifest_sha256(reparsed))

    def test_two_isolated_connected_full_project_graphs(self) -> None:
        self.assertEqual({row["key"] for row in self.manifest["projects"]}, {"own", "foreign"})
        adjacency: dict[str, set[str]] = defaultdict(set)
        for link in expected_link_rows(self.entities):
            source, target = link["from"], link["to"]
            self.assertEqual(
                self.by_id[source]["project_key"],
                self.by_id[target]["project_key"],
                f"cross-project link: {link}",
            )
            adjacency[source].add(target)
            adjacency[target].add(source)
        for project in self.manifest["projects"]:
            members = {
                row["external_id"] for row in self.entities if row["project_key"] == project["key"]
            }
            visited = {project["root_external_id"]}
            queue = deque(visited)
            while queue:
                node = queue.popleft()
                for neighbor in adjacency[node] - visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
            self.assertEqual(members, visited)
            self.assertEqual(25, len(members))

    def test_exact_counts_links_and_unique_names(self) -> None:
        external_ids = [row["external_id"] for row in self.entities]
        record_keys = [(row["doctype"], row["record_name"]) for row in self.entities]
        self.assertEqual(len(external_ids), len(set(external_ids)))
        self.assertEqual(len(record_keys), len(set(record_keys)))
        self.assertEqual(50, len(self.entities))
        self.assertTrue(all(row["seed_support"] == "supported" for row in self.entities))
        self.assertEqual(
            {"by_project": {"foreign": 25, "own": 25}, "by_doctype": EXPECTED_DOCTYPE_COUNTS},
            expected_count_summary(self.entities),
        )
        self.assertEqual(self.manifest["expected"]["counts"], expected_count_summary(self.entities))
        self.assertEqual(self.manifest["expected"]["links"], expected_link_summary(self.entities))
        self.assertEqual(146, self.manifest["expected"]["links"]["count"])
        self.assertEqual(0, self.manifest["expected"]["links"]["cross_project_count"])

    def test_all_twenty_acl_surfaces_match_policy_source_and_both_projects(self) -> None:
        direct = _policy_string_set("DIRECT_PROJECT_DOCTYPES")
        indirect = _policy_string_set("INDIRECT_PROJECT_DOCTYPES")
        policy_surfaces = direct | indirect | {"Ferum Service Project"}
        self.assertEqual(15, len(direct))
        self.assertEqual(4, len(indirect))
        self.assertEqual(20, len(policy_surfaces))
        self.assertEqual(policy_surfaces, set(self.manifest["business_graph"]["acl_surfaces"]))
        for project_key in ("own", "foreign"):
            actual = {row["doctype"] for row in self.entities if row["project_key"] == project_key}
            self.assertTrue(
                policy_surfaces.issubset(actual), f"ACL coverage drift for {project_key}"
            )

    def test_process_evidence_and_documentary_billing_are_explicit(self) -> None:
        billing = self.manifest["business_graph"]["documentary_billing"]
        self.assertEqual("not performed and not qualified", billing["accounting_posting"])
        self.assertEqual(
            {"Sales Invoice submitted", "GL Entry posted", "payment reconciled"},
            set(billing["forbidden_claims"]),
        )
        self.assertFalse(
            {"Sales Invoice", "Purchase Invoice", "Payment Entry", "GL Entry"}
            & {row["doctype"] for row in self.entities}
        )
        for project_key in ("own", "foreign"):
            process = self.by_id[f"ca.demo.v1.{project_key}.project_process"]
            step = self.by_id[f"ca.demo.v1.{project_key}.process_step"]
            evidence = self.by_id[f"ca.demo.v1.{project_key}.process_evidence"]
            cycle = self.by_id[f"ca.demo.v1.{project_key}.billing_cycle"]
            document = self.by_id[f"ca.demo.v1.{project_key}.billing_document"]
            self.assertEqual("Period Closing", process["values"]["process_type"])
            self.assertEqual({"$ref": process["external_id"]}, step["values"]["project_process"])
            self.assertEqual({"$ref": step["external_id"]}, evidence["values"]["process_step"])
            self.assertEqual("Manual Confirmation", evidence["values"]["evidence_type"])
            self.assertRegex(evidence["values"]["content_hash"], r"^[0-9a-f]{64}$")
            self.assertEqual({"$ref": process["external_id"]}, cycle["values"]["project_process"])
            self.assertEqual("Draft", document["values"]["status"])
            self.assertIn(document["values"]["document_type"], {"Act", "UPD"})

    def test_binary_fixtures_are_private_deterministic_and_wired_to_photo_evidence(self) -> None:
        fixtures = self.manifest["business_graph"]["binary_fixtures"]
        self.assertEqual({"own", "foreign"}, {row["project_key"] for row in fixtures})
        self.assertEqual(2, len(fixtures))
        for fixture in fixtures:
            payload = fixture["content_literal"].encode("utf-8")
            self.assertEqual(hashlib.sha256(payload).hexdigest(), fixture["content_sha256"])
            self.assertEqual(
                hashlib.md5(payload, usedforsecurity=False).hexdigest(),
                fixture["frappe_content_hash_md5"],
            )
            self.assertEqual(1, fixture["is_private"])
            self.assertEqual("bootstrap-owned prerequisite", fixture["materialization"])
            project_key = fixture["project_key"]
            self.assertEqual(
                f"ca.demo.v1.{project_key}.inspection", fixture["attached_to_external_id"]
            )
            photo = self.by_id[f"ca.demo.v1.{project_key}.photo_evidence"]
            self.assertEqual(fixture["record_name"], photo["values"]["file"])
            self.assertEqual(fixture["frappe_content_hash_md5"], photo["values"]["content_hash"])
        self.assertFalse(any(row["doctype"] == "File" for row in self.entities))

    def test_contractor_credential_privacy_and_revocation_scenarios_are_exact(self) -> None:
        scenarios = self.manifest["business_graph"]["typed_lifecycle_scenarios"]
        self.assertEqual({"own", "foreign"}, {row["project_key"] for row in scenarios})
        for scenario in scenarios:
            self.assertEqual(EXPECTED_LIFECYCLE_STEPS, scenario["steps"])
            self.assertTrue(scenario["manual_gate"])
            self.assertEqual(
                "assignment suspended and credential revoked", scenario["expected_terminal_state"]
            )
            key = scenario["project_key"]
            worker = self.by_id[f"ca.demo.v1.{key}.contractor_worker"]
            credential = self.by_id[f"ca.demo.v1.{key}.credential"]
            assignment = self.by_id[f"ca.demo.v1.{key}.contractor_assignment"]
            self.assertEqual("Inactive", worker["values"]["status"])
            self.assertEqual("Draft", credential["values"]["verification_status"])
            self.assertEqual({"$ref": worker["external_id"]}, credential["values"]["holder"])
            self.assertEqual(
                {"$ref": worker["external_id"]}, assignment["values"]["contractor_worker"]
            )
            self.assertEqual("Draft", assignment["values"]["status"])
            self.assertEqual("Pending Verification", assignment["values"]["credentials_readiness"])

    def test_manifest_contains_no_literal_personal_data_and_bindings_are_exact(self) -> None:
        text = MANIFEST_PATH.read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", text, re.I))
        self.assertIsNone(re.search(r"(?:\+7[\s(-]+|8[\s(-]+)\d{3}[\s()-]*\d{3}", text))
        self.assertIsNone(re.search(r"\b\d{3}-\d{3}-\d{3} \d{2}\b", text))
        self.assertIsNone(re.search(r"\b\d{4}\s+\d{6}\b", text))
        self.assertNotIn("@example.", text.lower())
        self.assertEqual(
            EXPECTED_BINDINGS,
            {key: row["doctype"] for key, row in self.manifest["required_bindings"].items()},
        )
        for binding in self.manifest["required_bindings"].values():
            self.assertEqual(set(binding), {"doctype", "required_roles", "customer_binding"})

    def test_confirmation_tokens_and_reset_default_are_exact(self) -> None:
        self.assertEqual(
            self.manifest["confirmation_tokens"],
            {
                "install": INSTALL_CONFIRMATION_TOKEN,
                "verify": VERIFY_CONFIRMATION_TOKEN,
                "reset": RESET_CONFIRMATION_TOKEN,
            },
        )
        self.assertEqual(3, len(set(self.manifest["confirmation_tokens"].values())))
        signature = inspect.signature(reset_module.reset)
        self.assertIs(signature.parameters["dry_run"].default, True)

    def test_reset_bypasses_only_explicit_guarded_custom_doctypes(self) -> None:
        bypass = reset_module._GUARDED_CUSTOM_DELETE_BYPASS
        self.assertTrue(bypass)
        self.assertTrue(all(doctype.startswith("Ferum ") for doctype in bypass))
        self.assertTrue(
            {
                "Company",
                "User",
                "Customer",
                "Supplier",
                "Address",
                "Currency",
                "Account",
                "Warehouse",
                "Cost Center",
                "Department",
                "User Permission",
                "ToDo",
                "DocShare",
                "Token",
                "Token Cache",
            }.isdisjoint(bypass)
        )

    def test_readme_uses_canonical_binding_free_smoke_commands(self) -> None:
        readme = (REPOSITORY_ROOT / "contract_accounting" / "demo_uat" / "README.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("contract_accounting.demo_uat.installer.install", readme)
        self.assertIn('"confirmation_token":"INSTALL_CONTRACT_ACCOUNTING_DEMO_UAT_V1"', readme)
        self.assertNotIn('"bindings"', readme)
        self.assertNotIn('"dry_run":false', readme)
        self.assertIn('"dry_run":False', readme)
        self.assertGreaterEqual(readme.count("contract_accounting.demo_uat.reset.reset"), 3)

    def test_qualification_and_unsupported_boundaries_are_exact(self) -> None:
        self.assertEqual(
            "FULL_SYNTHETIC_GRAPH_MANUAL_UAT_REQUIRED",
            self.manifest["qualification_status"],
        )
        self.assertEqual(
            EXPECTED_UNSUPPORTED_AREAS,
            {row["area"] for row in self.manifest["unsupported"]},
        )
        self.assertEqual(4, len(self.manifest["unsupported"]))
        self.assertTrue(all(row["manual_gate"] for row in self.manifest["role_scenarios"]))
        self.assertNotIn("PASS", self.manifest["qualification_status"])
        self.assertNotIn("READY", self.manifest["qualification_status"])


if __name__ == "__main__":
    unittest.main()
