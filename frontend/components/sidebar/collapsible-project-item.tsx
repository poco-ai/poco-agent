"use client";

import * as React from "react";
import { ChevronDown, ChevronRight, Folder } from "lucide-react";
import { useDroppable } from "@dnd-kit/core";
import { cn } from "@/lib/utils";
import { SidebarMenuButton, SidebarMenuItem } from "@/components/ui/sidebar";
import type {
  ProjectItem,
  TaskHistoryItem,
} from "@/app/[lng]/home/model/types";
import { TaskHistoryList } from "./task-history-list";

interface CollapsibleProjectItemProps {
  project: ProjectItem;
  tasks: TaskHistoryItem[];
  isExpanded: boolean;
  onToggle: () => void;
  onProjectClick: () => void;
  onDeleteTask: (taskId: string) => void;
  onRenameTask?: (taskId: string, newName: string) => void;
  onMoveTaskToProject?: (taskId: string, projectId: string | null) => void;
  allProjects: ProjectItem[];
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
}: CollapsibleProjectItemProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: project.id,
    data: {
      type: "project",
      projectId: project.id,
    },
  });

  return (
    <SidebarMenuItem>
      <div ref={setNodeRef} className={cn("w-full", isOver && "bg-primary/10")}>
        {/* 项目标题行 */}
        <SidebarMenuButton
          className={cn(
            "h-8 justify-start gap-3 text-sm hover:bg-sidebar-accent",
            isOver && "bg-primary/20",
          )}
          tooltip={project.name}
        >
          {/* 折叠按钮 */}
          <span
            role="button"
            onClick={(e) => {
              e.stopPropagation();
              onToggle();
            }}
            className="size-4 shrink-0 flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          >
            {isExpanded ? (
              <ChevronDown className="size-3 transition-transform" />
            ) : (
              <ChevronRight className="size-3 transition-transform" />
            )}
          </span>

          {/* 项目图标和名称 */}
          <div
            className="flex flex-1 items-center gap-3 min-w-0"
            onClick={onProjectClick}
          >
            <Folder
              className={cn(
                "size-4 text-muted-foreground group-data-[collapsible=icon]:hidden",
                isOver && "text-primary",
              )}
            />
            <span className={cn("flex-1 truncate", isOver && "text-primary")}>
              {project.name}
            </span>
            <span className="text-xs text-muted-foreground">
              {tasks.length}
            </span>
          </div>

          {isOver && (
            <span className="ml-auto text-xs text-primary shrink-0">
              移动到这里
            </span>
          )}
        </SidebarMenuButton>

        {/* 任务列表（可折叠） */}
        {isExpanded && (
          <div className="ml-4 mt-0.5">
            <TaskHistoryList
              tasks={tasks}
              onDeleteTask={onDeleteTask}
              onRenameTask={onRenameTask}
              onMoveTaskToProject={onMoveTaskToProject}
              projects={allProjects}
            />
          </div>
        )}
      </div>
    </SidebarMenuItem>
  );
}
