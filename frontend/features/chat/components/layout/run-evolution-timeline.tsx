"use client";

import * as React from "react";
import {
  Blocks,
  CheckCircle2,
  Circle,
  Loader2,
  MessageSquareText,
  MoreHorizontal,
  XCircle,
} from "lucide-react";
import type { RunResponse } from "@/features/chat/types";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n/client";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { getRunToolExecutionsAction } from "@/features/chat/actions/query-actions";

interface RunEvolutionTimelineProps {
  runs: RunResponse[];
  selectedRunId?: string;
  onSelectRun: (runId: string) => void;
}

type TimelineItem =
  | { type: "run"; run: RunResponse; index: number }
  | { type: "ellipsis"; key: string };

function hasRunArtifacts(run: RunResponse): boolean {
  const fileChanges = run.state_patch?.workspace_state?.file_changes ?? [];
  return (
    fileChanges.length > 0 ||
    Boolean(
      run.workspace_manifest_key ||
      run.workspace_files_prefix ||
      run.workspace_archive_key ||
      run.workspace_export_status === "ready",
    )
  );
}

function buildActionHint(
  run: RunResponse,
  hasToolExecutions: boolean,
): boolean {
  return hasRunArtifacts(run) || hasToolExecutions;
}

function formatDurationSeconds(run: RunResponse): string | null {
  if (!run.started_at) return null;
  const startedAt = new Date(run.started_at).getTime();
  const endAt = run.finished_at
    ? new Date(run.finished_at).getTime()
    : Date.now();
  if (
    !Number.isFinite(startedAt) ||
    !Number.isFinite(endAt) ||
    endAt <= startedAt
  ) {
    return null;
  }
  const seconds = Math.max(1, Math.round((endAt - startedAt) / 1000));
  if (seconds >= 60) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
  }
  return `${seconds}s`;
}

function buildVisibleItems(
  runs: RunResponse[],
  selectedIndex: number,
): TimelineItem[] {
  if (runs.length <= 10) {
    return runs.map((run, index) => ({ type: "run", run, index }));
  }

  const anchorIndexes = new Set<number>([
    0,
    1,
    runs.length - 2,
    runs.length - 1,
    selectedIndex - 1,
    selectedIndex,
    selectedIndex + 1,
  ]);

  const sortedIndexes = [...anchorIndexes]
    .filter((index) => index >= 0 && index < runs.length)
    .sort((a, b) => a - b);

  const items: TimelineItem[] = [];
  let previousIndex: number | null = null;

  for (const index of sortedIndexes) {
    if (previousIndex !== null && index - previousIndex > 1) {
      items.push({
        type: "ellipsis",
        key: `ellipsis-${previousIndex}-${index}`,
      });
    }
    items.push({ type: "run", run: runs[index]!, index });
    previousIndex = index;
  }

  return items;
}

function getStatusTone(status: string): {
  node: string;
  line: string;
  badge: string;
} {
  switch (status) {
    case "completed":
      return {
        node: "border-emerald-500/80 bg-emerald-500 text-white dark:border-emerald-400/80 dark:bg-emerald-400 dark:text-emerald-950",
        line: "bg-emerald-400/80 dark:bg-emerald-300/80",
        badge: "text-emerald-700 dark:text-emerald-300",
      };
    case "running":
    case "pending":
    case "claimed":
    case "queued":
    case "canceling":
      return {
        node: "border-primary/80 bg-primary text-primary-foreground dark:border-primary/70 dark:bg-primary dark:text-primary-foreground",
        line: "bg-primary/70 dark:bg-primary/80",
        badge: "text-primary dark:text-primary/90",
      };
    case "failed":
      return {
        node: "border-destructive/80 bg-destructive text-destructive-foreground dark:border-red-400/80 dark:bg-red-400 dark:text-red-950",
        line: "bg-destructive/70 dark:bg-red-400/80",
        badge: "text-destructive dark:text-red-300",
      };
    default:
      return {
        node: "border-border bg-muted/80 text-muted-foreground dark:border-border/80 dark:bg-muted/60 dark:text-muted-foreground",
        line: "bg-border dark:bg-border/80",
        badge: "text-muted-foreground dark:text-muted-foreground",
      };
  }
}

