/**
 * Run/Task-related API types matching backend schemas
 */

import type { TaskConfig, UsageResponse } from "./session";

export type { TaskConfig, InputFile, UsageResponse } from "./session";

export interface TaskEnqueueRequest {
  prompt: string;
  config?: TaskConfig | null;
  session_id?: string | null; // UUID, optional for continuing session
  permission_mode?: string; // e.g., "default" | "plan"
  schedule_mode?: string; // defaults to "immediate"
  timezone?: string | null;
  scheduled_at?: string | null; // ISO datetime
  project_id?: string | null;
  client_request_id?: string | null;
}

export interface TaskEnqueueResponse {
  session_id: string; // UUID
  accepted_type: "run" | "queued_query";
  run_id?: string | null; // UUID
  queue_item_id?: string | null; // UUID
  status: string;
  queued_query_count: number;
}

export interface RunResponse {
  run_id: string; // UUID
  session_id: string; // UUID
  user_message_id: number;
  status: string;
  permission_mode: string;
  progress: number;
  schedule_mode: string;
  scheduled_task_id?: string | null;
  scheduled_at: string; // ISO datetime
  usage?: UsageResponse | null;
  claimed_by: string | null;
  lease_expires_at: string | null;
  attempts: number;
  last_error: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string; // ISO datetime
  updated_at: string; // ISO datetime
}

export interface RunClaimRequest {
  worker_id: string;
  lease_seconds?: number; // defaults to 30
  schedule_modes?: string[] | null;
}

export interface RunClaimResponse {
  run: RunResponse;
  user_id: string;
  prompt: string;
  config_snapshot: Record<string, unknown> | null;
  sdk_session_id: string | null;
}

export interface RunStartRequest {
  worker_id: string;
}

export interface RunFailRequest {
  worker_id: string;
  error_message?: string | null;
}
