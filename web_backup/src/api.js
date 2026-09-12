async function handleResponse(res) {
  const raw = await res.text();
  let data = {};
  if (raw) {
    try {
      data = JSON.parse(raw);
    } catch {
      data = { detail: raw };
    }
  }
  if (!res.ok) {
    throw new Error(data.detail || `Request failed (${res.status})`);
  }
  return data;
}

export async function getStatus(topology = 'enterprise_20n') {
  const query = new URLSearchParams({ topology });
  const res = await fetch(`/api/status?${query.toString()}`);
  return handleResponse(res);
}

export async function getTopology(topology) {
  const res = await fetch(`/api/topology/${topology}`);
  return handleResponse(res);
}

export async function runSimulation(topology, nEpisodes, options = {}) {
  const {
    dataSource = 'simulation',
    telemetryWeight = 0.4,
  } = options;

  const res = await fetch('/api/simulate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      topology,
      n_episodes: nEpisodes,
      data_source: dataSource,
      telemetry_weight: telemetryWeight,
    }),
  });
  return handleResponse(res);
}

export async function runSimulationSeedSweep(topology, nEpisodes, seeds, options = {}) {
  const {
    dataSource = 'simulation',
    telemetryWeight = 0.4,
  } = options;

  const res = await fetch('/api/simulate/seed-sweep', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      topology,
      n_episodes: nEpisodes,
      seeds,
      data_source: dataSource,
      telemetry_weight: telemetryWeight,
    }),
  });
  return handleResponse(res);
}

export async function runPatchOptimization(topology, nBaseline, nEvalPerPatch, options = {}) {
  const {
    dataSource = 'simulation',
    telemetryWeight = 0.4,
  } = options;

  const res = await fetch('/api/patch-optimize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      topology,
      n_baseline: nBaseline,
      n_eval_per_patch: nEvalPerPatch,
      data_source: dataSource,
      telemetry_weight: telemetryWeight,
    }),
  });
  return handleResponse(res);
}

export async function getPatchResults(options = {}) {
  const {
    topology = 'enterprise_20n',
    dataSource = 'simulation',
    telemetryWeight = 0.4,
    nBaseline = 200,
    nEvalPerPatch = 50,
    refresh = false,
  } = options;

  const query = new URLSearchParams({
    topology,
    data_source: dataSource,
    telemetry_weight: String(telemetryWeight),
    n_baseline: String(nBaseline),
    n_eval_per_patch: String(nEvalPerPatch),
    refresh: String(refresh),
  });

  const res = await fetch(`/api/patch-results?${query.toString()}`);
  return handleResponse(res);
}

export async function getMarlResults() {
  const res = await fetch('/api/marl-results');
  const data = await handleResponse(res);
  // Backend returns { results: [ { round, red_win_rate, blue_win_rate, ... } ] }.
  // Normalize to the shape consumed by the UI.
  if (Array.isArray(data.results) && data.results.length > 0) {
    const history = data.results.map((row, idx) => ({
      ...row,
      round: Number(row.round ?? idx + 1),
      red_win_rate: Number(row.red_win_rate ?? 0),
      blue_win_rate: Number(row.blue_win_rate ?? 0),
    }));
    const latest = history[history.length - 1];
    const redAvg = history.reduce((sum, row) => sum + Number(row.red_win_rate || 0), 0) / history.length;
    const blueAvg = history.reduce((sum, row) => sum + Number(row.blue_win_rate || 0), 0) / history.length;

    return {
      rounds: history.length,
      red_win_rate: latest.red_win_rate ?? 0,
      blue_win_rate: latest.blue_win_rate ?? 0,
      red_win_rate_avg: redAvg,
      blue_win_rate_avg: blueAvg,
      history,
    };
  }
  return data;
}

export async function generateReport(topology) {
  const res = await fetch('/api/generate-report', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topology }),
  });
  return handleResponse(res);
}

export async function getReportHtml() {
  const res = await fetch('/api/report-html');
  return handleResponse(res);
}

export async function getScenarios() {
  const res = await fetch('/api/scenarios');
  return handleResponse(res);
}

