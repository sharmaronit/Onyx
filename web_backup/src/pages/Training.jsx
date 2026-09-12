import { useState, useEffect } from 'react';
import { useResults } from '../contexts/ResultsContext';
import { useUser } from '../contexts/UserContext';
import {
  getMarlResults,
  getCostModels,
  createCostModel,
  activateCostModel,
  createTrainingJob,
  getTrainingJobStatus,
} from '../api';
import { getRoleCapabilities, getPermissionReason } from '../utils/rolePermissions';
import { formatRatioPercent, getMarlHistoryRows } from '../utils/presentation';
import { FEATURE_VISIBILITY } from '../config/featureVisibility';
import './Training.css';

const TRAINING_PIPELINE = [
  { key: 'setup', label: 'Stage 1: Setup Verification', jobType: 'BLUE', episodes: 250 },
  { key: 'data', label: 'Stage 2: Data Generation', jobType: 'RED', episodes: 1200 },
  { key: 'gnn', label: 'Stage 3: GNN World Model', jobType: 'BLUE', episodes: 2000 },
  { key: 'red', label: 'Stage 4: Red Agent Training', jobType: 'RED', episodes: 5000 },
  { key: 'blue', label: 'Stage 5: Blue Agent Training', jobType: 'BLUE', episodes: 5000 },
  { key: 'marl', label: 'Stage 6: MARL Self-Play', jobType: 'MARL', episodes: 10000 },
  { key: 'patch', label: 'Stage 7: Patch Optimization', jobType: 'BLUE', episodes: 1000 },
  { key: 'report', label: 'Stage 8: Report Generation', jobType: 'MARL', episodes: 500 },
];

const createPipelineStageState = () =>
  TRAINING_PIPELINE.map((stage) => ({
    ...stage,
    status: 'idle',
    jobId: null,
    detail: '',
  }));

