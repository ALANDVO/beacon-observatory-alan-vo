// frontend/src/components/AnalysisDashboard.tsx
/** Hook Effectiveness Analysis Dashboard component. */
import { useState, useEffect, useCallback } from "react";
import { apiClient } from "../api/client";
import type {
  AnalysisJobResponse,
  AnalysisJobListResponse,
  EffectivenessReportResponse,
  LogSource,
} from "../types/api";

interface AnalysisDashboardProps {
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export function AnalysisDashboard({ autoRefresh = false, refreshInterval = 30000 }: AnalysisDashboardProps) {
  const [jobs, setJobs] = useState<AnalysisJobResponse[]>([]);
  const [selectedJob, setSelectedJob] = useState<AnalysisJobResponse | null>(null);
  const [report, setReport] = useState<EffectivenessReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creatingJob, setCreatingJob] = useState(false);
  const [newJobName, setNewJobName] = useState("");
  const [newJobDescription, setNewJobDescription] = useState("");

  const fetchJobs = useCallback(async () => {
    try {
      setError(null);
      const response: AnalysisJobListResponse = await apiClient.listAnalysisJobs(1, 50);
      setJobs(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch analysis jobs");
    }
  }, []);

  const fetchReport = useCallback(async (jobId: number) => {
    try {
      setError(null);
      const reportData: EffectivenessReportResponse = await apiClient.getEffectivenessReport(jobId);
      setReport(reportData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch effectiveness report");
    }
  }, []);

  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newJobName.trim()) return;

    setCreatingJob(true);
    try {
      setError(null);
      const job = await apiClient.createAnalysisJob({
        name: newJobName.trim(),
        description: newJobDescription.trim() || undefined,
      });
      setJobs((prev) => [job, ...prev]);
      setNewJobName("");
      setNewJobDescription("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create analysis job");
    } finally {
      setCreatingJob(false);
    }
  };

