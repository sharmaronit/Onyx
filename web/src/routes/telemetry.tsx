import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Locked, Metric, Panel, Shell } from "@/components/soc/Shell";
import {
  useEndpointCommand,
  useEndpoints,
  useCapabilities,
  useResolveIncident,
  useServerLink,
  useTelemetryEvents,
  useTelemetryStatus,
  useTopologies,
} from "@/hooks/use-api";
import type { EndpointAgent, TelemetryEvent } from "@/lib/api";
import { can, useRole } from "@/lib/rbac";
import { useAppMode } from "@/lib/app-mode";

export const Route = createFileRoute("/telemetry")({
  head: () => ({
    meta: [
      { title: "Live Endpoint Telemetry — Onyx" },
      {
        name: "description",
        content:
          "Live endpoint heartbeats, Microsoft Defender evidence, and acknowledged response actions.",
      },
    ],
  }),
  component: Telemetry,
});

function eventEvidence(event: TelemetryEvent) {
  const raw = event.raw ?? {};
  const threat = typeof raw["threat_name"] === "string" ? raw["threat_name"] : null;
  const path = typeof raw["path"] === "string" ? raw["path"] : null;
  if (threat && path) return `${threat} · ${path}`;
  if (threat) return threat;
  if (path) return path;
  return `${event.source_node} → ${event.target_node}`;
}

function ageLabel(seconds: number | null | undefined) {
  if (seconds == null) return "unknown";
  if (seconds < 60) return `${Math.round(seconds)}s ago`;
  return `${Math.round(seconds / 60)}m ago`;
}

function endpointTone(endpoint: EndpointAgent) {
  if (endpoint.security_state === "critical") return "bg-primary";
  if (
    endpoint.security_state === "compromised" ||
    endpoint.security_state === "affected" ||
    endpoint.quarantined
  )
    return "bg-destructive";
  if (endpoint.security_state === "warning") return "bg-warning";
  if (endpoint.status === "active") return "bg-success";
  return "bg-tile-muted";
}

