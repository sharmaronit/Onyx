import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Metric, Panel, Shell } from "@/components/soc/Shell";
import { MiniMap } from "@/components/soc/MiniMap";
import { edges, nodeById, nodes } from "@/lib/soc-data";

export const Route = createFileRoute("/topology")({
  head: () => ({
    meta: [
      { title: "Asset Topology — Sentinel Graph" },
      {
        name: "description",
        content:
          "Segment-aware asset inventory with reachability graph, exposure scores and crown-jewel classification.",
      },
      { property: "og:title", content: "Asset Topology — Sentinel Graph" },
      {
        property: "og:description",
        content: "Segment-aware asset inventory with reachability graph and exposure scores.",
      },
    ],
  }),
  component: Topology,
});

function Topology() {
  const [selected, setSelected] = useState<string>("app-02");
  const node = nodeById(selected);
  const neighbours = edges
    .filter(([a, b]) => a === selected || b === selected)
    .map(([a, b]) => (a === selected ? b : a));

  return (
    <Shell>
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-4">
          <Metric label="Monitored assets" value={String(nodes.length)} sub="4 network segments" />
          <Metric label="Crown jewels" value={String(nodes.filter((n) => n.critical).length)} sub="critical classification" tone="primary" />
          <Metric label="Graph edges" value={String(edges.length)} sub="observed reachability" />
          <Metric label="Highest exposure" value="88" sub="Web Frontend 01" tone="destructive" />
        </div>

        <div className="grid gap-6 xl:grid-cols-3">
          <Panel title="Reachability graph" className="xl:col-span-2">
            <MiniMap active={selected} onSelect={setSelected} height={380} />
          </Panel>
          <Panel title="Asset detail">
            <div className="space-y-4 p-5">
              <div>
                <p className="eyebrow">{node.segment} segment</p>
                <h3 className="mt-1 font-display text-[21px] font-semibold">{node.label}</h3>
                <p className="mt-1 font-mono text-[12px] text-muted-foreground">{node.ip}</p>
              </div>
              <dl className="space-y-2.5 text-[13px]">
                <div className="flex justify-between border-b border-hairline pb-2">
                  <dt className="text-muted-foreground">Type</dt>
                  <dd>{node.kind}</dd>
                </div>
                <div className="flex justify-between border-b border-hairline pb-2">
                  <dt className="text-muted-foreground">Exposure score</dt>
                  <dd className="tabular">{node.exposure}</dd>
                </div>
                <div className="flex justify-between border-b border-hairline pb-2">
                  <dt className="text-muted-foreground">Classification</dt>
                  <dd>{node.critical ? "Crown jewel" : "Standard"}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Adjacent nodes</dt>
                  <dd className="tabular">{neighbours.length}</dd>
                </div>
              </dl>
              <div className="flex flex-wrap gap-2">
                {neighbours.map((n) => (
                  <button
                    key={n}
                    onClick={() => setSelected(n)}
                    className="rounded-full bg-pearl px-3 py-1.5 text-[12px] text-secondary-foreground hover:text-primary"
                  >
                    {nodeById(n).label}
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
                  <th className="px-5 py-2.5 font-normal">Address</th>
                  <th className="px-5 py-2.5 font-normal">Type</th>
                  <th className="px-5 py-2.5 font-normal">Segment</th>
                  <th className="px-5 py-2.5 font-normal">Class</th>
                  <th className="px-5 py-2.5 font-normal text-right">Exposure</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {nodes.map((n) => (
                  <tr
                    key={n.id}
                    onClick={() => setSelected(n.id)}
                    className={`cursor-pointer transition-colors hover:bg-pearl ${
                      selected === n.id ? "bg-pearl" : ""
                    }`}
                  >
                    <td className="px-5 py-3">{n.label}</td>
                    <td className="px-5 py-3 font-mono text-[12px] text-muted-foreground">{n.ip}</td>
                    <td className="px-5 py-3">{n.kind}</td>
                    <td className="px-5 py-3">{n.segment}</td>
                    <td className="px-5 py-3">{n.critical ? "Crown jewel" : "Standard"}</td>
                    <td className="px-5 py-3 text-right tabular">{n.exposure}</td>
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
