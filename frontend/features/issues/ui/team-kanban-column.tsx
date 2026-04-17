"use client";

import { useDroppable } from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

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

function SortableIssueCard({
  issue,
  onOpenIssue,
}: {
  issue: WorkspaceIssue;
  onOpenIssue: (issueId: string) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({
      id: issue.issue_id,
      data: {
        type: "issue",
        issueId: issue.issue_id,
        status: issue.status,
      },
    });

  return (
    <TeamIssueCard
      ref={setNodeRef}
      issue={issue}
      onOpen={onOpenIssue}
      isDragging={isDragging}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
      }}
      className="touch-none"
      dragHandleProps={{ ...attributes, ...listeners }}
    />
  );
}

export function TeamKanbanColumn({
  status,
  issues,
  onOpenIssue,
  className,
}: TeamKanbanColumnProps) {
  const { t } = useT("translation");
  const { setNodeRef, isOver } = useDroppable({
    id: `column:${status}`,
    data: {
      type: "column",
      status,
    },
  });
  const issueIds = issues.map((issue) => issue.issue_id);

  return (
    <section
      ref={setNodeRef}
      className={cn(
        "flex min-h-[28rem] w-full flex-col gap-4 rounded-[28px] border border-border/70 bg-muted/10 p-4 transition-colors",
        isOver && "border-primary/35 bg-primary/8 shadow-[inset_0_0_0_1px_color-mix(in_oklab,var(--primary)_32%,transparent)]",
        className,
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="space-y-1.5">
          <p className="text-sm font-semibold text-foreground">
            {formatIssueStatus(t, status)}
          </p>
          <p className="text-xs text-muted-foreground">
            {t("issues.columns.count", { count: issues.length })}
          </p>
        </div>
        <Badge variant="secondary">{issues.length}</Badge>
      </div>

      <SortableContext items={issueIds} strategy={verticalListSortingStrategy}>
        {issues.length === 0 ? (
          <div
            className={cn(
              "flex min-h-[16rem] flex-1 items-center justify-center rounded-3xl border border-dashed border-border/70 bg-background/70 px-5 text-center transition-colors",
              isOver && "border-primary/35 bg-primary/5",
            )}
          >
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
              <SortableIssueCard
                key={issue.issue_id}
                issue={issue}
                onOpenIssue={onOpenIssue}
              />
            ))}
          </div>
        )}
      </SortableContext>
    </section>
  );
}
