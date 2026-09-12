import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from web.backend import database
from web.backend.server import app


class DeviceEnrollmentApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "enrollment.db"
        self.db_patch = patch.object(database, "DB_PATH", self.db_path)
        self.env_patch = patch.dict(
            os.environ,
            {
                "ONYX_ADMIN_API_KEY": "admin-test-key",
                "ONYX_ORGANIZATION_ID": "pilot-org",
                "ONYX_ALLOW_LEGACY_SHARED_AGENT_KEY": "false",
            },
        )
        self.db_patch.start()
        self.env_patch.start()
        database.init_db()
        self.client = TestClient(app)

    def tearDown(self):
        self.env_patch.stop()
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_one_time_token_binds_and_revokes_device_identity(self):
        issued = self.client.post(
            "/api/device-enrollment/tokens",
            headers={"Authorization": "Bearer admin-test-key"},
            json={"allowed_platform": "Windows", "expires_in_minutes": 15},
        )
        self.assertEqual(issued.status_code, 200)
        token = issued.json()["enrollment_token"]
        exchanged = self.client.post(
            "/api/device-enrollment/exchange",
            json={"enrollment_token": token, "endpoint_id": "office-1", "platform": "Windows"},
        )
        self.assertEqual(exchanged.status_code, 200)
        credential = exchanged.json()["device_credential"]
        reused = self.client.post(
            "/api/device-enrollment/exchange",
            json={"enrollment_token": token, "endpoint_id": "office-2", "platform": "Windows"},
        )
        self.assertEqual(reused.status_code, 401)
        heartbeat_payload = {
            "endpoint_id": "office-1", "hostname": "OFFICE-1",
            "topology": "enterprise_20n", "agent_version": "2.0.0", "platform": "Windows",
        }
        heartbeat = self.client.post(
            "/api/endpoints/heartbeat",
            headers={"Authorization": f"Bearer {credential}"}, json=heartbeat_payload,
        )
        self.assertEqual(heartbeat.status_code, 200)
        impersonation = self.client.post(
            "/api/endpoints/heartbeat",
            headers={"Authorization": f"Bearer {credential}"},
            json={**heartbeat_payload, "endpoint_id": "office-2"},
        )
        self.assertEqual(impersonation.status_code, 401)
        revoked = self.client.post(
            "/api/devices/office-1/revoke",
            headers={"Authorization": "Bearer admin-test-key"},
        )
        self.assertEqual(revoked.status_code, 200)
        denied = self.client.post(
            "/api/endpoints/heartbeat",
            headers={"Authorization": f"Bearer {credential}"}, json=heartbeat_payload,
        )
        self.assertEqual(denied.status_code, 401)


if __name__ == "__main__":
    unittest.main()
