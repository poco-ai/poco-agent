"use client";

import * as React from "react";
import {
  CornerDownRight,
  LayoutGrid,
  LayoutList,
  UserRound,
} from "lucide-react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import {
  buildChannelTaskColumns,
  buildChannelTaskListGroups,
} from "@/features/channel-tasks/lib/channel-task-board";
import type {
  ChannelTaskActorSummary,
  ChannelTask,
  ChannelTaskView,
} from "@/features/channel-tasks/model/types";
import type {
  ServerAgentItem,
  ServerChannelItem,
  ServerChannelMemberItem,
} from "@/features/servers/model/types";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

import { ServerAgentAvatar } from "./server-agent-avatar";

function normalizeTaskText(value?: string | null): string {
  return (value ?? "").replace(/\s+/g, " ").trim();
}

function getInitials(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) {
    return "?";
  }
  return trimmed
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");
}

function ActorAvatar({
  actor,
  agents,
  presets,
  className,
}: {
  actor?: ChannelTaskActorSummary | null;
  agents: ServerAgentItem[];
  presets: Preset[];
  className?: string;
}) {
  const label = actor?.label?.trim() || "Unassigned";
  if (actor?.actorType === "agent" && actor.agentIdentityId) {
    const agent = agents.find((item) => item.id === actor.agentIdentityId);
    if (agent) {
      return (
        <ServerAgentAvatar
          agent={agent}
          presets={presets}
          className={cn("size-7 rounded-md", className)}
          fallbackClassName="text-[0.65rem]"
        />
      );
    }
  }
  return (
    <Avatar className={cn("size-7 rounded-md border border-border", className)}>
      {actor?.avatarUrl ? (
        <AvatarImage src={actor.avatarUrl} alt={label} />
      ) : null}
      <AvatarFallback className="rounded-md bg-muted text-[0.65rem] font-semibold text-foreground">
        {actor ? getInitials(label) : <UserRound className="size-3.5" />}
      </AvatarFallback>
    </Avatar>
  );
}

function taskAssigneeValue(task: ChannelTask): string {
  if (task.assigneeAgentIdentityId) {
    return `agent:${task.assigneeAgentIdentityId}`;
  }
  if (task.assigneeUserId) {
    return `user:${task.assigneeUserId}`;
  }
  return "none:";
}

type AssigneeOption = {
  value: string;
  label: string;
  description: string;
  actor: ChannelTaskActorSummary | null;
  payload: {
    assigneeUserId: string | null;
    assigneeAgentIdentityId: string | null;
  };
};

