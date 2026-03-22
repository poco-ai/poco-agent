"use client";

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import { MoreHorizontal, GripVertical, Pin } from "lucide-react";
import { useDraggable } from "@dnd-kit/core";

import { useT } from "@/lib/i18n/client";
import { useLanguage } from "@/hooks/use-language";
import { cn } from "@/lib/utils";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import {
  RenameTaskDialog,
  TaskActionsDropdown,
  TASK_STATUS_META,
  type TaskHistoryItem,
} from "@/features/projects";
import {
  SIDEBAR_CARD_NESTED_INSET_CLASS,
  SIDEBAR_CARD_TEXT_CLASS,
  SIDEBAR_CARD_WITH_ACTION_CLASS,
  SIDEBAR_CARD_BASE_CLASS,
} from "./sidebar-card-styles";

interface Project {
  id: string;
  name: string;
}

interface DraggableTaskProps {
  task: TaskHistoryItem;
  isActive?: boolean;
  isPinned: boolean;
  lng?: string;
  onDeleteTask: (taskId: string) => Promise<void> | void;
  onRenameClick?: (task: TaskHistoryItem) => void;
  onMoveTaskToProject?: (taskId: string, projectId: string | null) => void;
  onTogglePin?: (taskId: string) => void;
  projects: Project[];
  isSelectionMode?: boolean;
  isSelected?: boolean;
  onToggleSelection?: (taskId: string) => void;
  isNested?: boolean;
  onNavigate?: () => void;
}

/**
 * Individual draggable task item
 */

// Task status dot colors:
// - pending   → bg-muted-foreground/40
// - running   → bg-primary (with blink animation)
// - completed → bg-primary
// - failed    → bg-destructive
// - canceled  → bg-chart-4/60

