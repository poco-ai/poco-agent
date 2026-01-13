"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  MoreHorizontal,
  Pencil,
  FolderPlus,
  Trash2,
  GripVertical,
} from "lucide-react";
import { useDraggable } from "@dnd-kit/core";

import { useT } from "@/app/i18n/client";
import { cn } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { RenameTaskDialog } from "@/components/task/rename-task-dialog";
import { MoveTaskToProjectDialog } from "@/components/task/move-task-to-project-dialog";

import { TASK_STATUS_META } from "@/app/[lng]/home/model/constants";
import type { TaskHistoryItem } from "@/app/[lng]/home/model/types";

interface Project {
  id: string;
  name: string;
}

interface DraggableTaskProps {
  task: TaskHistoryItem;
  onDeleteTask: (taskId: string) => void;
  onRenameClick: (task: TaskHistoryItem) => void;
  onMoveClick: (task: TaskHistoryItem) => void;
}

/**
 * Individual draggable task item
 */
function DraggableTask({
  task,
  onDeleteTask,
  onRenameClick,
  onMoveClick,
}: DraggableTaskProps) {
  const { t } = useT("translation");
  const router = useRouter();

  const { listeners, setNodeRef, isDragging } = useDraggable({
    id: task.id,
    data: {
      type: "task",
      taskId: task.id,
    },
  });

  const statusMeta = TASK_STATUS_META[task.status];

  return (
    <SidebarMenuItem
      ref={setNodeRef}
      key={task.id}
      className={cn(
        "relative group/menu-item transition-opacity",
        isDragging && "opacity-50",
      )}
      data-task-id={task.id}
    >
      <SidebarMenuButton
        className="h-[36px] min-w-0 max-w-[calc(var(--sidebar-width)-16px)] w-full justify-start gap-3 rounded-[10px] px-3 py-[7.5px] text-left transition-colors hover:bg-sidebar-accent group-data-[collapsible=icon]:w-[var(--sidebar-width-icon)] group-data-[collapsible=icon]:max-w-[var(--sidebar-width-icon)] group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:pr-0 pr-8"
        tooltip={task.title}
        onClick={() => router.push(`/chat/${task.id}`)}
      >
        {/* 拖拽手柄 */}
        <div
          className="size-4 shrink-0 flex items-center justify-center cursor-grab active:cursor-grabbing text-muted-foreground opacity-0 group-hover/menu-item:opacity-50 transition-opacity group-data-[collapsible=icon]:hidden"
          {...listeners}
        >
          <GripVertical className="size-3" />
        </div>

        {/* 第一栏：色点 */}
        <span
          className={cn(
            "size-2 shrink-0 rounded-full",
            statusMeta.dotClassName,
          )}
          aria-hidden="true"
        />
        <span className="sr-only">{t(statusMeta.labelKey)}</span>
        {/* 第二栏：文字（可截断） */}
        <span className="flex-1 min-w-0 truncate text-sm group-data-[collapsible=icon]:hidden">
          {task.title}
        </span>
      </SidebarMenuButton>
      {/* 第三栏：更多按钮 - 绝对定位在按钮外部 */}
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
            className="absolute top-1/2 right-2 -translate-y-1/2 shrink-0 size-5 flex items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground opacity-0 transition-opacity group-hover/menu-item:opacity-100 data-[state=open]:opacity-100 group-data-[collapsible=icon]:hidden cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring z-10"
          >
            <MoreHorizontal className="size-3.5" />
          </div>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" side="right">
          <DropdownMenuItem
            onClick={(e) => {
              e.stopPropagation();
              onRenameClick(task);
            }}
          >
            <Pencil className="size-4" />
            <span>{t("sidebar.rename")}</span>
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={(e) => {
              e.stopPropagation();
              onMoveClick(task);
            }}
          >
            <FolderPlus className="size-4" />
            <span>{t("sidebar.moveToProject")}</span>
          </DropdownMenuItem>
          <DropdownMenuItem
            variant="destructive"
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
    </SidebarMenuItem>
  );
}

export function TaskHistoryList({
  tasks,
  onDeleteTask,
  onRenameTask,
  onMoveTaskToProject,
  projects,
}: {
  tasks: TaskHistoryItem[];
  onDeleteTask: (taskId: string) => void;
  onRenameTask?: (taskId: string, newName: string) => void;
  onMoveTaskToProject?: (taskId: string, projectId: string | null) => void;
  projects?: Project[];
}) {
  // Dialog states
  const [renameDialogOpen, setRenameDialogOpen] = React.useState(false);
  const [moveDialogOpen, setMoveDialogOpen] = React.useState(false);
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

  const handleMoveClick = (task: TaskHistoryItem) => {
    setSelectedTask(task);
    setMoveDialogOpen(true);
  };

  const handleMove = (projectId: string | null) => {
    if (selectedTask) {
      onMoveTaskToProject?.(selectedTask.id, projectId);
    }
  };

  return (
    <>
      <SidebarMenu className="gap-0.5 overflow-hidden">
        {tasks.map((task) => (
          <DraggableTask
            key={task.id}
            task={task}
            onDeleteTask={onDeleteTask}
            onRenameClick={handleRenameClick}
            onMoveClick={handleMoveClick}
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

      {/* Move to Project Dialog */}
      <MoveTaskToProjectDialog
        open={moveDialogOpen}
        onOpenChange={setMoveDialogOpen}
        projects={projects || []}
        onMove={handleMove}
      />
    </>
  );
}
