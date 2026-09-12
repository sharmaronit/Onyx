import { createFileRoute } from "@tanstack/react-router";
import { Fragment, useEffect, useState } from "react";
import { Locked, Metric, Panel, Shell } from "@/components/soc/Shell";
import {
  useCostModel,
  usePatchResults,
  usePatchOptimize,
  useTopology,
  useRealityPatchRoi,
  useUpdateCostModel,
} from "@/hooks/use-api";
import type { CostModel } from "@/lib/api";
import { can, useRole } from "@/lib/rbac";
import { useAppMode } from "@/lib/app-mode";

export const Route = createFileRoute("/patches")({
  head: () => ({
    meta: [
      { title: "Patch Optimization & ROI — Onyx" },
      {
        name: "description",
        content:
          "Prioritized patch plan ranked by simulated risk reduction, remediation effort and ROI score, with explainability for every recommendation.",
      },
      { property: "og:title", content: "Patch Optimization & ROI — Onyx" },
      {
        property: "og:description",
        content:
          "Patch plan ranked by simulated risk reduction, effort and ROI, with per-row explainability.",
      },
    ],
  }),
  component: Patches,
});

function Patches() {
  const { mode } = useAppMode();
  const { role } = useRole();
  const allowed = can.editCostModel(role);

  const topology = useTopology();
  const patchesQuery = usePatchResults();
  const optimizeMutation = usePatchOptimize();
  const realityRoi = useRealityPatchRoi();
  const costModel = useCostModel();
  const updateCostModel = useUpdateCostModel();

  const [open, setOpen] = useState<string | null>(null);
  const [modal, setModal] = useState(false);
  const [responseKey, setResponseKey] = useState("");
  const [model, setModel] = useState<
    Pick<CostModel, "node_type_effort_hours" | "critical_asset_multiplier">
  >({
    node_type_effort_hours: {
      server: 6,
      workstation: 2.5,
      router: 4.5,
      firewall: 5.5,
      database: 8,
      cloud: 3.5,
    },
    critical_asset_multiplier: 1.7,
  });
  useEffect(() => {
    if (costModel.data?.model)
      setModel({
        node_type_effort_hours: costModel.data.model.node_type_effort_hours,
        critical_asset_multiplier: costModel.data.model.critical_asset_multiplier,
      });
  }, [costModel.data]);

  if (mode === "reality") {
    if (realityRoi.isLoading)
      return (
        <Shell>
          <div className="p-8">Loading evidence-backed patch priorities…</div>
        </Shell>
      );
    if (realityRoi.error)
      return (
        <Shell>
          <Panel title="Patch priorities unavailable">
            <p className="p-5 text-sm text-destructive">{realityRoi.error.message}</p>
          </Panel>
        </Shell>
      );
    const live = realityRoi.data;
    if (!live?.ready)
      return (
        <Shell>
          <div className="space-y-6">
            <Panel title="Remediation readiness">
              <div className="p-5">
                <p className="text-sm text-muted-foreground">
                  Patch ROI decides which verified fixes should be scheduled first. It needs scanner
                  findings plus observed reachability to avoid ranking work against an incomplete
                  environment.
                </p>
                <div className="mt-5 grid gap-3 md:grid-cols-3">
                  <Metric
                    label="Patchable findings"
                    value={String(live?.readiness.patchable_findings ?? 0)}
                    sub="fix availability confirmed"
                    tone={(live?.readiness.patchable_findings ?? 0) > 0 ? "success" : "warning"}
                  />
                  <Metric
                    label="Critical remediation"
                    value={String(live?.readiness.critical_findings ?? 0)}
                    sub="CVSS 9.0 or higher"
                    tone={(live?.readiness.critical_findings ?? 0) > 0 ? "destructive" : "warning"}
                  />
                  <Metric
                    label="Prioritization inputs"
                    value={`${live?.readiness.relationships ?? 0}/${live?.readiness.findings ?? 0}`}
                    sub="links / findings"
                    tone={
                      (live?.readiness.relationships ?? 0) > 0 &&
                      (live?.readiness.findings ?? 0) > 0
                        ? "success"
                        : "warning"
                    }
                  />
                </div>
                <div className="mt-5 rounded-md bg-pearl p-4 text-sm">
                  <b>To unlock:</b> import source-attributed findings with fix availability and
                  collect observed network relationships. This page will then rank remediation
                  effort and ROI—not exposure routes.
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
              label="Recommended fixes"
              value={String(live.results.length)}
              sub="source-attributed findings"
            />
            <Metric
              label="Fixes available"
              value={String(live.results.filter((r: any) => r.fix_available).length)}
              sub="verified by scanner"
              tone="success"
            />
            <Metric
              label="Highest priority"
              value={`${Math.max(0, ...live.results.map((r: any) => r.priority_score))}/100`}
              sub="non-additive estimate"
              tone="primary"
            />
            <Metric
              label="Evidence status"
              value="Live"
              sub={live.provenance || "scanner findings"}
              tone="success"
            />
          </div>
          <Panel title="Evidence-backed patch priorities">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[850px] text-sm">
                <thead className="bg-pearl text-left text-muted-foreground">
                  <tr>
                    <th className="p-4">Asset</th>
                    <th className="p-4">Finding</th>
                    <th className="p-4">CVSS</th>
                    <th className="p-4">Fix</th>
                    <th className="p-4 text-right">Effort</th>
                    <th className="p-4 text-right">Priority / hour</th>
                  </tr>
                </thead>
                <tbody>
                  {live.results.map((r: any) => (
                    <tr key={`${r.node_id}-${r.cve_id}`} className="border-t border-hairline">
                      <td className="p-4">{r.hostname}</td>
                      <td className="p-4">
                        <b>{r.cve_id}</b>
                        <span className="block text-xs text-muted-foreground">{r.source}</span>
                      </td>
                      <td className="p-4">{r.cvss_score.toFixed(1)}</td>
                      <td className="p-4">{r.fix_available ? "Available" : "Validate"}</td>
                      <td className="p-4 text-right">{r.effort_hours}h</td>
                      <td className="p-4 text-right font-semibold">{r.priority_per_effort}</td>
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

  const patches = patchesQuery.data?.results || [];
  const nodes = topology.data?.nodes || [];
  const nodeById = (id: string) => nodes.find((n: any) => n.node_id === id) || { node_id: id };

  const strongestSingleImpact =
    Math.max(0, ...patches.map((p: any) => p.simulation_impact || 0)) * 100;
  const totalEffort = patches.reduce(
    (a: number, p: any) => a + (p.effort_hours || p.effort || 0),
    0,
  );

  return (
    <Shell>
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-4">
          <Metric label="Recommended patches" value={String(patches.length)} sub="ranked by ROI" />
          <Metric
            label="Top single-patch effect"
            value={`-${strongestSingleImpact.toFixed(1)}%`}
            sub="paired simulation estimate"
            tone="success"
          />
          <Metric
            label="Total effort"
            value={`${Math.round(totalEffort)}h`}
            sub="engineering hours"
            tone="primary"
          />
          <Metric
            label="Quick wins"
            value={String(
              patches.filter((p: any) => (p.effort_hours || p.effort || 99) <= 3).length,
            )}
            sub="low effort patches"
            tone="warning"
          />
        </div>

        <Panel
          title="Prioritized action table"
          action={
            <div className="flex gap-2">
              <button
                disabled={!allowed || optimizeMutation.isPending}
                onClick={() =>
                  optimizeMutation.mutate({
                    topology: "enterprise_20n",
                    n_baseline: 200,
                    n_eval_per_patch: 50,
                  })
                }
                className="rounded-md bg-primary px-4 py-1.5 text-[13px] text-primary-foreground disabled:bg-chip disabled:text-muted-foreground"
              >
                {optimizeMutation.isPending ? "Running..." : "Run optimization"}
              </button>
              <button
                disabled={!allowed}
                onClick={() => setModal(true)}
                className="rounded-md bg-foreground px-4 py-1.5 text-[13px] text-primary-foreground disabled:bg-chip disabled:text-muted-foreground"
              >
                Cost model
              </button>
            </div>
          }
        >
          {(optimizeMutation.error || updateCostModel.error) && (
            <div
              role="alert"
              className="border-b border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive"
            >
              {optimizeMutation.error?.message || updateCostModel.error?.message}
            </div>
          )}
          {!allowed && (
            <div className="border-b border-hairline p-5">
              <Locked>
                Cost model parameters — effort hours per node type and critical-asset multipliers —
                can only be adjusted by the Security Architect role.
              </Locked>
            </div>
          )}
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-[13px]">
              <thead className="bg-pearl text-left text-[12px] text-muted-foreground">
                <tr>
                  <th className="px-5 py-2.5 font-normal">Rank</th>
                  <th className="px-5 py-2.5 font-normal">Node</th>
                  <th className="px-5 py-2.5 font-normal">CVE ID</th>
                  <th className="px-5 py-2.5 font-normal text-right">CVSS</th>
                  <th className="px-5 py-2.5 font-normal text-right">Sim. impact</th>
                  <th className="px-5 py-2.5 font-normal text-right">Effort (h)</th>
                  <th className="px-5 py-2.5 font-normal text-right">ROI score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {patches.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-5 py-8 text-center text-sm text-muted-foreground">
                      Click "Run optimization" to generate patch recommendations.
                    </td>
                  </tr>
                )}
                {patches.map((p: any, i: number) => (
                  <Fragment key={p.patch_id || p.cve_id || i}>
                    <tr
                      onClick={() => setOpen(open === p.cve_id ? null : p.cve_id)}
                      className={`cursor-pointer transition-colors hover:bg-pearl ${
                        open === p.cve_id ? "bg-pearl" : ""
                      }`}
                    >
                      <td className="px-5 py-3 tabular">{i + 1}</td>
                      <td className="px-5 py-3">{nodeById(p.node_id).label || p.node_id}</td>
                      <td className="px-5 py-3 font-mono text-[12px]">{p.cve_id}</td>
                      <td className="px-5 py-3 text-right tabular">
                        {p.cvss_score?.toFixed(1) ?? "—"}
                      </td>
                      <td className="px-5 py-3 text-right tabular">
                        −{p.simulation_impact ? (p.simulation_impact * 100).toFixed(1) : "0.0"}%
                      </td>
                      <td className="px-5 py-3 text-right tabular">{p.effort_hours ?? "—"}</td>
                      <td className="px-5 py-3 text-right tabular font-semibold">
                        {p.roi_score ?? p.simulation_rank ?? "—"}
                      </td>
                    </tr>
                    {open === p.cve_id && (
                      <tr>
                        <td colSpan={7} className="bg-card px-5 pb-5 pt-1">
                          <div className="rounded-lg bg-pearl p-5">
                            <p className="eyebrow">Why this is ranked #{i + 1}</p>
                            <ul className="mt-3 space-y-2 text-[15px]">
                              {[
                                p.description || `CVE ${p.cve_id} on ${p.node_id}`,
                                `CVSS score: ${p.cvss_score?.toFixed(1) ?? "?"} — ${p.cvss_severity ?? "Unknown severity"}`,
                                `Simulated risk reduction: ${p.simulation_impact ? (p.simulation_impact * 100).toFixed(1) : "0.0"}%`,
                              ].map((r: string) => (
                                <li key={r} className="flex gap-3">
                                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                                  <span>{r}</span>
                                </li>
                              ))}
                            </ul>
                            <p className="mt-4 text-[13px] text-muted-foreground">
                              Node type: {p.node_type}. Is critical asset:{" "}
                              {p.is_critical_asset ? "Yes" : "No"}.
                            </p>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>

      {modal && allowed && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-void/40 p-6">
          <div className="w-full max-w-md rounded-2xl bg-card p-6 shadow-product">
            <h3 className="font-display text-[21px] font-semibold">Cost model</h3>
            <p className="mt-1 text-[13px] text-muted-foreground">
              Effort baselines feed the ROI score for every recommendation.
            </p>
            <div className="mt-5 space-y-4">
              {(
                [
                  ["workstation", "Workstation effort (h)"],
                  ["server", "Server effort (h)"],
                  ["database", "Database effort (h)"],
                  ["router", "Router effort (h)"],
                  ["firewall", "Firewall effort (h)"],
                  ["cloud", "Cloud effort (h)"],
                ] as const
              ).map(([key, label]) => (
                <label key={key} className="block">
                  <span className="text-[13px]">{label}</span>
                  <input
                    type="number"
                    min={0.1}
                    step={0.1}
                    value={model.node_type_effort_hours[key]}
                    onChange={(e) =>
                      setModel({
                        ...model,
                        node_type_effort_hours: {
                          ...model.node_type_effort_hours,
                          [key]: Number(e.target.value),
                        },
                      })
                    }
                    className="mt-1.5 h-11 w-full rounded-full border border-input bg-card px-5 text-[15px] outline-none focus:border-primary-focus"
                  />
                </label>
              ))}
              <label className="block">
                <span className="text-[13px]">Critical asset multiplier</span>
                <input
                  type="number"
                  min={0.1}
                  max={10}
                  step={0.1}
                  value={model.critical_asset_multiplier}
                  onChange={(e) =>
                    setModel({ ...model, critical_asset_multiplier: Number(e.target.value) })
                  }
                  className="mt-1.5 h-11 w-full rounded-full border border-input bg-card px-5 text-[15px] outline-none focus:border-primary-focus"
                />
              </label>
              <label className="block">
                <span className="text-[13px]">Response API key</span>
                <input
                  type="password"
                  autoComplete="off"
                  value={responseKey}
                  onChange={(e) => setResponseKey(e.target.value)}
                  placeholder="Required when remote authorization is configured"
                  className="mt-1.5 h-11 w-full rounded-full border border-input bg-card px-5 text-[15px] outline-none focus:border-primary-focus"
                />
              </label>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setModal(false)}
                className="rounded-full px-5 py-2 text-[15px] text-primary"
              >
                Cancel
              </button>
              <button
                onClick={() =>
                  updateCostModel.mutate(
                    { model, responseKey },
                    { onSuccess: () => setModal(false) },
                  )
                }
                disabled={updateCostModel.isPending}
                className="rounded-full bg-primary px-6 py-2 text-[15px] text-primary-foreground"
              >
                {updateCostModel.isPending ? "Saving…" : "Save model"}
              </button>
            </div>
          </div>
        </div>
      )}
    </Shell>
  );
}
