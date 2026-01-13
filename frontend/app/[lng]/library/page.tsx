"use client";

import * as React from "react";

import { useT } from "@/app/i18n/client";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";

import { AppSidebar } from "@/components/sidebar/app-sidebar";
import { LibraryHeader } from "./components/library-header";
import { LibraryGrid } from "./components/library-grid";

import {
  createMockProjects,
  createMockTaskHistory,
} from "@/app/[lng]/home/model/mocks";
import type {
  ProjectItem,
  TaskHistoryItem,
} from "@/app/[lng]/home/model/types";

import { SettingsDialog } from "@/components/settings/settings-dialog";

export default function LibraryPage() {
  const { t } = useT("translation");

  const [isSettingsOpen, setIsSettingsOpen] = React.useState(false);
  const [projects, setProjects] = React.useState<ProjectItem[]>(() =>
    createMockProjects(t),
  );
  const [taskHistory] = React.useState<TaskHistoryItem[]>(() =>
    createMockTaskHistory(t),
  );

  return (
    <SidebarProvider defaultOpen={true}>
      <div className="flex min-h-svh w-full overflow-hidden bg-background">
        <AppSidebar
          projects={projects}
          taskHistory={taskHistory}
          // Passing undefined will trigger the default navigation in AppSidebar
          onNewTask={undefined}
          onDeleteTask={() => {}}
          onCreateProject={(name) => {
            // Mock create project for library page to show responsiveness
            setProjects((prev) => [
              ...prev,
              {
                id: `project-${Date.now()}`,
                name,
                taskCount: 0,
                icon: "📁",
              },
            ]);
          }}
          onOpenSettings={() => setIsSettingsOpen(true)}
        />

        <SidebarInset className="flex flex-col bg-muted/30">
          <LibraryHeader />

          <div className="flex flex-1 flex-col px-6 py-10">
            <div className="w-full max-w-6xl mx-auto">
              <LibraryGrid />
            </div>
          </div>
        </SidebarInset>

        <SettingsDialog
          open={isSettingsOpen}
          onOpenChange={setIsSettingsOpen}
        />
      </div>
    </SidebarProvider>
  );
}
