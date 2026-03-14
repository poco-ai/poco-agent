import { z } from "zod";
import { chatService } from "@/features/chat/api/chat-api";

const VALIDATION_ERRORS = {
  taskContentRequired: "validation.taskContentRequired",
  selectExecutionTime: "validation.selectExecutionTime",
  nightlyNoTime: "validation.nightlyNoTime",
  missingSessionId: "validation.missingSessionId",
  messageContentRequired: "validation.messageContentRequired",
  sessionNameRequired: "validation.sessionNameRequired",
  sessionNameTooLong: "validation.sessionNameTooLong",
} as const;

const inputFileSchema = z
  .object({
    id: z.string().optional().nullable(),
    type: z.string().optional(),
    name: z.string(),
    source: z.string(),
    size: z.number().optional().nullable(),
    content_type: z.string().optional().nullable(),
    path: z.string().optional().nullable(),
  })
  .passthrough();

const configSchema = z
  .object({
    repo_url: z.string().optional().nullable(),
    git_branch: z.string().optional(),
    git_token_env_key: z.string().optional().nullable(),
    model: z.string().optional().nullable(),
    model_provider_id: z.string().optional().nullable(),
    browser_enabled: z.boolean().optional(),
    memory_enabled: z.boolean().optional(),
    mcp_config: z.record(z.string(), z.boolean()).optional(),
    skill_config: z.record(z.string(), z.boolean()).optional(),
    plugin_config: z.record(z.string(), z.boolean()).optional(),
    input_files: z.array(inputFileSchema).optional(),
  })
  .passthrough();

const createSessionSchema = z
  .object({
    prompt: z.string(),
    config: configSchema.optional(),
    projectId: z.string().uuid().optional(),
    permission_mode: z
      .enum(["default", "acceptEdits", "plan", "bypassPermissions"])
      .optional(),
    schedule_mode: z.enum(["immediate", "scheduled", "nightly"]).optional(),
    timezone: z.string().optional().nullable(),
    scheduled_at: z.string().optional().nullable(),
  })
  .refine(
    (data) => {
      const hasPrompt = data.prompt.trim().length > 0;
      const hasFiles = Boolean(data.config?.input_files?.length);
      return hasPrompt || hasFiles;
    },
    {
      message: VALIDATION_ERRORS.taskContentRequired,
      path: ["prompt"],
    },
  )
  .refine(
    (data) => {
      if (data.schedule_mode !== "scheduled") return true;
      return Boolean((data.scheduled_at || "").trim());
    },
    {
      message: VALIDATION_ERRORS.selectExecutionTime,
      path: ["scheduled_at"],
    },
  )
  .refine(
    (data) => {
      if (data.schedule_mode !== "nightly") return true;
      return !data.scheduled_at;
    },
    {
      message: VALIDATION_ERRORS.nightlyNoTime,
      path: ["scheduled_at"],
    },
  );

const sendMessageSchema = z
  .object({
    sessionId: z.string().trim().min(1, VALIDATION_ERRORS.missingSessionId),
    content: z.string(),
    attachments: z.array(inputFileSchema).optional(),
    model: z.string().trim().optional().nullable(),
    model_provider_id: z.string().trim().optional().nullable(),
  })
  .refine(
    (data) =>
      data.content.trim().length > 0 ||
      (data.attachments && data.attachments.length > 0),
    {
      message: VALIDATION_ERRORS.messageContentRequired,
      path: ["content"],
    },
  );

const queuedQueryItemSchema = z.object({
  sessionId: z.string().trim().min(1, VALIDATION_ERRORS.missingSessionId),
  itemId: z.string().uuid(),
});

const updateQueuedQuerySchema = queuedQueryItemSchema
  .extend({
    prompt: z.string().optional(),
    attachments: z.array(inputFileSchema).optional(),
  })
  .refine(
    (data) => data.prompt !== undefined || data.attachments !== undefined,
    {
      message: VALIDATION_ERRORS.messageContentRequired,
      path: ["prompt"],
    },
  );

