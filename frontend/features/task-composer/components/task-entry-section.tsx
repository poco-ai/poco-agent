"use client";

import * as React from "react";

import { TaskComposer } from "@/features/task-composer/components/task-composer";
import { KeyboardHints } from "@/features/task-composer/components/keyboard-hints";
import type { ComposerMode } from "@/features/task-composer/types";
import { cn } from "@/lib/utils";

interface TaskEntrySectionProps {
  title: React.ReactNode;
  mode: ComposerMode;
  onModeChange: (mode: ComposerMode) => void;
  footer?: React.ReactNode;
  afterHints?: React.ReactNode;
  bottomPanel?: React.ReactNode;
  composerProps: Omit<
    React.ComponentProps<typeof TaskComposer>,
    "mode" | "onModeChange"
  >;
  className?: string;
}

export function TaskEntrySection({
  title,
  mode,
  onModeChange,
  footer,
  afterHints,
  bottomPanel,
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

        <TaskComposer
          {...composerProps}
          mode={mode}
          onModeChange={onModeChange}
          bottomAddon={footer}
        />

        {composerProps.value.length === 0 ? (
          <KeyboardHints className="mt-4" />
        ) : null}

        {afterHints}
      </div>

      {bottomPanel ? (
        <div className="mt-auto w-full max-w-2xl pt-8 pb-6">{bottomPanel}</div>
      ) : null}
    </div>
  );
}
