"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  Library,
  MessageSquare,
  MoreHorizontal,
  PanelLeftClose,
  PanelLeftOpen,
  PenSquare,
  Plus,
  Search,
  SlidersHorizontal,
} from "lucide-react";
import {
  DndContext,
  DragEndEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  useDroppable,
} from "@dnd-kit/core";

import { useT } from "@/app/i18n/client";
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

import type {
  ProjectItem,
  TaskHistoryItem,
} from "@/app/[lng]/home/model/types";
import { TaskHistoryList } from "./task-history-list";
import { CollapsibleProjectItem } from "./collapsible-project-item";
import { GlobalSearchDialog } from "@/components/search/global-search-dialog";
import { useSearchDialog } from "@/hooks/use-search-dialog";
import { CreateProjectDialog } from "@/components/project/create-project-dialog";

const TOP_NAV_ITEMS = [
  { id: "search", labelKey: "sidebar.search", icon: Search, href: null },
  {
    id: "library",
    labelKey: "sidebar.library",
    icon: Library,
    href: "/library",
  },
] as const;

function DroppableAllTasksGroup({
  title,
  tasks,
  onDeleteTask,
  onRenameTask,
  onMoveTaskToProject,
  projects,
}: {
  title: string;
  tasks: TaskHistoryItem[];
  onDeleteTask: (taskId: string) => void;
  onRenameTask?: (taskId: string, newName: string) => void;
  onMoveTaskToProject?: (taskId: string, projectId: string | null) => void;
  projects: ProjectItem[];
}) {
  const { setNodeRef, isOver } = useDroppable({
    id: "all-tasks",
    data: {
      type: "all-tasks",
    },
  });

  return (
    <SidebarGroup
      ref={setNodeRef}
      className={cn(
        "py-2 overflow-hidden group-data-[collapsible=icon]:hidden transition-colors rounded-lg",
        isOver && "bg-primary/10",
      )}
    >
      <SidebarGroupLabel className="text-xs font-medium text-muted-foreground group-data-[collapsible=icon]:hidden">
        {title}
      </SidebarGroupLabel>
      <SidebarGroupContent className="mt-1 group-data-[collapsible=icon]:mt-0">
        <TaskHistoryList
          tasks={tasks}
          onDeleteTask={onDeleteTask}
          onRenameTask={onRenameTask}
          onMoveTaskToProject={onMoveTaskToProject}
          projects={projects}
        />
        {isOver && (
          <div className="flex items-center justify-center p-2 text-xs text-primary bg-primary/5 rounded border border-dashed border-primary/20 mt-1">
            移出项目
          </div>
        )}
      </SidebarGroupContent>
    </SidebarGroup>
  );
}

export function MainSidebar({
  projects,
  taskHistory,
  onNewTask,
  onDeleteTask,
  onRenameTask,
  onMoveTaskToProject,
  onCreateProject,
  onOpenSettings,
}: {
  projects: ProjectItem[];
  taskHistory: TaskHistoryItem[];
  onNewTask: () => void;
  onDeleteTask: (taskId: string) => void;
  onRenameTask?: (taskId: string, newName: string) => void;
  onMoveTaskToProject?: (taskId: string, projectId: string | null) => void;
  onCreateProject?: (name: string) => void;
  onOpenSettings?: () => void;
}) {
  const { t } = useT("translation");
  const router = useRouter();
  const { toggleSidebar } = useSidebar();
  const { isSearchOpen, setIsSearchOpen, searchKey } = useSearchDialog();
  const [isCreateProjectDialogOpen, setIsCreateProjectDialogOpen] =
    React.useState(false);

  // 管理每个项目的折叠状态
  const [expandedProjects, setExpandedProjects] = React.useState<Set<string>>(
    new Set(),
  );

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

  const handleCreateProject = React.useCallback(
    (name: string) => {
      onCreateProject?.(name);
    },
    [onCreateProject],
  );

  const handleProjectClick = React.useCallback(
    (projectId: string) => {
      router.push(`/projects/${projectId}`);
    },
    [router],
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
                className="group/logo flex size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground transition-colors hover:bg-sidebar-primary/90"
                type="button"
              >
                <MessageSquare className="size-4 group-data-[collapsible=icon]:group-hover/logo:hidden" />
                <PanelLeftOpen className="hidden size-4 group-data-[collapsible=icon]:group-hover/logo:block" />
              </button>
              <span
                onClick={() => router.push("/")}
                className="text-sm font-semibold tracking-tight text-sidebar-foreground group-data-[collapsible=icon]:hidden cursor-pointer hover:opacity-80 transition-opacity"
              >
                OpenCoWork
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

          {TOP_NAV_ITEMS.map(({ id, labelKey, icon: Icon, href }) => (
            <SidebarMenu
              key={id}
              className="group-data-[collapsible=icon]:px-0"
            >
              <SidebarMenuItem>
                <SidebarMenuButton
                  onClick={() => {
                    if (id === "search") {
                      setIsSearchOpen(true);
                    } else if (href) {
                      router.push(href);
                    }
                  }}
                  className="h-[36px] min-w-0 max-w-[calc(var(--sidebar-width)-16px)] w-full justify-start gap-3 rounded-[10px] px-3 py-[7.5px] text-muted-foreground transition-colors hover:bg-sidebar-accent group-data-[collapsible=icon]:w-[var(--sidebar-width-icon)] group-data-[collapsible=icon]:max-w-[var(--sidebar-width-icon)] group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0"
                  tooltip={t(labelKey)}
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
          ))}
        </SidebarHeader>

        <SidebarContent className="overflow-hidden group-data-[collapsible=icon]:px-0">
          <ScrollArea className="h-full">
            {/* 所有任务（未归类） - 始终显示 */}
            <DroppableAllTasksGroup
              title={t("sidebar.allTasks")}
              tasks={unassignedTasks}
              onDeleteTask={onDeleteTask}
              onRenameTask={onRenameTask}
              onMoveTaskToProject={onMoveTaskToProject}
              projects={projects}
            />

            {/* 项目列表 */}
            <SidebarGroup className="py-2 overflow-hidden group-data-[collapsible=icon]:hidden">
              <div className="group/projects-header flex items-center justify-between pr-2">
                <SidebarGroupLabel className="text-xs font-medium text-muted-foreground group-data-[collapsible=icon]:hidden">
                  {t("sidebar.projects")}
                </SidebarGroupLabel>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setIsCreateProjectDialogOpen(true)}
                  className="size-5 text-muted-foreground hover:bg-sidebar-accent"
                  title={t("sidebar.newProject")}
                >
                  <Plus className="size-3" />
                </Button>
              </div>
              <SidebarGroupContent className="mt-1 group-data-[collapsible=icon]:mt-0">
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
                    />
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </ScrollArea>
        </SidebarContent>

        <SidebarFooter className="border-t border-sidebar-border p-2 group-data-[collapsible=icon]:p-2">
          {/* 底部工具栏 */}
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
        </SidebarFooter>

        <SidebarRail />

        {/* Global Search Dialog */}
        <GlobalSearchDialog
          open={isSearchOpen}
          onOpenChange={setIsSearchOpen}
        />

        {/* Create Project Dialog */}
        <CreateProjectDialog
          open={isCreateProjectDialogOpen}
          onOpenChange={setIsCreateProjectDialogOpen}
          onCreateProject={handleCreateProject}
        />
      </Sidebar>
    </DndContext>
  );
}
