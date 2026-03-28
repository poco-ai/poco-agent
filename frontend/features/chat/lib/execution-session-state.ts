import type { ExecutionSession, SessionResponse } from "@/features/chat/types";
import type { TaskHistoryItem } from "@/features/projects/types";

export type ExecutionUxPhase =
  | "pending"
  | "running"
  | "queued"
  | "export_pending"
  | "completed"
  | "failed"
  | "canceled";

type ExecutionSessionLike =
  | Pick<
      ExecutionSession,
      "status" | "workspace_export_status" | "queued_query_count"
    >
  | null
  | undefined;

export interface DerivedExecutionSessionState {
  phase: ExecutionUxPhase;
  queuedCount: number;
  hasQueuedQueries: boolean;
  isRunActive: boolean;
  isTerminal: boolean;
  isWorkspaceExportPending: boolean;
  isWorkspaceExportReady: boolean;
  shouldPollSession: boolean;
  shouldPollMessages: boolean;
  shouldPollDeliverables: boolean;
  shouldPollToolExecutions: boolean;
}

export function deriveExecutionSessionState(
  session: ExecutionSessionLike,
): DerivedExecutionSessionState {
  const status = session?.status;
  const queuedCount = Math.max(0, session?.queued_query_count ?? 0);
  const hasQueuedQueries = queuedCount > 0;
  const isRunActive = status === "pending" || status === "running";
  const isTerminal =
    status === "completed" || status === "failed" || status === "canceled";
  const isWorkspaceExportPending =
    session?.workspace_export_status === "pending";
  const isWorkspaceExportReady = session?.workspace_export_status === "ready";

  let phase: ExecutionUxPhase;
  switch (status) {
    case "running":
      phase = "running";
      break;
    case "pending":
      phase = "pending";
      break;
    case "failed":
    case "canceled":
    case "completed":
      if (hasQueuedQueries) {
        phase = "queued";
      } else if (status === "failed") {
        phase = "failed";
      } else if (status === "canceled") {
        phase = "canceled";
      } else if (isWorkspaceExportPending) {
        phase = "export_pending";
      } else {
        phase = "completed";
      }
      break;
    default:
      phase = isWorkspaceExportPending ? "export_pending" : "completed";
      break;
  }

  return {
    phase,
    queuedCount,
    hasQueuedQueries,
    isRunActive,
    isTerminal,
    isWorkspaceExportPending,
    isWorkspaceExportReady,
    shouldPollSession: Boolean(
      session && (isRunActive || hasQueuedQueries || isWorkspaceExportPending),
    ),
    shouldPollMessages: isRunActive,
    shouldPollDeliverables: isRunActive || isWorkspaceExportPending,
    shouldPollToolExecutions: isRunActive,
  };
}

export function mapSessionToTaskHistoryStatus(
  session: Pick<SessionResponse, "status" | "queued_query_count">,
): TaskHistoryItem["status"] {
  if (
    (session.queued_query_count ?? 0) > 0 &&
    (session.status === "completed" ||
      session.status === "failed" ||
      session.status === "canceled")
  ) {
    return "pending";
  }

  return session.status as TaskHistoryItem["status"];
}
