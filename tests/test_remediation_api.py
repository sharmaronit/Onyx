import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from web.backend import database, server
from web.backend.server import app


class RemediationApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "remediation.db"
        self.db_patch = patch.object(database, "DB_PATH", self.db_path)
        self.env_patch = patch.dict(
            os.environ,
            {"ONYX_ADMIN_API_KEY": "admin-test-key", "ONYX_ORGANIZATION_ID": "pilot-org"},
        )
        self.db_patch.start()
        self.env_patch.start()
        database.init_db()
        database.upsert_endpoint_heartbeat({
            "endpoint_id": "office-1", "hostname": "OFFICE-1",
            "topology": "enterprise_20n", "agent_version": "2.0.0",
        })
        database.upsert_vulnerability_findings("enterprise_20n", [{
            "endpoint_id": "office-1", "finding_id": "finding-1",
            "cve_id": "CVE-2026-1234", "title": "Scanner finding",
            "cvss_score": 8.1, "fix_available": True, "source": "test-scanner",
            "evidence": {"source_url": "https://scanner.invalid/finding-1"},
        }])
        self.client = TestClient(app)
        self.headers = {"Authorization": "Bearer admin-test-key"}

    def tearDown(self):
        self.env_patch.stop()
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_work_is_assigned_and_cannot_be_verified_without_evidence(self):
        unauthorized = self.client.get("/api/remediation/actions")
        self.assertEqual(unauthorized.status_code, 401)
        created = self.client.post(
            "/api/remediation/actions", headers=self.headers,
            json={
                "finding_id": "finding-1", "endpoint_id": "office-1",
                "title": "Upgrade affected package", "recommendation": "Deploy the approved update",
                "owner": "it-admin@example.test", "due_date": "2026-09-20", "priority": "high",
            },
        )
        self.assertEqual(created.status_code, 200)
        action_id = created.json()["action"]["action_id"]
        for state in ("accepted", "in_progress", "awaiting_verification"):
            changed = self.client.put(
                f"/api/remediation/actions/{action_id}", headers=self.headers, json={"state": state}
            )
            self.assertEqual(changed.status_code, 200)
        rejected = self.client.put(
            f"/api/remediation/actions/{action_id}", headers=self.headers, json={"state": "verified"}
        )
        self.assertEqual(rejected.status_code, 422)
        verified = self.client.put(
            f"/api/remediation/actions/{action_id}", headers=self.headers,
            json={"state": "verified", "verification": {
                "source": "follow-up scan", "timestamp": "2026-09-12T12:00:00Z",
                "observation": "Finding absent", "reviewer": "pilot-administrator",
            }},
        )
        self.assertEqual(verified.status_code, 200)
        self.assertEqual(verified.json()["action"]["state"], "verified")
        exported = self.client.get("/api/remediation/actions.csv", headers=self.headers)
        self.assertEqual(exported.status_code, 200)
        self.assertIn(action_id, exported.text)


if __name__ == "__main__":
    unittest.main()
