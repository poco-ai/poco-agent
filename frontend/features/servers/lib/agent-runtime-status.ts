import type { ServerAgentItem } from "@/features/servers/model/types";
import { getPersistentRuntimeStatus } from "../../../lib/persistent-runtime-status.ts";

export type AgentRuntimeTone = "success" | "warning" | "danger" | "muted";
export type AgentRuntimeState =
  | "running"
  | "warm_idle"
  | "sleeping"
  | "manually_stopped"
  | "stale"
  | "removed"
  | "failed"
  | "unknown";

export function getAgentRuntimeStatus(agent: ServerAgentItem): {
  state: AgentRuntimeState;
  labelKey:
    | "runtime.states.running"
    | "runtime.states.warmIdle"
    | "runtime.states.sleeping"
    | "runtime.states.manuallyStopped"
    | "runtime.states.stale"
    | "runtime.states.removed"
    | "runtime.states.failed"
    | "runtime.states.unknown";
  tone: AgentRuntimeTone;
  iconKey:
    | "running"
    | "warmIdle"
    | "sleeping"
    | "stopped"
    | "stale"
    | "removed"
    | "failed"
    | "unknown"
    | "pin";
  rawRuntimeStatus: string | null;
  rawLifecycleState: string | null;
  hasActiveExecution: boolean;
  isPinned: boolean;
} {
  const lifecycleState = (agent.lifecycleState || "").trim().toLowerCase();
  const runtimeStatus = (agent.persistentState?.runtimeStatus || "")
    .trim()
    .toLowerCase();
  const hasActiveExecution = Boolean(
    agent.persistentState?.activeSessionId ||
    agent.persistentState?.activeTaskId,
  );
  const status = getPersistentRuntimeStatus({
    removed: Boolean(agent.removedAt),
    lifecycleState,
    runtimeLifecycleState: agent.runtimeSummary?.lifecycleState,
    keepaliveUntil: agent.runtimeSummary?.keepaliveUntil,
    fallbackRuntimeStatus: runtimeStatus,
    hasActiveExecution,
  });

  return {
    state: status.state,
    labelKey: status.labelKey,
    tone: status.tone,
    iconKey: status.iconKey,
    rawRuntimeStatus: runtimeStatus || null,
    rawLifecycleState: lifecycleState || null,
    hasActiveExecution,
    isPinned: status.isPinned,
  };
}
