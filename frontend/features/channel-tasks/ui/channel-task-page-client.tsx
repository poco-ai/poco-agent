"use client";

import * as React from "react";
import Link from "next/link";
import {
  CheckCheck,
  ChevronRight,
  CircleDashed,
  Columns3,
  Flag,
  Hash,
  LayoutList,
  LoaderCircle,
  Plus,
  RefreshCw,
} from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";

import { PageHeaderShell } from "@/components/shared/page-header-shell";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { channelTasksApi } from "@/features/channel-tasks/api/channel-tasks-api";
import {
  buildChannelTaskColumns,
  buildChannelTaskListGroups,
  moveChannelTask,
  resolveChannelTaskView,
} from "@/features/channel-tasks/lib/channel-task-board";
import type {
  ChannelTaskActorSummary,
  ChannelTask,
  ChannelTaskCreateInput,
  ChannelTaskStatus,
  ChannelTaskView,
} from "@/features/channel-tasks/model/types";
import { ChannelTaskDetailDialog } from "@/features/channel-tasks/ui/channel-task-detail-dialog";
import { serversApi } from "@/features/servers";
import type {
  ServerChannelItem,
  ServerItem,
} from "@/features/servers/model/types";
import { useLanguage } from "@/hooks/use-language";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

const PRIORITY_TONE: Record<string, string> = {
  urgent: "text-red-500",
  high: "text-red-500",
  medium: "text-amber-500",
  low: "text-muted-foreground",
};

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function StatusIcon({ status }: { status: ChannelTaskStatus }) {
  if (status === "in_progress") {
    return <LoaderCircle className="size-3.5 text-primary" />;
  }
  if (status === "in_review") {
    return <ChevronRight className="size-3.5 text-primary" />;
  }
  if (status === "done") {
    return <CheckCheck className="size-3.5 text-primary" />;
  }
  return <CircleDashed className="size-3.5 text-muted-foreground" />;
}

function getActorInitials(actor: ChannelTaskActorSummary | null | undefined) {
  const label = actor?.label?.trim() || "?";
  return label
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");
}

function TaskActorPill({
  label,
  actor,
  fallback,
}: {
  label: string;
  actor: ChannelTaskActorSummary | null | undefined;
  fallback: string;
}) {
  return (
    <span className="inline-flex min-w-0 items-center gap-1.5 rounded-md border border-border/60 bg-background/70 px-2 py-1">
      <Avatar className="size-4">
        <AvatarImage src={actor?.avatarUrl ?? undefined} alt="" />
        <AvatarFallback className="text-[10px]">
          {getActorInitials(actor)}
        </AvatarFallback>
      </Avatar>
      <span className="min-w-0 truncate">
        {label}: {actor?.label?.trim() || fallback}
      </span>
    </span>
  );
}

