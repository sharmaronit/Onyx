import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { Locked, Metric, Panel, Shell } from "@/components/soc/Shell";
import { agents, kpis, makeEvent, type EventRow } from "@/lib/soc-data";
import { can, useRole } from "@/lib/rbac";

export const Route = createFileRoute("/telemetry")({
  head: () => ({
    meta: [
      { title: "Telemetry & Ingestion — Sentinel Graph" },
      {
        name: "description",
        content:
          "Live SOC event feed, sensor heartbeat grid and ingestion health metrics for endpoint, network and firewall telemetry.",
      },
      { property: "og:title", content: "Telemetry & Ingestion — Sentinel Graph" },
      {
        property: "og:description",
        content: "Live event feed, sensor heartbeats and ingestion health for endpoint and network telemetry.",
      },
    ],
  }),
  component: Telemetry,
});

const sevClass: Record<EventRow["severity"], string> = {
  info: "text-tile-muted",
  notice: "text-primary-on-dark",
  warn: "text-warning",
  critical: "text-destructive",
};

function Telemetry() {
  const { role } = useRole();
  const allowed = can.viewTelemetry(role);
  const [rows, setRows] = useState<EventRow[]>(() => Array.from({ length: 18 }, () => makeEvent()));
  const [live, setLive] = useState(true);
  const [ingested, setIngested] = useState(kpis.eventsToday);
  const feed = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!live || !allowed) return;
    const t = setInterval(() => {
      setRows((r) => [...r.slice(-120), makeEvent()]);
      setIngested((n) => n + Math.floor(40 + Math.random() * 260));
    }, 900);
    return () => clearInterval(t);
  }, [live, allowed]);

  useEffect(() => {
    if (feed.current) feed.current.scrollTop = feed.current.scrollHeight;
  }, [rows]);

  if (!allowed) {
    return (
      <Shell>
        <Locked>
          Raw telemetry is available to SOC Analyst and Security Architect roles. Executives see aggregated
          coverage metrics on the overview page.
        </Locked>
      </Shell>
    );
  }

  return (
    <Shell>
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-4">
          <Metric label="Events ingested today" value={ingested.toLocaleString("en-US")} sub="all sources" />
          <Metric label="Blocked attacks" value={kpis.blockedAttacks.toLocaleString("en-US")} sub="perimeter + endpoint" tone="success" />
          <Metric label="Sensors online" value={`${agents.filter((a) => a.status === "healthy").length}/${agents.length}`} sub="1 degraded · 1 offline" tone="warning" />
          <Metric label="Ingest rate" value={`${agents.reduce((a, b) => a + b.eps, 0).toLocaleString("en-US")}/s`} sub="events per second" tone="primary" />
        </div>

        <Panel
          title="Live event feed"
          action={
            <button
              onClick={() => setLive((l) => !l)}
              className="rounded-md bg-foreground px-4 py-1.5 text-[13px] text-primary-foreground"
            >
              {live ? "Pause stream" : "Resume stream"}
            </button>
          }
        >
          <div ref={feed} className="scroll-slim h-[380px] overflow-y-auto bg-tile-3 p-4 font-mono text-[12px]">
            {rows.map((e) => (
              <div key={e.id} className="flex gap-3 py-0.5 leading-relaxed">
                <span className="w-24 shrink-0 text-tile-muted">{e.ts}</span>
                <span className="w-20 shrink-0 text-tile-foreground">{e.host}</span>
                <span className="w-28 shrink-0 text-tile-muted">{e.source}</span>
                <span className={`min-w-0 flex-1 ${sevClass[e.severity]}`}>{e.message}</span>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Agent status grid">
          <div className="grid gap-4 p-5 sm:grid-cols-2 xl:grid-cols-3">
            {agents.map((a) => (
              <div key={a.id} className="rounded-lg border border-hairline p-4">
                <div className="flex items-start justify-between gap-3">
                  <p className="text-[13px] font-semibold leading-snug">{a.name}</p>
                  <span
                    className={`mt-1 h-2 w-2 shrink-0 rounded-full ${
                      a.status === "healthy"
                        ? "bg-success"
                        : a.status === "degraded"
                          ? "bg-warning"
                          : "bg-destructive"
                    }`}
                  />
                </div>
                <dl className="mt-3 space-y-1 text-[12px] text-muted-foreground">
                  <div className="flex justify-between">
                    <dt>Last heartbeat</dt>
                    <dd className="tabular">{a.heartbeat}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt>Throughput</dt>
                    <dd className="tabular">{a.eps} ev/s</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt>Status</dt>
                    <dd>{a.status}</dd>
                  </div>
                </dl>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </Shell>
  );
}
