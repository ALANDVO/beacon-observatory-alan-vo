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

// Session log types
export type LogSource = "claude-code" | "codex" | "copilot" | "pi" | "opencode" | "gemini" | "prime-agent";
export type SessionType = "main" | "subagent" | "headless";

export interface SessionLogCreate {
  source: LogSource;
  session_id: string;
  session_type: SessionType;
  timestamp: string; // ISO 8601
  hook_present?: boolean;
  hook_text?: string | null;
  router_opened?: boolean;
  playbook_opened?: boolean;
  principle_opened?: boolean;
  agent_type_detail?: string | null;
  raw_log_path?: string | null;
  metadata_json?: string | null;
}

export interface SessionLogResponse extends SessionLogCreate {
  id: number;
  created_at: string;
}

export interface SessionLogListResponse {
  items: SessionLogResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Analysis job types
export type AnalysisStatus = "pending" | "running" | "completed" | "failed";

export interface AnalysisJobCreate {
  name: string;
  description?: string | null;
  source_filter?: LogSource | null;
  session_type_filter?: SessionType | null;
  date_from?: string | null; // ISO 8601
  date_to?: string | null; // ISO 8601
}

export interface AnalysisJobResponse {
  id: number;
  name: string;
  description: string | null;
  source_filter: LogSource | null;
  session_type_filter: SessionType | null;
  date_from: string | null;
  date_to: string | null;
  status: AnalysisStatus;
  progress: number;
  total_logs: number;
  processed_logs: number;
  error_message: string | null;
  result_json: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface AnalysisJobListResponse {
  items: AnalysisJobResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Analysis result types
export interface AnalysisResultResponse {
  id: number;
  job_id: number;
  source: LogSource;
  session_type: SessionType;
  total_sessions: number;
  hook_reach_count: number;
  hook_reach_rate: number;
  router_open_count: number;
  router_open_rate: number;
  playbook_open_count: number;
  playbook_open_rate: number;
  principle_open_count: number;
  principle_open_rate: number;
  opens_per_100_prompts: number;
  created_at: string;
}

export interface EffectivenessReportResponse {
  job: AnalysisJobResponse;
  results: AnalysisResultResponse[];
  summary: Record<string, unknown>;
}

export type HealthStatus = HealthResponse["status"];