export type CreateSessionInput = z.infer<typeof createSessionSchema>;
export type SendMessageInput = z.infer<typeof sendMessageSchema>;
export type UpdateQueuedQueryInput = z.infer<typeof updateQueuedQuerySchema>;
export type QueuedQueryItemInput = z.infer<typeof queuedQueryItemSchema>;

export interface TaskEnqueueActionResult {
  sessionId: string;
  acceptedType: "run" | "queued_query";
  runId?: string;
  queueItemId?: string;
  status: string;
  queuedQueryCount: number;
}

function createClientRequestId(): string {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return crypto.randomUUID();
  }
  return `req-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function mapTaskEnqueueResult(result: {
  session_id: string;
  accepted_type: "run" | "queued_query";
  run_id?: string | null;
  queue_item_id?: string | null;
  status: string;
  queued_query_count: number;
}): TaskEnqueueActionResult {
  return {
    sessionId: result.session_id,
    acceptedType: result.accepted_type,
    runId: result.run_id ?? undefined,
    queueItemId: result.queue_item_id ?? undefined,
    status: result.status,
    queuedQueryCount: result.queued_query_count,
  };
}

export async function createSessionAction(input: CreateSessionInput) {
  const {
    prompt,
    config,
    projectId,
    permission_mode,
    schedule_mode,
    timezone,
    scheduled_at,
  } = createSessionSchema.parse(input);
  const hasInputFiles = Boolean(config?.input_files?.length);
  const finalPrompt =
    prompt.trim() || (hasInputFiles ? "Uploaded files" : prompt);
  const result = await chatService.createSession(
    finalPrompt,
    config,
    projectId,
    {
      schedule_mode,
      timezone: timezone || undefined,
      scheduled_at: scheduled_at || undefined,
    },
    permission_mode,
    createClientRequestId(),
  );
  return mapTaskEnqueueResult(result);
}

export async function sendMessageAction(input: SendMessageInput) {
  const { sessionId, content, attachments, model, model_provider_id } =
    sendMessageSchema.parse(input);

  // Ensure we have a prompt if content is empty but attachments exist
  const finalContent =
    content.trim() || (attachments?.length ? "Uploaded files" : content);
  const result = await chatService.sendMessage(
    sessionId,
    finalContent,
    model,
    model_provider_id,
    attachments,
    createClientRequestId(),
  );
  return mapTaskEnqueueResult(result);
}

const regenerateMessageSchema = z.object({
  sessionId: z.string().trim().min(1, VALIDATION_ERRORS.missingSessionId),
  userMessageId: z.number().int().positive(),
  assistantMessageId: z.number().int().positive(),
  model: z.string().trim().optional().nullable(),
  model_provider_id: z.string().trim().optional().nullable(),
});

export type RegenerateMessageInput = z.infer<typeof regenerateMessageSchema>;

export async function regenerateMessageAction(input: RegenerateMessageInput) {
  const {
    sessionId,
    userMessageId,
    assistantMessageId,
    model,
    model_provider_id,
  } = regenerateMessageSchema.parse(input);
  const result = await chatService.regenerateMessage(sessionId, {
    user_message_id: userMessageId,
    assistant_message_id: assistantMessageId,
    model,
    model_provider_id,
  });
  return mapTaskEnqueueResult(result);
}

const editMessageAndRegenerateSchema = z.object({
  sessionId: z.string().trim().min(1, VALIDATION_ERRORS.missingSessionId),
  userMessageId: z.number().int().positive(),
  content: z.string().trim().min(1, VALIDATION_ERRORS.messageContentRequired),
  model: z.string().trim().optional().nullable(),
  model_provider_id: z.string().trim().optional().nullable(),
});

export type EditMessageAndRegenerateInput = z.infer<
  typeof editMessageAndRegenerateSchema
>;

export async function editMessageAndRegenerateAction(
  input: EditMessageAndRegenerateInput,
) {
  const { sessionId, userMessageId, content, model, model_provider_id } =
    editMessageAndRegenerateSchema.parse(input);
  const result = await chatService.editMessageAndRegenerate(sessionId, {
    user_message_id: userMessageId,
    content,
    model,
    model_provider_id,
  });
  return mapTaskEnqueueResult(result);
}

const cancelSessionSchema = z.object({
  sessionId: z.string().trim().min(1, VALIDATION_ERRORS.missingSessionId),
  reason: z.string().optional().nullable(),
});

export type CancelSessionInput = z.infer<typeof cancelSessionSchema>;

export async function cancelSessionAction(input: CancelSessionInput) {
  const { sessionId, reason } = cancelSessionSchema.parse(input);
  return chatService.cancelSession(sessionId, {
    reason: reason ?? undefined,
  });
}

const branchSessionSchema = z.object({
  sessionId: z.string().trim().min(1, VALIDATION_ERRORS.missingSessionId),
  messageId: z.number().int().positive(),
});

export type BranchSessionInput = z.infer<typeof branchSessionSchema>;

export async function branchSessionAction(input: BranchSessionInput) {
  const { sessionId, messageId } = branchSessionSchema.parse(input);
  const result = await chatService.branchSession(sessionId, {
    message_id: messageId,
  });
  return {
    sessionId: result.session_id,
    sourceSessionId: result.source_session_id,
    cutoffMessageId: result.cutoff_message_id,
  };
}

const deleteSessionSchema = z.object({
  sessionId: z.string().trim().min(1, VALIDATION_ERRORS.missingSessionId),
});

export type DeleteSessionInput = z.infer<typeof deleteSessionSchema>;

export async function deleteSessionAction(input: DeleteSessionInput) {
  const { sessionId } = deleteSessionSchema.parse(input);
  await chatService.deleteSession(sessionId);
}

const renameSessionTitleSchema = z.object({
  sessionId: z.string().trim().min(1, VALIDATION_ERRORS.missingSessionId),
  title: z
    .string()
    .trim()
    .min(1, VALIDATION_ERRORS.sessionNameRequired)
    .max(255, VALIDATION_ERRORS.sessionNameTooLong),
});

export type RenameSessionTitleInput = z.infer<typeof renameSessionTitleSchema>;

export async function renameSessionTitleAction(input: RenameSessionTitleInput) {
  const { sessionId, title } = renameSessionTitleSchema.parse(input);
  return chatService.updateSession(sessionId, { title });
}

const setSessionPinSchema = z.object({
  sessionId: z.string().trim().min(1, VALIDATION_ERRORS.missingSessionId),
  isPinned: z.boolean(),
});

export type SetSessionPinInput = z.infer<typeof setSessionPinSchema>;

export async function setSessionPinAction(input: SetSessionPinInput) {
  const { sessionId, isPinned } = setSessionPinSchema.parse(input);
  return chatService.updateSession(sessionId, { is_pinned: isPinned });
}

export async function updateQueuedQueryAction(input: UpdateQueuedQueryInput) {
  const { sessionId, itemId, prompt, attachments } =
    updateQueuedQuerySchema.parse(input);
  return chatService.updateQueuedQuery(sessionId, itemId, {
    prompt,
    attachments,
  });
}

export async function deleteQueuedQueryAction(input: QueuedQueryItemInput) {
  const { sessionId, itemId } = queuedQueryItemSchema.parse(input);
  return chatService.deleteQueuedQuery(sessionId, itemId);
}

export async function sendQueuedQueryNowAction(input: QueuedQueryItemInput) {
  const { sessionId, itemId } = queuedQueryItemSchema.parse(input);
  const result = await chatService.sendQueuedQueryNow(sessionId, itemId);
  return mapTaskEnqueueResult(result);
}
