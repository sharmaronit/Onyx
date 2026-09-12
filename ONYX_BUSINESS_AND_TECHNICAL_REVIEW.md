# Onyx: Business and Technical Review

**Reviewed:** 12 September 2026  
**Stage you confirmed:** Customer conversations, no revenue yet. Prospects want software for office devices issued to employees.  
**Purpose:** Identify a credible route to revenue, mistakes to correct, and the work required before customer deployment.

## 1. My assessment

**Onyx has enough useful work to support a focused business experiment. It is not ready to be sold as dependable endpoint protection, autonomous cyber defence, or validated zero-day prediction.**

The most promising starting point, given your customer conversations, is a **device security operations product for small offices**, initially delivered with your help. It should help the office administrator see which company devices need attention, understand the supporting evidence, assign the work, and verify that the problem was addressed.

The current project contains three different product directions: an attack-simulation research platform, a vulnerability-prioritization tool, and an endpoint monitoring/response console. Each serves a different buying decision. Trying to commercialize all three together will make development, support, and sales harder.

Your first commercial question should be: **What will this office pay you to handle that its existing security tools and IT provider do not already handle adequately?** Installing software is a delivery mechanism; it is not the business outcome.

Your prospect may mean antivirus protection, device inventory, patch management, incident alerts, or remote administration. Their exact expectation, device count, operating systems, existing licenses, budget, and purchasing authority remain unconfirmed. Do not interpret interest in installing Onyx as a commitment to buy the current feature set.

**Recommended first promise, after implementing and validating the required workflow:**

> Onyx helps your IT administrator track security issues on company laptops, understand what needs fixing, and verify that assigned fixes were completed.

Keep existing endpoint protection in place. The inspected Windows collector forwards Microsoft Defender events; that does not make Onyx an independent antivirus engine.

## 2. What exists, and what it means commercially

This was an architecture-wide source review covering the core graph/simulation/ML modules, analytics, integrations, current web application, backend/database, endpoint collectors/installers, tests, configuration, runbooks, and selected evidence artifacts. I also compared the current web application with the other frontend copies at a structural level.

It was not a line-by-line audit of every generated file. Presentation binaries, all historical logs, model weights, archives, dependencies, private credentials, and customer database contents were not exhaustively inspected. No live customer deployment, load test, penetration test, or full retraining was performed.

| Area | What I found | Commercial interpretation |
|---|---|---|
| Network modelling | Graph objects, topology loading, CVE tagging, three supplied 10/20/30-node examples | A usable simulation foundation; not evidence of automatic, accurate enterprise discovery |
| Research engine | Rule-based simulation, GNN models, RL environments, training and checkpoints | Substantial research scaffolding, with important implementation and validation gaps |
| Patch analysis | Counterfactual optimizer, cost scoring, explanations, report generation | A useful product idea, but current correctness issues invalidate strong impact claims |
| Endpoint visibility | Heartbeats, observed connections, Defender/Sysmon collection, incident storage | Closest existing foundation to the office-device use case |
| Response | Command queue, reasons, timestamps, acknowledgements, firewall actions in one collector | Useful components; incomplete identity, delivery, recovery, and containment guarantees |
| Current UI | Overview, topology, exposure, simulation, patch and telemetry routes in `web/` | A substantial console, but customer onboarding and the remediation completion workflow need work |
| Evidence handling | Reality/demo branches, provenance fields, readiness checks, saved simulations | Good foundations for honest reporting; some field names and calculations undermine them |
| Business operations | No complete subscription, customer onboarding, or tenant-management workflow found in the reviewed application | Manual invoicing is acceptable initially; secure customer boundaries are essential |

**Keep these strengths:** typed graph structures, modular integrations, source-attributed findings, explicit response acknowledgements, saved simulation evidence, and the idea of reducing an administrator's work to a short action list. You do not need to discard the project or rewrite every module.

## 3. The product I would try to sell first

### Buyer and use case

Start with the warmest existing office prospect whose IT administrator or owner has a concrete, recurring security task and a budget. A working hypothesis is a Windows-heavy office with 20–100 company devices and limited dedicated security staff. This is a proposed segment, not a fact about your contacts.

The employee receives the company laptop. The administrator uses Onyx. The company pays. The employee should not need to interpret attack graphs, train models, or operate a SOC console.

The first version should answer:

