import type { Job, JobListResponse, Workflow, WorkflowExecution, Worker, DashboardStats, LogEntry } from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
  if (token) {
    localStorage.setItem('token', token);
  } else {
    localStorage.removeItem('token');
  }
}

export function getAuthToken(): string | null {
  if (authToken) return authToken;
  if (typeof window !== 'undefined') {
    authToken = localStorage.getItem('token');
  }
  return authToken;
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `API error: ${res.status}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// Auth
export async function login(username: string, password: string) {
  const data = await apiFetch<{ access_token: string }>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
  setAuthToken(data.access_token);
  return data;
}

export async function register(username: string, email: string, password: string) {
  return apiFetch<{ id: string; username: string }>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, email, password }),
  });
}

// Jobs
export async function listJobs(params: {
  page?: number;
  page_size?: number;
  status?: string;
  priority?: string;
  search?: string;
} = {}): Promise<JobListResponse> {
  const qs = new URLSearchParams();
  if (params.page) qs.set('page', String(params.page));
  if (params.page_size) qs.set('page_size', String(params.page_size));
  if (params.status) qs.set('status', params.status);
  if (params.priority) qs.set('priority', params.priority);
  if (params.search) qs.set('search', params.search);
  return apiFetch(`/api/jobs?${qs.toString()}`);
}

export async function getJob(id: string): Promise<Job> {
  return apiFetch(`/api/jobs/${id}`);
}

export async function createJob(data: {
  name: string;
  command: string;
  description?: string;
  payload?: Record<string, unknown>;
  priority?: string;
  queue_name?: string;
  max_retries?: number;
  timeout_seconds?: number;
  scheduled_at?: string;
  tags?: string[];
}): Promise<Job> {
  return apiFetch('/api/jobs', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function runJob(id: string): Promise<Job> {
  return apiFetch(`/api/jobs/${id}/run`, { method: 'POST' });
}

export async function cancelJob(id: string): Promise<Job> {
  return apiFetch(`/api/jobs/${id}/cancel`, { method: 'POST' });
}

export async function deleteJob(id: string): Promise<void> {
  return apiFetch(`/api/jobs/${id}`, { method: 'DELETE' });
}

// Workflows
export async function listWorkflows(): Promise<Workflow[]> {
  return apiFetch('/api/workflows');
}

export async function getWorkflow(id: string): Promise<Workflow> {
  return apiFetch(`/api/workflows/${id}`);
}

export async function createWorkflow(data: {
  name: string;
  description?: string;
  tasks: Array<{
    id: string;
    name: string;
    command: string;
    depends_on?: string[];
    payload?: Record<string, unknown>;
    max_retries?: number;
    timeout_seconds?: number;
  }>;
  schedule_type?: string;
  cron_expression?: string;
  interval_seconds?: number;
}): Promise<Workflow> {
  return apiFetch('/api/workflows', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function runWorkflow(id: string): Promise<WorkflowExecution> {
  return apiFetch(`/api/workflows/${id}/run`, { method: 'POST' });
}

export async function updateWorkflow(id: string, data: {
  name?: string;
  description?: string;
  tasks?: Array<{
    id: string;
    name: string;
    command: string;
    depends_on?: string[];
    payload?: Record<string, unknown>;
    max_retries?: number;
    timeout_seconds?: number;
  }>;
}): Promise<Workflow> {
  return apiFetch(`/api/workflows/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function getWorkflowExecutions(id: string): Promise<WorkflowExecution[]> {
  return apiFetch(`/api/workflows/${id}/executions`);
}

// Workers & Dashboard
export async function getDashboardStats(): Promise<DashboardStats> {
  return apiFetch('/api/dashboard/stats');
}

export async function listWorkers(): Promise<Worker[]> {
  return apiFetch('/api/workers');
}

export async function deleteWorker(id: string): Promise<void> {
  return apiFetch(`/api/workers/${id}`, { method: 'DELETE' });
}

export async function reactivateWorker(id: string): Promise<Worker> {
  return apiFetch(`/api/workers/${id}/reactivate`, { method: 'PATCH' });
}

export async function getJobLogs(jobId: string, limit = 100): Promise<LogEntry[]> {
  return apiFetch(`/api/jobs/${jobId}/logs?limit=${limit}`);
}
