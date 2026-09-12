# Onyx Remediation and Product Readiness Plan

**Source review:** [ONYX_BUSINESS_AND_TECHNICAL_REVIEW.md](ONYX_BUSINESS_AND_TECHNICAL_REVIEW.md)
**Goal:** Make Onyx safe and credible for a supervised, read-only office-device pilot, then improve the research engine without blocking early revenue.
**Recommended delivery window:** 12 weeks for a small focused team. Dates are sequencing targets, not fixed promises.

## 1. Product decision

Build the first commercial version around this promise:

> Onyx helps an office administrator see which company devices need attention, assign the required work, and verify that the work was completed.

The first paid version should complement existing antivirus, EDR, MDM, and vulnerability scanners. Attack simulation remains a clearly labelled research feature until its correctness and validation gates pass.

The initial pilot must be:

- One organization in an isolated deployment
- One authenticated administrator group
- 10–25 authorized Windows devices or an existing scanner export
- Read-only collection and recommendations
- No autonomous containment, patching, or remote device control
- Explicit data retention and uninstall procedures
- A human-reviewed action list and verification report

## 2. Problem summary and value of each fix

| Priority | Problem | Brief explanation | Planned fix | Value added |
|---|---|---|---|---|
| P0 | Product scope is unclear | The project mixes endpoint operations, vulnerability prioritization, and attack-simulation research. Buyers cannot easily understand what they are purchasing. | Make device visibility and remediation tracking the default product. Move simulation to a labelled research area. Publish a supported-capabilities matrix. | Clearer sales message, smaller support surface, faster path to a paid pilot. |
| P0 | Frontend roles are not security | A user can change their role in browser storage; many API reads and writes do not verify identity or ownership. | Add real administrator authentication, server-side authorization, trusted audit identities, and deny-by-default API protection. | Prevents unauthorized access and gives customers a defensible security boundary. |
| P0 | No customer/tenant isolation | Core tables, caches, reports, and IDs are shared without an organization boundary. | Use one isolated deployment per early customer. Add `organization_id` throughout the schema and enforce it from authenticated context before offering multi-tenancy. | Prevents cross-customer data exposure and enables safe expansion to multiple customers. |
| P0 | Device identity uses a shared key | A shared agent key can report or poll as another endpoint because credentials are not bound to a device. | Use one-time enrollment tokens followed by a unique, hashed, revocable device credential bound to the organization and endpoint. | Limits damage from one compromised device and supports device revocation/offboarding. |
| P0 | Installer/distribution can expose secrets | Some bundles embed reusable credentials and can be served from an unauthenticated directory. Downloaded helpers are executed without a complete trust check. | Replace public bundles with authenticated downloads, short-lived enrollment tokens, signed/verified packages, secure local secret storage, and key rotation. | Makes agent installation acceptable to an IT administrator and reduces supply-chain and credential risk. |
| P0 | Response controls overstate what happens | “Disconnect server link” changes display state only. Quarantine blocks selected TCP ports, not all network traffic. Containment may automatically close incidents. | Disable response controls for the first pilot. Rename or remove misleading actions, model incident states accurately, enforce device capability, and later implement/test exact containment behavior and rollback. | Avoids unsafe customer actions, misleading claims, and high-cost recovery incidents. |
| P0 | Patch optimizer cancels its own patch | The evaluator re-tags each graph, restoring the CVE that the optimizer removed. Reported patch impact is therefore unreliable. | Preserve interventions during evaluation, use paired deterministic seeds, add a known-answer regression test, and regenerate all affected evidence. | Restores trust in the core “which fix matters most” feature. |
| P0 | Example CVE data contains incorrect real identifiers | At least one real CVE ID is assigned to the wrong product and vulnerability. | Separate synthetic fixtures from production data, use `SYNTH-*` IDs for invented examples, validate imported CVEs against attributed sources, and record source/freshness. | Prevents customers from receiving technically false remediation advice. |
| P1 | Defender isolation action encoding is inconsistent | The mask enables one range of action numbers while the handler decodes another, so permitted isolation actions can do nothing. | Use one action codec based on `MAX_NODES`, reuse it in training/evaluation, test every action for 10/20/30-node graphs, then retrain affected agents. | Makes Blue-agent behavior real and reproducible instead of silently ineffective. |
| P1 | World-model and self-play claims exceed wiring | `transition_model` is accepted but ignored; Red and Blue agents train separately rather than against the current learned opponent. | First correct the product documentation. Then implement a transition adapter and frozen-opponent environment only if research remains a priority. | Honest positioning immediately; later, a real technical differentiator that can be evaluated. |
| P1 | Priority scores look like measured risk reduction | Heuristic CVSS/criticality formulas are returned with probability-like names, and individual impacts are added into totals that can exceed 100%. | Rename to `priority_score`, model provenance as a typed enum, remove additive “cumulative reduction,” and calculate combined effects only through an actual combined counterfactual. | Makes reports understandable, defensible, and less likely to mislead a buyer. |
| P1 | Command delivery can get stuck | A command is marked delivered before receipt is guaranteed; a lost response can leave it active and block recovery. | Add leased delivery, attempt counters, expiry, idempotency keys, acknowledgements, reconciliation, cancellation, and an emergency recovery path. | Improves reliability and reduces support emergencies when devices go offline or restart. |
| P1 | Cache and demo data can contaminate results | Cache keys omit customer/topology details and demo sample routes can write into operational stores. | Use composite cache keys, immutable run IDs, separate demo storage, authenticated demo-loading routes, and full provenance on artifacts. | Prevents one environment’s results from appearing in another customer’s report. |
| P1 | Readiness checks prove presence, not coverage | Having one asset, relationship, and finding can mark analytics ready even when most devices are missing or stale. | Track expected inventory, reporting coverage, freshness, unsupported devices, collector errors, and minimum coverage thresholds. | Administrators can trust “healthy,” “unknown,” and “offline” as different states. |
| P1 | Remediation workflow is incomplete | Findings can be displayed, but owners, due dates, exceptions, verification, and reopening are not a complete operational workflow. | Add action ownership, due dates, statuses, comments, verification evidence, exception reasons, CSV/ticket export, and weekly reports. | Converts security data into completed work—the most sellable customer outcome. |
| P1 | TypeScript and runtime checks fail | The current frontend type check reports errors, and the preferred local virtual environment points to a missing interpreter. | Fix type errors, make runtime discovery deterministic, pin supported versions, and gate releases on build and focused tests. | Reduces demo failures, onboarding friction, and support time. |
| P1 | Demo and placeholder features look operational | Some dashboard metrics are fixed, “Save world-model” saves configuration, and reports/training endpoints include placeholders. | Label every demo value, rename actions precisely, remove or complete placeholders, and keep generated demo data out of reality mode and exports. | Increases buyer confidence and prevents accidental overpromising. |
| P1 | Scientific evaluation does not establish real-world performance | The model learns simulator-generated transitions, uses random transition splits, derives probability from CVSS, and has limited comparison evidence. | Create transparent baselines, split by topology/episode/time, measure calibration and ranking quality, test interventions, and validate on authorized held-out lab/customer evidence. | Turns research claims into evidence and reveals whether ML improves customer decisions. |
| P2 | RL simulation is limited to 50 nodes | The fixed action/observation encoding prevents the existing RL design from representing larger networks. | Benchmark customer fleet workflows separately. Later use variable-size graph policies, hierarchical simulation, or scoped subgraphs if customer value justifies it. | Avoids false scale claims now and provides a path to larger environments later. |
| P2 | Release and operating discipline are incomplete | Multiple frontends, development servers, local SQLite, missing migrations/retention/backup validation, and no single release gate increase operational risk. | Declare `web/` canonical, archive alternatives, add migrations, backup/restore, retention, CI, versioned releases, deployment docs, and observability. | Creates repeatable deployments and reduces the cost of supporting each customer. |