export default function Training() {
  const { marlResults, loading, error, dispatch } = useResults();
  const { user } = useUser();
  const effectiveRole = FEATURE_VISIBILITY.enforcedRole || user?.role;
  const capabilities = getRoleCapabilities(effectiveRole);
  const [activeTab, setActiveTab] = useState('marl');
  const [costModels, setCostModels] = useState([]);
  const [trainingJobs, setTrainingJobs] = useState([]);
  const [pipelineStages, setPipelineStages] = useState(createPipelineStageState);
  const [newModelName, setNewModelName] = useState('');
  const [newModelDesc, setNewModelDesc] = useState('');
  const [queuedJobType, setQueuedJobType] = useState('MARL');
  const [queuedEpisodes, setQueuedEpisodes] = useState('1000');
  const [toastMessage, setToastMessage] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [trainingNotice, setTrainingNotice] = useState('');

  const marlHistoryRows = getMarlHistoryRows(marlResults);

  const normalizeTrainingJob = (job, fallbackType = 'MARL', fallbackEpisodes = 1000) => ({
    id: job?.id || job?.job_id || `${fallbackType.toLowerCase()}-${Date.now()}`,
    name: job?.name || job?.model_type || `${fallbackType} Training Job`,
    status: String(job?.status || 'queued').toLowerCase(),
    progress: Number.isFinite(Number(job?.progress))
      ? Number(job.progress)
      : Number.isFinite(Number(job?.progress_percent))
        ? Number(job.progress_percent)
        : 0,
    jobType: job?.jobType || job?.model_type || fallbackType,
    episodes: Number.isFinite(Number(job?.episodes)) ? Number(job.episodes) : fallbackEpisodes,
  });

  const showToast = (message, type = 'info') => {
    setToastMessage({ text: message, type });
    setTimeout(() => setToastMessage(null), 3000);
  };

  useEffect(() => {
    const loadTrainingData = async () => {
      const warnings = [];
      try {
        setIsLoading(true);
        setTrainingNotice('');
        
        // Load cost models if the tab is visible.
        if (FEATURE_VISIBILITY.showTrainingCostModelsTab) {
          try {
            const modelsData = await getCostModels(effectiveRole || 'default');
            setCostModels(modelsData.models || []);
          } catch (error) {
            setCostModels([]);
            warnings.push('cost models');
          }
        } else {
          setCostModels([]);
        }

        // Load MARL results
        try {
          const marlData = await getMarlResults();
          if (marlData) {
            dispatch({ type: 'SET_MARL_RESULTS', payload: marlData });
          }
        } catch (err) {
          console.error('MARL results unavailable:', err);
          warnings.push('MARL history');
        }

        // Load training jobs - for now, initialize empty
        setTrainingJobs([]);
      } catch (error) {
        console.error('Failed to load training data:', error);
        showToast('Failed to load training data', 'error');
        warnings.push('training data');
      } finally {
        if (warnings.length > 0) {
          setTrainingNotice(`Running in degraded mode: ${warnings.join(', ')} unavailable.`);
        }
        setIsLoading(false);
      }
    };

    loadTrainingData();
  }, [dispatch, effectiveRole]);

  const handleCreateCostModel = async () => {
    if (!capabilities.canManageCostModels) {
      showToast(getPermissionReason(user?.role, 'manageCostModels'), 'info');
      return;
    }

    if (!newModelName.trim()) {
      showToast('Please enter a model name', 'error');
      return;
    }

    try {
      setIsLoading(true);
      const result = await createCostModel(newModelName, newModelDesc, []);
      setCostModels([...costModels, result.model || result]);
      setNewModelName('');
      setNewModelDesc('');
      showToast('Cost model created successfully!', 'success');
    } catch (error) {
      showToast('Failed to create cost model: ' + error.message, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleActivateCostModel = async (modelId) => {
    if (!capabilities.canManageCostModels) {
      showToast(getPermissionReason(user?.role, 'manageCostModels'), 'info');
      return;
    }

    try {
      setIsLoading(true);
      await activateCostModel(modelId);
      setCostModels(costModels.map(m => ({
        ...m,
        active: m.id === modelId
      })));
      showToast('Cost model activated!', 'success');
    } catch (error) {
      showToast('Failed to activate cost model: ' + error.message, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleQueueTrainingJob = async (jobType) => {
    if (!capabilities.canQueueTrainingJob) {
      showToast(getPermissionReason(user?.role, 'queueTrainingJob'), 'info');
      return;
    }

    try {
      setIsLoading(true);
      const episodes = Math.max(1, Number.parseInt(queuedEpisodes, 10) || 1000);
      const result = await createTrainingJob(jobType, episodes);
      const normalizedJob = normalizeTrainingJob(result.job || result, jobType, episodes);
      setTrainingJobs((prev) => [...prev, normalizedJob]);
      showToast(`${jobType} training job queued!`, 'success');
    } catch (error) {
      showToast('Failed to queue training job: ' + error.message, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleQueuePipelineStage = async (stage) => {
    if (!capabilities.canQueueTrainingJob) {
      showToast(getPermissionReason(user?.role, 'queueTrainingJob'), 'info');
      return;
    }

    try {
      setIsLoading(true);
      const result = await createTrainingJob(stage.jobType, stage.episodes);
      const newJob = normalizeTrainingJob(result.job || result, stage.jobType, stage.episodes);
      setTrainingJobs((prev) => [...prev, newJob]);
      setPipelineStages((prev) =>
        prev.map((item) =>
          item.key === stage.key
            ? {
                ...item,
                status: newJob.status || 'queued',
                jobId: newJob.id || null,
                detail: `${stage.jobType} job queued (${stage.episodes} episodes)`,
              }
            : item,
        ),
      );
      showToast(`${stage.label} queued successfully.`, 'success');
    } catch (error) {
      setPipelineStages((prev) =>
        prev.map((item) =>
          item.key === stage.key
            ? { ...item, status: 'failed', detail: error.message }
            : item,
        ),
      );
      showToast(`Failed to queue ${stage.label}: ${error.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleQueueFullPipeline = async () => {
    if (!capabilities.canQueueTrainingJob) {
      showToast(getPermissionReason(user?.role, 'queueTrainingJob'), 'info');
      return;
    }

    for (const stage of TRAINING_PIPELINE) {
      // Queueing in sequence avoids flooding the API and provides stage-level feedback.
      // eslint-disable-next-line no-await-in-loop
      await handleQueuePipelineStage(stage);
    }
  };

  const handleRefreshPipelineStatus = async () => {
    const stagesWithJobs = pipelineStages.filter((stage) => stage.jobId);
    if (stagesWithJobs.length === 0) {
      showToast('No queued pipeline jobs yet.', 'info');
      return;
    }

    try {
      setIsLoading(true);
      const statusMap = {};

      for (const stage of stagesWithJobs) {
        // eslint-disable-next-line no-await-in-loop
        const status = await getTrainingJobStatus(stage.jobId);
        statusMap[stage.jobId] = status.job || status;
      }

      setPipelineStages((prev) =>
        prev.map((stage) => {
          if (!stage.jobId || !statusMap[stage.jobId]) {
            return stage;
          }
          const job = normalizeTrainingJob(statusMap[stage.jobId], stage.jobType, stage.episodes);
          return {
            ...stage,
            status: job.status || stage.status,
            detail: Number.isFinite(job.progress) ? `${job.progress}% complete` : stage.detail,
          };
        }),
      );

      setTrainingJobs((prev) =>
        prev.map((job) => {
          if (!job?.id || !statusMap[job.id]) {
            return job;
          }
          return { ...job, ...normalizeTrainingJob(statusMap[job.id], job.jobType, job.episodes) };
        }),
      );

      showToast('Pipeline status refreshed.', 'success');
    } catch (error) {
      showToast('Failed to refresh pipeline status: ' + error.message, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetPipeline = () => {
    setPipelineStages(createPipelineStageState());
    showToast('Pipeline tracker reset.', 'info');
  };

  return (
    <div className="training-page">
      {/* Tabs */}
      <div className="tabs-container">
        <div className="tabs-header">
          <button
            className={`tab-button ${activeTab === 'marl' ? 'active' : ''}`}
            onClick={() => setActiveTab('marl')}
          >
            MARL Arms Race
          </button>
          {FEATURE_VISIBILITY.showTrainingCostModelsTab && (
            <button
              className={`tab-button ${activeTab === 'costmodels' ? 'active' : ''}`}
              onClick={() => setActiveTab('costmodels')}
            >
              Cost Models
            </button>
          )}
          {FEATURE_VISIBILITY.showTrainingJobsTab && (
            <button
              className={`tab-button ${activeTab === 'jobs' ? 'active' : ''}`}
              onClick={() => setActiveTab('jobs')}
            >
              Training Jobs
            </button>
          )}
          {FEATURE_VISIBILITY.showTrainingJobsTab && (
            <button
              className={`tab-button ${activeTab === 'pipeline' ? 'active' : ''}`}
              onClick={() => setActiveTab('pipeline')}
            >
              Pipeline
            </button>
          )}
        </div>

        <div className="tab-content">
          {loading && <p className="training-hint">Refreshing shared analysis results...</p>}
          {error && <p className="training-warning">{error}</p>}
          {trainingNotice && <p className="training-warning">{trainingNotice}</p>}

          {/* MARL Results Tab */}
          {activeTab === 'marl' && (
            <div className="tab-pane">
              <h3>MARL Arms Race Results</h3>
              {marlResults ? (
                <div className="marl-container">
                  <div className="marl-info">
                    <p>
                      <strong>Status:</strong> Training in progress
                    </p>
                    <p>
                      <strong>Rounds Completed:</strong> {marlResults.rounds || 0}
                    </p>
                    <p>
                      <strong>Red Win Rate:</strong>{' '}
                      {formatRatioPercent(marlResults.red_win_rate)}
                    </p>
                    <p>
                      <strong>Blue Win Rate:</strong>{' '}
                      {formatRatioPercent(marlResults.blue_win_rate)}
                    </p>
                    <p>
                      <strong>Average Red Win Rate:</strong>{' '}
                      {formatRatioPercent(marlResults.red_win_rate_avg)}
                    </p>
                    <p>
                      <strong>Average Blue Win Rate:</strong>{' '}
                      {formatRatioPercent(marlResults.blue_win_rate_avg)}
                    </p>
                    <p>
                      Latest round: Red {formatRatioPercent(marlResults.red_win_rate)} vs Blue {formatRatioPercent(marlResults.blue_win_rate)}. Average across rounds: Red {formatRatioPercent(marlResults.red_win_rate_avg)} vs Blue {formatRatioPercent(marlResults.blue_win_rate_avg)}.
                    </p>
                  </div>
                  <div className="chart-placeholder">
                    <p><span className="mono-icon mono-icon-inline" aria-hidden="true">bar_chart</span>Training Convergence Chart</p>
                    <p className="muted">Multi-round training data visualization</p>
                  </div>
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
                        {marlHistoryRows.map((round, idx) => (
                          <tr key={round.round ?? idx}>
                            <td>Round {round.round ?? idx + 1}</td>
                            <td>{formatRatioPercent(round.red_win_rate)}</td>
                            <td>{formatRatioPercent(round.blue_win_rate)}</td>
                            <td>{round.status || 'Completed'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              ) : (
                <div className="empty-state">
                  <p>No MARL training results available yet.</p>
                  <p>Start a training job to see results.</p>
                </div>
              )}
            </div>
          )}

          {/* Cost Models Tab */}
          {FEATURE_VISIBILITY.showTrainingCostModelsTab && activeTab === 'costmodels' && (
            <div className="tab-pane">
              <h3>Cost Models</h3>
              {!capabilities.canManageCostModels && (
                <p className="empty-state">{getPermissionReason(user?.role, 'manageCostModels')}</p>
              )}
              <div className="cost-models-container">
                <div className="models-list">
                  {costModels.length > 0 ? (
                    costModels.map((model) => (
                      <div key={model.id} className={`model-card ${model.active ? 'active' : ''}`}>
                        <div className="model-header">
                          <h4>{model.name}</h4>
                          <span className={`badge ${model.active ? 'badge-active' : 'badge-inactive'}`}>
                            {model.active ? 'Active' : 'Inactive'}
                          </span>
                        </div>
                        <p className="model-info">
                          <strong>{model.patches?.length || model.patches || 0}</strong> patches configured
                        </p>
                        <div className="model-actions">
                          <button disabled={isLoading} className="btn btn-small">Edit</button>
                          <button
                            disabled={isLoading || model.active || !capabilities.canManageCostModels}
                            onClick={() => handleActivateCostModel(model.id)}
                            className="btn btn-small"
                            title={!capabilities.canManageCostModels ? getPermissionReason(user?.role, 'manageCostModels') : ''}
                          >
                            {model.active ? 'Active' : 'Activate'}
                          </button>
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="empty-state">No cost models configured</p>
                  )}
                </div>

                <div className="add-model-form">
                  <h4>Create New Cost Model</h4>
                  <div className="form-group">
                    <label>Model Name:</label>
                    <input
                      type="text"
                      placeholder="Enter model name"
                      value={newModelName}
                      onChange={(e) => setNewModelName(e.target.value)}
                      className="form-input"
                      disabled={isLoading || !capabilities.canManageCostModels}
                    />
                  </div>
                  <div className="form-group">
                    <label>Description:</label>
                    <textarea
                      placeholder="Enter description"
                      value={newModelDesc}
                      onChange={(e) => setNewModelDesc(e.target.value)}
                      className="form-input"
                      rows="3"
                      disabled={isLoading || !capabilities.canManageCostModels}
                    ></textarea>
                  </div>
                  <button
                    onClick={handleCreateCostModel}
                    disabled={isLoading || !capabilities.canManageCostModels}
                    className="btn btn-primary"
                    title={!capabilities.canManageCostModels ? getPermissionReason(user?.role, 'manageCostModels') : ''}
                  >
                    {isLoading ? 'Creating...' : 'Create Model'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Training Jobs Tab */}
          {FEATURE_VISIBILITY.showTrainingJobsTab && activeTab === 'jobs' && (
            <div className="tab-pane">
              <h3>Training Jobs</h3>
              {!capabilities.canQueueTrainingJob && (
                <p className="empty-state">{getPermissionReason(user?.role, 'queueTrainingJob')}</p>
              )}
              <div className="jobs-container">
                {trainingJobs.length > 0 ? (
                  <div className="jobs-list">
                    {trainingJobs.map((job) => (
                      <div key={job.id} className={`job-card job-${String(job.status || 'queued')}`}>
                        <div className="job-header">
                          <h4>{job.name}</h4>
                          <span className={`status-badge status-${String(job.status || 'queued')}`}>
                            {String(job.status || 'queued').charAt(0).toUpperCase() + String(job.status || 'queued').slice(1)}
                          </span>
                        </div>
                        <div className="progress-bar">
                          <div
                            className="progress-fill"
                            style={{ width: `${Number.isFinite(Number(job.progress)) ? Number(job.progress) : 0}%` }}
                          ></div>
                        </div>
                        <p className="progress-text">{Number.isFinite(Number(job.progress)) ? Number(job.progress) : 0}% Complete</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-state">
                    <p>No training jobs scheduled</p>
                  </div>
                )}

                <div className="queue-controls">
                  <h4>Queue New Training</h4>
                  <div className="form-group">
                    <label>Job Type:</label>
                    <select
                      value={queuedJobType}
                      onChange={(e) => setQueuedJobType(e.target.value)}
                      className="form-input"
                      disabled={isLoading || !capabilities.canQueueTrainingJob}
                    >
                      <option value="MARL">MARL Training Round</option>
                      <option value="BLUE">Blue Policy Training</option>
                      <option value="RED">Red Policy Training</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Episodes:</label>
                    <input
                      type="number"
                      min="1"
                      value={queuedEpisodes}
                      onChange={(e) => setQueuedEpisodes(e.target.value)}
                      className="form-input"
                      disabled={isLoading || !capabilities.canQueueTrainingJob}
                    />
                  </div>
                  <button
                    onClick={() => handleQueueTrainingJob(queuedJobType)}
                    disabled={isLoading || !capabilities.canQueueTrainingJob}
                    className="btn btn-primary"
                    title={!capabilities.canQueueTrainingJob ? getPermissionReason(user?.role, 'queueTrainingJob') : ''}
                  >
                    {isLoading ? 'Queuing...' : 'Queue Job'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {FEATURE_VISIBILITY.showTrainingJobsTab && activeTab === 'pipeline' && (
            <div className="tab-pane">
              <h3>End-to-End Training Pipeline</h3>
              {!capabilities.canQueueTrainingJob && (
                <p className="empty-state">{getPermissionReason(user?.role, 'queueTrainingJob')}</p>
              )}

              <div className="pipeline-actions">
                <button
                  onClick={handleQueueFullPipeline}
                  disabled={isLoading || !capabilities.canQueueTrainingJob}
                  className="btn btn-primary"
                  title={!capabilities.canQueueTrainingJob ? getPermissionReason(user?.role, 'queueTrainingJob') : ''}
                >
                  {isLoading ? 'Queuing...' : 'Queue Full 8-Stage Pipeline'}
                </button>
                <button
                  onClick={handleRefreshPipelineStatus}
                  disabled={isLoading}
                  className="btn btn-secondary"
                >
                  Refresh Status
                </button>
                <button
                  onClick={handleResetPipeline}
                  disabled={isLoading}
                  className="btn btn-secondary"
                >
                  Reset Tracker
                </button>
              </div>

              <div className="pipeline-grid">
                {pipelineStages.map((stage) => (
                  <div key={stage.key} className={`pipeline-card pipeline-${stage.status}`}>
                    <div className="pipeline-head">
                      <h4>{stage.label}</h4>
                      <span className={`status-badge status-${stage.status || 'queued'}`}>
                        {(stage.status || 'idle').toUpperCase()}
                      </span>
                    </div>
                    <p className="pipeline-meta">
                      Job type: {stage.jobType} • Episodes: {stage.episodes}
                    </p>
                    <p className="pipeline-detail">{stage.detail || 'Not queued yet.'}</p>
                    <button
                      onClick={() => handleQueuePipelineStage(stage)}
                      disabled={isLoading || !capabilities.canQueueTrainingJob}
                      className="btn btn-small"
                      title={!capabilities.canQueueTrainingJob ? getPermissionReason(user?.role, 'queueTrainingJob') : ''}
                    >
                      Queue Stage
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Toast Notifications */}
      {toastMessage && (
        <div className={`toast toast-${toastMessage.type}`}>
          {toastMessage.text}
        </div>
      )}
    </div>
  );
}
