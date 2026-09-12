import { createFileRoute } from "@tanstack/react-router";
import { Fragment, useState } from "react";
import { Locked, Metric, Panel, Shell } from "@/components/soc/Shell";
import { nodeById, patches } from "@/lib/soc-data";
import { can, useRole } from "@/lib/rbac";

export const Route = createFileRoute("/patches")({
  head: () => ({
    meta: [
      { title: "Patch Optimization & ROI — Sentinel Graph" },
      {
        name: "description",
        content:
          "Prioritized patch plan ranked by simulated risk reduction, remediation effort and ROI score, with explainability for every recommendation.",
      },
      { property: "og:title", content: "Patch Optimization & ROI — Sentinel Graph" },
      {
        property: "og:description",
        content: "Patch plan ranked by simulated risk reduction, effort and ROI, with per-row explainability.",
      },
    ],
  }),
  component: Patches,
});

function Patches() {
  const { role } = useRole();
  const allowed = can.editCostModel(role);
  const [open, setOpen] = useState<string | null>("CVE-2024-21412");
  const [modal, setModal] = useState(false);
  const [model, setModal2] = useState({ laptop: 2, server: 4, db: 8, criticalMultiplier: 1.8 });

  const totalReduction = patches.reduce((a, p) => a + p.riskReduction, 0);
  const totalEffort = patches.reduce((a, p) => a + p.effort, 0);

  return (
    <Shell>
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-4">
          <Metric label="Recommended patches" value={String(patches.length)} sub="ranked by ROI" />
          <Metric label="Cumulative risk reduction" value={`${totalReduction.toFixed(1)}%`} sub="if all applied" tone="success" />
          <Metric label="Total effort" value={`${totalEffort}h`} sub="engineering hours" tone="primary" />
          <Metric label="Quick wins" value="2" sub="≤3h, ≥20% reduction" tone="warning" />
        </div>

        <Panel
          title="Prioritized action table"
          action={
            <button
              disabled={!allowed}
              onClick={() => setModal(true)}
              className="rounded-md bg-foreground px-4 py-1.5 text-[13px] text-primary-foreground disabled:bg-chip disabled:text-muted-foreground"
            >
              Cost model settings
            </button>
          }
        >
          {!allowed && (
            <div className="border-b border-hairline p-5">
              <Locked>
                Cost model parameters — effort hours per node type and critical-asset multipliers — can only
                be adjusted by the Security Architect role.
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
                {patches.map((p) => (
                  <Fragment key={p.cve}>
                    <tr
                      onClick={() => setOpen(open === p.cve ? null : p.cve)}
                      className={`cursor-pointer transition-colors hover:bg-pearl ${
                        open === p.cve ? "bg-pearl" : ""
                      }`}
                    >
                      <td className="px-5 py-3 tabular">{p.rank}</td>
                      <td className="px-5 py-3">{nodeById(p.node).label}</td>
                      <td className="px-5 py-3 font-mono text-[12px]">{p.cve}</td>
                      <td className="px-5 py-3 text-right tabular">{p.cvss.toFixed(1)}</td>
                      <td className="px-5 py-3 text-right tabular">−{p.riskReduction}%</td>
                      <td className="px-5 py-3 text-right tabular">{p.effort}</td>
                      <td className="px-5 py-3 text-right tabular font-semibold">{p.roi}</td>
                    </tr>
                    {open === p.cve && (
                      <tr>
                        <td colSpan={7} className="bg-card px-5 pb-5 pt-1">
                          <div className="rounded-lg bg-pearl p-5">
                            <p className="eyebrow">Why this is ranked #{p.rank}</p>
                            <ul className="mt-3 space-y-2 text-[15px]">
                              {p.reasons.map((r) => (
                                <li key={r} className="flex gap-3">
                                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                                  <span>{r}</span>
                                </li>
                              ))}
                            </ul>
                            <p className="mt-4 text-[13px] text-muted-foreground">
                              Effort derived from cost model: {nodeById(p.node).kind} baseline
                              {nodeById(p.node).critical ? `, ×${model.criticalMultiplier} critical multiplier` : ""}.
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
                  ["laptop", "Laptop / endpoint effort (h)"],
                  ["server", "Server effort (h)"],
                  ["db", "Database effort (h)"],
                  ["criticalMultiplier", "Critical asset multiplier"],
                ] as const
              ).map(([key, label]) => (
                <label key={key} className="block">
                  <span className="text-[13px]">{label}</span>
                  <input
                    type="number"
                    step={key === "criticalMultiplier" ? 0.1 : 1}
                    value={model[key]}
                    onChange={(e) => setModal2({ ...model, [key]: Number(e.target.value) })}
                    className="mt-1.5 h-11 w-full rounded-full border border-input bg-card px-5 text-[15px] outline-none focus:border-primary-focus"
                  />
                </label>
              ))}
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setModal(false)}
                className="rounded-full px-5 py-2 text-[15px] text-primary"
              >
                Cancel
              </button>
              <button
                onClick={() => setModal(false)}
                className="rounded-full bg-primary px-6 py-2 text-[15px] text-primary-foreground"
              >
                Save model
              </button>
            </div>
          </div>
        </div>
      )}
    </Shell>
  );
}
