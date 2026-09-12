# 🧪 Onyx — Comprehensive Test Plan

> **Purpose:** Verify the correctness of every layer of the Onyx platform — from low-level data structures to full integration with trained models and the web API.
>
> **Run context:** All tests assume `cd D:\Onyx`, the `.venv` activated, and `requirements.txt` + `web/backend/requirements.txt` installed.
>
> **Notation:**  
> ✅ = expected pass &nbsp; ⚠️ = may vary by environment &nbsp; 🔴 = known limitation

---

## Table of Contents

1. [Layer 0 — Data Structures & Constants](#layer-0--data-structures--constants)
2. [Layer 1 — Graph Module](#layer-1--graph-module)
3. [Layer 2 — PyG Converter](#layer-2--pyg-converter)
4. [Layer 3 — Rule-Based Simulator](#layer-3--rule-based-simulator)
5. [Layer 4 — Episode Generator & HDF5 Dataset](#layer-4--episode-generator--hdf5-dataset)
6. [Layer 5 — GNN World Model (Architecture)](#layer-5--gnn-world-model-architecture)
7. [Layer 6 — GNN World Model (Trained Checkpoint)](#layer-6--gnn-world-model-trained-checkpoint)
8. [Layer 7 — Transition Model Interface](#layer-7--transition-model-interface)
9. [Layer 8 — Attacker Environment (Red)](#layer-8--attacker-environment-red)
10. [Layer 9 — Defender Environment (Blue)](#layer-9--defender-environment-blue)
11. [Layer 10 — MARL Environment (PettingZoo)](#layer-10--marl-environment-pettingzoo)
12. [Layer 11 — RL Agent Loading & Inference](#layer-11--rl-agent-loading--inference)
13. [Layer 12 — MARL Self-Play Results](#layer-12--marl-self-play-results)
14. [Layer 13 — Attack Path Analyzer](#layer-13--attack-path-analyzer)
15. [Layer 14 — Patch Optimizer (USP)](#layer-14--patch-optimizer-usp)
16. [Layer 15 — Cost-Aware Optimizer](#layer-15--cost-aware-optimizer)
17. [Layer 16 — Explainability Cards](#layer-16--explainability-cards)
18. [Layer 17 — Report Generator](#layer-17--report-generator)
19. [Layer 18 — Data Provider Abstraction](#layer-18--data-provider-abstraction)
20. [Layer 19 — Telemetry Integration](#layer-19--telemetry-integration)
21. [Layer 20 — Web API Endpoints (FastAPI)](#layer-20--web-api-endpoints-fastapi)
22. [Layer 21 — End-to-End Pipeline Integration](#layer-21--end-to-end-pipeline-integration)
23. [Appendix — How to Run](#appendix--how-to-run)

---

## Layer 0 — Data Structures & Constants

### T0.1 — CVE dataclass fields
```python
from src.graph.network_graph import CVE
cve = CVE(cve_id="CVE-2023-0001", software="OpenSSH", version="8.9",
          cvss_score=9.8, attack_vector="network")
```
| Check                              | Expected                       |
| ---------------------------------- | ------------------------------ |
| `cve.severity_label`               | `"CRITICAL"`                   |
| CVE with cvss=7.5 → severity       | `"HIGH"`                       |
| CVE with cvss=5.0 → severity       | `"MEDIUM"`                     |
| CVE with cvss=2.0 → severity       | `"LOW"`                        |

### T0.2 — Node dataclass runtime state
```python
from src.graph.network_graph import Node
node = Node(node_id="srv1", node_type="server", software="Apache", version="2.4")
```
| Check                                  | Expected            |
| -------------------------------------- | -------------------- |
| `node.max_cvss` (no vulns)             | `0.0`                |
| `node.num_vulns` (no vulns)            | `0`                  |
| `node.compromise_probability` (no vulns) | `0.0`              |
| After `node.is_patched = True` → `compromise_probability` | `0.0` |
| After `node.reset()` → `is_compromised, is_patched, is_isolated` | All `False` |

### T0.3 — Node compromise probability calculation
```python
node.vulnerabilities = [CVE("CVE-1", "Apache", "2.4", 8.0, "network")]
```
| Check                              | Expected                       |
| ---------------------------------- | ------------------------------ |
| `node.compromise_probability`      | `≈ 0.8` (8.0/10 × 1.0 network mult) |
| Value ≤ 0.95 (capped)             | ✅                              |

### T0.4 — Edge dataclass
```python
from src.graph.network_graph import Edge
edge = Edge(source="srv1", target="srv2", connection_type="ssh", permission_level="admin")
```
| Check                | Expected |
| -------------------- | -------- |
| `edge.permission_value` | `1.0` |
| Edge with `"read"` → `permission_value` | `0.33` |
| Edge with `"write"` → `permission_value` | `0.66` |

### T0.5 — Constants
```python
from src.graph.network_graph import NODE_TYPES, CONNECTION_TYPES
```
| Check | Expected |
| ----- | -------- |
| `NODE_TYPES` | `["server", "workstation", "router", "firewall", "database", "cloud"]` |
| `CONNECTION_TYPES` | `["ssh", "http", "sql", "rdp", "ftp", "vpn"]` |

---

## Layer 1 — Graph Module

### T1.1 — Load enterprise topology
```python
from src.graph.topology_loader import load_topology
graph = load_topology("data/topologies/enterprise_20n.json")
```
| Check                    | Expected     |
| ------------------------ | ------------ |
| `graph.num_nodes`        | `20`         |
| `graph.num_edges`        | `> 0` (at least 20 edges) |
| `len(graph.entry_points)` | `≥ 1`      |
| `len(graph.critical_assets)` | `≥ 1`  |
| All node_ids are unique  | ✅           |

### T1.2 — Load all topologies
```python
from src.graph.topology_loader import load_all_topologies
topos = load_all_topologies("data/topologies")
```
| Check                     | Expected |
| ------------------------- | -------- |
| `len(topos)`              | `3` (enterprise_20n, small_office_10n, cloud_hybrid_30n) |
| All values are `NetworkGraph` instances | ✅ |
| `topos["small_office_10n"].num_nodes` | `10` |
| `topos["cloud_hybrid_30n"].num_nodes` | `30` |

### T1.3 — Load nonexistent file
```python
load_topology("data/topologies/nonexistent.json")
```
| Check | Expected |
| ----- | -------- |
| Raises `FileNotFoundError` | ✅ |

### T1.4 — CVE tagging
```python
from src.graph.cve_tagger import load_cve_database, tag_graph
cve_db = load_cve_database("data/cve/cve_dataset.json")
tag_graph(graph, cve_db)
```
| Check                                  | Expected |
| -------------------------------------- | -------- |
| `len(cve_db)` > 0                     | ✅       |
| At least 1 node has `num_vulns > 0`   | ✅       |
| Nodes with matching software get CVEs  | ✅       |
| Nodes with non-matching software get `[]` | ✅    |

### T1.5 — CVE tagging with `include_local_vulns=False`
```python
tag_graph(graph, cve_db, include_local_vulns=False)
```
| Check | Expected |
| ----- | -------- |
| No node has a CVE with `attack_vector == "local"` | ✅ |

### T1.6 — Vulnerability summary
```python
from src.graph.cve_tagger import get_vulnerability_summary
summary = get_vulnerability_summary(graph)
```
| Check                                  | Expected |
| -------------------------------------- | -------- |
| `isinstance(summary, dict)`           | ✅       |
| Each entry has keys: `num_cves, max_cvss, severity, cve_ids` | ✅ |

### T1.7 — Reachability
```python
graph.reset_runtime_state()
entry = graph.entry_points[0]
reachable = graph.reachable_from([entry])
```
| Check | Expected |
| ----- | -------- |
| `len(reachable) >= 1` | ✅ |
| Entry point NOT in reachable (one-hop successors only) | ✅ |
| Isolated node NOT in reachable | ✅ |

### T1.8 — Deep copy independence
```python
copy = graph.deep_copy()
copy.get_node(copy.node_ids[0]).is_compromised = True
```
| Check | Expected |
| ----- | -------- |
| Original node `is_compromised` | `False` (unchanged) |
| Copy node `is_compromised` | `True` |

### T1.9 — Degree centrality
```python
dc = graph.degree_centrality()
```
| Check | Expected |
| ----- | -------- |
| `len(dc) == graph.num_nodes` | ✅ |
| All values between 0.0 and 1.0 | ✅ |

---

## Layer 2 — PyG Converter

### T2.1 — Basic conversion (no action)
```python
from src.graph.pyg_converter import to_pyg, get_compromise_vector
data = to_pyg(graph)
```
| Check                     | Expected |
| ------------------------- | -------- |
| `data.x.shape`            | `(20, 11)` — 20 nodes, 11 features |
| `data.edge_index.shape[0]` | `2` |
| `data.edge_attr.shape[1]` | `5` |
| `data.node_ids`           | list of 20 strings |
| All x values in `[0.0, 1.0]` | ✅ |

### T2.2 — Conversion with attacked node (12th feature)
```python
attacked_nid = graph.node_ids[5]
data_atk = to_pyg(graph, attacked_node_id=attacked_nid)
```
| Check                            | Expected |
| -------------------------------- | -------- |
| `data_atk.x.shape`              | `(20, 12)` — 12th feature added |
| Feature 11 on attacked node     | `1.0` |
| Feature 11 on all other nodes   | `0.0` |

### T2.3 — Isolated node edge removal
```python
graph.get_node(graph.node_ids[3]).is_isolated = True
data_iso = to_pyg(graph)
```
| Check | Expected |
| ----- | -------- |
| Edges to/from isolated node excluded from `edge_index` | ✅ |
| Total edges < non-isolated edge count | ✅ |

### T2.4 — Compromise vector
```python
graph.get_node(graph.node_ids[0]).is_compromised = True
cv = get_compromise_vector(graph)
```
| Check              | Expected |
| ------------------ | -------- |
| `cv.shape`         | `(20,)` |
| `cv[0]`            | `1.0`  |
| All others         | `0.0`  |

---

## Layer 3 — Rule-Based Simulator

### T3.1 — Simulator reset
```python
from src.simulator.rule_based import AttackSimulator
graph = load_topology("data/topologies/enterprise_20n.json")
tag_graph(graph, cve_db)
sim = AttackSimulator(graph, max_steps=50, seed=42)
entry = sim.reset()
```
| Check                    | Expected |
| ------------------------ | -------- |
| `entry` is a valid node_id | ✅ |
| `entry in graph.entry_points` or fallback | ✅ |
| `len(sim.compromised)` | `1` (the entry point) |
| `graph.get_node(entry).is_compromised` | `True` |

### T3.2 — Single step (valid target)
```python
targets = sim.reachable_targets
action = targets[0] if targets else None
reward, done = sim.step(action)
```
| Check                                | Expected |
| ------------------------------------ | -------- |
| `reward` is a float                  | ✅       |
| `reward` includes step penalty (-0.1)| ✅       |
| If success: `action in sim.compromised` | ✅    |
| `done` is bool                       | ✅       |

### T3.3 — Invalid action penalties
```python
sim2 = AttackSimulator(graph, max_steps=50, seed=42)
sim2.reset()
already_compromised = sim2.compromised[0]
reward_invalid, _ = sim2.step(already_compromised)
```
| Check | Expected |
| ----- | -------- |
| `reward_invalid` includes `-0.5` penalty (invalid action) | ✅ |

### T3.4 — Max attempts per target
```python
sim3 = AttackSimulator(graph, max_steps=50, max_attempts_per_target=2, seed=42)
sim3.reset()
target = sim3.reachable_targets[0]
sim3.step(target)
sim3.step(target)  # 2nd attempt
reward3, _ = sim3.step(target)  # 3rd attempt — over limit
```
| Check | Expected |
| ----- | -------- |
| `reward3` includes `-0.45` penalty (max attempts exceeded) | ✅ |

### T3.5 — Full episode run
```python
ep = sim.run_episode()
```
| Check                   | Expected |
| ----------------------- | -------- |
| `ep.entry_point` is a string | ✅ |
| `ep.total_steps > 0`   | ✅       |
| `ep.attack_path` is a list | ✅    |
| `len(ep.transitions) > 0` | ✅    |
| Each transition has: `step, action_node_id, success, reward, done` | ✅ |

### T3.6 — Batch simulation
```python
stats = sim.run_batch(n_episodes=100)
```
| Check                            | Expected |
| -------------------------------- | -------- |
| `stats["n_episodes"]`            | `100`    |
| `0.0 <= stats["success_rate"] <= 1.0` | ✅  |
| `stats["mean_steps"] > 0`       | ✅       |

### T3.7 — Recommended episode limit
```python
from src.simulator.rule_based import recommended_episode_limit
limit = recommended_episode_limit(graph)
```
| Check | Expected |
| ----- | -------- |
| `10 <= limit <= 40` | ✅ |

### T3.8 — Connection multiplier values
| Connection | Multiplier |
| ---------- | ---------- |
| `"http"`   | `0.83`     |
| `"ssh"`    | `0.79`     |
| `"rdp"`    | `0.74`     |
| `"sql"`    | `0.71`     |
| `"ftp"`    | `0.66`     |
| `"vpn"`    | `0.70`     |

### T3.9 — Critical asset hardening
| Check | Expected |
| ----- | -------- |
| Critical nodes have `0.78` multiplier applied to compromise probability | ✅ |
| Non-critical nodes have `1.0` multiplier | ✅ |

### T3.10 — Deterministic replay with same seed
```python
sim_a = AttackSimulator(graph.deep_copy(), max_steps=50, seed=42)
tag_graph(sim_a.graph, cve_db)
ep_a = sim_a.run_episode()

sim_b = AttackSimulator(graph.deep_copy(), max_steps=50, seed=42)
tag_graph(sim_b.graph, cve_db)
ep_b = sim_b.run_episode()
```
| Check | Expected |
| ----- | -------- |
| `ep_a.attack_path == ep_b.attack_path` | ✅ |
| `ep_a.total_reward == ep_b.total_reward` | ✅ |

---

## Layer 4 — Episode Generator & HDF5 Dataset

### T4.1 — Generate from single graph
```python
from src.simulator.episode_generator import generate_episodes_from_graph
transitions = generate_episodes_from_graph(graph, n_episodes=10, max_steps=20, seed=42)
```
| Check                             | Expected |
| --------------------------------- | -------- |
| `len(transitions) > 0`           | ✅       |
| Each tuple has 5 elements: `(feats_t, action, feats_t1, comp_t1, edge_idx)` | ✅ |
| `feats_t.shape` = `(N, 11)`      | ✅       |
| `action.shape` = `(N,)` and is one-hot | ✅ |
| `comp_t1.shape` = `(N,)` with values in `{0.0, 1.0}` | ✅ |
| `edge_idx.shape[0]` = `2`        | ✅       |

### T4.2 — Full HDF5 dataset generation (small)
```python
from src.simulator.episode_generator import generate_dataset
stats = generate_dataset(
    topologies_dir="data/topologies",
    cve_path="data/cve/cve_dataset.json",
    output_path="data/episodes/test_transitions.h5",
    episodes_per_topology=10,
    max_steps=20,
    seed=42,
)
```
| Check                              | Expected |
| ---------------------------------- | -------- |
| `stats["total_transitions"] > 0`   | ✅       |
| `stats["num_topologies"]` = `3`    | ✅       |
| HDF5 file exists at output path    | ✅       |

### T4.3 — HDF5 dataset structure
```python
import h5py
with h5py.File("data/episodes/test_transitions.h5", "r") as f:
    keys = list(f.keys())
```
| Check | Expected |
| ----- | -------- |
| `"node_feats_t" in keys` | ✅ |
| `"action_vec" in keys` | ✅ |
| `"node_feats_t1" in keys` | ✅ |
| `"compromise_t1" in keys` | ✅ |
| `"n_nodes" in keys` | ✅ |
| `"edge_index" in keys` | ✅ |
| `"n_edges" in keys` | ✅ |
| Shapes padded to MAX_N=50 | ✅ |

### T4.4 — EpisodeDataset PyTorch loader
```python
from src.simulator.episode_generator import EpisodeDataset
ds = EpisodeDataset("data/episodes/test_transitions.h5")
x, ct1, n, ei = ds[0]
```
| Check                  | Expected |
| ---------------------- | -------- |
| `x.shape[1]` = `12`   | ✅ (11 features + action) |
| `ct1.shape[0]` = `n`  | ✅       |
| `ei.shape[0]` = `2`   | ✅       |

---

## Layer 5 — GNN World Model (Architecture)

### T5.1 — GraphSAGE model instantiation
```python
from src.models.gnn_world_model import GNNWorldModel
model = GNNWorldModel(in_channels=12, hidden_channels=64, num_layers=3, dropout=0.1)
```
| Check                         | Expected |
| ----------------------------- | -------- |
| `len(model.convs)` = `3`     | ✅       |
| `len(model.bns)` = `2`       | ✅ (no BN on last layer) |

### T5.2 — Forward pass shape
```python
import torch
x = torch.randn(20, 12)
edge_index = torch.randint(0, 20, (2, 40))
out = model(x, edge_index)
```
| Check                        | Expected |
| ---------------------------- | -------- |
| `out.shape` = `(20, 1)`     | ✅       |
| All values in `[0.0, 1.0]`  | ✅ (sigmoid) |

### T5.3 — predict_proba wrapper
```python
probs = model.predict_proba(x, edge_index)
```
| Check                         | Expected |
| ----------------------------- | -------- |
| `probs.shape` = `(20,)`     | ✅       |
| No gradients tracked         | ✅       |

### T5.4 — GAT model instantiation and forward
```python
from src.models.gnn_world_model import GATWorldModel
gat = GATWorldModel(in_channels=12, hidden_channels=64, heads=4)
out_gat = gat(x, edge_index)
```
| Check                    | Expected |
| ------------------------ | -------- |
| `out_gat.shape` = `(20, 1)` | ✅   |

### T5.5 — GCN model instantiation and forward
```python
from src.models.gnn_world_model import GCNWorldModel
gcn = GCNWorldModel(in_channels=12, hidden_channels=64)
out_gcn = gcn(x, edge_index)
```
| Check                    | Expected |
| ------------------------ | -------- |
| `out_gcn.shape` = `(20, 1)` | ✅   |

---

## Layer 6 — GNN World Model (Trained Checkpoint)

### T6.1 — Load trained checkpoint
```python
import torch
from src.models.gnn_world_model import GNNWorldModel

model = GNNWorldModel()
state_dict = torch.load("checkpoints/gnn_world_model.pt", map_location="cpu")
model.load_state_dict(state_dict)
model.eval()
```
| Check                               | Expected |
| ----------------------------------- | -------- |
| No errors on load                   | ✅       |
| `model.training` = `False`          | ✅       |

### T6.2 — Inference on real topology
```python
from src.graph.pyg_converter import to_pyg
graph = load_topology("data/topologies/enterprise_20n.json")
tag_graph(graph, cve_db)

# Simulate: entry point compromised, attack on an adjacent node
entry = graph.entry_points[0]
graph.get_node(entry).is_compromised = True
target = graph.reachable_from([entry])[0]
data = to_pyg(graph, attacked_node_id=target)

probs = model.predict_proba(data.x, data.edge_index)
```
| Check                                    | Expected |
| ---------------------------------------- | -------- |
| `probs.shape` = `(20,)`                 | ✅       |
| All values in `[0.0, 1.0]`              | ✅       |
| Entry point probability near `1.0`       | ✅ (already compromised) |
| Target node probability > other non-compromised nodes | ✅ (attacked node should have elevated prob) |

### T6.3 — Quality thresholds (AUC / accuracy)

Run a small evaluation loop: for ~100 transitions from the HDF5 dataset, compute the model's per-node predictions vs actual `compromise_t1` labels.

| Metric | Expected Threshold |
| ------ | ------------------ |
| **ROC-AUC** (node-level) | ≥ `0.87` (from config target) |
| **Accuracy** (threshold=0.5) | ≥ `0.85` |
| **Precision on compromised class** | ≥ `0.70` |

**Verification command:**
```python
from sklearn.metrics import roc_auc_score, accuracy_score
# Load 100 samples from HDF5, run model, compute metrics
```

### T6.4 — Model sensitivity: patched node reduces prediction
```python
# Before patch: check P(compromise) on a vulnerable node
p_before = probs[node_idx].item()

# After patch: remove vulns, recompute
graph.get_node(target).is_patched = True
graph.get_node(target).vulnerabilities = []
data_patched = to_pyg(graph, attacked_node_id=target)
p_after = model.predict_proba(data_patched.x, data_patched.edge_index)[node_idx].item()
```
| Check | Expected |
| ----- | -------- |
| `p_after < p_before` | ✅ (model sees patched=True, fewer vulns) |

---

## Layer 7 — Transition Model Interface

### T7.1 — RuleBasedTransition
```python
from src.simulator.transition_model import RuleBasedTransition
rb = RuleBasedTransition()
result = rb.predict_next_state(graph, action_node_id=target)
```
| Check                              | Expected |
| ---------------------------------- | -------- |
| `isinstance(result, dict)`         | ✅       |
| Entry point in result with value `1.0` | ✅   |
| Target node has `0 < value ≤ 0.95` | ✅      |
| Non-reachable nodes have `0.0`     | ✅       |

### T7.2 — GNNTransition
```python
from src.simulator.transition_model import GNNTransition
gnn_t = GNNTransition("checkpoints/gnn_world_model.pt", device="cpu")
result = gnn_t.predict_next_state(graph, action_node_id=target)
```
| Check                              | Expected |
| ---------------------------------- | -------- |
| `isinstance(result, dict)`         | ✅       |
| All values in `[0.0, 1.0]`        | ✅       |
| Keys = `graph.node_ids`           | ✅       |

---

## Layer 8 — Attacker Environment (Red)

### T8.1 — Environment creation
```python
from src.envs.attacker_env import AttackerEnv, MAX_NODES, NODE_FEAT_DIM
env = AttackerEnv(
    topology_path="data/topologies/enterprise_20n.json",
    cve_path="data/cve/cve_dataset.json",
    max_steps=50, seed=42
)
```
| Check                              | Expected |
| ---------------------------------- | -------- |
| `env.observation_space.shape`      | `(550,)` — MAX_NODES × NODE_FEAT_DIM |
| `env.action_space.n`               | `50` — MAX_NODES |

### T8.2 — Reset returns valid obs + info
```python
obs, info = env.reset()
```
| Check                              | Expected |
| ---------------------------------- | -------- |
| `obs.shape` = `(550,)`            | ✅       |
| `obs.dtype` = `float32`           | ✅       |
| `"action_mask" in info`           | ✅       |
| `info["action_mask"].shape` = `(50,)` | ✅   |
| At least one True in action mask   | ✅       |
| `info["n_real_nodes"]` = `20`     | ✅       |

### T8.3 — Step with valid action
```python
valid_actions = np.where(info["action_mask"])[0]
action = valid_actions[0]
obs2, reward, terminated, truncated, info2 = env.step(int(action))
```
| Check                              | Expected |
| ---------------------------------- | -------- |
| `obs2.shape` = `(550,)`           | ✅       |
| `isinstance(reward, float)`       | ✅       |
| `isinstance(terminated, bool)`    | ✅       |
| `isinstance(truncated, bool)`     | ✅       |
| `"action_mask" in info2`          | ✅       |
| `"compromised" in info2`          | ✅       |

### T8.4 — Step with out-of-range action
```python
obs3, reward3, _, _, _ = env.step(49)  # padding node
```
| Check | Expected |
| ----- | -------- |
| `reward3` = `-0.5` (invalid action penalty) | ✅ |

### T8.5 — action_masks() method (for MaskablePPO)
```python
mask = env.action_masks()
```
| Check                    | Expected |
| ------------------------ | -------- |
| `mask.shape` = `(50,)`  | ✅       |
| `mask.dtype` = `bool`   | ✅       |

### T8.6 — Episode runs to truncation
```python
env.reset()
for _ in range(50):
    mask = env.action_masks()
    if not mask.any():
        break
    action = np.where(mask)[0][0]
    _, _, terminated, truncated, _ = env.step(int(action))
    if terminated or truncated:
        break
```
| Check | Expected |
| ----- | -------- |
| Loop terminates within 50 steps | ✅ |

---

## Layer 9 — Defender Environment (Blue)

### T9.1 — Environment creation
```python
from src.envs.defender_env import DefenderEnv
env_blue = DefenderEnv(
    topology_path="data/topologies/enterprise_20n.json",
    cve_path="data/cve/cve_dataset.json",
    max_steps=50, seed=42
)
```
| Check                               | Expected |
| ----------------------------------- | -------- |
| `env_blue.action_space.n`           | `100` — 2 × MAX_NODES (patch + isolate) |
| `env_blue.observation_space.shape`  | `(550,)` |

### T9.2 — Defender action mask
```python
obs, info = env_blue.reset()
mask = info["action_mask"]
```
| Check                              | Expected |
| ---------------------------------- | -------- |
| `mask.shape` = `(100,)`           | ✅       |
| Patch actions (0..19): True only for nodes with vulns | ✅ |
| Isolate actions (50..69): True for non-isolated nodes | ✅ |

### T9.3 — Patch action removes vulnerabilities
```python
# Find a patchable node
patch_idx = np.where(mask[:20])[0][0]
obs2, reward, _, _, _ = env_blue.step(int(patch_idx))
node = env_blue._graph.get_node(env_blue._node_order[patch_idx])
```
| Check | Expected |
| ----- | -------- |
| `node.is_patched` | `True` |
| `node.num_vulns` | `0` |

### T9.4 — Isolate action
```python
isolate_idx = MAX_NODES + 0  # isolate first node
env_blue.reset()
env_blue.step(isolate_idx)
node0 = env_blue._graph.get_node(env_blue._node_order[0])
```
| Check | Expected |
| ----- | -------- |
| `node0.is_isolated` | `True` |

### T9.5 — Defender earns bonus for protecting critical assets
Run a full episode without the attacker reaching critical assets.

| Check | Expected |
| ----- | -------- |
| Terminal reward includes `+10.0` bonus | ✅ |

---

## Layer 10 — MARL Environment (PettingZoo)

### T10.1 — Environment creation
```python
from src.envs.marl_env import OnyxMARLEnv
marl = OnyxMARLEnv(
    topology_path="data/topologies/enterprise_20n.json",
    cve_path="data/cve/cve_dataset.json",
    max_steps=20, seed=42
)
```
| Check                                   | Expected |
| --------------------------------------- | -------- |
| `marl.possible_agents`                  | `["attacker_0", "defender_0"]` |
| `marl.action_spaces["attacker_0"].n`    | `50`     |
| `marl.action_spaces["defender_0"].n`    | `100`    |

### T10.2 — Reset and turn order
```python
marl.reset()
```
| Check                                    | Expected |
| ---------------------------------------- | -------- |
| `marl.agent_selection` = `"attacker_0"` | ✅ (attacker goes first) |
| `len(marl.agents)` = `2`               | ✅       |

### T10.3 — Step alternation
```python
marl.reset()
first_agent = marl.agent_selection
mask1 = marl.infos[first_agent]["action_mask"]
action1 = np.where(mask1)[0][0] if mask1.any() else 0
marl.step(int(action1))
second_agent = marl.agent_selection
```
| Check | Expected |
| ----- | -------- |
| `first_agent` = `"attacker_0"` | ✅ |
| `second_agent` = `"defender_0"` | ✅ |

### T10.4 — Termination on critical asset capture
Manually run attacker steps targeting critical assets until one is captured.

| Check | Expected |
| ----- | -------- |
| `marl.terminations["attacker_0"]` = `True` | ✅ |
| `marl.rewards["defender_0"]` includes `-10.0` penalty | ✅ |
| `marl.agents` = `[]` (episode over) | ✅ |

---

## Layer 11 — RL Agent Loading & Inference

### T11.1 — Load Red agent
```python
from sb3_contrib import MaskablePPO
red_agent = MaskablePPO.load("checkpoints/red_agent.zip")
```
| Check | Expected |
| ----- | -------- |
| No errors on load | ✅ |
| `red_agent.policy` is not None | ✅ |

### T11.2 — Red agent prediction
```python
env = AttackerEnv("data/topologies/enterprise_20n.json", "data/cve/cve_dataset.json")
obs, info = env.reset()
action, _ = red_agent.predict(obs, action_masks=info["action_mask"], deterministic=True)
```
| Check                              | Expected |
| ---------------------------------- | -------- |
| `0 <= action < 50`                | ✅       |
| `info["action_mask"][action]` = `True` | ✅ (valid action) |

### T11.3 — Red agent runs a full episode
```python
obs, info = env.reset()
total_reward = 0
for _ in range(50):
    mask = env.action_masks()
    if not mask.any():
        break
    action, _ = red_agent.predict(obs, action_masks=mask, deterministic=False)
    obs, reward, terminated, truncated, info = env.step(int(action))
    total_reward += reward
    if terminated or truncated:
        break
```
| Check | Expected |
| ----- | -------- |
| Episode terminates | ✅ |
| `total_reward > -50` (not all penalties) | ✅ |
| `len(info["compromised"]) > 1` (compromised more than entry point) | ✅ |

### T11.4 — Load Blue agent
```python
blue_agent = MaskablePPO.load("checkpoints/blue_agent.zip")
```
| Check | Expected |
| ----- | -------- |
| No errors on load | ✅ |

### T11.5 — Blue agent prediction
```python
env_blue = DefenderEnv("data/topologies/enterprise_20n.json", "data/cve/cve_dataset.json")
obs, info = env_blue.reset()
action, _ = blue_agent.predict(obs, action_masks=info["action_mask"], deterministic=True)
```
| Check | Expected |
| ----- | -------- |
| `0 <= action < 100` | ✅ |
| `info["action_mask"][action]` = `True` | ✅ |

---

## Layer 12 — MARL Self-Play Results

### T12.1 — MARL checkpoint files exist
| File | Path | Check |
| ---- | ---- | ----- |
| MARL results JSON | `checkpoints/marl/marl_results.json` | ✅ file exists |
| MARL red agents | `checkpoints/marl/red_round_*.zip` | ⚠️ at least 1 |
| MARL blue agents | `checkpoints/marl/blue_round_*.zip` | ⚠️ at least 1 |

### T12.2 — MARL results structure
```python
import json
with open("checkpoints/marl/marl_results.json") as f:
    marl_results = json.load(f)
```
| Check | Expected |
| ----- | -------- |
| Has key `"rounds"` or similar list | ✅ |
| Each round has `red_reward`, `blue_reward` or equivalent | ✅ |
| At least 5 rounds recorded | ✅ |

### T12.3 — Arms race pattern
| Check | Expected |
| ----- | -------- |
| Red reward generally increases over rounds | ✅ (learning trend) |
| Blue reward adapts (not monotonically decreasing) | ✅ |

---

## Layer 13 — Attack Path Analyzer

### T13.1 — Run analysis (rule-based, no agent)
```python
from src.analysis.attack_path_analyzer import analyze_attack_paths
result = analyze_attack_paths(
    topology_path="data/topologies/enterprise_20n.json",
    cve_path="data/cve/cve_dataset.json",
    agent_path=None,
    n_episodes=100,
    seed=42,
)
```
| Check                                  | Expected |
| -------------------------------------- | -------- |
| `"edge_frequency" in result`           | ✅       |
| `"node_frequency" in result`           | ✅       |
| `"top_paths" in result`               | ✅       |
| `"success_rate" in result`            | ✅       |
| `0.0 <= result["success_rate"] <= 1.0` | ✅      |
| `result["n_episodes"]` = `100`        | ✅       |
| Edge frequencies are normalised `[0,1]` | ✅     |

### T13.2 — Run analysis WITH trained agent
```python
result_agent = analyze_attack_paths(
    topology_path="data/topologies/enterprise_20n.json",
    cve_path="data/cve/cve_dataset.json",
    agent_path="checkpoints/red_agent.zip",
    n_episodes=100,
    seed=42,
)
```
| Check                                  | Expected |
| -------------------------------------- | -------- |
| `result_agent["success_rate"]` >= `result["success_rate"]` | ✅ (trained agent should be better than random) |
| `len(result_agent["top_paths"]) > 0`  | ✅       |

---

## Layer 14 — Patch Optimizer (USP)

### T14.1 — Pre-computed results exist
```python
import json
with open("reports/patch_analysis.json") as f:
    patch_results = json.load(f)
```
| Check                                    | Expected |
| ---------------------------------------- | -------- |
| `len(patch_results) > 0`                | ✅       |
| Each entry has: `node_id, cve_id, cvss_score, simulation_impact, simulation_rank, cvss_rank` | ✅ |
| `baseline_success_rate` is present       | ✅       |

### T14.2 — CVSS rank ≠ Simulation rank for at least some CVEs
This is the **core USP claim**: network-context-aware ranking diverges from generic CVSS.

| Check | Expected |
| ----- | -------- |
| At least 1 entry where `cvss_rank != simulation_rank` | ✅ |
| Top simulation-ranked CVE is NOT necessarily the highest CVSS score | ✅ (demonstrates value) |

### T14.3 — Impact is non-negative
| Check | Expected |
| ----- | -------- |
| All `simulation_impact >= 0` | ✅ (patching should not increase attack success) |

### T14.4 — Live patch optimizer run (small scale)
```python
from src.analysis.patch_optimizer import compute_patch_impact
results = compute_patch_impact(
    topology_path="data/topologies/small_office_10n.json",
    cve_path="data/cve/cve_dataset.json",
    agent_path="checkpoints/red_agent.zip",
    n_baseline=50,
    n_eval_per_patch=20,
    verbose=False,
)
```
| Check                        | Expected |
| ---------------------------- | -------- |
| `len(results) > 0`          | ✅       |
| Results sorted by `simulation_impact` desc | ✅ |
| `results[0]["simulation_rank"]` = `1` | ✅ |

---

## Layer 15 — Cost-Aware Optimizer

### T15.1 — Load default cost model
```python
from src.analysis.cost_optimizer import load_cost_model
model = load_cost_model()
```
| Check                                   | Expected |
| --------------------------------------- | -------- |
| `"node_type_effort_hours" in model`     | ✅       |
| `model["node_type_effort_hours"]["server"]` = `6.0` | ✅ |
| `model["critical_asset_multiplier"]` = `1.7` | ✅ |

### T15.2 — Load custom cost model
```python
model_custom = load_cost_model("configs/cost_model.json")
```
| Check | Expected |
| ----- | -------- |
| Returns dict with merged defaults | ✅ |

### T15.3 — Rank patches by cost-aware ROI
```python
from src.analysis.cost_optimizer import rank_cost_aware_patches
ranking = rank_cost_aware_patches(
    patch_results=patch_results,
    topology_path="data/topologies/enterprise_20n.json",
    cve_path="data/cve/cve_dataset.json",
)
```
| Check | Expected |
| ----- | -------- |
| `"top_recommendations" in ranking` | ✅ |
| Each recommendation has: `roi_score, effort_hours, risk_reduction_pp, cost_rank` | ✅ |
| Sorted by `roi_score` descending | ✅ |
| `effort_hours > 0` for all entries | ✅ |

---

## Layer 16 — Explainability Cards

### T16.1 — Build explanation cards
```python
from src.analysis.explainability import build_explanation_cards
cards = build_explanation_cards(
    cost_recommendations=ranking["top_recommendations"],
    sim_results=result,
    baseline_success_rate=0.45,
    top_n=5,
)
```
| Check                               | Expected |
| ----------------------------------- | -------- |
| `len(cards)` ≤ `5`                 | ✅       |
| Each card has: `key, title, summary, why_ranked, tradeoffs, impact_preview` | ✅ |
| `impact_preview` has `before, after, delta_pp` | ✅ |

---

## Layer 17 — Report Generator

### T17.1 — Generate HTML report
```python
from src.analysis.report_generator import generate_report
html = generate_report(
    patch_results=patch_results,
    topology_name="enterprise_20n",
    n_episodes=10000,
    output_html="reports/test_report.html",
)
```
| Check                              | Expected |
| ---------------------------------- | -------- |
| `len(html) > 100`                 | ✅       |
| Contains `"Onyx Morning Report"` | ✅   |
| Contains `"Top 5 Patch Recommendations"` | ✅ |
| Contains baseline success rate     | ✅       |
| File written to `reports/test_report.html` | ✅ |

### T17.2 — Report with empty results
```python
html_empty = generate_report(patch_results=[], topology_name="test")
```
| Check | Expected |
| ----- | -------- |
| Returns valid HTML without crashing | ✅ |
| Contains "No patch results available" | ✅ |

### T17.3 — Existing morning report file
| Check | Expected |
| ----- | -------- |
| `reports/morning_report.html` exists | ✅ |
| File size > 1KB | ✅ |

---

## Layer 18 — Data Provider Abstraction

### T18.1 — Normalize data source strings
```python
from src.analysis.data_provider import normalize_data_source, DataSource
```
| Input | Expected |
| ----- | -------- |
| `"simulation"` | `DataSource.SIMULATION` |
| `"sim"` | `DataSource.SIMULATION` |
| `"telemetry"` | `DataSource.TELEMETRY` |
| `"real"` | `DataSource.TELEMETRY` |
| `"hybrid"` | `DataSource.HYBRID` |
| `""` | `DataSource.SIMULATION` |
| `None` | `DataSource.SIMULATION` |

### T18.2 — SimulationProvider runs analysis
```python
from src.analysis.data_provider import SimulationProvider, ProviderContext
from pathlib import Path
ctx = ProviderContext(
    project_root=Path("D:/Onyx"),
    topology_path="data/topologies/enterprise_20n.json",
    topology_key="enterprise_20n",
    cve_path="data/cve/cve_dataset.json",
    agent_path=None,
)
provider = SimulationProvider(ctx)
result = provider.run_attack_analysis(n_episodes=50, seed=42)
```
| Check | Expected |
| ----- | -------- |
| `result["data_source"]` = `"simulation"` | ✅ |
| `"success_rate" in result` | ✅ |
| `"evaluation_runs" in result` | ✅ |
| `"data_freshness_at" in result` | ✅ |

### T18.3 — build_data_provider factory
```python
from src.analysis.data_provider import build_data_provider
p = build_data_provider(ctx, data_source="simulation")
```
| Check | Expected |
| ----- | -------- |
| `isinstance(p, SimulationProvider)` | ✅ |

---

## Layer 19 — Telemetry Integration

### T19.1 — Load telemetry settings
```python
from src.integrations.telemetry_client import load_telemetry_settings
from pathlib import Path
settings = load_telemetry_settings(Path("D:/Onyx"))
```
| Check                          | Expected |
| ------------------------------ | -------- |
| `settings.enabled`            | `False` (default config) |
| `settings.fallback_to_simulation` | `True` |

### T19.2 — TelemetryClient with disabled telemetry
```python
from src.integrations.telemetry_client import TelemetryClient
client = TelemetryClient(Path("D:/Onyx"))
```
| Check | Expected |
| ----- | -------- |
| `client.settings.enabled` = `False` | ✅ |
| Calling `_post_json` raises `RuntimeError("telemetry_disabled")` | ✅ |

### T19.3 — TelemetryProvider falls back to simulation
```python
from src.analysis.data_provider import TelemetryProvider
tp = TelemetryProvider(ctx)
result = tp.run_attack_analysis(n_episodes=50, seed=42)
```
| Check | Expected |
| ----- | -------- |
| `result["data_source"]` = `"simulation"` (fallback) | ✅ |
| `"telemetry_unavailable_fallback" in result["data_source_note"]` | ✅ |

---

## Layer 20 — Web API Endpoints (FastAPI)

All API tests use `fastapi.testclient.TestClient`.

```python
from fastapi.testclient import TestClient
from web.backend.server import app
client = TestClient(app)
```

### T20.1 — Health check
```python
r = client.get("/api/health")
```
| Check | Expected |
| ----- | -------- |
| `r.status_code` = `200` | ✅ |
| `r.json()["status"]` = `"ok"` or similar | ✅ |

### T20.2 — Detailed health
```python
r = client.get("/api/health/detailed")
```
| Check | Expected |
| ----- | -------- |
| `r.status_code` = `200` | ✅ |
| Response includes system info | ✅ |

### T20.3 — List topologies
```python
r = client.get("/api/topologies")
```
| Check | Expected |
| ----- | -------- |
| `r.status_code` = `200` | ✅ |
| Response contains `"enterprise_20n"` | ✅ |
| At least 3 topologies listed | ✅ |

### T20.4 — Get topology details
```python
r = client.get("/api/topology/enterprise_20n")
```
| Check | Expected |
| ----- | -------- |
| `r.status_code` = `200` | ✅ |
| Response has `nodes` and `edges` or equivalent | ✅ |

### T20.5 — Get status
```python
r = client.get("/api/status")
```
| Check | Expected |
| ----- | -------- |
| `r.status_code` = `200` | ✅ |

### T20.6 — Run simulation
```python
r = client.post("/api/simulate", json={
    "topology": "enterprise_20n",
    "n_episodes": 100,
    "data_source": "simulation",
})
```
| Check | Expected |
| ----- | -------- |
| `r.status_code` = `200` | ✅ |
| `"success_rate" in r.json()` | ✅ |

### T20.7 — Simulate seed sweep
```python
r = client.post("/api/simulate/seed-sweep", json={
    "topology": "enterprise_20n",
    "n_episodes": 100,
    "seeds": [42, 73],
})
```
| Check | Expected |
| ----- | -------- |
| `r.status_code` = `200` | ✅ |

### T20.8 — Get scenarios
```python
r = client.get("/api/scenarios")
```
| Check | Expected |
| ----- | -------- |
| `r.status_code` = `200` | ✅ |

### T20.9 — Get patch results (cached)
```python
r = client.get("/api/patch-results")
```
| Check | Expected |
| ----- | -------- |
| `r.status_code` = `200` | ✅ |
| Response is a list of patch entries | ✅ |

### T20.10 — Get MARL results
```python
r = client.get("/api/marl-results")
```
| Check | Expected |
| ----- | -------- |
| `r.status_code` = `200` | ✅ |

### T20.11 — Generate report endpoint
```python
r = client.post("/api/generate-report", json={"topology": "enterprise_20n"})
```
| Check | Expected |
| ----- | -------- |
| `r.status_code` = `200` | ✅ |

### T20.12 — Get report HTML
```python
r = client.get("/api/report-html")
```
| Check | Expected |
| ----- | -------- |
| `r.status_code` = `200` | ✅ |
| Response contains HTML content | ✅ |

### T20.13 — Patch optimize endpoint
```python
r = client.post("/api/patch-optimize", json={
    "topology": "enterprise_20n",
    "n_baseline": 50,
    "n_eval_per_patch": 10,
})
```
| Check | Expected |
| ----- | -------- |
| `r.status_code` = `200` | ✅ |

### T20.14 — Cost model endpoint
```python
r = client.get("/api/cost-model")
```
| Check | Expected |
| ----- | -------- |
| `r.status_code` = `200` | ✅ |
| Response contains cost model data | ✅ |

### T20.15 — Patch cost ranking endpoint
```python
r = client.post("/api/patch-cost-ranking")
```
| Check | Expected |
| ----- | -------- |
| `r.status_code` = `200` | ✅ |

### T20.16 — Explainability endpoint
```python
r = client.post("/api/explainability")
```
| Check | Expected |
| ----- | -------- |
| `r.status_code` = `200` | ✅ |

### T20.17 — Risk scorecard endpoint
```python
r = client.post("/api/risk-scorecard", json={
    "topology": "enterprise_20n",
    "n_episodes": 100,
    "top_k_patches": 3,
})
```
| Check | Expected |
| ----- | -------- |
| `r.status_code` = `200` | ✅ |

### T20.18 — Telemetry status
```python
r = client.get("/api/telemetry/status")
```
| Check | Expected |
| ----- | -------- |
| `r.status_code` = `200` | ✅ |
| Response includes `enabled` field | ✅ |

### T20.19 — Evidence bundle
```python
r = client.post("/api/evidence-bundle")
```
| Check | Expected |
| ----- | -------- |
| `r.status_code` = `200` | ✅ |

### T20.20 — User preferences CRUD
```python
# Set preference
r = client.post("/api/preferences", json={"user_id": "test-user", "default_topology": "enterprise_20n"})
# Get preference
r = client.get("/api/preferences/test-user")
```
| Check | Expected |
| ----- | -------- |
| Both return `200` | ✅ |

### T20.21 — Training jobs CRUD
```python
r = client.post("/api/training/jobs", json={"user_id": "test", "stage": "red"})
job_id = r.json().get("job_id")
r2 = client.get(f"/api/training/jobs/{job_id}")
```
| Check | Expected |
| ----- | -------- |
| Both return `200` | ✅ |

### T20.22 — Metrics and logs
```python
r_metrics = client.get("/api/metrics")
r_logs = client.get("/api/logs")
```
| Check | Expected |
| ----- | -------- |
| Both return `200` | ✅ |

### T20.23 — Invalid topology returns error
```python
r = client.get("/api/topology/nonexistent_topo")
```
| Check | Expected |
| ----- | -------- |
| `r.status_code` = `404` or `400` | ✅ |

---

## Layer 21 — End-to-End Pipeline Integration

### T21.1 — Full pipeline smoke test
Run `python run.py --stage setup` and verify all checks pass.

```powershell
.\.venv\Scripts\python.exe run.py --stage setup
```
| Check | Expected |
| ----- | -------- |
| `[OK] Python 3.x` | ✅ |
| `[OK] PyTorch x.x` | ✅ |
| `[OK] PyTorch Geometric x.x` | ✅ |
| `[OK] Stable-Baselines3 x.x` | ✅ |
| `[OK] sb3-contrib` | ✅ |
| All data files exist | ✅ |
| Topology loads and tags successfully | ✅ |
| `[DONE] Setup verified.` | ✅ |

### T21.2 — Import test
```powershell
.\.venv\Scripts\python.exe test_imports.py
```
| Check | Expected |
| ----- | -------- |
| `✓ AttackerEnv imported` | ✅ |
| `✓ DefenderEnv imported` | ✅ |
| `✓ OnyxMARLEnv imported` | ✅ |

### T21.3 — Trained model files exist
| File | Path | Min Size |
| ---- | ---- | -------- |
| GNN World Model | `checkpoints/gnn_world_model.pt` | > 10KB |
| Red Agent | `checkpoints/red_agent.zip` | > 100KB |
| Blue Agent | `checkpoints/blue_agent.zip` | > 100KB |
| Patch Analysis | `reports/patch_analysis.json` | > 1KB |
| Morning Report | `reports/morning_report.html` | > 1KB |

### T21.4 — Streamlit demo starts
```powershell
.\.venv\Scripts\python.exe -m streamlit run demo/app.py --server.port 8511
```
| Check | Expected |
| ----- | -------- |
| Process starts without crash | ✅ |
| `http://localhost:8511` loads in browser | ✅ |
| 4 tabs visible | ✅ |

### T21.5 — React web frontend starts
```powershell
cd web
npm run dev
```
| Check | Expected |
| ----- | -------- |
| FastAPI backend starts on port 8020 | ✅ |
| Vite frontend starts on port 5183 | ✅ |
| `http://localhost:5183` loads dashboard | ✅ |
| `/api/health` responds from 5183 (proxy) | ✅ |

### T21.6 — Full pipeline run (data → report)
> ⚠️ **Warning:** This takes 12–14 hours. Only run if training from scratch.

```powershell
.\.venv\Scripts\python.exe run.py --all
```
| Stage | Check |
| ----- | ----- |
| Stage 0 (setup) | All imports verified |
| Stage 1 (data) | > 50K transitions generated |
| Stage 2 (GNN) | AUC ≥ 0.87 on test set |
| Stage 3 (Red) | Agent trains for 1M steps without crash |
| Stage 4 (Blue) | Agent trains for 1M steps without crash |
| Stage 5 (MARL) | 5 rounds complete, results saved |
| Stage 6 (Patch) | `patch_analysis.json` generated |
| Stage 7 (Report) | `morning_report.html` generated |

---

## Appendix — How to Run

### Quick validation (< 5 minutes)
```powershell
cd D:\Onyx
.\.venv\Scripts\Activate.ps1
python test_imports.py
python run.py --stage setup
```

### Core module tests (interactive Python, ~10 minutes)
Open a Python REPL and run the Layer 0–6 tests manually:
```powershell
.\.venv\Scripts\python.exe -i
```
Then paste code blocks from the test cases above.

### API tests (~2 minutes)
```python
# From project root
import sys; sys.path.insert(0, ".")
from fastapi.testclient import TestClient
from web.backend.server import app
client = TestClient(app)

# Then run T20.1 through T20.23
```

### Full integration (12–14 hours)
```powershell
.\.venv\Scripts\python.exe run.py --all
```

---

> **Last updated:** 2026-09-06  
> **Coverage:** 21 layers × 100+ individual checks  
> **Modules tested:** `network_graph`, `topology_loader`, `cve_tagger`, `pyg_converter`, `gnn_world_model`, `gnn_policy`, `attacker_env`, `defender_env`, `marl_env`, `rule_based`, `transition_model`, `episode_generator`, `attack_path_analyzer`, `patch_optimizer`, `cost_optimizer`, `explainability`, `report_generator`, `data_provider`, `telemetry_client`, `server` (FastAPI)
