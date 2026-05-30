export type RuntimeStatusTone = "success" | "warning" | "danger" | "muted";
export type RuntimeStatusIconKey =
  | "running"
  | "warmIdle"
  | "sleeping"
  | "stopped"
  | "stale"
  | "removed"
  | "failed"
  | "unknown"
  | "pin";

export type RuntimeStatusState =
  | "running"
  | "warm_idle"
  | "sleeping"
  | "manually_stopped"
  | "stale"
  | "removed"
  | "failed"
  | "unknown";

export interface PersistentRuntimeStatusPresentation {
  state: RuntimeStatusState;
  labelKey:
    | "runtime.states.running"
    | "runtime.states.warmIdle"
    | "runtime.states.sleeping"
    | "runtime.states.manuallyStopped"
    | "runtime.states.stale"
    | "runtime.states.removed"
    | "runtime.states.failed"
    | "runtime.states.unknown";
  tone: RuntimeStatusTone;
  iconKey: RuntimeStatusIconKey;
  isPinned: boolean;
}

function isPinned(keepaliveUntil?: string | null): boolean {
  if (!keepaliveUntil) {
    return false;
  }
  const keepaliveAt = new Date(keepaliveUntil);
  return !Number.isNaN(keepaliveAt.getTime()) && keepaliveAt.getTime() > Date.now();
}

export function getPersistentRuntimeStatus(input: {
  removed?: boolean;
  lifecycleState?: string | null;
  runtimeLifecycleState?: string | null;
  keepaliveUntil?: string | null;
  fallbackRuntimeStatus?: string | null;
  hasActiveExecution?: boolean;
}): PersistentRuntimeStatusPresentation {
  const lifecycleState = (input.lifecycleState || "").trim().toLowerCase();
  const runtimeLifecycleState = (input.runtimeLifecycleState || "")
    .trim()
    .toLowerCase();
  const fallbackRuntimeStatus = (input.fallbackRuntimeStatus || "")
    .trim()
    .toLowerCase();
  const pinned = isPinned(input.keepaliveUntil);

  if (input.removed || runtimeLifecycleState === "removed") {
    return {
      state: "removed",
      labelKey: "runtime.states.removed",
      tone: "muted",
      iconKey: "removed",
      isPinned: false,
    };
  }

  if (
    runtimeLifecycleState === "manually_stopped" ||
    lifecycleState === "inactive"
  ) {
    return {
      state: "manually_stopped",
      labelKey: "runtime.states.manuallyStopped",
      tone: "muted",
      iconKey: "stopped",
      isPinned: false,
    };
  }

  if (runtimeLifecycleState === "running") {
    return {
      state: "running",
      labelKey: "runtime.states.running",
      tone: "warning",
      iconKey: "running",
      isPinned: pinned,
    };
  }

  if (runtimeLifecycleState === "warm_idle") {
    return {
      state: "warm_idle",
      labelKey: "runtime.states.warmIdle",
      tone: "success",
      iconKey: "warmIdle",
      isPinned: pinned,
    };
  }

  if (runtimeLifecycleState === "sleeping") {
    return {
      state: "sleeping",
      labelKey: "runtime.states.sleeping",
      tone: "muted",
      iconKey: "sleeping",
      isPinned: pinned,
    };
  }

  if (runtimeLifecycleState === "stale") {
    return {
      state: "stale",
      labelKey: "runtime.states.stale",
      tone: "danger",
      iconKey: "stale",
      isPinned: pinned,
    };
  }

  if (fallbackRuntimeStatus === "failed") {
    return {
      state: "failed",
      labelKey: "runtime.states.failed",
      tone: "danger",
      iconKey: "failed",
      isPinned: pinned,
    };
  }

  if (fallbackRuntimeStatus === "busy" || input.hasActiveExecution) {
    return {
      state: "running",
      labelKey: "runtime.states.running",
      tone: "warning",
      iconKey: "running",
      isPinned: pinned,
    };
  }

  if (fallbackRuntimeStatus === "idle" || fallbackRuntimeStatus === "active") {
    return {
      state: "warm_idle",
      labelKey: "runtime.states.warmIdle",
      tone: "success",
      iconKey: "warmIdle",
      isPinned: pinned,
    };
  }

  return {
    state: "unknown",
    labelKey: "runtime.states.unknown",
    tone: "muted",
    iconKey: "unknown",
    isPinned: pinned,
  };
}
