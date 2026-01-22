import { z } from "zod";
import { chatService } from "@/features/chat/services/chat-service";

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
    mcp_config: z.record(z.string(), z.boolean()).optional(),
    skill_files: z.record(z.string(), z.unknown()).optional(),
    input_files: z.array(inputFileSchema).optional(),
  })
  .passthrough();

const createSessionSchema = z
  .object({
    prompt: z.string(),
    config: configSchema.optional(),
    projectId: z.string().uuid().optional(),
  })
  .refine(
    (data) => {
      const hasPrompt = data.prompt.trim().length > 0;
      const hasFiles = Boolean(data.config?.input_files?.length);
      return hasPrompt || hasFiles;
    },
    {
      message: "请输入任务内容",
      path: ["prompt"],
    },
  );

const sendMessageSchema = z
  .object({
    sessionId: z.string().trim().min(1, "缺少会话 ID"),
    content: z.string(),
    attachments: z.array(inputFileSchema).optional(),
  })
  .refine(
    (data) =>
      data.content.trim().length > 0 ||
      (data.attachments && data.attachments.length > 0),
    {
      message: "请输入消息内容",
      path: ["content"],
    },
  );

export type CreateSessionInput = z.infer<typeof createSessionSchema>;
export type SendMessageInput = z.infer<typeof sendMessageSchema>;

export async function createSessionAction(input: CreateSessionInput) {
  const { prompt, config, projectId } = createSessionSchema.parse(input);
  const hasInputFiles = Boolean(config?.input_files?.length);
  const finalPrompt =
    prompt.trim() || (hasInputFiles ? "Uploaded files" : prompt);
  const result = await chatService.createSession(
    finalPrompt,
    config,
    projectId,
  );
  return {
    sessionId: result.session_id,
    runId: result.run_id,
    status: result.status,
  };
}

export async function sendMessageAction(input: SendMessageInput) {
  const { sessionId, content, attachments } = sendMessageSchema.parse(input);
  // Ensure we have a prompt if content is empty but attachments exist
  const finalContent =
    content.trim() || (attachments?.length ? "Uploaded files" : content);
  const result = await chatService.sendMessage(
    sessionId,
    finalContent,
    attachments,
  );
  return {
    sessionId: result.session_id,
    runId: result.run_id,
    status: result.status,
  };
}

const deleteSessionSchema = z.object({
  sessionId: z.string().trim().min(1, "缺少会话 ID"),
});

export type DeleteSessionInput = z.infer<typeof deleteSessionSchema>;

export async function deleteSessionAction(input: DeleteSessionInput) {
  const { sessionId } = deleteSessionSchema.parse(input);
  await chatService.deleteSession(sessionId);
}
