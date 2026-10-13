// frontend/src/components/HealthStatus.tsx
/** Health status display component. */
import { useEffect, useState } from "react";
import apiClient from "../api/client";
import type { HealthResponse, DetailedHealthResponse } from "../types/api";

interface HealthStatusProps {
  detailed?: boolean;
}

export function HealthStatus({ detailed = false }: HealthStatusProps) {
  const [health, setHealth] = useState<HealthResponse | DetailedHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = detailed
        ? await apiClient.getDetailedHealth()
        : await apiClient.getHealth();
      setHealth(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch health");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30_000);
    return () => clearInterval(interval);
  }, [detailed]);

  if (loading && !health) {
    return (
      <div className="health-status loading" role="status" aria-live="polite">
        <span className="spinner" aria-hidden="true"></span>
        <span>Checking backend health...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="health-status error" role="alert">
        <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <circle cx="12" cy="12" r="10" />
          <line x1="15" y1="9" x2="9" y2="15" />
          <line x1="9" y1="9" x2="15" y2="15" />
        </svg>
        <span>Health check failed: {error}</span>
        <button onClick={fetchHealth} className="retry-btn">
          Retry
        </button>
      </div>
    );
  }

  if (!health) {
    return null;
  }

  const isHealthy = health.status === "healthy";
  const statusClass = isHealthy ? "healthy" : "degraded";

  return (
    <div className={`health-status ${statusClass}`} role="region" aria-label="Backend health status">
      <div className="health-header">
        <svg className={`icon status-icon ${statusClass}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          {isHealthy ? (
            <>
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </>
          ) : (
            <>
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </>
          )}
        </svg>
        <div className="health-title">
          <strong>{isHealthy ? "Healthy" : "Degraded"}</strong>
          <small>Backend API</small>
        </div>
      </div>

      <dl className="health-details">
        <div className="detail-row">
          <dt>Version</dt>
          <dd>{health.version}</dd>
        </div>
        <div className="detail-row">
          <dt>Environment</dt>
          <dd>{health.environment}</dd>
        </div>
        <div className="detail-row">
          <dt>Database</dt>
          <dd className={health.database === "connected" ? "connected" : "disconnected"}>
            {health.database}
          </dd>
        </div>
        <div className="detail-row">
          <dt>Last Check</dt>
          <dd>{new Date(health.timestamp).toLocaleTimeString()}</dd>
        </div>

        {detailed && "checks" in health && (
          <>
            <div className="detail-row">
              <dt>Uptime</dt>
              <dd>{Math.floor((health as DetailedHealthResponse).uptime_seconds)}s</dd>
            </div>
            <div className="detail-row checks">
              <dt>Checks</dt>
              <dd>
                <ul className="checks-list">
                  {Object.entries(health.checks).map(([key, value]) => (
                    <li key={key} className={value ? "pass" : "fail"}>
                      <span className="check-name">{key}</span>
                      <span className="check-value">{value ? "✓" : "✗"}</span>
                    </li>
                  ))}
                </ul>
              </dd>
            </div>
          </>
        )}
      </dl>
    </div>
  );
}

export default HealthStatus;