  const handleRunJob = async (jobId: number) => {
    try {
      setError(null);
      const updatedJob = await apiClient.runAnalysisJob(jobId);
      setJobs((prev) => prev.map((j) => (j.id === jobId ? updatedJob : j)));
      if (selectedJob?.id === jobId) {
        setSelectedJob(updatedJob);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run analysis job");
    }
  };

  const handleSelectJob = (job: AnalysisJobResponse) => {
    setSelectedJob(job);
    if (job.status === "completed") {
      fetchReport(job.id);
    } else {
      setReport(null);
    }
  };

  const handleDeleteJob = async (jobId: number) => {
    if (!window.confirm("Delete this analysis job and its results?")) return;

    try {
      setError(null);
      await apiClient.deleteAnalysisJob(jobId);
      setJobs((prev) => prev.filter((j) => j.id !== jobId));
      if (selectedJob?.id === jobId) {
        setSelectedJob(null);
        setReport(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete analysis job");
    }
  };

  const handleRefresh = () => {
    fetchJobs();
    if (selectedJob) {
      const freshJob = jobs.find((j) => j.id === selectedJob.id);
      if (freshJob) {
        setSelectedJob(freshJob);
        if (freshJob.status === "completed") {
          fetchReport(freshJob.id);
        }
      }
    }
  };

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(handleRefresh, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, handleRefresh]);

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "\u2014";
    return new Date(dateStr).toLocaleString();
  };

  const formatRate = (rate: number) => `${(rate * 100).toFixed(1)}%`;

  const formatOpensPer100 = (value: number) => value.toFixed(2);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "status-completed";
      case "running":
        return "status-running";
      case "pending":
        return "status-pending";
      case "failed":
        return "status-failed";
      default:
        return "";
    }
  };

  const getSourceColor = (source: LogSource) => {
    const colors: Record<LogSource, string> = {
      "claude-code": "source-claude",
      codex: "source-codex",
      copilot: "source-copilot",
      pi: "source-pi",
      opencode: "source-opencode",
      gemini: "source-gemini",
      "prime-agent": "source-prime",
    };
    return colors[source] || "";
  };

  return (
    <div className="analysis-dashboard">
      <div className="dashboard-header">
        <h2>Hook Effectiveness Analyzer</h2>
        <p className="dashboard-description">
          Analyze session logs to measure hook reach and follow-through rates across agent types.
        </p>
      </div>

      {error && <div className="error-banner" role="alert">{error}</div>}

      <section className="dashboard-section jobs-section" aria-labelledby="jobs-heading">
        <div className="section-header">
          <h3 id="jobs-heading">Analysis Jobs</h3>
          <button className="btn btn-secondary" onClick={handleRefresh}>
            Refresh
          </button>
        </div>

        <form className="create-job-form" onSubmit={handleCreateJob}>
          <div className="form-row">
            <input
              type="text"
              placeholder="Job name (required)"
              value={newJobName}
              onChange={(e) => setNewJobName(e.target.value)}
              required
              disabled={creatingJob}
            />
            <input
              type="text"
              placeholder="Description (optional)"
              value={newJobDescription}
              onChange={(e) => setNewJobDescription(e.target.value)}
              disabled={creatingJob}
            />
            <button type="submit" className="btn btn-primary" disabled={creatingJob || !newJobName.trim()}>
              {creatingJob ? "Creating\u2026" : "Create Job"}
            </button>
          </div>
        </form>

        {jobs.length === 0 ? (
          <p className="empty-state">No analysis jobs yet. Create one above to get started.</p>
        ) : (
          <div className="jobs-list" role="list">
            {jobs.map((job) => (
              <article
                key={job.id}
                className={`job-card ${selectedJob?.id === job.id ? "selected" : ""}`}
                role="listitem"
                onClick={() => handleSelectJob(job)}
              >
                <div className="job-header">
                  <h4>{job.name}</h4>
                  <span className={`status-badge ${getStatusColor(job.status)}`}>{job.status}</span>
                </div>
                <div className="job-meta">
                  <span>Created: {formatDate(job.created_at)}</span>
                  {job.started_at && <span>Started: {formatDate(job.started_at)}</span>}
                  {job.completed_at && <span>Completed: {formatDate(job.completed_at)}</span>}
                  <span>Progress: {Math.round(job.progress * 100)}% ({job.processed_logs}/{job.total_logs} logs)</span>
                </div>
                {job.description && <p className="job-description">{job.description}</p>}
                <div className="job-actions">
                  {job.status === "pending" && (
                    <button className="btn btn-small btn-primary" onClick={(e) => { e.stopPropagation(); handleRunJob(job.id); }}>
                      Run Analysis
                    </button>
                  )}
                  {job.status === "running" && <span className="running-indicator">Running\u2026</span>}
                  {job.status === "completed" && (
                    <button className="btn btn-small btn-secondary" onClick={(e) => { e.stopPropagation(); handleSelectJob(job); }}>
                      View Report
                    </button>
                  )}
                  <button
                    className="btn btn-small btn-danger"
                    onClick={(e) => { e.stopPropagation(); handleDeleteJob(job.id); }}
                    disabled={job.status === "running"}
                  >
                    Delete
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      {selectedJob && (
        <section className="dashboard-section report-section" aria-labelledby="report-heading">
          <div className="section-header">
            <h3 id="report-heading">Effectiveness Report: {selectedJob.name}</h3>
            <button className="btn btn-secondary" onClick={() => setSelectedJob(null)}>
              Close
            </button>
          </div>

          {report ? (
            <div className="report-content">
              <div className="report-summary">
                <h4>Summary</h4>
                <pre>{JSON.stringify(report.summary, null, 2)}</pre>
              </div>

              <div className="report-results">
                <h4>Results by Source &amp; Session Type</h4>
                {report.results.length === 0 ? (
                  <p className="empty-state">No results available.</p>
                ) : (
                  <div className="results-table-container">
                    <table className="results-table">
                      <thead>
                        <tr>
                          <th>Source</th>
                          <th>Session Type</th>
                          <th>Total Sessions</th>
                          <th>Hook Reach</th>
                          <th>Router Open</th>
                          <th>Playbook Open</th>
                          <th>Principle Open</th>
                          <th>Opens / 100 Prompts</th>
                        </tr>
                      </thead>
                      <tbody>
                        {report.results.map((result) => (
                          <tr key={result.id}>
                            <td>
                              <span className={`source-badge ${getSourceColor(result.source)}`}>
                                {result.source}
                              </span>
                            </td>
                            <td><span className="session-type-badge">{result.session_type}</span></td>
                            <td>{result.total_sessions}</td>
                            <td>{formatRate(result.hook_reach_rate)}</td>
                            <td>{formatRate(result.router_open_rate)}</td>
                            <td>{formatRate(result.playbook_open_rate)}</td>
                            <td>{formatRate(result.principle_open_rate)}</td>
                            <td className="opens-per-100">{formatOpensPer100(result.opens_per_100_prompts)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              <div className="report-export">
                <h4>Export</h4>
                <div className="export-buttons">
                  <button
                    className="btn btn-secondary"
                    onClick={() => {
                      const json = JSON.stringify(report, null, 2);
                      const blob = new Blob([json], { type: "application/json" });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement("a");
                      a.href = url;
                      a.download = `effectiveness-report-${selectedJob.id}.json`;
                      a.click();
                      URL.revokeObjectURL(url);
                    }}
                  >
                    Download JSON
                  </button>
                  <button
                    className="btn btn-secondary"
                    onClick={() => {
                      const headers = [
                        "Source",
                        "Session Type",
                        "Total Sessions",
                        "Hook Reach Rate",
                        "Router Open Rate",
                        "Playbook Open Rate",
                        "Principle Open Rate",
                        "Opens per 100 Prompts",
                      ];
                      const rows = report.results.map((r) => [
                        r.source,
                        r.session_type,
                        r.total_sessions,
                        formatRate(r.hook_reach_rate),
                        formatRate(r.router_open_rate),
                        formatRate(r.playbook_open_rate),
                        formatRate(r.principle_open_rate),
                        formatOpensPer100(r.opens_per_100_prompts),
                      ]);
                      const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
                      const blob = new Blob([csv], { type: "text/csv" });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement("a");
                      a.href = url;
                      a.download = `effectiveness-report-${selectedJob.id}.csv`;
                      a.click();
                      URL.revokeObjectURL(url);
                    }}
                  >
                    Download CSV
                  </button>
                </div>
              </div>
            </div>
          ) : selectedJob.status === "completed" ? (
            <div className="loading-report">Loading report\u2026</div>
          ) : (
            <div className="report-pending">
              <p>Job status: <strong>{selectedJob.status}</strong></p>
              <p>Run the analysis job to generate a report.</p>
              {selectedJob.status === "pending" && (
                <button className="btn btn-primary" onClick={() => handleRunJob(selectedJob.id)}>
                  Run Analysis
                </button>
              )}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

export default AnalysisDashboard;