function DraggableTask({
  task,
  isActive,
  isPinned,
  lng,
  onDeleteTask,
  onRenameClick,
  onMoveTaskToProject,
  onTogglePin,
  projects,
  isSelectionMode,
  isSelected,
  onToggleSelection,
  isNested,
  onNavigate,
}: DraggableTaskProps) {
  const { t } = useT("translation");
  const router = useRouter();
  const [isDropdownOpen, setIsDropdownOpen] = React.useState(false);
  const { listeners, setNodeRef, isDragging } = useDraggable({
    id: task.id,
    data: {
      type: "task",
      taskId: task.id,
    },
    disabled: isSelectionMode,
  });

  const statusMeta = TASK_STATUS_META[task.status];
  const isRunningTask = task.status === "running";
  const shouldShowDragHandle = !isRunningTask;

  const handleClick = (e: React.MouseEvent) => {
    if (isSelectionMode) {
      e.preventDefault();
      onToggleSelection?.(task.id);
    } else {
      router.push(lng ? `/${lng}/chat/${task.id}` : `/chat/${task.id}`);
      onNavigate?.();
    }
  };

  return (
    <SidebarMenuItem
      ref={setNodeRef}
      className={cn("relative transition-opacity", isDragging && "opacity-50")}
      data-task-id={task.id}
    >
      {isSelectionMode ? (
        <div
          role="button"
          tabIndex={0}
          data-slot="sidebar-menu-button"
          data-sidebar="menu-button"
          className={cn(
            "flex w-full min-w-0 items-center cursor-pointer outline-hidden rounded-md",
            SIDEBAR_CARD_BASE_CLASS,
            isNested && SIDEBAR_CARD_NESTED_INSET_CLASS,
          )}
          onClick={handleClick}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              (e.currentTarget as HTMLElement).click();
            }
          }}
        >
          <div className="flex items-center gap-3 min-w-0 w-full">
            <div className="shrink-0 flex items-center justify-center">
              <Checkbox
                checked={isSelected}
                onCheckedChange={() => onToggleSelection?.(task.id)}
                className="size-4"
                onClick={(e) => e.stopPropagation()}
              />
            </div>
            <span
              className={cn(SIDEBAR_CARD_TEXT_CLASS, isSelectionMode && "ml-1")}
            >
              {task.title || t("chat.newChat")}
            </span>
          </div>
        </div>
      ) : (
        <div
          className="relative group/task-card"
          data-active={isActive ? "true" : undefined}
        >
          <SidebarMenuButton
            isActive={isActive}
            className={cn(
              SIDEBAR_CARD_WITH_ACTION_CLASS,
              isNested && SIDEBAR_CARD_NESTED_INSET_CLASS,
            )}
            tooltip={task.title}
            onClick={handleClick}
          >
            {/* Status indicator and drag handle - same slot, toggled on hover */}
            <div className="size-4 shrink-0 flex items-center justify-center relative">
              {/* Default: status dot (hidden on hover) */}
              <span
                className={cn(
                  "size-2 shrink-0 rounded-full transition-opacity",
                  statusMeta.dotClassName,
                  isRunningTask &&
                    "motion-safe:animate-[running-status-dot-blink_1.05s_ease-in-out_infinite] motion-reduce:animate-none",
                  shouldShowDragHandle && "group-hover/task-card:opacity-0",
                  shouldShowDragHandle &&
                    "group-data-[active=true]/task-card:opacity-0",
                )}
                aria-hidden="true"
              />
              <span className="sr-only">{t(statusMeta.labelKey)}</span>

              {/* Hover: drag handle (overlays the dot) */}
              <div
                className={cn(
                  "absolute inset-0 flex items-center justify-center text-muted-foreground opacity-0 transition-opacity cursor-grab active:cursor-grabbing group-data-[collapsible=icon]:hidden",
                  shouldShowDragHandle &&
                    "group-hover/task-card:opacity-100 group-data-[active=true]/task-card:opacity-100",
                )}
                {...(shouldShowDragHandle ? listeners : {})}
                onClick={(e) => e.stopPropagation()}
              >
                {shouldShowDragHandle ? (
                  <GripVertical className="size-3" />
                ) : null}
              </div>
            </div>

            {/* Text */}
            <div className="flex min-w-0 flex-1 items-center gap-2">
              <span className={SIDEBAR_CARD_TEXT_CLASS}>
                {task.title || t("chat.newChat")}
              </span>
              {task.hasPendingUserInput && (
                <Badge className="shrink-0 bg-primary text-primary-foreground px-2 py-0 text-[10px] font-semibold animate-[ask-blink_1.2s_ease-in-out_infinite] group-data-[collapsible=icon]:hidden">
                  {t("sidebar.askTag")}
                </Badge>
              )}
            </div>
          </SidebarMenuButton>

          {isPinned && (
            <div
              className={cn(
                "pointer-events-none absolute top-1/2 right-2 -translate-y-1/2 shrink-0 size-5 flex items-center justify-center rounded-lg text-muted-foreground transition-opacity group-data-[collapsible=icon]:hidden",
                isDropdownOpen
                  ? "opacity-0"
                  : "opacity-100 group-hover/task-card:opacity-0 group-data-[active=true]/task-card:opacity-0",
              )}
              aria-hidden="true"
            >
              <Pin className="size-3.5" />
            </div>
          )}

          {/* More actions - only in non-selection mode */}
          <TaskActionsDropdown
            taskId={task.id}
            isPinned={isPinned}
            projects={projects}
            onTogglePin={onTogglePin}
            onRename={onRenameClick ? () => onRenameClick(task) : undefined}
            onMoveToProject={onMoveTaskToProject}
            onDelete={onDeleteTask}
            open={isDropdownOpen}
            onOpenChange={setIsDropdownOpen}
            side="right"
          >
            <div
              role="button"
              tabIndex={0}
              onClick={(e) => {
                e.stopPropagation();
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  e.stopPropagation();
                  (e.currentTarget as HTMLElement).click();
                }
              }}
              className="absolute top-1/2 right-2 -translate-y-1/2 shrink-0 size-5 flex items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground opacity-0 transition-opacity group-hover/task-card:opacity-100 group-data-[active=true]/task-card:opacity-100 data-[state=open]:opacity-100 group-data-[collapsible=icon]:hidden cursor-pointer focus-visible:outline-none z-10"
            >
              <MoreHorizontal className="size-3.5" />
            </div>
          </TaskActionsDropdown>
        </div>
      )}
    </SidebarMenuItem>
  );
}

