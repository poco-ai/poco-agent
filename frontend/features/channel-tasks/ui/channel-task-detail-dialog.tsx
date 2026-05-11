"use client";

import * as React from "react";
import {
  CheckCheck,
  ChevronRight,
  CircleDashed,
  LoaderCircle,
  Save,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { channelTasksApi } from "@/features/channel-tasks/api/channel-tasks-api";
import type {
  ChannelTask,
  ChannelTaskActorSummary,
  ChannelTaskActivityMessage,
  ChannelTaskMessageContext,
  ChannelTaskStatus,
} from "@/features/channel-tasks/model/types";
import { serversApi } from "@/features/servers";
import type {
  ServerAgentItem,
  ServerConversationMessage,
  ServerMemberItem,
} from "@/features/servers/model/types";
import {
  getChannelEventContent,
  getChannelEventLabelKey,
} from "@/features/servers/lib/server-conversation-messages";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";
import { MessageRow } from "@/features/servers/ui/conversation-message-row";

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

function formatEventLabel(
  message: ChannelTaskActivityMessage,
  t: (key: string, options?: Record<string, unknown>) => string,
): { actor: string; label: string } | null {
  const event = getChannelEventContent(toConversationMessage(message));
  if (!event) {
    return null;
  }
  const actor = event.actorLabel?.trim() || t("conversationView.events.actor");
  const assignee = getActorLabel(event.assignee);
  const taskTitle =
    event.taskTitle?.trim() ||
    event.title?.trim() ||
    t("conversationView.events.task");
  const taskNumber =
    event.taskNumber === null || event.taskNumber === undefined
      ? ""
      : String(event.taskNumber);
  const task = taskNumber ? `#${taskNumber}: ${taskTitle}` : taskTitle;
  const labelKey =
    event.eventType === "task.created" && assignee
      ? "conversationView.events.taskCreatedAssigned"
      : getChannelEventLabelKey(event.eventType);
  return {
    actor,
    label: t(labelKey, {
      actor,
      target: event.targetLabel ?? actor,
      task,
      taskTitle,
      taskNumber,
      assignee,
      fromAssignee: getActorLabel(event.fromAssignee),
      toAssignee: getActorLabel(event.toAssignee),
      comment: event.commentText ?? "",
      fromStatus: event.fromStatus ?? "",
      toStatus: event.toStatus ?? event.status ?? "",
    }),
  };
}

function getActorLabel(value: unknown): string {
  if (!value || typeof value !== "object") {
    return "";
  }
  const label = (value as { label?: unknown }).label;
  return typeof label === "string" ? label.trim() : "";
}

function toConversationMessage(
  message: ChannelTaskActivityMessage,
): ServerConversationMessage {
  return {
    id: message.messageId,
    channelId: message.channelId,
    authorUserId: message.authorUserId,
    messageType: message.messageType,
    content: message.content,
    textPreview: message.textPreview,
    threadRootMessageId: message.threadRootMessageId,
    replyCount: 0,
    reactions: [],
    createdAt: message.createdAt,
    updatedAt: message.updatedAt,
  };
}

function ActorSummaryLine({
  label,
  actor,
  fallback,
}: {
  label: string;
  actor: ChannelTaskActorSummary | null | undefined;
  fallback: string;
}) {
  return (
    <div className="min-w-0 rounded-md border border-border/60 bg-background/70 px-3 py-2">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className="mt-1 truncate text-sm font-medium text-foreground">
        {actor?.label?.trim() || fallback}
      </p>
    </div>
  );
}

function ActivityItem({
  message,
  onOpenContext,
}: {
  message: ChannelTaskActivityMessage;
  onOpenContext: (messageId: string) => void;
}) {
  const { t } = useT("translation");
  const eventLabel = formatEventLabel(message, t);
  return (
    <button
      type="button"
      onClick={() => onOpenContext(message.messageId)}
      className="w-full rounded-md border border-border/60 bg-background/70 px-4 py-3 text-left transition-colors hover:bg-muted/20"
    >
      <div className="flex min-w-0 items-center justify-between gap-3">
        <p className="min-w-0 flex-1 truncate text-sm text-muted-foreground">
          {eventLabel ? (
            <>
              <span className="font-medium underline decoration-muted-foreground/50 underline-offset-4">
                {eventLabel.actor}
              </span>
              {eventLabel.label.startsWith(eventLabel.actor)
                ? eventLabel.label.slice(eventLabel.actor.length)
                : ` ${eventLabel.label}`}
            </>
          ) : (
            message.textPreview || t("conversationView.emptyMessage")
          )}
        </p>
        <span className="text-xs text-muted-foreground">
          {formatDateTime(message.createdAt)}
        </span>
      </div>
    </button>
  );
}

export function ChannelTaskDetailDialog({
  open,
  onOpenChange,
  serverId,
  channelId,
  taskId,
  onTaskUpdated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  serverId: string;
  channelId: string;
  taskId: string | null;
  onTaskUpdated: (task: ChannelTask) => void;
}) {
  const { t } = useT("translation");
  const [task, setTask] = React.useState<ChannelTask | null>(null);
  const [activity, setActivity] = React.useState<ChannelTaskActivityMessage[]>(
    [],
  );
  const [members, setMembers] = React.useState<ServerMemberItem[]>([]);
  const [agents, setAgents] = React.useState<ServerAgentItem[]>([]);
  const [context, setContext] =
    React.useState<ChannelTaskMessageContext | null>(null);
  const [highlightMessageId, setHighlightMessageId] = React.useState<
    string | null
  >(null);
  const [isLoading, setIsLoading] = React.useState(false);
  const [isSaving, setIsSaving] = React.useState(false);
  const [title, setTitle] = React.useState("");
  const [description, setDescription] = React.useState("");

  const loadTask = React.useCallback(async () => {
    if (!open || !taskId) {
      return;
    }
    setIsLoading(true);
    try {
      const nextTask = await channelTasksApi.getTask(
        serverId,
        channelId,
        taskId,
      );
      setTask(nextTask);
      setTitle(nextTask.title);
      setDescription(nextTask.description ?? "");
      setContext(null);
      setHighlightMessageId(null);
      setActivity(
        nextTask.threadRootMessageId
          ? await channelTasksApi.getTaskThread(
              serverId,
              channelId,
              nextTask.threadRootMessageId,
            )
          : [],
      );
    } catch (error) {
      console.error("[ChannelTasks] detail load failed", error);
      toast.error(t("channelTasks.toasts.detailLoadFailed"));
    } finally {
      setIsLoading(false);
    }
  }, [channelId, open, serverId, t, taskId]);

  React.useEffect(() => {
    void loadTask();
  }, [loadTask]);

  React.useEffect(() => {
    if (!open) {
      return;
    }
    void Promise.all([
      serversApi.listMembers(serverId),
      serversApi.listChannelAgents(serverId, channelId),
    ])
      .then(([nextMembers, nextAgents]) => {
        setMembers(nextMembers.filter((member) => member.status === "active"));
        setAgents(nextAgents);
      })
      .catch((error) => {
        console.error("[ChannelTasks] assignee options load failed", error);
      });
  }, [channelId, open, serverId]);

  const syncTask = (nextTask: ChannelTask) => {
    setTask(nextTask);
    setTitle(nextTask.title);
    setDescription(nextTask.description ?? "");
    onTaskUpdated(nextTask);
  };

  const handleSave = async () => {
    if (!taskId) {
      return;
    }
    setIsSaving(true);
    try {
      const nextTask = await channelTasksApi.updateTask(
        serverId,
        channelId,
        taskId,
        {
          title,
          description,
        },
      );
      syncTask(nextTask);
      toast.success(t("channelTasks.toasts.updated"));
    } catch (error) {
      console.error("[ChannelTasks] update failed", error);
      toast.error(t("channelTasks.toasts.updateFailed"));
    } finally {
      setIsSaving(false);
    }
  };

  const handleClaimToggle = async () => {
    if (!taskId || !task) {
      return;
    }
    setIsSaving(true);
    try {
      const nextTask =
        task.assigneeUserId ||
        task.assigneePresetId ||
        task.assigneeAgentIdentityId
          ? await channelTasksApi.unclaimTask(serverId, channelId, taskId)
          : await channelTasksApi.claimTask(serverId, channelId, taskId);
      syncTask(nextTask);
      await loadTask();
      toast.success(
        task.assigneeUserId ||
          task.assigneePresetId ||
          task.assigneeAgentIdentityId
          ? t("channelTasks.toasts.unclaimed")
          : t("channelTasks.toasts.claimed"),
      );
    } catch (error) {
      console.error("[ChannelTasks] claim toggle failed", error);
      toast.error(t("channelTasks.toasts.claimFailed"));
    } finally {
      setIsSaving(false);
    }
  };

  const handleAssigneeChange = async (value: string) => {
    if (!taskId) {
      return;
    }
    setIsSaving(true);
    const [kind, id] = value.split(":", 2);
    try {
      const nextTask = await channelTasksApi.updateTask(
        serverId,
        channelId,
        taskId,
        {
          title,
          description,
          assigneeUserId: kind === "user" ? id : null,
          assigneeAgentIdentityId: kind === "agent" ? id : null,
          assigneePresetId: null,
        },
      );
      syncTask(nextTask);
      await loadTask();
      toast.success(t("channelTasks.toasts.assigneeUpdated"));
    } catch (error) {
      console.error("[ChannelTasks] assignee update failed", error);
      toast.error(t("channelTasks.toasts.assigneeFailed"));
    } finally {
      setIsSaving(false);
    }
  };

  const handleOpenContext = async (messageId: string) => {
    setHighlightMessageId(messageId);
    try {
      setContext(
        await channelTasksApi.getMessageContext(serverId, channelId, messageId),
      );
    } catch (error) {
      console.error("[ChannelTasks] context load failed", error);
      toast.error(t("channelTasks.toasts.contextFailed"));
    }
  };

  const handleStatusChange = async (status: ChannelTaskStatus) => {
    if (!taskId || !task) {
      return;
    }
    setIsSaving(true);
    try {
      const nextTask = await channelTasksApi.updateTaskStatus(
        serverId,
        channelId,
        taskId,
        {
          status,
          position: task.position,
        },
      );
      syncTask(nextTask);
      await loadTask();
      toast.success(t("channelTasks.toasts.statusUpdated"));
    } catch (error) {
      console.error("[ChannelTasks] status update failed", error);
      toast.error(t("channelTasks.toasts.statusFailed"));
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-hidden sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>{t("channelTasks.detail.title")}</DialogTitle>
          <DialogDescription>
            {t("channelTasks.detail.description")}
          </DialogDescription>
        </DialogHeader>

        {isLoading || !task ? (
          <div className="space-y-4">
            <Skeleton className="h-10 rounded-xl" />
            <Skeleton className="h-32 rounded-2xl" />
            <Skeleton className="h-48 rounded-2xl" />
          </div>
        ) : (
          <div className="grid gap-6 overflow-y-auto pr-1 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
            <section className="space-y-4">
              <div className="rounded-3xl border border-border/70 bg-card p-5">
                <div className="space-y-4">
                  <div className="space-y-1.5">
                    <p className="text-sm font-semibold text-foreground">
                      {t("channelTasks.detail.overview")}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {t("channelTasks.detail.overviewDescription")}
                    </p>
                  </div>
                  <Input
                    value={title}
                    onChange={(event) => setTitle(event.target.value)}
                  />
                  <Textarea
                    value={description}
                    onChange={(event) => setDescription(event.target.value)}
                    rows={6}
                    className="rounded-2xl border-border/60 bg-background/80 shadow-none"
                  />
                  <div className="grid gap-3 sm:grid-cols-2">
                    <ActorSummaryLine
                      label={t("channelTasks.detail.creator")}
                      actor={task.creator}
                      fallback={t("channelTasks.detail.unknownActor")}
                    />
                    <ActorSummaryLine
                      label={t("channelTasks.detail.assignee")}
                      actor={task.assignee}
                      fallback={t("channelTasks.detail.unassigned")}
                    />
                  </div>
                  <label className="block space-y-1.5">
                    <span className="text-xs font-medium text-muted-foreground">
                      {t("channelTasks.detail.assignee")}
                    </span>
                    <select
                      value={
                        task.assigneeAgentIdentityId
                          ? `agent:${task.assigneeAgentIdentityId}`
                          : task.assigneeUserId
                            ? `user:${task.assigneeUserId}`
                            : "none:"
                      }
                      disabled={isSaving}
                      onChange={(event) =>
                        void handleAssigneeChange(event.target.value)
                      }
                      className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground shadow-none"
                    >
                      <option value="none:">
                        {t("channelTasks.detail.unassigned")}
                      </option>
                      {members.map((member) => (
                        <option key={member.id} value={`user:${member.userId}`}>
                          {member.user?.displayName || member.userId}
                        </option>
                      ))}
                      {agents.map((agent) => (
                        <option key={agent.id} value={`agent:${agent.id}`}>
                          @{agent.handle} / {agent.displayName}
                        </option>
                      ))}
                    </select>
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {(
                      ["todo", "in_progress", "in_review", "done"] as const
                    ).map((status) => (
                      <Button
                        key={status}
                        type="button"
                        variant={task.status === status ? "default" : "outline"}
                        size="sm"
                        disabled={isSaving}
                        onClick={() => void handleStatusChange(status)}
                      >
                        <StatusIcon status={status} />
                        {t(`channelTasks.statuses.${status}`)}
                      </Button>
                    ))}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      onClick={() => void handleSave()}
                      disabled={isSaving}
                    >
                      <Save className="size-4" />
                      {t("channelTasks.actions.save")}
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => void handleClaimToggle()}
                      disabled={isSaving}
                    >
                      {task.assigneeUserId ||
                      task.assigneePresetId ||
                      task.assigneeAgentIdentityId
                        ? t("channelTasks.actions.unclaim")
                        : t("channelTasks.actions.claim")}
                    </Button>
                  </div>
                </div>
              </div>

              <div className="rounded-3xl border border-border/70 bg-card p-5">
                <div className="space-y-1.5">
                  <p className="text-sm font-semibold text-foreground">
                    {t("channelTasks.detail.activity")}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {t("channelTasks.detail.activityDescription")}
                  </p>
                </div>
                <div className="mt-4 space-y-3">
                  {activity.length > 0 ? (
                    activity.map((message) => (
                      <ActivityItem
                        key={message.messageId}
                        message={message}
                        onOpenContext={handleOpenContext}
                      />
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      {t("channelTasks.detail.emptyActivity")}
                    </p>
                  )}
                </div>
              </div>
            </section>

            <section className="space-y-4">
              <div className="rounded-3xl border border-border/70 bg-card p-5">
                <div className="space-y-1.5">
                  <p className="text-sm font-semibold text-foreground">
                    {context
                      ? t("channelTasks.detail.context")
                      : t("channelTasks.detail.execution")}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {context
                      ? t("channelTasks.detail.contextDescription")
                      : t("channelTasks.detail.executionDescription")}
                  </p>
                </div>
                {context ? (
                  <div className="mt-4 max-h-[50vh] space-y-2 overflow-y-auto rounded-md border border-border bg-background">
                    {context.messages.map((message) => (
                      <div
                        key={message.messageId}
                        className={cn(
                          "border-b border-border last:border-b-0",
                          message.messageId === highlightMessageId &&
                            "bg-primary/10",
                        )}
                      >
                        <MessageRow
                          message={toConversationMessage(message)}
                          compact
                          onOpenThread={() => undefined}
                          onToggleSaved={() => undefined}
                        />
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="mt-4 rounded-2xl border border-dashed border-border/70 bg-muted/10 px-4 py-5">
                  <p className="text-sm text-foreground">
                    {t("channelTasks.detail.executionPlaceholder")}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Badge variant="secondary">
                      {t("channelTasks.detail.currentStatus", {
                        status: t(`channelTasks.statuses.${task.status}`),
                      })}
                    </Badge>
                    <Badge variant="outline">
                      {task.assigneeUserId ||
                      task.assigneePresetId ||
                      task.assigneeAgentIdentityId
                        ? t("channelTasks.detail.assigneeAttached")
                        : t("channelTasks.detail.assigneePending")}
                    </Badge>
                  </div>
                  </div>
                )}
              </div>
            </section>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
