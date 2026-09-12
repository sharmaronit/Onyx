"""SQLite persistence layer for Onyx Web API."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).parent / "onyx.db"


def init_db() -> None:
    """Initialize database schema."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # User preferences
    c.execute(
        """CREATE TABLE IF NOT EXISTS user_preferences (
        id INTEGER PRIMARY KEY,
        user_id TEXT UNIQUE NOT NULL,
        default_topology TEXT DEFAULT 'enterprise_20n',
        default_episodes INTEGER DEFAULT 1000,
        cost_model_customization TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )"""
    )

    # Scenario history
    c.execute(
        """CREATE TABLE IF NOT EXISTS scenario_history (
        id INTEGER PRIMARY KEY,
        user_id TEXT NOT NULL,
        scenario_id TEXT NOT NULL,
        topology TEXT NOT NULL,
        n_episodes INTEGER,
        success_rate REAL,
        risk_reduction_pp REAL,
        top_patch_node TEXT,
        top_patch_cve TEXT,
        execution_time_seconds REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )"""
    )

    # Analysis results cache
    c.execute(
        """CREATE TABLE IF NOT EXISTS analysis_results (
        id INTEGER PRIMARY KEY,
        analysis_id TEXT UNIQUE NOT NULL,
        topology TEXT NOT NULL,
        analysis_type TEXT NOT NULL,
        result TEXT NOT NULL,
        execution_time_seconds REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )"""
    )

    # Cost model versions
    c.execute(
        """CREATE TABLE IF NOT EXISTS cost_models (
        id INTEGER PRIMARY KEY,
        user_id TEXT NOT NULL,
        model_name TEXT NOT NULL,
        model_config TEXT NOT NULL,
        is_active INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, model_name)
    )"""
    )

    # API request logs
    c.execute(
        """CREATE TABLE IF NOT EXISTS request_logs (
        id INTEGER PRIMARY KEY,
        endpoint TEXT NOT NULL,
        method TEXT NOT NULL,
        status_code INTEGER,
        response_time_ms REAL,
        user_id TEXT,
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )"""
    )

    # Model training jobs
    c.execute(
        """CREATE TABLE IF NOT EXISTS training_jobs (
        id INTEGER PRIMARY KEY,
        job_id TEXT UNIQUE NOT NULL,
        model_type TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        progress_percent INTEGER DEFAULT 0,
        config TEXT,
        result TEXT,
        error_message TEXT,
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )"""
    )

    c.execute(
        """CREATE TABLE IF NOT EXISTS telemetry_events (
        id INTEGER PRIMARY KEY,
        topology TEXT NOT NULL,
        source_node TEXT NOT NULL,
        event_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        event_timestamp TEXT NOT NULL,
        event_json TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(topology, source_node, event_id)
    )"""
    )
    c.execute(
        """CREATE INDEX IF NOT EXISTS telemetry_events_topology_time
        ON telemetry_events(topology, event_timestamp DESC)"""
    )

    c.execute(
        """CREATE TABLE IF NOT EXISTS endpoint_agents (
        endpoint_id TEXT PRIMARY KEY,
        hostname TEXT NOT NULL,
        ip_address TEXT,
        topology TEXT NOT NULL,
        agent_version TEXT NOT NULL,
        platform TEXT,
        quarantined INTEGER NOT NULL DEFAULT 0,
        last_error TEXT,
        metadata_json TEXT,
        first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )"""
    )

    c.execute(
        """CREATE TABLE IF NOT EXISTS response_commands (
        id INTEGER PRIMARY KEY,
        command_id TEXT UNIQUE NOT NULL,
        endpoint_id TEXT NOT NULL,
        action TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        reason TEXT NOT NULL,
        requested_by TEXT NOT NULL,
        parameters_json TEXT,
        result_json TEXT,
        error_message TEXT,
        requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        delivered_at TIMESTAMP,
        completed_at TIMESTAMP,
        FOREIGN KEY(endpoint_id) REFERENCES endpoint_agents(endpoint_id)
    )"""
    )
    c.execute(
        """CREATE INDEX IF NOT EXISTS response_commands_endpoint_time
        ON response_commands(endpoint_id, requested_at DESC)"""
    )
    c.execute(
        """CREATE UNIQUE INDEX IF NOT EXISTS response_commands_one_active
        ON response_commands(endpoint_id)
        WHERE status IN ('pending', 'delivered')"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS endpoint_incidents (
        id INTEGER PRIMARY KEY,
        incident_id TEXT UNIQUE NOT NULL,
        endpoint_id TEXT NOT NULL,
        topology TEXT NOT NULL,
        event_id TEXT NOT NULL,
        source TEXT NOT NULL,
        severity TEXT NOT NULL DEFAULT 'critical',
        summary TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_at TIMESTAMP,
        resolved_by TEXT,
        resolution_reason TEXT,
        UNIQUE(endpoint_id, event_id)
    )"""
    )
    c.execute("CREATE INDEX IF NOT EXISTS endpoint_incidents_open ON endpoint_incidents(endpoint_id, status, created_at DESC)")
    c.execute(
        """CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY,
        notification_id TEXT UNIQUE NOT NULL,
        endpoint_id TEXT,
        incident_id TEXT,
        kind TEXT NOT NULL,
        severity TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        read_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )"""
    )
    c.execute("CREATE INDEX IF NOT EXISTS notifications_time ON notifications(created_at DESC)")
    c.execute(
        """CREATE TABLE IF NOT EXISTS simulation_runs (
        simulation_id TEXT PRIMARY KEY,
        mode TEXT NOT NULL,
        topology TEXT NOT NULL,
        seed INTEGER NOT NULL,
        requested_episodes INTEGER NOT NULL,
        completed_episodes INTEGER NOT NULL,
        success_rate REAL NOT NULL,
        successful_runs INTEGER NOT NULL,
        failed_runs INTEGER NOT NULL,
        unique_paths INTEGER NOT NULL,
        result_json TEXT NOT NULL,
        replay_json TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )"""
    )
    c.execute("CREATE INDEX IF NOT EXISTS simulation_runs_time ON simulation_runs(created_at DESC)")
    c.execute(
        """CREATE TABLE IF NOT EXISTS simulation_paths (
        id INTEGER PRIMARY KEY,
        simulation_id TEXT NOT NULL,
        path_rank INTEGER NOT NULL,
        path_json TEXT NOT NULL,
        path_count INTEGER NOT NULL,
        frequency REAL NOT NULL,
        FOREIGN KEY(simulation_id) REFERENCES simulation_runs(simulation_id) ON DELETE CASCADE,
        UNIQUE(simulation_id, path_rank)
    )"""
    )
    c.execute("CREATE INDEX IF NOT EXISTS simulation_paths_run ON simulation_paths(simulation_id, path_rank)")
    c.execute(
        """CREATE TABLE IF NOT EXISTS vulnerability_findings (
        id INTEGER PRIMARY KEY,
        endpoint_id TEXT NOT NULL,
        topology TEXT NOT NULL,
        finding_id TEXT NOT NULL,
        cve_id TEXT,
        title TEXT NOT NULL,
        cvss_score REAL NOT NULL,
        software TEXT,
        software_version TEXT,
        fix_available INTEGER NOT NULL DEFAULT 0,
        effort_hours REAL,
        source TEXT NOT NULL,
        evidence_json TEXT NOT NULL,
        observed_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open',
        UNIQUE(endpoint_id, finding_id, source)
    )"""
    )
    c.execute("CREATE INDEX IF NOT EXISTS vulnerability_findings_live ON vulnerability_findings(topology, status, observed_at DESC)")
    c.execute("""CREATE TABLE IF NOT EXISTS endpoint_server_links (
        endpoint_id TEXT PRIMARY KEY, disconnected INTEGER NOT NULL DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS observed_relationships (
        source_asset TEXT NOT NULL, target_asset TEXT NOT NULL, topology TEXT NOT NULL,
        relation_type TEXT NOT NULL, confidence REAL NOT NULL DEFAULT 0.6,
        last_observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(source_asset, target_asset, topology, relation_type)
    )""")

    conn.commit()
    conn.close()


