# Telemetry Normalization Schema

This schema is used to map external findings/events to Onyx attack analysis and patch ranking.

## Normalized Event Fields
- event_id: string (required after normalization)
- timestamp: ISO-8601 string
- topology: string
- source_node: string
- target_node: string
- event_type: string
- cve_id: string (uppercased)
- cvss_score: float [0..10]
- confidence: float [0..1]
- blocked: boolean
- reached_critical: boolean
- raw: object (original payload)

## Accepted Input Aliases
- source_node: source_node | src | host | source
- target_node: target_node | dst | destination | target
- cve_id: cve_id | vulnerability | cve
- event_type: event_type | type
- cvss_score: cvss_score | severity_score | cvss
- confidence: confidence | signal_confidence
- blocked: blocked | was_blocked
- reached_critical: reached_critical | critical_asset_hit

## Mapping Outputs

### Attack analysis shape
- edge_frequency: {"source||target": float}
- node_frequency: {"node_id": float}
- top_paths: [{path, count, frequency}]
- success_rate: float
- n_episodes: int
- data_source: telemetry
- confidence: measured

### Patch results shape
- results: [{node_id, cve_id, cvss_score, baseline_success_rate, patched_success_rate, simulation_impact, simulation_rank, cvss_rank, ...}]
- data_source: telemetry
- telemetry_mode: local_ingest | remote_endpoint
