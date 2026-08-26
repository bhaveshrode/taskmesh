export interface Job {
  id: string;
  name: string;
  description: string;
  command: string;
  payload: Record<string, unknown>;
  status: 'pending' | 'queued' | 'running' | 'success' | 'failed' | 'cancelled' | 'retrying';
  priority: 'low' | 'default' | 'high';
  queue_name: string;
  schedule_type: 'once' | 'interval' | 'cron' | 'workflow';
  attempt: number;
  max_retries: number;
  timeout_seconds: number;
  worker_id: string | null;
  result: Record<string, unknown> | null;
  error_message: string | null;
  exit_code: number | null;
  tags: string[];
  owner_id: string | null;
  workflow_id: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
  scheduled_at: string | null;
  cron_expression: string | null;
  interval_seconds: number | null;
}

export interface JobListResponse {
  jobs: Job[];
  total: number;
  page: number;
  page_size: number;
}

export interface Workflow {
  id: string;
  name: string;
  description: string;
  dag_definition: {
    tasks: Record<string, {
      command: string;
      depends_on: string[];
      payload: Record<string, unknown>;
      max_retries: number;
      timeout_seconds: number;
      name: string;
    }>;
  };
  status: 'pending' | 'running' | 'success' | 'failed' | 'cancelled';
  schedule_type: string;
  cron_expression: string | null;
  interval_seconds: number | null;
  owner_id: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface WorkflowExecution {
  id: string;
  workflow_id: string;
  status: string;
  task_states: Record<string, { status: string; job_id: string }>;
  result: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface Worker {
  id: string;
  hostname: string;
  pid: number;
  status: string;
  queues: string[];
  max_concurrent: number;
  current_jobs: string[];
  heartbeat_at: string | null;
  jobs_completed: number;
  jobs_failed: number;
  created_at: string;
  updated_at: string;
}

export interface DashboardStats {
  total_jobs: number;
  running_jobs: number;
  queued_jobs: number;
  failed_jobs: number;
  completed_jobs: number;
  total_workflows: number;
  active_workers: number;
  jobs_last_24h: number;
}

export interface LogEntry {
  id: string;
  job_id: string;
  level: string;
  message: string;
  metadata: Record<string, unknown>;
  timestamp: string;
}

export interface User {
  id: string;
  username: string;
  email: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}
