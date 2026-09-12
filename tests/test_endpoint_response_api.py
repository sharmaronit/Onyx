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
                "ONYX_RESPONSE_CONTROLS_ENABLED": "true",
                "ONYX_ALLOW_LEGACY_SHARED_AGENT_KEY": "true",
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
                "metadata": {"response_capable": True},
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
        self.assertEqual(endpoint["open_incident_count"], 1)

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

    def test_response_controls_are_disabled_by_default(self):
        with patch.dict(os.environ, {"ONYX_RESPONSE_CONTROLS_ENABLED": "false"}):
            response = self.client.post(
                "/api/endpoints/unknown/commands?mode=demo",
                json={
                    "action": "quarantine",
                    "reason": "test safe default",
                    "requested_by": "security_architect",
                },
            )
        self.assertEqual(response.status_code, 403)

    def test_expired_command_lease_is_reclaimed_and_ack_is_idempotent(self):
        agent_headers = {"Authorization": "Bearer agent-test-key"}
        self.client.post(
            "/api/endpoints/heartbeat",
            headers=agent_headers,
            json={
                "endpoint_id": "lease-laptop",
                "hostname": "LEASE-LAPTOP",
                "topology": "enterprise_20n",
                "agent_version": "2.0.0",
            },
        )
        created = database.create_response_command(
            "cmd-lease", "lease-laptop", "quarantine", "lease test", "test", {}
        )
        self.assertEqual(created["status"], "pending")
        first = database.claim_pending_commands("lease-laptop", lease_seconds=10)
        self.assertEqual(first[0]["attempt_count"], 1)
        self.assertEqual(database.claim_pending_commands("lease-laptop"), [])
        with database.sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE response_commands SET lease_expires_at=datetime('now', '-1 second') "
                "WHERE command_id='cmd-lease'"
            )
        second = database.claim_pending_commands("lease-laptop")
        self.assertEqual(second[0]["attempt_count"], 2)
        completed = database.complete_response_command(
            "cmd-lease", "lease-laptop", "succeeded", {"ok": True}, None, True
        )
        retried = database.complete_response_command(
            "cmd-lease", "lease-laptop", "succeeded", {"ok": True}, None, True
        )
        self.assertEqual(completed["status"], "succeeded")
        self.assertEqual(retried["status"], "succeeded")


if __name__ == "__main__":
    unittest.main()