1. Which company devices are enrolled, who owns them, and when did they last report?
2. Which devices have reported security findings or are missing required security evidence?
3. What should the administrator do, and what source supports that recommendation?
4. Who owns the action, when is it due, and has a later check verified completion?

### The smallest useful paid workflow

| Step | Customer experience | Implementation status or need |
|---|---|---|
| Set up organization | Administrator signs in and defines the approved device group | Add authenticated administrator identity and isolation |
| Enroll devices | IT installs a trusted package or connects an existing management source | Harden enrollment, installer verification, credential handling, and uninstall |
| Review coverage | Inventory distinguishes reporting, offline, unsupported and unknown devices | Extend current heartbeat inventory; add owner and lifecycle management |
| Review issues | A short queue displays source, time, device, severity, and recommended action | Reuse telemetry/findings; remove unsupported confidence claims |
| Assign work | Administrator assigns a fix and due date | Add remediation owner, state, exceptions, and ticket/CSV export |
| Verify | A later inventory scan, event, or operator review confirms the result | Implement evidence-based closure; containment alone must not close an incident |
| Report | Weekly summary shows coverage, overdue issues, completed work and unresolved questions | Reuse reporting components with truthful metrics |

Security posture checks such as antivirus status/signature age, OS update status, firewall state, and disk encryption could be valuable **if prospects need them**. The inspected live Windows collector does not already provide a complete posture assessment. Add a small agreed set, with explicit collection permissions and timestamps. Collect security metadata needed for the service, avoiding unnecessary employee file contents or activity monitoring.

The first deployment should be a supervised, read-only cohort of perhaps 10–25 approved devices after the deployment blockers below are addressed. Those numbers are pilot scope suggestions, not tested capacity claims. Establish reliability on a few lab devices first.

### What the buyer must understand

There is a material difference between receiving an antivirus alert, identifying a vulnerable application, predicting a simulated attack path, and preventing an actual attack. Explain exactly which one Onyx supplies.

If the buyer really wants established antivirus, ransomware protection, remote wipe, application deployment, or full device management, Onyx does not currently satisfy that request. You can still earn revenue by helping the buyer deploy and operate an appropriate existing platform, with Onyx added only where it solves an additional measured problem. Third-party licenses and support obligations must be priced separately and described accurately.

## 4. Competition and differentiation

