"use client";

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import {
  MoreHorizontal,
  FolderPlus,
  Pencil,
  Trash2,
  GripVertical,
  Loader2,
} from "lucide-react";
import { useDraggable } from "@dnd-kit/core";

import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";
import { Checkbox } from "@/components/ui/checkbox";
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
import { RenameTaskDialog } from "@/features/projects/components/rename-task-dialog";

import { TASK_STATUS_META } from "@/features/home/constants/constants";
import type { TaskHistoryItem } from "@/features/projects/types";
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
            "flex w-full min-w-0 items-center cursor-pointer outline-hidden focus-visible:ring-2 focus-visible:ring-sidebar-ring rounded-md",
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
            {/* 状态指示器和拖拽手柄 - 同一位置，hover 时切换 */}
            <div className="size-4 shrink-0 flex items-center justify-center relative">
              {/* 默认显示：颜色点 - hover 时隐藏 */}
              {task.status === "running" ? (
                <Loader2
                  className={cn(
                    "size-3 shrink-0 animate-spin text-info transition-opacity",
                    "group-hover/task-card:opacity-0",
                  )}
                />
              ) : (
                <span
                  className={cn(
                    "size-2 shrink-0 rounded-full transition-opacity",
                    statusMeta.dotClassName,
                    "group-hover/task-card:opacity-0",
                  )}
                  aria-hidden="true"
                />
              )}
              <span className="sr-only">{t(statusMeta.labelKey)}</span>

              {/* Hover 时显示：拖拽手柄 - 覆盖在颜色点上 */}
              <div
                className="absolute inset-0 flex items-center justify-center text-muted-foreground opacity-0 group-hover/task-card:opacity-100 transition-opacity cursor-grab active:cursor-grabbing group-data-[collapsible=icon]:hidden"
                {...listeners}
                onClick={(e) => e.stopPropagation()}
              >
                <GripVertical className="size-3" />
              </div>
            </div>

            {/* 文字 */}
            <span className={SIDEBAR_CARD_TEXT_CLASS}>
              {task.title || t("chat.newChat")}
            </span>
          </SidebarMenuButton>

          {/* 更多按钮 - 仅在非选择模式显示 */}
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
                className="absolute top-1/2 right-2 -translate-y-1/2 shrink-0 size-5 flex items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground opacity-0 transition-opacity group-hover/task-card:opacity-100 data-[state=open]:opacity-100 group-data-[collapsible=icon]:hidden cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring z-10"
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
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteTask(task.id);
                }}
              >
                <Trash2 className="size-4" />
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
  isSelectionMode?: boolean;
  selectedTaskIds?: Set<string>;
  onToggleTaskSelection?: (taskId: string) => void;
  isNested?: boolean;
  onNavigate?: () => void;
}) {
  const params = useParams();
  const lng = React.useMemo(() => {
    const value = params?.lng;
    if (!value) return undefined;
    return Array.isArray(value) ? value[0] : value;
  }, [params]);

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
