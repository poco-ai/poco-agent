"use client";

import * as React from "react";
import {
  ChevronRight,
  Folder,
  MoreHorizontal,
  PenSquare,
  Trash2,
} from "lucide-react";
import { useDroppable } from "@dnd-kit/core";
import { cn } from "@/lib/utils";
import {
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuAction,
  SidebarMenuBadge,
} from "@/components/ui/sidebar";
import type { ProjectItem, TaskHistoryItem } from "@/features/projects/types";
import { TaskHistoryList } from "./task-history-list";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useT } from "@/lib/i18n/client";
import { RenameProjectDialog } from "@/features/projects/components/rename-project-dialog";
import { Checkbox } from "@/components/ui/checkbox";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

interface CollapsibleProjectItemProps {
  project: ProjectItem;
  tasks: TaskHistoryItem[];
  isExpanded: boolean;
  onToggle: () => void;
  onProjectClick: () => void;
  onDeleteTask: (taskId: string) => Promise<void> | void;
  onRenameTask?: (taskId: string, newName: string) => void;
  onMoveTaskToProject?: (taskId: string, projectId: string | null) => void;
  allProjects: ProjectItem[];
  onRenameProject?: (projectId: string, newName: string) => void;
  onDeleteProject?: (projectId: string) => Promise<void> | void;
  isSelectionMode?: boolean;
  selectedTaskIds?: Set<string>;
  selectedProjectIds?: Set<string>;
  onToggleTaskSelection?: (taskId: string) => void;
  onEnableSelectionMode?: (taskId: string) => void;
  onToggleProjectSelection?: (projectId: string) => void;
  onEnableProjectSelectionMode?: (projectId: string) => void;
}

/**
 * 可折叠的项目项，包含项目及其任务列表
 */