The competitive issue is especially serious for an employee-device product. Microsoft currently lists Defender for Business at **US$3 per user per month, paid yearly, excluding tax**, with up to five devices per user and up to 300 users. This is the US public offer checked for this review, not an Indian quote or a per-device price. Microsoft describes endpoint protection, vulnerability management, and automated investigation/remediation, and includes Defender for Business in Microsoft 365 Business Premium. Ask what the prospect already owns before quoting Onyx. [Microsoft product and pricing page](https://www.microsoft.com/en-us/security/business/endpoint-security/microsoft-defender-business)

| Alternative | Established capability described by its provider | Implication for Onyx |
|---|---|---|
| Microsoft Intune | Device/app management and device security/compliance workflows | Do not promise an MDM replacement; consume existing management evidence where useful. [Documentation](https://learn.microsoft.com/en-us/intune/) |
| Wazuh | Open-source SIEM/XDR and software-inventory-based vulnerability detection | A dashboard that displays events and CVEs is not enough differentiation. [Platform](https://wazuh.com/platform/overview/), [vulnerability detection](https://documentation.wazuh.com/current/user-manual/capabilities/vulnerability-detection/index.html) |
| XM Cyber | Attack-path choke-point remediation and validation | The claim that one fix can interrupt many paths is already established positioning. [Remediation operations](https://xmcyber.com/platform/remediation-operations/) |
| Tenable One | Exposure prioritization using technical/business context and attack paths | Graphs and contextual prioritization alone will not distinguish Onyx. [Exposure prioritization](https://www.tenable.com/products/tenable-one/capabilities/exposure-prioritization) |
| Pentera / Cymulate | Security validation, exposure analysis, and remediation workflows | Distinguish inferred simulation results from experimentally validated exploitability. [Pentera](https://pentera.io/pentera-platform/), [Cymulate](https://cymulate.com/solutions/exposure-management/) |

These are vendor descriptions, not independent performance comparisons. They establish competitive overlap; they do not prove unmet demand for Onyx.

**A possible reason to buy Onyx:** the buyer wants someone to turn scattered device evidence into accountable, completed work, with a simpler workflow and a clearly scoped support service. Test that proposition against the buyer's current process. Do not assume the incumbents cannot provide it.

Your future defensibility could come from reliable integrations, normalized device histories, effective remediation workflows, customer trust, and measured improvements in administrator productivity. MARL becomes commercially meaningful only if it improves outcomes over simpler methods.

## 5. Mistakes and technical blockers

Priority meanings: **P0** blocks customer deployment or a core paid claim; **P1** should be fixed before a repeatable paid rollout; **P2** is maintainability or later product work. These priorities depend on scope: a simulation bug blocks a simulation-based promise, while an insecure installer blocks employee-device installation.

### P0 — Customer access and device identity are not strong enough

The frontend role is selected locally and stored in browser localStorage. It is a view preference, not authenticated authorization: [web/src/lib/rbac.tsx](web/src/lib/rbac.tsx), lines 13–36.

Many backend routes expose data or accept changes without authenticated ownership checks, including endpoint inventory, telemetry, notification deletion, preferences, and logs: [web/backend/server.py](web/backend/server.py), lines 1218, 1559, 1596, 2450, and 2682. Database tables do not provide tenant boundaries for the main endpoint/incident/command data: [web/backend/database.py](web/backend/database.py), lines 105–259.

Agent heartbeats, command polling, and acknowledgements use a shared ingest credential while accepting caller-supplied endpoint IDs. A device credential is not bound to one specific endpoint. Response audit identity is also supplied by the caller: `server.py`, lines 1202–1209, 1507–1513, and 1520–1543.

**Fix:** authenticated administrator sessions, backend permissions, trusted audit identities, and separate revocable device credentials. Use a separate secured deployment/database for each initial customer. Later multi-tenancy must scope records, queries, jobs, caches and files; adding a tenant field alone is insufficient. Protect reads as well as writes.

### P0 — Installer and publishing workflows could expose credentials

The internet setup script prepares a bundle containing a key, serves the publish directory using an unauthenticated HTTP server/tunnel, and writes a state file containing an API key inside that directory: [tools/sysmon/setup_internet_access.ps1](tools/sysmon/setup_internet_access.ps1), lines 377–445. Direct-connect bundle generation embeds credentials in launchers: [tools/endpoint_heartbeat/build_direct_connect_bundles.py](tools/endpoint_heartbeat/build_direct_connect_bundles.py), lines 43, 71, 106, and 138.

The inspected download flow executes downloaded helpers without consuming the builder's integrity manifest. Some installation tasks run with SYSTEM/highest privileges. This makes trustworthy software delivery a core product requirement, not packaging polish.

**Fix:** authenticated distribution, short-lived one-use enrollment tokens, per-device credentials, verified installers/updates, and no secret-bearing state or logs in a public download directory. Review previously shared bundles before reusing their credentials. **The review established the risky code path; it did not establish that a live public endpoint currently exposes a secret. No secret values were inspected.**

Response authorization also accepts local callers when its separate response key is absent: `server.py`, lines 1028–1037. Proxy/tunnel source handling can make this unsafe. Remove the local-source exception and fail closed. The precise network bypass was not runtime-tested.

### P0 — Device response promises exceed the implementation

“Disconnect server link” updates a database flag and hides a graph relationship; it does not instruct an endpoint to disconnect: `server.py`, lines 1454–1465 and 1398–1403; `database.py`, lines 568–579.

The Sysmon forwarder's quarantine action blocks selected TCP ports. It is not complete host isolation, and other traffic is outside those rules: [tools/sysmon/forwarder.py](tools/sysmon/forwarder.py), lines 349–384. Successful acknowledgement automatically resolves open incidents: `server.py`, lines 1551–1555. Containment is not proof of remediation.

Several clients explicitly declare `response_capable=false`, including the live Windows demonstration agent: [tools/endpoint_heartbeat/windows_live_endpoint_agent.ps1](tools/endpoint_heartbeat/windows_live_endpoint_agent.ps1), line 35. Command admission must enforce actual capabilities.

**Fix:** accurately label each action, distinguish detected/contained/remediated/verified states, enforce endpoint capabilities, and test recovery. Start the paid product with read-only observation. Release disruptive controls only after controlled tests prove the exact policy, delivery, acknowledgement and rollback behavior.

### P0 — The patch optimizer restores the vulnerability it removed

The optimizer removes a CVE from a copied node, then the evaluator re-tags the graph from the unchanged software/version database on every episode. That restores the CVE: [src/analysis/patch_optimizer.py](src/analysis/patch_optimizer.py), lines 69 and 160–165; [src/graph/cve_tagger.py](src/graph/cve_tagger.py), line 71.

**Confirmed in memory:** the selected CVE was absent immediately after removal and present again after the evaluator's re-tagging operation. This affects the CLI optimizer and the API branch that calls it at `server.py:653`; it is separate from the reality-mode heuristic ranking.

**Consequence:** reported patch improvement can reflect differences between effectively unpatched evaluations. Do not use those results to justify customer patch decisions or superiority claims.

**Fix:** preserve the intervention throughout every evaluation; test it on a small graph with a known blocking patch; use controlled paired seeds. The current seed also uses Python's process-dependent `hash()`, which weakens reproducibility across processes. Recompute affected evidence after fixing the implementation.

### P0 — At least one real CVE identifier is attached to the wrong vulnerability

[data/cve/cve_dataset.json](data/cve/cve_dataset.json), line 4, assigns `CVE-2024-1002` to Apache 2.4.49 path traversal. The official NVD record describes a Totolink N200RE vulnerability. [NVD record](https://nvd.nist.gov/vuln/detail/CVE-2024-1002)

This is a verified example, not an assertion that every record was checked. Using real-looking identifiers for invented scenarios can cause incorrect customer remediation.

**Fix:** validate every production identifier/product/version mapping against attributed sources. Use unmistakably synthetic IDs for synthetic fixtures, store them separately, and preserve source/observation timestamps for imported findings.

### P1 — The stated world-model/self-play architecture is not fully wired

`AttackerEnv` accepts a `transition_model` parameter but does not use it; reset constructs the rule-based `AttackSimulator`: [src/envs/attacker_env.py](src/envs/attacker_env.py), lines 116 and 164.

The MARL training loop trains ordinary attacker and defender environments separately; the learned opponent is not injected into those training environments. Red-vs-blue evaluation does occur, but the training comments about freezing the opponent overstate the implemented coupling: [src/training/train_marl.py](src/training/train_marl.py), lines 173–180 and 214–240.

**Fix:** either correctly implement and verify learned transitions/opponent coupling, or describe the current system accurately. For the office-device business, defer this research work until a customer outcome requires it.

### P1 — Defender isolation actions have an indexing bug

The mask enables isolation at `MAX_NODES + i`; the action handler interprets isolation at `number_of_real_nodes + i`: [src/envs/defender_env.py](src/envs/defender_env.py), lines 168–170 and 190. A similar mismatch exists in MARL evaluation at `train_marl.py`, lines 128–140.

**Confirmed in memory:** on the 20-node example, action 50 was permitted by the mask but isolated no node. This is a simulation correctness issue, distinct from the operational firewall issue above.

**Fix:** use one action encoding everywhere, test all allowed actions across topology sizes, and retrain/re-evaluate artifacts affected by the correction.

### P1 — Ranking scores are presented with risk-reduction semantics

Reality-mode patch ROI computes a capped formula from CVSS, an asset multiplier, fix availability, and effort; it does not run a patch counterfactual: `server.py`, lines 1375–1388. Its provenance correctly calls the result an estimate, but the field is named `simulation_impact` and the UI adds the values into an “Estimated reduction” percentage.

The demo patch page also sums individual impacts and labels the result cumulative risk reduction “if all applied”: [web/src/routes/patches.tsx](web/src/routes/patches.tsx), lines 150–151 and 202–217. Overlapping interventions cannot generally be added. Two critical findings can each receive a heuristic value of 1, producing a displayed total of 200% without measuring any risk reduction.

The older telemetry patch path can label formula-derived results `measured`: `server.py`, lines 603–628; [src/integrations/telemetry_mapping.py](src/integrations/telemetry_mapping.py), lines 195–218.

**Fix:** call heuristic outputs priority scores. Distinguish observed data from estimated effects and measured outcomes. For a combined patch plan, evaluate the combined intervention. A change from 60% to 40% simulated success is 20 percentage points, or 33.3% relative reduction; neither proves a customer's real breach probability fell by that amount. Effort-normalized priority is not financial ROI.

### P1 — Endpoint command delivery needs recovery semantics

Polling marks a command delivered before the response is confirmed received. Later polls select pending commands only. A delivered command remains active and can prevent a new action: `database.py`, lines 160–163 and 621–639; `server.py`, lines 1500–1516.

**Fix:** delivery leases, retries, idempotent execution, expiry, reconciliation and emergency recovery. Test dropped HTTP responses, agent restarts, offline devices, duplicate acknowledgements and interrupted restore. These are predictable office support cases.

### P1 — Cache and demo boundaries can produce misleading results

Patch results are cached by mode without sufficient topology identity: `server.py`, lines 2322–2347. Shared latest-result/report state also exists. A request for one topology can receive results from another.

The sample-data route writes into ordinary telemetry and clears reality caches without authentication: `server.py`, lines 1765–1785. The fixed server-side live collection workflow also lacks authorization at lines 1795–1835; this is an exposed privileged workflow, not a finding of arbitrary command execution.

**Fix:** isolate demo storage and restrict operator actions. Key artifacts and caches by customer, input snapshot/topology, model version, parameters and run ID. Add explicit stale/unknown states and input-coverage thresholds: the current readiness function primarily checks whether some inventory, relationships and findings exist, not whether coverage is complete (`server.py:1310`).

### P1/P2 — UI and runtime readiness need a release gate

The current TypeScript check failed with **16 diagnostics** across simulation, telemetry, topology and Vite configuration. Problems include possibly undefined saved-run data, implicit types and optional-property mismatches. This establishes a failed type check, not that every screen fails at runtime.

The local `.venv` Python launcher also failed because it points to an unavailable base interpreter. The bundled `.runtime-python310` worked for the bounded checks in this review. `web/scripts/dev-backend.mjs` normally prefers the existing `.venv` launcher, so a reliable documented runtime selection matters.

Demo overview values include a fixed weekly delta, mean path length, coverage and historical trend: [web/src/routes/index.tsx](web/src/routes/index.tsx), lines 73–80. Reality has a separate branch, which is good; maintain visible demo labels on screens and exports. “Save world-model” currently saves browser configuration parameters, not a model artifact: [web/src/routes/simulation.tsx](web/src/routes/simulation.tsx), lines 105 and 128.

Some backend workflows are placeholders: mock report lists at `server.py:2417`, and training-start updates status without launching a worker at `server.py:2639`. Choose one maintained frontend (`web/` appears current), document the purpose of `web_backup/`, `Security Sentinel/`, and Streamlit, and archive copies deliberately. No repository cleanup was performed in this review.

## 6. Scientific and product claims to change

The README's zero-day language exceeds what the inspected system demonstrates. The original concept document's “NSA-level” comparison is also unsuitable as a substantiated commercial claim.

The model is trained on generated simulator transitions, with random dataset splitting: [src/simulator/episode_generator.py](src/simulator/episode_generator.py), line 122; [src/training/train_gnn.py](src/training/train_gnn.py), line 177. Good performance on that data can demonstrate learning the simulator, but not real-world prediction. Splitting by held-out topology, episode and time would provide a stronger generalization check than nearby transition samples alone.

The core compromise probability starts from `max_cvss / 10`: [src/graph/network_graph.py](src/graph/network_graph.py), line 73. CVSS communicates severity; it is not directly a per-attempt exploit probability. EPSS estimates whether a published CVE will be exploited in the wild within 30 days, which is also not an individual company's breach probability. [FIRST CVSS FAQ](https://www.first.org/cvss/faq), [FIRST EPSS](https://www.first.org/epss/)

If you keep the simulation product, compare it with a transparent baseline using verified vulnerability data, exploitation evidence, exposure, asset importance, and simple graph analysis. Do not multiply CVSS and EPSS and call the result calibrated risk. [FIRST usage guidance](https://www.first.org/epss/using-epss)

The RL environments have a hard 50-node limit (`src/envs/attacker_env.py:29,133`). That does not prove the telemetry backend has the same limit, but it prevents an unsupported claim that the existing RL setup can model a large employee fleet. Benchmark the proposed fleet workflow separately from simulation.

Your April evidence summary compares a simulated baseline with a three-event telemetry comparison. That is not a controlled same-environment before/after patch experiment: [reports/evidence/bundle-20260416-093950/summary.md](reports/evidence/bundle-20260416-093950/summary.md). Older checklists also leave validation unfinished; newer code is more explicit about separating simulation. Treat these artifacts as limited historical evidence, not current proof of commercial accuracy.

Showing uncertainty and provenance is good. Adjusting a demo until its percentages look plausible is not validation. Validate first, then explain the result clearly, including an unexpectedly high or low result.

## 7. Pricing and a route to first revenue

**These are proposed experiments, not proven market prices, earnings forecasts, or amounts your prospects have agreed to pay.** INR examples are offered for a possible local-office sale; the prospect's geography is unconfirmed. Adjust to their actual budget and your cost of delivery.

| Offer | Proposed starting experiment | Scope |
|---|---|---|
| Paid readiness assessment | ₹10,000–25,000 one-time | Review existing device/security exports, identify coverage gaps, deliver a human-reviewed action plan; no new production agent required |
| Controlled device pilot | ₹20,000–40,000 for 30 days | After security gates: one office, 10–25 approved devices, supervised onboarding, read-only findings, two reviews and an outcome report |
| Continuing service with Onyx | Test ₹150–300 per managed device/month, with a ₹5,000–10,000 organization minimum | Defined evidence refreshes, action tracking, reports, and tightly limited business-hours support |

Choose a concrete quote within a range for each proposal. Do not present a confusing menu of speculative tiers. Price extra onboarding work separately; customer-owned endpoint protection licenses are separate. Do not include unlimited support, 24/7 monitoring, or incident response you cannot staff.

The willingness to pay must come from the additional workflow/service outcome. Microsoft's per-user bundled protection price makes charging a similar amount merely to display Defender alerts difficult to justify. If customers only want a familiar protection package, a configuration/support service around existing tools may earn revenue sooner than developing another agent.

**Illustrative economics:** 50 devices at ₹200/device/month yields ₹10,000 monthly revenue. If delivery/support consumes four hours at a replacement cost of ₹1,000/hour, infrastructure costs ₹1,000, and other direct costs are ₹500, contribution is ₹4,500 before sales, general overhead and taxes. At ten delivery hours, the same account loses ₹1,500 before those additional costs. Founder time is not free.

Ten identical accounts would produce ₹1 lakh monthly recurring revenue, not ₹1 lakh profit. At four support hours per account that already requires 40 hours each month, before sales and development. There is no evidence yet that ten such accounts can be won or retained.

Start with invoices and a simple written scope. Automated billing can wait. Define billable device counts, replacement/offboarding rules, included support, payment timing and cancellation so disputes do not consume your margin.

## 8. Convert your existing conversations into purchases

Return to your existing contacts with a specific proposed outcome. Do not restart broad discovery or spend another month adding features without a purchasing conversation.

For each prospect, record their device count/OS, current antivirus/management platform, most recent security problem, administrator, budget owner, acceptable data collection, requested outcome, quote and decision date. Ask them to show how they handle that task today.

Use a proposal along these lines:

> For a fixed 30-day pilot, we will review an agreed group of company laptops, show which devices need attention with supporting evidence, assign actions with your administrator, and verify completed work. Your current security protection stays in place. We will agree the device scope, support hours, price, and success measures before starting.

**Proposed pilot success measures to agree with the buyer:**

- Enrollment succeeds on the approved supported cohort, with successful uninstall/recovery demonstrated.
- The inventory explains missing and stale devices rather than treating them as healthy.
- The administrator can verify the source of each material recommendation.
- Planning/review time improves against the recorded current process.
- Several agreed actions reach independently verified completion.
- The buyer wants a second paid month at a stated price.

Measure incorrect recommendations, missed expected events, collector failures, and support time too. Avoid using a simulated risk percentage as the acceptance criterion. Agree data freshness, performance and delivery thresholds for the pilot; none has been measured at fleet scale here.

My suggested commercial gate is two paid pilots, followed by at least two renewals/expansions among the first three completed pilots, before broadening the platform. These are management targets, not industry benchmarks. If prospects praise the demo but will not provide a budget, data, an administrator and a decision date, the sale is not yet qualified.

## 9. What to do over the next 90 days

This is an order of work and decision gates, not a promise that every engineering task fits the calendar. A small team should defer features rather than skip deployment safety.

| Period | Commercial work | Engineering work | Exit evidence |
|---|---|---|---|
| Days 1–7 | Qualify current office contacts; confirm protection vs monitoring expectations; quote a paid readiness assessment | Document supported capabilities; remove unsupported sales claims; catalogue P0 issues; standardize the working runtime | Named buyer, defined problem, concrete scope and purchase decision |
| Days 8–21 | Deliver export-based assessment if purchased; define pilot acceptance and support scope | Secure admin access, device identities and distribution; isolate customer data; implement a read-only deployment path; fix type errors and misleading metrics | Lab enrollment/uninstall, authorization checks, recovery checks and reliable evidence collection |
| Days 22–45 | Run the first paid device pilot only if its deployment gates pass | Add owner/action/verification workflow; observe a small approved cohort; handle stale/offline devices and failed deliveries | Accepted findings, completed actions, measured support effort, buyer review |
| Days 46–60 | Ask for renewal and one introduction; validate a second buyer with the same problem | Improve the most expensive onboarding/support steps; test backup/restore and retention; avoid bespoke feature sprawl | Repeatable delivery and a paid continuation |
| Days 61–90 | Assess renewal and contribution margin; standardize one offer | Expand cohort/source coverage only after reliability evidence; keep research separate; introduce queues/quotas as load requires | Evidence of repeatable sales and sustainable delivery cost |

If the endpoint deployment gates are not ready, continue the paid assessment/service using existing customer exports instead of distributing an unsafe agent. If the customer does not value the observation/remediation workflow, reconsider the offer before building more of it.

**Defer:** new dashboard themes, more frontend rewrites, GPU training for its own sake, broad multi-OS control, autonomous patching, a 24/7 SOC promise, complex billing, and an MSSP multi-tenant platform. Those are not the next obstacle to the first sound sale.

## 10. Development discipline that will help revenue

Create a maintained release path for the current application. The reviewed root was not recognized as a Git repository in this workspace; that does not establish that your project has no remote or other checkout. Confirm version-control ownership and keep generated/private artifacts separate. The root `.gitignore` ignores all `data/`, so deliberately preserve sanitized fixtures elsewhere or explicitly include them for reproducible builds.

Run type checking and meaningful regression tests in CI. Add tests for patch intervention preservation, action encoding, customer isolation, device identity binding, stale data, cache scope, installer/update trust, command recovery and verification of closure. A green HTTP response test is not proof that the business recommendation is correct.

Use one dependable installation/update process. For software living on employee devices, successful reboot recovery, offline buffering, acceptable resource use, revocation, uninstall and signed/verified updates matter more than another chart. Existing collectors are useful starting points, not demonstrated fleet-management maturity.

SQLite can be adequate for a small isolated pilot. First prove retention, backups, restore, failure handling and measured load behavior. Changing the database alone does not provide security or scalability. Likewise, containerization is useful only as part of a working, reproducible release and operating process.

Make the default dashboard operational: devices needing attention, evidence freshness, assigned work and verified completion. Keep the research replay accessible as a clearly labelled research feature if it remains useful. The current console exposes concepts such as topology keys and response keys that an office administrator should not routinely need to manage.

## 11. Verification performed for this review

| Check | Result and limitation |
|---|---|
| Frontend `node .\node_modules\typescript\bin\tsc --noEmit` in `web/` | Failed with 16 diagnostics. No source changes made to fix them. Production build/browser testing was not performed. |
| Focused endpoint response tests | Two existing tests passed during the isolated backend review, using temporary persistence and no real endpoint/firewall execution. |
| `.runtime-python310\python.exe -B -m unittest tests.test_attack_path_regression -v` | One existing missing-agent/import regression test passed. This validates that narrow fallback case. |
| In-memory patch re-tag check | Confirmed a removed CVE is restored by the evaluation preparation operation. No full optimizer run or model training required. |
| In-memory defender action check | Confirmed mask-permitted action 50 isolates no node on the 20-node example. No actual device action executed. |
| Python runtime check | `.venv` launcher failed due to unavailable base interpreter; bundled Python 3.10.11 worked with NumPy 1.26.4. |
| External fact checks | Current primary vendor sources, FIRST guidance, and the official CVE record were checked. Prices are dated observations; proposed Onyx prices are experiments. |

The older [test_execution_report.md](test_execution_report.md) records a checkpoint compatibility failure. This review did not reload all checkpoints, so that historical report is not presented as a newly reproduced current model-loading failure. No dependency vulnerability audit was performed, and no specific package CVE is asserted.

No production source code, customer data, device policies, credentials, or running services were intentionally changed. The requested review document is the deliverable.

**My recommendation:** use the existing office conversations to sell a tightly scoped, evidence-based service and earn the right to expand the software. The first durable milestone is a customer who understands what Onyx actually does, pays for a measurable outcome, and renews because the office's work became easier. Correctness, trusted deployment and completed remediation will determine that outcome more than the complexity of the AI architecture.
