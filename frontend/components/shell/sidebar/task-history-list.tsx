"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  MoreHorizontal,
  FolderPlus,
  Pencil,
  Trash2,
  GripVertical,
} from "lucide-react";
import { useDraggable } from "@dnd-kit/core";

import { useT } from "@/lib/i18n/client";
import { useLanguage } from "@/hooks/use-language";
import { cn } from "@/lib/utils";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import {
  RenameTaskDialog,
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
  lng?: string;
  onDeleteTask: (taskId: string) => Promise<void> | void;
  onRenameClick?: (task: TaskHistoryItem) => void;
  onMoveTaskToProject?: (taskId: string, projectId: string | null) => void;
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
  lng,
  onDeleteTask,
  onRenameClick,
  onMoveTaskToProject,
  projects,
  isSelectionMode,
  isSelected,
  onToggleSelection,
  isNested,
  onNavigate,
}: DraggableTaskProps) {
  const { t } = useT("translation");
  const router = useRouter();
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
        <div className="relative group/task-card">
          <SidebarMenuButton
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
                  "group-hover/task-card:opacity-0",
                )}
                aria-hidden="true"
              />
              <span className="sr-only">{t(statusMeta.labelKey)}</span>

              {/* Hover: drag handle (overlays the dot) */}
              <div
                className="absolute inset-0 flex items-center justify-center text-muted-foreground opacity-0 group-hover/task-card:opacity-100 transition-opacity cursor-grab active:cursor-grabbing group-data-[collapsible=icon]:hidden"
                {...listeners}
                onClick={(e) => e.stopPropagation()}
              >
                <GripVertical className="size-3" />
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

          {/* More actions - only in non-selection mode */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
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
                className="absolute top-1/2 right-2 -translate-y-1/2 shrink-0 size-5 flex items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground opacity-0 transition-opacity group-hover/task-card:opacity-100 data-[state=open]:opacity-100 group-data-[collapsible=icon]:hidden cursor-pointer focus-visible:outline-none z-10"
              >
                <MoreHorizontal className="size-3.5" />
              </div>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" side="right">
              {onRenameClick && (
                <DropdownMenuItem
                  onClick={(e) => {
                    e.stopPropagation();
                    onRenameClick(task);
                  }}
                >
                  <Pencil className="size-4" />
                  <span>{t("sidebar.rename")}</span>
                </DropdownMenuItem>
              )}
              {onMoveTaskToProject ? (
                <DropdownMenuSub>
                  <DropdownMenuSubTrigger className="focus:bg-muted focus:text-foreground data-[state=open]:bg-muted data-[state=open]:text-foreground">
                    <FolderPlus className="size-4" />
                    <span>{t("sidebar.moveToProject")}</span>
                  </DropdownMenuSubTrigger>
                  <DropdownMenuSubContent className="bg-popover">
                    {projects.map((project) => (
                      <DropdownMenuItem
                        key={project.id}
                        className="focus:bg-muted focus:text-foreground"
                        onClick={(e) => {
                          e.stopPropagation();
                          onMoveTaskToProject(task.id, project.id);
                        }}
                      >
                        <span className="truncate">{project.name}</span>
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuSubContent>
                </DropdownMenuSub>
              ) : (
                <DropdownMenuItem disabled>
                  <FolderPlus className="size-4" />
                  <span>{t("sidebar.moveToProject")}</span>
                </DropdownMenuItem>
              )}
              <DropdownMenuItem
                variant="destructive"
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteTask(task.id);
                }}
              >
                <Trash2 className="size-4 text-destructive" />
                <span>{t("sidebar.delete")}</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      )}
    </SidebarMenuItem>
  );
}

export function TaskHistoryList({
  tasks,
  onDeleteTask,
  onRenameTask,
  onMoveTaskToProject,
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
  onDeleteTask: (taskId: string) => Promise<void> | void;
  onRenameTask?: (taskId: string, newName: string) => Promise<void> | void;
  onMoveTaskToProject?: (taskId: string, projectId: string | null) => void;
  projects?: Project[];
  showDropIndicator?: boolean;
  dropIndicatorLabel?: string;
  isSelectionMode?: boolean;
  selectedTaskIds?: Set<string>;
  onToggleTaskSelection?: (taskId: string) => void;
  isNested?: boolean;
  onNavigate?: () => void;
}) {
  const lng = useLanguage();

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
        {tasks.map((task) => (
          <DraggableTask
            key={task.id}
            task={task}
            lng={lng}
            onDeleteTask={onDeleteTask}
            onRenameClick={onRenameTask ? handleRenameClick : undefined}
            onMoveTaskToProject={onMoveTaskToProject}
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
