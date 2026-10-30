// frontend/src/api/client.ts
/** Typed API client for backend communication. */
import type {
  HealthResponse,
  DetailedHealthResponse,
  SessionLogCreate,
  SessionLogResponse,
  SessionLogListResponse,
  AnalysisJobCreate,
  AnalysisJobResponse,
  AnalysisJobListResponse,
  EffectivenessReportResponse,
} from "../types/api";
 
const API_BASE = "/api";
 
class ApiClient {
  private baseUrl: string;
 
  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }
 
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });
 
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }
 
    return response.json() as Promise<T>;
  }
 
  async getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/healthz");
  }
 
  async getDetailedHealth(): Promise<DetailedHealthResponse> {
    return this.request<DetailedHealthResponse>("/health");
  }
 
  async createSessionLog(log: SessionLogCreate): Promise<SessionLogResponse> {
    return this.request<SessionLogResponse>("/analyze/logs", {
      method: "POST",
      body: JSON.stringify(log),
    });
  }

  async createSessionLogsBulk(logs: SessionLogCreate[]): Promise<SessionLogResponse[]> {
    return this.request<SessionLogResponse[]>("/analyze/logs/bulk", {
      method: "POST",
      body: JSON.stringify(logs),
    });
  }
 
  async listSessionLogs(params?: {
    page?: number;
    page_size?: number;
    source?: string;
    session_type?: string;
    date_from?: string;
    date_to?: string;
  }): Promise<SessionLogListResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value));
        }
      });
    }
    return this.request<SessionLogListResponse>(`/analyze/logs?${searchParams.toString()}`);
  }
 
  // Analysis job endpoints
  async createAnalysisJob(job: AnalysisJobCreate): Promise<AnalysisJobResponse> {
    return this.request<AnalysisJobResponse>("/analyze/jobs", {
      method: "POST",
      body: JSON.stringify(job),
    });
  }
 
  async listAnalysisJobs(page = 1, pageSize = 20): Promise<AnalysisJobListResponse> {
    return this.request<AnalysisJobListResponse>(`/analyze/jobs?page=${page}&page_size=${pageSize}`);
  }
 
  async getAnalysisJob(jobId: number): Promise<AnalysisJobResponse> {
    return this.request<AnalysisJobResponse>(`/analyze/jobs/${jobId}`);
  }
 
  async runAnalysisJob(jobId: number): Promise<AnalysisJobResponse> {
    return this.request<AnalysisJobResponse>(`/analyze/jobs/${jobId}/run`, {
      method: "POST",
    });
  }
 
  async getEffectivenessReport(jobId: number): Promise<EffectivenessReportResponse> {
    return this.request<EffectivenessReportResponse>(`/analyze/jobs/${jobId}/report`);
  }
 
  async deleteAnalysisJob(jobId: number): Promise<void> {
    await this.request<void>(`/analyze/jobs/${jobId}`, {
      method: "DELETE",
    });
  }
}
 
export const apiClient = new ApiClient();
export default apiClient;