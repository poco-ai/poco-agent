"use client";

import * as React from "react";
import {
  Loader2,
  ArrowUp,
  Plus,
  Settings2,
  Clock,
  Chrome,
  Paperclip,
  Code2,
  SquareTerminal,
  ListTodo,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useT } from "@/lib/i18n/client";
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

interface ComposerToolbarProps {
  mode: ComposerMode;
  onModeChange: (mode: ComposerMode) => void;
  isSubmitting?: boolean;
  isUploading: boolean;
  canSubmit: boolean;
  browserEnabled: boolean;
  onOpenRepoDialog: () => void;
  onBrowserEnabledChange: (enabled: boolean) => void;
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
  onModeChange,
  isSubmitting,
  isUploading,
  canSubmit,
  browserEnabled,
  onOpenRepoDialog,
  onBrowserEnabledChange,
  onOpenFileInput,
  onSubmit,
  scheduledSummary,
  onOpenScheduledSettings,
}: ComposerToolbarProps) {
  const { t } = useT("translation");
  const disabled = isSubmitting || isUploading;

  return (
    <div className="flex w-full flex-wrap items-center justify-between gap-3">
      {/* Left: attach menu */}
      <div className="flex items-center gap-1">
        <Tooltip>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  disabled={disabled}
                  className="size-9 rounded-xl hover:bg-accent"
                  aria-label={t("hero.uploadFile")}
                >
                  {isUploading ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <Plus className="size-4" />
                  )}
                </Button>
              </TooltipTrigger>
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
          <TooltipContent side="top" sideOffset={8}>
            {t("hero.uploadFile")}
          </TooltipContent>
        </Tooltip>

        {/* Configure menu: mode + browser */}
        <Tooltip>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  disabled={disabled}
                  className="size-9 rounded-xl border border-transparent text-muted-foreground hover:bg-accent hover:text-foreground data-[state=open]:border-border data-[state=open]:bg-accent/60 data-[state=open]:text-foreground"
                  aria-label={t("hero.configure")}
                  data-onboarding="home-mode-toggle"
                >
                  <Settings2 className="size-4" />
                </Button>
              </TooltipTrigger>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="start"
              side="top"
              sideOffset={8}
              className="w-52"
            >
              <DropdownMenuRadioGroup
                value={mode}
                onValueChange={(next) => onModeChange(next as ComposerMode)}
              >
                {COMPOSER_MODE_SEQUENCE.map((value) => {
                  const Icon = MODE_ICONS[value];
                  return (
                    <DropdownMenuRadioItem key={value} value={value}>
                      <Icon className="size-4" />
                      <span>{t(`hero.modeLabels.${value}`)}</span>
                    </DropdownMenuRadioItem>
                  );
                })}
              </DropdownMenuRadioGroup>
              <DropdownMenuSeparator />
              <DropdownMenuCheckboxItem
                checked={browserEnabled}
                onCheckedChange={(next) => {
                  onBrowserEnabledChange(Boolean(next));
                }}
              >
                <Chrome className="size-4" />
                <span>{t("hero.browser.toggle")}</span>
              </DropdownMenuCheckboxItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <TooltipContent side="top" sideOffset={8}>
            {t("hero.configure")}
          </TooltipContent>
        </Tooltip>

        {/* Plan mode indicator */}
        {mode === "plan" ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <Badge
                variant="secondary"
                role="button"
                tabIndex={0}
                className="inline-flex size-9 cursor-pointer items-center justify-center rounded-xl select-none border border-primary/25 bg-primary/10 p-0 text-primary hover:bg-primary/15"
                aria-label={t("hero.modeLabels.plan")}
                onClick={() => {
                  if (disabled) return;
                  onModeChange("task");
                }}
                onKeyDown={(e) => {
                  if (e.key !== "Enter" && e.key !== " ") return;
                  e.preventDefault();
                  if (disabled) return;
                  onModeChange("task");
                }}
              >
                <ListTodo className="size-4" />
              </Badge>
            </TooltipTrigger>
            <TooltipContent side="top" sideOffset={8}>
              {t("hero.modes.planHelp")}
            </TooltipContent>
          </Tooltip>
        ) : null}

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

      {/* Right: send */}
      <div className="flex items-center gap-1">
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
