import { z } from "zod";
import { chatService } from "@/features/chat/api/chat-api";

// Validation error messages - translation keys that will be resolved by the caller
const VALIDATION_ERRORS = {
  missingSessionId: "validation.missingSessionId",
  missingToolUseId: "validation.missingToolUseId",
} as const;

const listSessionsSchema = z.object({
  userId: z.string().optional(),
  limit: z.number().int().positive().optional(),
  offset: z.number().int().min(0).optional(),
});

const sessionIdSchema = z.object({
  sessionId: z.string().trim().min(1, VALIDATION_ERRORS.missingSessionId),
});

const getMessagesSchema = sessionIdSchema.extend({
  realUserMessageIds: z.array(z.number().int()).optional(),
});

const executionSessionSchema = sessionIdSchema.extend({
  currentProgress: z.number().min(0).optional(),
});

const toolExecutionsSchema = sessionIdSchema.extend({
  limit: z.number().int().positive().optional(),
  offset: z.number().int().min(0).optional(),
});

const browserScreenshotSchema = sessionIdSchema.extend({
  toolUseId: z.string().trim().min(1, VALIDATION_ERRORS.missingToolUseId),
});

export type ListSessionsInput = z.infer<typeof listSessionsSchema>;
export type GetExecutionSessionInput = z.infer<typeof executionSessionSchema>;
export type GetMessagesInput = z.infer<typeof getMessagesSchema>;
export type GetMessageAttachmentsInput = z.infer<typeof sessionIdSchema>;
export type GetFilesInput = z.infer<typeof sessionIdSchema>;
export type GetRunsBySessionInput = z.infer<typeof sessionIdSchema>;
export type GetToolExecutionsInput = z.infer<typeof toolExecutionsSchema>;
export type GetBrowserScreenshotInput = z.infer<typeof browserScreenshotSchema>;

export async function listSessionsAction(input?: ListSessionsInput) {
  const { userId, limit, offset } = listSessionsSchema.parse(input ?? {});
  return chatService.listSessions({ user_id: userId, limit, offset });
}

export async function getExecutionSessionAction(
  input: GetExecutionSessionInput,
) {
  const { sessionId, currentProgress } = executionSessionSchema.parse(input);
  return chatService.getExecutionSession(sessionId, currentProgress);
}

export async function getMessagesAction(input: GetMessagesInput) {
  const { sessionId, realUserMessageIds } = getMessagesSchema.parse(input);
  return chatService.getMessages(sessionId, { realUserMessageIds });
}

export async function getMessagesBaseAction(input: GetMessagesInput) {
  const { sessionId, realUserMessageIds } = getMessagesSchema.parse(input);
  return chatService.getMessagesBase(sessionId, { realUserMessageIds });
}

export async function getMessageAttachmentsAction(
  input: GetMessageAttachmentsInput,
) {
  const { sessionId } = sessionIdSchema.parse(input);
  return chatService.getMessageAttachments(sessionId);
}

export async function getFilesAction(input: GetFilesInput) {
  const { sessionId } = sessionIdSchema.parse(input);
  return chatService.getFiles(sessionId);
}

export async function getRunsBySessionAction(input: GetRunsBySessionInput) {
  const { sessionId } = sessionIdSchema.parse(input);
  return chatService.getRunsBySession(sessionId, { limit: 1000, offset: 0 });
}

export async function getToolExecutionsAction(input: GetToolExecutionsInput) {
  const { sessionId, limit, offset } = toolExecutionsSchema.parse(input);
  return chatService.getToolExecutions(sessionId, { limit, offset });
}

export async function getBrowserScreenshotAction(
  input: GetBrowserScreenshotInput,
) {
  const { sessionId, toolUseId } = browserScreenshotSchema.parse(input);
  return chatService.getBrowserScreenshot(sessionId, toolUseId);
}
