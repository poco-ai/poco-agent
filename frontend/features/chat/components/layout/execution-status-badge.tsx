"use client";

import { Badge } from "@/components/ui/badge";
import { deriveExecutionSessionState } from "@/features/chat/lib/execution-session-state";
import type { ExecutionSession } from "@/features/chat/types";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

interface ExecutionStatusBadgeProps {
  session: ExecutionSession | null;
  className?: string;
}

const phaseClassName: Record<
  ReturnType<typeof deriveExecutionSessionState>["phase"],
  string
> = {
  pending:
    "border-amber-500/20 bg-amber-500/10 text-amber-700 dark:text-amber-300",
  running: "border-primary/20 bg-primary/10 text-primary",
  queued: "border-sky-500/20 bg-sky-500/10 text-sky-700 dark:text-sky-300",
  export_pending:
    "border-violet-500/20 bg-violet-500/10 text-violet-700 dark:text-violet-300",
  completed:
    "border-emerald-500/20 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  failed: "border-destructive/20 bg-destructive/10 text-destructive",
  canceled: "border-muted-foreground/20 bg-muted text-muted-foreground",
};

export function ExecutionStatusBadge({
  session,
  className,
}: ExecutionStatusBadgeProps) {
  const { t } = useT("translation");

  if (!session) return null;

  const state = deriveExecutionSessionState(session);
  const labelKey = (() => {
    switch (state.phase) {
      case "running":
        return "chat.executionState.running";
      case "queued":
        return "chat.executionState.queued";
      case "export_pending":
        return "chat.executionState.exportPending";
      case "completed":
        return "chat.executionState.completed";
      case "failed":
        return "chat.executionState.failed";
      case "canceled":
        return "chat.executionState.canceled";
      case "pending":
      default:
        return "chat.executionState.pending";
    }
  })();

  const title = state.isWorkspaceExportPending
    ? t("chat.executionState.exportPendingHint")
    : state.hasQueuedQueries
      ? t("chat.executionState.queueCount", { count: state.queuedCount })
      : t(labelKey);

  return (
    <Badge
      variant="outline"
      className={cn(
        "h-6 shrink-0 rounded-full px-2.5 text-[11px] font-semibold",
        phaseClassName[state.phase],
        className,
      )}
      title={title}
      aria-label={title}
    >
      {t(labelKey)}
    </Badge>
  );
}
