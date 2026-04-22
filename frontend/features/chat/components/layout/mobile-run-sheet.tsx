"use client";

import * as React from "react";
import {
  Blocks,
  CheckCircle2,
  Circle,
  Loader2,
  MessageSquareText,
  XCircle,
} from "lucide-react";
import type { RunResponse } from "@/features/chat/types";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n/client";
import { useRunRecordSummary } from "@/features/chat/hooks/use-run-record-summary";
import {
  buildActionHint,
  formatDurationSeconds,
  getRunFileChangeCount,
  getStatusTone,
} from "@/features/chat/components/layout/run-timeline-utils";

interface MobileRunSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  runs: RunResponse[];
  selectedRunId?: string;
  currentRunId?: string;
  onSelectRun: (runId: string) => void;
  onFollowCurrentRun?: () => void;
}

export function MobileRunSheet({
  open,
  onOpenChange,
  runs,
  selectedRunId,
  currentRunId,
  onSelectRun,
  onFollowCurrentRun,
}: MobileRunSheetProps) {
  const { t } = useT("translation");
  const runRecordSummaries = useRunRecordSummary(runs, open);

  const isViewingHistory = Boolean(
    selectedRunId && currentRunId && selectedRunId !== currentRunId,
  );
  const orderedRuns = React.useMemo(() => [...runs].reverse(), [runs]);

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className="!h-[85vh] !max-h-[85vh]">
        <DrawerHeader className="pb-2 text-left">
          <DrawerTitle>{t("mobile.runs.allRuns")}</DrawerTitle>
          <DrawerDescription>
            {t("mobile.runs.sheetDescription")}
          </DrawerDescription>
        </DrawerHeader>

        {isViewingHistory && currentRunId && onFollowCurrentRun ? (
          <div className="px-4 pb-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8 w-full justify-center rounded-full"
              onClick={() => {
                onFollowCurrentRun();
                onOpenChange(false);
              }}
            >
              {t("mobile.runs.backToCurrent")}
            </Button>
          </div>
        ) : null}

        {runs.length > 1 ? (
          <div className="px-4 pb-2 text-xs text-muted-foreground">
            {t("mobile.runs.sheetHint")}
          </div>
        ) : null}

        <ScrollArea className="flex-1 min-h-0 px-2 pb-4">
          <div className="space-y-2 px-2 pb-4">
            {orderedRuns.map((run) => {
              const isSelected = run.run_id === selectedRunId;
              const isCurrent = run.run_id === currentRunId;
              const recordSummary = runRecordSummaries[run.run_id];
              const fileChangeCount =
                recordSummary?.fileChangeCount ?? getRunFileChangeCount(run);
              const replayStepCount = recordSummary?.replayStepCount ?? 0;
              const isActionNode = buildActionHint(run, replayStepCount > 0);
              const statusTone = getStatusTone(run.status);
              const duration = formatDurationSeconds(run);
              const summary = run.last_error
                ? run.last_error
                : run.state_patch?.current_step ||
                  (isActionNode
                    ? t("runTimeline.preview.executionSummary")
                    : t("runTimeline.preview.conversationOnly"));

              return (
                <button
                  key={run.run_id}
                  type="button"
                  onClick={() => {
                    onSelectRun(run.run_id);
                    onOpenChange(false);
                  }}
                  className={cn(
                    "flex w-full flex-row items-start gap-3 rounded-2xl border px-3 py-3 text-left transition-colors",
                    isSelected
                      ? "border-primary/25 bg-primary/10"
                      : "border-border/60 bg-background hover:bg-muted/40",
                  )}
                >
                  <div
                    className={cn(
                      "mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full border",
                      statusTone.node,
                      !isActionNode && "bg-background dark:bg-card",
                      run.status === "running" &&
                        "motion-safe:animate-pulse shadow-primary/30",
                    )}
                  >
                    {run.status === "running" ? (
                      <Loader2 className="size-4 animate-spin" />
                    ) : isActionNode ? (
                      <Blocks className="size-4" />
                    ) : (
                      <MessageSquareText className="size-3.5" />
                    )}
                  </div>

                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-foreground">
                        {t("runTimeline.runLabel", {
                          number:
                            runs.findIndex(
                              (item) => item.run_id === run.run_id,
                            ) + 1,
                        })}
                      </span>
                      {isCurrent ? (
                        <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
                          {t("mobile.runs.current")}
                        </span>
                      ) : null}
                    </div>
                    <div className="line-clamp-2 text-xs leading-4 text-muted-foreground">
                      {summary}
                    </div>
                    <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
                      <span
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
                      </span>
                      <span className="rounded-full bg-muted px-2 py-0.5">
                        {isActionNode
                          ? t("runTimeline.preview.execution", {
                              files: fileChangeCount,
                              steps: replayStepCount,
                            })
                          : t("runTimeline.node.chat")}
                      </span>
                      {isActionNode ? (
                        <span className="rounded-full bg-muted px-2 py-0.5">
                          {t("runTimeline.node.action")}
                        </span>
                      ) : null}
                      {duration ? (
                        <span className="rounded-full bg-muted px-2 py-0.5">
                          {t("runTimeline.preview.duration", {
                            duration,
                          })}
                        </span>
                      ) : null}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </ScrollArea>
      </DrawerContent>
    </Drawer>
  );
}
