"use client";

import * as React from "react";
import { motion } from "motion/react";
import { SquareTerminal, ListTodo, Clock } from "lucide-react";

import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n/client";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

import type { ComposerMode } from "@/features/task-composer/types";
import { COMPOSER_MODE_SEQUENCE } from "@/features/task-composer/lib/mode-utils";

const MODE_ICONS: Record<
  ComposerMode,
  React.ComponentType<React.SVGProps<SVGSVGElement>>
> = {
  task: SquareTerminal,
  plan: ListTodo,
  scheduled: Clock,
};

interface ModeToggleProps {
  mode: ComposerMode;
  onModeChange: (mode: ComposerMode) => void;
  disabled?: boolean;
  className?: string;
  showLabels?: boolean;
}

/**
 * Unified mode toggle with animated background highlight.
 * Used on both mobile (above composer) and desktop (inside composer) so that
 * the visual interaction remains consistent across breakpoints.
 */
export function ModeToggle({
  mode,
  onModeChange,
  disabled = false,
  className,
  showLabels = true,
}: ModeToggleProps) {
  const { t } = useT("translation");
  const highlightId = React.useId();

  return (
    <div
      className={cn(
        "relative inline-flex items-center gap-1 rounded-full border border-border bg-muted/40 p-1 text-sm shadow-inner ring-1 ring-black/5 dark:ring-white/5",
        className,
      )}
    >
      {COMPOSER_MODE_SEQUENCE.map((value) => {
        const Icon = MODE_ICONS[value];
        const isActive = value === mode;
        const label = t(`hero.modeLabels.${value}`);
        const help = t(`hero.modes.${value}Help`);

        const button = (
          <button
            key={value}
            type="button"
            aria-pressed={isActive}
            aria-label={label}
            disabled={disabled}
            onClick={() => onModeChange(value)}
            className={cn(
              "relative flex flex-1 items-center justify-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              showLabels ? "gap-2 px-3 py-2 text-sm font-medium" : "px-2 py-2",
              disabled && "cursor-not-allowed opacity-50",
              isActive ? "text-primary-foreground" : "text-muted-foreground",
            )}
          >
            {isActive ? (
              <motion.div
                layoutId={`mode-toggle-highlight-${highlightId}`}
                className="absolute inset-0 rounded-full bg-primary shadow-sm"
                transition={{ type: "spring", stiffness: 440, damping: 40 }}
              />
            ) : null}
            <Icon
              className={cn(
                "relative z-10 size-4 transition-none",
                isActive ? "text-primary-foreground" : "text-muted-foreground",
              )}
            />
            {showLabels ? (
              <span className="relative z-10 whitespace-nowrap">{label}</span>
            ) : null}
          </button>
        );

        return showLabels ? (
          button
        ) : (
          <Tooltip key={value}>
            <TooltipTrigger asChild>{button}</TooltipTrigger>
            <TooltipContent side="top" sideOffset={8}>
              <div className="font-medium">{label}</div>
              <div className="text-xs text-muted-foreground max-w-[220px]">
                {help}
              </div>
            </TooltipContent>
          </Tooltip>
        );
      })}
    </div>
  );
}
