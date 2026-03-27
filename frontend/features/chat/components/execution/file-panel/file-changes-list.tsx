"use client";

import React from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useT } from "@/lib/i18n/client";
import { FileChangeCard } from "./file-change-card";
import type { DeliverableResponse, FileChange } from "@/features/chat/types";

interface FileChangesListProps {
  fileChanges?: FileChange[];
  sessionStatus?: "pending" | "running" | "completed" | "failed" | "canceled";
  deliverables?: DeliverableResponse[];
  selectedDeliverableId?: string | null;
  selectedDeliverableVersionId?: string | null;
  onSelectDeliverable?: (
    deliverableId: string,
    versionId: string | null,
  ) => void;
  onFileClick?: (filePath: string) => void;
}

interface Summary {
  added: number;
  modified: number;
  deleted: number;
  renamed: number;
}

interface ArtifactsSummaryBarProps {
  summary: Summary;
  t: (key: string) => string;
}

function ArtifactsSummaryBar({ summary, t }: ArtifactsSummaryBarProps) {
  return (
    <div
      className="
        flex items-center gap-3
        px-4 py-3
        bg-muted/30
        border-b border-border
        text-sm
        min-w-0 max-w-full
        overflow-hidden
        [container-type:inline-size]
      "
    >
      {/* 左侧总计 */}
      <div className="flex shrink-0 items-center gap-2">
        <span className="text-muted-foreground">
          {t("artifacts.summary.total")}
        </span>
      </div>

      {/* 右侧统计 */}
      <div className="flex flex-nowrap gap-2 min-w-0 overflow-hidden">
        {summary.added > 0 && (
          <Badge
            color="added"
            prefix="+"
            value={summary.added}
            label={t("artifacts.summary.added")}
          />
        )}

        {summary.modified > 0 && (
          <Badge
            color="modified"
            value={summary.modified}
            label={t("artifacts.summary.modified")}
          />
        )}

        {summary.deleted > 0 && (
          <Badge
            color="deleted"
            prefix="-"
            value={summary.deleted}
            label={t("artifacts.summary.deleted")}
          />
        )}

        {summary.renamed > 0 && (
          <Badge
            color="renamed"
            value={summary.renamed}
            label={t("artifacts.summary.renamed")}
          />
        )}
      </div>
    </div>
  );
}

interface BadgeProps {
  value: number;
  label: string;
  prefix?: string;
  color: "added" | "modified" | "deleted" | "renamed";
}

function Badge({ value, label, prefix = "", color }: BadgeProps) {
  const colorMap = {
    added: "bg-primary/10 text-primary",
    modified: "bg-chart-2/10 text-chart-2",
    deleted: "bg-destructive/10 text-destructive",
    renamed: "bg-chart-3/10 text-chart-3",
  };

  return (
    <span
      className={`
        inline-flex items-center
        px-2 py-0.5
        rounded-full
        text-xs font-medium
        whitespace-nowrap
        shrink-0
        ${colorMap[color]}
      `}
    >
      {/* 数字永远显示 */}
      {prefix}
      {value}

      {/* 文字：当容器小于 360px 自动隐藏 */}
      <span
        className="
          ml-1
          transition-all
          [@container(max-width:360px)]:hidden
        "
      >
        {label}
      </span>
    </span>
  );
}

/**
 * Enhanced scrollable list of file changes with summary
 */
export function FileChangesList({
  fileChanges = [],
  sessionStatus,
  onFileClick,
}: FileChangesListProps) {
  const { t } = useT("translation");

  if (fileChanges.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center text-muted-foreground">
          <p className="text-sm">{t("artifacts.empty.noChanges")}</p>
        </div>
      </div>
    );
  }

  const summary = fileChanges.reduce(
    (acc, change) => {
      switch (change.status) {
        case "added":
          acc.added++;
          break;
        case "modified":
          acc.modified++;
          break;
        case "deleted":
          acc.deleted++;
          break;
        case "renamed":
          acc.renamed++;
          break;
      }
      return acc;
    },
    { added: 0, modified: 0, deleted: 0, renamed: 0 },
  );

  return (
    <div className="flex flex-col h-full min-w-0 max-w-full overflow-hidden">
      <ArtifactsSummaryBar summary={summary} t={t} />
      <ScrollArea className="flex-1 min-w-0 max-w-full overflow-hidden [&_[data-slot=scroll-area-viewport]]:overflow-x-hidden">
        <div className="w-full min-w-0 max-w-full px-4 py-4 space-y-3">
          {fileChanges.map((change, index) => (
            <FileChangeCard
              key={`${change.path}-${index}`}
              change={change}
              sessionStatus={sessionStatus}
              onFileClick={() => onFileClick?.(change.path)}
            />
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
