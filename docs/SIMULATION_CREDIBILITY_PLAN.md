# Simulation Credibility Plan

## Goal
Make Onyx simulation outputs look realistic and judge-safe by avoiding flat 100% success rates, exposing uncertainty, and separating presentation fixes from core simulation fixes.

## Problem Summary
The current simulation view can appear fake because:
- Success is shown as a single percentage with limited context.
- The simulation can naturally trend toward 100% when many retries and high-severity CVEs are combined.
- The UI rounds values to one decimal place, which can hide near-100% results.
- Judges do not see enough evidence that the result varies across seeds, topologies, or data sources.

## Recommended Approach
Use a two-step fix:
1. Improve the presentation first so the current system looks more credible immediately.
2. Calibrate the simulation logic so the underlying output is less extreme and more defensible.

## Plan
### Phase 1: Presentation credibility
- Show success rate with more precision.
- Add raw counts next to percentages, for example `487 / 700` instead of only `69.6%`.
- Show mean, min, max, and variation across multiple seeds.
- Display a small comparison view for simulation vs hybrid vs telemetry when available.
- Make the confidence/provenance label more visible in the UI.

### Phase 2: Simulation calibration
- Limit repeated attack attempts on the same target within one episode.
- Make attack success depend on more than CVSS alone.
- Add penalties or friction for firewalls, permission level, and connection type.
- Reduce or vary episode length based on topology size or path depth.
- Make local vulnerabilities behave differently from remote network exploits.

### Phase 3: Validation and judge-readiness
- Run the same scenario across several random seeds and compare results.
- Add a small variance summary to the dashboard and report.
- Verify that small office, enterprise, and cloud hybrid topologies produce different outcomes.
- Capture an evidence bundle showing baseline, comparison, and patch impact.

## Todo Tasks
- [x] Update the UI so success rate is shown with 2 decimals and raw counts.
- [x] Add a seed sweep for simulation runs and compute summary statistics.
- [x] Add a confidence/variance card to the Analysis page.
- [x] Review simulation win conditions so success is not guaranteed by repeated retries.
- [x] Add topology-aware episode limits.
- [x] Add edge-aware penalties for firewall and permission strength.
- [x] Separate network-exploitable CVEs from local-only CVEs in the attack flow.
- [x] Compare outputs across `enterprise_20n`, `small_office_10n`, and `cloud_hybrid_30n`.
- [ ] Generate an updated report/evidence bundle for judges.
- [ ] Rehearse the demo with a less extreme result set and a fallback explanation.

## Success Criteria
- The dashboard no longer shows a flat 100% for every run.
- Different topologies produce different success-rate distributions.
- The result can be explained as a measured simulation output, not a hard-coded demo value.
- Judges can see why the result is credible through variance and provenance.

## Notes
This plan is intentionally narrow. It does not redesign the whole product; it only addresses simulation credibility and judge trust.
