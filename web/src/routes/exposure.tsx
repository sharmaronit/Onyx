import { createFileRoute } from "@tanstack/react-router";
import { Metric, Panel, Shell } from "@/components/soc/Shell";
import { useStatus, useTopology, usePatchResults, useRealityExposure } from "@/hooks/use-api";
import { useAppMode } from "@/lib/app-mode";

export const Route = createFileRoute("/exposure")({
  head: () => ({
    meta: [
      { title: "Exposure Analysis — Onyx" },
      {
        name: "description",
        content:
          "Attack-path exposure analysis: chokepoints, crown-jewel reachability and open vulnerability findings by asset.",
      },
      { property: "og:title", content: "Exposure Analysis — Onyx" },
      {
        property: "og:description",
        content: "Chokepoints, crown-jewel reachability and open vulnerability findings by asset.",
      },
    ],
  }),
  component: Exposure,
});

const paths = [
  { id: "P-001", entry: "lap-b", target: "db-fin", hops: 4, likelihood: 0.62, impact: "Critical" },
  {
    id: "P-002",
    entry: "vpn-01",
    target: "s3-backup",
    hops: 3,
    likelihood: 0.48,
    impact: "Critical",
  },
  { id: "P-003", entry: "web-01", target: "db-fin", hops: 3, likelihood: 0.41, impact: "Critical" },
  { id: "P-004", entry: "lap-a", target: "dc-01", hops: 2, likelihood: 0.37, impact: "High" },
  { id: "P-005", entry: "fw-edge", target: "app-02", hops: 3, likelihood: 0.29, impact: "High" },
  { id: "P-006", entry: "lap-b", target: "s3-backup", hops: 4, likelihood: 0.24, impact: "Medium" },
];

