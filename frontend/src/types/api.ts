// frontend/src/types/api.ts
/** API response types matching backend schemas. */

export interface HealthResponse {
  status: "healthy" | "degraded";
  version: string;
  environment: string;
  timestamp: string; // ISO 8601
  database: "connected" | "disconnected" | "unknown";
  details?: {
    checks: Record<string, boolean>;
  };
}

export interface DetailedHealthResponse extends HealthResponse {
  uptime_seconds: number;
  checks: Record<string, boolean>;
  details?: {
    checks: Record<string, boolean>;
    uptime_seconds: number;
    database_status: string;
  };
}

export interface ApiError {
  detail: string;
  code?: string;
}

export type HealthStatus = HealthResponse["status"];