# Onyx: Hackathon Judge Questions and Answer Guide

Prepared against the repository on 7 September 2026. This is a rehearsal guide, not an official SIH scoring rubric. Suggested answers distinguish implemented code, demonstration behavior, and future work. A module existing in the repository does not prove that every dashboard operation uses it or that it has passed production validation.

## 1. Project overview for the entire team

| Item | Current description |
| --- | --- |
| Project | Onyx |
| Team | ALGORYTHMS, as stated in the supplied presentation |
| Problem statement | SIH26145: Automated AI Threat Simulation and Proactive Cyber Defense, as stated in the supplied presentation |
| Main question | Which remediation should a security team prioritize in its network? |
| Product | React/TypeScript dashboard and FastAPI backend with offline attack simulation and a separate view of live endpoint evidence |
| Main pages | Overview, Topology, Exposure, Telemetry, Simulation, Patches |
| Research components | GraphSAGE transition model, GAT/GCN alternatives, reinforcement-learning environments, Red and Blue policy training |
| Current analyzer | Rule-based attack transitions with a trained Red policy when it loads, or random action selection as a fallback |
| Live data | Registered endpoints, heartbeats, observed relationships, imported vulnerability findings, and telemetry |
| Remediation ranking | Simulation impact and effort for modeled scenarios; a separate heuristic score for live vulnerability findings |
| Deployment | Local server laptop with client agents over a trusted network |
| Readiness | Prototype with functional components and regression tests; enterprise security and real-world effectiveness validation remain unfinished |

### A 30-second introduction

“Onyx helps security teams decide what to fix first. It models network assets and runs offline attack scenarios to compare remediation choices. The dashboard also shows evidence from connected laptops, including endpoint status and imported vulnerability findings. Our current prototype combines simulation, patch prioritization, and live visibility. We are validating the learned-model integration and the relationship between simulation results and real security outcomes.”

### A 90-second explanation

“A vulnerability score describes a weakness, but a security team also needs to understand where that weakness sits in its network. Onyx represents assets and their connections as a graph, simulates movement toward critical assets, and compares patch choices using estimated security benefit and effort.

The working web application has six main views and two data modes. Demo mode supports controlled scenarios. Reality mode shows evidence from connected endpoints and imported findings. Attack simulation remains an offline operation in either mode.

Our research code includes a GraphSAGE model that predicts the next compromise state and Red/Blue reinforcement-learning components. The current web attack analyzer still uses rule-based transitions, optionally guided by a trained Red policy. That distinction is part of our validation plan. The next milestone is to demonstrate that a fully integrated learned transition model improves recommendations on unseen network scenarios.”

## 2. Problem, users, and originality

### Q1. What exact problem are you solving?

**Suggested answer:** We are helping analysts prioritize remediation across interconnected assets. A long list of vulnerabilities does not directly tell an analyst which fix most reduces modeled access to a critical asset.

**Judge follow-up:** Show one scenario where the highest-CVSS vulnerability and the highest-impact remediation differ. Explain the connections responsible for the difference.

### Q2. Who is the first intended user?

**Suggested answer:** A security analyst or small IT security team managing a controlled network. The initial deployment should support analyst decisions in a lab or pilot before the organization relies on it for operational response.

**Evidence to prepare:** A specific user workflow and, if available, genuine interview notes. Do not invent customer validation.

### Q3. Why does network context matter?

**Suggested answer:** Two vulnerabilities with the same severity may expose very different assets. Reachability, entry points, and asset criticality can change the importance of a fix. Onyx lets us investigate those differences under an explicit model.

### Q4. Why can an analyst not simply sort by CVSS?

**Suggested answer:** That is a useful baseline. Our hypothesis is that comparing modeled outcomes after each candidate patch provides additional context. We must demonstrate the improvement against the same CVSS baseline on the same scenarios.

### Q5. What is original about Onyx?

**Suggested answer:** Our contribution is the project-specific integration of graph simulation, remediation comparison, and an analyst interface with separate live evidence. We use established algorithms. We have not established that the overall concept is unique across all commercial or research systems.