function Telemetry() {
  const { role } = useRole();
  const { mode } = useAppMode();
  const allowedToView = can.viewTelemetry(role);
  const capabilities = useCapabilities();
  const responseControlsEnabled = capabilities.data?.response_controls === true;
  const allowedToRespond = can.respondToEndpoint(role) && responseControlsEnabled;
  const [live, setLive] = useState(true);
  const [topology, setTopology] = useState("enterprise_20n");
  const [responseKey, setResponseKey] = useState("");
  const [reason, setReason] = useState("Confirmed security threat during authorized demonstration");

  const topologies = useTopologies();
  const status = useTelemetryStatus(topology, allowedToView && live);
  const endpointQuery = useEndpoints(topology, allowedToView && live);
  const eventQuery = useTelemetryEvents(topology, allowedToView && live);
  const command = useEndpointCommand();
  const resolveIncident = useResolveIncident();
  const serverLink = useServerLink();
  const endpoints = endpointQuery.data?.endpoints ?? [];
  const registeredEndpointIds = new Set(endpoints.map((endpoint) => endpoint.endpoint_id));
  const events = (eventQuery.data?.events ?? []).filter((event) =>
    registeredEndpointIds.has(event.source_node),
  );
  const endpointEventCount = endpoints.reduce((total, endpoint) => total + endpoint.event_count, 0);
  const defenderDetectionCount = endpoints.reduce(
    (total, endpoint) => total + endpoint.threat_count,
    0,
  );
  const quarantinedCount = endpoints.filter((endpoint) => endpoint.quarantined).length;
  const affectedCount = endpoints.filter((endpoint) =>
    ["warning", "compromised", "critical", "affected"].includes(
      endpoint.security_state ?? "healthy",
    ),
  ).length;
  const activeCount = endpoints.filter((endpoint) => endpoint.status === "active").length;
  const loadError = status.error || endpointQuery.error || eventQuery.error || topologies.error;

  const requestAction = (endpoint: EndpointAgent, action: "quarantine" | "restore") => {
    const verb = action === "quarantine" ? "quarantine" : "restore connectivity for";
    if (
      !window.confirm(
        `Send a ${action} command to ${endpoint.hostname}? This will ${verb} the endpoint.`,
      )
    ) {
      return;
    }
    command.mutate({
      endpointId: endpoint.endpoint_id,
      action,
      reason,
      requestedBy: role,
      responseKey,
    });
  };

  if (!allowedToView) {
    return (
      <Shell>
        <Locked>
          Endpoint telemetry is available to SOC Analyst and Security Architect roles.
        </Locked>
      </Shell>
    );
  }

  return (
    <Shell>
      <div className="space-y-6">
        {(loadError || command.error) && (
          <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
            {loadError
              ? `Backend telemetry unavailable: ${loadError.message}`
              : `Response action failed: ${command.error?.message}`}
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-5">
          <Metric
            label="Affected laptops"
            value={String(affectedCount)}
            sub="open security incidents"
            tone={affectedCount ? "destructive" : "success"}
          />
          <Metric
            label="Registered endpoints"
            value={String(endpoints.length)}
            sub={`${activeCount} reporting within 30 seconds`}
          />
          <Metric
            label="Events stored"
            value={String(endpointEventCount)}
            sub="events from registered endpoint agents"
            tone="primary"
          />
          <Metric
            label="Defender detections"
            value={String(defenderDetectionCount)}
            sub="confirmed Microsoft Defender events"
            tone={defenderDetectionCount ? "destructive" : "success"}
          />
          <Metric
            label="Quarantined"
            value={String(quarantinedCount)}
            sub="endpoint-acknowledged policies"
            tone={quarantinedCount ? "warning" : "success"}
          />
        </div>

        <Panel title="Live controls">
          {!responseControlsEnabled && (
            <div className="border-b border-warning/30 bg-warning/5 px-5 py-3 text-[12px] text-warning">
              Response controls are disabled by the server. Telemetry remains read-only.
            </div>
          )}
          <div className="grid gap-4 p-5 md:grid-cols-3">
            <label className="text-[12px] text-muted-foreground">
              Topology
              <select
                value={topology}
                onChange={(event) => setTopology(event.target.value)}
                className="mt-1 block w-full rounded-md border border-hairline bg-card px-3 py-2 text-foreground"
              >
                {Object.keys(topologies.data?.topologies ?? {}).map((key) => (
                  <option key={key} value={key}>
                    {key}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-[12px] text-muted-foreground">
              {mode === "demo" ? "Demo response" : "Response authorization key"}
              <input
                type="password"
                autoComplete="off"
                value={responseKey}
                onChange={(event) => setResponseKey(event.target.value)}
                placeholder={
                  mode === "demo"
                    ? "No key required for simulated actions"
                    : "Required for response actions"
                }
                disabled={mode === "demo"}
                className="mt-1 block w-full rounded-md border border-hairline bg-card px-3 py-2 text-foreground"
              />
            </label>
            <label className="text-[12px] text-muted-foreground">
              Audit reason
              <input
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                className="mt-1 block w-full rounded-md border border-hairline bg-card px-3 py-2 text-foreground"
              />
            </label>
          </div>
          <div className="flex items-center justify-between border-t border-hairline px-5 py-3 text-[12px] text-muted-foreground">
            <span>{live ? "Polling backend every 3 seconds" : "Live polling paused"}</span>
            <button
              onClick={() => setLive((current) => !current)}
              className="rounded-md bg-foreground px-4 py-1.5 text-primary-foreground"
            >
              {live ? "Pause" : "Resume"}
            </button>
          </div>
        </Panel>

        <Panel title="Real endpoint inventory">
          <div className="grid gap-4 p-5 sm:grid-cols-2 xl:grid-cols-3">
            {endpoints.length === 0 && (
              <p className="text-sm text-muted-foreground">
                No endpoint agent has registered with this backend yet.
              </p>
            )}
            {[...endpoints]
              .sort(
                (a, b) =>
                  Number(
                    ["warning", "compromised", "critical", "affected"].includes(
                      b.security_state ?? "",
                    ),
                  ) -
                  Number(
                    ["warning", "compromised", "critical", "affected"].includes(
                      a.security_state ?? "",
                    ),
                  ),
              )
              .map((endpoint) => {
                const actionPending =
                  endpoint.latest_command &&
                  ["pending", "delivered"].includes(endpoint.latest_command.status);
                const responseCapable = endpoint.metadata["response_capable"] === true;
                return (
                  <div
                    key={endpoint.endpoint_id}
                    className={`rounded-lg border p-4 ${endpoint.security_state === "critical" ? "border-primary bg-primary/5" : endpoint.security_state === "compromised" || endpoint.security_state === "affected" ? "border-destructive bg-destructive/5" : endpoint.security_state === "warning" ? "border-warning bg-warning/5" : "border-hairline"}`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-[13px] font-semibold">{endpoint.hostname}</p>
                        <p className="font-mono text-[11px] text-muted-foreground">
                          {endpoint.endpoint_id}
                        </p>
                      </div>
                      <span className={`mt-1 h-2.5 w-2.5 rounded-full ${endpointTone(endpoint)}`} />
                    </div>
                    <dl className="mt-4 space-y-1.5 text-[12px] text-muted-foreground">
                      <div className="flex justify-between">
                        <dt>IP address</dt>
                        <dd>{endpoint.ip_address || "unknown"}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt>Heartbeat</dt>
                        <dd>{ageLabel(endpoint.seconds_since_last_seen)}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt>Agent</dt>
                        <dd>v{endpoint.agent_version}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt>Defender threats</dt>
                        <dd>{endpoint.threat_count}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt>Network state</dt>
                        <dd>{endpoint.quarantined ? "quarantined" : endpoint.status}</dd>
                      </div>
                    </dl>
                    {endpoint.latest_command && (
                      <p className="mt-3 rounded bg-pearl p-2 text-[11px] text-muted-foreground">
                        {endpoint.latest_command.action}: {endpoint.latest_command.status}
                        {endpoint.latest_command.error_message
                          ? ` · ${endpoint.latest_command.error_message}`
                          : ""}
                      </p>
                    )}
                    {endpoint.last_error && (
                      <p className="mt-2 text-[11px] text-destructive">
                        Agent error: {endpoint.last_error}
                      </p>
                    )}
                    {endpoint.latest_incident && (
                      <div className="mt-3 rounded bg-destructive/10 p-2 text-[11px] text-destructive">
                        <p className="font-semibold">
                          Affected ·{" "}
                          {endpoint.latest_incident.source === "simulated"
                            ? "Safe simulated detection"
                            : "Microsoft Defender"}
                        </p>
                        <p>{endpoint.latest_incident.summary}</p>
                        <button
                          disabled={!allowedToRespond || resolveIncident.isPending}
                          onClick={() =>
                            resolveIncident.mutate({
                              incidentId: endpoint.latest_incident!.incident_id,
                              resolvedBy: role,
                              reason,
                              responseKey,
                            })
                          }
                          className="mt-2 rounded bg-foreground px-2 py-1 text-primary-foreground disabled:bg-chip"
                        >
                          Resolve incident
                        </button>
                      </div>
                    )}
                    {["warning", "compromised", "critical", "affected"].includes(
                      endpoint.security_state ?? "",
                    ) && (
                      <button
                        disabled={!allowedToRespond || serverLink.isPending}
                        onClick={() =>
                          serverLink.mutate({
                            endpointId: endpoint.endpoint_id,
                            disconnected: !endpoint.server_link_disconnected,
                            requestedBy: role,
                            reason,
                            responseKey,
                          })
                        }
                        className="mt-3 w-full rounded-md border border-destructive px-3 py-2 text-[12px] text-destructive disabled:border-chip disabled:text-muted-foreground"
                      >
                        {endpoint.server_link_disconnected
                          ? "Restore server link"
                          : "Cut server link"}
                      </button>
                    )}
                    <button
                      disabled={
                        !allowedToRespond ||
                        reason.trim().length < 3 ||
                        !!actionPending ||
                        command.isPending ||
                        endpoint.status !== "active" ||
                        !responseCapable
                      }
                      onClick={() =>
                        requestAction(endpoint, endpoint.quarantined ? "restore" : "quarantine")
                      }
                      className="mt-4 w-full rounded-md bg-foreground px-3 py-2 text-[12px] text-primary-foreground disabled:bg-chip disabled:text-muted-foreground"
                    >
                      {!responseCapable
                        ? "Heartbeat-only agent"
                        : actionPending
                          ? "Awaiting endpoint acknowledgement"
                          : endpoint.quarantined
                            ? "Restore protected services"
                            : "Quarantine protected services"}
                    </button>
                  </div>
                );
              })}
          </div>
          {!allowedToRespond && (
            <div className="border-t border-hairline p-5">
              <Locked>
                {responseControlsEnabled
                  ? "Endpoint response actions require the Security Architect role."
                  : "Endpoint response actions are disabled by the server."}
              </Locked>
            </div>
          )}
        </Panel>

        <Panel title="Recent backend telemetry">
          <div className="max-h-[420px] overflow-y-auto">
            {events.length === 0 && (
              <p className="p-5 text-sm text-muted-foreground">
                No telemetry events have been received.
              </p>
            )}
            {events.map((event) => (
              <div
                key={`${event.source_node}-${event.event_id}`}
                className="grid gap-2 border-b border-hairline px-5 py-3 text-[12px] md:grid-cols-[170px_160px_170px_1fr]"
              >
                <span className="font-mono text-muted-foreground">
                  {new Date(event.timestamp).toLocaleString()}
                </span>
                <span>{event.source_node}</span>
                <span
                  className={
                    event.event_type === "malware_detected"
                      ? "font-semibold text-destructive"
                      : event.blocked
                        ? "text-success"
                        : "text-muted-foreground"
                  }
                >
                  {event.event_type}
                </span>
                <span className="min-w-0 break-words">{eventEvidence(event)}</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </Shell>
  );
}