def save_simulation_run(simulation_id: str, mode: str, result: Dict[str, Any], replay: Dict[str, Any]) -> None:
    """Persist a complete reproducible world-model run and its ranked paths."""
    init_db()
    evidence = replay.get("evidence") or {}
    execution = evidence.get("execution") or {}
    model = evidence.get("model") or {}
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.execute("PRAGMA busy_timeout = 10000")
        conn.execute(
            """INSERT INTO simulation_runs
            (simulation_id, mode, topology, seed, requested_episodes, completed_episodes,
             success_rate, successful_runs, failed_runs, unique_paths, result_json, replay_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                simulation_id, mode, replay.get("topology", "enterprise_20n"), int(model.get("seed") or 42),
                int(execution.get("requested_episodes") or replay.get("n_episodes") or 0),
                int(execution.get("completed_episodes") or replay.get("n_episodes") or 0),
                float(replay.get("success_rate") or 0.0), int(replay.get("successful_runs") or 0),
                int(replay.get("failed_runs") or 0), int(replay.get("total_unique_paths") or 0),
                json.dumps(result, allow_nan=False), json.dumps(replay, allow_nan=False),
            ),
        )
        for rank, path in enumerate(result.get("top_paths") or [], start=1):
            conn.execute(
                """INSERT INTO simulation_paths (simulation_id, path_rank, path_json, path_count, frequency)
                VALUES (?, ?, ?, ?, ?)""",
                (simulation_id, rank, json.dumps(path.get("path")), int(path.get("count") or 0), float(path.get("frequency") or 0.0)),
            )


def list_simulation_runs(limit: int = 30) -> List[Dict[str, Any]]:
    init_db()
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT simulation_id, mode, topology, seed, requested_episodes, completed_episodes,
            success_rate, successful_runs, failed_runs, unique_paths, created_at
            FROM simulation_runs ORDER BY created_at DESC, rowid DESC LIMIT ?""",
            (max(1, min(int(limit), 100)),),
        ).fetchall()
    return [dict(row) for row in rows]


