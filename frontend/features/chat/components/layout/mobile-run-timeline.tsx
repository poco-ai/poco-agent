"use client";

import * as React from "react";
import { Blocks, Loader2, MessageSquareText } from "lucide-react";
import type { RunResponse } from "@/features/chat/types";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n/client";
import { getRunToolExecutionsAction } from "@/features/chat/actions/query-actions";
import {
  buildActionHint,
  getStatusTone,
} from "@/features/chat/components/layout/run-timeline-utils";

interface MobileRunTimelineProps {
  runs: RunResponse[];
  selectedRunId?: string;
  onSelectRun: (runId: string) => void;
}

function buildCompactRuns(
  runs: RunResponse[],
  selectedRunId?: string,
  limit = 4,
): RunResponse[] {
  if (runs.length <= limit) return runs;

  const recentRuns = runs.slice(-limit);
  if (recentRuns.some((run) => run.run_id === selectedRunId)) {
    return recentRuns;
  }

  const selectedRun = runs.find((run) => run.run_id === selectedRunId);
  if (!selectedRun) return recentRuns;

  return [selectedRun, ...runs.slice(-(limit - 1))];
}

export function MobileRunTimeline({
  runs,
  selectedRunId,
  onSelectRun,
}: MobileRunTimelineProps) {
  const { t } = useT("translation");
  const [runToolPresence, setRunToolPresence] = React.useState<
    Record<string, boolean>
  >({});

  const visibleRuns = React.useMemo(
    () => buildCompactRuns(runs, selectedRunId),
    [runs, selectedRunId],
  );

  React.useEffect(() => {
    let cancelled = false;

    const unresolvedRuns = visibleRuns.filter(
      (run) => runToolPresence[run.run_id] === undefined,
    );
    if (unresolvedRuns.length === 0) return;

    const loadToolPresence = async () => {
      const entries = await Promise.all(
        unresolvedRuns.map(async (run) => {
          try {
            const items = await getRunToolExecutionsAction({
              runId: run.run_id,
              limit: 1,
              offset: 0,
            });
            return [run.run_id, items.length > 0] as const;
          } catch (error) {
            console.error(
              "[MobileRunTimeline] Failed to load run tool presence:",
              error,
            );
            return [run.run_id, false] as const;
          }
        }),
      );

      if (cancelled) return;
      setRunToolPresence((prev) => {
        const next = { ...prev };
        for (const [runId, hasTools] of entries) {
          next[runId] = hasTools;
        }
        return next;
      });
    };

    void loadToolPresence();
    return () => {
      cancelled = true;
    };
  }, [runToolPresence, visibleRuns]);

  if (runs.length <= 1) return null;

  return (
    <div className="min-w-0 flex-1 overflow-x-auto">
      <div className="flex min-w-max items-center gap-1.5">
        {visibleRuns.map((run, index) => {
          const isSelected = run.run_id === selectedRunId;
          const isActionNode = buildActionHint(
            run,
            runToolPresence[run.run_id] === true,
          );
          const statusTone = getStatusTone(run.status);
          const runNumber =
            runs.findIndex((item) => item.run_id === run.run_id) + 1;
          const isLast = index === visibleRuns.length - 1;

          return (
            <React.Fragment key={run.run_id}>
              <button
                type="button"
                onClick={() => onSelectRun(run.run_id)}
                aria-label={t("runTimeline.selectRun", {
                  number: runNumber,
                })}
                className={cn(
                  "group inline-flex h-8 shrink-0 items-center gap-1 rounded-full border px-2.5 text-xs transition-colors",
                  isSelected
                    ? "border-primary/20 bg-primary/10 text-foreground"
                    : "border-border/60 bg-background/90 text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                )}
              >
                <span
                  className={cn(
                    "flex size-4 shrink-0 items-center justify-center rounded-full border",
                    statusTone.node,
                    !isActionNode && "bg-background dark:bg-card",
                    run.status === "running" &&
                      "motion-safe:animate-pulse shadow-primary/30",
                  )}
                >
                  {run.status === "running" ? (
                    <Loader2 className="size-2.5 animate-spin" />
                  ) : isActionNode ? (
                    <Blocks className="size-2.5" />
                  ) : (
                    <MessageSquareText className="size-2.5" />
                  )}
                </span>
                <span className="font-medium tabular-nums">{`R${runNumber}`}</span>
              </button>
              {!isLast ? (
                <div className="h-px w-2 shrink-0 bg-border/70" />
              ) : null}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