### Q6. Is this an antivirus, SIEM, or penetration-testing replacement?

**Suggested answer:** It is a prototype for security analysis and prioritization. The live Windows agent forwards Microsoft Defender detections. Onyx does not independently provide Defender's malware-detection capability. It can complement existing operational tools and analyst testing.

### Q7. Why use AI instead of ordinary graph traversal?

**Suggested answer:** Graph traversal can identify reachable routes and should remain a baseline. Learned models and policies may help estimate transitions or explore decisions, but that benefit needs controlled measurement. Where simple methods perform equally well, the simpler method may be preferable.

### Q8. What would make a judge believe this is more than a dashboard?

**Suggested answer:** We can trace an endpoint heartbeat into the API, show stored evidence, run a simulation with explicit parameters, and inspect the ranking calculation. The important evidence is the computation and data flow behind each screen.

## 3. Architecture and data flow

### Q9. Explain the architecture without library names

**Suggested answer:** There are two main flows. Client laptops report observations to the server, which presents live evidence. Separately, the server loads a modeled network, evaluates attack scenarios, and produces remediation analysis. The dashboard gives analysts access to both flows with their provenance visible.

### Q10. What is your digital twin?

**Suggested answer:** A security abstraction of network assets, connections, vulnerability information, and state. It models selected conditions relevant to an attack scenario. It does not reproduce every operating-system behavior or prove that every displayed connection is exploitable.

### Q11. What do nodes and edges represent?

**Suggested answer:** Modeled nodes represent assets such as servers, workstations, routers, firewalls, databases, and cloud assets. Edges represent connections. Live relationships come from observations. Modeled topology and observed relationships must retain their distinct meanings.

### Q12. Does connecting a laptop discover every vulnerability on it?

**Suggested answer:** No. Heartbeats register the endpoint. The live Windows agent adds observed connections and Defender events. Vulnerability findings have a separate ingestion endpoint. Registration alone does not establish a complete software inventory or vulnerability scan.

### Q13. Does Reality mode automatically train the world model?

**Suggested answer:** No. The current `/api/simulate` handler explicitly uses offline simulation and excludes real endpoint telemetry as attacker input. A future training pipeline would require deliberate collection, labeling, validation, and model-version management.

### Q14. Why can Reality Exposure or Patch ROI be empty?

**Suggested answer:** The backend checks whether sufficient live evidence exists before returning analysis. Connected laptops without the required findings or relationships do not justify a populated exposure report. We should show readiness information rather than substitute a demo result.

### Q15. What is the frontend technology stack?

**Suggested answer:** React with TypeScript, TanStack routing and query handling, and a Vite development workflow. The Python FastAPI service supplies the data. SQLite supports backend persistence. The repository also contains an older Streamlit interface.

### Q16. What makes the interface useful to an analyst?

**Suggested answer:** The analyst can move from endpoint status to topology, inspect evidence, and review remediation priorities. Error and empty states matter because an unavailable backend must not look like a healthy network. A successful frontend build is not the same as completed accessibility or usability validation.

## 4. World model and research depth

### Q17. What is a world model in this project?

**Suggested answer:** A transition predictor. Given graph state and a selected attack target, the GNN predicts each node's probability of being compromised in the next state. This is more specific than a general-purpose model of the entire enterprise.

**Code to show:** `src/models/gnn_world_model.py` and `src/simulator/transition_model.py`.

### Q18. What exactly enters and leaves the GNN?

**Suggested answer:** The input contains graph connectivity and 12 features per node. Eleven describe state and asset characteristics, and the twelfth flags the attacked node. The output is one sigmoid probability per node.

The state features include compromise status, normalized CVSS, vulnerability count, a four-category asset encoding, criticality, patch status, isolation status, and degree centrality. Database and cloud assets share the server category in this encoding.

### Q19. What is the implemented model architecture?

**Suggested answer:** The default GraphSAGE implementation has three convolution layers, a default hidden width of 64, normalization and dropout in hidden processing, and a final sigmoid output. GAT and GCN alternatives exist for comparison. Their presence does not establish that an ablation study has been completed.

### Q20. Do edge attributes influence the GNN prediction?

