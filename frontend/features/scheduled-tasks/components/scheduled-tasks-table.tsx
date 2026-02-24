"use client";

import { useMemo } from "react";
import { Pencil, Play, Trash2 } from "lucide-react";

import { useT } from "@/lib/i18n/client";
import { useAppShell } from "@/components/shell/app-shell-context";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import type { ScheduledTask } from "@/features/scheduled-tasks/types";

type StatusBadgeVariant = "default" | "secondary" | "destructive" | "outline";

interface ScheduledTasksTableProps {
  tasks: ScheduledTask[];
  savingId: string | null;
  onToggleEnabled: (task: ScheduledTask) => void;
  onOpen: (task: ScheduledTask) => void;
  onEdit: (task: ScheduledTask) => void;
  onTrigger: (task: ScheduledTask) => void;
  onDelete: (task: ScheduledTask) => void;
}

export function ScheduledTasksTable({
  tasks,
  savingId,
  onToggleEnabled,
  onOpen,
  onEdit,
  onTrigger,
  onDelete,
}: ScheduledTasksTableProps) {
  const { t } = useT("translation");
  const { lng } = useAppShell();

  const statusLabel = (status: string | null | undefined) => {
    const normalized = (status || "").trim().toLowerCase();
    if (!normalized || normalized === "-") return "-";
    const known = new Set([
      "queued",
      "claimed",
      "running",
      "completed",
      "failed",
      "canceled",
    ]);
    const key = known.has(normalized) ? normalized : "unknown";
    return t(`library.scheduledTasks.status.${key}`);
  };

  const statusVariant = (
    status: string | null | undefined,
  ): StatusBadgeVariant => {
    const normalized = (status || "").trim().toLowerCase();
    if (normalized === "completed") return "default" as const;
    if (
      normalized === "running" ||
      normalized === "claimed" ||
      normalized === "queued"
    ) {
      return "secondary" as const;
    }
    if (normalized === "failed" || normalized === "canceled") {
      return "destructive" as const;
    }
    return "outline" as const;
  };

  const formatDateTime = (
    value: string | null | undefined,
    timeZone: string | null | undefined,
  ) => {
    if (!value) return "-";
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return value;
    try {
      return new Intl.DateTimeFormat(lng, {
        timeZone: timeZone || undefined,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }).format(d);
    } catch {
      return d.toLocaleString();
    }
  };

  const rows = useMemo(() => {
    return tasks.map((task) => {
      return {
        ...task,
        nextRunAt: task.next_run_at,
        lastStatus: task.last_run_status ?? "-",
      };
    });
  }, [tasks]);

  const headerCellClass =
    "px-3 py-4 text-center text-xs font-semibold uppercase tracking-wide text-foreground first:pl-[var(--table-gutter)] last:pr-[var(--table-gutter)]";
  const cellClass =
    "px-3 py-4 text-center align-middle text-foreground first:pl-[var(--table-gutter)] last:pr-[var(--table-gutter)]";
  const hasRows = rows.length > 0;

  return (
    <div className="rounded-2xl border border-border/70 bg-card/80 shadow-sm">
      <div className="w-full overflow-x-auto rounded-2xl [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <table className="w-full min-w-[760px] whitespace-nowrap text-sm [--table-gutter:1.25rem] sm:[--table-gutter:1.75rem]">
          <thead className="bg-muted/40 text-muted-foreground/80">
            <tr>
              <th scope="col" className={headerCellClass}>
                {t("library.scheduledTasks.fields.name")}
              </th>
              <th scope="col" className={headerCellClass}>
                {t("library.scheduledTasks.fields.enabled")}
              </th>
              <th scope="col" className={headerCellClass}>
                {t("library.scheduledTasks.fields.cron")}
              </th>
              <th scope="col" className={headerCellClass}>
                {t("library.scheduledTasks.fields.timezone")}
              </th>
              <th scope="col" className={headerCellClass}>
                {t("library.scheduledTasks.fields.nextRunAt")}
              </th>
              <th scope="col" className={headerCellClass}>
                {t("library.scheduledTasks.fields.lastStatus")}
              </th>
              <th scope="col" className={headerCellClass}>
                {t("library.scheduledTasks.fields.actions")}
              </th>
            </tr>
          </thead>
          <tbody className="[&_tr]:border-t [&_tr]:border-border/60 [&_tr:first-child]:border-t-0 [&_tr]:transition-colors [&_tr:hover]:bg-muted/20">
            {!hasRows ? (
              <tr>
                <td
                  colSpan={7}
                  className="h-[320px] px-3 py-12 text-center text-foreground align-middle first:pl-[var(--table-gutter)] last:pr-[var(--table-gutter)]"
                >
                  {t("library.scheduledTasks.page.empty")}
                </td>
              </tr>
            ) : null}
            {rows.map((task) => {
              const busy = savingId === task.scheduled_task_id;
              return (
                <tr key={task.scheduled_task_id}>
                  <td className={`${cellClass} font-medium`}>
                    <Button
                      variant="ghost"
                      className="px-0 h-auto justify-center text-foreground hover:text-foreground"
                      onClick={() => onOpen(task)}
                      disabled={busy}
                      title={task.name}
                    >
                      <span className="max-w-[320px] truncate text-center">
                        {task.name}
                      </span>
                    </Button>
                  </td>
                  <td className={cellClass}>
                    <Switch
                      checked={task.enabled}
                      onCheckedChange={() => onToggleEnabled(task)}
                      disabled={busy}
                    />
                  </td>
                  <td className={cellClass}>{task.cron}</td>
                  <td className={cellClass}>{task.timezone}</td>
                  <td className={cellClass}>
                    {formatDateTime(task.nextRunAt, task.timezone)}
                  </td>
                  <td className={cellClass}>
                    <Badge
                      variant={statusVariant(task.lastStatus)}
                      className="capitalize"
                    >
                      {statusLabel(task.lastStatus)}
                    </Badge>
                  </td>
                  <td className={cellClass}>
                    <div className="flex flex-wrap items-center justify-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        className="gap-2"
                        onClick={() => onEdit(task)}
                        disabled={busy}
                      >
                        <Pencil className="size-4" />
                        {t("library.scheduledTasks.detail.edit")}
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="gap-2"
                        onClick={() => onTrigger(task)}
                        disabled={busy}
                      >
                        <Play className="size-4" />
                        {t("library.scheduledTasks.page.trigger")}
                      </Button>
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button
                            size="sm"
                            variant="destructive"
                            className="gap-2"
                            disabled={busy}
                          >
                            <Trash2 className="size-4" />
                            {t("common.delete")}
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>
                              {t("library.scheduledTasks.detail.deleteTitle")}
                            </AlertDialogTitle>
                            <AlertDialogDescription>
                              {t(
                                "library.scheduledTasks.detail.deleteDescription",
                              )}
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>
                              {t("common.cancel")}
                            </AlertDialogCancel>
                            <AlertDialogAction onClick={() => onDelete(task)}>
                              {t("common.delete")}
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
