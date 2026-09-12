import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from web.backend import database
from web.backend import server
from web.backend.server import app


class EndpointResponseApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "endpoint-response.db"
        self.db_patch = patch.object(database, "DB_PATH", self.db_path)
        self.root_patch = patch.object(server, "PROJECT_ROOT", Path(self.temp_dir.name))
        self.env_patch = patch.dict(
            os.environ,
            {
                "ONYX_TELEMETRY_INGEST_API_KEY": "agent-test-key",
                "ONYX_RESPONSE_API_KEY": "response-test-key",
            },
        )
        self.db_patch.start()
        self.root_patch.start()
        self.env_patch.start()
        database.init_db()
        self.client = TestClient(app)

    def tearDown(self):
        self.env_patch.stop()
        self.root_patch.stop()
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_detection_and_acknowledged_quarantine_lifecycle(self):
        agent_headers = {"Authorization": "Bearer agent-test-key"}
        heartbeat = self.client.post(
            "/api/endpoints/heartbeat",
            headers=agent_headers,
            json={
                "endpoint_id": "judge-laptop-1",
                "hostname": "JUDGE-LAPTOP-1",
                "ip_address": "192.168.1.51",
                "topology": "enterprise_20n",
                "agent_version": "2.0.0",
                "platform": "Windows",
                "quarantined": False,
            },
        )
        self.assertEqual(heartbeat.status_code, 200)

        detection = self.client.post(
            "/api/telemetry/ingest",
            headers=agent_headers,
            json={
                "source": "windows-defender",
                "topology": "enterprise_20n",
                "events": [
                    {
                        "event_id": "defender-42-1116",
                        "timestamp": "2026-09-06T10:00:00Z",
                        "source_node": "judge-laptop-1",
                        "target_node": "judge-laptop-1",
                        "event_type": "malware_detected",
                        "confidence": 1.0,
                        "blocked": False,
                        "reached_critical": False,
                        "raw": {
                            "provider": "Microsoft-Windows-Windows Defender",
                            "windows_event_id": 1116,
                            "threat_name": "Test threat",
                        },
                    }
                ],
            },
        )
        self.assertEqual(detection.status_code, 200)
        self.assertEqual(detection.json()["ingested"], 1)

        command_response = self.client.post(
            "/api/endpoints/judge-laptop-1/commands",
            headers={"Authorization": "Bearer response-test-key"},
            json={
                "action": "quarantine",
                "reason": "Confirmed Defender detection",
                "requested_by": "security_architect",
                "protected_ports": [445, 3389],
            },
        )
        self.assertEqual(command_response.status_code, 200)
        command_id = command_response.json()["command"]["command_id"]

        pending = self.client.get(
            "/api/endpoints/judge-laptop-1/commands/pending",
            headers=agent_headers,
        )
        self.assertEqual(pending.status_code, 200)
        self.assertEqual(pending.json()["commands"][0]["command_id"], command_id)

        acknowledgement = self.client.post(
            f"/api/endpoints/judge-laptop-1/commands/{command_id}/ack",
            headers=agent_headers,
            json={
                "status": "succeeded",
                "quarantined": True,
                "result": {"firewall_group": "Onyx Endpoint Quarantine"},
            },
        )
        self.assertEqual(acknowledgement.status_code, 200)

        inventory = self.client.get("/api/endpoints?topology=enterprise_20n")
        self.assertEqual(inventory.status_code, 200)
        endpoint = inventory.json()["endpoints"][0]
        self.assertTrue(endpoint["quarantined"])
        self.assertEqual(endpoint["threat_count"], 1)
        self.assertEqual(endpoint["latest_command"]["status"], "succeeded")

    def test_sensitive_routes_fail_closed(self):
        unauthorized_heartbeat = self.client.post(
            "/api/endpoints/heartbeat",
            json={
                "endpoint_id": "judge-laptop-2",
                "hostname": "JUDGE-LAPTOP-2",
                "topology": "enterprise_20n",
                "agent_version": "2.0.0",
            },
        )
        self.assertEqual(unauthorized_heartbeat.status_code, 401)


if __name__ == "__main__":
    unittest.main()
