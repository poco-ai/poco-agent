import type {
  ChatFileReference,
  ChatSkillReference,
  InputFile,
} from "./session";

export interface SessionQueueItemResponse {
  queue_item_id: string;
  session_id: string;
  sequence_no: number;
  status: "queued" | "paused" | "promoted" | "canceled";
  prompt: string;
  permission_mode: string;
  attachments: InputFile[];
  file_references?: ChatFileReference[] | null;
  input_file_references?: ChatFileReference[] | null;
  skill_references?: ChatSkillReference[] | null;
  client_request_id?: string | null;
  linked_run_id?: string | null;
  linked_user_message_id?: number | null;
  created_at: string;
  updated_at: string;
}

export interface SessionQueueItemUpdateRequest {
  prompt?: string | null;
  attachments?: InputFile[] | null;
  file_references?: ChatFileReference[] | null;
  input_file_references?: ChatFileReference[] | null;
  skill_references?: ChatSkillReference[] | null;
}