## 3. Ordered implementation plan

### Phase 0 — Freeze unsafe promises and define the pilot (Days 1–3)

**Purpose:** Establish the product boundary before changing architecture.

Tasks:

1. Add a feature configuration with `response_controls_enabled=false` by default.
2. Hide or disable quarantine, restore, and server-link actions when the flag is off.
3. Mark simulation pages and exports as `Research / simulated environment`.
4. Create `SUPPORTED_CAPABILITIES.md` with four states: supported, pilot-only, research, and unavailable.
5. Define the pilot’s device count, Windows versions, collected fields, retention period, support hours, and uninstall process.
6. Define the first commercial success measures: enrollment reliability, evidence freshness, administrator time saved, actions verified, and renewal decision.

Acceptance criteria:

- A customer cannot trigger an endpoint response action in the default build.
- Every dashboard/export clearly identifies demo, simulated, estimated, and observed data.
- The pilot agreement does not promise antivirus, autonomous response, zero-day discovery, or real breach probability.

### Phase 1 — Repair correctness and truthfulness (Week 1)

**Purpose:** Stop generating technically incorrect recommendations before building more features.

#### 1.1 Fix patch intervention preservation

Implementation:

- Change evaluation to accept a fully prepared graph and do no unconditional re-tagging.
- Represent interventions explicitly, such as `{node_id, cve_id}` or `patched_cves`, and apply them after any required tagging.
- Generate a stable seed from SHA-256 or pass an explicit seed list. Do not use Python `hash()`.
- Use the same episode seeds for baseline and patched evaluations to reduce sampling noise.
- Include input snapshot, intervention, seed set, engine version, and model version in results.

