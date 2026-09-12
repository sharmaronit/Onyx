import { createFileRoute } from "@tanstack/react-router";
import { Metric, Panel, Shell } from "@/components/soc/Shell";
import { kpis, nodeById, nodes, patches, segmentRisk } from "@/lib/soc-data";

export const Route = createFileRoute("/exposure")({
  head: () => ({
    meta: [
      { title: "Exposure Analysis — Sentinel Graph" },
      {
        name: "description",
        content:
          "Attack-path exposure analysis: chokepoints, crown-jewel reachability and open vulnerability findings by asset.",
      },
      { property: "og:title", content: "Exposure Analysis — Sentinel Graph" },
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
  { id: "P-002", entry: "vpn-01", target: "s3-backup", hops: 3, likelihood: 0.48, impact: "Critical" },
  { id: "P-003", entry: "web-01", target: "db-fin", hops: 3, likelihood: 0.41, impact: "Critical" },
  { id: "P-004", entry: "lap-a", target: "dc-01", hops: 2, likelihood: 0.37, impact: "High" },
  { id: "P-005", entry: "fw-edge", target: "app-02", hops: 3, likelihood: 0.29, impact: "High" },
  { id: "P-006", entry: "lap-b", target: "s3-backup", hops: 4, likelihood: 0.24, impact: "Medium" },
];

function Exposure() {
  return (
    <Shell>
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-4">
          <Metric label="Open findings" value="61" sub="across 10 assets" />
          <Metric label="Critical CVEs" value="9" sub="CVSS ≥ 9.0" tone="destructive" />
          <Metric label="Paths to crown jewels" value={String(kpis.criticalPaths)} sub="of 148 total" tone="primary" />
          <Metric label="Chokepoints" value="2" sub="App Server 02 · Domain Controller" tone="warning" />
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
                        <span className="tabular text-[12px]">{(p.likelihood * 100).toFixed(0)}%</span>
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
              {nodes.slice(0, 6).map((n, i) => (
                <li key={n.id} className="flex items-center justify-between px-5 py-3.5 text-[13px]">
                  <span>
                    {n.label}
                    <span className="ml-2 text-[12px] text-muted-foreground">{n.segment}</span>
                  </span>
                  <span className="tabular text-muted-foreground">{12 - i} open</span>
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
                    <span className="block h-full rounded-full bg-primary" style={{ width: `${s.score}%` }} />
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
                {patches.map((p) => (
                  <tr key={p.cve} className="hover:bg-pearl">
                    <td className="px-5 py-3 font-mono text-[12px]">{p.cve}</td>
                    <td className="px-5 py-3">{nodeById(p.node).label}</td>
                    <td className="px-5 py-3 text-right tabular">{p.cvss.toFixed(1)}</td>
                    <td className="px-5 py-3 text-right tabular">{p.effort}</td>
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