export function RunEvolutionTimeline({
  runs,
  selectedRunId,
  onSelectRun,
}: RunEvolutionTimelineProps) {
  const { t } = useT("translation");
  const [runToolCounts, setRunToolCounts] = React.useState<
    Record<string, number>
  >({});
  const selectedIndex = Math.max(
    0,
    runs.findIndex((run) => run.run_id === selectedRunId),
  );
  const visibleItems = React.useMemo(
    () => buildVisibleItems(runs, selectedIndex),
    [runs, selectedIndex],
  );

  React.useEffect(() => {
    let cancelled = false;

    const unresolvedRuns = runs.filter((run) => {
      if (hasRunArtifacts(run)) return false;
      return runToolCounts[run.run_id] === undefined;
    });
    if (unresolvedRuns.length === 0) return;

    const loadToolCounts = async () => {
      const entries = await Promise.all(
        unresolvedRuns.map(async (run) => {
          try {
            const items = await getRunToolExecutionsAction({
              runId: run.run_id,
              limit: 2000,
              offset: 0,
            });
            return [run.run_id, items.length] as const;
          } catch (error) {
            console.error(
              "[RunEvolutionTimeline] Failed to load run tool counts:",
              error,
            );
            return [run.run_id, 0] as const;
          }
        }),
      );

      if (cancelled) return;
      setRunToolCounts((prev) => {
        const next = { ...prev };
        for (const [runId, toolCount] of entries) {
          next[runId] = toolCount;
        }
        return next;
      });
    };

    void loadToolCounts();
    return () => {
      cancelled = true;
    };
  }, [runToolCounts, runs]);

  const handleArrowNavigation = React.useCallback(
    (event: React.KeyboardEvent<HTMLDivElement>) => {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      if (runs.length <= 1) return;

      const currentIndex = runs.findIndex(
        (run) => run.run_id === selectedRunId,
      );
      const safeIndex = currentIndex >= 0 ? currentIndex : runs.length - 1;
      const nextIndex =
        event.key === "ArrowLeft"
          ? Math.max(0, safeIndex - 1)
          : Math.min(runs.length - 1, safeIndex + 1);
      if (nextIndex === safeIndex) return;
      event.preventDefault();
      onSelectRun(runs[nextIndex]!.run_id);
    },
    [onSelectRun, runs, selectedRunId],
  );

  if (runs.length <= 1) return null;

  return (
    <div className="border-b border-border/60 bg-background/90 px-3 py-1.5 dark:bg-background/95">
      <div
        tabIndex={0}
        onKeyDown={handleArrowNavigation}
        className="rounded-lg border border-border/60 bg-background/95 px-2 py-1.5 shadow-sm shadow-black/5 outline-none focus-visible:ring-2 focus-visible:ring-ring dark:border-border/80 dark:bg-card/80 dark:shadow-black/25"
      >
        <div className="overflow-x-auto">
          <div className="flex min-w-max items-center gap-1">
            {visibleItems.map((item, itemIndex) => {
              if (item.type === "ellipsis") {
                return (
                  <div
                    key={item.key}
                    className="flex items-center gap-1 px-0.5 text-muted-foreground/80"
                  >
                    <div className="h-px w-4 bg-border" />
                    <MoreHorizontal className="size-3" />
                    <div className="h-px w-4 bg-border" />
                  </div>
                );
              }

              const run = item.run;
              const isSelected = run.run_id === selectedRunId;
              const isActionNode = buildActionHint(
                run,
                (runToolCounts[run.run_id] ?? 0) > 0,
              );
              const fileChanges =
                run.state_patch?.workspace_state?.file_changes ?? [];
              const executionSummaryCount =
                fileChanges.length + (runToolCounts[run.run_id] ?? 0);
              const durationLabel = formatDurationSeconds(run);
              const statusTone = getStatusTone(run.status);
              const summary = run.last_error
                ? run.last_error
                : run.state_patch?.current_step ||
                  (isActionNode
                    ? t("runTimeline.preview.executionSummary", {
                        count: executionSummaryCount,
                      })
                    : t("runTimeline.preview.conversationOnly"));

              const nextVisible = visibleItems[itemIndex + 1];
              const showConnector = nextVisible?.type === "run";
              const connectorDashed =
                run.status === "canceled" ||
                (nextVisible?.type === "run" &&
                  nextVisible.run.status === "canceled");

              return (
                <React.Fragment key={run.run_id}>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        type="button"
                        onClick={() => onSelectRun(run.run_id)}
                        className={cn(
                          "group flex min-w-[52px] flex-col items-center gap-0.5 rounded-lg border px-1.5 py-1 transition-all",
                          isSelected
                            ? "border-transparent shadow-none"
                            : "border-transparent hover:bg-muted/40 dark:hover:bg-muted/30",
                        )}
                        aria-label={t("runTimeline.selectRun", {
                          number: item.index + 1,
                        })}
                      >
                        <div className="relative flex items-center justify-center">
                          <div
                            className={cn(
                              "flex size-5 items-center justify-center rounded-full border text-[10px] shadow-sm transition-transform duration-200",
                              statusTone.node,
                              isActionNode
                                ? "size-6"
                                : "size-5 bg-background dark:bg-card",
                              isSelected
                                ? "scale-110 ring-4 ring-primary/10 dark:ring-primary/20"
                                : "scale-100 opacity-95 group-hover:scale-105",
                              run.status === "running" &&
                                "shadow-primary/30 motion-safe:animate-pulse dark:shadow-primary/40",
                            )}
                          >
                            {run.status === "running" ? (
                              <Loader2 className="size-3 animate-spin" />
                            ) : isActionNode ? (
                              <Blocks className="size-3" />
                            ) : (
                              <MessageSquareText className="size-2.5" />
                            )}
                          </div>
                          {isSelected ? (
                            <>
                              <span className="absolute -inset-1 rounded-full border border-primary/30" />
                            </>
                          ) : null}
                        </div>

                        <div className="min-w-0 text-center">
                          <div
                            className={cn(
                              "rounded-full px-1.5 py-0.5 text-[10px] font-medium leading-none transition-colors",
                              isSelected
                                ? "bg-primary text-primary-foreground dark:bg-primary dark:text-primary-foreground"
                                : "text-muted-foreground group-hover:text-foreground dark:group-hover:text-foreground",
                            )}
                          >
                            {`R${item.index + 1}`}
                          </div>
                        </div>
                      </button>
                    </TooltipTrigger>
                    <TooltipContent
                      side="bottom"
                      align="start"
                      className="max-w-72 rounded-xl border border-border/80 bg-popover/98 p-3 text-popover-foreground shadow-xl shadow-black/10 backdrop-blur-sm dark:border-border dark:bg-popover dark:shadow-black/40"
                    >
                      <div className="space-y-2 text-xs">
                        <div className="flex items-center justify-between gap-3">
                          <div className="font-medium text-foreground">
                            {t("runTimeline.runLabel", {
                              number: item.index + 1,
                            })}
                          </div>
                          <div
                            className={cn(
                              "inline-flex items-center gap-1",
                              statusTone.badge,
                            )}
                          >
                            {run.status === "failed" ? (
                              <XCircle className="size-3.5" />
                            ) : run.status === "completed" ? (
                              <CheckCircle2 className="size-3.5" />
                            ) : run.status === "running" ? (
                              <Loader2 className="size-3.5 animate-spin" />
                            ) : (
                              <Circle className="size-3.5" />
                            )}
                            <span>{run.status}</span>
                          </div>
                        </div>
                        <div className="line-clamp-2 text-[11px] leading-4 text-muted-foreground">
                          {summary}
                        </div>
                        <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
                          <span className="rounded-full bg-muted px-2 py-0.5 dark:bg-muted/70">
                            {isActionNode
                              ? t("runTimeline.preview.execution", {
                                  count: executionSummaryCount,
                                })
                              : t("runTimeline.preview.conversationOnly")}
                          </span>
                          {durationLabel ? (
                            <span className="rounded-full bg-muted px-2 py-0.5 dark:bg-muted/70">
                              {t("runTimeline.preview.duration", {
                                duration: durationLabel,
                              })}
                            </span>
                          ) : null}
                        </div>
                      </div>
                    </TooltipContent>
                  </Tooltip>

                  {showConnector ? (
                    <div className="flex w-5 items-center justify-center">
                      <div
                        className={cn(
                          "h-0.5 w-full rounded-full",
                          statusTone.line,
                          connectorDashed &&
                            "bg-none bg-[linear-gradient(to_right,currentColor_50%,transparent_0%)] bg-[length:8px_1px] text-muted-foreground/60",
                        )}
                      />
                    </div>
                  ) : null}
                </React.Fragment>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