export function CollapsibleProjectItem({
  project,
  tasks,
  isExpanded,
  onToggle,
  onProjectClick,
  onDeleteTask,
  onRenameTask,
  onMoveTaskToProject,
  allProjects,
  onRenameProject,
  onDeleteProject,
  isSelectionMode,
  selectedTaskIds,
  selectedProjectIds,
  onToggleTaskSelection,
  onEnableSelectionMode,
  onToggleProjectSelection,
  onEnableProjectSelectionMode,
}: CollapsibleProjectItemProps) {
  const { t } = useT("translation");
  const { setNodeRef, isOver } = useDroppable({
    id: project.id,
    data: {
      type: "project",
      projectId: project.id,
    },
  });
  const [isRenameDialogOpen, setIsRenameDialogOpen] = React.useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = React.useState(false);
  const [isDeleting, setIsDeleting] = React.useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = React.useState(false);
  const longPressTimerRef = React.useRef<NodeJS.Timeout | null>(null);

  const longPressTriggeredRef = React.useRef(false);

  const isSelected = selectedProjectIds?.has(project.id);

  const handleRename = (newName: string) => {
    onRenameProject?.(project.id, newName);
  };

  const handleDelete = async () => {
    if (!onDeleteProject) return;
    try {
      setIsDeleting(true);
      await onDeleteProject(project.id);
    } finally {
      setIsDeleting(false);
      setIsDeleteDialogOpen(false);
    }
  };

  const handlePointerDown = (e: React.PointerEvent) => {
    if (isSelectionMode) return;
    if (e.button !== 0) return;

    longPressTriggeredRef.current = false;

    longPressTimerRef.current = setTimeout(() => {
      longPressTriggeredRef.current = true;
      onEnableProjectSelectionMode?.(project.id);
    }, 500);
  };

  const clearPointerTimer = () => {
    if (longPressTimerRef.current) {
      clearTimeout(longPressTimerRef.current);
      longPressTimerRef.current = null;
    }
  };

  return (
    <SidebarMenuItem>
      <div
        ref={setNodeRef}
        className={cn(
          "relative w-full group/project-item",
          isOver && "bg-primary/10",
        )}
      >
        {/* 项目标题行 */}
        <div className="relative">
          <SidebarMenuButton
            asChild
            className={cn(
              "h-8 justify-start gap-3 text-sm hover:bg-sidebar-accent pr-8",
              isOver && "bg-primary/20",
            )}
            tooltip={project.name}
            onPointerDown={handlePointerDown}
            onPointerUp={clearPointerTimer}
            onPointerLeave={clearPointerTimer}
          >
            <div className="cursor-pointer">
              {isSelectionMode && (
                <Checkbox
                  checked={isSelected}
                  onCheckedChange={() => onToggleProjectSelection?.(project.id)}
                  className="size-4"
                  onClick={(e) => e.stopPropagation()}
                />
              )}
              <div className="flex flex-1 items-center gap-1.5 min-w-0">
                <span
                  role="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggle();
                  }}
                  className="size-5 shrink-0 flex items-center justify-center text-muted-foreground/70 hover:text-foreground hover:bg-sidebar-accent rounded-sm transition-all cursor-pointer group/toggle"
                >
                  <Folder className="size-4 group-hover/project-item:hidden" />
                  <ChevronRight
                    className={cn(
                      "size-4 hidden group-hover/project-item:block transition-transform duration-200",
                      isExpanded && "rotate-90",
                    )}
                  />
                </span>

                <span
                  className={cn(
                    "flex-1 truncate cursor-pointer",
                    isOver && "text-primary",
                  )}
                  onClick={(e) => {
                    if (longPressTriggeredRef.current) {
                      e.preventDefault();
                      e.stopPropagation();
                      longPressTriggeredRef.current = false;
                      return;
                    }
                    e.stopPropagation();
                    if (isSelectionMode) {
                      onToggleProjectSelection?.(project.id);
                    } else {
                      onProjectClick();
                    }
                  }}
                >
                  {project.name}
                </span>
              </div>

              {isOver && (
                <span className="ml-auto text-xs text-primary shrink-0">
                  移动到这里
                </span>
              )}
            </div>
          </SidebarMenuButton>

          {/* 任务数量 - 默认显示，悬浮或下拉菜单打开时隐藏 */}
          {!isDropdownOpen && (
            <SidebarMenuBadge className="right-2 opacity-100 transition-opacity group-hover/project-item:opacity-0 group-data-[collapsible=icon]:hidden">
              {tasks.length}
            </SidebarMenuBadge>
          )}

          {/* 更多按钮 - 默认隐藏，悬浮时显示 */}
          {onRenameProject && !isSelectionMode && (
            <DropdownMenu
              open={isDropdownOpen}
              onOpenChange={setIsDropdownOpen}
            >
              <DropdownMenuTrigger asChild>
                <SidebarMenuAction
                  showOnHover
                  onClick={(e) => e.stopPropagation()}
                  className="right-2"
                >
                  <MoreHorizontal />
                </SidebarMenuAction>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" side="right">
                <DropdownMenuItem
                  onClick={(e) => {
                    e.stopPropagation();
                    setIsRenameDialogOpen(true);
                  }}
                >
                  <PenSquare className="size-4" />
                  <span>{t("project.rename")}</span>
                </DropdownMenuItem>
                {onDeleteProject && (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      className="text-destructive focus:text-destructive focus:bg-destructive/10"
                      onClick={(e) => {
                        e.stopPropagation();
                        setIsDeleteDialogOpen(true);
                      }}
                    >
                      <Trash2 className="size-4" />
                      <span>{t("project.delete")}</span>
                    </DropdownMenuItem>
                  </>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>

        {/* 任务列表（可折叠） */}
        {isExpanded && (
          <div className="ml-4 mt-0.5">
            <TaskHistoryList
              tasks={tasks}
              onDeleteTask={onDeleteTask}
              onRenameTask={onRenameTask}
              onMoveTaskToProject={onMoveTaskToProject}
              projects={allProjects}
              isSelectionMode={isSelectionMode}
              selectedTaskIds={selectedTaskIds}
              onToggleTaskSelection={onToggleTaskSelection}
              onEnableSelectionMode={onEnableSelectionMode}
            />
          </div>
        )}

        <RenameProjectDialog
          open={isRenameDialogOpen}
          onOpenChange={setIsRenameDialogOpen}
          projectName={project.name}
          onRename={handleRename}
        />
        <AlertDialog
          open={isDeleteDialogOpen}
          onOpenChange={setIsDeleteDialogOpen}
        >
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>{t("project.delete")}</AlertDialogTitle>
              <AlertDialogDescription>
                {t("project.deleteDescription")}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel disabled={isDeleting}>
                {t("common.cancel", "Cancel")}
              </AlertDialogCancel>
              <AlertDialogAction
                onClick={handleDelete}
                disabled={isDeleting}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                {t("project.deleteConfirm", "Delete")}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </SidebarMenuItem>
  );
}
