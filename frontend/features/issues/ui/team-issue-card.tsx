"use client";

import { Check, Clock3, MoreHorizontal, RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import { PresetGlyph } from "@/features/capabilities/presets/components/preset-glyph";
import type { WorkspaceIssue } from "@/features/issues/model/types";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

function formatRelativeTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

interface TeamIssueCardProps {
  issue: WorkspaceIssue;
  preset: Preset | null;
  onOpen: (issueId: string) => void;
  onToggleStatus: (issueId: string) => void;
  isStatusPending?: boolean;
  surface?: "card" | "plain";
}

export function TeamIssueCard({
  issue,
  preset,
  onOpen,
  onToggleStatus,
  isStatusPending = false,
  surface = "card",
}: TeamIssueCardProps) {
  const { t } = useT("translation");
  const isCompleted = issue.status === "done" || issue.status === "canceled";

  return (
    <article
      className={cn(
        "group flex items-center gap-3 transition hover:bg-muted/20",
        surface === "card" &&
          "rounded-xl border border-border/70 bg-card px-5 py-3 hover:border-border",
        surface === "plain" && "bg-transparent px-5 py-3",
        isCompleted && "opacity-60",
      )}
    >
      <button
        type="button"
        onClick={() => onOpen(issue.issue_id)}
        className="min-w-0 flex-1 text-left"
      >
        <p
          className={cn(
            "truncate text-sm font-medium",
            isCompleted
              ? "text-muted-foreground line-through"
              : "text-foreground",
          )}
        >
          {issue.title}
        </p>
        {issue.description ? (
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {issue.description}
          </p>
        ) : null}
        <div className="mt-1 flex flex-wrap items-center gap-1.5">
          {issue.status === "in_progress" && !isCompleted ? (
            <span className="inline-flex items-center gap-1 rounded bg-primary/12 px-1.5 py-px text-[0.6875rem] font-medium text-primary">
              <span className="relative flex size-1.5">
                <span className="absolute inline-flex size-full animate-ping rounded-full bg-primary/60" />
                <span className="relative inline-flex size-1.5 rounded-full bg-primary" />
              </span>
              {t("issues.statuses.in_progress")}
            </span>
          ) : null}
        </div>
      </button>

      <div className="flex shrink-0 items-center gap-2.5">
        {preset ? (
          <PresetGlyph
            preset={preset}
            variant="status"
          />
        ) : null}
        <span className="flex items-center gap-1 text-xs text-muted-foreground">
          <Clock3 className="size-3" />
          {formatRelativeTime(issue.created_at)}
        </span>
        <div className="flex items-center gap-0.5 opacity-100 transition sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-7"
            onClick={() => onOpen(issue.issue_id)}
          >
            <MoreHorizontal className="size-3.5" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-7"
            onClick={() => onToggleStatus(issue.issue_id)}
            disabled={isStatusPending}
            aria-label={
              isCompleted
                ? t("issues.actions.reopen")
                : t("issues.actions.markDone")
            }
          >
            {isCompleted ? (
              <RotateCcw className="size-3.5" />
            ) : (
              <Check className="size-3.5" />
            )}
          </Button>
        </div>
      </div>
    </article>
  );
}