function Exposure() {
  const { mode } = useAppMode();
  const status = useStatus();
  const topology = useTopology();
  const patchesQuery = usePatchResults();
  const reality = useRealityExposure();

  if (mode === "reality") {
    if (reality.isLoading)
      return (
        <Shell>
          <div className="p-8">Loading verified exposure evidence…</div>
        </Shell>
      );
    if (reality.error)
      return (
        <Shell>
          <Panel title="Exposure analysis unavailable">
            <p className="p-5 text-sm text-destructive">{reality.error.message}</p>
          </Panel>
        </Shell>
      );
    const live = reality.data;
    if (!live?.ready)
      return (
        <Shell>
          <div className="space-y-6">
            <Panel title="Exposure coverage">
              <div className="p-5">
                <p className="text-sm text-muted-foreground">
                  Exposure Analysis maps evidence of reachability from vulnerable assets. It is
                  blocked until the live asset graph is trustworthy.
                </p>
                <div className="mt-5 grid gap-3 md:grid-cols-3">
                  <Metric
                    label="Assets discovered"
                    value={String(live?.readiness.assets ?? 0)}
                    sub="identity coverage"
                    tone={(live?.readiness.assets ?? 0) > 0 ? "success" : "warning"}
                  />
                  <Metric
                    label="Topology evidence"
                    value={String(live?.readiness.relationships ?? 0)}
                    sub="observed network links"
                    tone={(live?.readiness.relationships ?? 0) > 0 ? "success" : "warning"}
                  />
                  <Metric
                    label="Assets exposed"
                    value={String(live?.readiness.findings ?? 0)}
                    sub="with scanner findings"
                    tone={(live?.readiness.findings ?? 0) > 0 ? "success" : "warning"}
                  />
                </div>
                <div className="mt-5 rounded-md bg-pearl p-4 text-sm">
                  <b>To unlock:</b> collect observed network relationships and import vulnerability
                  findings. This page will then show exposure routes and vulnerable assets—not patch
                  priorities.
                </div>
              </div>
            </Panel>
          </div>
        </Shell>
      );
    return (
      <Shell>
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-4">
            <Metric
              label="Open findings"
              value={String(live.findings.length)}
              sub={`${live.readiness.assets} verified assets`}
            />
            <Metric
              label="Critical CVEs"
              value={String(live.findings.filter((f: any) => f.cvss_score >= 9).length)}
              sub="scanner-reported CVSS ≥ 9"
              tone="destructive"
            />
            <Metric
              label="Observed exposure links"
              value={String(live.paths.length)}
              sub={`${live.readiness.relationships} verified relationships`}
              tone="primary"
            />
            <Metric
              label="Evidence freshness"
              value="Live"
              sub={live.provenance || "source attributed"}
              tone="success"
            />
          </div>
          <Panel title="Assets with live vulnerability evidence">
            <div className="divide-y divide-hairline">
              {live.assets.map((asset: any) => (
                <div key={asset.endpoint_id} className="flex justify-between gap-4 p-5 text-sm">
                  <span>
                    <b>{asset.hostname}</b>
                    <span className="ml-2 text-muted-foreground">{asset.endpoint_id}</span>
                  </span>
                  <span>
                    {asset.open_findings} findings · CVSS {asset.max_cvss.toFixed(1)}
                  </span>
                </div>
              ))}
            </div>
          </Panel>
          <Panel title="Observed relationships from exposed assets">
            <div className="divide-y divide-hairline">
              {live.paths.length ? (
                live.paths.map((path: any) => (
                  <div key={path.id} className="p-4 text-sm">
                    <b>{path.entry}</b> → {path.target}
                    <span className="ml-3 text-muted-foreground">
                      {path.relation_type} · {(path.confidence * 100).toFixed(0)}% observed
                      confidence
                    </span>
                  </div>
                ))
              ) : (
                <p className="p-5 text-sm text-muted-foreground">
                  No exposed asset has an observed outgoing relationship yet.
                </p>
              )}
            </div>
          </Panel>
          <Panel title="Live vulnerability backlog">
            <div className="divide-y divide-hairline">
              {live.findings.map((finding: any) => (
                <div
                  key={`${finding.endpoint_id}-${finding.finding_id}`}
                  className="flex justify-between gap-4 p-4 text-sm"
                >
                  <span>
                    <b>{finding.cve_id || finding.finding_id}</b> · {finding.title}
                    <span className="ml-2 text-muted-foreground">
                      on {finding.endpoint_id} · {finding.source}
                    </span>
                  </span>
                  <span>
                    CVSS {finding.cvss_score.toFixed(1)} ·{" "}
                    {finding.fix_available ? "fix available" : "no verified fix"}
                  </span>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </Shell>
    );
  }

  if (status.isLoading || topology.isLoading || patchesQuery.isLoading) {
    return (
      <Shell>
        <div className="p-8">Loading exposure data...</div>
      </Shell>
    );
  }

  const nodes = topology.data?.nodes || [];
  const patches = patchesQuery.data?.results || [];
  const nodeById = (id: string) =>
    nodes.find((n: any) => n.node_id === id) || {
      label: id,
      segment: "Unknown",
      node_type: "Unknown",
    };

  const kpis = {
    criticalPaths: status.data?.critical_assets || 0,
    openFindings: status.data?.total_cves || 0,
    criticalCves: patches.filter((p: any) => (p.cvss_score ?? p.cvss ?? 0) >= 9.0).length,
  };

  const segmentRisk = [
    { segment: "DMZ", score: 84, assets: 3 },
    { segment: "Corp", score: 68, assets: 3 },
    { segment: "Core", score: 57, assets: 2 },
    { segment: "Restricted", score: 41, assets: 2 },
  ];

  return (
    <Shell>
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-4">
          <Metric
            label="Open findings"
            value={String(kpis.openFindings)}
            sub={`across ${nodes.length} assets`}
          />
          <Metric
            label="Critical CVEs"
            value={String(kpis.criticalCves)}
            sub="CVSS ≥ 9.0"
            tone="destructive"
          />
          <Metric
            label="Crown jewels"
            value={String(kpis.criticalPaths)}
            sub="monitored"
            tone="primary"
          />
          <Metric
            label="Chokepoints"
            value="2"
            sub="App Server 02 · Domain Controller"
            tone="warning"
          />
        </div>

        <Panel title="Highest-likelihood attack paths">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-[13px]">
              <thead className="bg-pearl text-left text-[12px] text-muted-foreground">
                <tr>
                  <th className="px-5 py-2.5 font-normal">Path</th>
                  <th className="px-5 py-2.5 font-normal">Entry point</th>
                  <th className="px-5 py-2.5 font-normal">Target</th>
                  <th className="px-5 py-2.5 font-normal text-right">Hops</th>
                  <th className="px-5 py-2.5 font-normal">Likelihood</th>
                  <th className="px-5 py-2.5 font-normal">Impact</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {paths.map((p) => (
                  <tr key={p.id} className="hover:bg-pearl">
                    <td className="px-5 py-3 font-mono text-[12px]">{p.id}</td>
                    <td className="px-5 py-3">{nodeById(p.entry).label}</td>
                    <td className="px-5 py-3">{nodeById(p.target).label}</td>
                    <td className="px-5 py-3 text-right tabular">{p.hops}</td>
                    <td className="px-5 py-3">
                      <span className="flex items-center gap-2">
                        <span className="h-1.5 w-24 rounded-full bg-muted">
                          <span
                            className="block h-full rounded-full bg-primary"
                            style={{ width: `${p.likelihood * 100}%` }}
                          />
                        </span>
                        <span className="tabular text-[12px]">
                          {(p.likelihood * 100).toFixed(0)}%
                        </span>
                      </span>
                    </td>
                    <td className="px-5 py-3">{p.impact}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <div className="grid gap-6 xl:grid-cols-2">
          <Panel title="Findings by asset">
            <ul className="divide-y divide-hairline">
              {nodes.slice(0, 6).map((n: any, i: number) => (
                <li
                  key={n.node_id}
                  className="flex items-center justify-between px-5 py-3.5 text-[13px]"
                >
                  <span>
                    {n.node_id}
                    <span className="ml-2 text-[12px] text-muted-foreground">{n.node_type}</span>
                  </span>
                  <span className="tabular text-muted-foreground">{n.num_vulns || 0} open</span>
                </li>
              ))}
            </ul>
          </Panel>
          <Panel title="Segment exposure vs. asset count">
            <ul className="divide-y divide-hairline">
              {segmentRisk.map((s) => (
                <li key={s.segment} className="px-5 py-4">
                  <div className="flex items-baseline justify-between text-[13px]">
                    <span>{s.segment}</span>
                    <span className="tabular text-muted-foreground">
                      {s.assets} assets · score {s.score}
                    </span>
                  </div>
                  <span className="mt-2 block h-1.5 rounded-full bg-muted">
                    <span
                      className="block h-full rounded-full bg-primary"
                      style={{ width: `${s.score}%` }}
                    />
                  </span>
                </li>
              ))}
            </ul>
          </Panel>
        </div>

        <Panel title="Vulnerability backlog">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-[13px]">
              <thead className="bg-pearl text-left text-[12px] text-muted-foreground">
                <tr>
                  <th className="px-5 py-2.5 font-normal">CVE</th>
                  <th className="px-5 py-2.5 font-normal">Node</th>
                  <th className="px-5 py-2.5 font-normal text-right">CVSS</th>
                  <th className="px-5 py-2.5 font-normal text-right">Effort (h)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {patches.map((p: any) => (
                  <tr key={p.cve_id || p.cve} className="hover:bg-pearl">
                    <td className="px-5 py-3 font-mono text-[12px]">{p.cve_id}</td>
                    <td className="px-5 py-3">{nodeById(p.node_id).label || p.node_id}</td>
                    <td className="px-5 py-3 text-right tabular">
                      {p.cvss_score?.toFixed(1) ?? "—"}
                    </td>
                    <td className="px-5 py-3 text-right tabular">
                      {p.simulation_impact ? (p.simulation_impact * 100).toFixed(1) + "%" : "—"}
                    </td>
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