export function TaskHistoryList({
  tasks,
  pinnedTaskIds = [],
  onDeleteTask,
  onRenameTask,
  onMoveTaskToProject,
  onToggleTaskPin,
  projects,
  showDropIndicator = false,
  dropIndicatorLabel,
  isSelectionMode = false,
  selectedTaskIds = new Set(),
  onToggleTaskSelection,
  isNested = false,
  onNavigate,
}: {
  tasks: TaskHistoryItem[];
  pinnedTaskIds?: string[];
  onDeleteTask: (taskId: string) => Promise<void> | void;
  onRenameTask?: (taskId: string, newName: string) => Promise<void> | void;
  onMoveTaskToProject?: (taskId: string, projectId: string | null) => void;
  onToggleTaskPin?: (taskId: string) => void;
  projects?: Project[];
  showDropIndicator?: boolean;
  dropIndicatorLabel?: string;
  isSelectionMode?: boolean;
  selectedTaskIds?: Set<string>;
  onToggleTaskSelection?: (taskId: string) => void;
  isNested?: boolean;
  onNavigate?: () => void;
}) {
  const params = useParams();
  const activeTaskId =
    typeof params?.id === "string" ? (params.id as string) : undefined;
  const lng = useLanguage();
  const pinnedOrder = React.useMemo(() => {
    const orderMap = new Map<string, number>();
    pinnedTaskIds.forEach((id, index) => {
      orderMap.set(id, index);
    });
    return orderMap;
  }, [pinnedTaskIds]);
  const orderedTasks = React.useMemo(() => {
    if (!tasks.length || pinnedOrder.size === 0) return tasks;

    const pinned: TaskHistoryItem[] = [];
    const unpinned: TaskHistoryItem[] = [];

    for (const task of tasks) {
      if (pinnedOrder.has(task.id)) {
        pinned.push(task);
      } else {
        unpinned.push(task);
      }
    }

    pinned.sort(
      (a, b) => (pinnedOrder.get(a.id) ?? 0) - (pinnedOrder.get(b.id) ?? 0),
    );
    return [...pinned, ...unpinned];
  }, [pinnedOrder, tasks]);

  // Dialog states
  const [renameDialogOpen, setRenameDialogOpen] = React.useState(false);
  const [selectedTask, setSelectedTask] =
    React.useState<TaskHistoryItem | null>(null);

  const handleRenameClick = (task: TaskHistoryItem) => {
    setSelectedTask(task);
    setRenameDialogOpen(true);
  };

  const handleRename = (newName: string) => {
    if (selectedTask) {
      onRenameTask?.(selectedTask.id, newName);
    }
  };

  return (
    <>
      <SidebarMenu className="gap-0.5 overflow-hidden">
        {showDropIndicator && (
          <SidebarMenuItem aria-hidden="true">
            <div
              className={cn(
                "flex min-w-0 w-full items-center justify-center border border-dashed border-primary/40 bg-primary/10 text-primary",
                SIDEBAR_CARD_BASE_CLASS,
                isNested && SIDEBAR_CARD_NESTED_INSET_CLASS,
              )}
            >
              <span
                className={cn(
                  SIDEBAR_CARD_TEXT_CLASS,
                  "flex-none text-xs font-medium",
                )}
              >
                {dropIndicatorLabel}
              </span>
            </div>
          </SidebarMenuItem>
        )}
        {orderedTasks.map((task) => (
          <DraggableTask
            key={task.id}
            task={task}
            isActive={task.id === activeTaskId}
            isPinned={pinnedOrder.has(task.id)}
            lng={lng}
            onDeleteTask={onDeleteTask}
            onRenameClick={onRenameTask ? handleRenameClick : undefined}
            onMoveTaskToProject={onMoveTaskToProject}
            onTogglePin={onToggleTaskPin}
            projects={projects || []}
            isSelectionMode={isSelectionMode}
            isSelected={selectedTaskIds.has(task.id)}
            onToggleSelection={onToggleTaskSelection}
            isNested={isNested}
            onNavigate={onNavigate}
          />
        ))}
      </SidebarMenu>

      {/* Rename Dialog */}
      <RenameTaskDialog
        open={renameDialogOpen}
        onOpenChange={setRenameDialogOpen}
        taskName={selectedTask?.title || ""}
        onRename={handleRename}
      />
    </>
  );
}
