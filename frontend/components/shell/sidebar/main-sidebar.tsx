"use client";

import * as React from "react";
import {
  DndContext,
  type DragEndEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  pointerWithin,
  rectIntersection,
  type CollisionDetection,
} from "@dnd-kit/core";

import { Sidebar, SidebarRail } from "@/components/ui/sidebar";

import type { ProjectItem, TaskHistoryItem } from "@/features/projects/types";
import type { SettingsTabId } from "@/features/settings/types";

import { SidebarHeaderSection } from "./sidebar-header";
import { SidebarContentSection } from "./sidebar-content";
import { SidebarFooterSection } from "./sidebar-footer";
import { useSidebarSelection } from "./hooks/use-sidebar-selection";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface MainSidebarProps {
  projects: ProjectItem[];
  taskHistory: TaskHistoryItem[];
  onNewTask: () => void;
  onDeleteTask: (taskId: string) => Promise<void> | void;
  onRenameTask?: (taskId: string, newName: string) => Promise<void> | void;
  onMoveTaskToProject?: (taskId: string, projectId: string | null) => void;
  onRenameProject?: (projectId: string, newName: string) => void;
  onDeleteProject?: (projectId: string) => Promise<void> | void;
  onOpenSettings?: (tab?: SettingsTabId) => void;
  onStartOnboarding?: () => void;
  onOpenCreateProjectDialog?: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Main application sidebar.
 *
 * This component is a **thin orchestrator** that composes three sections
 * (header, content, footer) and provides the DnD context for task
 * reordering across projects.
 *
 * All visual and behavioural logic lives in the child components:
 * - `SidebarHeaderSection` – logo, new-task button, navigation items
 * - `SidebarContentSection` – project list, task history with DnD
 * - `SidebarFooterSection` – settings, theme, language, batch operations
 */
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
  onStartOnboarding,
  onOpenCreateProjectDialog,
}: MainSidebarProps) {
  // ---- Selection state ----
  const selection = useSidebarSelection({
    onDeleteTask,
    onDeleteProject,
  });

  // ---- DnD ----
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    }),
  );

  const collisionDetection = React.useCallback<CollisionDetection>((args) => {
    if (args.active?.data.current?.type === "task") {
      const pointerCollisions = pointerWithin(args);
      if (pointerCollisions.length > 0) return pointerCollisions;
      return rectIntersection(args);
    }
    return closestCorners(args);
  }, []);

  const handleDragEnd = React.useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || active.id === over.id) return;

      const activeData = active.data.current;
      const overData = over.data.current;

      if (activeData?.type !== "task") return;

      const taskId = activeData.taskId as string;
      let targetProjectId: string | null | undefined;

      if (overData?.type === "project") {
        targetProjectId = overData.projectId as string;
      } else if (overData?.type === "all-tasks") {
        targetProjectId = null;
      }

      if (targetProjectId !== undefined) {
        onMoveTaskToProject?.(taskId, targetProjectId);
      }
    },
    [onMoveTaskToProject],
  );

  // ---- Render ----
  return (
    <DndContext
      sensors={sensors}
      collisionDetection={collisionDetection}
      onDragEnd={handleDragEnd}
    >
      <Sidebar
        collapsible="icon"
        className="border-r-0 bg-sidebar overflow-hidden"
      >
        <SidebarHeaderSection onNewTask={onNewTask} />

        <SidebarContentSection
          projects={projects}
          taskHistory={taskHistory}
          onDeleteTask={onDeleteTask}
          onRenameTask={onRenameTask}
          onMoveTaskToProject={onMoveTaskToProject}
          onRenameProject={onRenameProject}
          onDeleteProject={onDeleteProject}
          onOpenCreateProjectDialog={onOpenCreateProjectDialog}
          isTaskSelectionMode={selection.isTaskSelectionMode}
          isProjectSelectionMode={selection.isProjectSelectionMode}
          selectedTaskIds={selection.selectedTaskIds}
          selectedProjectIds={selection.selectedProjectIds}
          onEnterTaskSelectionMode={selection.enterTaskSelectionMode}
          onEnterProjectSelectionMode={selection.enterProjectSelectionMode}
          onCancelSelection={selection.cancelSelectionMode}
          onToggleTaskSelection={selection.toggleTaskSelection}
          onToggleProjectSelection={selection.toggleProjectSelection}
        />

        <SidebarFooterSection
          isSelectionMode={selection.isSelectionMode}
          selectedCount={selection.selectedCount}
          onCancelSelection={selection.cancelSelectionMode}
          onDeleteSelected={selection.deleteSelectedItems}
          onOpenSettings={onOpenSettings ?? (() => {})}
          onStartOnboarding={onStartOnboarding}
        />

        <SidebarRail />
      </Sidebar>
    </DndContext>
  );
}
