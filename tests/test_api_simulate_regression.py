import builtins
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from web.backend.server import app


class SimulateApiRegressionTests(unittest.TestCase):
    def test_simulate_endpoint_handles_missing_attacker_env_import(self):
        client = TestClient(app)
        original_import = builtins.__import__

        def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "src.envs.attacker_env":
                raise ModuleNotFoundError("No module named 'gymnasium'")
            return original_import(name, globals, locals, fromlist, level)

        payload = {
            "topology": "enterprise_20n",
            "n_episodes": 100,
            "data_source": "hybrid",
            "telemetry_weight": 0.4,
        }

        with patch("builtins.__import__", side_effect=guarded_import):
            response = client.post("/api/simulate", json=payload)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("success_rate", data)
        self.assertIn("summary", data)


if __name__ == "__main__":
    unittest.main()
