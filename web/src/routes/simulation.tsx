import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { Locked, Metric, Panel, Shell } from "@/components/soc/Shell";
import { MiniMap } from "@/components/soc/MiniMap";
import { useReplayLatest, useSavedSimulation, useSavedSimulations, useSimulation, useTopologies, useTopology } from "@/hooks/use-api";
import type { DataSource, ReplayStep } from "@/lib/api";
import { can, useRole } from "@/lib/rbac";

export const Route = createFileRoute("/simulation")({
  head: () => ({
    meta: [
      { title: "Attack Simulation Replay — Onyx" },
      {
        name: "description",
        content:
          "Replay the backend's most common simulated attack path using run and topology data.",
      },
    ],
  }),
  component: Simulation,
});

const DATA_SOURCE_LABELS: Record<DataSource, string> = {
  simulation: "Simulation",
  telemetry: "Telemetry",
  hybrid: "Hybrid",
};

function percent(value: number | undefined) {
  return `${((value ?? 0) * 100).toFixed(1)}%`;
}

function Simulation() {
  const { role } = useRole();
  const allowedToRun = can.runSimulation(role);
  const [topologyKey, setTopologyKey] = useState("enterprise_20n");
  const [episodes, setEpisodes] = useState(100);
  const [seed, setSeed] = useState(42);
  const [step, setStep] = useState(1);
  const [playing, setPlaying] = useState(false);
  const [view, setView] = useState<"run" | "saved">("run");
  const [selectedSavedId, setSelectedSavedId] = useState<string | null>(null);
  const [configSaved, setConfigSaved] = useState(false);
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [mapMode, setMapMode] = useState<"path" | "topology">("path");

  const topologies = useTopologies();
  const topology = useTopology(topologyKey);
  const replayQuery = useReplayLatest(topologyKey);
  const simMutation = useSimulation();
  const savedRuns = useSavedSimulations();
  const savedRun = useSavedSimulation(selectedSavedId);
  const replay = savedRun.data?.replay ?? replayQuery.data?.replay ?? null;
  const selectedRun = savedRuns.data?.runs.find((run) => run.simulation_id === selectedSavedId);
  const episode = useMemo<ReplayStep[]>(() => replay?.steps ?? [], [replay]);
  // The replay always visualizes the frozen world-model topology, never the
  // customer live asset map. This keeps a simulation safe and reproducible.
  const nodes = topology.data?.nodes ?? [];
  const edges = topology.data?.edges ?? [];
  const frame = episode.length ? episode[Math.min(step - 1, episode.length - 1)] : null;
  const traversedNodes = useMemo(
    () => episode.slice(0, step).map((item) => item.node_id),
    [episode, step],
  );
  const pathNodeIds = useMemo(() => Array.from(new Set(episode.map((item) => item.node_id))), [episode]);
  const mapNodes = useMemo(() => {
    if (mapMode === "topology" || pathNodeIds.length === 0) return nodes;
    return pathNodeIds.map((nodeId, index) => {
      const node = nodes.find((item) => item.node_id === nodeId);
      return { ...(node ?? { node_id: nodeId }), x: pathNodeIds.length === 1 ? 50 : 10 + (80 * index) / (pathNodeIds.length - 1), y: 50 };
    });
  }, [mapMode, nodes, pathNodeIds]);
  const mapEdges = useMemo(() => mapMode === "topology" ? edges : pathNodeIds.slice(1).map((target, index) => ({ source: pathNodeIds[index], target, connection_type: "replay" })), [mapMode, edges, pathNodeIds]);
  const validationError = episodes < 100 || episodes > 10000 ? "Episodes must be between 100 and 10,000." : seed < 0 ? "Seed cannot be negative." : null;
  const estimatedSeconds = Math.max(2, Math.ceil(episodes / 40));

  useEffect(() => {
    setPlaying(false);
    setStep(1);
  }, [topologyKey]);

  useEffect(() => {
    if (!playing || episode.length === 0) return;
    const timer = window.setInterval(() => {
      setStep((current) => {
        if (current >= episode.length) {
          setPlaying(false);
          return current;
        }
        return current + 1;
      });
    }, 1200);
    return () => window.clearInterval(timer);
  }, [playing, episode.length]);

  const runSimulation = () => {
    if (validationError) return;
    setPlaying(false);
    simMutation.mutate(
      { topology: topologyKey, data_source: "simulation", n_episodes: episodes, seed },
      { onSuccess: () => { setSelectedSavedId(null); setView("run"); setStep(1); } },
    );
  };
  const saveConfiguration = () => {
    window.localStorage.setItem("onyx-simulation-config", JSON.stringify({ topologyKey, episodes, seed }));
    setConfigSaved(true);
    setConfigModalOpen(false);
    window.setTimeout(() => setConfigSaved(false), 1800);
  };

  const loadError = topology.error || replayQuery.error || topologies.error;
  if (topology.isLoading || replayQuery.isLoading || topologies.isLoading) {
    return (
      <Shell>
        <div className="p-8">Loading simulation data from the backend…</div>
      </Shell>
    );
  }

  return (
    <Shell>
      <div className="space-y-6">
        <div className="flex items-center justify-between gap-3 border-b border-hairline pb-3">
          <div className="flex gap-2">
          <button onClick={() => setView("run")} className={`border-b-2 px-4 py-2 text-sm font-semibold transition-colors hover:text-foreground ${view === "run" ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:border-primary"}`}>Run simulation</button>
          <button onClick={() => setView("saved")} className={`border-b-2 px-4 py-2 text-sm font-semibold transition-colors hover:text-foreground ${view === "saved" ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:border-primary"}`}>Saved</button>
          </div>
          <button type="button" onClick={() => setConfigModalOpen(true)} className="rounded-md border border-hairline bg-card px-3 py-2 text-xs font-semibold text-foreground transition-colors hover:bg-pearl">Save world-model</button>
        </div>
        {loadError && (
          <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
            Backend data could not be loaded: {loadError.message}
          </div>
        )}
        {simMutation.error && (
          <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
            Simulation failed: {simMutation.error.message}
          </div>
        )}

        <Panel title="Run configuration" action={<span className="text-[11px] text-muted-foreground">World-model only</span>}>
          <div className="grid items-start gap-4 p-5 md:grid-cols-[1.1fr_1.1fr_1fr_1fr_auto]">
            <label className="block text-[12px] text-muted-foreground">
              Topology
              <select
                value={topologyKey}
                onChange={(event) => setTopologyKey(event.target.value)}
                className="mt-1 block w-full rounded-md border border-hairline bg-card px-3 py-2 text-[13px] text-foreground"
              >
                {Object.keys(topologies.data?.topologies ?? {}).map((key) => (
                  <option key={key} value={key}>
                    {key}
                  </option>
                ))}
              </select>
            </label>
            <div className="block text-[12px] text-muted-foreground">
              Execution environment
              <div title="No packets or endpoint actions are sent." className="mt-1 flex min-h-10 items-center rounded-md border border-hairline bg-pearl px-3 py-2 text-[13px] font-medium text-foreground">
                World model simulation
              </div>
              <span className="mt-1 block text-[10px]">No packets or endpoint actions are sent.</span>
            </div>
            <label className="block text-[12px] text-muted-foreground">
              Evaluation episodes
              <input
                type="number"
                min={100}
                max={10000}
                value={episodes}
                onChange={(event) =>
                  setEpisodes(Math.max(100, Math.min(10000, Number(event.target.value) || 100)))
                }
                className="mt-1 block w-full rounded-md border border-hairline bg-card px-3 py-2 text-[13px] text-foreground"
              />
            </label>
            <label className="block text-[12px] text-muted-foreground">
              Reproducibility seed
              <input
                type="number"
                min={0}
                value={seed}
                onChange={(event) => setSeed(Math.max(0, Number(event.target.value) || 0))}
                className="mt-1 block w-full rounded-md border border-hairline bg-card px-3 py-2 text-[13px] text-foreground"
              />
            </label>
            <div className="flex h-full flex-col items-stretch justify-end gap-2 pt-5">
              <button
                disabled={!allowedToRun || simMutation.isPending || !!loadError || !!validationError}
                onClick={runSimulation}
                className="min-w-[190px] rounded-md bg-primary px-5 py-2.5 text-[13px] font-semibold text-primary-foreground shadow-sm transition-all hover:-translate-y-px hover:shadow-md disabled:bg-chip disabled:text-muted-foreground disabled:shadow-none"
              >
                {simMutation.isPending ? "Running on backend…" : "Run new simulation"}
              </button>
              <button type="button" onClick={() => setConfigModalOpen(true)} className="text-[11px] font-medium text-muted-foreground transition-colors hover:text-foreground">{configSaved ? "Configuration saved" : "Save configuration"}</button>
            </div>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-hairline px-5 py-3 text-[11px] text-muted-foreground">
            <span>Estimated runtime: <strong className="text-foreground">~{estimatedSeconds}s</strong></span>
            {validationError && <span className="text-destructive">{validationError}</span>}
            {simMutation.isPending && <span className="font-medium text-primary">Simulation in progress…</span>}
          </div>
          {!allowedToRun && (
            <div className="border-t border-hairline p-5">
              <Locked>
                Running simulations is limited to Security Architect and SOC Analyst roles.
              </Locked>
            </div>
          )}
        </Panel>

        {view === "saved" && (
          <Panel title="Saved world-model runs">
            <div className="divide-y divide-hairline">
              {savedRuns.isLoading && <p className="p-5 text-sm text-muted-foreground">Loading saved runs…</p>}
              {savedRuns.error && <p className="p-5 text-sm text-destructive">Could not load saved runs: {savedRuns.error.message}</p>}
              {!savedRuns.isLoading && !savedRuns.error && savedRuns.data?.runs.length === 0 && <p className="p-5 text-sm text-muted-foreground">No saved runs yet. Run the world model once to create an auditable record.</p>}
              {savedRuns.data?.runs.map((run) => (
                <div key={run.simulation_id}>
                <button
                  onClick={() => { setSelectedSavedId(run.simulation_id); setTopologyKey(run.topology); setEpisodes(run.requested_episodes); setSeed(run.seed); setStep(1); }}
                  className={`flex w-full flex-wrap items-center justify-between gap-3 p-5 text-left hover:bg-pearl ${selectedSavedId === run.simulation_id ? "bg-pearl" : ""}`}
                >
                  <span><span className="block font-mono text-xs text-primary">{run.simulation_id}</span><span className="mt-1 block text-sm">{run.topology} · seed {run.seed} · {run.completed_episodes.toLocaleString()} completed</span></span>
                  <span className="text-right text-xs text-muted-foreground"><span className="block">{percent(run.success_rate)} success · {run.unique_paths} paths</span><span>{new Date(run.created_at).toLocaleString()}</span></span>
                </button>
                {selectedSavedId === run.simulation_id && savedRun.data && <div className="border-t border-hairline bg-pearl/45 px-5 py-4"><div className="flex items-center justify-between gap-3"><div><p className="eyebrow">Stored ranked paths</p><p className="mt-1 text-[11px] text-muted-foreground">{run.topology} · {percent(run.success_rate)} success · {run.unique_paths} paths</p></div><button type="button" onClick={() => setSelectedSavedId(null)} className="text-[11px] font-semibold text-muted-foreground hover:text-foreground">Close</button></div><div className="mt-3 max-h-72 space-y-1.5 overflow-y-auto pr-1 text-[12px]">{savedRun.data.paths.map((path) => <div key={path.rank} className="rounded-md border border-hairline bg-card px-3 py-2"><span className="mr-2 font-semibold text-primary">#{path.rank}</span>{Array.isArray(path.path) ? path.path.join(" → ") : path.path}<span className="float-right text-[11px] text-muted-foreground">{path.count} runs · {percent(path.frequency)}</span></div>)}</div></div>}
                </div>
              ))}
            </div>
            {false && savedRun.data && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setSelectedSavedId(null); }}>
                <button type="button" onClick={() => setSelectedSavedId(null)} className="fixed right-6 top-6 z-10 text-2xl text-white hover:text-white/70" aria-label="Close saved run">×</button>
                <div className="max-h-[65vh] w-full max-w-xl overflow-y-auto rounded-lg border border-hairline bg-card p-4 shadow-2xl"><p className="eyebrow">Stored ranked paths</p>{selectedRun && <p className="mt-1 text-[11px] text-muted-foreground">{selectedRun.topology} · {percent(selectedRun.success_rate)} success · {selectedRun.unique_paths} paths</p>}<div className="mt-3 space-y-1.5 text-[12px]">
                  {savedRun.data.paths.map((path) => <div key={path.rank} className="rounded bg-pearl p-3"><span className="mr-2 text-primary">#{path.rank}</span>{Array.isArray(path.path) ? path.path.join(" → ") : path.path}<span className="float-right text-muted-foreground">{path.count} runs · {percent(path.frequency)}</span></div>)}
                </div></div>
              </div>
            )}
          </Panel>
        )}

        <div className="grid gap-4 md:grid-cols-4">
          <Metric
            label="Attack success rate"
            value={replay ? percent(replay.success_rate) : "—"}
            sub={
              replay
                ? `${replay.successful_runs} of ${replay.n_episodes} backend runs`
                : "No run loaded"
            }
            tone="destructive"
          />
          <Metric
            label="Selected path frequency"
            value={replay ? percent(replay.selected_path_frequency) : "—"}
            sub={replay ? `${replay.selected_path_count} occurrences` : "No run loaded"}
            tone="primary"
          />
          <Metric
            label="Unique attack paths"
            value={replay ? String(replay.total_unique_paths) : "—"}
            sub={replay ? `${episode.length} nodes in replayed path` : "No run loaded"}
          />
          <Metric
            label="Result source"
            value={replay ? DATA_SOURCE_LABELS[replay.data_source] : "—"}
            sub={
              replay
                ? `${replay.analysis_engine.replaceAll("_", " ")} · ${replay.confidence} confidence`
                : "No run loaded"
            }
            tone="success"
          />
        </div>

        <Panel title="Simulation evidence">
          {!replay?.evidence ? (
            <p className="p-5 text-sm text-muted-foreground">
              Run the world model to record its topology snapshot, seed, and completed episode count.
            </p>
          ) : (
            <div className="grid gap-px bg-hairline sm:grid-cols-2 lg:grid-cols-4">
              <div className="bg-card p-4">
                <p className="eyebrow">Execution proof</p>
                <p className="mt-2 text-lg font-semibold">
                  {replay.evidence.execution.completed_episodes.toLocaleString()} completed
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {replay.evidence.execution.requested_episodes.toLocaleString()} requested · {replay.evidence.execution.successful_runs.toLocaleString()} successful
                </p>
              </div>
              <div className="bg-card p-4">
                <p className="eyebrow">Frozen input</p>
                <p className="mt-2 text-sm font-semibold">{replay.evidence.topology.key}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {replay.evidence.topology.nodes} nodes · {replay.evidence.topology.edges} edges · hash {replay.evidence.topology.snapshot_sha256}
                </p>
              </div>
              <div className="bg-card p-4">
                <p className="eyebrow">Model & seed</p>
                <p className="mt-2 text-sm font-semibold">{replay.evidence.model.engine.replaceAll("_", " ")}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Seed {replay.evidence.model.seed} · {replay.evidence.model.checkpoint_present ? "checkpoint loaded" : "rule-based fallback"}
                </p>
              </div>
              <div className="bg-card p-4">
                <p className="eyebrow">Safety & replay</p>
                <p className="mt-2 text-xs text-muted-foreground">{replay.evidence.safety}</p>
                <p className="mt-2 text-xs text-primary">{replay.evidence.reproduce}</p>
              </div>
            </div>
          )}
        </Panel>

        <Panel
          title={
            replay?.reaches_critical_asset
              ? "Most frequent successful attack path"
              : "Most frequent observed path"
          }
          action={<div className="flex items-center gap-3"><div className="flex items-center gap-1 border-b border-hairline text-[11px]"><button type="button" onClick={() => setMapMode("path")} className={`border-b-2 px-2 py-1.5 font-semibold transition-colors ${mapMode === "path" ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:border-primary hover:text-foreground"}`}>Path view</button><button type="button" onClick={() => setMapMode("topology")} className={`border-b-2 px-2 py-1.5 font-semibold transition-colors ${mapMode === "topology" ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:border-primary hover:text-foreground"}`}>Topology view</button></div><span className="text-[12px] text-muted-foreground">{replay?.topology ?? topologyKey}</span></div>}
        >
          {mapMode === "path" && <p className="px-5 pt-4 text-[11px] text-muted-foreground"><span className="font-semibold text-destructive">Red</span> shows the simulated route. Numbered nodes show the attack order; the ring marks the current replay step.</p>}
          <div className="chart-frame"><MiniMap
            nodes={mapNodes}
            edges={mapEdges}
            compromised={mapMode === "path" ? pathNodeIds : traversedNodes}
            active={frame?.node_id}
            height={mapMode === "path" ? 300 : 420}
            pathStepIds={mapMode === "path" ? pathNodeIds : []}
          /></div>
          <div className="border-t border-hairline bg-pearl/35 p-5">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div><p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">Replay controls</p><p className="mt-1 text-xs text-muted-foreground">Review the observed attack sequence step by step.</p></div>
              <span className="rounded-full border border-hairline bg-card px-2.5 py-1 text-[11px] font-medium text-muted-foreground">{episode.length ? `${step} / ${episode.length}` : "No replay"}</span>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                disabled={episode.length === 0}
                onClick={() => setPlaying((current) => !current)}
                className="rounded-md bg-primary px-4 py-2 text-[12px] font-semibold text-primary-foreground shadow-sm transition-all hover:-translate-y-px hover:shadow-md disabled:bg-chip disabled:text-muted-foreground disabled:shadow-none"
              >
                {playing ? "Pause replay" : "Play replay"}
              </button>
              <button
                disabled={step <= 1 || episode.length === 0}
                onClick={() => {
                  setPlaying(false);
                  setStep((current) => Math.max(1, current - 1));
                }}
                className="rounded-md border border-hairline bg-card px-3 py-2 text-[12px] font-semibold text-foreground transition-colors hover:bg-background disabled:bg-chip disabled:text-muted-foreground"
              >
                ‹ Step back
              </button>
              <button
                disabled={step >= episode.length}
                onClick={() => {
                  setPlaying(false);
                  setStep((current) => Math.min(episode.length, current + 1));
                }}
                className="rounded-md border border-hairline bg-card px-3 py-2 text-[12px] font-semibold text-foreground transition-colors hover:bg-background disabled:bg-chip disabled:text-muted-foreground"
              >
                Step forward ›
              </button>
              <button
                disabled={episode.length === 0}
                onClick={() => {
                  setPlaying(false);
                  setStep(1);
                }}
                className="rounded-md border border-hairline bg-card px-3 py-2 text-[12px] font-medium text-secondary-foreground transition-colors hover:bg-background disabled:text-muted-foreground"
              >
                Reset replay
              </button>
            </div>

            <div className="max-w-3xl">
            <input
              type="range"
              min={1}
              max={Math.max(1, episode.length)}
              value={Math.min(step, Math.max(1, episode.length))}
              disabled={episode.length === 0}
              onChange={(event) => {
                setPlaying(false);
                setStep(Number(event.target.value));
              }}
              className="mt-5 h-2 w-full cursor-pointer accent-primary disabled:cursor-not-allowed disabled:opacity-40"
            />
            </div>
            <div className="mt-2 flex justify-between text-[11px] font-medium text-muted-foreground">
              <span>{episode.length ? `Step ${step}` : "No path"}</span>
              <span>
                {episode.length
                  ? `${episode.length} total steps`
                  : "Run a simulation to create a replay"}
              </span>
            </div>
            {replay?.data_source_note && (
              <p className="mt-4 rounded-md border border-hairline bg-card px-3 py-2 text-[11px] text-muted-foreground">
                <span className="font-semibold text-foreground">Evidence note:</span> {replay.data_source_note}
              </p>
            )}
          </div>
        </Panel>

        <div className="grid gap-6 xl:grid-cols-3">
          <Panel title="Current backend step" className="xl:col-span-1">
            <div className="space-y-3 p-5">
              {!frame ? (
                <p className="text-sm text-muted-foreground">
                  Run a simulation to generate an attack path.
                </p>
              ) : (
                <>
                  <p className="eyebrow">
                    Step {frame.step} · {frame.node_type}
                  </p>
                  <h3 className="font-display text-[19px] font-semibold leading-snug">
                    {frame.node_id}
                  </h3>
                  <p className="text-[13px] text-muted-foreground">
                    {frame.software} {frame.version}
                  </p>
                  <dl className="space-y-2 text-[13px]">
                    <div className="flex justify-between gap-4">
                      <dt>Highest CVSS</dt>
                      <dd>{frame.max_cvss.toFixed(1)}</dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt>Tagged CVEs</dt>
                      <dd>{frame.num_vulns}</dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt>Compromise probability</dt>
                      <dd>{percent(frame.compromise_probability)}</dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt>Asset classification</dt>
                      <dd>
                        {frame.is_critical_asset
                          ? "Critical asset"
                          : frame.is_entry_point
                            ? "Entry point"
                            : "Internal asset"}
                      </dd>
                    </div>
                  </dl>
                  {frame.edge && (
                    <div className="rounded-md bg-pearl p-3 text-[12px] text-muted-foreground">
                      Transition from {frame.edge.source} via{" "}
                      {frame.edge.connection_type.toUpperCase()} · {frame.edge.permission_level}{" "}
                      permission · {frame.edge.has_firewall ? "firewall present" : "no firewall"}
                    </div>
                  )}
                </>
              )}
            </div>
          </Panel>

          <Panel title="Backend path timeline" className="xl:col-span-2">
            <ol className="divide-y divide-hairline">
              {episode.length === 0 && (
                <li className="p-5 text-sm text-muted-foreground">
                  No replay data returned by the backend.
                </li>
              )}
              {episode.map((item) => (
                <li key={`${item.step}-${item.node_id}`}>
                  <button
                    onClick={() => {
                      setPlaying(false);
                      setStep(item.step);
                    }}
                    className={`flex w-full items-start gap-4 px-5 py-3 text-left transition-colors hover:bg-pearl ${item.step === step ? "bg-pearl" : ""} ${item.step > step ? "opacity-45" : ""}`}
                  >
                    <span className="w-14 shrink-0 font-mono text-[12px] text-muted-foreground">
                      #{item.step}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-[13px]">{item.node_id}</span>
                      <span className="block text-[12px] text-muted-foreground">
                        {item.edge
                          ? `${item.edge.connection_type.toUpperCase()} from ${item.edge.source}`
                          : "Path entry"}{" "}
                        · {item.node_type} · CVSS {item.max_cvss.toFixed(1)}
                      </span>
                    </span>
                    {(item.is_entry_point || item.is_critical_asset) && (
                      <span className="shrink-0 rounded-full bg-pearl px-2 py-0.5 text-[11px] text-primary">
                        {item.is_critical_asset ? "critical" : "entry"}
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ol>
          </Panel>
        </div>
      </div>
      {configModalOpen && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/35 p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setConfigModalOpen(false); }}>
        <div role="dialog" aria-modal="true" aria-labelledby="save-config-title" className="w-full max-w-sm animate-in fade-in slide-in-from-top-2 rounded-lg border border-hairline bg-card p-5 shadow-2xl duration-200">
          <div className="flex items-start justify-between gap-3"><div><h2 id="save-config-title" className="text-base font-semibold">Save world-model configuration</h2><p className="mt-1 text-xs text-muted-foreground">Review the parameters before saving.</p></div><button type="button" onClick={() => setConfigModalOpen(false)} className="text-lg leading-none text-muted-foreground hover:text-foreground" aria-label="Close">×</button></div>
          <dl className="mt-4 divide-y divide-hairline rounded-md border border-hairline"><div className="flex justify-between px-3 py-2 text-xs"><dt className="text-muted-foreground">Topology</dt><dd className="font-medium">{topologyKey}</dd></div><div className="flex justify-between px-3 py-2 text-xs"><dt className="text-muted-foreground">Environment</dt><dd className="font-medium">World model</dd></div><div className="flex justify-between px-3 py-2 text-xs"><dt className="text-muted-foreground">Episodes</dt><dd className="font-medium">{episodes.toLocaleString()}</dd></div><div className="flex justify-between px-3 py-2 text-xs"><dt className="text-muted-foreground">Seed</dt><dd className="font-medium">{seed}</dd></div><div className="flex justify-between px-3 py-2 text-xs"><dt className="text-muted-foreground">Estimated runtime</dt><dd className="font-medium">~{estimatedSeconds}s</dd></div></dl>
          <div className="mt-5 flex justify-end gap-2"><button type="button" onClick={() => setConfigModalOpen(false)} className="rounded-md border border-hairline px-3 py-2 text-xs font-medium text-secondary-foreground hover:bg-pearl">Cancel</button><button type="button" onClick={saveConfiguration} disabled={!!validationError} className="rounded-md bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground disabled:bg-chip disabled:text-muted-foreground">Save configuration</button></div>
        </div>
      </div>}
    </Shell>
  );
}