export async function runScenario(scenarioId, nEpisodes, options = {}) {
  const {
    dataSource = 'simulation',
    telemetryWeight = 0.4,
  } = options;

  const res = await fetch(`/api/run-scenario/${scenarioId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      n_episodes: nEpisodes,
      data_source: dataSource,
      telemetry_weight: telemetryWeight,
    }),
  });
  const data = await handleResponse(res);
  // Unwrap nested response structure: {scenario, simulation, replay}
  // and return simulation data at top level for compatibility
  if (data.simulation) {
    return {
      ...data.simulation,
      scenario: data.scenario,
      replay: data.replay,
    };
  }
  return data;
}

export async function getLatestReplay() {
  const res = await fetch('/api/replay/latest');
  const data = await handleResponse(res);
  return data.replay || data;
}

export async function getRiskScorecard(topology, nEpisodes, topKPatches = 3, options = {}) {
  const {
    dataSource = 'simulation',
    telemetryWeight = 0.4,
  } = options;

  const res = await fetch('/api/risk-scorecard', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      topology,
      n_episodes: nEpisodes,
      top_k_patches: topKPatches,
      data_source: dataSource,
      telemetry_weight: telemetryWeight,
    }),
  });
  return handleResponse(res);
}

export async function runCostAwareRanking(topology, topK = 12) {
  const res = await fetch('/api/patch-cost-ranking', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topology, top_k: topK }),
  });
  return handleResponse(res);
}

export async function getExplainability(topology, topN = 5) {
  const res = await fetch('/api/explainability', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topology, top_n: topN }),
  });
  return handleResponse(res);
}

export async function getCostModels(userId = 'default') {
  const res = await fetch(`/api/cost-models/${userId}`);
  return handleResponse(res);
}

export async function createCostModel(name, description, patchIds) {
  const res = await fetch('/api/cost-models', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description, patches: patchIds }),
  });
  return handleResponse(res);
}

export async function activateCostModel(modelId) {
  const res = await fetch(`/api/cost-models/${modelId}/activate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  return handleResponse(res);
}

export async function createTrainingJob(jobType, episodes, modelId = null) {
  const res = await fetch('/api/training/jobs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_type: jobType, n_episodes: episodes, model_id: modelId }),
  });
  return handleResponse(res);
}

export async function getTrainingJobStatus(jobId) {
  const res = await fetch(`/api/training/jobs/${jobId}`);
  return handleResponse(res);
}

export async function getReportHistory(userId = 'default') {
  const res = await fetch(`/api/reports/${userId}`);
  return handleResponse(res);
}

export async function loadTelemetrySample(topology = 'enterprise_20n') {
  const query = new URLSearchParams({ topology });
  const res = await fetch(`/api/telemetry/load-sample?${query.toString()}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  return handleResponse(res);
}

export async function getTelemetryStatus(topology = 'enterprise_20n') {
  const query = new URLSearchParams({ topology });
  const res = await fetch(`/api/telemetry/status?${query.toString()}`);
  return handleResponse(res);
}

export async function runLiveTelemetryIngest(options = {}) {
  const {
    topology = 'enterprise_20n',
    mode = 'pure',
    maxConnections = 20,
    maxProcesses = 20,
  } = options;

  const res = await fetch('/api/telemetry/ingest-live', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      topology,
      mode,
      max_connections: maxConnections,
      max_processes: maxProcesses,
    }),
  });
  return handleResponse(res);
}

export async function generateEvidenceBundle(options = {}) {
  const {
    topology = 'enterprise_20n',
    nEpisodes = 700,
    nBaseline = 200,
    nEvalPerPatch = 50,
    telemetryWeight = 0.6,
    topKPatches = 3,
    comparisonSource,
  } = options;

  const res = await fetch('/api/evidence-bundle', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      topology,
      n_episodes: nEpisodes,
      n_baseline: nBaseline,
      n_eval_per_patch: nEvalPerPatch,
      telemetry_weight: telemetryWeight,
      top_k_patches: topKPatches,
      comparison_source: comparisonSource,
    }),
  });
  return handleResponse(res);
}
