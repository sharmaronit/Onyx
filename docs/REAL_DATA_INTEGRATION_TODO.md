# Real Data Integration TODO

Status: In progress
Owner: Onyx team
Last updated: 2026-04-05

## Phase 0 - Planning and alignment
- [x] Confirm credibility issue and root causes from current outputs.
- [x] Define phased strategy: simulation -> hybrid -> telemetry-backed.
- [x] Confirm first external data source for pilot (scanner export, SIEM logs, or lab feed).
- [x] Define legal boundary: only owned/authorized infrastructure.

## Phase 1 - Data source abstraction (start now)
- [x] Add shared TODO file for implementation tracking.
- [x] Create data provider abstraction with Simulation, TelemetryStub, and Hybrid providers.
- [x] Wire provider selection into backend `/api/simulate` and scenario execution.
- [x] Add request fields for `data_source` and `telemetry_weight` with backward-compatible defaults.
- [x] Expose data source metadata in API responses for UI labeling.
- [x] Keep simulation mode fully functional as fallback.

## Phase 2 - Configuration and connector shell
- [x] Extend config with telemetry section (enabled, endpoint, timeout, cache, fallback).
- [x] Add telemetry connector module (read-only client, timeout, retry, validation).
- [x] Add safe fallback path from telemetry/hybrid to simulation when source unavailable.
- [x] Add structured logs for source chosen and fallback reason.

## Phase 3 - Real input mapping
- [x] Define normalized schema for external findings/events to Onyx graph nodes and CVEs.
- [x] Map external attack events to attack-path format consumed by UI.
- [x] Implement confidence metadata (`measured`, `estimated`, `hybrid`).
- [x] Replace static report assumptions with generated output where possible.

## Phase 4 - Judge-facing transparency
- [x] Add source badge in UI (`Simulation`, `Hybrid`, `Telemetry`).
- [x] Add freshness timestamp for telemetry-backed outputs.
- [x] Mark estimated metrics explicitly in scorecard/report.
- [x] Add one-click demo mode that uses stable hybrid defaults.

## Phase 5 - Validation and evidence
- [ ] Validate against at least one authorized real/lab source.
- [ ] Run before/after comparison and record variance.
- [ ] Capture reproducible demo script and evidence bundle for judges.
- [ ] Document known limitations and risk assumptions.

## Definition of done (MVP)
- [x] Backend accepts and applies data source selection.
- [x] Hybrid mode works even when telemetry is unavailable.
- [x] API returns source metadata for each result set.
- [x] Demo can show at least one result with non-simulated provenance.
