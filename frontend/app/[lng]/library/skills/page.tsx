"use client";

import * as React from "react";

import { useT } from "@/app/i18n/client";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/sidebar/app-sidebar";

import { SkillsHeader } from "./components/skills-header";
import { SkillsGrid } from "./components/skills-grid";

import {
  createMockProjects,
  createMockTaskHistory,
} from "@/app/[lng]/home/model/mocks";
import type {
  ProjectItem,
  TaskHistoryItem,
} from "@/app/[lng]/home/model/types";

export default function SkillsPage() {
  const { t } = useT("translation");

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
          onNewTask={() => {}}
          onDeleteTask={() => {}}
        />

        <SidebarInset className="flex flex-col bg-muted/30">
          <SkillsHeader />

          <div className="flex flex-1 flex-col px-6 py-10">
            <div className="w-full max-w-6xl mx-auto">
              <SkillsGrid />
            </div>
          </div>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
}