**Suggested answer:** The converter constructs edge attributes, but the current GraphSAGE forward method consumes `x` and `edge_index`, without `edge_attr`. Connectivity influences message passing. We should not claim that protocol or firewall attributes directly enter this GNN's prediction through edge features.

### Q21. Where do training labels come from?

**Suggested answer:** The training pipeline can generate transitions from the rule-based simulator and store them in HDF5. The target is the next-state binary compromise vector. This teaches the GNN the behavior represented by the simulator, not independently verified attacker behavior in production.

### Q22. If a simulator generates your labels, can your model exceed its knowledge?

**Suggested answer:** It may approximate that simulator or generalize patterns within the modeled distribution. That does not prove discovery of threats beyond the simulator's assumptions. We need independent scenarios and real evidence to test whether the learned model provides useful additional value.

### Q23. What are the loss and training metrics?

**Suggested answer:** The training code uses binary cross-entropy and records AUC, thresholded accuracy, and loss. It selects checkpoints using validation AUC. The configuration's `0.87` target is a target, not a measured result we can quote as achieved.

### Q24. How do you avoid train/test leakage?

**Suggested answer:** The current trainer uses a seeded 80/10/10 random split of dataset samples. Related transitions can therefore potentially span splits. A stronger evaluation should hold out whole episodes and network topologies, then test on unseen asset configurations.

### Q25. Does a high AUC mean the probability is accurate?

**Suggested answer:** No. Ranking quality and probability calibration answer different questions. We should evaluate calibration and performance specifically on newly compromised nodes, since already compromised nodes can make aggregate performance look better than the hard transition task.

### Q26. Does every simulation shown in the dashboard use the GNN?

**Suggested answer:** No. The current attack analyzer instantiates the rule-based `AttackSimulator`. It can use a trained Red policy for action selection, but that is distinct from using a learned GNN for state transitions. The GNN implementation and transition adapter exist elsewhere in the project.

**Judge follow-up:** Trace `/api/simulate`, `_run_attack_analysis`, the data provider, and `analyze_attack_paths`. A UI label saying “world model” is not sufficient evidence of GNN execution.

### Q27. Are you implementing Dreamer or DreamerV3?

**Suggested answer:** Our research motivation draws on learning environment dynamics and evaluating imagined scenarios. The present graph transition model is not a reproduction of the full Dreamer architecture. We cite those papers as research foundations, not as the exact algorithm running in the product.

### Q28. Can Onyx discover zero-day vulnerabilities?

**Suggested answer:** We have not demonstrated that. The current project models known or synthetic vulnerabilities and defined transitions. It can explore combinations within those assumptions. Discovery of a previously unknown software vulnerability requires different evidence.

### Q29. What happens if the model checkpoint is missing or incompatible?

**Suggested answer:** The attack analyzer can fall back to random action selection within the rule-based simulator if the Red policy fails to load. Results expose `policy_engine`. A completed run therefore does not prove that the learned policy loaded successfully.

### Q30. How would you prove that the learned world model helps?

**Suggested answer:** Compare the same scenarios using rule-based transitions and GNN transitions. Hold out topologies, vary seeds, and report transition quality, rollout errors, ranking quality, runtime, and calibration. Also compare against graph traversal and random-policy baselines. These are proposed experiments, not claimed results.

## 5. Reinforcement learning and attack paths

### Q31. What do the Red and Blue agents do?

**Suggested answer:** Red selects modeled attack targets. Blue has modeled patch and isolation actions. Their environments encode rewards and valid actions. These actions change simulated state and should not be confused with installing a patch or isolating a real laptop.

### Q32. Why MaskablePPO?

**Suggested answer:** The action space contains choices that are invalid in a particular state, such as unavailable targets or padded nodes. MaskablePPO can exclude invalid choices. Its suitability still needs comparison with simpler policies and inspection of action-mask correctness.

### Q33. What are the reward examples?

**Suggested answer:** Configuration examples reward Red for compromising nodes and reaching a critical asset, with a step penalty. Blue receives a penalty for newly compromised nodes and a reward when critical assets remain protected at episode end. Actual behavior must be checked in the environment methods, not inferred solely from configuration comments.

