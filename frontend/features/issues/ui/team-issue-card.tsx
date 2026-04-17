"use client";

import * as React from "react";
import { Bot } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { formatAssignmentStatus, formatIssuePriority } from "@/features/issues/lib/issue-presentation";
import type { WorkspaceIssue } from "@/features/issues/model/types";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

interface TeamIssueCardProps {
  issue: WorkspaceIssue;
  onOpen: (issueId: string) => void;
  className?: string;
  style?: React.CSSProperties;
  disabled?: boolean;
  isDragging?: boolean;
  dragHandleProps?: React.HTMLAttributes<HTMLButtonElement>;
}

export const TeamIssueCard = React.forwardRef<HTMLButtonElement, TeamIssueCardProps>(
  function TeamIssueCard(
    {
      issue,
      onOpen,
      className,
      style,
      disabled,
      isDragging,
      dragHandleProps,
    },
    ref,
  ) {
    const { t } = useT("translation");

    return (
      <button
        ref={ref}
        type="button"
        onClick={() => onOpen(issue.issue_id)}
        className={cn(
          "group flex w-full flex-col gap-4 rounded-3xl border border-border/70 bg-background/95 px-4 py-4 text-left transition hover:border-foreground/15 hover:bg-muted/20",
          isDragging && "opacity-60 shadow-lg ring-2 ring-primary/15",
          disabled && "cursor-default",
          className,
        )}
        style={style}
        disabled={disabled}
        {...dragHandleProps}
      >
        <div className="space-y-2">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 space-y-1">
              <p className="line-clamp-2 text-sm font-semibold text-foreground">
                {issue.title}
              </p>
              <p className="line-clamp-2 text-sm text-muted-foreground">
                {issue.description || t("issues.emptyDescription")}
              </p>
            </div>
            {issue.agent_assignment ? (
              <span className="inline-flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                <Bot className="size-4" />
              </span>
            ) : null}
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">
              {formatIssuePriority(t, issue.priority)}
            </Badge>
            {issue.related_project_id ? (
              <Badge variant="secondary">
                {t("issues.fields.project")}
              </Badge>
            ) : null}
            {issue.agent_assignment ? (
              <Badge variant="secondary">
                {formatAssignmentStatus(t, issue.agent_assignment.status)}
              </Badge>
            ) : null}
          </div>
        </div>
        <div className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
          <span>
            {t("issues.fields.updatedAt")} · {formatDateTime(issue.updated_at)}
          </span>
          <span>#{issue.position + 1}</span>
        </div>
      </button>
    );
  },
);
