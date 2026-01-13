"use client";

import * as React from "react";
import { useT } from "@/app/i18n/client";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/sidebar/app-sidebar";
import { NotificationsHeader } from "./components/notifications-header";
import { ChangelogList } from "./components/changelog-list";
import {
  createMockProjects,
  createMockTaskHistory,
} from "@/app/[lng]/home/model/mocks";

// Types
import type {
  ProjectItem,
  TaskHistoryItem,
} from "@/app/[lng]/home/model/types";

export default function NotificationsPage() {
  const { t } = useT("translation");

  // Mock sidebar data
  const [projects] = React.useState<ProjectItem[]>(() => createMockProjects(t));
  const [taskHistory] = React.useState<TaskHistoryItem[]>(() =>
    createMockTaskHistory(t),
  );

  return (
    <SidebarProvider defaultOpen={true}>
      <div className="flex min-h-svh w-full overflow-hidden bg-background">
        <AppSidebar
          projects={projects}
          taskHistory={taskHistory}
          onNewTask={undefined}
          onDeleteTask={() => {}}
          onCreateProject={() => {}}
        />

        <SidebarInset className="flex flex-col bg-muted/30">
          <NotificationsHeader />
          <div className="flex flex-1 flex-col px-6 py-10 overflow-y-auto">
            <div className="w-full max-w-4xl mx-auto">
              <ChangelogList />
            </div>
          </div>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
}
