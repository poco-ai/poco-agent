"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Pencil, Play, RefreshCw, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { useT } from "@/lib/i18n/client";
import { useAppShell } from "@/components/shell/app-shell-context";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
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
import { scheduledTasksService } from "@/features/scheduled-tasks/api/scheduled-tasks-api";
import type {
  ScheduledTask,
  ScheduledTaskUpdateInput,
} from "@/features/scheduled-tasks/types";
import type { RunResponse } from "@/features/chat/types/api/run";
import {
  formatScheduleSummary,
  inferScheduleFromCron,
} from "@/features/scheduled-tasks/utils/schedule";
import { ScheduledTaskEditDialog } from "@/features/scheduled-tasks/components/scheduled-task-edit-dialog";

function formatDateTime(
  value: string | null | undefined,
  opts: { locale: string; timeZone?: string | null },
): string {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  try {
    return new Intl.DateTimeFormat(opts.locale, {
      timeZone: opts.timeZone || undefined,
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
}

function formatDurationLabel(
  durationMs: number,
  t: (key: string, options?: Record<string, unknown>) => string,
): string {
  const totalSeconds = Math.max(0, Math.floor(durationMs / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return minutes > 0
    ? t("library.scheduledTasks.detail.durationMinutesSeconds", {
        minutes,
        seconds,
      })
    : t("library.scheduledTasks.detail.durationSeconds", { seconds });
}

function pickNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function formatCostUsd(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "-";
  return `$${value.toFixed(6)}`;
}

export function ScheduledTaskDetailPageClient({ taskId }: { taskId: string }) {
  const { t } = useT("translation");
  const router = useRouter();
  const { lng } = useAppShell();

  const [task, setTask] = useState<ScheduledTask | null>(null);
  const [runs, setRuns] = useState<RunResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [saving, setSaving] = useState<string | null>(null);
  const [editOpen, setEditOpen] = useState(false);

  const tzName = task?.timezone ?? "UTC";
  const scheduleSummary = useMemo(() => {
    if (!task?.cron) return "-";
    const inferred = inferScheduleFromCron(task.cron);
    return formatScheduleSummary(inferred, t);
  }, [task?.cron, t]);

  const statusLabel = useCallback(
    (status: string | null | undefined) => {
      const normalized = (status || "").trim().toLowerCase();
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
    },
    [t],
  );

  const refresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const [taskResp, runsResp] = await Promise.all([
        scheduledTasksService.get(taskId),
        scheduledTasksService.listRuns(taskId),
      ]);
      setTask(taskResp);
      setRuns(runsResp);
    } catch (error) {
      console.error("[ScheduledTasks] detail refresh failed", error);
      toast.error(t("library.scheduledTasks.toasts.error"));
    } finally {
      setIsRefreshing(false);
    }
  }, [t, taskId]);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      try {
        const [taskResp, runsResp] = await Promise.all([
          scheduledTasksService.get(taskId),
          scheduledTasksService.listRuns(taskId),
        ]);
        setTask(taskResp);
        setRuns(runsResp);
      } catch (error) {
        console.error("[ScheduledTasks] detail load failed", error);
        toast.error(t("library.scheduledTasks.toasts.error"));
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, [t, taskId]);

  const updateTask = useCallback(
    async (input: ScheduledTaskUpdateInput) => {
      setSaving("update");
      try {
        const updated = await scheduledTasksService.update(taskId, input);
        setTask(updated);
        toast.success(t("library.scheduledTasks.toasts.updated"));
      } catch (error) {
        console.error("[ScheduledTasks] update failed", error);
        toast.error(t("library.scheduledTasks.toasts.error"));
      } finally {
        setSaving(null);
      }
    },
    [t, taskId],
  );

  const trigger = useCallback(async () => {
    setSaving("trigger");
    try {
      const resp = await scheduledTasksService.trigger(taskId);
      toast.success(t("library.scheduledTasks.toasts.triggered"));
      await refresh();
      router.push(`/${lng}/chat/${resp.session_id}`);
    } catch (error) {
      console.error("[ScheduledTasks] trigger failed", error);
      toast.error(t("library.scheduledTasks.toasts.error"));
    } finally {
      setSaving(null);
    }
  }, [lng, refresh, router, t, taskId]);

  const remove = useCallback(async () => {
    setSaving("delete");
    try {
      await scheduledTasksService.remove(taskId);
      toast.success(t("library.scheduledTasks.toasts.deleted"));
      router.push(`/${lng}/capabilities/scheduled-tasks`);
    } catch (error) {
      console.error("[ScheduledTasks] delete failed", error);
      toast.error(t("library.scheduledTasks.toasts.error"));
    } finally {
      setSaving(null);
    }
  }, [lng, router, t, taskId]);

  return (
    <>
      <header className="flex h-16 shrink-0 items-center justify-between border-b border-border/50 bg-background/50 px-6 backdrop-blur-sm sticky top-0 z-10 font-serif">
        <div className="flex items-center gap-3 min-w-0">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => router.push(`/${lng}/capabilities/scheduled-tasks`)}
            className="mr-2"
          >
            <ArrowLeft className="size-5" />
          </Button>
          <div className="min-w-0">
            <div className="truncate text-lg font-bold tracking-tight">
              {task?.name || t("library.scheduledTasks.detail.title")}
            </div>
            {task ? (
              <div className="text-xs text-muted-foreground truncate">
                {t("library.scheduledTasks.detail.subtitle", {
                  schedule: scheduleSummary,
                })}
              </div>
            ) : null}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => refresh()}
            disabled={isRefreshing || isLoading}
          >
            <RefreshCw className="size-4" />
            {t("library.scheduledTasks.detail.refresh")}
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => setEditOpen(true)}
            disabled={!task || saving !== null}
          >
            <Pencil className="size-4" />
            {t("library.scheduledTasks.detail.edit")}
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="gap-2"
            onClick={() => trigger()}
            disabled={!task || saving !== null}
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
                disabled={!task || saving !== null}
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
                  {t("library.scheduledTasks.detail.deleteDescription")}
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>{t("common.cancel")}</AlertDialogCancel>
                <AlertDialogAction onClick={() => remove()}>
                  {t("common.delete")}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </header>

      <div className="flex flex-1 flex-col overflow-hidden">
        <div className="flex flex-1 flex-col px-6 py-6 overflow-auto">
          <div className="w-full max-w-5xl mx-auto space-y-6">
            {isLoading ? (
              <div className="rounded-lg border border-border p-6 text-sm text-muted-foreground">
                {t("actions.processing")}
              </div>
            ) : !task ? (
              <div className="rounded-lg border border-border p-6 text-sm text-muted-foreground">
                {t("library.scheduledTasks.detail.notFound")}
              </div>
            ) : (
              <>
                <div className="rounded-lg border border-border p-4 space-y-4">
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">
                        {t("library.scheduledTasks.fields.enabled")}
                      </div>
                      <div className="flex items-center gap-3">
                        <Switch
                          checked={task.enabled}
                          onCheckedChange={() =>
                            updateTask({ enabled: !task.enabled })
                          }
                          disabled={saving !== null}
                        />
                        <div className="text-sm">
                          {task.enabled
                            ? t("library.scheduledTasks.detail.enabledOn")
                            : t("library.scheduledTasks.detail.enabledOff")}
                        </div>
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">
                        {t("library.scheduledTasks.fields.nextRunAt")}
                      </div>
                      <div className="font-mono text-xs">
                        {formatDateTime(task.next_run_at, {
                          locale: lng,
                          timeZone: tzName,
                        })}
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">
                        {t("library.scheduledTasks.detail.lastRun")}
                      </div>
                      <div className="text-sm">
                        {statusLabel(task.last_run_status)}
                      </div>
                      {task.last_error ? (
                        <div className="text-xs text-destructive line-clamp-2">
                          {task.last_error}
                        </div>
                      ) : null}
                    </div>
                  </div>

                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">
                        {t("library.scheduledTasks.detail.schedule")}
                      </div>
                      <div className="text-sm">{scheduleSummary}</div>
                      <div className="font-mono text-xs text-muted-foreground">
                        {task.cron} · {task.timezone}
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">
                        {t("library.scheduledTasks.fields.reuseSession")}
                      </div>
                      <div className="text-sm">
                        {task.reuse_session
                          ? t("library.scheduledTasks.detail.reuseSessionOn")
                          : t("library.scheduledTasks.detail.reuseSessionOff")}
                      </div>
                      {task.session_id ? (
                        <Button
                          size="sm"
                          variant="link"
                          className="px-0 h-auto"
                          onClick={() =>
                            router.push(`/${lng}/chat/${task.session_id}`)
                          }
                        >
                          {t("library.scheduledTasks.detail.openWorkspace")}
                        </Button>
                      ) : null}
                    </div>
                  </div>
                </div>

                <div className="rounded-lg border border-border p-4 space-y-3">
                  <div className="flex min-w-0 flex-nowrap items-center justify-between gap-3 overflow-x-auto whitespace-nowrap [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                    <div className="text-sm font-medium shrink-0">
                      {t("library.scheduledTasks.fields.prompt")}
                    </div>
                  </div>
                  <div className="whitespace-pre-wrap text-sm text-foreground">
                    {task.prompt}
                  </div>
                </div>

                <div className="rounded-lg border border-border p-4 space-y-3">
                  <div className="flex min-w-0 flex-nowrap items-center justify-between gap-3 overflow-x-auto whitespace-nowrap [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                    <div className="text-sm font-medium shrink-0">
                      {t("library.scheduledTasks.detail.runsTitle")}
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      className="gap-2 shrink-0"
                      onClick={() => refresh()}
                      disabled={isRefreshing}
                    >
                      <RefreshCw className="size-4" />
                      {t("library.scheduledTasks.detail.refresh")}
                    </Button>
                  </div>

                  {runs.length === 0 ? (
                    <div className="py-8 text-sm text-muted-foreground text-center">
                      {t("library.scheduledTasks.detail.noRuns")}
                    </div>
                  ) : (
                    <div className="w-full overflow-x-auto rounded-lg border border-border [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                      <table className="w-full min-w-[720px] whitespace-nowrap text-sm">
                        <thead className="bg-muted/40 text-muted-foreground">
                          <tr>
                            <th className="px-4 py-3 text-left font-medium">
                              {t(
                                "library.scheduledTasks.detail.runTriggeredAt",
                              )}
                            </th>
                            <th className="px-4 py-3 text-left font-medium">
                              {t("library.scheduledTasks.detail.runStatus")}
                            </th>
                            <th className="px-4 py-3 text-left font-medium">
                              {t("library.scheduledTasks.detail.runDuration")}
                            </th>
                            <th className="px-4 py-3 text-left font-medium">
                              {t("library.scheduledTasks.detail.runCost")}
                            </th>
                            <th className="px-4 py-3 text-left font-medium">
                              {t("library.scheduledTasks.detail.runTokens")}
                            </th>
                            <th className="px-4 py-3 text-left font-medium">
                              {t("library.scheduledTasks.detail.runProgress")}
                            </th>
                            <th className="px-4 py-3 text-right font-medium">
                              {t("library.scheduledTasks.fields.actions")}
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {runs.map((run) => {
                            const durationMs =
                              run.started_at && run.finished_at
                                ? new Date(run.finished_at).getTime() -
                                  new Date(run.started_at).getTime()
                                : null;

                            const usageJson = run.usage?.usage_json as
                              | Record<string, unknown>
                              | null
                              | undefined;
                            const inputTokens = pickNumber(
                              usageJson?.input_tokens,
                            );
                            const outputTokens = pickNumber(
                              usageJson?.output_tokens,
                            );
                            const tokensLabel =
                              inputTokens !== null && outputTokens !== null
                                ? `${inputTokens.toLocaleString()}/${outputTokens.toLocaleString()}`
                                : "-";

                            return (
                              <tr
                                key={run.run_id}
                                className="border-t border-border"
                              >
                                <td className="px-4 py-3 font-mono text-xs">
                                  {formatDateTime(run.scheduled_at, {
                                    locale: lng,
                                    timeZone: tzName,
                                  })}
                                </td>
                                <td className="px-4 py-3">
                                  {statusLabel(run.status)}
                                </td>
                                <td className="px-4 py-3 font-mono text-xs">
                                  {durationMs !== null
                                    ? formatDurationLabel(durationMs, t)
                                    : "-"}
                                </td>
                                <td className="px-4 py-3 font-mono text-xs">
                                  {formatCostUsd(run.usage?.total_cost_usd)}
                                </td>
                                <td className="px-4 py-3 font-mono text-xs">
                                  {tokensLabel}
                                </td>
                                <td className="px-4 py-3 font-mono text-xs">
                                  {run.progress}%
                                </td>
                                <td className="px-4 py-3 text-right">
                                  <div className="inline-flex items-center gap-2">
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      onClick={() =>
                                        router.push(
                                          `/${lng}/chat/${run.session_id}`,
                                        )
                                      }
                                    >
                                      {t(
                                        "library.scheduledTasks.detail.viewResult",
                                      )}
                                    </Button>
                                  </div>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      <ScheduledTaskEditDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        task={task}
        isSaving={saving === "update"}
        onSave={async (payload) => {
          await updateTask(payload);
          await refresh();
        }}
      />
    </>
  );
}
