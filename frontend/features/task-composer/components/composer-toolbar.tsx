"use client";

import * as React from "react";
import {
  Loader2,
  ArrowUp,
  Plus,
  Chrome,
  Clock,
  Paperclip,
  Code2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";
import type { ComposerMode } from "@/features/task-composer/types";

interface ComposerToolbarProps {
  mode: ComposerMode;
  isSubmitting?: boolean;
  isUploading: boolean;
  canSubmit: boolean;
  browserEnabled: boolean;
  onOpenRepoDialog: () => void;
  onToggleBrowser: () => void;
  onOpenFileInput: () => void;
  onSubmit: () => void;
  scheduledSummary?: string;
  onOpenScheduledSettings?: () => void;
}

/**
 * Bottom toolbar for the TaskComposer.
 *
 * Contains action buttons: repo, schedule, browser, file upload, and send.
 */
export function ComposerToolbar({
  mode,
  isSubmitting,
  isUploading,
  canSubmit,
  browserEnabled,
  onOpenRepoDialog,
  onToggleBrowser,
  onOpenFileInput,
  onSubmit,
  scheduledSummary,
  onOpenScheduledSettings,
}: ComposerToolbarProps) {
  const { t } = useT("translation");
  const disabled = isSubmitting || isUploading;
  const browserTooltipTitle = browserEnabled
    ? t("hero.browser.enabledTooltipTitle")
    : t("hero.browser.disabledTooltipTitle");
  const browserTooltipDescription = browserEnabled
    ? t("hero.browser.enabledTooltipDescription")
    : t("hero.browser.disabledTooltipDescription");
  const browserButtonClassName = cn(
    "size-9 rounded-xl transition-opacity hover:bg-accent",
    !browserEnabled && "text-muted-foreground/50",
  );

  return (
    <div className="flex w-full flex-wrap items-center justify-between gap-3">
      {/* Left: attach menu */}
      <div className="flex items-center gap-1">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              disabled={disabled}
              className="size-9 rounded-xl hover:bg-accent"
              aria-label={t("hero.attachFile")}
              title={t("hero.attachFile")}
            >
              {isUploading ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Plus className="size-4" />
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align="start"
            side="top"
            sideOffset={8}
            className="w-44"
          >
            <DropdownMenuItem onSelect={onOpenFileInput}>
              <Paperclip className="size-4" />
              <span>{t("hero.uploadFile")}</span>
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={onOpenRepoDialog}>
              <Code2 className="size-4" />
              <span>{t("hero.importCode")}</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Scheduled summary badge (scheduled mode only) */}
        {mode === "scheduled" &&
          scheduledSummary &&
          onOpenScheduledSettings && (
            <Badge
              variant="secondary"
              role="button"
              tabIndex={0}
              className="inline-flex h-9 w-fit items-center gap-2 rounded-xl cursor-pointer select-none px-3 py-0"
              onClick={onOpenScheduledSettings}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onOpenScheduledSettings();
                }
              }}
              aria-label={t("hero.modes.scheduled")}
              title={t("hero.modes.scheduled")}
            >
              <Clock className="size-3" />
              <span className="text-sm font-medium">{scheduledSummary}</span>
            </Badge>
          )}
      </div>

      {/* Right: browser, send */}
      <div className="flex items-center gap-1">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              disabled={disabled}
              className={browserButtonClassName}
              aria-label={browserTooltipTitle}
              title={browserTooltipTitle}
              onClick={onToggleBrowser}
            >
              <Chrome
                className={cn("size-4", !browserEnabled && "opacity-55")}
                strokeWidth={2}
              />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="top" sideOffset={8} className="max-w-56">
            <div className="space-y-1">
              <p className="text-xs font-medium">{browserTooltipTitle}</p>
              <p className="text-[11px] leading-relaxed text-background/80">
                {browserTooltipDescription}
              </p>
            </div>
          </TooltipContent>
        </Tooltip>

        <Button
          onClick={onSubmit}
          disabled={!canSubmit || disabled}
          size="icon"
          className="size-9 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground"
          title={t("hero.send")}
        >
          <ArrowUp className="size-4" />
        </Button>
      </div>
    </div>
  );
}
