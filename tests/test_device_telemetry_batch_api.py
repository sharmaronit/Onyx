import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from web.backend import database
from web.backend.server import app


class DeviceTelemetryBatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.db = Path(self.temp.name) / "test.db"
        self.db_patch = patch.object(database, "DB_PATH", self.db); self.db_patch.start()
        self.env = patch.dict(os.environ, {"ONYX_ADMIN_API_KEY": "admin", "ONYX_ORGANIZATION_ID": "org-a", "ONYX_ALLOW_LEGACY_SHARED_AGENT_KEY": "false"}); self.env.start()
        database.init_db(); self.client = TestClient(app)
        token = self.client.post("/api/device-enrollment/tokens", headers={"Authorization":"Bearer admin"}, json={"allowed_platform":"Windows"}).json()["enrollment_token"]
        self.credential = self.client.post("/api/device-enrollment/exchange", json={"enrollment_token":token,"endpoint_id":"agent-1","platform":"Windows"}).json()["device_credential"]

    def tearDown(self): self.env.stop(); self.db_patch.stop(); self.temp.cleanup()

    def test_batch_is_device_bound_and_idempotent(self):
        headers = {"Authorization": f"Bearer {self.credential}"}
        payload = {"batch_id":"batch-12345678", "events":[{"event_id":"defender-1","event_type":"malware_detected","source_node":"forged"}]}
        first = self.client.post("/api/devices/agent-1/telemetry/batches", headers=headers, json=payload)
        self.assertEqual(first.status_code, 200); self.assertFalse(first.json()["duplicate"])
        again = self.client.post("/api/devices/agent-1/telemetry/batches", headers=headers, json=payload)
        self.assertTrue(again.json()["duplicate"])
        other = self.client.post("/api/devices/agent-2/telemetry/batches", headers=headers, json=payload)
        self.assertEqual(other.status_code, 401)
        rows = database.get_telemetry_events("enterprise_20n", organization_id="org-a")
        self.assertEqual(rows[0]["source_node"], "agent-1")

    def test_rotation_invalidates_previous_credential(self):
        headers = {"Authorization": f"Bearer {self.credential}"}
        rotated = self.client.post("/api/devices/agent-1/rotate-credential", headers=headers, json={"reason":"test rotation"})
        self.assertEqual(rotated.status_code, 200)
        old = self.client.get("/api/devices/agent-1/configuration", headers=headers)
        self.assertEqual(old.status_code, 401)

if __name__ == "__main__": unittest.main()
