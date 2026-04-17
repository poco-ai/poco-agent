"use client";

import { Badge } from "@/components/ui/badge";
import { formatIssueStatus } from "@/features/issues/lib/issue-presentation";
import type { WorkspaceIssue, WorkspaceIssueStatus } from "@/features/issues/model/types";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

import { TeamIssueCard } from "./team-issue-card";

interface TeamKanbanColumnProps {
  status: WorkspaceIssueStatus;
  issues: WorkspaceIssue[];
  onOpenIssue: (issueId: string) => void;
  className?: string;
}

export function TeamKanbanColumn({
  status,
  issues,
  onOpenIssue,
  className,
}: TeamKanbanColumnProps) {
  const { t } = useT("translation");

  return (
    <section
      className={cn(
        "flex min-h-[28rem] w-full flex-col gap-4 rounded-[28px] border border-border/70 bg-muted/10 p-4",
        className,
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="space-y-1">
          <p className="text-sm font-semibold text-foreground">
            {formatIssueStatus(t, status)}
          </p>
          <p className="text-xs text-muted-foreground">
            {t("issues.columns.count", { count: issues.length })}
          </p>
        </div>
        <Badge variant="secondary">{issues.length}</Badge>
      </div>

      {issues.length === 0 ? (
        <div className="flex min-h-[16rem] flex-1 items-center justify-center rounded-3xl border border-dashed border-border/70 bg-background/70 px-5 text-center">
          <div className="space-y-2">
            <p className="text-sm font-medium text-foreground">
              {t("issues.columns.emptyTitle")}
            </p>
            <p className="text-sm text-muted-foreground">
              {t("issues.columns.emptyDescription")}
            </p>
          </div>
        </div>
      ) : (
        <div className="flex flex-1 flex-col gap-3">
          {issues.map((issue) => (
            <TeamIssueCard
              key={issue.issue_id}
              issue={issue}
              onOpen={onOpenIssue}
            />
          ))}
        </div>
      )}
    </section>
  );
}
