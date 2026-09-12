import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useResults } from '../contexts/ResultsContext';
import { useUser } from '../contexts/UserContext';
import { generateReport, getReportHtml, getReportHistory } from '../api';
import {
  formatPercentValue,
  formatRatioPercent,
  getConfidenceKey,
  getConfidenceLabel,
  getSourceLabel,
  toPercentNumber,
} from '../utils/presentation';
import { FEATURE_VISIBILITY } from '../config/featureVisibility';
import './Reports.css';

const SNAPSHOT_ARTIFACTS_KEY = 'onyx_reports_dashboard_snapshots_v1';

const readDashboardSnapshotArtifacts = () => {
  if (typeof window === 'undefined') {
    return [];
  }
  try {
    const raw = window.localStorage.getItem(SNAPSHOT_ARTIFACTS_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter((item) => item && typeof item === 'object');
  } catch {
    return [];
  }
};

const mergeSnapshotArtifacts = (baseReports) => {
  const existing = Array.isArray(baseReports) ? baseReports : [];
  const artifacts = readDashboardSnapshotArtifacts();
  const existingIds = new Set(existing.map((report) => report.id));
  const artifactReports = artifacts.filter((artifact) => artifact.id && !existingIds.has(artifact.id));
  return [...artifactReports, ...existing];
};

export default function Reports() {
  const location = useLocation();
  const { simulationResults } = useResults();
  const { user } = useUser();
  const [activeTab, setActiveTab] = useState('list');
  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [focusedArtifactId, setFocusedArtifactId] = useState('');
  const [exportOptions, setExportOptions] = useState({
    includeSimulationData: true,
    includeAttackPaths: true,
    includeRawMetrics: false,
  });

  const showToast = (message, type = 'info') => {
    setToastMessage({ text: message, type });
    setTimeout(() => setToastMessage(null), 3000);
  };

  useEffect(() => {
    const loadReports = async () => {
      try {
        setIsLoading(true);
        const data = await getReportHistory(user?.role || 'default');
        setReports(mergeSnapshotArtifacts(data.reports || []));
      } catch (error) {
        console.error('Failed to load reports:', error);
        // Fallback to default reports on error
        setReports(mergeSnapshotArtifacts([
          {
            id: 1,
            name: 'Enterprise Ransomware Scenario',
            topology: 'enterprise_20n',
            successRate: 99.5,
            created: 'Apr 4, 2026',
            dataSource: 'simulation',
            confidence: 'estimated',
          },
          {
            id: 2,
            name: 'Cloud Pivot Attack Analysis',
            topology: 'cloud_hybrid_30n',
            successRate: 87.3,
            created: 'Apr 3, 2026',
            dataSource: 'simulation',
            confidence: 'estimated',
          },
          {
            id: 3,
            name: 'Small Office Quick Demo',
            topology: 'small_office_10n',
            successRate: 92.1,
            created: 'Apr 2, 2026',
            dataSource: 'simulation',
            confidence: 'estimated',
          },
        ]));
      } finally {
        setIsLoading(false);
      }
    };
    loadReports();
  }, [user]);

  useEffect(() => {
    if (!location.state?.focusReportId || !reports.length) {
      return;
    }

    const reportId = location.state.focusReportId;
    if (reportId === focusedArtifactId) {
      return;
    }

    const target = reports.find((report) => report.id === reportId);
    if (target) {
      setFocusedArtifactId(reportId);
      if (location.state.openTab) {
        setActiveTab(location.state.openTab);
      }
      setSelectedReport(target);
      showToast('Dashboard snapshot added to Report List.', 'success');
    }
  }, [location.state, reports, focusedArtifactId]);

  const handleGenerateReport = async () => {
    if (!simulationResults) {
      showToast('No simulation results to generate report from', 'error');
      return;
    }

    try {
      setIsLoading(true);
      const reportData = await generateReport('enterprise_20n');
      const successRate = formatRatioPercent(simulationResults.success_rate);
      
      const newReport = {
        id: reports.length + 1,
        name: `Report from ${new Date().toLocaleString()}`,
        topology: 'generated',
        date: new Date().toISOString().split('T')[0],
        successRate: successRate,
        created: new Date().toLocaleDateString(),
        dataSource: simulationResults.data_source || simulationResults.requested_data_source || 'simulation',
        confidence: getConfidenceKey(simulationResults),
        dataFreshnessAt: simulationResults.data_freshness_at,
        ...reportData,
      };
      setReports([newReport, ...reports]);
      setSelectedReport(newReport);
      setActiveTab('viewer');
      showToast('Report generated successfully!', 'success');
    } catch (error) {
      showToast('Failed to generate report: ' + error.message, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownloadPDF = async () => {
    try {
      setIsLoading(true);
      const htmlContent = await getReportHtml();
      // Create a simple modal or download PDF
      showToast('PDF download initiated (feature in development)', 'info');
    } catch (error) {
      showToast('Failed to download PDF: ' + error.message, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleExportCSV = () => {
    try {
      const headers = ['Report', 'Topology', 'Success Rate', 'Date'];
      const rows = reports.map((r) => [r.name, r.topology, formatPercentValue(r.successRate), r.created]);
      const csv = [headers, ...rows].map((r) => r.join(',')).join('\n');
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `reports-${new Date().toISOString().split('T')[0]}.csv`;
      a.click();
      showToast('CSV exported successfully!', 'success');
    } catch (error) {
      showToast('Failed to export CSV: ' + error.message, 'error');
    }
  };

  const handleExportJSON = () => {
    try {
      const payload = {
        generatedAt: new Date().toISOString(),
        options: exportOptions,
        reports,
      };
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `reports-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      showToast('JSON exported successfully!', 'success');
    } catch (error) {
      showToast('Failed to export JSON: ' + error.message, 'error');
    }
  };

  const handleExportPDFBundle = async () => {
    try {
      setIsLoading(true);
      await getReportHtml();
      window.print();
      showToast('PDF bundle export opened in print dialog.', 'success');
    } catch (error) {
      showToast('Failed to export PDF bundle: ' + error.message, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCustomExport = () => {
    try {
      const filteredReports = reports.map((report) => {
        const next = { ...report };
        if (!exportOptions.includeSimulationData) {
          delete next.dataSource;
          delete next.confidence;
          delete next.dataFreshnessAt;
        }
        if (!exportOptions.includeAttackPaths) {
          delete next.top_paths;
        }
        if (!exportOptions.includeRawMetrics) {
          delete next.raw_metrics;
          delete next.metrics;
        }
        return next;
      });

      const blob = new Blob([JSON.stringify(filteredReports, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `reports-custom-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      showToast('Custom export completed.', 'success');
    } catch (error) {
      showToast('Custom export failed: ' + error.message, 'error');
    }
  };

  return (
    <div className="reports-page">
      {/* Tabs */}
      <div className="tabs-container">
        <div className="tabs-header">
          <button
            className={`tab-button ${activeTab === 'list' ? 'active' : ''}`}
            onClick={() => setActiveTab('list')}
          >
            Report List
          </button>
          <button
            className={`tab-button ${activeTab === 'viewer' ? 'active' : ''}`}
            onClick={() => setActiveTab('viewer')}
          >
            Viewer
          </button>
          {FEATURE_VISIBILITY.showReportsExportTab && (
            <button
              className={`tab-button ${activeTab === 'export' ? 'active' : ''}`}
              onClick={() => setActiveTab('export')}
            >
              Export
            </button>
          )}
        </div>

        <div className="tab-content">
          {/* Report List Tab */}
          {activeTab === 'list' && (
            <div className="tab-pane">
              <h3>Generated Reports</h3>

              <div className="list-controls">
                <button
                  onClick={handleGenerateReport}
                  disabled={!simulationResults || isLoading}
                  className="btn btn-primary"
                >
                  {isLoading ? 'Generating...' : simulationResults ? '+ Generate New Report' : 'Run Simulation First'}
                </button>
              </div>

              <div className="reports-table">
                {reports.length > 0 ? (
                  <div className="table-wrapper">
                    <table>
                      <thead>
                        <tr>
                          <th>Report Name</th>
                          <th>Topology</th>
                          <th>Success Rate</th>
                          <th>Source</th>
                          <th>Confidence</th>
                          <th>Created</th>
                          <th>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {reports.map((report) => (
                          <tr key={report.id} className="table-row">
                            <td className="name">
                              {report.name}
                              {report.artifactType === 'dashboard_snapshot' && (
                                <span className="report-tag">Snapshot</span>
                              )}
                            </td>
                            <td>
                              <span className="topology-badge">{report.topology}</span>
                            </td>
                            <td>
                              <span className="rate-badge">{formatPercentValue(report.successRate)}</span>
                            </td>
                            <td>
                              <span className={`source-chip source-${report.dataSource || 'simulation'}`}>
                                {getSourceLabel(report.dataSource)}
                              </span>
                            </td>
                            <td>
                              <span className={`confidence-chip confidence-${report.confidence || 'estimated'}`}>
                                {getConfidenceLabel(report.confidence)}
                              </span>
                            </td>
                            <td className="date">{report.created}</td>
                            <td className="actions">
                              <button
                                onClick={() => {
                                  setSelectedReport(report);
                                  setActiveTab('viewer');
                                }}
                                className="btn btn-small"
                              >
                                View
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="empty-state">
                    <p>No reports generated yet</p>
                    <p>Run a simulation and generate a report</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Report Viewer Tab */}
          {activeTab === 'viewer' && (
            <div className="tab-pane">
              <h3>Report Viewer</h3>

              {selectedReport ? (
                <div className="viewer-container">
                  <div className="report-header">
                    <h4>{selectedReport.name}</h4>
                    <div className="header-info">
                      <span>Topology: {selectedReport.topology}</span>
                      <span>Success Rate: {formatPercentValue(selectedReport.successRate)}</span>
                      <span>Source: {getSourceLabel(selectedReport.dataSource)}</span>
                      <span>Confidence: {getConfidenceLabel(selectedReport.confidence)}</span>
                      <span>Date: {selectedReport.created}</span>
                    </div>
                  </div>

                  <div className="report-content">
                    <div className="report-section">
                      <h5>Executive Summary</h5>
                      <p>
                        This report analyzes the security posture of your network based on <br />
                        {formatPercentValue(selectedReport.successRate)} attack success rate across multiple attack scenarios.
                      </p>
                      {selectedReport.summary?.takeaway && (
                        <div className="summary-callout">
                          <strong>{selectedReport.summary.takeaway}</strong>
                          {Array.isArray(selectedReport.summary.bullets) && selectedReport.summary.bullets.length > 0 && (
                            <ul className="summary-bullets">
                              {selectedReport.summary.bullets.map((bullet) => (
                                <li key={bullet}>{bullet}</li>
                              ))}
                            </ul>
                          )}
                        </div>
                      )}
                      <p className="transparency-note">
                        Metric confidence: <strong>{getConfidenceLabel(selectedReport.confidence)}</strong>. Source:
                        {' '}
                        <strong>{getSourceLabel(selectedReport.dataSource)}</strong>.
                        {selectedReport.summary?.note && <> {selectedReport.summary.note}</>}
                        {selectedReport.confidence === 'estimated' && (
                          <> This value is model-estimated and should be validated with live telemetry when available.</>
                        )}
                        {selectedReport.confidence === 'hybrid' && (
                          <> This value blends telemetry and simulation for faster but transparent decision support.</>
                        )}
                        {selectedReport.confidence === 'measured' && (
                          <> This value is derived from telemetry-backed measurements.</>
                        )}
                      </p>
                    </div>

                    <div className="report-section">
                      <h5>Key Findings</h5>
                      <ul>
                        <li>Critical vulnerabilities identified in{' ' + selectedReport.topology}</li>
                        <li>Attack path length averaging 5-7 hops</li>
                        <li>
                          Lateral movement detected in {Math.round((toPercentNumber(selectedReport.successRate) || 0) / 10)} asset groups
                        </li>
                        <li>Recommended patch prioritization strategy</li>
                      </ul>
                    </div>

                    <div className="report-section">
                      <h5>Recommendations</h5>
                      <ol>
                        <li>Implement network segmentation</li>
                        <li>Deploy advanced threat detection</li>
                        <li>Create incident response procedures</li>
                        <li>Schedule regular penetration testing</li>
                      </ol>
                    </div>
                  </div>

                  <div className="viewer-actions">
                    {FEATURE_VISIBILITY.showDownloadPdfButton && (
                      <button
                        onClick={handleDownloadPDF}
                        disabled={isLoading}
                        className="btn btn-primary"
                      >
                        {isLoading ? (
                          <>
                            <span className="mono-icon mono-icon-inline" aria-hidden="true">progress_activity</span>
                            Downloading...
                          </>
                        ) : (
                          <>
                            <span className="mono-icon mono-icon-inline" aria-hidden="true">download</span>
                            Download PDF
                          </>
                        )}
                      </button>
                    )}
                    <button
                      onClick={() => window.print()}
                      disabled={isLoading}
                      className="btn btn-secondary"
                    >
                      <span className="mono-icon mono-icon-inline" aria-hidden="true">print</span>
                      Print
                    </button>
                  </div>
                </div>
              ) : (
                <div className="empty-state">
                  <p>Select a report to view</p>
                </div>
              )}
            </div>
          )}

          {/* Export Tab */}
          {FEATURE_VISIBILITY.showReportsExportTab && activeTab === 'export' && (
            <div className="tab-pane">
              <h3>Export Options</h3>

              <div className="export-container">
                <div className="export-section">
                  <h4>Export Selected Reports</h4>
                  <p>Choose format to export report data:</p>

                  <div className="export-options">
                    <div className="export-option">
                      <div className="option-icon"><span className="mono-icon" aria-hidden="true">description</span></div>
                      <h5>CSV Format</h5>
                      <p>Spreadsheet-compatible format</p>
                      <button
                        onClick={handleExportCSV}
                        disabled={isLoading || reports.length === 0}
                        className="btn btn-primary"
                      >
                        {isLoading ? 'Exporting...' : 'Export CSV'}
                      </button>
                    </div>

                    <div className="export-option">
                      <div className="option-icon"><span className="mono-icon" aria-hidden="true">analytics</span></div>
                      <h5>JSON Format</h5>
                      <p>Machine-readable structured data</p>
                      <button
                        onClick={handleExportJSON}
                        disabled={isLoading || reports.length === 0}
                        className="btn btn-primary"
                      >
                        {isLoading ? 'Exporting...' : 'Export JSON'}
                      </button>
                    </div>

                    <div className="export-option">
                      <div className="option-icon"><span className="mono-icon" aria-hidden="true">assignment</span></div>
                      <h5>PDF Bundle</h5>
                      <p>All reports as single PDF</p>
                      <button
                        onClick={handleExportPDFBundle}
                        disabled={isLoading || reports.length === 0}
                        className="btn btn-primary"
                      >
                        {isLoading ? 'Preparing...' : 'Export PDF'}
                      </button>
                    </div>
                  </div>
                </div>

                <div className="export-section">
                  <h4>Advanced Export</h4>
                  <div className="form-group">
                    <label>
                      <input
                        type="checkbox"
                        checked={exportOptions.includeSimulationData}
                        onChange={(e) =>
                          setExportOptions((prev) => ({ ...prev, includeSimulationData: e.target.checked }))
                        }
                      />{' '}
                      Include simulation data
                    </label>
                    <label>
                      <input
                        type="checkbox"
                        checked={exportOptions.includeAttackPaths}
                        onChange={(e) =>
                          setExportOptions((prev) => ({ ...prev, includeAttackPaths: e.target.checked }))
                        }
                      />{' '}
                      Include attack paths
                    </label>
                    <label>
                      <input
                        type="checkbox"
                        checked={exportOptions.includeRawMetrics}
                        onChange={(e) =>
                          setExportOptions((prev) => ({ ...prev, includeRawMetrics: e.target.checked }))
                        }
                      />{' '}
                      Include raw metrics
                    </label>
                  </div>
                  <button
                    onClick={handleCustomExport}
                    disabled={isLoading || reports.length === 0}
                    className="btn btn-primary"
                  >
                    {isLoading ? 'Exporting...' : 'Custom Export'}
                  </button>
                </div>
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
