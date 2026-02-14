"use client";

import * as React from "react";
import { useRouter, useParams } from "next/navigation";
import {
  Bot,
  PanelLeftClose,
  PanelLeftOpen,
  PenSquare,
  Plus,
  Search,
  SlidersHorizontal,
  Sparkles,
  Clock,
  Trash2,
  X,
  ChevronRight,
  Settings2,
  Moon,
  Sun,
  Languages,
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

import { useTheme } from "next-themes";

import { useT } from "@/lib/i18n/client";
import { Button } from "@/components/ui/button";
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
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

import type { ProjectItem, TaskHistoryItem } from "@/features/projects/types";
import type { SettingsTabId } from "@/features/settings/types";
import { TaskHistoryList } from "./task-history-list";
import { CollapsibleProjectItem } from "./collapsible-project-item";
import { useSearchDialog } from "@/features/search/hooks/use-search-dialog";
import { useSettingsLanguage } from "@/features/settings/hooks/use-settings-language";
import {
  useBackendPreference,
  type BackendOption,
} from "@/features/settings/hooks/use-backend-preference";
import { useUserAccount } from "@/features/user/hooks/use-user-account";

const TOP_NAV_ITEMS = [
  { id: "search", labelKey: "sidebar.search", icon: Search, href: null },
  {
    id: "capabilities",
    labelKey: "sidebar.library",
    icon: Sparkles,
    href: "/capabilities",
  },
  {
    id: "scheduled-tasks",
    labelKey: "sidebar.scheduledTasks",
    icon: Clock,
    href: "/capabilities/scheduled-tasks",
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
  onTaskNavigate,
}: {
  title: string;
  tasks: TaskHistoryItem[];
  onDeleteTask: (taskId: string) => Promise<void> | void;
  onRenameTask?: (taskId: string, newName: string) => Promise<void> | void;
  onMoveTaskToProject?: (taskId: string, projectId: string | null) => void;
  projects: ProjectItem[];
  isSelectionMode?: boolean;
  selectedTaskIds?: Set<string>;
  onToggleTaskSelection?: (taskId: string) => void;
  onEnableSelectionMode?: (taskId: string) => void;
  onTaskNavigate?: () => void;
}) {
  const { t } = useT("translation");
  const { setNodeRef, isOver } = useDroppable({
    id: "all-tasks",
    data: {
      type: "all-tasks",
    },
  });

  return (
    <Collapsible defaultOpen className="group/collapsible-tasks flex flex-col">
      <SidebarGroup
        ref={setNodeRef}
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
        </div>
        <CollapsibleContent>
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
              onNavigate={onTaskNavigate}
            />
            {isOver && (
              <div className="flex items-center justify-center p-2 text-xs text-primary bg-primary/5 rounded border border-dashed border-primary/20 mt-1">
                {t("sidebar.removeFromProject")}
              </div>
            )}
          </SidebarGroupContent>
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
  onRenameTask?: (taskId: string, newName: string) => Promise<void> | void;
  onMoveTaskToProject?: (taskId: string, projectId: string | null) => void;
  onRenameProject?: (projectId: string, newName: string) => void;
  onDeleteProject?: (projectId: string) => Promise<void> | void;
  onOpenSettings?: (tab?: SettingsTabId) => void;
  onOpenCreateProjectDialog?: () => void;
}) {
  const { t } = useT("translation");
  const router = useRouter();
  const params = useParams();
  const { toggleSidebar, isMobile, setOpenMobile } = useSidebar();
  const { searchKey } = useSearchDialog();
  const { theme, setTheme } = useTheme();
  const { currentLanguage, changeLanguage } = useSettingsLanguage();
  const { backend, setBackend } = useBackendPreference();
  const { profile } = useUserAccount();
  const mobileUserName = profile?.email
    ? profile.email.split("@")[0] || profile.email
    : t("sidebar.defaultUserName");
  const mobileAvatarInitial = mobileUserName.charAt(0).toUpperCase() || "U";

  const lng = React.useMemo(() => {
    const value = params?.lng;
    if (!value) return undefined;
    return Array.isArray(value) ? value[0] : value;
  }, [params]);

  const handleThemeSelect = React.useCallback(
    (nextTheme: string) => {
      if (nextTheme !== "light" && nextTheme !== "dark") return;
      setTheme(nextTheme);
    },
    [setTheme],
  );

  const handleBackendSelect = React.useCallback(
    (nextBackend: string) => {
      if (nextBackend !== "claude-code") return;
      setBackend(nextBackend as BackendOption);
    },
    [setBackend],
  );

  // Selection Mode State
  const [isSelectionMode, setIsSelectionMode] = React.useState(false);
  const [selectedTaskIds, setSelectedTaskIds] = React.useState<Set<string>>(
    new Set(),
  );
  const [selectedProjectIds, setSelectedProjectIds] = React.useState<
    Set<string>
  >(new Set());

  // Track expanded/collapsed state for each project.
  const [expandedProjects, setExpandedProjects] = React.useState<Set<string>>(
    new Set(),
  );
  const [isContentScrolled, setIsContentScrolled] = React.useState(false);

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

  // Tasks not assigned to any project.
  const unassignedTasks = React.useMemo(
    () => taskHistory.filter((task) => !task.projectId),
    [taskHistory],
  );

  // Group tasks by project.
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

  const closeMobileSidebar = React.useCallback(() => {
    if (isMobile) {
      setOpenMobile(false);
    }
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

  const handleContentScroll = React.useCallback(
    (event: React.UIEvent<HTMLDivElement>) => {
      setIsContentScrolled(event.currentTarget.scrollTop > 0);
    },
    [],
  );

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
          {/* Logo and collapse button */}
          <div className="mb-3 flex items-center justify-between pt-2 group-data-[collapsible=icon]:justify-start">
            <div className="flex items-center gap-3 group-data-[collapsible=icon]:gap-0">
              {/* Collapsed: show logo by default; show expand icon on hover. */}
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
              {/* New task button */}
              <SidebarMenu className="group-data-[collapsible=icon]:px-0">
                <SidebarMenuItem>
                  <SidebarMenuButton
                    onClick={() => {
                      onNewTask();
                      closeMobileSidebar();
                    }}
                    className="h-[36px] min-w-0 max-w-[calc(var(--sidebar-width)-16px)] w-full justify-start gap-3 rounded-[10px] px-3 py-[7.5px] text-muted-foreground transition-colors hover:bg-sidebar-accent group-data-[collapsible=icon]:w-[var(--sidebar-width-icon)] group-data-[collapsible=icon]:max-w-[var(--sidebar-width-icon)] group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0 group/new-task"
                    tooltip={t("sidebar.newTask")}
                  >
                    <PenSquare className="size-4 shrink-0 transition-transform duration-200 group-hover/new-task:rotate-12 group-hover/new-task:scale-110" />
                    <span className="text-sm truncate group-data-[collapsible=icon]:hidden">
                      {t("sidebar.newTask")}
                    </span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>

              {TOP_NAV_ITEMS.map(({ id, labelKey, icon: Icon, href }) => {
                const isDisabled = id === "search"; // Search temporarily disabled
                // Apply different icon animations per menu item.
                const getIconAnimation = () => {
                  if (isDisabled) return ""; // No animation when disabled.
                  switch (id) {
                    case "capabilities":
                      return "transition-all duration-300 group-hover/menu-item:rotate-12 group-hover/menu-item:scale-110";
                    case "scheduled-tasks":
                      return "transition-transform duration-500 group-hover/menu-item:rotate-[360deg]";
                    default:
                      return "";
                  }
                };

                return (
                  <SidebarMenu
                    key={id}
                    className="group-data-[collapsible=icon]:px-0"
                  >
                    <SidebarMenuItem className="group/menu-item">
                      <SidebarMenuButton
                        onClick={() => {
                          if (isDisabled) return; // Disabled - do nothing
                          if (href) {
                            router.push(lng ? `/${lng}${href}` : href);
                            closeMobileSidebar();
                          }
                        }}
                        className={cn(
                          "h-[36px] min-w-0 max-w-[calc(var(--sidebar-width)-16px)] w-full justify-start gap-3 rounded-[10px] px-3 py-[7.5px] text-muted-foreground transition-colors hover:bg-sidebar-accent group-data-[collapsible=icon]:w-[var(--sidebar-width-icon)] group-data-[collapsible=icon]:max-w-[var(--sidebar-width-icon)] group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0",
                          isDisabled &&
                            "opacity-50 cursor-not-allowed hover:bg-transparent",
                        )}
                        tooltip={t(labelKey)}
                      >
                        <Icon
                          className={cn("size-4 shrink-0", getIconAnimation())}
                        />
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
              {t("sidebar.batchOperations")}
            </div>
          )}
        </SidebarHeader>

        <SidebarContent
          onScroll={handleContentScroll}
          className={cn(
            "border-t flex flex-col overflow-y-auto gap-0 transition-colors",
            isContentScrolled ? "border-border" : "border-transparent",
          )}
        >
          {/* Projects (top) */}
          <div className="flex flex-col">
            <Collapsible
              defaultOpen
              className="group/collapsible-projects flex flex-col"
            >
              <SidebarGroup className="p-0 flex flex-col group-data-[collapsible=icon]:hidden">
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
                    className="relative z-10 size-5 flex items-center justify-center text-muted-foreground hover:bg-sidebar-accent mr-1"
                    title={t("sidebar.newProject")}
                  >
                    <Plus className="size-4" />
                  </Button>
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
                          isSelectionMode={isSelectionMode}
                          selectedTaskIds={selectedTaskIds}
                          selectedProjectIds={selectedProjectIds}
                          onToggleTaskSelection={handleToggleTaskSelection}
                          onEnableSelectionMode={handleEnableTaskSelectionMode}
                          onToggleProjectSelection={
                            handleToggleProjectSelection
                          }
                          onEnableProjectSelectionMode={
                            handleEnableProjectSelectionMode
                          }
                          onTaskNavigate={closeMobileSidebar}
                        />
                      ))}
                    </SidebarMenu>
                  </SidebarGroupContent>
                </CollapsibleContent>
              </SidebarGroup>
            </Collapsible>
          </div>

          <div className="flex flex-col">
            {/* All tasks (unassigned) (bottom) */}
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
              onTaskNavigate={closeMobileSidebar}
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
                title={t("common.cancel")}
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
                title={t("common.delete")}
              >
                <Trash2 className="size-4" />
              </Button>
            </div>
          ) : isMobile ? (
            <button
              type="button"
              onClick={() => {
                onOpenSettings?.();
                closeMobileSidebar();
              }}
              className="flex w-full items-center justify-between gap-3 rounded-2xl border border-sidebar-border/60 bg-sidebar-accent/30 px-3 py-2 text-left text-sidebar-foreground transition hover:bg-sidebar-accent/50"
            >
              <div className="flex items-center gap-3">
                <Avatar className="size-10 border border-sidebar-border/60">
                  {profile?.avatar ? (
                    <AvatarImage src={profile.avatar} alt={mobileUserName} />
                  ) : null}
                  <AvatarFallback className="bg-sidebar text-sidebar-foreground/80">
                    {mobileAvatarInitial}
                  </AvatarFallback>
                </Avatar>
                <div className="flex flex-col text-left">
                  <span className="text-sm font-semibold leading-tight truncate max-w-[120px]">
                    {mobileUserName}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {t("sidebar.settings")}
                  </span>
                </div>
              </div>
              <span className="inline-flex size-8 items-center justify-center rounded-full bg-sidebar-accent/40">
                <Settings2 className="size-4" />
              </span>
            </button>
          ) : (
            /* Footer toolbar (normal mode) */
            <div className="flex w-full items-center justify-between px-1 group-data-[collapsible=icon]:px-0">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => onOpenSettings?.()}
                className="size-8 text-muted-foreground hover:bg-sidebar-accent"
                title={t("sidebar.settings")}
              >
                <SlidersHorizontal className="size-4" />
              </Button>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-8 text-muted-foreground hover:bg-sidebar-accent"
                    title={t("settings.dialogTitle")}
                  >
                    <Settings2 className="size-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" side="top" className="w-48">
                  <DropdownMenuSub>
                    <DropdownMenuSubTrigger>
                      <Bot className="size-4" />
                      <span>{t("settings.backend")}</span>
                    </DropdownMenuSubTrigger>
                    <DropdownMenuSubContent>
                      <DropdownMenuRadioGroup
                        value={backend}
                        onValueChange={handleBackendSelect}
                      >
                        <DropdownMenuRadioItem value="claude-code">
                          {t("settings.claudeCode")}
                        </DropdownMenuRadioItem>
                      </DropdownMenuRadioGroup>
                    </DropdownMenuSubContent>
                  </DropdownMenuSub>

                  <DropdownMenuSub>
                    <DropdownMenuSubTrigger>
                      {theme === "dark" ? (
                        <Moon className="size-4" />
                      ) : (
                        <Sun className="size-4" />
                      )}
                      <span>{t("settings.theme")}</span>
                    </DropdownMenuSubTrigger>
                    <DropdownMenuSubContent>
                      <DropdownMenuRadioGroup
                        value={theme === "dark" ? "dark" : "light"}
                        onValueChange={handleThemeSelect}
                      >
                        <DropdownMenuRadioItem value="light">
                          {t("settings.lightMode")}
                        </DropdownMenuRadioItem>
                        <DropdownMenuRadioItem value="dark">
                          {t("settings.darkMode")}
                        </DropdownMenuRadioItem>
                      </DropdownMenuRadioGroup>
                    </DropdownMenuSubContent>
                  </DropdownMenuSub>

                  <DropdownMenuSub>
                    <DropdownMenuSubTrigger>
                      <Languages className="size-4" />
                      <span>{t("settings.language")}</span>
                    </DropdownMenuSubTrigger>
                    <DropdownMenuSubContent>
                      <DropdownMenuRadioGroup
                        value={currentLanguage}
                        onValueChange={changeLanguage}
                      >
                        <DropdownMenuRadioItem value="en">
                          {t("settings.english")}
                        </DropdownMenuRadioItem>
                        <DropdownMenuRadioItem value="zh">
                          {t("settings.simplifiedChinese")}
                        </DropdownMenuRadioItem>
                        <DropdownMenuRadioItem value="fr">
                          {t("settings.french")}
                        </DropdownMenuRadioItem>
                        <DropdownMenuRadioItem value="ja">
                          {t("settings.japanese")}
                        </DropdownMenuRadioItem>
                        <DropdownMenuRadioItem value="de">
                          {t("settings.german")}
                        </DropdownMenuRadioItem>
                        <DropdownMenuRadioItem value="ru">
                          {t("settings.russian")}
                        </DropdownMenuRadioItem>
                      </DropdownMenuRadioGroup>
                    </DropdownMenuSubContent>
                  </DropdownMenuSub>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          )}
        </SidebarFooter>

        <SidebarRail />
      </Sidebar>
    </DndContext>
  );
}