### Q34. Is your alternating training truly opponent-conditioned self-play?

**Suggested answer:** The script alternates Red and Blue training and evaluates the policies against one another. However, the inspected training environment constructors do not inject the current opposing policy. We should describe it as alternating training with joint evaluation until direct training against a frozen opponent is implemented and verified.

### Q35. Is there a technical weakness in Blue's action handling?

**Suggested answer:** Yes. The inspected mask places isolation actions at `MAX_NODES + i`, while action application uses the actual node count as the isolation offset. For networks smaller than the padded limit, these can disagree. This needs correction and behavioral tests before making strong claims about learned defense performance.

### Q36. What is an attack success rate?

**Suggested answer:** In the modeled evaluation, it is the number of runs reaching a critical asset divided by the number of evaluated runs. It depends on the model, policy, starting state, and episode budget. It is not a forecast of next month's breach probability.

### Q37. Are all displayed “top paths” successful exploit chains?

**Suggested answer:** The analyzer counts compromise sequences from all episodes, while tracking successes separately. A sequence can also reflect branching compromise events rather than one validated edge-by-edge exploit chain. We should explain those outputs as modeled episode sequences unless a path has been separately validated.

### Q38. What limits the supported network size?

**Suggested answer:** The current RL observations and actions use `MAX_NODES = 50`, and the environment checks that limit. The live inventory is a separate concern. We have not established enterprise-scale simulation or ingestion throughput through load testing.

## 6. Patch prioritization and measurement

### Q39. How does simulation-based patch ranking work?

**Suggested answer:** The optimizer compares a baseline attack success rate with the rate after a modeled patch. The difference is the estimated impact under the scenario. We need to verify that patch state survives graph copying and vulnerability tagging, and that the comparison uses controlled evaluation conditions.

### Q40. What is the cost-aware ROI formula?

**Suggested answer:** The code computes effort from asset-type hours, severity, and critical-asset multipliers, with a minimum of half an hour. It converts positive simulation impact into percentage points and divides by estimated effort.

```text
effort_hours = max(0.5, round(base_hours * severity_multiplier * critical_multiplier, 2))
risk_reduction_pp = max(0, simulation_impact * 100)
roi_score = risk_reduction_pp / effort_hours
```

This is a prioritization score in percentage points per estimated hour, not a financial return calculation.

### Q41. Give a simple worked example

**Suggested answer:** As an illustration, reducing modeled success from 40% to 25% gives 15 percentage points of reduction. If estimated effort is three hours, the score is five percentage points per hour. Those numbers illustrate the formula and are not project benchmark results.

### Q42. Does Reality-mode Patch ROI use that same experiment?

**Suggested answer:** No. The Reality endpoint computes a heuristic from imported finding severity, endpoint criticality, fix availability, and effort. Its response explicitly describes the reduction as a prioritization estimate. The field named `simulation_impact` in that response does not mean an attack simulation occurred.

### Q43. Can you add individual patch benefits together?

**Suggested answer:** Not reliably. Two patches may block the same route, and their effects can overlap. A multi-patch recommendation needs evaluation of combinations under a budget. Individually ranked results do not establish the optimal portfolio.

### Q44. What does a negative or tiny patch impact mean?

**Suggested answer:** It may reflect simulation variability, an ineffective modeled change, or a modeling defect. The cost ranking clamps negative impact to zero, so the underlying baseline and patched rates must remain available for diagnosis. More runs alone cannot fix incorrect assumptions.

### Q45. Which measurements would demonstrate practical value?

**Suggested answer:** Proposed pilot measures include agreement with analyst-reviewed priorities, time to a justified decision, critical-asset reachability after remediation, recommendation stability, and actual remediation effort. These require a defined baseline and pilot data before we claim improvement.

## 7. Live demonstration and multiple laptops

### Q46. What runs on the server laptop?

**Suggested answer:** The backend and web dashboard. The active backend launcher binds port `8020`, and the Vite proxy forwards `/api` to it. Client agents use the server's LAN address. The complete operational commands are in [the laptop runbook](SERVER_AND_CLIENT_LAPTOP_RUNBOOK.md).