Tests:

- A removed CVE remains absent in every evaluation episode.
- A hand-built graph with one decisive vulnerability shows the expected reduction.
- Repeated runs in separate processes produce identical results for the same inputs.

#### 1.2 Fix the defender action codec

Implementation:

- Define shared helpers: `encode_patch(i)`, `encode_isolate(i)`, and `decode_defender_action(action)`.
- Use `0..MAX_NODES-1` for patch and `MAX_NODES..2*MAX_NODES-1` for isolate everywhere.
- Replace custom decoding in `DefenderEnv`, MARL evaluation, and future response-policy code.

Tests:

- Every enabled action changes exactly the expected node.
- Padded actions remain disabled.
- Tests cover all three example topology sizes.

#### 1.3 Repair vulnerability data integrity

Implementation:

- Move invented records into `data/fixtures/synthetic_cves.json` with `SYNTH-ONYX-*` identifiers.
- Add `source_url`, `source_name`, `retrieved_at`, `affected_product`, and normalized version fields to production findings.
- Reject or quarantine imports whose real CVE/product mapping cannot be verified.

Tests:

- Synthetic fixtures can never appear with production provenance.
- Known CVE fixtures match their expected product and version.

#### 1.4 Correct metric semantics

Implementation:

- Add typed measurement classes: `observed`, `scanner_reported`, `estimated_score`, `simulated_counterfactual`, and `verified_outcome`.
- Replace `simulation_impact` in heuristic reality ranking with `priority_score`.
- Replace financial `ROI` wording with `priority_per_effort` unless money saved is actually measured.
- Remove sums of independent patch impacts.

Acceptance criteria:

- No UI or report can display a heuristic score as measured risk reduction.
- Percentages identify their denominator and measurement type.
- Combined reduction is shown only when a combined intervention was evaluated.

### Phase 2 — Establish identity and isolation (Weeks 2–3)

**Purpose:** Create a security boundary suitable for customer data.

#### 2.1 Administrator identity

Implementation:

- Choose a standards-based identity provider using OIDC/OAuth rather than building password storage.
- Validate signed tokens in FastAPI.
- Derive actor identity and organization from the validated token, never request bodies or query strings.
- Implement server-side roles such as `owner`, `administrator`, `analyst`, and `viewer`.
- Require authorization dependencies on every API route; explicitly mark truly public health endpoints.

#### 2.2 Organization isolation

Implementation:

- For the first pilot, deploy a separate database and service instance per customer.
- Design migrations adding `organization_id` to endpoints, telemetry, findings, incidents, commands, notifications, simulations, preferences, reports, jobs, scenarios, and audit events.
- Use organization-scoped composite uniqueness constraints.
- Scope filesystem artifacts and caches with organization and immutable run identifiers.
- Add an authorization matrix test that attempts cross-organization access for every resource.

