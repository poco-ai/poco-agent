import type { TaskHistoryItem } from "@/features/projects/types";

export const TASK_STATUS_META: Record<
  TaskHistoryItem["status"],
  { dotClassName: string; labelKey: string }
> = {
  pending: {
    dotClassName: "bg-muted-foreground/40",
    labelKey: "status.pending",
  },
  running: {
    dotClassName: "bg-primary ring-1 ring-primary/45",
    labelKey: "status.running",
  },
  completed: { dotClassName: "bg-primary", labelKey: "status.completed" },
  failed: { dotClassName: "bg-destructive", labelKey: "status.failed" },
  canceled: {
    dotClassName: "bg-chart-4/60",
    labelKey: "status.canceled",
  },
};
