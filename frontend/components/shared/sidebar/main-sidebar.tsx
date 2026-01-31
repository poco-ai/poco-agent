"use client";

import * as React from "react";
import { useRouter, useParams } from "next/navigation";
import {
  Bot,
  MoreHorizontal,
  PanelLeftClose,
  PanelLeftOpen,
  PenSquare,
  Plus,
  Search,
  SlidersHorizontal,
  Sparkles,
  Trash2,
  X,
  ChevronRight,
  ListFilter,
} from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  DndContext,
  DragEndEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  useDroppable,
} from "@dnd-kit/core";

import { useT } from "@/lib/i18n/client";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  useSidebar,
} from "@/components/ui/sidebar";

import type { ProjectItem, TaskHistoryItem } from "@/features/projects/types";
import { TaskHistoryList } from "./task-history-list";
import { CollapsibleProjectItem } from "./collapsible-project-item";
import { useSearchDialog } from "@/features/search/hooks/use-search-dialog";

const TOP_NAV_ITEMS = [
  { id: "search", labelKey: "sidebar.search", icon: Search, href: null },
  {
    id: "capabilities",
    labelKey: "sidebar.library",
    icon: Sparkles,
    href: "/capabilities",
  },
] as const;

function DroppableAllTasksGroup({
  title,
  tasks,
  onDeleteTask,
  onRenameTask,
  onMoveTaskToProject,
  projects,
  isSelectionMode,
  selectedTaskIds,
  onToggleTaskSelection,
  onEnableSelectionMode,
}: {
  title: string;
  tasks: TaskHistoryItem[];
  onDeleteTask: (taskId: string) => Promise<void> | void;
  onRenameTask?: (taskId: string, newName: string) => void;
  onMoveTaskToProject?: (taskId: string, projectId: string | null) => void;
  projects: ProjectItem[];
  isSelectionMode?: boolean;
  selectedTaskIds?: Set<string>;
  onToggleTaskSelection?: (taskId: string) => void;
  onEnableSelectionMode?: (taskId: string) => void;
}) {
  const { t } = useT("translation");
  const { setNodeRef, isOver } = useDroppable({
    id: "all-tasks",
    data: {
      type: "all-tasks",
    },
  });

  return (
    <Collapsible
      defaultOpen
      className="group/collapsible-tasks flex flex-col h-full min-h-0"
    >
      <SidebarGroup
        ref={setNodeRef}
        className={cn(
          "p-0 flex flex-col h-full min-h-0 transition-colors rounded-lg overflow-hidden",
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
          <Button
            variant="ghost"
            size="icon"
            className="relative z-10 size-5 flex items-center justify-center text-muted-foreground hover:bg-sidebar-accent"
            title={t("sidebar.filter") || "Filter"}
          >
            <ListFilter className="size-3.5" />
          </Button>
        </div>
        <CollapsibleContent className="flex-1 min-h-0 data-[state=closed]:flex-none">
          <ScrollArea className="h-full">
            <SidebarGroupContent className="p-2 pt-0 mt-0 group-data-[collapsible=icon]:mt-0">
              <TaskHistoryList
                tasks={tasks}
                onDeleteTask={onDeleteTask}
                onRenameTask={onRenameTask}
                onMoveTaskToProject={onMoveTaskToProject}
                projects={projects}
                isSelectionMode={isSelectionMode}
                selectedTaskIds={selectedTaskIds}
                onToggleTaskSelection={onToggleTaskSelection}
                onEnableSelectionMode={onEnableSelectionMode}
              />
              {isOver && (
                <div className="flex items-center justify-center p-2 text-xs text-primary bg-primary/5 rounded border border-dashed border-primary/20 mt-1">
                  {t("sidebar.removeFromProject")}
                </div>
              )}
            </SidebarGroupContent>
          </ScrollArea>
        </CollapsibleContent>
      </SidebarGroup>
    </Collapsible>
  );
}

export function MainSidebar({
  projects,
  taskHistory,
  onNewTask,
  onDeleteTask,
  onRenameTask,
  onMoveTaskToProject,
  onRenameProject,
  onDeleteProject,
  onOpenSettings,
  onOpenCreateProjectDialog,
}: {
  projects: ProjectItem[];
  taskHistory: TaskHistoryItem[];
  onNewTask: () => void;
  onDeleteTask: (taskId: string) => Promise<void> | void;
  onRenameTask?: (taskId: string, newName: string) => void;
  onMoveTaskToProject?: (taskId: string, projectId: string | null) => void;
  onRenameProject?: (projectId: string, newName: string) => void;
  onDeleteProject?: (projectId: string) => Promise<void> | void;
  onOpenSettings?: () => void;
  onOpenCreateProjectDialog?: () => void;
}) {
  const { t } = useT("translation");
  const router = useRouter();
  const params = useParams();
  const { toggleSidebar } = useSidebar();
  const { searchKey } = useSearchDialog();

  const lng = React.useMemo(() => {
    const value = params?.lng;
    if (!value) return undefined;
    return Array.isArray(value) ? value[0] : value;
  }, [params]);

  // Selection Mode State
  const [isSelectionMode, setIsSelectionMode] = React.useState(false);
  const [selectedTaskIds, setSelectedTaskIds] = React.useState<Set<string>>(
    new Set(),
  );
  const [selectedProjectIds, setSelectedProjectIds] = React.useState<
    Set<string>
  >(new Set());

  // 管理每个项目的折叠状态
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

  // 过滤出未归类到项目的任务
  const unassignedTasks = React.useMemo(
    () => taskHistory.filter((task) => !task.projectId),
    [taskHistory],
  );

  // 按项目分组任务
  const tasksByProject = React.useMemo(() => {
    const grouped = new Map<string, TaskHistoryItem[]>();
    taskHistory.forEach((task) => {
      if (task.projectId) {
        if (!grouped.has(task.projectId)) {
          grouped.set(task.projectId, []);
        }
        grouped.get(task.projectId)!.push(task);
      }
    });
    return grouped;
  }, [taskHistory]);

  // Configure drag sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // 8px movement required to start dragging
      },
    }),
  );

  // Selection handlers
  const handleEnableTaskSelectionMode = React.useCallback((taskId: string) => {
    setIsSelectionMode(true);
    setSelectedTaskIds(new Set([taskId]));
    setSelectedProjectIds(new Set());
  }, []);

  const handleToggleTaskSelection = React.useCallback((taskId: string) => {
    setSelectedTaskIds((prev) => {
      const next = new Set(prev);
      if (next.has(taskId)) {
        next.delete(taskId);
      } else {
        next.add(taskId);
      }
      return next;
    });
  }, []);

  const handleToggleProjectSelection = React.useCallback(
    (projectId: string) => {
      setSelectedProjectIds((prev) => {
        const next = new Set(prev);
        if (next.has(projectId)) {
          next.delete(projectId);
        } else {
          next.add(projectId);
        }
        return next;
      });
    },
    [],
  );

  const handleEnableProjectSelectionMode = React.useCallback(
    (projectId: string) => {
      setIsSelectionMode(true);
      setSelectedProjectIds(new Set([projectId]));
      setSelectedTaskIds(new Set());
    },
    [],
  );

  const handleCancelSelectionMode = React.useCallback(() => {
    setIsSelectionMode(false);
    setSelectedTaskIds(new Set());
    setSelectedProjectIds(new Set());
  }, []);

  // Handle Esc key to exit selection mode
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isSelectionMode) {
        handleCancelSelectionMode();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isSelectionMode, handleCancelSelectionMode]);

  const handleDeleteSelectedItems = React.useCallback(async () => {
    await Promise.all(
      Array.from(selectedTaskIds).map((taskId) =>
        Promise.resolve(onDeleteTask(taskId)),
      ),
    );

    if (onDeleteProject) {
      for (const projectId of selectedProjectIds) {
        await onDeleteProject(projectId);
      }
    }

    handleCancelSelectionMode();
  }, [
    selectedTaskIds,
    selectedProjectIds,
    onDeleteTask,
    onDeleteProject,
    handleCancelSelectionMode,
  ]);

  const handleRenameProject = React.useCallback(
    (projectId: string, name: string) => {
      onRenameProject?.(projectId, name);
    },
    [onRenameProject],
  );

  const handleProjectClick = React.useCallback(
    (projectId: string) => {
      router.push(
        lng ? `/${lng}/projects/${projectId}` : `/projects/${projectId}`,
      );
    },
    [router, lng],
  );

  const toggleProjectExpanded = React.useCallback((projectId: string) => {
    setExpandedProjects((prev) => {
      const next = new Set(prev);
      if (next.has(projectId)) {
        next.delete(projectId);
      } else {
        next.add(projectId);
      }
      return next;
    });
  }, []);

  // Handle drag end event
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (!over) return;

    const activeId = active.id;
    const overId = over.id;

    if (activeId === overId) return;

    const activeData = active.data.current;
    const overData = over.data.current;

    // Ensure we are dragging a task
    if (activeData?.type !== "task") return;

    const taskId = activeData.taskId as string;
    let targetProjectId: string | null | undefined = undefined;

    // If dropped on a project item
    if (overData?.type === "project") {
      targetProjectId = overData.projectId;
    } else if (overData?.type === "all-tasks") {
      targetProjectId = null;
    }

    // If we have a valid target (including null for unassigning), trigger move
    if (targetProjectId !== undefined) {
      onMoveTaskToProject?.(taskId, targetProjectId);
    }
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragEnd={handleDragEnd}
    >
      <Sidebar
        collapsible="icon"
        className="border-r-0 bg-sidebar overflow-hidden"
      >
        <SidebarHeader className="gap-2 pb-2">
          {/* Logo 和折叠按钮 */}
          <div className="mb-3 flex items-center justify-between pt-2 group-data-[collapsible=icon]:justify-start">
            <div className="flex items-center gap-3 group-data-[collapsible=icon]:gap-0">
              {/* 折叠状态下：默认显示 Logo，悬停显示展开按钮 */}
              <button
                onClick={toggleSidebar}
                className="group/logo relative flex size-8 items-center justify-center overflow-hidden rounded-lg bg-sidebar-primary text-sidebar-primary-foreground shadow-md transition-all hover:shadow-lg active:scale-95 active:shadow-sm"
                type="button"
              >
                <Bot className="size-5 transition-opacity group-data-[collapsible=icon]:group-hover/logo:opacity-0" />
                <PanelLeftOpen className="absolute hidden size-4 group-data-[collapsible=icon]:group-hover/logo:block" />
              </button>
              <span
                onClick={() => router.push(lng ? `/${lng}/home` : "/")}
                className="text-xl font-medium tracking-tight text-sidebar-foreground group-data-[collapsible=icon]:hidden cursor-pointer hover:opacity-80 transition-opacity font-[family-name:var(--font-space-grotesk)]"
              >
                Poco
              </span>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleSidebar}
              className="size-8 text-sidebar-foreground hover:bg-sidebar-accent group-data-[collapsible=icon]:hidden"
            >
              <PanelLeftClose className="size-4" />
            </Button>
          </div>

          {!isSelectionMode && (
            <>
              {/* 新建任务按钮 */}
              <SidebarMenu className="group-data-[collapsible=icon]:px-0">
                <SidebarMenuItem>
                  <SidebarMenuButton
                    onClick={onNewTask}
                    className="h-[36px] min-w-0 max-w-[calc(var(--sidebar-width)-16px)] w-full justify-start gap-3 rounded-[10px] px-3 py-[7.5px] text-muted-foreground transition-colors hover:bg-sidebar-accent group-data-[collapsible=icon]:w-[var(--sidebar-width-icon)] group-data-[collapsible=icon]:max-w-[var(--sidebar-width-icon)] group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0"
                    tooltip={t("sidebar.newTask")}
                  >
                    <PenSquare className="size-4 shrink-0" />
                    <span className="text-sm truncate group-data-[collapsible=icon]:hidden">
                      {t("sidebar.newTask")}
                    </span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>

              {TOP_NAV_ITEMS.map(({ id, labelKey, icon: Icon, href }) => {
                const isDisabled = id === "search"; // Search temporarily disabled
                return (
                  <SidebarMenu
                    key={id}
                    className="group-data-[collapsible=icon]:px-0"
                  >
                    <SidebarMenuItem>
                      <SidebarMenuButton
                        onClick={() => {
                          if (isDisabled) return; // Disabled - do nothing
                          if (href) {
                            router.push(lng ? `/${lng}${href}` : href);
                          }
                        }}
                        className={cn(
                          "h-[36px] min-w-0 max-w-[calc(var(--sidebar-width)-16px)] w-full justify-start gap-3 rounded-[10px] px-3 py-[7.5px] text-muted-foreground transition-colors hover:bg-sidebar-accent group-data-[collapsible=icon]:w-[var(--sidebar-width-icon)] group-data-[collapsible=icon]:max-w-[var(--sidebar-width-icon)] group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0",
                          isDisabled &&
                            "opacity-50 cursor-not-allowed hover:bg-transparent",
                        )}
                        tooltip={
                          isDisabled ? `${t(labelKey)} (暂不可用)` : t(labelKey)
                        }
                      >
                        <Icon className="size-4 shrink-0" />
                        <span className="text-sm truncate group-data-[collapsible=icon]:hidden">
                          {t(labelKey)}
                        </span>
                        {id === "search" && (
                          <kbd className="ml-auto text-xs opacity-60 group-data-[collapsible=icon]:hidden">
                            {searchKey}
                          </kbd>
                        )}
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  </SidebarMenu>
                );
              })}
            </>
          )}

          {isSelectionMode && (
            <div className="px-2 py-1 text-sm font-medium text-sidebar-foreground group-data-[collapsible=icon]:hidden">
              批量操作
            </div>
          )}
        </SidebarHeader>

        <SidebarContent className="flex flex-col !overflow-hidden gap-0">
          {/* 项目列表 - 放在上面 */}
          <div className="flex-shrink-0 max-h-[50%] flex flex-col min-h-0">
            <Collapsible
              defaultOpen
              className="group/collapsible-projects flex flex-col min-h-0 h-full"
            >
              <SidebarGroup className="p-0 flex flex-col min-h-0 h-full overflow-hidden group-data-[collapsible=icon]:hidden">
                <div className="group/projects-header relative flex items-center justify-between p-2 shrink-0">
                  <SidebarGroupLabel asChild>
                    <CollapsibleTrigger className="flex flex-1 items-center gap-2 text-xs font-medium text-muted-foreground hover:text-foreground cursor-pointer">
                      {t("sidebar.projects")}
                      <ChevronRight className="size-4 transition-transform duration-200 group-data-[state=open]/collapsible-projects:rotate-90" />
                    </CollapsibleTrigger>
                  </SidebarGroupLabel>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => onOpenCreateProjectDialog?.()}
                    className="relative z-10 size-5 flex items-center justify-center text-muted-foreground hover:bg-sidebar-accent"
                    title={t("sidebar.newProject")}
                  >
                    <Plus className="size-3.5" />
                  </Button>
                </div>
                <CollapsibleContent className="flex-1 min-h-0 data-[state=closed]:flex-none">
                  <ScrollArea className="h-full">
                    <SidebarGroupContent className="mt-1 group-data-[collapsible=icon]:mt-0 p-2 pt-0">
                      <SidebarMenu>
                        {projects.map((project) => (
                          <CollapsibleProjectItem
                            key={project.id}
                            project={project}
                            tasks={tasksByProject.get(project.id) || []}
                            isExpanded={expandedProjects.has(project.id)}
                            onToggle={() => toggleProjectExpanded(project.id)}
                            onProjectClick={() =>
                              handleProjectClick(project.id)
                            }
                            onDeleteTask={onDeleteTask}
                            onRenameTask={onRenameTask}
                            onMoveTaskToProject={onMoveTaskToProject}
                            allProjects={projects}
                            onRenameProject={handleRenameProject}
                            onDeleteProject={onDeleteProject}
                            isSelectionMode={isSelectionMode}
                            selectedTaskIds={selectedTaskIds}
                            selectedProjectIds={selectedProjectIds}
                            onToggleTaskSelection={handleToggleTaskSelection}
                            onEnableSelectionMode={
                              handleEnableTaskSelectionMode
                            }
                            onToggleProjectSelection={
                              handleToggleProjectSelection
                            }
                            onEnableProjectSelectionMode={
                              handleEnableProjectSelectionMode
                            }
                          />
                        ))}
                      </SidebarMenu>
                    </SidebarGroupContent>
                  </ScrollArea>
                </CollapsibleContent>
              </SidebarGroup>
            </Collapsible>
          </div>

          <div className="flex-1 min-h-0 flex flex-col">
            {/* 所有任务（未归类） - 放在下面 */}
            <DroppableAllTasksGroup
              title={t("sidebar.allTasks")}
              tasks={unassignedTasks}
              onDeleteTask={onDeleteTask}
              onRenameTask={onRenameTask}
              onMoveTaskToProject={onMoveTaskToProject}
              projects={projects}
              isSelectionMode={isSelectionMode}
              selectedTaskIds={selectedTaskIds}
              onToggleTaskSelection={handleToggleTaskSelection}
              onEnableSelectionMode={handleEnableTaskSelectionMode}
            />
          </div>
        </SidebarContent>

        <SidebarFooter className="border-t border-sidebar-border p-2 group-data-[collapsible=icon]:p-2 relative bg-sidebar">
          {isSelectionMode ? (
            <div className="flex items-center justify-between w-full animate-in slide-in-from-bottom duration-200 px-1">
              <Button
                variant="ghost"
                size="icon"
                onClick={handleCancelSelectionMode}
                className="size-8 text-muted-foreground hover:bg-sidebar-accent"
                title={t("common.cancel") || "取消"}
              >
                <X className="size-4" />
              </Button>

              <div className="text-xs text-muted-foreground font-medium">
                {selectedTaskIds.size + selectedProjectIds.size}
              </div>

              <Button
                variant="ghost"
                size="icon"
                onClick={handleDeleteSelectedItems}
                disabled={selectedTaskIds.size + selectedProjectIds.size === 0}
                className="size-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                title={t("common.delete") || "删除"}
              >
                <Trash2 className="size-4" />
              </Button>
            </div>
          ) : (
            /* 底部工具栏 - 正常模式 */
            <div className="flex items-center justify-start px-1 group-data-[collapsible=icon]:px-0">
              <Button
                variant="ghost"
                size="icon"
                onClick={onOpenSettings}
                className="size-8 text-muted-foreground hover:bg-sidebar-accent"
                title={t("sidebar.settings")}
              >
                <SlidersHorizontal className="size-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="ml-auto size-8 text-muted-foreground hover:bg-sidebar-accent group-data-[collapsible=icon]:hidden"
              >
                <MoreHorizontal className="size-4" />
              </Button>
            </div>
          )}
        </SidebarFooter>

        <SidebarRail />
      </Sidebar>
    </DndContext>
  );
}