#### 2.3 Device identity and enrollment

Implementation:

- Create one-time enrollment tokens with short expiry, organization, allowed platform, and maximum uses.
- Exchange the token for a randomly generated device credential; store only a strong hash server-side.
- Bind the credential to one `organization_id` and `endpoint_id`.
- Add rotation, revocation, last-used metadata, and offboarding.
- Reject endpoint ID changes made with an existing credential.

Acceptance criteria:

- Unauthenticated API access is denied by default.
- Users and devices cannot read or modify another organization’s data.
- Revoked devices cannot ingest data or poll commands.
- Audit actors are derived from trusted credentials.

### Phase 3 — Make installation trustworthy (Weeks 3–4)

**Purpose:** Protect employee devices and make deployment acceptable to IT.

Tasks:

1. Stop generating bundles with reusable API keys.
2. Remove secret-bearing state, logs, and installers from served directories.
3. Serve packages only over authenticated HTTPS.
4. Sign the Windows package/script or provide an enterprise-verifiable publisher signature.
5. Verify package signature and expected version before execution.
6. Store device credentials using Windows DPAPI/Credential Manager with restricted ACLs.
7. Document installation, upgrade, rotation, revocation, uninstall, and recovery.
8. Add offline buffering with a bounded encrypted queue if the pilot requires it.
9. Measure CPU, memory, disk, and network overhead on supported devices.

Acceptance criteria:

- No long-lived credential is present inside a downloadable bundle.
- Tampered installers fail before privileged execution.
- Enrollment tokens cannot be reused.
- Uninstall removes scheduled tasks, local secrets, rules, and application files.
- A clean reinstall and credential rotation both succeed.

### Phase 4 — Build the sellable remediation workflow (Weeks 4–6)

**Purpose:** Convert collected security evidence into accountable work.

Data model:

- `remediation_action`: organization, finding, device, title, recommendation, owner, due date, priority, state, created/updated actor and timestamps.
- States: `proposed`, `accepted`, `in_progress`, `contained`, `awaiting_verification`, `verified`, `exception`, `closed`, and `reopened`.
- `verification_evidence`: source, timestamp, observation, collector version, and reviewer.
- `exception`: reason, approver, expiry, and compensating control.

UI:

- Default landing page: devices needing attention, stale/unknown coverage, overdue actions, and newly verified work.
- Device detail: owner, status, evidence timeline, open findings, assigned actions, and freshness.
- Action queue: filters by owner, state, due date, severity, and source.
- Weekly report: coverage, new issues, completed/verified actions, overdue work, exceptions, and collector failures.
- CSV export first; add ticket-system integration only after a paying pilot requests a specific one.

Rules:

- An alert does not prove compromise.
- A containment acknowledgement changes state to `contained`, not `verified` or `closed`.
- A finding closes only after new evidence or authorized human verification.
- Missing/stale evidence produces `unknown`, not `healthy`.

Value test:

- Record how long the administrator’s current process takes.
- Measure time to triage, assign, and verify the same work in Onyx.
- Record accepted, rejected, incorrect, and unverifiable recommendations.

### Phase 5 — Make data and command behavior reliable (Weeks 6–8)

#### 5.1 Coverage and freshness

- Maintain an expected-device inventory and lifecycle state.
- Calculate active, stale, offline, unenrolled, unsupported, and unknown counts.
- Set freshness thresholds by evidence type.
- Gate analytics on defined coverage, not the mere existence of one record.
- Show collector errors and last successful collection.

#### 5.2 Cache and artifact isolation

- Use a composite identity: organization, topology/input snapshot hash, data mode, model/engine version, parameters, and run ID.
- Make reports immutable outputs of a recorded run.
- Store demo information in a separate database/schema and prevent demo-to-reality writes.
- Remove global “latest” state from customer-facing report generation.

#### 5.3 Reliable command protocol

Keep command execution disabled for the read-only pilot while implementing:

- States: `queued`, `leased`, `acknowledged`, `executing`, `succeeded`, `failed`, `expired`, and `cancelled`.
- Lease owner, lease expiry, attempt count, retry time, command expiry, and idempotency key.
- Redelivery after lease expiry.
- Agent-side idempotent execution and state verification.
- Capability enforcement before command creation.
- Cancellation and emergency recovery procedures.

Acceptance criteria:

- A dropped poll response does not lose a command.
- Duplicate delivery does not repeat a destructive action.
- Offline and restarted devices recover safely.
- Topology A cannot receive cached results from topology B.
- Demo data never appears in reality-mode results.

### Phase 6 — Create a release gate (Weeks 7–9)

**Purpose:** Make every build repeatable and supportable.

Tasks:

1. Declare `web/` the canonical application.
2. Move `web_backup/` and `Security Sentinel/` to an archive branch or documented archive directory after confirming no unique required code.
3. Fix all TypeScript diagnostics and frontend lint/build errors.
4. Repair Python environment creation; fail clearly when the interpreter is incompatible.
5. Add database migrations rather than running schema creation during ordinary requests.
6. Add configuration validation and fail closed on missing production secrets.
7. Add CI for type checking, lint, safe unit/integration tests, secret scanning, and dependency review.
8. Test database backup, restore, retention, and corrupted/interrupted recovery.
9. Replace development servers and reload mode with a documented production service configuration.
10. Add structured operational health: ingestion failures, stale devices, command backlog, database errors, and report failures.

Release gate:

- Clean checkout installs from documented commands.
- Type check, lint, build, and approved tests pass.
- No secrets or customer data appear in the Git tree or build artifacts.
- Migration up/down or forward-recovery procedure is tested.
- Backup restoration succeeds in an isolated environment.
- Pilot install, upgrade, reboot, offline/reconnect, and uninstall scenarios pass.

### Phase 7 — Validate and then improve the research engine (Weeks 9–12 and later)

**Purpose:** Determine whether Onyx’s ML produces better decisions than simpler methods.

#### 7.1 Establish baselines

Compare Onyx with:

- CVSS ordering
- Known exploitation status such as KEV
- EPSS used according to its defined meaning
- Asset criticality plus exposure
- A simple shortest-path/chokepoint graph heuristic
- A transparent priority-per-effort formula

Do not combine scores and call them calibrated probability without evidence.

#### 7.2 Improve evaluation design

- Split datasets by complete episode, topology, and time rather than random neighboring transitions.
- Hold out topology families from training.
- Measure ranking quality, calibration, false positives, stability across seeds, and intervention accuracy.
- Validate against authorized lab scenarios with known reachable and blocked paths.
- For customer data, measure whether recommendations are accepted and later verified—not whether the simulator produced an attractive percentage.

#### 7.3 Decide the world-model/MARL scope

Short-term option:

- Remove claims that the current attacker environment uses learned transitions or that training is full opponent-coupled self-play.
- Keep the rule-based simulator as a transparent research engine.

Research option after the product is stable:

- Add a transition-model interface that is actually called for every state change.
- Create opponent-aware environments that receive frozen policy snapshots.
- Alternate training against versioned opponent populations and evaluate against unseen opponents.
- Add exploitability constraints and uncertainty rather than treating CVSS as exploit probability.
- Replace fixed 50-node flat actions only if larger-network simulation has demonstrated customer value.

Promotion gate for customer-facing simulation claims:

- Correctness tests pass.
- Results beat a transparent baseline on held-out scenarios.
- Confidence intervals and failure cases are published internally.
- At least one authorized real/lab validation links recommendations to verified outcomes.
- Product language describes exactly what was measured.

## 4. Workstreams and dependencies

```text
Product boundary
├── Identity and tenant isolation
│   └── Secure device enrollment
│       └── Trusted installer
│           └── Read-only customer pilot
├── Metric semantics
│   └── Remediation workflow
│       └── Verified outcome reporting
└── Simulation correctness
    ├── Patch intervention fix
    ├── Defender action fix
    └── Scientific evaluation
        └── Customer-facing simulation claim
```