def get_simulation_run(simulation_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        run = conn.execute("SELECT * FROM simulation_runs WHERE simulation_id = ?", (simulation_id,)).fetchone()
        if not run:
            return None
        paths = conn.execute(
            "SELECT path_rank, path_json, path_count, frequency FROM simulation_paths WHERE simulation_id = ? ORDER BY path_rank",
            (simulation_id,),
        ).fetchall()
    payload = dict(run)
    payload["result"] = json.loads(payload.pop("result_json"))
    payload["replay"] = json.loads(payload.pop("replay_json"))
    payload["paths"] = [
        {"rank": row["path_rank"], "path": json.loads(row["path_json"]), "count": row["path_count"], "frequency": row["frequency"]}
        for row in paths
    ]
    return payload


def upsert_vulnerability_findings(topology: str, findings: List[Dict[str, Any]]) -> int:
    init_db()
    changed = 0
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.execute("PRAGMA busy_timeout = 10000")
        for finding in findings:
            cursor = conn.execute(
                """INSERT INTO vulnerability_findings
                (endpoint_id, topology, finding_id, cve_id, title, cvss_score, software, software_version,
                 fix_available, effort_hours, source, evidence_json, observed_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(endpoint_id, finding_id, source) DO UPDATE SET
                cve_id=excluded.cve_id, title=excluded.title, cvss_score=excluded.cvss_score,
                software=excluded.software, software_version=excluded.software_version,
                fix_available=excluded.fix_available, effort_hours=excluded.effort_hours,
                evidence_json=excluded.evidence_json, observed_at=excluded.observed_at, status=excluded.status""",
                (
                    str(finding["endpoint_id"]), topology, str(finding["finding_id"]), finding.get("cve_id"),
                    str(finding.get("title") or finding.get("cve_id") or "Vulnerability finding"),
                    float(finding.get("cvss_score") or 0), finding.get("software"), finding.get("software_version"),
                    int(bool(finding.get("fix_available"))), finding.get("effort_hours"), str(finding.get("source") or "scanner"),
                    json.dumps(finding.get("evidence") or {}, allow_nan=False),
                    str(finding.get("observed_at") or datetime.utcnow().isoformat()), str(finding.get("status") or "open"),
                ),
            )
            changed += cursor.rowcount
    return changed


def list_vulnerability_findings(topology: str, limit: int = 1000) -> List[Dict[str, Any]]:
    init_db()
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM vulnerability_findings WHERE topology = ? AND status = 'open' ORDER BY cvss_score DESC, observed_at DESC LIMIT ?",
            (topology, max(1, min(int(limit), 5000))),
        ).fetchall()
    findings = []
    for row in rows:
        item = dict(row)
        item["fix_available"] = bool(item["fix_available"])
        item["evidence"] = json.loads(item.pop("evidence_json") or "{}")
        findings.append(item)
    return findings