function TaskAssignmentControl({
  task,
  members,
  agents,
  presets,
  disabled,
  canUpdateAssignee,
  onUpdateAssignee,
}: {
  task: ChannelTask;
  members: ServerChannelMemberItem[];
  agents: ServerAgentItem[];
  presets: Preset[];
  disabled: boolean;
  canUpdateAssignee: boolean;
  onUpdateAssignee: (
    task: ChannelTask,
    value: {
      assigneeUserId: string | null;
      assigneeAgentIdentityId: string | null;
    },
  ) => Promise<void>;
}) {
  const { t } = useT("translation");
  const [open, setOpen] = React.useState(false);
  const [search, setSearch] = React.useState("");
  const [selectedValue, setSelectedValue] = React.useState(() =>
    taskAssigneeValue(task),
  );
  const currentValue = taskAssigneeValue(task);

  React.useEffect(() => {
    if (open) {
      setSelectedValue(currentValue);
      setSearch("");
    }
  }, [currentValue, open]);

  const options = React.useMemo<AssigneeOption[]>(() => {
    const userOptions = members.map<AssigneeOption>((member) => {
      const label = member.user?.displayName || member.userId;
      return {
        value: `user:${member.userId}`,
        label,
        description: member.userId,
        actor: {
          actorType: "user",
          userId: member.userId,
          label,
          avatarUrl: member.user?.avatarUrl,
        },
        payload: {
          assigneeUserId: member.userId,
          assigneeAgentIdentityId: null,
        },
      };
    });
    const agentOptions = agents.map<AssigneeOption>((agent) => ({
      value: `agent:${agent.id}`,
      label: agent.displayName,
      description: `@${agent.handle}`,
      actor: {
        actorType: "agent",
        agentIdentityId: agent.id,
        agentHandle: agent.handle,
        label: agent.displayName,
        visualKey: agent.visualKey,
      },
      payload: {
        assigneeUserId: null,
        assigneeAgentIdentityId: agent.id,
      },
    }));
    return [
      {
        value: "none:",
        label: t("channelTasks.detail.unassigned"),
        description: "",
        actor: null,
        payload: {
          assigneeUserId: null,
          assigneeAgentIdentityId: null,
        },
      },
      ...userOptions,
      ...agentOptions,
    ];
  }, [agents, members, t]);

  const filteredOptions = React.useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) {
      return options;
    }
    return options.filter((option) =>
      `${option.label} ${option.description}`.toLowerCase().includes(query),
    );
  }, [options, search]);

  const selectedOption =
    options.find((option) => option.value === selectedValue) ?? options[0];

  const handleConfirm = async () => {
    if (!selectedOption) {
      return;
    }
    await onUpdateAssignee(task, selectedOption.payload);
    setOpen(false);
  };

  return (
    <div className="flex min-w-0 items-center gap-1.5">
      <ActorAvatar
        actor={task.creator}
        agents={agents}
        presets={presets}
        className="size-6"
      />
      <CornerDownRight
        className="size-3.5 shrink-0 text-muted-foreground"
        strokeWidth={1.7}
      />
      <Dialog open={open} onOpenChange={setOpen}>
        <button
          type="button"
          disabled={disabled || !canUpdateAssignee}
          onClick={(event) => {
            event.stopPropagation();
            setOpen(true);
          }}
          className="flex size-7 items-center justify-center rounded-md border border-border bg-background transition-colors hover:bg-muted/30 disabled:cursor-not-allowed disabled:opacity-60"
          aria-label={t("channelTasks.detail.assignee")}
          title={task.assignee?.label || t("channelTasks.detail.unassigned")}
        >
          <ActorAvatar
            actor={task.assignee}
            agents={agents}
            presets={presets}
            className="size-5"
          />
        </button>
        <DialogContent
          onClick={(event) => event.stopPropagation()}
          className="sm:max-w-md"
        >
          <DialogHeader>
            <DialogTitle>{t("channelTasks.detail.assignee")}</DialogTitle>
            <DialogDescription>{task.title}</DialogDescription>
          </DialogHeader>
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t("conversationView.searchInServer")}
          />
          <div className="max-h-80 space-y-1 overflow-y-auto rounded-md border border-border p-1">
            {filteredOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => setSelectedValue(option.value)}
                className={cn(
                  "flex w-full items-center gap-3 rounded-md px-3 py-2 text-left transition-colors",
                  option.value === selectedValue
                    ? "bg-primary/15"
                    : "hover:bg-muted/30",
                )}
              >
                <ActorAvatar
                  actor={option.actor}
                  agents={agents}
                  presets={presets}
                  className="size-8"
                />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-foreground">
                    {option.label}
                  </span>
                  {option.description ? (
                    <span className="block truncate text-xs text-muted-foreground">
                      {option.description}
                    </span>
                  ) : null}
                </span>
              </button>
            ))}
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
            >
              {t("conversationView.close")}
            </Button>
            <Button
              type="button"
              onClick={() => void handleConfirm()}
              disabled={disabled || selectedValue === currentValue}
            >
              {t("common.confirm")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function TaskCard({
  task,
  members,
  agents,
  presets,
  isSaving,
  canUpdateAssignee,
  onOpenTask,
  onUpdateAssignee,
}: {
  task: ChannelTask;
  members: ServerChannelMemberItem[];
  agents: ServerAgentItem[];
  presets: Preset[];
  isSaving: boolean;
  canUpdateAssignee: boolean;
  onOpenTask: (taskId: string) => void;
  onUpdateAssignee: (
    task: ChannelTask,
    value: {
      assigneeUserId: string | null;
      assigneeAgentIdentityId: string | null;
    },
  ) => Promise<void>;
}) {
  const title = normalizeTaskText(task.title);
  const description = normalizeTaskText(task.description);
  const showDescription = Boolean(description) && description !== title;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onOpenTask(task.taskId)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onOpenTask(task.taskId);
        }
      }}
      className="w-full rounded-md border border-border bg-card px-4 py-4 text-left transition-colors hover:bg-muted/20"
    >
      <div className="flex min-w-0 items-start justify-between gap-3">
        <p className="min-w-0 truncate text-xs font-medium text-muted-foreground">
          #{task.displayNumber}
        </p>
        <TaskAssignmentControl
          task={task}
          members={members}
          agents={agents}
          presets={presets}
          disabled={isSaving}
          canUpdateAssignee={canUpdateAssignee}
          onUpdateAssignee={onUpdateAssignee}
        />
      </div>
      <p className="mt-2 line-clamp-2 break-words text-base font-semibold leading-6 text-foreground">
        {title}
      </p>
      {showDescription ? (
        <p className="mt-2 line-clamp-2 break-words text-sm text-muted-foreground">
          {description}
        </p>
      ) : null}
    </div>
  );
}

