"use client";

import * as React from "react";

import type { ProjectPreset } from "@/features/capabilities/presets";
import { ConnectorsBar } from "@/features/connectors";
import { ProjectInfoSection } from "@/features/projects/components/project-info-section";
import { ProjectSessionList } from "@/features/projects/components/project-session-list";
import type { ProjectItem, TaskHistoryItem } from "@/features/projects/types";
import {
  TaskEntrySection,
  type ComposerMode,
  type TaskSendOptions,
} from "@/features/task-composer";

interface ProjectDetailPanelProps {
  project: ProjectItem;
  projectTitle: string;
  projectTasks: TaskHistoryItem[];
  projectPresets: ProjectPreset[];
  mode: ComposerMode;
  onModeChange: (mode: ComposerMode) => void;
  onUpdateProject: (updates: Partial<ProjectItem>) => Promise<void>;
  onOpenSettings: () => void;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  inputValue: string;
  onInputChange: (value: string) => void;
  onSendTask: (options?: TaskSendOptions) => Promise<void>;
  isSubmitting: boolean;
  initialPresetId: number | null;
  onRepoDefaultsSave: (payload: {
    repo_url?: string | null;
    git_branch?: string | null;
    git_token_env_key?: string | null;
  }) => Promise<void>;
}

export function ProjectDetailPanel({
  project,
  projectTitle,
  projectTasks,
  projectPresets,
  mode,
  onModeChange,
  onUpdateProject,
  onOpenSettings,
  textareaRef,
  inputValue,
  onInputChange,
  onSendTask,
  isSubmitting,
  initialPresetId,
  onRepoDefaultsSave,
}: ProjectDetailPanelProps) {
  return (
    <>
      <div className="px-4 pt-6 sm:px-6">
        <div className="mx-auto w-full max-w-5xl">
          <ProjectInfoSection
            project={project}
            sessionCount={projectTasks.length}
            presetCount={projectPresets.length}
            onUpdateProject={onUpdateProject}
            onOpenSettings={onOpenSettings}
          />
        </div>
      </div>

      <TaskEntrySection
        title={projectTitle}
        mode={mode}
        onModeChange={onModeChange}
        footer={<ConnectorsBar />}
        className="px-4 pt-8 sm:px-6 md:pt-10"
        bottomPanel={<ProjectSessionList tasks={projectTasks} />}
        composerProps={{
          textareaRef,
          value: inputValue,
          onChange: onInputChange,
          onSend: onSendTask,
          isSubmitting,
          allowProjectize: false,
          initialPresetId,
          onRepoDefaultsSave,
        }}
      />
    </>
  );
}
