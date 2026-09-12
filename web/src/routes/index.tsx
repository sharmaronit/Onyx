import { createFileRoute, Link } from "@tanstack/react-router";
import { Metric, Panel, Shell } from "@/components/soc/Shell";
import { MiniMap } from "@/components/soc/MiniMap";
import { useStatus, useTopology, usePatchResults, useRealityOverview } from "@/hooks/use-api";
import { roleLabel, useRole } from "@/lib/rbac";
import { useAppMode } from "@/lib/app-mode";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Executive Overview — Onyx SOC Console" },
      {
        name: "description",
        content:
          "Enterprise SOC console: attack-path risk posture, exposure analysis, breach simulation replay and patch ROI prioritization.",
      },
      { property: "og:title", content: "Executive Overview — Onyx SOC Console" },
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
    .map(
      (v, i) => `${(i / (data.length - 1)) * 100},${100 - ((v - min) / (max - min || 1)) * 88 - 6}`,
    )
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
  const { mode } = useAppMode();
  const status = useStatus();
  const topology = useTopology();
  const patchesQuery = usePatchResults();
  const live = useRealityOverview();

  if (mode === "reality") {
    const data = live.data;
    if (live.isLoading)
      return (
        <Shell>
          <div className="p-8">Loading verified live posture...</div>
        </Shell>
      );
    if (live.error)
      return (
        <Shell>
          <Panel title="Reality service unavailable">
            <div className="p-5 text-sm text-destructive">
              {live.error.message}. Restart the Onyx backend on port 8020, then refresh the browser
              once.
            </div>
          </Panel>
        </Shell>
      );
    const ready = data?.readiness ?? {};
    return (
      <Shell>
        <div className="space-y-6">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="eyebrow">Reality mode · verified customer evidence</p>
              <h2 className="mt-1 text-2xl font-semibold">Security operations overview</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Live posture from enrolled endpoints and received telemetry.
              </p>
            </div>
            <Link
              to="/telemetry"
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
            >
              Open incident queue
            </Link>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <Metric
              label="Enrolled assets"
              value={String(data?.enrolled_assets ?? 0)}
              sub={`${data?.active_assets ?? 0} reporting now`}
            />
            <Metric
              label="Affected assets"
              value={String(data?.affected_assets ?? 0)}
              sub={`${data?.open_incidents ?? 0} open incidents`}
              tone={(data?.affected_assets ?? 0) ? "destructive" : "success"}
            />
            <Metric
              label="Telemetry coverage"
              value={`${data?.coverage_percent ?? 0}%`}
              sub={`${data?.telemetry_events ?? 0} received events`}
              tone="primary"
            />
            <Metric
              label="Observed relationships"
              value={String(data?.relationships ?? 0)}
              sub="verified network evidence"
            />
          </div>
          <Panel title="Reality-mode readiness">
            <div className="grid gap-3 p-5 md:grid-cols-4">
              {Object.entries(ready).map(([key, value]) => (
                <div
                  key={key}
                  className={`rounded-md p-3 text-sm ${value ? "bg-success/10 text-success" : "bg-pearl text-muted-foreground"}`}
                >
                  {value ? "Ready" : "Required"} · {key.replaceAll("_", " ")}
                </div>
              ))}
            </div>
            {!data?.analytics_ready && (
              <p className="border-t border-hairline p-5 text-sm text-muted-foreground">
                Risk, exposure, simulation, and patch analytics remain unavailable until live
                relationship and vulnerability coverage are complete.
              </p>
            )}
          </Panel>
        </div>
      </Shell>
    );
  }

  if (status.isLoading || topology.isLoading) {
    return (
      <Shell>
        <div className="p-8">Loading dashboard...</div>
      </Shell>
    );
  }

  const kpis = {
    riskScore: status.data?.last_simulation
      ? Math.round(status.data.last_simulation.success_rate * 100)
      : 72,
    riskDelta: -6, // backend doesn't provide historical trend yet
    exposedPaths: status.data?.total_edges || 0,
    criticalPaths: status.data?.critical_assets || 0,
    meanPathLength: 4.3, // stub
    coverage: 86,
  };

  const riskTrend = [88, 85, 86, 81, 79, 80, 76, 74, 75, kpis.riskScore];
  const segmentRisk = [
    { segment: "DMZ", score: 84, assets: 3 },
    { segment: "Corp", score: 68, assets: 3 },
    { segment: "Core", score: 57, assets: 2 },
    { segment: "Restricted", score: 41, assets: 2 },
  ];

  const patches = patchesQuery.data?.results || [];
  const nodes = topology.data?.nodes || [];
  const edges = topology.data?.edges || [];

  const nodeById = (id: string) => nodes.find((n: any) => n.node_id === id) || { label: id };
  return (
    <Shell>
      <div className="space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="eyebrow">Dashboard · {roleLabel(role)}</p>
            <h2 className="mt-1 text-2xl font-semibold">Security posture overview</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Portfolio-level risk, exposure, and remediation signals.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              to="/simulation"
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
            >
              Review simulation
            </Link>
            <Link
              to="/patches"
              className="rounded-md border border-hairline bg-card px-4 py-2 text-sm font-medium text-foreground hover:bg-pearl"
            >
              Patch priorities
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
          <Metric
            label="Reachable attack paths"
            value={String(kpis.exposedPaths)}
            sub={`${kpis.criticalPaths} reach restricted data`}
          />
          <Metric
            label="Mean path length"
            value={kpis.meanPathLength.toFixed(1)}
            sub="hops to crown jewels"
            tone="primary"
          />
          <Metric
            label="Telemetry coverage"
            value={`${kpis.coverage}%`}
            sub="of assets reporting"
            tone="success"
          />
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

        <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.7fr)_minmax(260px,0.8fr)]">
          <Panel title="Latest simulated blast radius">
            <div className="chart-frame ml-0">
              <MiniMap
                nodes={nodes}
                edges={edges}
                compromised={["web_server_1", "vpn_gateway", "customer_db"]}
                height={300}
              />
            </div>
          </Panel>
          <Panel title="Attack path trend">
            <div className="p-5">
              <div className="flex items-end justify-between">
                <div>
                  <p className="eyebrow">10-week view</p>
                  <p className="mt-1 text-2xl font-semibold tabular">{kpis.riskScore}%</p>
                </div>
                <span className="rounded-full bg-primary/10 px-2 py-1 text-[11px] text-primary">
                  current
                </span>
              </div>
              <div className="mt-5 rounded-md bg-pearl p-3">
                <Sparkline data={riskTrend} />
              </div>
              <div className="mt-3 flex justify-between text-[11px] text-muted-foreground">
                <span>W-10</span>
                <span>Now</span>
              </div>
              <p className="mt-4 text-xs text-muted-foreground">
                Attack success trend from the latest world-model evaluations.
              </p>
            </div>
          </Panel>
        </div>

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
              {patches.slice(0, 3).map((p: any, i: number) => (
                <tr key={p.patch_id || p.cve_id || i}>
                  <td className="px-5 py-3 tabular">{i + 1}</td>
                  <td className="px-5 py-3">{nodeById(p.node_id).label || p.node_id}</td>
                  <td className="px-5 py-3 font-mono text-[12px]">{p.cve_id || p.cve}</td>
                  <td className="px-5 py-3 text-right tabular">
                    {p.risk_reduction_pp ? (p.risk_reduction_pp * 100).toFixed(1) : p.riskReduction}
                    %
                  </td>
                  <td className="px-5 py-3 text-right tabular">{p.roi_score || p.roi || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      </div>
    </Shell>
  );
}
