import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Metric, Panel, Shell } from "@/components/soc/Shell";
import { MiniMap, type MapEdge, type MapNode } from "@/components/soc/MiniMap";
import { useEndpoints, useRealityTopology, useTopology } from "@/hooks/use-api";
import { useAppMode } from "@/lib/app-mode";

export const Route = createFileRoute("/topology")({
  head: () => ({
    meta: [
      { title: "Asset Topology — Onyx" },
      {
        name: "description",
        content:
          "Segment-aware asset inventory with reachability graph, exposure scores and crown-jewel classification.",
      },
      { property: "og:title", content: "Asset Topology — Onyx" },
      {
        property: "og:description",
        content: "Segment-aware asset inventory with reachability graph and exposure scores.",
      },
    ],
  }),
  component: Topology,
});

function Topology() {
  const { mode } = useAppMode();
  const reality = useRealityTopology();
  const topology = useTopology();
  const endpoints = useEndpoints();
  const [selected, setSelected] = useState<string | null>(null);

  if (mode === "reality") {
    const nodes = reality.data?.nodes ?? [];
    const edges = reality.data?.edges ?? [];
    const affected = nodes.filter((node: any) => ["compromised", "affected"].includes(node.security_state)).map((node: any) => node.node_id);
    return <Shell><div className="space-y-6"><div><p className="eyebrow">Verified asset graph</p><h2 className="mt-1 font-display text-2xl font-semibold">Live discovered topology</h2><p className="mt-2 text-sm text-muted-foreground">Nodes and connections update in place from endpoint evidence; the page does not reload.</p></div>{reality.isLoading ? <div className="p-8">Loading live topology...</div> : reality.error ? <Panel title="Reality topology unavailable"><p className="p-5 text-sm text-destructive">{reality.error.message}. Restart the backend on port 8020.</p></Panel> : nodes.length <= 1 ? <Panel title="No verified assets yet"><p className="p-5 text-sm text-muted-foreground">Enroll a Windows endpoint agent to start building this map. Static demo nodes are intentionally hidden in Reality mode.</p></Panel> : <><div className="grid gap-4 md:grid-cols-3"><Metric label="Verified assets" value={String(Math.max(0, nodes.length - 1))} sub="agents and discovered peers"/><Metric label="Observed connections" value={String(edges.length)} sub="telemetry-backed only"/><Metric label="Affected assets" value={String(affected.length)} sub="open incidents" tone={affected.length ? "destructive" : "success"}/></div><Panel title="Observed relationships"><MiniMap nodes={nodes} edges={edges} compromised={affected} active={selected ?? undefined} onSelect={setSelected} height={560} layout="circular"/></Panel></>}</div></Shell>;
  }

  if (topology.isLoading) {
    return (
      <Shell>
        <div className="p-8">Loading topology...</div>
      </Shell>
    );
  }

  const topologyNodes: MapNode[] = topology.data?.nodes || [];
  const topologyEdges: MapEdge[] = topology.data?.edges || [];
  const summary = topology.data?.summary || {};
  const serverNodeId = "onyx_control_server";
  const liveEndpoints = endpoints.data?.endpoints || [];
  const nodes: MapNode[] = [
    ...topologyNodes,
    {
      node_id: serverNodeId,
      node_type: "control server",
      software: "Onyx API",
      version: "live",
      num_vulns: 0,
      max_cvss: 0,
      severity: "informational",
      is_critical_asset: false,
      is_entry_point: false,
      endpoint_status: "active",
    },
    ...liveEndpoints
      .filter((endpoint) => !topologyNodes.some((node) => node.node_id === endpoint.endpoint_id))
      .map((endpoint) => ({
        node_id: endpoint.endpoint_id,
        node_type: "endpoint laptop",
        software: endpoint.platform || "Endpoint heartbeat agent",
        version: endpoint.agent_version,
        num_vulns: endpoint.threat_count,
        max_cvss: 0,
        severity: endpoint.threat_count > 0 ? "detection reported" : "healthy",
        is_critical_asset: false,
        is_entry_point: false,
        hostname: endpoint.hostname,
        ip_address: endpoint.ip_address,
        endpoint_status: endpoint.quarantined ? "quarantined" : endpoint.status,
        security_state: endpoint.security_state,
      })),
  ];
  const edges: MapEdge[] = [
    ...topologyEdges,
    ...liveEndpoints
      .filter((endpoint) => nodes.some((node) => node.node_id === endpoint.endpoint_id) && !endpoint.server_link_disconnected)
      .map((endpoint) => ({
        source: endpoint.endpoint_id,
        target: serverNodeId,
        connection_type: "authenticated heartbeat",
        permission_level: "agent",
        has_firewall: true,
      })),
  ];

  // Default to first node if none selected
  const activeNodeId = selected || nodes[0]?.node_id;
  const node = nodes.find((n) => n.node_id === activeNodeId) || {
    node_id: activeNodeId || "unknown",
  };
  const selectedEndpoint = liveEndpoints.find((endpoint) => endpoint.endpoint_id === activeNodeId);

  const neighbours = edges
    .filter((edge) => edge.source === activeNodeId || edge.target === activeNodeId)
    .map((edge) => (edge.source === activeNodeId ? edge.target : edge.source));

  const nodeById = (id: string): MapNode => nodes.find((n) => n.node_id === id) || { node_id: id };

  return (
    <Shell>
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-4">
          <Metric
            label="Monitored assets"
            value={String(nodes.length)}
            sub={`${liveEndpoints.length} live endpoint agents`}
          />
          <Metric
            label="Crown jewels"
            value={String(summary.critical_assets || 0)}
            sub="critical classification"
            tone="primary"
          />
          <Metric
            label="Graph edges"
            value={String(edges.length)}
            sub="modeled and agent connections"
          />
          <Metric
            label="Total CVEs"
            value={String(summary.total_cves || 0)}
            sub="vulnerabilities across network"
            tone="destructive"
          />
        </div>

        <div className="grid gap-6 xl:grid-cols-3">
          <Panel title="Reachability graph" className="xl:col-span-2">
            <MiniMap
              nodes={nodes}
              edges={edges}
              compromised={liveEndpoints.filter((endpoint) => ["compromised", "affected"].includes(endpoint.security_state)).map((endpoint) => endpoint.endpoint_id)}
              active={activeNodeId}
              onSelect={setSelected}
              height={480}
            />
          </Panel>
          <Panel title="Asset detail">
            <div className="space-y-4 p-5">
              <div>
                <p className="eyebrow">{node.node_type} role</p>
                <h3 className="mt-1 font-display text-[21px] font-semibold">{node.node_id}</h3>
                <p className="mt-1 font-mono text-[12px] text-muted-foreground">
                  {node.software} {node.version}
                </p>
                {node.hostname && (
                  <p className="mt-1 text-[12px] text-muted-foreground">
                    {node.hostname} {node.ip_address ? `(${node.ip_address})` : ""}
                  </p>
                )}
              </div>
              <dl className="space-y-2.5 text-[13px]">
                {selectedEndpoint?.latest_incident && <div className="rounded border border-destructive bg-destructive/5 p-2 text-[12px] text-destructive">
                  <p className="font-semibold">Affected · {selectedEndpoint.latest_incident.source === "simulated" ? "Safe simulated detection" : "Microsoft Defender"}</p>
                  <p>{selectedEndpoint.latest_incident.summary}</p>
                </div>}
                <div className="flex justify-between border-b border-hairline pb-2">
                  <dt className="text-muted-foreground">Vulnerabilities</dt>
                  <dd>
                    {node.num_vulns || 0}{" "}
                    {node.node_type === "endpoint laptop" ? "detections" : "CVEs"}
                  </dd>
                </div>
                <div className="flex justify-between border-b border-hairline pb-2">
                  <dt className="text-muted-foreground">Max CVSS</dt>
                  <dd className="tabular">{node.max_cvss || 0}</dd>
                </div>
                <div className="flex justify-between border-b border-hairline pb-2">
                  <dt className="text-muted-foreground">Classification</dt>
                  <dd>
                    {node.is_critical_asset
                      ? "Crown jewel"
                      : node.is_entry_point
                        ? "Entry point"
                        : "Standard"}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Adjacent nodes</dt>
                  <dd className="tabular">{neighbours.length}</dd>
                </div>
              </dl>
              <div className="flex flex-wrap gap-2">
                {neighbours.map((n: string) => (
                  <button
                    key={n}
                    onClick={() => setSelected(n)}
                    className="rounded-full bg-pearl px-3 py-1.5 text-[12px] text-secondary-foreground hover:text-primary"
                  >
                    {nodeById(n).node_id}
                  </button>
                ))}
              </div>
            </div>
          </Panel>
        </div>

        <Panel title="Inventory">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-[13px]">
              <thead className="bg-pearl text-left text-[12px] text-muted-foreground">
                <tr>
                  <th className="px-5 py-2.5 font-normal">Asset</th>
                  <th className="px-5 py-2.5 font-normal">Software</th>
                  <th className="px-5 py-2.5 font-normal">Type</th>
                  <th className="px-5 py-2.5 font-normal">Severity</th>
                  <th className="px-5 py-2.5 font-normal">Class</th>
                  <th className="px-5 py-2.5 font-normal text-right">CVSS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {nodes.map((n) => (
                  <tr
                    key={n.node_id}
                    onClick={() => setSelected(n.node_id)}
                    className={`cursor-pointer transition-colors hover:bg-pearl ${
                      activeNodeId === n.node_id ? "bg-pearl" : ""
                    }`}
                  >
                    <td className="px-5 py-3">{n.node_id}</td>
                    <td className="px-5 py-3 font-mono text-[12px] text-muted-foreground">
                      {n.software}
                    </td>
                    <td className="px-5 py-3">{n.node_type}</td>
                    <td className="px-5 py-3">{n.severity}</td>
                    <td className="px-5 py-3">
                      {n.is_critical_asset ? "Crown jewel" : "Standard"}
                    </td>
                    <td className="px-5 py-3 text-right tabular">{n.max_cvss}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>
    </Shell>
  );
}
