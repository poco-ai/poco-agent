import * as React from "react";
import {
  FilePlus,
  FileEdit,
  FileX,
  GitCompare,
  ArrowRight,
  Plus,
  Minus,
  Eye,
  EyeOff,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import type { FileChange } from "@/features/chat/types";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

interface FileChangeCardProps {
  change: FileChange;
  sessionStatus?:
    | "running"
    | "accepted"
    | "completed"
    | "failed"
    | "canceled"
    | "stopped";
  onFileClick?: () => void;
}

/**
 * Get icon and color for file change status
 */
function getStatusConfig(status: FileChange["status"]) {
  switch (status) {
    case "added":
      return {
        icon: FilePlus,
        color: "text-success",
      };
    case "modified":
      return {
        icon: FileEdit,
        color: "text-info",
      };
    case "deleted":
      return {
        icon: FileX,
        color: "text-destructive",
      };
    case "renamed":
      return {
        icon: GitCompare,
        color: "text-renamed",
      };
    default:
      return {
        icon: FileEdit,
        color: "text-muted-foreground",
      };
  }
}

/**
 * Individual file change card
 */
export function FileChangeCard({
  change,
  sessionStatus,
  onFileClick,
}: FileChangeCardProps) {
  const { t } = useT("translation");
  const statusConfig = getStatusConfig(change.status);
  const StatusIcon = statusConfig.icon;
  const [isDiffCollapsed, setIsDiffCollapsed] = React.useState(false);

  const addedLines = change.added_lines ?? 0;
  const deletedLines = change.deleted_lines ?? 0;
  const hasLineChanges = addedLines > 0 || deletedLines > 0;
  const diffLines = React.useMemo(
    () => (change.diff ? change.diff.split("\n") : []),
    [change.diff],
  );

  // Determine if session is running (execution state)
  const isSessionRunning =
    sessionStatus === "running" || sessionStatus === "accepted";

  const handlePreviewClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!isSessionRunning && onFileClick) {
      onFileClick();
    }
  };

  const handleToggleDiffCollapse = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsDiffCollapsed((prev) => !prev);
  };

  const getDiffLineClass = React.useCallback((line: string) => {
    if (line.startsWith("+++ ") || line.startsWith("--- ")) {
      return "text-muted-foreground";
    }
    if (line.startsWith("@@")) {
      return "text-info";
    }
    if (line.startsWith("+")) {
      return "text-success bg-success/10";
    }
    if (line.startsWith("-")) {
      return "text-destructive bg-destructive/10";
    }
    if (line.startsWith("\\")) {
      return "text-muted-foreground";
    }
    return "text-foreground/80";
  }, []);

  const previewButton = (
    <Button
      variant="ghost"
      size="icon"
      className={`shrink-0 size-8 ${
        isSessionRunning ? "opacity-50 cursor-not-allowed" : "hover:bg-muted"
      }`}
      onClick={handlePreviewClick}
      disabled={isSessionRunning}
      title={
        isSessionRunning
          ? t("fileChange.previewDisabled")
          : t("fileChange.previewFile")
      }
    >
      {isSessionRunning ? (
        <EyeOff className="size-4" />
      ) : (
        <Eye className="size-4" />
      )}
    </Button>
  );

  return (
    <div className="w-full min-w-0 max-w-full overflow-hidden rounded-lg border border-border bg-card">
      {/* Header */}
      <div className="flex w-full min-w-0 items-center gap-3 overflow-hidden px-4 py-3">
        <StatusIcon className={`size-5 shrink-0 ${statusConfig.color}`} />

        <div className="w-0 flex-1 min-w-0 overflow-hidden">
          {change.status === "renamed" && change.old_path ? (
            <div className="flex items-center gap-2 min-w-0">
              <span
                className="w-0 flex-1 min-w-0 truncate text-sm font-medium text-muted-foreground line-through"
                title={change.old_path}
              >
                {change.old_path}
              </span>
              <ArrowRight className="size-3.5 text-muted-foreground shrink-0" />
              <span
                className="w-0 flex-1 min-w-0 truncate text-sm font-medium"
                title={change.path}
              >
                {change.path}
              </span>
            </div>
          ) : (
            <p
              className="w-full min-w-0 truncate text-sm font-medium"
              title={change.path}
            >
              {change.path}
            </p>
          )}
        </div>

        {!hasLineChanges && <div className="shrink-0">{previewButton}</div>}
      </div>

      {/* Line changes statistics */}
      {hasLineChanges && (
        <div className="flex min-w-0 items-center gap-3 overflow-hidden bg-muted/30 px-4 py-2 text-xs">
          {change.diff ? (
            <Button
              variant="ghost"
              size="icon"
              className="size-6 shrink-0 text-muted-foreground hover:text-foreground"
              onClick={handleToggleDiffCollapse}
              title={t("fileChange.viewDiff")}
              aria-label={t("fileChange.viewDiff")}
            >
              <ChevronRight
                className={cn(
                  "size-3.5 transition-transform duration-200",
                  isDiffCollapsed ? "rotate-0" : "rotate-90",
                )}
              />
            </Button>
          ) : null}
          <div className="flex-1 min-w-0 items-center gap-3 overflow-hidden">
            {(addedLines > 0 || deletedLines > 0) && (
              <div className="flex gap-3 min-w-0 overflow-hidden">
                <span className="flex items-center gap-1.5 min-w-0">
                  <Plus className="size-3 shrink-0 text-success" />
                  <span className="font-medium shrink-0 text-success">
                    {addedLines}
                  </span>
                  <span className="text-muted-foreground shrink-0">
                    {t("fileChange.linesAdded")}
                  </span>
                  <Minus className="size-3 shrink-0 text-destructive" />
                  <span className="font-medium shrink-0 text-destructive">
                    {deletedLines}
                  </span>
                  <span className="text-muted-foreground shrink-0">
                    {t("fileChange.linesDeleted")}
                  </span>
                </span>
              </div>
            )}
          </div>
          <div className="ml-auto flex items-center">{previewButton}</div>
        </div>
      )}

      {/* Diff preview (if available) */}
      {change.diff && !isDiffCollapsed ? (
        <div className="border-t border-border px-4 py-3">
          <div className="w-full min-w-0">
            <div className="w-full min-w-0 text-xs font-mono bg-muted/50 rounded p-2 whitespace-pre-wrap break-all">
              {/* fuck you overflow! */}
              {diffLines.map((line, index) => (
                <div
                  key={`${index}-${line}`}
                  className={cn("w-full", getDiffLineClass(line))}
                >
                  {line}
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
