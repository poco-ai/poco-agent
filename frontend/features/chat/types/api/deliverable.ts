import type { ToolExecutionResponse } from "./session";

export interface DeliverableResponse {
  id: string;
  session_id: string;
  kind: string;
  logical_name: string;
  latest_version_id?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface DeliverableVersionResponse {
  id: string;
  session_id: string;
  run_id: string;
  deliverable_id: string;
  source_message_id?: number | null;
  version_no: number;
  file_path: string;
  file_name?: string | null;
  mime_type?: string | null;
  input_refs_json?: Record<string, unknown> | null;
  related_tool_execution_ids_json?: Record<string, unknown> | null;
  detection_metadata_json?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export type DeliverableVersionToolExecutionResponse = ToolExecutionResponse;
