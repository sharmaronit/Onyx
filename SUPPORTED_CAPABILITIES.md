# Onyx supported capabilities

This matrix defines what Onyx may be presented as doing. Product copy, demonstrations, reports, and pilot agreements must follow it.

| Capability | State | What the state means |
|---|---|---|
| Windows endpoint heartbeat and inventory | Pilot-only | Suitable for an authorized, supervised 10–25 device evaluation after identity and installer checks pass. |
| Microsoft Defender event collection | Pilot-only | Onyx reports source-attributed Windows Defender evidence; it does not replace Defender. |
| Vulnerability finding import | Pilot-only | Findings must retain their scanner source and observation time. |
| Device attention queue and evidence freshness | Pilot-only | Operational visibility for one organization in an isolated deployment. |
| Patch priority per effort | Pilot-only | A transparent estimate for ordering work; it is not financial ROI or measured risk reduction. |
| CSV/report export | Pilot-only | Exports must preserve measurement type and provenance. |
| Attack-path simulation | Research | Offline synthetic world-model output. It is not a live breach observation or calibrated breach probability. |
| Patch counterfactual simulation | Research | A paired simulated comparison for model evaluation; it is not a promised customer outcome. |
| MARL/self-play | Research | Experimental and excluded from pilot success claims. |
| Endpoint quarantine/restore | Unavailable by default | Backend-enforced off unless `ONYX_RESPONSE_CONTROLS_ENABLED=true` is deliberately configured for a controlled lab. |
| Server-link control | Unavailable by default | The current state flag is not a network enforcement mechanism and must not be sold as one. |
| Autonomous patching or containment | Unavailable | No customer-facing support. |
| Antivirus, EDR, MDM, or zero-day replacement | Unavailable | Onyx complements existing security and device-management products. |
| Multi-tenant SaaS | Unavailable | Early customers require isolated service and database deployments. |
| Blockchain | Unavailable | It does not address the present identity, evidence, workflow, or validation needs. |

## Evidence language

Use one of these measurement types on important output:

- `observed`: directly collected behavior or relationship.
- `scanner_reported`: a finding asserted by an identified scanner.
- `estimated_priority`: a transparent heuristic used to order work.
- `simulated_counterfactual`: output from an offline model comparison.
- `verified_outcome`: new evidence or an authorized reviewer confirms completion.

Never sum independent patch effects, call a priority score ROI, or describe an alert as proof of compromise.
