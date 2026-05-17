import type { ServerAgentItem } from "@/features/servers/model/types";

export type AgentRuntimeTone = "success" | "warning" | "danger" | "muted";
export type AgentRuntimeState =
  | "active"
  | "idle"
  | "stopped"
  | "removed"
  | "failed"
  | "unknown";

export function getAgentRuntimeStatus(agent: ServerAgentItem): {
  state: AgentRuntimeState;
  labelKey:
    | "conversationView.colleagues.runtimeStates.active"
    | "conversationView.colleagues.runtimeStates.idle"
    | "conversationView.colleagues.runtimeStates.stopped"
    | "conversationView.colleagues.runtimeStates.removed"
    | "conversationView.colleagues.runtimeStates.failed"
    | "conversationView.colleagues.runtimeStates.unknown";
  tone: AgentRuntimeTone;
  rawRuntimeStatus: string | null;
  rawLifecycleState: string | null;
  hasActiveExecution: boolean;
} {
  const lifecycleState = (agent.lifecycleState || "").trim().toLowerCase();
  const runtimeStatus = (agent.persistentState?.runtimeStatus || "")
    .trim()
    .toLowerCase();
  const hasActiveExecution = Boolean(
    agent.persistentState?.activeSessionId || agent.persistentState?.activeTaskId,
  );

  if (agent.removedAt) {
    return {
      state: "removed",
      labelKey: "conversationView.colleagues.runtimeStates.removed",
      tone: "muted",
      rawRuntimeStatus: runtimeStatus || null,
      rawLifecycleState: lifecycleState || null,
      hasActiveExecution,
    };
  }

  if (lifecycleState === "inactive") {
    return {
      state: "stopped",
      labelKey: "conversationView.colleagues.runtimeStates.stopped",
      tone: "muted",
      rawRuntimeStatus: runtimeStatus || null,
      rawLifecycleState: lifecycleState || null,
      hasActiveExecution,
    };
  }

  if (runtimeStatus === "busy" || hasActiveExecution) {
    return {
      state: "active",
      labelKey: "conversationView.colleagues.runtimeStates.active",
      tone: "warning",
      rawRuntimeStatus: runtimeStatus || null,
      rawLifecycleState: lifecycleState || null,
      hasActiveExecution,
    };
  }

  if (runtimeStatus === "failed") {
    return {
      state: "failed",
      labelKey: "conversationView.colleagues.runtimeStates.failed",
      tone: "danger",
      rawRuntimeStatus: runtimeStatus || null,
      rawLifecycleState: lifecycleState || null,
      hasActiveExecution,
    };
  }

  if (runtimeStatus === "idle" || runtimeStatus === "active") {
    return {
      state: "idle",
      labelKey: "conversationView.colleagues.runtimeStates.idle",
      tone: "success",
      rawRuntimeStatus: runtimeStatus || null,
      rawLifecycleState: lifecycleState || null,
      hasActiveExecution,
    };
  }

  return {
    state: "unknown",
    labelKey: "conversationView.colleagues.runtimeStates.unknown",
    tone: "muted",
    rawRuntimeStatus: runtimeStatus || null,
    rawLifecycleState: lifecycleState || null,
    hasActiveExecution,
  };
}

export function getAgentRuntimeDotClassName(tone: AgentRuntimeTone): string {
  switch (tone) {
    case "success":
      return "bg-emerald-500";
    case "warning":
      return "bg-amber-500";
    case "danger":
      return "bg-rose-500";
    default:
      return "bg-muted-foreground/50";
  }
}
