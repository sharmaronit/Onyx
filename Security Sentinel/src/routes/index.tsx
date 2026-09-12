import { createFileRoute, Link } from "@tanstack/react-router";
import { Metric, Panel, Shell } from "@/components/soc/Shell";
import { MiniMap } from "@/components/soc/MiniMap";
import { kpis, nodeById, patches, riskTrend, segmentRisk } from "@/lib/soc-data";
import { roleLabel, useRole } from "@/lib/rbac";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Executive Overview — Sentinel Graph SOC Console" },
      {
        name: "description",
        content:
          "Enterprise SOC console: attack-path risk posture, exposure analysis, breach simulation replay and patch ROI prioritization.",
      },
      { property: "og:title", content: "Executive Overview — Sentinel Graph SOC Console" },
      {
        property: "og:description",
        content:
          "Attack-path risk posture, simulation replay and patch ROI prioritization for enterprise security operations.",
      },
    ],
  }),
  component: Overview,
});

function Sparkline({ data }: { data: number[] }) {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const pts = data
    .map((v, i) => `${(i / (data.length - 1)) * 100},${100 - ((v - min) / (max - min || 1)) * 88 - 6}`)
    .join(" ");
  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="h-24 w-full">
      <polyline
        points={pts}
        fill="none"
        stroke="var(--primary)"
        strokeWidth="2"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

function Overview() {
  const { role } = useRole();
  return (
    <Shell>
      <div className="space-y-6">
        <div className="panel bg-tile px-8 py-10 text-tile-foreground">
          <p className="text-[12px] uppercase tracking-[0.08em] text-tile-muted">
            Signed in as {roleLabel(role)}
          </p>
          <h2 className="mt-3 hero-display max-w-3xl">
            Your riskiest path is four hops long.
          </h2>
          <p className="mt-4 max-w-xl text-[17px] text-tile-muted">
            Aggregate posture across 10 monitored assets, 148 reachable attack paths and 12 paths
            terminating on crown-jewel data.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              to="/simulation"
              className="rounded-full bg-primary px-6 py-2.5 text-[15px] text-primary-foreground transition-opacity hover:opacity-90"
            >
              Review latest episode
            </Link>
            <Link
              to="/patches"
              className="rounded-full px-6 py-2.5 text-[15px] text-primary-on-dark transition-opacity hover:opacity-80"
            >
              Prioritized patch plan ›
            </Link>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Metric
            label="Composite risk score"
            value={String(kpis.riskScore)}
            sub={`${kpis.riskDelta} vs. last week`}
            tone="destructive"
          />
          <Metric label="Reachable attack paths" value={String(kpis.exposedPaths)} sub={`${kpis.criticalPaths} reach restricted data`} />
          <Metric label="Mean path length" value={kpis.meanPathLength.toFixed(1)} sub="hops to crown jewels" tone="primary" />
          <Metric label="Telemetry coverage" value={`${kpis.coverage}%`} sub="of assets reporting" tone="success" />
        </div>

        <div className="grid gap-6 xl:grid-cols-3">
          <Panel title="Risk trend — 10 weeks" className="xl:col-span-2">
            <div className="p-5">
              <Sparkline data={riskTrend} />
              <div className="mt-3 flex justify-between text-[12px] text-muted-foreground tabular">
                <span>W-10 · 88</span>
                <span>Now · {kpis.riskScore}</span>
              </div>
            </div>
          </Panel>
          <Panel title="Risk by segment">
            <ul className="divide-y divide-hairline">
              {segmentRisk.map((s) => (
                <li key={s.segment} className="flex items-center gap-4 px-5 py-3.5">
                  <span className="w-24 text-[13px]">{s.segment}</span>
                  <span className="h-1.5 flex-1 rounded-full bg-muted">
                    <span
                      className="block h-full rounded-full bg-primary"
                      style={{ width: `${s.score}%` }}
                    />
                  </span>
                  <span className="w-8 text-right text-[13px] tabular">{s.score}</span>
                </li>
              ))}
            </ul>
          </Panel>
        </div>

        <Panel title="Latest simulated blast radius">
          <MiniMap compromised={["lap-b", "jump-01", "app-02", "dc-01", "db-fin"]} height={300} />
        </Panel>

        <Panel title="Top three recommended actions">
          <table className="w-full text-[13px]">
            <thead className="bg-pearl text-left text-[12px] text-muted-foreground">
              <tr>
                <th className="px-5 py-2.5 font-normal">Rank</th>
                <th className="px-5 py-2.5 font-normal">Node</th>
                <th className="px-5 py-2.5 font-normal">CVE</th>
                <th className="px-5 py-2.5 font-normal text-right">Risk reduction</th>
                <th className="px-5 py-2.5 font-normal text-right">ROI</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-hairline">
              {patches.slice(0, 3).map((p) => (
                <tr key={p.cve}>
                  <td className="px-5 py-3 tabular">{p.rank}</td>
                  <td className="px-5 py-3">{nodeById(p.node).label}</td>
                  <td className="px-5 py-3 font-mono text-[12px]">{p.cve}</td>
                  <td className="px-5 py-3 text-right tabular">{p.riskReduction}%</td>
                  <td className="px-5 py-3 text-right tabular">{p.roi}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      </div>
    </Shell>
  );
}
