"use client";

import * as React from "react";
import { Blocks, Loader2, MessageSquareText } from "lucide-react";
import type { RunResponse } from "@/features/chat/types";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n/client";
import { useRunRecordSummary } from "@/features/chat/hooks/use-run-record-summary";
import {
  buildActionHint,
  getStatusTone,
} from "@/features/chat/components/layout/run-timeline-utils";

interface MobileRunTimelineProps {
  runs: RunResponse[];
  selectedRunId?: string;
  onSelectRun: (runId: string) => void;
}

export function MobileRunTimeline({
  runs,
  selectedRunId,
  onSelectRun,
}: MobileRunTimelineProps) {
  const { t } = useT("translation");
  const containerRef = React.useRef<HTMLDivElement | null>(null);
  const runRefs = React.useRef(new Map<string, HTMLButtonElement>());
  const runRecordSummaries = useRunRecordSummary(runs);

  React.useEffect(() => {
    const targetRunId = selectedRunId ?? runs.at(-1)?.run_id;
    if (!targetRunId) return;

    const container = containerRef.current;
    const target = runRefs.current.get(targetRunId);
    if (!container || !target) return;

    const containerRect = container.getBoundingClientRect();
    const targetRect = target.getBoundingClientRect();
    const isFullyVisible =
      targetRect.left >= containerRect.left &&
      targetRect.right <= containerRect.right;

    if (!isFullyVisible) {
      target.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
        inline: "center",
      });
    }
  }, [runs, selectedRunId]);

  if (runs.length <= 1) return null;

  return (
    <div
      ref={containerRef}
      className="min-w-0 flex-1 overflow-x-auto overscroll-x-contain [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden"
    >
      <div className="flex min-w-max snap-x snap-mandatory items-center gap-1.5 px-0.5">
        {runs.map((run, index) => {
          const isSelected = run.run_id === selectedRunId;
          const recordSummary = runRecordSummaries[run.run_id];
          const isActionNode = buildActionHint(
            run,
            (recordSummary?.replayStepCount ?? 0) > 0,
          );
          const statusTone = getStatusTone(run.status);
          const runNumber = index + 1;
          const isLast = index === runs.length - 1;

          return (
            <React.Fragment key={run.run_id}>
              <button
                ref={(node) => {
                  if (node) {
                    runRefs.current.set(run.run_id, node);
                    return;
                  }

                  runRefs.current.delete(run.run_id);
                }}
                type="button"
                onClick={() => onSelectRun(run.run_id)}
                aria-label={t("runTimeline.selectRun", {
                  number: runNumber,
                })}
                className={cn(
                  "group inline-flex h-8 shrink-0 snap-start items-center gap-1 rounded-full border px-2.5 text-xs transition-colors",
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