function CreateTaskDialog({
  open,
  onOpenChange,
  onCreate,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreate: (input: ChannelTaskCreateInput) => Promise<void>;
}) {
  const { t } = useT("translation");
  const [title, setTitle] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [isSaving, setIsSaving] = React.useState(false);

  React.useEffect(() => {
    if (!open) {
      setTitle("");
      setDescription("");
      setIsSaving(false);
    }
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("channelTasks.create.title")}</DialogTitle>
          <DialogDescription>
            {t("channelTasks.create.description")}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <Input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder={t("channelTasks.create.titlePlaceholder")}
            autoFocus
          />
          <Textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder={t("channelTasks.create.descriptionPlaceholder")}
            rows={4}
            className="rounded-xl border-border/60 bg-background/80 shadow-none"
          />
        </div>
        <DialogFooter>
          <Button
            type="button"
            disabled={isSaving || !title.trim()}
            onClick={() => {
              setIsSaving(true);
              void onCreate({ title, description }).finally(() =>
                setIsSaving(false),
              );
            }}
          >
            {t("channelTasks.actions.createTask")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function TaskCard({
  task,
  view,
  onDragStart,
  onDropBefore,
  onOpenTask,
}: {
  task: ChannelTask;
  view: ChannelTaskView;
  onDragStart?: (taskId: string) => void;
  onDropBefore?: (targetTaskId: string, status: ChannelTaskStatus) => void;
  onOpenTask?: (taskId: string) => void;
}) {
  const { t } = useT("translation");
  const priorityTone =
    PRIORITY_TONE[task.priority ?? "medium"] ?? PRIORITY_TONE.medium;

  return (
    <article
      draggable={view === "board"}
      onDragStart={() => onDragStart?.(task.taskId)}
      onClick={() => onOpenTask?.(task.taskId)}
      onDragOver={(event) => {
        if (view === "board") {
          event.preventDefault();
        }
      }}
      onDrop={(event) => {
        if (view === "board") {
          event.preventDefault();
          onDropBefore?.(task.taskId, task.status);
        }
      }}
      className={cn(
        "min-w-0 rounded-2xl border border-border/70 bg-card p-4 transition-shadow",
        view === "board" && "cursor-grab hover:shadow-[var(--shadow-md)]",
      )}
    >
      <div className="space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 space-y-1.5">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <StatusIcon status={task.status} />
              <span className="font-medium text-foreground">
                #{task.displayNumber}
              </span>
              <span>{t(`channelTasks.statuses.${task.status}`)}</span>
            </div>
            <h3 className="line-clamp-2 text-sm font-semibold text-foreground">
              {task.title}
            </h3>
          </div>
          <Badge variant="outline" className="shrink-0">
            <Flag className={cn("size-3.5", priorityTone)} />
            {t(`channelTasks.priorities.${task.priority ?? "medium"}`)}
          </Badge>
        </div>
        {task.description ? (
          <p className="line-clamp-3 text-sm text-muted-foreground">
            {task.description}
          </p>
        ) : null}
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <TaskActorPill
            label={t("channelTasks.detail.creator")}
            actor={task.creator}
            fallback={t("channelTasks.detail.unknownActor")}
          />
          <TaskActorPill
            label={t("channelTasks.detail.assignee")}
            actor={task.assignee}
            fallback={t("channelTasks.detail.unassigned")}
          />
          <Badge variant="secondary">{t("channelTasks.threadReady")}</Badge>
          <span>
            {t("channelTasks.updatedAt", {
              date: formatDateTime(task.updatedAt),
            })}
          </span>
        </div>
      </div>
    </article>
  );
}

export function ChannelTaskPageClient({
  serverId,
  channelId,
}: {
  serverId: string;
  channelId: string;
}) {
  const { t } = useT("translation");
  const lng = useLanguage() || "en";
  const router = useRouter();
  const searchParams = useSearchParams();

  const [servers, setServers] = React.useState<ServerItem[]>([]);
  const [channels, setChannels] = React.useState<ServerChannelItem[]>([]);
  const [tasks, setTasks] = React.useState<ChannelTask[]>([]);
  const [isLoading, setIsLoading] = React.useState(true);
  const [isRefreshing, setIsRefreshing] = React.useState(false);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [draggingTaskId, setDraggingTaskId] = React.useState<string | null>(
    null,
  );

  const view = resolveChannelTaskView(searchParams.get("view"));
  const selectedTaskId = searchParams.get("task");
  const selectedServer =
    servers.find((server) => server.id === serverId) ?? null;
  const selectedChannel =
    channels.find((channel) => channel.id === channelId) ?? null;
  const columns = React.useMemo(() => buildChannelTaskColumns(tasks), [tasks]);
  const listGroups = React.useMemo(
    () => buildChannelTaskListGroups(tasks),
    [tasks],
  );

  const loadPage = React.useCallback(async () => {
    setIsLoading(true);
    try {
      const [nextServers, nextChannels, nextTasks] = await Promise.all([
        serversApi.listServers(),
        serversApi.listChannels(serverId),
        channelTasksApi.listTasks(serverId, channelId),
      ]);
      setServers(nextServers);
      setChannels(nextChannels);
      setTasks(nextTasks);
    } catch (error) {
      console.error("[ChannelTasks] load failed", error);
      toast.error(t("channelTasks.toasts.loadFailed"));
    } finally {
      setIsLoading(false);
    }
  }, [channelId, serverId, t]);

  React.useEffect(() => {
    void loadPage();
  }, [loadPage]);

  const updateView = (nextView: ChannelTaskView) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("view", nextView);
    router.replace(
      `/${lng}/servers/${serverId}/channels/${channelId}?${params.toString()}`,
      {
        scroll: false,
      },
    );
  };

  const openTask = (taskId: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("task", taskId);
    router.replace(
      `/${lng}/servers/${serverId}/channels/${channelId}?${params.toString()}`,
      {
        scroll: false,
      },
    );
  };

  const closeTask = () => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete("task");
    router.replace(
      `/${lng}/servers/${serverId}/channels/${channelId}${params.toString() ? `?${params.toString()}` : ""}`,
      {
        scroll: false,
      },
    );
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await loadPage();
    setIsRefreshing(false);
  };

  const handleCreateTask = async (input: ChannelTaskCreateInput) => {
    try {
      const task = await channelTasksApi.createTask(serverId, channelId, input);
      setTasks((current) => [task, ...current]);
      setDialogOpen(false);
      toast.success(t("channelTasks.toasts.created"));
    } catch (error) {
      console.error("[ChannelTasks] create failed", error);
      toast.error(t("channelTasks.toasts.createFailed"));
    }
  };

  const moveTask = async (move: {
    taskId: string;
    status: ChannelTaskStatus;
    position: number;
  }) => {
    const previousTasks = tasks;
    const optimisticTasks = moveChannelTask(previousTasks, move);
    setTasks(optimisticTasks);
    try {
      const updatedTask = await channelTasksApi.updateTaskStatus(
        serverId,
        channelId,
        move.taskId,
        {
          status: move.status,
          position: move.position,
        },
      );
      setTasks((current) =>
        moveChannelTask(
          current.map((task) =>
            task.taskId === updatedTask.taskId ? updatedTask : task,
          ),
          {
            taskId: updatedTask.taskId,
            status: updatedTask.status,
            position: updatedTask.position,
          },
        ),
      );
    } catch (error) {
      console.error("[ChannelTasks] move failed", error);
      setTasks(previousTasks);
      toast.error(t("channelTasks.toasts.moveFailed"));
    }
  };

  const statusCounts = React.useMemo(
    () =>
      columns.map((column) => ({
        status: column.status,
        count: column.tasks.length,
      })),
    [columns],
  );

  return (
    <>
      <PageHeaderShell
        left={
          <div className="min-w-0 space-y-1.5">
            <p className="truncate text-base font-semibold leading-tight text-foreground">
              {selectedChannel?.name ?? t("channelTasks.title")}
            </p>
            <p className="truncate text-xs text-muted-foreground">
              {selectedServer
                ? t("channelTasks.subtitle", {
                    server: selectedServer.name,
                    channel: selectedChannel?.name ?? channelId,
                  })
                : t("channelTasks.loading")}
            </p>
          </div>
        }
        right={
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void handleRefresh()}
              disabled={isRefreshing}
            >
              <RefreshCw
                className={cn("size-4", isRefreshing && "animate-spin")}
              />
              {t("channelTasks.actions.refresh")}
            </Button>
            <Button type="button" size="sm" onClick={() => setDialogOpen(true)}>
              <Plus className="size-4" />
              {t("channelTasks.actions.newTask")}
            </Button>
          </div>
        }
      />

      <main className="flex-1 overflow-auto px-4 pb-6 pt-8 sm:px-6">
        <div className="mx-auto flex max-w-none flex-col gap-6">
          <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto]">
            <div className="rounded-3xl border border-border/70 bg-card px-5 py-5">
              <div className="space-y-1.5">
                <p className="text-sm font-semibold text-foreground">
                  {selectedChannel?.name ?? channelId}
                </p>
                <p className="text-sm text-muted-foreground">
                  {t("channelTasks.channelDescription")}
                </p>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {statusCounts.map((item) => (
                  <Badge
                    key={item.status}
                    variant="secondary"
                    className="gap-1.5"
                  >
                    <StatusIcon status={item.status} />
                    {t(`channelTasks.statuses.${item.status}`)}
                    <span className="tabular-nums">{item.count}</span>
                  </Badge>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-2 rounded-3xl border border-border/70 bg-card p-2">
              <Button
                type="button"
                variant={view === "list" ? "default" : "ghost"}
                size="sm"
                onClick={() => updateView("list")}
              >
                <LayoutList className="size-4" />
                {t("channelTasks.views.list")}
              </Button>
              <Button
                type="button"
                variant={view === "board" ? "default" : "ghost"}
                size="sm"
                onClick={() => updateView("board")}
              >
                <Columns3 className="size-4" />
                {t("channelTasks.views.board")}
              </Button>
            </div>
          </section>

          {isLoading ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {Array.from({ length: 4 }).map((_, index) => (
                <Skeleton key={index} className="h-44 rounded-3xl" />
              ))}
            </div>
          ) : tasks.length === 0 ? (
            <Empty className="min-h-80 rounded-3xl border border-dashed border-border bg-muted/10">
              <EmptyContent>
                <EmptyMedia variant="icon">
                  <Hash className="size-5" />
                </EmptyMedia>
                <EmptyHeader>
                  <EmptyTitle>{t("channelTasks.empty.title")}</EmptyTitle>
                  <EmptyDescription>
                    {t("channelTasks.empty.description")}
                  </EmptyDescription>
                </EmptyHeader>
              </EmptyContent>
            </Empty>
          ) : view === "list" ? (
            <div className="space-y-6">
              {listGroups.map((group) => (
                <section key={group.status} className="space-y-3">
                  <div className="flex items-center gap-3 px-1">
                    <StatusIcon status={group.status} />
                    <h2 className="text-sm font-semibold text-foreground">
                      {t(`channelTasks.statuses.${group.status}`)}
                    </h2>
                    <span className="text-xs text-muted-foreground tabular-nums">
                      {group.tasks.length}
                    </span>
                  </div>
                  <div className="grid gap-3 xl:grid-cols-2">
                    {group.tasks.map((task) => (
                      <TaskCard
                        key={task.taskId}
                        task={task}
                        view="list"
                        onOpenTask={openTask}
                      />
                    ))}
                  </div>
                </section>
              ))}
            </div>
          ) : (
            <div className="grid gap-4 xl:grid-cols-4">
              {columns.map((column) => (
                <section
                  key={column.status}
                  className="rounded-3xl border border-border/70 bg-muted/10 p-3"
                  onDragOver={(event) => {
                    event.preventDefault();
                  }}
                  onDrop={(event) => {
                    event.preventDefault();
                    if (!draggingTaskId) {
                      return;
                    }
                    void moveTask({
                      taskId: draggingTaskId,
                      status: column.status,
                      position: column.tasks.length,
                    });
                    setDraggingTaskId(null);
                  }}
                >
                  <div className="mb-3 flex items-center justify-between gap-3 px-1">
                    <div className="flex items-center gap-2">
                      <StatusIcon status={column.status} />
                      <h2 className="text-sm font-semibold text-foreground">
                        {t(`channelTasks.statuses.${column.status}`)}
                      </h2>
                    </div>
                    <Badge variant="outline" className="tabular-nums">
                      {column.tasks.length}
                    </Badge>
                  </div>
                  <div className="space-y-3">
                    {column.tasks.map((task, index) => (
                      <TaskCard
                        key={task.taskId}
                        task={task}
                        view="board"
                        onDragStart={(taskId) => setDraggingTaskId(taskId)}
                        onDropBefore={(targetTaskId, status) => {
                          if (
                            !draggingTaskId ||
                            draggingTaskId === targetTaskId
                          ) {
                            return;
                          }
                          void moveTask({
                            taskId: draggingTaskId,
                            status,
                            position: index,
                          });
                          setDraggingTaskId(null);
                        }}
                        onOpenTask={openTask}
                      />
                    ))}
                    <button
                      type="button"
                      className="flex min-h-24 w-full items-center justify-center rounded-2xl border border-dashed border-border/70 bg-background/70 px-3 text-xs text-muted-foreground"
                      onDragOver={(event) => event.preventDefault()}
                      onDrop={(event) => {
                        event.preventDefault();
                        if (!draggingTaskId) {
                          return;
                        }
                        void moveTask({
                          taskId: draggingTaskId,
                          status: column.status,
                          position: column.tasks.length,
                        });
                        setDraggingTaskId(null);
                      }}
                    >
                      {t("channelTasks.dropzone")}
                    </button>
                  </div>
                </section>
              ))}
            </div>
          )}

          <div className="rounded-3xl border border-border/70 bg-card px-5 py-4 text-sm text-muted-foreground">
            <p>{t("channelTasks.urlHint", { view })}</p>
            <Link
              href={`/${lng}/servers`}
              className="mt-2 inline-flex items-center gap-2 text-sm font-medium text-primary"
            >
              {t("channelTasks.backToServers")}
              <ChevronRight className="size-4" />
            </Link>
          </div>
        </div>
      </main>

      <CreateTaskDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onCreate={handleCreateTask}
      />
      <ChannelTaskDetailDialog
        open={Boolean(selectedTaskId)}
        onOpenChange={(nextOpen) => {
          if (!nextOpen) {
            closeTask();
          }
        }}
        serverId={serverId}
        channelId={channelId}
        taskId={selectedTaskId}
        onTaskUpdated={(nextTask) => {
          setTasks((current) =>
            current.map((task) =>
              task.taskId === nextTask.taskId ? nextTask : task,
            ),
          );
        }}
      />
    </>
  );
}
