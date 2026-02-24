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
  SIDEBAR_CARD_TEXT_CLASS,
  SIDEBAR_CARD_WITH_ACTION_CLASS,
} from "./sidebar-card-styles";
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
  onRenameTask?: (taskId: string, newName: string) => Promise<void> | void;
  onMoveTaskToProject?: (taskId: string, projectId: string | null) => void;
  allProjects: ProjectItem[];
  onRenameProject?: (projectId: string, newName: string) => void;
  onDeleteProject?: (projectId: string) => Promise<void> | void;
  isProjectSelectionMode?: boolean;
  isTaskSelectionMode?: boolean;
  selectedTaskIds?: Set<string>;
  selectedProjectIds?: Set<string>;
  onToggleTaskSelection?: (taskId: string) => void;
  onToggleProjectSelection?: (projectId: string) => void;
  onTaskNavigate?: () => void;
}

/**
 * Collapsible project item that renders the project row and its nested task list.
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
  isProjectSelectionMode,
  isTaskSelectionMode,
  selectedTaskIds,
  selectedProjectIds,
  onToggleTaskSelection,
  onToggleProjectSelection,
  onTaskNavigate,
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

  return (
    <SidebarMenuItem>
      <div
        ref={setNodeRef}
        className={cn("relative w-full", isOver && "bg-primary/10")}
      >
        {/* Project header row */}
        <div className="relative group/project-card">
          <SidebarMenuButton
            asChild
            className={cn(
              SIDEBAR_CARD_WITH_ACTION_CLASS,
              isOver && "bg-primary/20",
            )}
            tooltip={project.name}
          >
            <div className="flex min-w-0 w-full items-center">
              <div className="flex flex-1 items-center gap-1.5 min-w-0">
                <span
                  role="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (isProjectSelectionMode) {
                      onToggleProjectSelection?.(project.id);
                      return;
                    }
                    onToggle();
                  }}
                  className={cn(
                    "size-5 shrink-0 flex items-center justify-center rounded-sm transition-all cursor-pointer group/toggle",
                    isProjectSelectionMode
                      ? "text-sidebar-foreground"
                      : "text-muted-foreground/70 hover:text-foreground hover:bg-sidebar-accent",
                  )}
                >
                  {isProjectSelectionMode ? (
                    <Checkbox
                      checked={isSelected}
                      onCheckedChange={() =>
                        onToggleProjectSelection?.(project.id)
                      }
                      className="size-4"
                      onClick={(e) => e.stopPropagation()}
                    />
                  ) : (
                    <>
                      <Folder className="size-4 hidden md:block md:group-hover/project-card:hidden" />
                      <ChevronRight
                        className={cn(
                          "size-4 block transition-transform duration-200 md:hidden md:group-hover/project-card:block",
                          isExpanded && "rotate-90",
                        )}
                      />
                    </>
                  )}
                </span>

                <span
                  className={cn(
                    SIDEBAR_CARD_TEXT_CLASS,
                    "cursor-pointer",
                    isOver && "text-primary",
                  )}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (isProjectSelectionMode) {
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
                  {t("sidebar.moveToHere")}
                </span>
              )}
            </div>
          </SidebarMenuButton>

          {/* Task count badge - shown by default; hidden on hover or when the dropdown is open */}
          {!isDropdownOpen && (
            <SidebarMenuBadge className="right-2 opacity-100 transition-opacity group-hover/project-card:opacity-0 group-focus-within/project-card:opacity-0 group-data-[collapsible=icon]:hidden">
              {tasks.length}
            </SidebarMenuBadge>
          )}

          {/* More actions - hidden by default; shown on hover */}
          {onRenameProject && !isProjectSelectionMode && (
            <DropdownMenu
              open={isDropdownOpen}
              onOpenChange={setIsDropdownOpen}
            >
              <DropdownMenuTrigger asChild>
                <SidebarMenuAction
                  onClick={(e) => e.stopPropagation()}
                  className="right-2 opacity-0 transition-opacity group-hover/project-card:opacity-100 group-focus-within/project-card:opacity-100 data-[state=open]:opacity-100"
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
                      <Trash2 className="size-4 text-destructive" />
                      <span>{t("project.delete")}</span>
                    </DropdownMenuItem>
                  </>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>

        {/* Collapsible task list */}
        {isExpanded && (
          <div className="mt-0.5 min-w-0 max-w-[calc(var(--sidebar-width)-16px)] overflow-hidden">
            <TaskHistoryList
              tasks={tasks}
              onDeleteTask={onDeleteTask}
              onRenameTask={onRenameTask}
              onMoveTaskToProject={onMoveTaskToProject}
              projects={allProjects}
              isSelectionMode={isTaskSelectionMode}
              selectedTaskIds={selectedTaskIds}
              onToggleTaskSelection={onToggleTaskSelection}
              isNested
              onNavigate={onTaskNavigate}
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
