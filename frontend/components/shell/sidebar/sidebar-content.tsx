"use client";

import * as React from "react";
import { useRouter, useParams } from "next/navigation";
import { CheckCheck, ChevronRight, Plus } from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { useDroppable } from "@dnd-kit/core";

import { useT } from "@/lib/i18n/client";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  useSidebar,
} from "@/components/ui/sidebar";
import { ScrollArea } from "@/components/ui/scroll-area";

import type { ProjectItem, TaskHistoryItem } from "@/features/projects/types";
import { TaskHistoryList } from "./task-history-list";
import { CollapsibleProjectItem } from "./collapsible-project-item";

const LONG_PRESS_DURATION_MS = 650;

interface LongPressActionButtonProps {
  icon: React.ReactNode;
  label: string;
  onComplete: () => void;
  disabled?: boolean;
  durationMs?: number;
  className?: string;
}

function LongPressActionButton({
  icon,
  label,
  onComplete,
  disabled,
  durationMs = LONG_PRESS_DURATION_MS,
  className,
}: LongPressActionButtonProps) {
  const timerRef = React.useRef<number | null>(null);
  const completedRef = React.useRef(false);

  const clearTimer = React.useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const handlePointerDown = React.useCallback(
    (e: React.PointerEvent<HTMLButtonElement>) => {
      if (disabled) return;
      if (e.button !== 0) return;

      completedRef.current = false;
      clearTimer();
      timerRef.current = window.setTimeout(() => {
        if (completedRef.current) return;
        completedRef.current = true;
        onComplete();
      }, durationMs);
    },
    [clearTimer, disabled, durationMs, onComplete],
  );

  const handlePointerEnd = React.useCallback(() => {
    clearTimer();
    completedRef.current = false;
  }, [clearTimer]);

  React.useEffect(() => () => clearTimer(), [clearTimer]);

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      disabled={disabled}
      title={label}
      aria-label={label}
      onPointerDown={handlePointerDown}
      onPointerUp={handlePointerEnd}
      onPointerLeave={handlePointerEnd}
      onPointerCancel={handlePointerEnd}
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => {
        if (disabled) return;
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onComplete();
        }
      }}
      className={cn(
        "relative size-6 text-muted-foreground hover:text-foreground hover:bg-sidebar-accent",
        className,
      )}
    >
      <span className="relative size-5 flex items-center justify-center">
        <span className="relative z-10 flex items-center justify-center">
          {icon}
        </span>
      </span>
    </Button>
  );
}

// ---------------------------------------------------------------------------
// Droppable "All Tasks" group
// ---------------------------------------------------------------------------

interface DroppableAllTasksGroupProps {
  title: string;
  tasks: TaskHistoryItem[];
  onDeleteTask: (taskId: string) => Promise<void> | void;
  onRenameTask?: (taskId: string, newName: string) => Promise<void> | void;
  onMoveTaskToProject?: (taskId: string, projectId: string | null) => void;
  projects: ProjectItem[];
  isSelectionMode?: boolean;
  isOtherSelectionMode?: boolean;
  selectedTaskIds?: Set<string>;
  onToggleTaskSelection?: (taskId: string) => void;
  onEnterSelectionMode?: () => void;
  onTaskNavigate?: () => void;
}

function DroppableAllTasksGroup({
  title,
  tasks,
  onDeleteTask,
  onRenameTask,
  onMoveTaskToProject,
  projects,
  isSelectionMode,
  isOtherSelectionMode,
  selectedTaskIds,
  onToggleTaskSelection,
  onEnterSelectionMode,
  onTaskNavigate,
}: DroppableAllTasksGroupProps) {
  const { t } = useT("translation");
  const { setNodeRef, isOver } = useDroppable({
    id: "all-tasks",
    data: { type: "all-tasks" },
  });

  return (
    <Collapsible defaultOpen className="group/collapsible-tasks flex flex-col">
      <SidebarGroup
        ref={setNodeRef}
        data-onboarding="sidebar-task-list"
        className={cn(
          "p-0 flex flex-col transition-colors rounded-lg overflow-hidden",
          isOver && "bg-primary/10",
        )}
      >
        <div className="group/tasks-header relative flex items-center justify-between p-2 shrink-0">
          <SidebarGroupLabel asChild>
            <CollapsibleTrigger className="flex flex-1 items-center gap-2 text-xs font-medium text-muted-foreground hover:text-foreground cursor-pointer">
              {title}
              <ChevronRight className="size-4 transition-transform duration-200 group-data-[state=open]/collapsible-tasks:rotate-90" />
            </CollapsibleTrigger>
          </SidebarGroupLabel>
          <LongPressActionButton
            icon={<CheckCheck className="size-4" />}
            label={
              isSelectionMode
                ? t("sidebar.holdToExitSelect")
                : t("sidebar.holdToSelect")
            }
            disabled={isOtherSelectionMode}
            onComplete={() => onEnterSelectionMode?.()}
            className="opacity-0 group-hover/tasks-header:opacity-100 transition-opacity group-data-[collapsible=icon]:hidden"
          />
        </div>
        <CollapsibleContent>
          <SidebarGroupContent className="p-2 pt-0 mt-0 group-data-[collapsible=icon]:mt-0">
            <TaskHistoryList
              tasks={tasks}
              onDeleteTask={onDeleteTask}
              onRenameTask={onRenameTask}
              onMoveTaskToProject={onMoveTaskToProject}
              projects={projects}
              showDropIndicator={isOver}
              dropIndicatorLabel={t("sidebar.moveToHere")}
              isSelectionMode={isSelectionMode}
              selectedTaskIds={selectedTaskIds}
              onToggleTaskSelection={onToggleTaskSelection}
              onNavigate={onTaskNavigate}
            />
          </SidebarGroupContent>
        </CollapsibleContent>
      </SidebarGroup>
    </Collapsible>
  );
}