### Q47. What does the simplest Windows connection agent collect?

**Suggested answer:** `windows_heartbeat_agent.ps1` sends registration and heartbeat metadata. It does not collect security telemetry or observed connections. `windows_live_endpoint_agent.ps1` additionally sends observed established connections and polls Defender detections. Each laptop needs a unique endpoint ID.

### Q48. Does a connected laptop prove that you detected an attack?

**Suggested answer:** No. A heartbeat proves that the reporting path works. A Defender event shows forwarded detection evidence. A synthetic event demonstrates the handling workflow. Each supports a different claim.

### Q49. How will you demonstrate an incident safely?

**Suggested answer:** Use the live endpoint agent's `-EmitSimulatedDetection` switch and explicitly label the event as a rehearsal. It creates no malware file. Then show the submitted event, its provenance, and how the dashboard presents it.

### Q50. Can your lightweight agents quarantine the client laptop?

**Suggested answer:** No. Both lightweight Windows agents declare `response_capable = false`. The backend has command queue and acknowledgement endpoints, and Demo mode can update simulated state. Actual containment requires an agent that executes the command and evidence of the resulting operating-system change.

### Q51. What does an acknowledgement test prove?

**Suggested answer:** The endpoint response test exercises a submitted detection, command lifecycle, and reported acknowledgement. It checks application behavior. It does not independently verify a firewall rule on a physical client.

### Q52. What happens when a client disconnects?

**Suggested answer:** The backend labels it offline after its last heartbeat becomes older than roughly 30 seconds. Stored evidence remains historical evidence. We should not present an old healthy state as a current observation.

### Q53. Can the presentation run without internet?

**Suggested answer:** The local dashboard, LAN reporting, and local scenarios can run with installed dependencies and required artifacts. New downloads, external feeds, or initial Sysmon setup may require internet. We should rehearse the exact offline configuration beforehand.

## 8. Security, privacy, and reliability

### Q54. How are clients authenticated?

**Suggested answer:** Ingest endpoints check the configured telemetry key through a Bearer token or `X-API-Key`. Response operations have a separate key. These shared keys do not establish individual device identity and should evolve into enrollment, per-device credentials, and revocation.

### Q55. Does the role selector enforce secure user permissions?

**Suggested answer:** A frontend role selector controls the interface, not trusted authorization. Server-side identity and permission checks must enforce access. The current prototype does not have a complete enterprise identity system.

### Q56. Is the backend production-ready for public internet exposure?

**Suggested answer:** No. API coverage for authentication is incomplete, development serving uses local HTTP, and shared keys have limitations. The response-auth helper also contains a localhost exception when no response key is configured. A local frontend proxy can make remote browser requests appear local to the backend, so keys and centralized authorization are essential.

### Q57. Could someone fake endpoint evidence?

**Suggested answer:** A caller holding the shared ingest key can submit endpoint claims. A reported hostname or endpoint ID is not cryptographic proof of identity. Device-specific authentication, anti-replay measures, rate limits, and server-side validation are needed to strengthen trust.

### Q58. What private information can the agents report?

**Suggested answer:** Depending on the agent, reports can include hostnames, IP addresses, connection endpoints, process information, and Defender event details or file paths. Collection should match the agreed pilot scope. Data minimization, retention, and access restrictions remain operational requirements.

### Q59. What evidence exists for software correctness?

**Suggested answer:** The repository contains regression tests for missing-policy/import fallback and the endpoint detection/acknowledgement lifecycle. Earlier checks passed four targeted tests and the frontend build. Those checks cover limited behavior and do not establish full security, model quality, or multi-laptop reliability. Re-run the relevant checks on the demonstration revision.

### Q60. How do you handle misleading or unavailable data in the UI?

**Suggested answer:** Reality pages use readiness and error states, and API polling depends on the selected mode. Some Demo values are fixed or illustrative. We must show data origin, freshness, and engine status when explaining a result. Accessibility and broader frontend test coverage remain areas to improve.

## 9. Feasibility, business, and roadmap

