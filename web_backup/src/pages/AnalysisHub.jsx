import { useState, useEffect, useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import { useSimulation } from '../contexts/SimulationContext';
import { useResults } from '../contexts/ResultsContext';
import { useUser } from '../contexts/UserContext';
import {
  getScenarios,
  runSimulation,
  runSimulationSeedSweep,
  runScenario,
  runPatchOptimization,
  loadTelemetrySample,
  getTelemetryStatus,
  getMarlResults,
  getLatestReplay,
  runLiveTelemetryIngest,
} from '../api';
import { getRoleCapabilities, getPermissionReason } from '../utils/rolePermissions';
import {
  formatDateTime,
  formatRatioPercent,
  getConfidenceLabel,
  getMarlHistoryRows,
  getSourceLabel,
  getTotalUniquePaths,
} from '../utils/presentation';
import { FEATURE_VISIBILITY } from '../config/featureVisibility';
import './AnalysisHub.css';

export default function AnalysisHub() {
  const location = useLocation();
  const { user } = useUser();
  const effectiveRole = FEATURE_VISIBILITY.enforcedRole || user?.role;
  const capabilities = getRoleCapabilities(effectiveRole);
  const {
    selectedTopology,
    selectedScenario,
    episodeCount,
    isRunning,
    dispatch: dispatchSimulation,
  } = useSimulation();
  const {
    simulationResults,
    patchResults,
    marlResults,
    replayData,
    error,
    dispatch: dispatchResults,
  } = useResults();

  const [activeTab, setActiveTab] = useState('simulation');
  const [scenarios, setScenarios] = useState([]);
  const [topologies, setTopologies] = useState([]);
  const [toastMessage, setToastMessage] = useState(null);
  const [nBaseline, setNBaseline] = useState(1000);
  const [nEvalPerPatch, setNEvalPerPatch] = useState(500);
  const [dataSource, setDataSource] = useState('hybrid');
  const [telemetryWeight, setTelemetryWeight] = useState(0.4);
  const [liveTelemetryMode, setLiveTelemetryMode] = useState('pure');
  const [isLiveIngestRunning, setIsLiveIngestRunning] = useState(false);
  const [seedSweepInput, setSeedSweepInput] = useState('11,21,42,73,101');
  const [seedSweepResults, setSeedSweepResults] = useState(null);
  const [isSeedSweepRunning, setIsSeedSweepRunning] = useState(false);
  const [telemetryStatusSnapshot, setTelemetryStatusSnapshot] = useState(null);

  const applyJudgePreset = () => {
    dispatchSimulation({ type: 'SET_TOPOLOGY', payload: 'enterprise_20n' });
    dispatchSimulation({ type: 'SET_SCENARIO', payload: 'ransomware-lateral' });
    dispatchSimulation({ type: 'SET_EPISODES', payload: 700 });
    setDataSource('hybrid');
    setTelemetryWeight(0.6);
    showToast('Judge hybrid preset applied.', 'success');
  };

  useEffect(() => {
    if (episodeCount > capabilities.maxEpisodes) {
      dispatchSimulation({ type: 'SET_EPISODES', payload: capabilities.maxEpisodes });
    }
  }, [episodeCount, capabilities.maxEpisodes, dispatchSimulation]);

  useEffect(() => {
    const loadInitialData = async () => {
      setTopologies([
        { key: 'enterprise_20n', label: 'Enterprise (20 nodes)' },
        { key: 'small_office_10n', label: 'Small Office (10 nodes)' },
        { key: 'cloud_hybrid_30n', label: 'Cloud Hybrid (30 nodes)' },
      ]);

      try {
        const scenariosData = await getScenarios();
        const scenariosList = scenariosData.scenarios || scenariosData;
        setScenarios(scenariosList || []);
      } catch (loadError) {
        console.error('Scenario load error:', loadError);
        showToast('Scenario list unavailable. Using manual mode.', 'info');
      }

      try {
        const marlData = await getMarlResults();
        if (marlData) {
          dispatchResults({ type: 'SET_MARL_RESULTS', payload: marlData });
        }
      } catch (loadError) {
        console.error('MARL load error:', loadError);
      }
    };

    loadInitialData();
  }, [dispatchResults]);

  useEffect(() => {
    if (!location.state?.quickDemo) {
      return;
    }

    const preset = location.state.preset || {};
    dispatchSimulation({ type: 'SET_TOPOLOGY', payload: preset.topology || 'enterprise_20n' });
    dispatchSimulation({ type: 'SET_SCENARIO', payload: preset.scenario || 'ransomware-lateral' });
    dispatchSimulation({ type: 'SET_EPISODES', payload: preset.episodes || 700 });
    setDataSource(preset.dataSource || 'hybrid');
    setTelemetryWeight(preset.telemetryWeight ?? 0.6);
    showToast('Quick demo preset loaded for judges.', 'success');
  }, [location.state, dispatchSimulation]);

  const showToast = (message, type = 'info') => {
    setToastMessage({ text: message, type });
    setTimeout(() => setToastMessage(null), 3000);
  };

  const formatDataSourceNote = (result) => {
    const source = (result?.data_source || result?.requested_data_source || '').toLowerCase();
    const note = String(result?.data_source_note || '').toLowerCase();

    if (source === 'telemetry') {
      return 'Telemetry-backed result.';
    }

    if (source === 'hybrid') {
      return 'Hybrid result blending simulation with telemetry where available.';
    }

    if (note.includes('telemetry_unavailable_fallback')) {
      return 'Telemetry was unavailable, so this run used the simulation fallback.';
    }

    if (note.includes('simulated_attack_paths')) {
      return 'Simulation-backed attack paths.';
    }

    if (note.includes('computed_from_patch_optimizer')) {
      return 'Patch ranking was computed from simulation impact.';
    }

    if (note.includes('estimated_without_trained_red_agent')) {
      return 'Estimated from simulation because a trained red agent is not available.';
    }

    return '';
  };

  const buildSimulationSummary = (result) => {
    if (!result) {
      return { takeaway: '', bullets: [], note: '' };
    }

    const summary = result.summary || {};
    const successRate = Number(summary.success_rate_percent ?? (Number(result.success_rate || 0) * 100));
    const episodes = Number(summary.episodes || result.n_episodes || result.evaluation_runs || 0);
    const successfulRuns = Number(summary.successful_runs ?? result.successful_runs ?? 0);
    const attackPaths = Number(summary.attack_paths ?? getTotalUniquePaths(result));
    const sourceLabel = summary.source || getSourceLabel(result.data_source || result.requested_data_source);
    const confidenceLabel = String(summary.confidence || getConfidenceLabel(result)).toLowerCase();
    const riskBand = successRate >= 60 ? 'high' : successRate >= 25 ? 'moderate' : 'low';

    const takeaway = summary.takeaway || `Risk is ${riskBand}: ${successRate.toFixed(2)}% attack success across ${episodes} episodes.`;

    const bullets = Array.isArray(summary.bullets) && summary.bullets.length > 0
      ? summary.bullets
      : [
          `${attackPaths} distinct attack path${attackPaths === 1 ? '' : 's'} identified.`,
          `${successfulRuns} of ${Number(result.evaluation_runs || result.n_episodes || 0)} runs succeeded.`,
          `${sourceLabel} source with ${confidenceLabel} confidence.`,
        ];

    const note = summary.note || formatDataSourceNote(result);

    return { takeaway, bullets, note };
  };

  const marlHistoryRows = getMarlHistoryRows(marlResults);

  const parseSeedList = (rawValue) => {
    const seeds = String(rawValue || '')
      .split(',')
      .map((token) => parseInt(token.trim(), 10))
      .filter((num) => Number.isInteger(num));
    return Array.from(new Set(seeds));
  };

  const refreshTelemetryStatus = async ({ notify = false } = {}) => {
    if (!selectedTopology) {
      return null;
    }

    const status = await getTelemetryStatus(selectedTopology);
    setTelemetryStatusSnapshot(status);

    if (notify) {
      showToast(
        `Telemetry events: ${status.event_count || 0}, blocked: ${status.blocked_events || 0}, critical reaches: ${status.critical_reaches || 0}`,
        'info',
      );
    }

    return status;
  };

  useEffect(() => {
    if (!selectedTopology) {
      setTelemetryStatusSnapshot(null);
      return undefined;
    }

    let cancelled = false;

    const pullStatus = async () => {
      try {
        const status = await getTelemetryStatus(selectedTopology);
        if (!cancelled) {
          setTelemetryStatusSnapshot(status);
        }
      } catch {
        if (!cancelled) {
          setTelemetryStatusSnapshot(null);
        }
      }
    };

    pullStatus();
    const intervalId = setInterval(pullStatus, 15000);

    return () => {
      cancelled = true;
      clearInterval(intervalId);
    };
  }, [selectedTopology]);

  const handleRunSimulation = async () => {
    if (!capabilities.canRunSimulation) {
      showToast(getPermissionReason(user?.role, 'runSimulation'), 'info');
      return;
    }

    if (!selectedTopology) {
      showToast('Please select a topology', 'error');
      return;
    }

    try {
      dispatchSimulation({ type: 'START_EXECUTION' });
      dispatchResults({ type: 'START_LOADING' });

      const results = await runSimulation(selectedTopology, episodeCount, {
        dataSource,
        telemetryWeight,
      });
      dispatchResults({ type: 'SET_SIMULATION_RESULTS', payload: results });

      const replay = await getLatestReplay();
      if (replay) {
        dispatchResults({ type: 'SET_REPLAY_DATA', payload: replay });
      }

      dispatchSimulation({ type: 'END_EXECUTION' });
      showToast('Simulation completed successfully!', 'success');
    } catch (err) {
      dispatchResults({ type: 'SET_ERROR', payload: err.message });
      dispatchSimulation({ type: 'END_EXECUTION' });
      showToast('Simulation failed: ' + err.message, 'error');
    }
  };

  const handleRunScenario = async (scenarioId) => {
    if (!capabilities.canRunScenario) {
      showToast(getPermissionReason(user?.role, 'runScenario'), 'info');
      return;
    }

    try {
      dispatchSimulation({ type: 'START_EXECUTION' });
      dispatchResults({ type: 'START_LOADING' });

      const results = await runScenario(scenarioId, episodeCount, {
        dataSource,
        telemetryWeight,
      });
      dispatchResults({ type: 'SET_SIMULATION_RESULTS', payload: results });

      if (results?.replay) {
        dispatchResults({ type: 'SET_REPLAY_DATA', payload: results.replay });
      } else {
        const replay = await getLatestReplay();
        if (replay) {
          dispatchResults({ type: 'SET_REPLAY_DATA', payload: replay });
        }
      }

      dispatchSimulation({ type: 'END_EXECUTION' });
      showToast('Scenario execution completed!', 'success');
    } catch (err) {
      dispatchResults({ type: 'SET_ERROR', payload: err.message });
      dispatchSimulation({ type: 'END_EXECUTION' });
      showToast('Scenario execution failed: ' + err.message, 'error');
    }
  };

  const handleRunPatchOptimization = async () => {
    if (!capabilities.canRunPatchOptimization) {
      showToast(getPermissionReason(user?.role, 'runPatchOptimization'), 'info');
      return;
    }

    if (!selectedTopology) {
      showToast('Please select a topology', 'error');
      return;
    }

    try {
      dispatchSimulation({ type: 'START_EXECUTION' });
      dispatchResults({ type: 'START_LOADING' });

      const results = await runPatchOptimization(selectedTopology, nBaseline, nEvalPerPatch, {
        dataSource,
        telemetryWeight,
      });
      dispatchResults({ type: 'SET_PATCH_RESULTS', payload: results });
      dispatchSimulation({ type: 'END_EXECUTION' });

      showToast('Patch optimization completed!', 'success');
    } catch (err) {
      dispatchResults({ type: 'SET_ERROR', payload: err.message });
      dispatchSimulation({ type: 'END_EXECUTION' });
      showToast('Patch optimization failed: ' + err.message, 'error');
    }
  };

  const handleRunSeedSweep = async () => {
    if (!selectedTopology) {
      showToast('Please select a topology', 'error');
      return;
    }

    const seeds = parseSeedList(seedSweepInput);
    if (!seeds.length) {
      showToast('Enter numeric seeds like 11,21,42.', 'error');
      return;
    }

    try {
      setIsSeedSweepRunning(true);
      const result = await runSimulationSeedSweep(selectedTopology, episodeCount, seeds, {
        dataSource,
        telemetryWeight,
      });
      setSeedSweepResults(result);
      const summary = result?.summary || {};
      showToast(
        `Seed sweep done: mean ${(Number(summary.mean_success_rate || 0) * 100).toFixed(2)}%, spread ${Number(summary.spread_pp || 0).toFixed(2)} pp.`,
        'success',
      );
    } catch (err) {
      showToast('Seed sweep failed: ' + err.message, 'error');
    } finally {
      setIsSeedSweepRunning(false);
    }
  };

  const handleLoadTelemetrySample = async () => {
    if (!selectedTopology) {
      showToast('Select a topology first.', 'error');
      return;
    }

    try {
      const result = await loadTelemetrySample(selectedTopology);
      await refreshTelemetryStatus();
      showToast(`Loaded ${result.loaded || 0} telemetry events for ${selectedTopology}.`, 'success');
    } catch (err) {
      showToast('Telemetry sample load failed: ' + err.message, 'error');
    }
  };

  const handleRunLiveTelemetryIngest = async () => {
    if (!selectedTopology) {
      showToast('Select a topology first.', 'error');
      return;
    }

    try {
      setIsLiveIngestRunning(true);
      const result = await runLiveTelemetryIngest({
        topology: selectedTopology,
        mode: liveTelemetryMode,
      });
      const summary = result.summary || {};
      await refreshTelemetryStatus();
      showToast(
        `Live ${liveTelemetryMode} ingest complete: ${summary.event_count || 0} events, blocked ${summary.blocked_events || 0}, critical ${summary.critical_reaches || 0}.`,
        'success',
      );
    } catch (err) {
      showToast('Live telemetry ingest failed: ' + err.message, 'error');
    } finally {
      setIsLiveIngestRunning(false);
    }
  };

  const handleTelemetryStatus = async () => {
    if (!selectedTopology) {
      showToast('Select a topology first.', 'error');
      return;
    }

    try {
      await refreshTelemetryStatus({ notify: true });
    } catch (err) {
      showToast('Telemetry status check failed: ' + err.message, 'error');
    }
  };

  const connectedLaptops = useMemo(() => {
    const clients = telemetryStatusSnapshot?.connected_clients;
    if (!Array.isArray(clients)) {
      return [];
    }
    return clients;
  }, [telemetryStatusSnapshot]);

  const getVisibleTabs = () => {
    const allTabs = [
      { key: 'simulation', label: 'Simulation Results' },
      { key: 'attack', label: 'Attack Analysis' },
      { key: 'patch', label: 'Patch Optimization' },
      { key: 'marl', label: 'Red vs Blue' },
      { key: 'replay', label: 'Replay Timeline' },
    ];
    return allTabs.filter((tab) => capabilities.analysisTabs.includes(tab.key));
  };

  const topologyNodeCount = useMemo(() => {
    const topologyNodes = {
      enterprise_20n: 248,
      small_office_10n: 96,
      cloud_hybrid_30n: 382,
    };
    return topologyNodes[selectedTopology] || 0;
  }, [selectedTopology]);

  const metricCards = useMemo(() => {
    const successRate = simulationResults ? formatRatioPercent(simulationResults.success_rate, 1) : '--';
    const attackPaths = simulationResults
      ? simulationResults.total_unique_paths ?? simulationResults.top_paths?.length ?? 0
      : 0;
    const activeCves = patchResults?.results?.length ?? 0;

    return [
      { label: 'Network Nodes', value: topologyNodeCount || '--' },
      { label: 'Active CVEs', value: activeCves || '--' },
      { label: 'Success Rate', value: successRate },
      { label: 'Attack Paths', value: attackPaths || '--' },
    ];
  }, [simulationResults, patchResults, topologyNodeCount]);

  const recentActivity = useMemo(() => {
    const feed = [];

    if (simulationResults) {
      feed.push({
        title: 'Analysis completed',
        detail: selectedScenario || 'Simulation',
        age: 'now',
      });
    }

    if (patchResults?.results?.length) {
      feed.push({
        title: 'Patch optimization updated',
        detail: `${patchResults.results.length} patch recommendations`,
        age: 'recent',
      });
    }

    if (marlHistoryRows.length) {
      feed.push({
        title: 'MARL history loaded',
        detail: `${marlHistoryRows.length} rounds available`,
        age: 'recent',
      });
    }

    if (selectedTopology) {
      feed.push({
        title: 'Config updated',
        detail: selectedTopology,
        age: 'recent',
      });
    }

    if (!feed.length) {
      feed.push({
        title: 'Waiting for analysis run',
        detail: 'Run analysis to populate live activity.',
        age: 'idle',
      });
    }

    return feed.slice(0, 6);
  }, [simulationResults, patchResults, marlHistoryRows, selectedTopology, selectedScenario]);

  return (
    <div className="analysis-hub-page">
      <div className="analysis-layout">
        <aside className="analysis-sidebar">
          <section className="control-panel">
            <h2>Analysis Config</h2>
            <div className="control-grid">
          <div className="control-group">
            <label htmlFor="topology-select">Topology:</label>
            <select
              id="topology-select"
              value={selectedTopology || ''}
              onChange={(e) => dispatchSimulation({ type: 'SET_TOPOLOGY', payload: e.target.value })}
              disabled={isRunning}
              className="control-input"
            >
              <option value="">Select a topology...</option>
              {topologies.map((t) => (
                <option key={t.key} value={t.key}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>

          {FEATURE_VISIBILITY.showScenarioSelector && (
            <div className="control-group">
              <label htmlFor="scenario-select">Demo Scenario (Optional):</label>
              <select
                id="scenario-select"
                value={selectedScenario || ''}
                onChange={(e) => dispatchSimulation({ type: 'SET_SCENARIO', payload: e.target.value })}
                disabled={isRunning}
                className="control-input"
              >
                <option value="">Manual topology selection</option>
                {scenarios.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name || s.scenario_name} ({s.topology || s.topology_name})
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="control-group">
            <label htmlFor="episodes-input">Episodes:</label>
            <input
              id="episodes-input"
              type="number"
              value={episodeCount}
              onChange={(e) =>
                dispatchSimulation({ type: 'SET_EPISODES', payload: parseInt(e.target.value, 10) || 1000 })
              }
              disabled={isRunning || capabilities.lockEpisodes}
              className="control-input"
              min="1"
              max={capabilities.maxEpisodes}
            />
          </div>

          <div className="control-group">
            <label htmlFor="source-select">Data Source:</label>
            <select
              id="source-select"
              value={dataSource}
              onChange={(e) => setDataSource(e.target.value)}
              disabled={isRunning}
              className="control-input"
            >
              <option value="simulation">Simulation</option>
              <option value="hybrid">Hybrid</option>
              <option value="telemetry">Telemetry</option>
            </select>
          </div>

          <div className="control-group">
            <label htmlFor="telemetry-weight">Telemetry Weight: {(telemetryWeight * 100).toFixed(0)}%</label>
            <input
              id="telemetry-weight"
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={telemetryWeight}
              onChange={(e) => setTelemetryWeight(parseFloat(e.target.value))}
              disabled={isRunning || dataSource === 'simulation'}
              className="control-input telemetry-slider"
            />
          </div>

              <div className="control-actions-container">
                <button
                  onClick={() => (selectedScenario ? handleRunScenario(selectedScenario) : handleRunSimulation())}
                  disabled={!selectedTopology || isRunning || isLiveIngestRunning || isSeedSweepRunning || (!capabilities.canRunSimulation && !selectedScenario) || (!capabilities.canRunScenario && !!selectedScenario)}
                  className="btn btn-primary analysis-run-btn"
                  title={
                    selectedScenario
                      ? (!capabilities.canRunScenario ? getPermissionReason(user?.role, 'runScenario') : '')
                      : (!capabilities.canRunSimulation ? getPermissionReason(user?.role, 'runSimulation') : '')
                  }
                >
                  {isRunning ? 'Running...' : 'Run Analysis'}
                </button>

                {FEATURE_VISIBILITY.showJudgePresetButton && (
                  <button
                    onClick={applyJudgePreset}
                    disabled={isRunning || isLiveIngestRunning || isSeedSweepRunning}
                    className="btn btn-secondary"
                  >
                    Quick Demo
                  </button>
                )}

                <button
                  onClick={handleRunPatchOptimization}
                  disabled={!selectedTopology || isRunning || !capabilities.canRunPatchOptimization}
                  className="btn btn-secondary"
                  title={!capabilities.canRunPatchOptimization ? getPermissionReason(user?.role, 'runPatchOptimization') : ''}
                >
                  {isRunning ? 'Running...' : 'Optimize Patches'}
                </button>

                <button
                  onClick={() => dispatchResults({ type: 'RESET' })}
                  disabled={isRunning || isLiveIngestRunning || isSeedSweepRunning}
                  className="btn btn-secondary analysis-clear-btn"
                >
                  Clear Results
                </button>

                {FEATURE_VISIBILITY.showTelemetryUtilityButtons && (
                  <details className="advanced-utilities">
                    <summary>Advanced Utilities</summary>
                    <div className="utility-cards-grid">
                      <div className="utility-card seed-sweep-card">
                        <div className="seed-sweep-controls">
                          <label htmlFor="seed-sweep-input">Seed Sweep</label>
                          <input
                            id="seed-sweep-input"
                            value={seedSweepInput}
                            onChange={(e) => setSeedSweepInput(e.target.value)}
                            disabled={isRunning || isLiveIngestRunning || isSeedSweepRunning}
                            className="control-input seed-sweep-input"
                            placeholder="11,21,42,73,101"
                          />
                          <button
                            onClick={handleRunSeedSweep}
                            disabled={!selectedTopology || isRunning || isLiveIngestRunning || isSeedSweepRunning}
                            className="btn btn-secondary"
                          >
                            {isSeedSweepRunning ? 'Running Seed Sweep...' : 'Run Seed Sweep'}
                          </button>
                        </div>
                      </div>

                      <div className="utility-card telemetry-live-card">
                        <div className="telemetry-live-controls">
                          <label htmlFor="live-mode-select">Live Telemetry Mode</label>
                          <select
                            id="live-mode-select"
                            value={liveTelemetryMode}
                            onChange={(e) => setLiveTelemetryMode(e.target.value)}
                            disabled={isRunning || isLiveIngestRunning || isSeedSweepRunning}
                            className="control-input telemetry-live-select"
                          >
                            <option value="pure">Pure Live</option>
                            <option value="enriched">Enriched Live</option>
                          </select>
                          <button
                            onClick={handleRunLiveTelemetryIngest}
                            disabled={!selectedTopology || isRunning || isLiveIngestRunning || isSeedSweepRunning}
                            className="btn btn-secondary"
                          >
                            {isLiveIngestRunning ? 'Ingesting Live Telemetry...' : 'Ingest Live Telemetry'}
                          </button>
                        </div>
                      </div>

                      <div className="utility-card telemetry-pair-card">
                        <div className="utility-dual-actions">
                          <button
                            onClick={handleLoadTelemetrySample}
                            disabled={isRunning || isLiveIngestRunning || isSeedSweepRunning}
                            className="btn btn-secondary"
                          >
                            Load Telemetry Sample
                          </button>

                          <button
                            onClick={handleTelemetryStatus}
                            disabled={isRunning || isLiveIngestRunning || isSeedSweepRunning}
                            className="btn btn-secondary"
                          >
                            Telemetry Status
                          </button>
                        </div>
                      </div>
                    </div>
                  </details>
                )}
              </div>

          {!capabilities.canRunSimulation && (
            <p className="empty-state" style={{ marginTop: '0.5rem' }}>
              {getPermissionReason(effectiveRole, 'runSimulation')}
            </p>
          )}
            </div>
          </section>
        </aside>

        <section className="analysis-main">
          <section className="analysis-kpi-grid" aria-label="Executive metrics">
            {metricCards.map((metric) => (
              <article key={metric.label} className="analysis-kpi-card">
                <p className="analysis-kpi-label">{metric.label}</p>
                <p className="analysis-kpi-value">{metric.value}</p>
              </article>
            ))}
          </section>

          <section className="tab-panel">
        <div className="tabs-header">
          {getVisibleTabs().map((tab) => (
            <button
              key={tab.key}
              className={`tab-button ${activeTab === tab.key ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="tab-content">
          {activeTab === 'simulation' && (
            <div className="tab-pane">
              <h3>Simulation Results</h3>
              {isRunning && <p className="loading-text">Running simulation...</p>}
              {error && <p className="error-text">Error: {error}</p>}
              {simulationResults ? (
                <div className="results-display">
                  <div className="provenance-row">
                    <span className={`source-badge source-${simulationResults.data_source || 'simulation'}`}>
                      Source: {getSourceLabel(simulationResults.data_source || simulationResults.requested_data_source)}
                    </span>
                    <span className="freshness-badge">Confidence: {getConfidenceLabel(simulationResults)}</span>
                    <span className="freshness-badge">
                      Freshness: {formatDateTime(simulationResults.data_freshness_at)}
                    </span>
                  </div>
                  <div className="simulation-summary-card">
                    <h4>Key Takeaway</h4>
                    {(() => {
                      const summary = buildSimulationSummary(simulationResults);
                      return (
                        <>
                          <p className="simulation-summary-headline">{summary.takeaway}</p>
                          <ul className="simulation-summary-list">
                            {summary.bullets.map((bullet, index) => (
                              <li key={index}>{bullet}</li>
                            ))}
                          </ul>
                          {summary.note && <p className="result-detail">{summary.note}</p>}
                        </>
                      );
                    })()}
                  </div>
                  <div className="metric-display">
                    <div className="metric-item">
                      <span className="metric-label">Attack Success Rate</span>
                      <span className="metric-value">{formatRatioPercent(simulationResults.success_rate, 2)}</span>
                      <span className="metric-subvalue">
                        {simulationResults.successful_runs ?? 0} / {simulationResults.evaluation_runs ?? simulationResults.n_episodes ?? 0} successful runs
                      </span>
                    </div>
                    <div className="metric-item">
                      <span className="metric-label">Total Episodes</span>
                      <span className="metric-value">{simulationResults.n_episodes}</span>
                    </div>
                    <div className="metric-item">
                      <span className="metric-label">Attack Paths Found</span>
                      <span className="metric-value">
                        {(simulationResults.total_unique_paths ?? simulationResults.top_paths?.length) || 0}
                      </span>
                    </div>
                  </div>
                  <p className="result-summary">Simulation completed with {simulationResults.n_episodes} episodes.</p>
                  <div className="provenance-row">
                    <span className={`source-badge source-${simulationResults.data_source || 'simulation'}`}>
                      {getSourceLabel(simulationResults.data_source || simulationResults.requested_data_source)}
                    </span>
                    <span className="freshness-badge">Confidence: {getConfidenceLabel(simulationResults)}</span>
                  </div>
                  {formatDataSourceNote(simulationResults) && <p className="result-detail">{formatDataSourceNote(simulationResults)}</p>}
                  {seedSweepResults?.summary && (
                    <div className="seed-variance-card">
                      <h4>Confidence And Variance</h4>
                      <div className="seed-variance-grid">
                        <div className="seed-metric">
                          <span className="metric-label">Mean Success</span>
                          <span className="metric-value">{(Number(seedSweepResults.summary.mean_success_rate || 0) * 100).toFixed(2)}%</span>
                        </div>
                        <div className="seed-metric">
                          <span className="metric-label">Range</span>
                          <span className="metric-value">
                            {(Number(seedSweepResults.summary.min_success_rate || 0) * 100).toFixed(2)}% - {(Number(seedSweepResults.summary.max_success_rate || 0) * 100).toFixed(2)}%
                          </span>
                        </div>
                        <div className="seed-metric">
                          <span className="metric-label">Std Dev</span>
                          <span className="metric-value">{(Number(seedSweepResults.summary.std_dev_success_rate || 0) * 100).toFixed(2)}%</span>
                        </div>
                        <div className="seed-metric">
                          <span className="metric-label">Spread</span>
                          <span className="metric-value">{Number(seedSweepResults.summary.spread_pp || 0).toFixed(2)} pp</span>
                        </div>
                      </div>
                      <p className="result-detail">Seeds tested: {(seedSweepResults.seeds || []).join(', ')}</p>
                    </div>
                  )}
                </div>
              ) : (
                <p className="empty-state">Run a simulation to view results</p>
              )}
            </div>
          )}

          {activeTab === 'attack' && (
            <div className="tab-pane">
              <h3>Attack Analysis</h3>
              {simulationResults?.top_paths ? (
                <div className="attack-analysis">
                  <p>
                    Top Attack Paths (showing {simulationResults.top_paths.length} of{' '}
                    {simulationResults.total_unique_paths ?? simulationResults.top_paths.length})
                  </p>
                  <ol className="attack-list">
                    {simulationResults.top_paths.map((pathObj, idx) => (
                      <li key={idx} className="attack-item">
                        <strong>{pathObj.path}</strong>
                        <br />
                        <small>
                          Frequency: {(pathObj.frequency * 100).toFixed(1)}% ({pathObj.count} times)
                        </small>
                      </li>
                    ))}
                  </ol>
                </div>
              ) : (
                <p className="empty-state">Run a simulation to analyze attack paths</p>
              )}
            </div>
          )}

          {activeTab === 'patch' && (
            <div className="tab-pane">
              <h3>Patch Optimization</h3>
              {!capabilities.canRunPatchOptimization && (
                <p className="empty-state">{getPermissionReason(user?.role, 'runPatchOptimization')}</p>
              )}
              <div className="patch-controls">
                <div className="control-group">
                  <label>Baseline Episodes:</label>
                  <input
                    type="number"
                    value={nBaseline}
                    onChange={(e) => setNBaseline(parseInt(e.target.value, 10))}
                    disabled={isRunning}
                    min="100"
                  />
                </div>
                <div className="control-group">
                  <label>Eval Episodes per Patch:</label>
                  <input
                    type="number"
                    value={nEvalPerPatch}
                    onChange={(e) => setNEvalPerPatch(parseInt(e.target.value, 10))}
                    disabled={isRunning}
                    min="100"
                  />
                </div>
                <button
                  onClick={handleRunPatchOptimization}
                  disabled={!selectedTopology || isRunning || !capabilities.canRunPatchOptimization}
                  className="btn btn-primary"
                  title={!capabilities.canRunPatchOptimization ? getPermissionReason(user?.role, 'runPatchOptimization') : ''}
                >
                  {isRunning ? 'Running...' : 'Run Patch Optimization'}
                </button>
              </div>
              {patchResults ? (
                <div className="patch-results">
                  <div className="provenance-row">
                    <span className={`source-badge source-${patchResults.data_source || 'simulation'}`}>
                      Source: {getSourceLabel(patchResults.data_source || patchResults.requested_data_source)}
                    </span>
                    <span className="freshness-badge">Confidence: {getConfidenceLabel(patchResults)}</span>
                    <span className="freshness-badge">Freshness: {formatDateTime(patchResults.data_freshness_at)}</span>
                  </div>
                  <p>Patch optimization completed for {patchResults.results?.length || 0} patches</p>
                  {patchResults.results && (
                    <table className="results-table">
                      <thead>
                        <tr>
                          <th>Patch</th>
                          <th>CVE</th>
                          <th>Impact</th>
                          <th>Cost</th>
                        </tr>
                      </thead>
                      <tbody>
                        {patchResults.results.slice(0, 10).map((patch, idx) => (
                          <tr key={idx}>
                            <td>{patch.node_id || patch.patch_id || 'N/A'}</td>
                            <td>{patch.cve_id || 'N/A'}</td>
                            <td>{((patch.simulation_impact || patch.impact || 0) * 100).toFixed(2)}%</td>
                            <td>{patch.cvss_score || patch.cost || 'N/A'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                  {patchResults.data_source_note && <p className="result-detail">{patchResults.data_source_note}</p>}
                  {formatDataSourceNote(patchResults) && <p className="result-detail">{formatDataSourceNote(patchResults)}</p>}
                </div>
              ) : (
                <p className="empty-state">Run patch optimization to view recommendations</p>
              )}
            </div>
          )}

          {activeTab === 'marl' && (
            <div className="tab-pane">
              <h3>Red vs Blue - MARL Arms Race</h3>
              {!['architect', 'demo', 'analyst', 'executive'].includes(effectiveRole) && (
                <p className="empty-state">Role configuration unavailable.</p>
              )}
              {marlResults ? (
                <div className="marl-results">
                  <p>MARL training results for {marlResults.rounds || 0} rounds</p>
                  <p className="result-detail">
                    Latest round: Red {(Number(marlResults.red_win_rate || 0) * 100).toFixed(1)}% vs Blue {(Number(marlResults.blue_win_rate || 0) * 100).toFixed(1)}%.
                    Average across rounds: Red {(Number(marlResults.red_win_rate_avg || 0) * 100).toFixed(1)}% vs Blue {(Number(marlResults.blue_win_rate_avg || 0) * 100).toFixed(1)}%.
                  </p>
                  {marlHistoryRows.length > 0 && (
                    <table className="results-table">
                      <thead>
                        <tr>
                          <th>Round</th>
                          <th>Red Win Rate</th>
                          <th>Blue Win Rate</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {marlHistoryRows.map((round, i) => (
                          <tr key={round.round ?? i}>
                            <td>Round {round.round ?? i + 1}</td>
                            <td>{(Number(round.red_win_rate || 0) * 100).toFixed(1)}%</td>
                            <td>{(Number(round.blue_win_rate || 0) * 100).toFixed(1)}%</td>
                            <td>{round.status || 'Completed'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              ) : (
                <p className="empty-state">MARL training results will appear here</p>
              )}
            </div>
          )}

          {activeTab === 'replay' && (
            <div className="tab-pane">
              <h3>Incident Replay Timeline</h3>
              {replayData?.steps ? (
                <ol className="timeline-list">
                  {replayData.steps.slice(0, 10).map((step, idx) => (
                    <li key={idx} className="timeline-item">
                      <strong>T+{idx}</strong>: {step.node_id} (P={(step.compromise_probability * 100).toFixed(1)}%)
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="empty-state">Run a scenario to view replay timeline</p>
              )}
            </div>
          )}
        </div>
          </section>
        </section>

        <aside className="analysis-activity-panel" aria-label="Recent activity">
          <h3>Recent Activity</h3>
          <ul className="activity-feed">
            {recentActivity.map((item, index) => (
              <li key={`${item.title}-${index}`} className="activity-item">
                <span className="activity-age">{item.age}</span>
                <strong>{item.title}</strong>
                <span>{item.detail}</span>
              </li>
            ))}
          </ul>

          <section className="connected-laptops-panel" aria-label="Connected laptops">
            <div className="connected-laptops-header">
              <h4>Connected Laptops</h4>
              <button
                onClick={() => refreshTelemetryStatus()}
                disabled={isRunning || isLiveIngestRunning || isSeedSweepRunning || !selectedTopology}
                className="connected-refresh-btn"
              >
                Refresh
              </button>
            </div>

            {connectedLaptops.length > 0 ? (
              <ul className="connected-laptops-list">
                {connectedLaptops.slice(0, 10).map((client) => (
                  <li key={client.node} className="connected-laptop-item">
                    <span className={`status-dot status-${client.status || 'unknown'}`} aria-hidden="true" />
                    <div className="connected-node-body">
                      <strong className="connected-node-name">{client.node}</strong>
                      <span className="connected-node-meta">
                        Events: {client.event_count || 0} · Blocked: {client.blocked_events || 0} · Critical: {client.critical_reaches || 0}
                      </span>
                    </div>
                    <span className="connected-node-seen">
                      {client.last_seen_at ? formatDateTime(client.last_seen_at) : 'No timestamp'}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="connected-empty">No laptop telemetry yet. Ingest live telemetry to populate this list.</p>
            )}
          </section>
        </aside>
      </div>

      {toastMessage && <div className={`toast toast-${toastMessage.type}`}>{toastMessage.text}</div>}
    </div>
  );
}
