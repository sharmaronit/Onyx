import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { Locked, Metric, Panel, Shell } from "@/components/soc/Shell";
import { MiniMap } from "@/components/soc/MiniMap";
import { episode, nodeById } from "@/lib/soc-data";
import { can, useRole } from "@/lib/rbac";

export const Route = createFileRoute("/simulation")({
  head: () => ({
    meta: [
      { title: "Attack Simulation Replay — Sentinel Graph" },
      {
        name: "description",
        content:
          "Step frame-by-frame through a simulated breach episode with MITRE technique mapping and live compromised-node mini-map.",
      },
      { property: "og:title", content: "Attack Simulation Replay — Sentinel Graph" },
      {
        property: "og:description",
        content: "Frame-by-frame breach episode replay with MITRE mapping and compromised-node mini-map.",
      },
    ],
  }),
  component: Simulation,
});

function Simulation() {
  const { role } = useRole();
  const allowed = can.runSimulation(role);
  const [step, setStep] = useState(1);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    if (!playing) return;
    const t = setInterval(() => {
      setStep((s) => {
        if (s >= episode.length) {
          setPlaying(false);
          return s;
        }
        return s + 1;
      });
    }, 1200);
    return () => clearInterval(t);
  }, [playing]);

  const frame = episode[step - 1] ?? episode[0]!;
  const compromised = useMemo(() => episode.slice(0, step).map((f) => f.node), [step]);
  const detectedCount = episode.slice(0, step).filter((f) => f.detected).length;

  return (
    <Shell>
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-4">
          <Metric label="Episode" value="EP-4417" sub="Ransomware precursor, 8 frames" />
          <Metric label="Frames elapsed" value={`${step}/${episode.length}`} sub={frame.time} tone="primary" />
          <Metric label="Nodes compromised" value={String(new Set(compromised).size)} sub="of 10 monitored" tone="destructive" />
          <Metric
            label="Detection coverage"
            value={`${Math.round((detectedCount / step) * 100)}%`}
            sub={`${detectedCount} of ${step} frames alerted`}
            tone="success"
          />
        </div>

        <Panel
          title="Blast radius at current frame"
          action={<span className="text-[12px] text-muted-foreground tabular">{frame.time}</span>}
        >
          <MiniMap compromised={compromised} active={frame.node} height={380} />

          <div className="border-t border-hairline p-5">
            <div className="flex flex-wrap items-center gap-3">
              <button
                disabled={!allowed}
                onClick={() => setPlaying((p) => !p)}
                className="rounded-full bg-primary px-5 py-2 text-[14px] text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:bg-chip disabled:text-muted-foreground"
              >
                {playing ? "Pause simulation" : "Run simulation"}
              </button>
              <button
                disabled={!allowed || step <= 1}
                onClick={() => setStep((s) => Math.max(1, s - 1))
                }
                className="rounded-md bg-foreground px-4 py-2 text-[13px] text-primary-foreground disabled:bg-chip disabled:text-muted-foreground"
              >
                ‹ Step back
              </button>
              <button
                disabled={!allowed || step >= episode.length}
                onClick={() => setStep((s) => Math.min(episode.length, s + 1))}
                className="rounded-md bg-foreground px-4 py-2 text-[13px] text-primary-foreground disabled:bg-chip disabled:text-muted-foreground"
              >
                Step forward ›
              </button>
              <button
                disabled={!allowed}
                onClick={() => {
                  setPlaying(false);
                  setStep(1);
                }}
                className="rounded-md bg-pearl px-4 py-2 text-[13px] text-secondary-foreground disabled:text-muted-foreground"
              >
                Reset
              </button>
            </div>

            <input
              type="range"
              min={1}
              max={episode.length}
              value={step}
              disabled={!allowed}
              onChange={(e) => setStep(Number(e.target.value))}
              className="mt-5 w-full accent-primary disabled:opacity-40"
            />
            <div className="mt-2 flex justify-between text-[11px] text-muted-foreground tabular">
              {episode.map((f) => (
                <span key={f.step} className={f.step === step ? "text-primary" : ""}>
                  {f.time}
                </span>
              ))}
            </div>

            {!allowed && (
              <div className="mt-5">
                <Locked>
                  Running simulations is limited to Security Architect and SOC Analyst roles. Executives
                  see the completed replay in read-only mode.
                </Locked>
              </div>
            )}
          </div>
        </Panel>

        <div className="grid gap-6 xl:grid-cols-3">
          <Panel title="Current frame" className="xl:col-span-1">
            <div className="space-y-3 p-5">
              <p className="eyebrow">{frame.tactic}</p>
              <h3 className="font-display text-[19px] font-semibold leading-snug">{frame.technique}</h3>
              <p className="text-[13px] text-muted-foreground">{nodeById(frame.node).label}</p>
              <p className="text-[15px] leading-relaxed">{frame.detail}</p>
              <p className={`text-[13px] ${frame.detected ? "text-success" : "text-destructive"}`}>
                {frame.detected ? "Detected by existing controls" : "No detection — visibility gap"}
              </p>
            </div>
          </Panel>

          <Panel title="Episode timeline" className="xl:col-span-2">
            <ol className="divide-y divide-hairline">
              {episode.map((f) => (
                <li key={f.step}>
                  <button
                    onClick={() => allowed && setStep(f.step)}
                    className={`flex w-full items-start gap-4 px-5 py-3 text-left transition-colors hover:bg-pearl ${
                      f.step === step ? "bg-pearl" : ""
                    } ${f.step > step ? "opacity-45" : ""}`}
                  >
                    <span className="w-16 shrink-0 font-mono text-[12px] text-muted-foreground">{f.time}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-[13px]">{f.technique}</span>
                      <span className="block text-[12px] text-muted-foreground">
                        {f.tactic} · {nodeById(f.node).label}
                      </span>
                    </span>
                    <span
                      className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] ${
                        f.detected ? "bg-pearl text-success" : "bg-pearl text-destructive"
                      }`}
                    >
                      {f.detected ? "alerted" : "missed"}
                    </span>
                  </button>
                </li>
              ))}
            </ol>
          </Panel>
        </div>
      </div>
    </Shell>
  );
}
