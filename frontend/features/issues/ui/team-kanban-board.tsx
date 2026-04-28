"use client";

import * as React from "react";
import { ChevronDown } from "lucide-react";

import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import { buildBoardLanes } from "@/features/issues/lib/issues-index-view";
import type { WorkspaceBoard, WorkspaceIssue } from "@/features/issues/model/types";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

import { TeamIssueCard } from "./team-issue-card";

export const LANE_COLORS = [
  "oklch(0.8348 0.1302 160.908)",
  "oklch(0.7686 0.1647 70.0804)",
  "oklch(0.6231 0.188 259.8145)",
  "oklch(0.6056 0.2189 292.7172)",
  "oklch(0.6959 0.1491 162.4796)",
  "oklch(0.5523 0.1927 32.7272)",
];

function resolvePreset(
  issue: WorkspaceIssue,
  presetMap: Map<number, Preset>,
): Preset | null {
  return issue.assignee_preset_id
    ? presetMap.get(issue.assignee_preset_id) ?? null
    : null;
}

export function hashCode(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash |= 0;
  }
  return hash;
}

interface TeamKanbanBoardProps {
  boards: WorkspaceBoard[];
  issues: WorkspaceIssue[];
  selectedBoardId: string | null;
  presetMap: Map<number, Preset>;
  onOpenIssue: (issueId: string) => void;
  onToggleIssueStatus: (issueId: string) => void;
  pendingIssueId?: string | null;
}

export function TeamKanbanBoard({
  boards,
  issues,
  selectedBoardId,
  presetMap,
  onOpenIssue,
  onToggleIssueStatus,
  pendingIssueId,
}: TeamKanbanBoardProps) {
  const { t } = useT("translation");
  const lanes = React.useMemo(() => buildBoardLanes(boards, issues), [boards, issues]);
  const lane = lanes.find((l) => l.board.board_id === selectedBoardId) ?? lanes[0];

  if (!lane) {
    return null;
  }

  return (
    <div className="overflow-hidden rounded-[28px] border border-border/70 bg-card shadow-sm">
      {lane.pendingSections.length === 0 && lane.completedIssues.length === 0 ? (
        <div className="flex min-h-48 items-center justify-center px-6 py-12 text-center">
          <div className="space-y-1.5">
            <p className="text-sm font-medium text-foreground">
              {t("issues.lane.emptyTitle")}
            </p>
            <p className="text-sm text-muted-foreground">
              {t("issues.lane.emptyDescription")}
            </p>
          </div>
        </div>
      ) : (
        <div className="divide-y divide-border/50">
          {lane.pendingSections.map((section) => (
            <div key={section.priority}>
              <div className="flex items-center gap-3 px-5 pt-4 pb-2">
                <span
                  className={
                    section.priority === "high"
                      ? "size-2 rounded-full bg-primary"
                      : section.priority === "low"
                        ? "size-2 rounded-full bg-muted-foreground/55"
                        : "size-2 rounded-full bg-foreground/70"
                  }
                />
                <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
                  {t(`issues.prioritySections.${section.priority}`)}
                </p>
                <span className="text-xs tabular-nums text-muted-foreground/60">
                  {section.issues.length}
                </span>
              </div>
              {section.issues.map((issue) => (
                <TeamIssueCard
                  key={issue.issue_id}
                  issue={issue}
                  preset={resolvePreset(issue, presetMap)}
                  onOpen={onOpenIssue}
                  onToggleStatus={onToggleIssueStatus}
                  isStatusPending={pendingIssueId === issue.issue_id}
                />
              ))}
            </div>
          ))}

          {lane.completedIssues.length > 0 ? (
            <CollapsibleCompletedSection
              issues={lane.completedIssues}
              presetMap={presetMap}
              onOpenIssue={onOpenIssue}
              onToggleStatus={onToggleIssueStatus}
              pendingIssueId={pendingIssueId}
            />
          ) : null}
        </div>
      )}
    </div>
  );
}

function CollapsibleCompletedSection({
  issues,
  presetMap,
  onOpenIssue,
  onToggleStatus,
  pendingIssueId,
}: {
  issues: WorkspaceIssue[];
  presetMap: Map<number, Preset>;
  onOpenIssue: (issueId: string) => void;
  onToggleStatus: (issueId: string) => void;
  pendingIssueId?: string | null;
}) {
  const { t } = useT("translation");
  const [expanded, setExpanded] = React.useState(false);

  return (
    <div className="border-t border-dashed border-border/50">
      <button
        type="button"
        className="flex w-full items-center justify-between px-5 py-2.5 text-sm text-muted-foreground transition hover:bg-muted/30"
        onClick={() => setExpanded((prev) => !prev)}
      >
        <span className="flex items-center gap-2">
          <span className="font-semibold tabular-nums">{issues.length}</span>
          {t("issues.lane.completedLabel")}
        </span>
        <span className="flex items-center gap-1 text-xs">
          {expanded
            ? t("issues.actions.hideCompleted")
            : t("issues.actions.showCompleted")}
          <ChevronDown
            className={cn(
              "size-3.5 transition-transform",
              expanded && "rotate-180",
            )}
          />
        </span>
      </button>
      {expanded ? (
        issues.length === 0 ? (
          <p className="px-5 pb-3 text-sm text-muted-foreground">
            {t("issues.lane.emptyCompleted")}
          </p>
        ) : (
          issues.map((issue) => (
            <TeamIssueCard
              key={issue.issue_id}
              issue={issue}
              preset={resolvePreset(issue, presetMap)}
              onOpen={onOpenIssue}
              onToggleStatus={onToggleStatus}
              isStatusPending={pendingIssueId === issue.issue_id}
            />
          ))
        )
      ) : null}
    </div>
  );
}
