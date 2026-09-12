import builtins
import unittest
from pathlib import Path
from unittest.mock import patch

from src.analysis.attack_path_analyzer import analyze_attack_paths


class AttackPathAnalyzerRegressionTests(unittest.TestCase):
    def test_no_attacker_env_import_when_agent_is_missing(self):
        repo_root = Path(__file__).resolve().parents[1]
        topology_path = repo_root / "data" / "topologies" / "enterprise_20n.json"
        cve_path = repo_root / "data" / "cve" / "cve_dataset.json"

        original_import = builtins.__import__

        def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "src.envs.attacker_env":
                raise ModuleNotFoundError("No module named 'gymnasium'")
            return original_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=guarded_import):
            result = analyze_attack_paths(
                topology_path=str(topology_path),
                cve_path=str(cve_path),
                agent_path=None,
                n_episodes=1,
                seed=42,
            )

        self.assertIn("success_rate", result)
        self.assertIn("top_paths", result)
        self.assertEqual(result["n_episodes"], 1)


if __name__ == "__main__":
    unittest.main()