export function ChannelTasksWorkspace({
  tasks,
  taskView,
  activeChannelId,
  topLevelChannels,
  members,
  agents,
  presets,
  canUpdateAssignee,
  onSelectChannel,
  onUpdateView,
  onOpenTask,
  onUpdateAssignee,
}: {
  tasks: ChannelTask[];
  taskView: ChannelTaskView;
  activeChannelId: string | null;
  topLevelChannels: ServerChannelItem[];
  members: ServerChannelMemberItem[];
  agents: ServerAgentItem[];
  presets: Preset[];
  canUpdateAssignee: boolean;
  onSelectChannel: (channelId: string) => void;
  onUpdateView: (view: ChannelTaskView) => void;
  onOpenTask: (taskId: string) => void;
  onUpdateAssignee: (
    task: ChannelTask,
    value: {
      assigneeUserId: string | null;
      assigneeAgentIdentityId: string | null;
    },
  ) => Promise<void>;
}) {
  const { t } = useT("translation");
  const [savingTaskId, setSavingTaskId] = React.useState<string | null>(null);

  const updateAssignee = async (
    task: ChannelTask,
    value: {
      assigneeUserId: string | null;
      assigneeAgentIdentityId: string | null;
    },
  ) => {
    setSavingTaskId(task.taskId);
    try {
      await onUpdateAssignee(task, value);
    } finally {
      setSavingTaskId(null);
    }
  };

  return (
    <section className="flex min-w-0 flex-1 flex-col overflow-hidden">
      <div className="grid min-w-0 grid-cols-1 items-center gap-3 border-b border-border px-6 py-4 sm:grid-cols-[minmax(0,15rem)_minmax(0,1fr)]">
        <Select value={activeChannelId ?? ""} onValueChange={onSelectChannel}>
          <SelectTrigger className="min-w-0 max-w-full border-border bg-background text-sm">
            <SelectValue placeholder={t("conversationView.channels")} />
          </SelectTrigger>
          <SelectContent>
            {topLevelChannels.map((channel) => (
              <SelectItem key={channel.id} value={channel.id}>
                {channel.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="min-w-0 justify-self-start sm:justify-self-end">
          <div className="flex max-w-full items-center gap-1 overflow-x-auto rounded-md border border-border bg-card p-1">
            <Button
              type="button"
              variant={taskView === "board" ? "default" : "ghost"}
              size="sm"
              onClick={() => onUpdateView("board")}
              className="shrink-0 whitespace-nowrap"
            >
              <LayoutGrid className="size-4" />
              {t("conversationView.boardView")}
            </Button>
            <Button
              type="button"
              variant={taskView === "list" ? "default" : "ghost"}
              size="sm"
              onClick={() => onUpdateView("list")}
              className="shrink-0 whitespace-nowrap"
            >
              <LayoutList className="size-4" />
              {t("conversationView.listView")}
            </Button>
          </div>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-6 py-6">
        {taskView === "board" ? (
          <div className="overflow-x-auto">
            <div className="grid min-w-[980px] grid-cols-4 gap-4">
              {buildChannelTaskColumns(tasks).map((column) => (
                <section
                  key={column.status}
                  className="flex min-h-[32rem] flex-col rounded-md border border-border bg-muted/10 p-3"
                >
                  <div className="mb-3 flex items-center justify-between gap-3 px-1">
                    <span className="text-sm font-semibold text-foreground">
                      {t(`channelTasks.statuses.${column.status}`)}
                    </span>
                    <span className="rounded-md border border-border bg-background px-2 py-0.5 text-xs tabular-nums text-muted-foreground">
                      {column.tasks.length}
                    </span>
                  </div>
                  <div className="min-h-0 flex-1 space-y-3">
                    {column.tasks.length > 0 ? (
                      column.tasks.map((task) => (
                        <TaskCard
                          key={task.taskId}
                          task={task}
                          members={members}
                          agents={agents}
                          presets={presets}
                          isSaving={savingTaskId === task.taskId}
                          canUpdateAssignee={canUpdateAssignee}
                          onOpenTask={onOpenTask}
                          onUpdateAssignee={updateAssignee}
                        />
                      ))
                    ) : (
                      <div className="flex min-h-32 items-center rounded-md border border-dashed border-border bg-background/70 px-4 py-10 text-sm text-muted-foreground">
                        {t("conversationView.emptyTaskColumn", {
                          status: t(`channelTasks.statuses.${column.status}`),
                        })}
                      </div>
                    )}
                  </div>
                </section>
              ))}
            </div>
          </div>
        ) : buildChannelTaskListGroups(tasks).length > 0 ? (
          <div className="space-y-6">
            {buildChannelTaskListGroups(tasks).map((group) => (
              <section key={group.status} className="space-y-3">
                <div className="flex items-center gap-3">
                  <span className="rounded-sm bg-primary/15 px-2 py-1 text-xs font-semibold uppercase text-foreground">
                    {t(`channelTasks.statuses.${group.status}`)}
                  </span>
                  <span className="text-sm text-muted-foreground">
                    {group.tasks.length}
                  </span>
                </div>
                <div className="space-y-3">
                  {group.tasks.map((task) => (
                    <TaskCard
                      key={task.taskId}
                      task={task}
                      members={members}
                      agents={agents}
                      presets={presets}
                      isSaving={savingTaskId === task.taskId}
                      canUpdateAssignee={canUpdateAssignee}
                      onOpenTask={onOpenTask}
                      onUpdateAssignee={updateAssignee}
                    />
                  ))}
                </div>
              </section>
            ))}
          </div>
        ) : (
          <div className="flex min-h-[28rem] items-center justify-center rounded-md border border-dashed border-border bg-muted/10 px-6 py-12 text-center">
            <div className="max-w-sm space-y-2">
              <LayoutList className="mx-auto size-8 text-muted-foreground" />
              <p className="text-sm font-semibold text-foreground">
                {t("conversationView.emptyTaskListTitle")}
              </p>
              <p className="text-sm text-muted-foreground">
                {t("conversationView.emptyTaskListDescription")}
              </p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