### Q61. What is the actual hardware cost and runtime?

**Suggested answer:** We have not established a general cost figure. Training time depends on topology, episodes, model, and hardware. GPU support exists, but a judge-facing claim should include a measured run with hardware specifications. Older documentation's time estimates are not a benchmark for every laptop.

### Q62. Who would pay, and why?

**Suggested answer:** A possible customer is an organization that spends significant analyst effort prioritizing remediation. A proposed business model could charge per managed environment or endpoint tier. Willingness to pay, pricing, and savings still require customer validation.

### Q63. Why would an organization choose this over existing products?

**Suggested answer:** We would evaluate ease of local deployment, transparency of recommendations, and usefulness for smaller teams. We have not completed a verified competitive benchmark and should not claim that existing products lack these features.

### Q64. What are the next three development priorities?

**Suggested answer:** First, verify the learned-transition integration and correct training/action semantics. Second, establish independent evaluation on held-out networks with calibrated, reproducible results. Third, harden identity, device trust, and response execution before a supervised pilot.

### Q65. What is the biggest risk to the idea?

**Suggested answer:** A convincing simulation can still produce poor advice if the network representation or transition assumptions are wrong. Our evaluation must test recommendation usefulness against evidence outside the simulator that generated the training data.

### Q66. Why should judges select this team?

**Suggested answer:** We have implemented a concrete workflow that connects an operational interface with graph analysis and research components. We can explain its computations and identify where validation remains. The strongest case is a transparent, repeatable demo and a specific plan for the next measurable milestone.

## 10. Claims judges may challenge immediately

| Claim to avoid without evidence | Defensible wording for this revision |
| --- | --- |
| “Every run uses our learned world model” | “The GNN module exists; the current analyzer uses rule-based transitions with optional learned action selection.” |
| “Fully implemented adversarial self-play” | “Alternating training and joint evaluation exist; opponent-conditioned training needs verification and completion.” |
| “We discover zero-days” | “We explore scenarios within modeled vulnerabilities and transition assumptions.” |
| “We predict the real probability of a breach” | “We measure modeled scenario success under stated assumptions.” |
| “Reality ROI is a measured reduction in attacks” | “Reality ROI is currently a heuristic prioritization estimate.” |
| “One click isolates any connected laptop” | “The backend has a command lifecycle; lightweight clients cannot perform containment.” |
| “Our heartbeat agent scans vulnerabilities” | “Heartbeat registration, detection forwarding, and finding ingestion are separate capabilities.” |
| “99% accurate” or “10,000 threats prevented” | “We will report named metrics, dataset scope, and measured results when validated.” |
| “Unlimited scale” | “The current RL environment has a 50-node padded limit; broader scaling requires evaluation.” |
| “NSA-grade” or “production-ready” | “A prototype with specified components, known limitations, and a pilot validation plan.” |

## 11. A practical mock judging round

Use this suggested 12-minute rehearsal with a teammate acting as a skeptical judge.

| Time | Judge's task |
| --- | --- |
| 0:00–1:00 | Ask for the user problem and 30-second pitch. Interrupt vague claims. |
| 1:00–3:00 | Ask the team to connect one laptop and trace its heartbeat to the dashboard. |
| 3:00–5:00 | Run an offline scenario. Ask which transition engine and policy actually executed. |
| 5:00–7:00 | Explain one patch result, units, assumptions, and the difference between Demo and Reality ranking. |
| 7:00–9:00 | Inspect model training, data splits, and the evidence supporting any accuracy claim. |
| 9:00–11:00 | Ask about client authentication, containment capability, and frontend role enforcement. |
| 11:00–12:00 | Ask for the largest limitation and the next measurable milestone. |

### Evidence to have ready

- A specific repository revision and the environment used for the demo.
- One registered client with a unique ID and a recent heartbeat.
- An incident event with clearly visible real or synthetic provenance.
- A saved scenario result with topology, episode count, seed, and policy-engine metadata.
- A worked patch calculation with effort units and the origin of the impact estimate.
- Model configuration, a checkpoint-load result, and actual evaluation outputs if claiming learned-model performance.
- Relevant regression-test results and a fallback demonstration whose data origin is explicit.
- A team contribution record based on work actually completed by each member.