// ---------------------------------------------------------------------------
// Main content section
// ---------------------------------------------------------------------------

interface SidebarContentSectionProps {
  projects: ProjectItem[];
  taskHistory: TaskHistoryItem[];
  onDeleteTask: (taskId: string) => Promise<void> | void;
  onRenameTask?: (taskId: string, newName: string) => Promise<void> | void;
  onMoveTaskToProject?: (taskId: string, projectId: string | null) => void;
  onRenameProject?: (projectId: string, newName: string) => void;
  onDeleteProject?: (projectId: string) => Promise<void> | void;
  onOpenCreateProjectDialog?: () => void;
  // Selection state (from useSidebarSelection)
  isTaskSelectionMode: boolean;
  isProjectSelectionMode: boolean;
  selectedTaskIds: Set<string>;
  selectedProjectIds: Set<string>;
  onEnterTaskSelectionMode: () => void;
  onEnterProjectSelectionMode: () => void;
  onCancelSelection: () => void;
  onToggleTaskSelection: (taskId: string) => void;
  onToggleProjectSelection: (projectId: string) => void;
}

export function SidebarContentSection({
  projects,
  taskHistory,
  onDeleteTask,
  onRenameTask,
  onMoveTaskToProject,
  onRenameProject,
  onDeleteProject,
  onOpenCreateProjectDialog,
  isTaskSelectionMode,
  isProjectSelectionMode,
  selectedTaskIds,
  selectedProjectIds,
  onEnterTaskSelectionMode,
  onEnterProjectSelectionMode,
  onCancelSelection,
  onToggleTaskSelection,
  onToggleProjectSelection,
}: SidebarContentSectionProps) {
  const { t } = useT("translation");
  const router = useRouter();
  const params = useParams();
  const { isMobile, setOpenMobile } = useSidebar();

  const lng = React.useMemo(() => {
    const value = params?.lng;
    if (!value) return undefined;
    return Array.isArray(value) ? value[0] : value;
  }, [params]);

  // Track scroll state for border
  const [isContentScrolled, setIsContentScrolled] = React.useState(false);
  const scrollAreaRef = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    const viewport = scrollAreaRef.current?.querySelector<HTMLElement>(
      "[data-slot='scroll-area-viewport']",
    );
    if (!viewport) return;

    const handleViewportScroll = () => {
      setIsContentScrolled(viewport.scrollTop > 0);
    };

    handleViewportScroll();
    viewport.addEventListener("scroll", handleViewportScroll, {
      passive: true,
    });
    return () => {
      viewport.removeEventListener("scroll", handleViewportScroll);
    };
  }, []);

  // Project expand/collapse state
  const [expandedProjects, setExpandedProjects] = React.useState<Set<string>>(
    new Set(),
  );

  // Auto-expand project when navigating to a session
  React.useEffect(() => {
    const activeTaskId = params?.id;
    if (activeTaskId && typeof activeTaskId === "string") {
      const activeTask = taskHistory.find((task) => task.id === activeTaskId);
      if (activeTask?.projectId) {
        setExpandedProjects((prev) => {
          if (!prev.has(activeTask.projectId!)) {
            const next = new Set(prev);
            next.add(activeTask.projectId!);
            return next;
          }
          return prev;
        });
      }
    }
  }, [params?.id, taskHistory]);

  const toggleProjectExpanded = React.useCallback((projectId: string) => {
    setExpandedProjects((prev) => {
      const next = new Set(prev);
      if (next.has(projectId)) next.delete(projectId);
      else next.add(projectId);
      return next;
    });
  }, []);

  // Derived data
  const unassignedTasks = React.useMemo(
    () => taskHistory.filter((task) => !task.projectId),
    [taskHistory],
  );

  const tasksByProject = React.useMemo(() => {
    const grouped = new Map<string, TaskHistoryItem[]>();
    taskHistory.forEach((task) => {
      if (task.projectId) {
        if (!grouped.has(task.projectId)) grouped.set(task.projectId, []);
        grouped.get(task.projectId)!.push(task);
      }
    });
    return grouped;
  }, [taskHistory]);

  const closeMobileSidebar = React.useCallback(() => {
    if (isMobile) setOpenMobile(false);
  }, [isMobile, setOpenMobile]);

  const handleProjectClick = React.useCallback(
    (projectId: string) => {
      router.push(
        lng ? `/${lng}/projects/${projectId}` : `/projects/${projectId}`,
      );
      closeMobileSidebar();
    },
    [router, lng, closeMobileSidebar],
  );

  const handleRenameProject = React.useCallback(
    (projectId: string, name: string) => {
      onRenameProject?.(projectId, name);
    },
    [onRenameProject],
  );

  return (
    <SidebarContent
      className={cn(
        "border-t flex flex-col overflow-hidden gap-0 transition-colors",
        isContentScrolled ? "border-border" : "border-transparent",
      )}
    >
      <ScrollArea
        ref={scrollAreaRef}
        className="min-h-0 flex-1 [&_[data-slot=scroll-area-viewport]]:overflow-x-hidden"
      >
        <div className="flex flex-col">
          {/* Projects section */}
          <div className="flex flex-col">
            <Collapsible
              defaultOpen
              className="group/collapsible-projects flex flex-col"
            >
              <SidebarGroup
                className="p-0 flex flex-col group-data-[collapsible=icon]:hidden"
                data-onboarding="sidebar-projects"
              >
                <div className="group/projects-header relative flex items-center justify-between p-2 shrink-0">
                  <SidebarGroupLabel asChild>
                    <CollapsibleTrigger className="flex flex-1 items-center gap-2 text-xs font-medium text-muted-foreground hover:text-foreground cursor-pointer">
                      {t("sidebar.projects")}
                      <ChevronRight className="size-4 transition-transform duration-200 group-data-[state=open]/collapsible-projects:rotate-90" />
                    </CollapsibleTrigger>
                  </SidebarGroupLabel>
                  <div className="flex items-center gap-1">
                    <LongPressActionButton
                      icon={<CheckCheck className="size-4" />}
                      label={
                        isProjectSelectionMode
                          ? t("sidebar.holdToExitSelect")
                          : t("sidebar.holdToSelect")
                      }
                      disabled={isTaskSelectionMode}
                      onComplete={
                        isProjectSelectionMode
                          ? onCancelSelection
                          : onEnterProjectSelectionMode
                      }
                      className="opacity-0 group-hover/projects-header:opacity-100 transition-opacity"
                    />
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => onOpenCreateProjectDialog?.()}
                      className="size-6 text-muted-foreground hover:text-foreground hover:bg-sidebar-accent opacity-0 group-hover/projects-header:opacity-100 transition-opacity"
                      title={t("sidebar.newProject")}
                    >
                      <Plus className="size-4" />
                    </Button>
                  </div>
                </div>
                <CollapsibleContent className="data-[state=closed]:flex-none">
                  <SidebarGroupContent className="mt-1 group-data-[collapsible=icon]:mt-0 p-2 pt-0">
                    <SidebarMenu>
                      {projects.map((project) => (
                        <CollapsibleProjectItem
                          key={project.id}
                          project={project}
                          tasks={tasksByProject.get(project.id) || []}
                          isExpanded={expandedProjects.has(project.id)}
                          onToggle={() => toggleProjectExpanded(project.id)}
                          onProjectClick={() => handleProjectClick(project.id)}
                          onDeleteTask={onDeleteTask}
                          onRenameTask={onRenameTask}
                          onMoveTaskToProject={onMoveTaskToProject}
                          allProjects={projects}
                          onRenameProject={handleRenameProject}
                          onDeleteProject={onDeleteProject}
                          isProjectSelectionMode={isProjectSelectionMode}
                          isTaskSelectionMode={isTaskSelectionMode}
                          selectedTaskIds={selectedTaskIds}
                          selectedProjectIds={selectedProjectIds}
                          onToggleTaskSelection={onToggleTaskSelection}
                          onToggleProjectSelection={onToggleProjectSelection}
                          onTaskNavigate={closeMobileSidebar}
                        />
                      ))}
                    </SidebarMenu>
                  </SidebarGroupContent>
                </CollapsibleContent>
              </SidebarGroup>
            </Collapsible>
          </div>

          {/* Unassigned tasks section */}
          <div className="flex flex-col">
            <DroppableAllTasksGroup
              title={t("sidebar.allTasks")}
              tasks={unassignedTasks}
              onDeleteTask={onDeleteTask}
              onRenameTask={onRenameTask}
              onMoveTaskToProject={onMoveTaskToProject}
              projects={projects}
              isSelectionMode={isTaskSelectionMode}
              isOtherSelectionMode={isProjectSelectionMode}
              selectedTaskIds={selectedTaskIds}
              onToggleTaskSelection={onToggleTaskSelection}
              onEnterSelectionMode={
                isTaskSelectionMode
                  ? onCancelSelection
                  : onEnterTaskSelectionMode
              }
              onTaskNavigate={closeMobileSidebar}
            />
          </div>
        </div>
      </ScrollArea>
    </SidebarContent>
  );
}
