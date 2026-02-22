"use client";

import * as React from "react";

import { ModeToggle } from "@/features/home/components/mode-toggle";
import { TaskComposer } from "@/features/home/components/task-composer";
import { ConnectorsBar } from "@/features/home/components/connectors-bar";
import { KeyboardHints } from "@/features/home/components/keyboard-hints";
import type { ComposerMode } from "@/features/home/components/task-composer";
import { cn } from "@/lib/utils";

interface TaskEntrySectionProps {
  title: React.ReactNode;
  mode: ComposerMode;
  onModeChange: (mode: ComposerMode) => void;
  toggleDisabled?: boolean;
  connectorsExpanded?: boolean;
  composerProps: Omit<React.ComponentProps<typeof TaskComposer>, "mode">;
  className?: string;
}

export function TaskEntrySection({
  title,
  mode,
  onModeChange,
  toggleDisabled = false,
  connectorsExpanded = false,
  composerProps,
  className,
}: TaskEntrySectionProps) {
  return (
    <div
      className={cn(
        "flex flex-1 flex-col items-center justify-start px-6 pt-[20vh] min-h-0 overflow-auto",
        className,
      )}
    >
      <div className="w-full max-w-2xl">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-medium tracking-tight text-foreground">
            {title}
          </h1>
        </div>

        <div className="mb-5" data-onboarding="home-mode-toggle">
          <ModeToggle
            mode={mode}
            onModeChange={onModeChange}
            disabled={toggleDisabled}
            className="w-full"
          />
        </div>

        <TaskComposer {...composerProps} mode={mode} />

        <ConnectorsBar forceExpanded={connectorsExpanded} />

        {composerProps.value.length === 0 ? (
          <KeyboardHints className="mt-4" />
        ) : null}
      </div>
    </div>
  );
}