### Suggested evaluation rubric

This is a preparation rubric, not an official competition rubric. Score each item from 1 to 5, and write down the missing evidence before assigning a higher score.

| Area | What earns confidence |
| --- | --- |
| Problem understanding | A specific user, decision, and reason current practice is insufficient |
| Technical understanding | The team can trace code execution and explain model assumptions |
| Working prototype | A repeatable workflow with visible data provenance |
| Validation | Honest baselines, controlled experiments, and reproducible results |
| Practical deployment | Clear onboarding, failure handling, and realistic resource needs |
| Security and trust | Accurate boundaries between observation, authorization, and action |
| Original contribution | A precise explanation of project work versus reused research and libraries |
| Communication | Concise answers with evidence and explicit limitations |

## 12. Research references and their relationship to Onyx

1. **Ha and Schmidhuber, World Models (2018).** Research foundation for learning an environment representation and training behavior within a learned model. This does not establish Onyx's real-world effectiveness. [Read the paper](https://arxiv.org/abs/1803.10122).
2. **Hafner et al., Dream to Control: Learning Behaviors by Latent Imagination (2019 preprint).** Dreamer learns behavior through trajectories imagined in a latent world model. Onyx's GraphSAGE predictor is a different implementation. [Read the paper](https://arxiv.org/abs/1912.01603).
3. **Hafner et al., Mastering Diverse Domains through World Models (2023 preprint).** DreamerV3 is relevant background for world-model-based learning across tasks. Its reported results do not transfer automatically to cybersecurity or this project. [Read the paper](https://arxiv.org/abs/2301.04104).
4. **Hamilton, Ying, and Leskovec, Inductive Representation Learning on Large Graphs (2017).** GraphSAGE provides the research basis for learning node representations by aggregating neighborhood information. [Read the paper](https://arxiv.org/abs/1706.02216).

## 13. Where to find evidence in the repository

| Topic | File or entry point |
| --- | --- |
| GNN architectures and prediction signature | [gnn_world_model.py](src/models/gnn_world_model.py) |
| Graph and action features | [pyg_converter.py](src/graph/pyg_converter.py) |
| GNN training, loss, and split | [train_gnn.py](src/training/train_gnn.py) |
| Training configuration targets | [config.yaml](configs/config.yaml) |
| Learned/rule-based transition interfaces | [transition_model.py](src/simulator/transition_model.py) |
| Actual attack analyzer and fallback | [attack_path_analyzer.py](src/analysis/attack_path_analyzer.py) |
| Simulation data providers | [data_provider.py](src/analysis/data_provider.py) |
| Alternating training and policy evaluation | [train_marl.py](src/training/train_marl.py) |
| Defender actions and masks | [defender_env.py](src/envs/defender_env.py) |
| Patch impact experiment | [patch_optimizer.py](src/analysis/patch_optimizer.py) |
| Effort and ROI calculation | [cost_optimizer.py](src/analysis/cost_optimizer.py) |
| Reality scoring, authentication, simulation, and commands | [server.py](web/backend/server.py) |
| Heartbeat-only client | [windows_heartbeat_agent.ps1](tools/endpoint_heartbeat/windows_heartbeat_agent.ps1) |
| Defender evidence and safe rehearsal event | [windows_live_endpoint_agent.ps1](tools/endpoint_heartbeat/windows_live_endpoint_agent.ps1) |
| Response lifecycle regression test | [test_endpoint_response_api.py](tests/test_endpoint_response_api.py) |
| Simulation fallback regression test | [test_api_simulate_regression.py](tests/test_api_simulate_regression.py) |
| Server and client startup instructions | [SERVER_AND_CLIENT_LAPTOP_RUNBOOK.md](SERVER_AND_CLIENT_LAPTOP_RUNBOOK.md) |

Use the inspected execution path as the authority when an older README, slide, UI label, or code comment makes a broader claim. Answer the question directly, show the evidence, and describe the next validation step when the evidence is incomplete.
