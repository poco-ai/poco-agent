import type { AgentAssignment } from "../model/types.ts";

export interface AssignmentExecutionMeta {
  isScheduled: boolean;
  hasSession: boolean;
  hasRetainedContainer: boolean;
  lastTriggeredAt: string | null;
  lastCompletedAt: string | null;
}

export function getAssignmentExecutionMeta(
  assignment: AgentAssignment | null | undefined,
): AssignmentExecutionMeta {
  return {
    isScheduled: assignment?.trigger_mode === "scheduled_task",
    hasSession: Boolean(assignment?.session_id),
    hasRetainedContainer: Boolean(assignment?.container_id),
    lastTriggeredAt: assignment?.last_triggered_at ?? null,
    lastCompletedAt: assignment?.last_completed_at ?? null,
  };
}
