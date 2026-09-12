import unittest
import json
from pathlib import Path

from src.analysis.patch_optimizer import evaluate_agent_success_rate
from src.envs.attacker_env import MAX_NODES
from src.envs.defender_env import (
    DefenderEnv,
    decode_defender_action,
    encode_isolate,
    encode_patch,
)
from src.graph.cve_tagger import load_cve_database, tag_graph
from src.graph.topology_loader import load_topology


ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY = ROOT / "data" / "topologies" / "enterprise_20n.json"
CVE_DATA = ROOT / "data" / "cve" / "cve_dataset.json"


class FirstValidActionAgent:
    def predict(self, _obs, action_masks, deterministic=False):
        del deterministic
        valid = action_masks.nonzero()[0]
        return int(valid[0]), None


class SimulationCorrectnessTests(unittest.TestCase):
    def test_bundled_vulnerability_data_is_explicitly_synthetic(self):
        dataset = json.loads(CVE_DATA.read_text(encoding="utf-8"))
        self.assertEqual(dataset["dataset_type"], "synthetic_fixture")
        self.assertTrue(dataset["notice"])
        self.assertTrue(dataset["cves"])
        self.assertTrue(
            all(item["cve_id"].startswith("SYNTH-ONYX-") for item in dataset["cves"])
        )

    def test_patch_intervention_survives_evaluation(self):
        graph = load_topology(str(TOPOLOGY))
        cves = load_cve_database(str(CVE_DATA))
        tag_graph(graph, cves)
        node = next(item for item in graph.nodes if item.vulnerabilities)
        removed = node.vulnerabilities[0].cve_id
        node.vulnerabilities = [item for item in node.vulnerabilities if item.cve_id != removed]

        evaluate_agent_success_rate(
            FirstValidActionAgent(),
            graph,
            cves,
            n_episodes=1,
            episode_seeds=[12345],
        )

        self.assertNotIn(removed, [item.cve_id for item in node.vulnerabilities])

    def test_defender_mask_and_decoder_use_same_isolation_offset(self):
        env = DefenderEnv(str(TOPOLOGY), str(CVE_DATA), seed=42)
        env.reset()
        action = MAX_NODES

        self.assertTrue(env.action_masks()[action])
        self.assertEqual(decode_defender_action(action, env._n_real), ("isolate", 0))
        env._apply_defender_action(action)
        first_node = env._graph.get_node(env._node_order[0])
        self.assertTrue(first_node.is_isolated)

    def test_padded_defender_actions_are_rejected(self):
        with self.assertRaises(ValueError):
            decode_defender_action(30, 20)
        with self.assertRaises(ValueError):
            decode_defender_action(MAX_NODES + 20, 20)

    def test_action_codec_for_every_bundled_topology_size(self):
        for topology_name in (
            "small_office_10n.json",
            "enterprise_20n.json",
            "cloud_hybrid_30n.json",
        ):
            env = DefenderEnv(str(ROOT / "data" / "topologies" / topology_name), str(CVE_DATA))
            env.reset(seed=42)
            mask = env.action_masks()
            for index in range(env._n_real):
                self.assertEqual(decode_defender_action(encode_patch(index), env._n_real), ("patch", index))
                self.assertEqual(decode_defender_action(encode_isolate(index), env._n_real), ("isolate", index))
                self.assertTrue(mask[encode_isolate(index)])


if __name__ == "__main__":
    unittest.main()