def store_telemetry_events(topology: str, events: List[Dict[str, Any]]) -> int:
    """Persist normalized telemetry idempotently and return the insert count."""
    init_db()
    inserted = 0
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.execute("PRAGMA busy_timeout = 10000")
        for event in events:
            cursor = conn.execute(
                """INSERT OR IGNORE INTO telemetry_events
                (topology, source_node, event_id, event_type, event_timestamp, event_json)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    topology,
                    str(event.get("source_node") or "unknown_source"),
                    str(event.get("event_id") or ""),
                    str(event.get("event_type") or "unknown_event"),
                    str(event.get("timestamp") or datetime.utcnow().isoformat()),
                    json.dumps(event, allow_nan=False),
                ),
            )
            inserted += cursor.rowcount
    return inserted


def get_telemetry_events(topology: str, limit: int = 500) -> List[Dict[str, Any]]:
    init_db()
    safe_limit = max(1, min(int(limit), 5000))
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        rows = conn.execute(
            """SELECT event_json FROM telemetry_events
            WHERE topology = ? ORDER BY event_timestamp DESC LIMIT ?""",
            (topology, safe_limit),
        ).fetchall()
    return [json.loads(row[0]) for row in rows]


def upsert_endpoint_heartbeat(endpoint: Dict[str, Any]) -> Dict[str, Any]:
    init_db()
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.execute(
            """INSERT INTO endpoint_agents
            (endpoint_id, hostname, ip_address, topology, agent_version, platform,
             quarantined, last_error, metadata_json, last_seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(endpoint_id) DO UPDATE SET
                hostname=excluded.hostname,
                ip_address=excluded.ip_address,
                topology=excluded.topology,
                agent_version=excluded.agent_version,
                platform=excluded.platform,
                quarantined=excluded.quarantined,
                last_error=excluded.last_error,
                metadata_json=excluded.metadata_json,
                last_seen_at=CURRENT_TIMESTAMP""",
            (
                endpoint["endpoint_id"],
                endpoint["hostname"],
                endpoint.get("ip_address"),
                endpoint["topology"],
                endpoint["agent_version"],
                endpoint.get("platform"),
                1 if endpoint.get("quarantined") else 0,
                endpoint.get("last_error"),
                json.dumps(endpoint.get("metadata") or {}, allow_nan=False),
            ),
        )
    return get_endpoint(endpoint["endpoint_id"]) or {}


def get_endpoint(endpoint_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM endpoint_agents WHERE endpoint_id = ?", (endpoint_id,)
        ).fetchone()
    return _endpoint_row(row) if row else None


def list_endpoints(topology: Optional[str] = None) -> List[Dict[str, Any]]:
    init_db()
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        if topology:
            rows = conn.execute(
                "SELECT * FROM endpoint_agents WHERE topology = ? ORDER BY last_seen_at DESC",
                (topology,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM endpoint_agents ORDER BY last_seen_at DESC"
            ).fetchall()
    return [_endpoint_row(row) for row in rows]


def _endpoint_row(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "endpoint_id": row["endpoint_id"],
        "hostname": row["hostname"],
        "ip_address": row["ip_address"],
        "topology": row["topology"],
        "agent_version": row["agent_version"],
        "platform": row["platform"],
        "quarantined": bool(row["quarantined"]),
        "last_error": row["last_error"],
        "metadata": json.loads(row["metadata_json"] or "{}"),
        "first_seen_at": row["first_seen_at"],
        "last_seen_at": row["last_seen_at"],
    }


def create_incident(endpoint_id: str, topology: str, event_id: str, source: str, summary: str, severity: str = "critical") -> Optional[Dict[str, Any]]:
    """Open one idempotent incident per telemetry event."""
    import uuid
    init_db()
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            """INSERT OR IGNORE INTO endpoint_incidents
            (incident_id, endpoint_id, topology, event_id, source, severity, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (f"inc_{uuid.uuid4().hex}", endpoint_id, topology, event_id, source, severity, summary),
        )
        if cursor.rowcount != 1:
            return None
        row = conn.execute("SELECT * FROM endpoint_incidents WHERE endpoint_id=? AND event_id=?", (endpoint_id, event_id)).fetchone()
    return _incident_row(row) if row else None


def list_open_incidents(endpoint_id: str) -> List[Dict[str, Any]]:
    init_db()
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM endpoint_incidents WHERE endpoint_id=? AND status='open' ORDER BY created_at DESC", (endpoint_id,)).fetchall()
    return [_incident_row(row) for row in rows]


def resolve_incident(incident_id: str, resolved_by: str, reason: str) -> Optional[Dict[str, Any]]:
    init_db()
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("""UPDATE endpoint_incidents SET status='resolved', resolved_at=CURRENT_TIMESTAMP,
                     resolved_by=?, resolution_reason=? WHERE incident_id=? AND status='open'""", (resolved_by, reason, incident_id))
        row = conn.execute("SELECT * FROM endpoint_incidents WHERE incident_id=?", (incident_id,)).fetchone()
    return _incident_row(row) if row else None


def _incident_row(row: sqlite3.Row) -> Dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def create_notification(kind: str, severity: str, title: str, message: str, endpoint_id: Optional[str] = None, incident_id: Optional[str] = None) -> Dict[str, Any]:
    import uuid
    init_db()
    notification_id = f"ntf_{uuid.uuid4().hex}"
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.execute("""INSERT INTO notifications(notification_id, endpoint_id, incident_id, kind, severity, title, message)
                     VALUES (?, ?, ?, ?, ?, ?, ?)""", (notification_id, endpoint_id, incident_id, kind, severity, title, message))
    return get_notification(notification_id) or {}


def get_notification(notification_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM notifications WHERE notification_id=?", (notification_id,)).fetchone()
    return dict(row) if row else None


def list_notifications(limit: int = 100) -> List[Dict[str, Any]]:
    init_db()
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM notifications ORDER BY created_at DESC LIMIT ?", (max(1, min(limit, 500)),)).fetchall()
    return [dict(row) for row in rows]


def mark_notifications_read(notification_id: Optional[str] = None) -> None:
    init_db()
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        if notification_id:
            conn.execute("UPDATE notifications SET read_at=CURRENT_TIMESTAMP WHERE notification_id=?", (notification_id,))
        else:
            conn.execute("UPDATE notifications SET read_at=CURRENT_TIMESTAMP WHERE read_at IS NULL")


def clear_notifications() -> int:
    init_db()
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        return conn.execute("DELETE FROM notifications").rowcount


def set_server_link(endpoint_id: str, disconnected: bool) -> None:
    init_db()
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.execute("""INSERT INTO endpoint_server_links(endpoint_id, disconnected, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
                     ON CONFLICT(endpoint_id) DO UPDATE SET disconnected=excluded.disconnected, updated_at=CURRENT_TIMESTAMP""", (endpoint_id, 1 if disconnected else 0))


def server_link_disconnected(endpoint_id: str) -> bool:
    init_db()
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        row = conn.execute("SELECT disconnected FROM endpoint_server_links WHERE endpoint_id=?", (endpoint_id,)).fetchone()
    return bool(row and row[0])


def upsert_relationship(source_asset: str, target_asset: str, topology: str, relation_type: str = "observed_connection", confidence: float = 0.6) -> None:
    init_db()
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.execute("""INSERT INTO observed_relationships(source_asset, target_asset, topology, relation_type, confidence, last_observed_at)
                     VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                     ON CONFLICT(source_asset, target_asset, topology, relation_type)
                     DO UPDATE SET confidence=excluded.confidence, last_observed_at=CURRENT_TIMESTAMP""", (source_asset, target_asset, topology, relation_type, confidence))


def list_relationships(topology: str) -> List[Dict[str, Any]]:
    init_db()
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM observed_relationships WHERE topology=? ORDER BY last_observed_at DESC", (topology,)).fetchall()
    return [dict(row) for row in rows]


def create_response_command(
    command_id: str,
    endpoint_id: str,
    action: str,
    reason: str,
    requested_by: str,
    parameters: Dict[str, Any],
) -> Dict[str, Any]:
    init_db()
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute(
                """INSERT INTO response_commands
                (command_id, endpoint_id, action, reason, requested_by, parameters_json)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (command_id, endpoint_id, action, reason, requested_by, json.dumps(parameters)),
            )
    except sqlite3.IntegrityError:
        return {}
    return get_response_command(command_id) or {}


def claim_pending_commands(endpoint_id: str) -> List[Dict[str, Any]]:
    init_db()
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        rows = conn.execute(
            """SELECT * FROM response_commands
            WHERE endpoint_id = ? AND status = 'pending'
            ORDER BY requested_at LIMIT 10""",
            (endpoint_id,),
        ).fetchall()
        command_ids = [row["command_id"] for row in rows]
        if command_ids:
            conn.executemany(
                """UPDATE response_commands SET status='delivered',
                delivered_at=CURRENT_TIMESTAMP WHERE command_id=? AND status='pending'""",
                [(command_id,) for command_id in command_ids],
            )
    return [_command_row(row, status_override="delivered") for row in rows]


def complete_response_command(
    command_id: str,
    endpoint_id: str,
    status: str,
    result: Dict[str, Any],
    error_message: Optional[str],
    quarantined: bool,
) -> Optional[Dict[str, Any]]:
    init_db()
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        cursor = conn.execute(
            """UPDATE response_commands SET status=?, result_json=?, error_message=?,
            completed_at=CURRENT_TIMESTAMP
            WHERE command_id=? AND endpoint_id=? AND status='delivered'""",
            (status, json.dumps(result), error_message, command_id, endpoint_id),
        )
        if cursor.rowcount != 1:
            return None
        conn.execute(
            """UPDATE endpoint_agents SET quarantined=?, last_error=?,
            last_seen_at=CURRENT_TIMESTAMP WHERE endpoint_id=?""",
            (1 if quarantined else 0, error_message, endpoint_id),
        )
    return get_response_command(command_id)


def get_response_command(command_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM response_commands WHERE command_id=?", (command_id,)
        ).fetchone()
    return _command_row(row) if row else None


def list_response_commands(endpoint_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    init_db()
    safe_limit = max(1, min(int(limit), 500))
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        if endpoint_id:
            rows = conn.execute(
                """SELECT * FROM response_commands WHERE endpoint_id=?
                ORDER BY requested_at DESC LIMIT ?""",
                (endpoint_id, safe_limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM response_commands ORDER BY requested_at DESC LIMIT ?",
                (safe_limit,),
            ).fetchall()
    return [_command_row(row) for row in rows]


def _command_row(row: sqlite3.Row, status_override: Optional[str] = None) -> Dict[str, Any]:
    return {
        "command_id": row["command_id"],
        "endpoint_id": row["endpoint_id"],
        "action": row["action"],
        "status": status_override or row["status"],
        "reason": row["reason"],
        "requested_by": row["requested_by"],
        "parameters": json.loads(row["parameters_json"] or "{}"),
        "result": json.loads(row["result_json"] or "{}"),
        "error_message": row["error_message"],
        "requested_at": row["requested_at"],
        "delivered_at": row["delivered_at"],
        "completed_at": row["completed_at"],
    }


# ============ User Preferences ============


def set_user_preference(
    user_id: str,
    default_topology: Optional[str] = None,
    default_episodes: Optional[int] = None,
    cost_model: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Set user preferences."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Check if user exists
    c.execute("SELECT id FROM user_preferences WHERE user_id = ?", (user_id,))
    exists = c.fetchone()

    cost_model_json = json.dumps(cost_model) if cost_model else None

    if exists:
        c.execute(
            """UPDATE user_preferences 
            SET default_topology = COALESCE(?, default_topology),
                default_episodes = COALESCE(?, default_episodes),
                cost_model_customization = COALESCE(?, cost_model_customization),
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?""",
            (default_topology, default_episodes, cost_model_json, user_id),
        )
    else:
        c.execute(
            """INSERT INTO user_preferences 
            (user_id, default_topology, default_episodes, cost_model_customization)
            VALUES (?, ?, ?, ?)""",
            (user_id, default_topology or "enterprise_20n", default_episodes or 1000, cost_model_json),
        )

    conn.commit()
    conn.close()
    return get_user_preference(user_id)


def get_user_preference(user_id: str) -> Dict[str, Any]:
    """Get user preferences."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT * FROM user_preferences WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return {
            "user_id": user_id,
            "default_topology": "enterprise_20n",
            "default_episodes": 1000,
            "cost_model_customization": None,
        }

    return {
        "user_id": row[1],
        "default_topology": row[2],
        "default_episodes": row[3],
        "cost_model_customization": json.loads(row[4]) if row[4] else None,
        "created_at": row[5],
        "updated_at": row[6],
    }


# ============ Scenario History ============


def log_scenario_execution(
    user_id: str,
    scenario_id: str,
    topology: str,
    n_episodes: int,
    success_rate: float,
    risk_reduction_pp: float,
    top_patch: Optional[Dict[str, str]] = None,
    execution_time_seconds: float = 0.0,
) -> int:
    """Log a scenario execution."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    top_patch_node = top_patch.get("node_id") if top_patch else None
    top_patch_cve = top_patch.get("cve_id") if top_patch else None

    c.execute(
        """INSERT INTO scenario_history 
        (user_id, scenario_id, topology, n_episodes, success_rate, risk_reduction_pp, 
         top_patch_node, top_patch_cve, execution_time_seconds)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            scenario_id,
            topology,
            n_episodes,
            success_rate,
            risk_reduction_pp,
            top_patch_node,
            top_patch_cve,
            execution_time_seconds,
        ),
    )

    conn.commit()
    record_id = c.lastrowid
    conn.close()
    return record_id


def get_scenario_history(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Get scenario execution history for user."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        """SELECT * FROM scenario_history 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?""",
        (user_id, limit),
    )
    rows = c.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "scenario_id": row[2],
            "topology": row[3],
            "n_episodes": row[4],
            "success_rate": row[5],
            "risk_reduction_pp": row[6],
            "top_patch_node": row[7],
            "top_patch_cve": row[8],
            "execution_time_seconds": row[9],
            "created_at": row[10],
        }
        for row in rows
    ]


# ============ Cost Models ============


def save_cost_model(
    user_id: str, model_name: str, model_config: Dict[str, Any], is_active: bool = False
) -> int:
    """Save a cost model configuration."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    model_json = json.dumps(model_config)

    try:
        c.execute(
            """INSERT INTO cost_models (user_id, model_name, model_config, is_active)
            VALUES (?, ?, ?, ?)""",
            (user_id, model_name, model_json, 1 if is_active else 0),
        )
    except sqlite3.IntegrityError:
        # Update existing
        c.execute(
            """UPDATE cost_models SET model_config = ?, is_active = ? 
            WHERE user_id = ? AND model_name = ?""",
            (model_json, 1 if is_active else 0, user_id, model_name),
        )

    conn.commit()
    record_id = c.lastrowid
    conn.close()
    return record_id


def get_cost_models(user_id: str) -> List[Dict[str, Any]]:
    """Get all cost models for a user."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT id, model_name, model_config, is_active, created_at FROM cost_models WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "model_name": row[1],
            "model_config": json.loads(row[2]),
            "is_active": bool(row[3]),
            "created_at": row[4],
        }
        for row in rows
    ]


def get_active_cost_model(user_id: str) -> Optional[Dict[str, Any]]:
    """Get the active cost model for a user."""
    models = get_cost_models(user_id)
    active = next((m for m in models if m["is_active"]), None)
    return active


# ============ Request Logging ============


def log_request(
    endpoint: str,
    method: str,
    status_code: int,
    response_time_ms: float,
    user_id: Optional[str] = None,
    error_message: Optional[str] = None,
) -> None:
    """Log an API request."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        """INSERT INTO request_logs 
        (endpoint, method, status_code, response_time_ms, user_id, error_message)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (endpoint, method, status_code, response_time_ms, user_id, error_message),
    )

    conn.commit()
    conn.close()


def get_request_logs(limit: int = 100, hours: int = 24) -> List[Dict[str, Any]]:
    """Get recent request logs."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        f"""SELECT * FROM request_logs 
        WHERE created_at > datetime('now', '-{hours} hours')
        ORDER BY created_at DESC 
        LIMIT ?""",
        (limit,),
    )
    rows = c.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "endpoint": row[1],
            "method": row[2],
            "status_code": row[3],
            "response_time_ms": row[4],
            "user_id": row[5],
            "error_message": row[6],
            "created_at": row[7],
        }
        for row in rows
    ]


def get_metrics() -> Dict[str, Any]:
    """Get API metrics."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('SELECT COUNT(*) FROM request_logs WHERE created_at > datetime("now", "-1 hour")')
    requests_1h = c.fetchone()[0]

    c.execute('SELECT AVG(response_time_ms) FROM request_logs WHERE created_at > datetime("now", "-1 hour")')
    avg_response_time = c.fetchone()[0] or 0.0

    c.execute('SELECT COUNT(*) FROM request_logs WHERE status_code >= 400')
    total_errors = c.fetchone()[0]

    c.execute('SELECT COUNT(DISTINCT user_id) FROM scenario_history')
    unique_users = c.fetchone()[0]

    c.execute('SELECT COUNT(*) FROM scenario_history')
    total_scenarios_run = c.fetchone()[0]

    conn.close()

    return {
        "requests_last_1h": requests_1h,
        "avg_response_time_ms": round(avg_response_time, 2),
        "total_errors": total_errors,
        "unique_users": unique_users,
        "total_scenarios_run": total_scenarios_run,
    }


# ============ Training Jobs ============


def create_training_job(job_id: str, model_type: str, config: Dict[str, Any]) -> str:
    """Create a new training job."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    config_json = json.dumps(config)

    c.execute(
        """INSERT INTO training_jobs (job_id, model_type, status, config)
        VALUES (?, ?, ?, ?)""",
        (job_id, model_type, "pending", config_json),
    )

    conn.commit()
    conn.close()
    return job_id


def update_training_job(
    job_id: str,
    status: Optional[str] = None,
    progress_percent: Optional[int] = None,
    result: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
) -> None:
    """Update training job status."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    updates = []
    params = []

    if status:
        updates.append("status = ?")
        params.append(status)
    if progress_percent is not None:
        updates.append("progress_percent = ?")
        params.append(progress_percent)
    if result:
        updates.append("result = ?")
        params.append(json.dumps(result))
    if error_message:
        updates.append("error_message = ?")
        params.append(error_message)

    if status == "completed":
        updates.append("completed_at = CURRENT_TIMESTAMP")
    if status == "running" and not any("started_at" in u for u in updates):
        updates.append("started_at = CURRENT_TIMESTAMP")

    params.append(job_id)

    query = f"UPDATE training_jobs SET {', '.join(updates)} WHERE job_id = ?"
    c.execute(query, params)

    conn.commit()
    conn.close()


def get_training_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Get training job details."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT * FROM training_jobs WHERE job_id = ?", (job_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "job_id": row[1],
        "model_type": row[2],
        "status": row[3],
        "progress_percent": row[4],
        "config": json.loads(row[5]) if row[5] else None,
        "result": json.loads(row[6]) if row[6] else None,
        "error_message": row[7],
        "started_at": row[8],
        "completed_at": row[9],
        "created_at": row[10],
    }
