"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { GlobalSearchDialog } from "@/components/search/global-search-dialog";
import { useSearchDialog } from "@/hooks/use-search-dialog";
import { CreateProjectDialog } from "@/components/project/create-project-dialog";
import { MainSidebar } from "./main-sidebar";
import type {
  ProjectItem,
  TaskHistoryItem,
} from "@/app/[lng]/home/model/types";

interface AppSidebarProps {
  projects: ProjectItem[];
  taskHistory: TaskHistoryItem[];
  onNewTask?: () => void;
  onDeleteTask?: (taskId: string) => void;
  onRenameTask?: (taskId: string, newName: string) => void;
  onMoveTaskToProject?: (taskId: string, projectId: string | null) => void;
  onCreateProject?: (name: string) => void;
  onOpenSettings?: () => void;
}

// 默认空函数
const noop = () => {};

/**
 * 统一的侧边栏组件，根据当前路由自动调整行为
 * 所有页面应使用此组件以保持侧边栏一致
 */
export function AppSidebar({
  projects,
  taskHistory,
  onNewTask,
  onDeleteTask,
  onRenameTask,
  onMoveTaskToProject,
  onCreateProject,
  onOpenSettings,
}: AppSidebarProps) {
  const router = useRouter();
  const { isSearchOpen, setIsSearchOpen } = useSearchDialog();
  const [isCreateProjectDialogOpen, setIsCreateProjectDialogOpen] =
    React.useState(false);

  // 处理新建任务
  const handleNewTask = React.useCallback(() => {
    // 在首页或其他页面，执行默认行为
    if (onNewTask) {
      onNewTask();
    } else {
      router.push("/");
    }
  }, [router, onNewTask]);

  // 处理创建项目
  const handleCreateProject = React.useCallback(
    (name: string) => {
      onCreateProject?.(name);
    },
    [onCreateProject],
  );

  return (
    <>
      <MainSidebar
        projects={projects}
        taskHistory={taskHistory}
        onNewTask={handleNewTask}
        onDeleteTask={onDeleteTask ?? noop}
        onRenameTask={onRenameTask}
        onMoveTaskToProject={onMoveTaskToProject}
        onCreateProject={handleCreateProject}
        onOpenSettings={onOpenSettings}
      />

      {/* Global Search Dialog */}
      <GlobalSearchDialog open={isSearchOpen} onOpenChange={setIsSearchOpen} />

      {/* Create Project Dialog */}
      <CreateProjectDialog
        open={isCreateProjectDialogOpen}
        onOpenChange={setIsCreateProjectDialogOpen}
        onCreateProject={handleCreateProject}
      />
    </>
  );
}
