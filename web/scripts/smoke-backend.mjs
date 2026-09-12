const baseUrl = (process.env.BACKEND_URL || "http://127.0.0.1:8020").replace(/\/$/, "");

async function requestJson(path, options = {}) {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const raw = await response.text();
  let payload = {};
  if (raw) {
    try {
      payload = JSON.parse(raw);
    } catch {
      payload = { detail: raw };
    }
  }

  if (!response.ok) {
    throw new Error(`${path} -> ${response.status}: ${payload.detail || raw || "request failed"}`);
  }

  return payload;
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function main() {
  const health = await requestJson("/api/health");
  assert(health.status === "ok", "health status was not ok");

  const scenarios = await requestJson("/api/scenarios");
  assert(Array.isArray(scenarios.scenarios), "scenarios payload missing list");
  assert(scenarios.scenarios.length > 0, "no demo scenarios were returned");

  const marl = await requestJson("/api/marl-results");
  assert(Array.isArray(marl.results), "marl results payload missing list");

  const patch = await requestJson("/api/patch-optimize", {
    method: "POST",
    body: JSON.stringify({
      topology: "enterprise_20n",
      n_baseline: 50,
      n_eval_per_patch: 10,
      data_source: "simulation",
      telemetry_weight: 0.4,
    }),
  });
  assert(Array.isArray(patch.results), "patch optimize results missing list");
  assert(patch.summary && patch.summary.takeaway, "patch optimize summary missing takeaway");

  console.log(
    JSON.stringify(
      {
        backendUrl: baseUrl,
        health: health.status,
        scenarios: scenarios.scenarios.length,
        marlResults: marl.results.length,
        patchResults: patch.results.length,
        summary: patch.summary.takeaway,
      },
      null,
      2,
    ),
  );
}

main().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