The read-only pilot depends on identity, isolation, safe enrollment, trustworthy installation, truthful metrics, and basic remediation tracking. It does **not** depend on MARL, autonomous containment, multi-tenant SaaS, or a large-network RL redesign.

## 5. Suggested issue backlog

Create one GitHub epic for each group and link the implementation issues beneath it.

| Epic | First issues | Completion signal |
|---|---|---|
| E1 Product boundary | Feature-disable response; capability matrix; research labels | Pilot scope is explicit in UI/docs |
| E2 Simulation correctness | Preserve patch; stable paired seeds; action codec; regression tests | Known-answer simulations pass |
| E3 Data integrity | Synthetic CVE split; validation schema; provenance | No false real CVE fixtures |
| E4 Authentication | OIDC validation; protected routes; server RBAC | Authorization matrix passes |
| E5 Organization isolation | Schema migration; query scoping; cache/artifact scoping | Cross-org tests all deny |
| E6 Device enrollment | One-time token; bound device credential; revoke/rotate | Device impersonation tests fail safely |
| E7 Trusted installer | Authenticated download; signature verification; uninstall | Lab lifecycle tests pass |
| E8 Remediation workflow | Owners; dates; states; verification; CSV/report | Admin completes end-to-end task |
| E9 Reliability | Coverage/freshness; cache isolation; command leases | Failure/reconnect scenarios pass |
| E10 Release engineering | Type fixes; runtime; CI; migrations; backup/restore | Release gate passes from clean checkout |
| E11 Research validation | Baselines; held-out splits; calibration; lab evidence | ML benefit is measured or rejected |

Every issue should contain:

- User or system risk being addressed
- Exact behavior before and after
- Data migration or compatibility impact
- Automated tests and manual verification
- Security/privacy considerations
- Rollback or recovery procedure where relevant
- Evidence required to close the issue

## 6. Pilot launch checklist

Do not install Onyx on employee devices until all items in this section pass.

- [ ] One customer/environment is isolated from all other data.
- [ ] Administrator login and server-side authorization are enabled.
- [ ] Each device has a unique, revocable identity.
- [ ] Installer authenticity and integrity are verified before privileged execution.
- [ ] No reusable credential exists in a downloadable bundle or Git repository.
- [ ] Collected fields and retention have customer approval.
- [ ] Read-only response mode is enforced by the backend, not only hidden in the UI.
- [ ] Unknown, stale, offline, and healthy states are distinct.
- [ ] Findings show source and freshness.
- [ ] Owners, due dates, exceptions, and verification states work end to end.
- [ ] Type check, build, focused API tests, and authorization tests pass.
- [ ] Reboot, offline/reconnect, upgrade, uninstall, and credential revocation pass in the lab.
- [ ] Backup and restore are tested.
- [ ] Support hours, escalation contacts, and rollback responsibilities are documented.
- [ ] The customer accepts written success measures and a paid scope.

## 7. What to defer

Defer these until the first pilot works and a customer asks for them with budget:

- Autonomous quarantine or patching
- Full MDM/EDR replacement
- Multi-tenant MSSP console
- Additional dashboard redesigns
- More model training without a defined evaluation question
- Large-network RL redesign
- Many integrations before one source works reliably
- Automated subscription billing
- 24/7 monitoring or incident-response promises
- Blockchain integration; it does not solve the current trust, identity, correctness, or workflow problems

## 8. Definition of project readiness

Onyx is ready for a supervised paid pilot when:

1. Customer and device identities are authenticated and isolated.
2. Installation, update, revocation, and uninstall are trustworthy and repeatable.
3. The default experience is read-only and cannot accidentally trigger experimental controls.
4. Every important result states whether it is observed, reported, estimated, simulated, or verified.
5. Administrators can assign, track, verify, reopen, and report remediation work.
6. Stale or missing evidence is visible and never silently treated as healthy.
7. A clean release passes the build, authorization, isolation, lifecycle, backup, and recovery gates.

Onyx is ready to market its simulation as a differentiator only after the separate research promotion gate in Phase 7 passes.
