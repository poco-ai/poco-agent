"use client";

import * as React from "react";

import { ConnectorsBar } from "@/features/connectors";
import {
  TaskEntrySection,
  type ComposerMode,
  type LocalFilesystemDraft,
  type TaskSendOptions,
} from "@/features/task-composer";

interface ProjectDetailPanelProps {
  projectTitle: string;
  mode: ComposerMode;
  onModeChange: (mode: ComposerMode) => void;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  inputValue: string;
  onInputChange: (value: string) => void;
  onSendTask: (options?: TaskSendOptions) => Promise<void>;
  isSubmitting: boolean;
  initialPresetId: number | null;
  initialLocalFilesystemDraft?: LocalFilesystemDraft;
  onLocalFilesystemDraftSave?: (value: LocalFilesystemDraft) => Promise<void>;
  onRepoDefaultsSave: (payload: {
    repo_url?: string | null;
    git_branch?: string | null;
    git_token_env_key?: string | null;
  }) => Promise<void>;
}

export function ProjectDetailPanel({
  projectTitle,
  mode,
  onModeChange,
  textareaRef,
  inputValue,
  onInputChange,
  onSendTask,
  isSubmitting,
  initialPresetId,
  initialLocalFilesystemDraft,
  onLocalFilesystemDraftSave,
  onRepoDefaultsSave,
}: ProjectDetailPanelProps) {
  return (
    <TaskEntrySection
      title={projectTitle}
      mode={mode}
      onModeChange={onModeChange}
      footer={<ConnectorsBar />}
      composerProps={{
        textareaRef,
        value: inputValue,
        onChange: onInputChange,
        onSend: onSendTask,
        isSubmitting,
        allowProjectize: false,
        initialPresetId,
        initialLocalFilesystemDraft,
        onLocalFilesystemDraftSave,
        onRepoDefaultsSave,
      }}
    />
  );
}
