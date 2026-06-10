"use client";

import * as React from "react";
import {
  CheckCircle2,
  Circle,
  FileEdit,
  FilePlus,
  FileText,
  FileX,
  GitCompare,
  Terminal,
  Wrench,
  XCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent } from "@/components/ui/tabs";
import { PanelHeader } from "@/components/shared/panel-header";
import { ExecutionTabsSwitch } from "@/features/chat/components/layout/execution-tabs-switch";
import { RunEvolutionTimeline } from "@/features/chat/components/layout/run-evolution-timeline";
import { formatDurationSeconds } from "@/features/chat/components/layout/run-timeline-utils";
import type {
  FileChange,
  RunResponse,
  SessionShareSnapshot,
  SharedRunSummary,
  SharedToolExecution,
} from "@/features/chat/types";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

interface SessionShareExecutionPanelProps {
  snapshot: SessionShareSnapshot;
}

function mapSharedRunToRunResponse(
  run: SharedRunSummary,
  sessionId: string,
): RunResponse {
  return {
    run_id: run.runId,
    session_id: sessionId,
    user_message_id: run.userMessageId,
    status: run.status,
    permission_mode: "default",
    progress: run.progress,
    schedule_mode: run.scheduleMode,
    scheduled_task_id: null,
    scheduled_at: run.startedAt ?? run.createdAt,
    state_patch: {
      workspace_state: {
        file_change_count: run.fileChangeCount,
        file_changes: run.fileChanges,
        last_change: run.updatedAt,
      },
    },
    workspace_archive_url: null,
    workspace_files_prefix: null,
    workspace_manifest_key: null,
    workspace_archive_key: null,
    workspace_export_status: run.workspaceExportStatus,
    usage: null,
    replay_step_count: run.replayStepCount,
    file_change_count: run.fileChangeCount,
    claimed_by: null,
    lease_expires_at: null,
    attempts: 0,
    last_error: null,
    started_at: run.startedAt ?? null,
    finished_at: run.finishedAt ?? null,
    created_at: run.createdAt,
    updated_at: run.updatedAt,
  };
}

function formatDurationMs(
  durationMs: number | null | undefined,
  t: (key: string, values?: Record<string, unknown>) => string,
) {
  if (typeof durationMs !== "number" || durationMs <= 0) return null;
  if (durationMs >= 1000) {
    return t("computer.replay.durationSec", {
      sec: Math.max(1, Math.round(durationMs / 1000)),
    });
  }
  return t("computer.replay.durationMs", { ms: durationMs });
}

function getToolSummary(execution: SharedToolExecution) {
  const input = execution.toolInput ?? {};
  for (const key of [
    "command",
    "url",
    "path",
    "file_path",
    "query",
    "pattern",
  ]) {
    const value = input[key];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return execution.toolName;
}

function getToolIcon(toolName: string) {
  const normalized = toolName.toLowerCase().replace(/[\s_-]/g, "");
  if (normalized === "bash") return Terminal;
  if (["read", "write", "edit", "glob", "grep"].includes(normalized)) {
    return FileText;
  }
  return Wrench;
}

function getFileChangeIcon(status: FileChange["status"]) {
  switch (status) {
    case "added":
      return FilePlus;
    case "deleted":
      return FileX;
    case "renamed":
      return GitCompare;
    case "modified":
    default:
      return FileEdit;
  }
}

function getFileChangeTone(status: FileChange["status"]) {
  switch (status) {
    case "added":
      return "text-primary";
    case "deleted":
      return "text-destructive";
    case "renamed":
      return "text-chart-3";
    case "modified":
    default:
      return "text-chart-2";
  }
}

function StatusBadge({ status }: { status: string }) {
  const Icon =
    status === "completed"
      ? CheckCircle2
      : status === "failed"
        ? XCircle
        : Circle;
  return (
    <Badge variant="outline" className="h-6 gap-1.5 rounded-full">
      <Icon className="size-3" />
      <span className="truncate">{status}</span>
    </Badge>
  );
}

function SharedComputerSnapshot({
  run,
  runNumber,
}: {
  run: SharedRunSummary;
  runNumber: number;
}) {
  const { t } = useT("translation");
  const duration = formatDurationSeconds(
    mapSharedRunToRunResponse(run, "shared-session"),
  );

  return (
    <ScrollArea className="h-full min-h-0 [&_[data-slot=scroll-area-viewport]]:overflow-x-hidden">
      <div className="space-y-3 p-4">
        <div className="rounded-xl border border-border bg-card p-4">
          <div className="flex min-w-0 items-start justify-between gap-3">
            <div className="min-w-0 space-y-1">
              <div className="text-sm font-medium">
                {t("runTimeline.runLabel", { number: runNumber })}
              </div>
              <div className="text-xs text-muted-foreground">
                {t("runTimeline.preview.execution", {
                  files: run.fileChangeCount,
                  steps: run.replayStepCount,
                })}
              </div>
              {duration ? (
                <div className="text-xs text-muted-foreground">
                  {t("runTimeline.preview.duration", { duration })}
                </div>
              ) : null}
            </div>
            <StatusBadge status={run.status} />
          </div>
        </div>

        {run.toolExecutions.length > 0 ? (
          <div className="space-y-2">
            {run.toolExecutions.map((execution) => {
              const Icon = getToolIcon(execution.toolName);
              const durationLabel = formatDurationMs(execution.durationMs, t);
              const summary = getToolSummary(execution);
              return (
                <div
                  key={execution.id}
                  className={cn(
                    "flex min-w-0 items-start gap-3 rounded-xl border bg-card p-3 text-sm",
                    execution.isError
                      ? "border-destructive/30"
                      : "border-border",
                  )}
                >
                  <div className="flex size-8 shrink-0 items-center justify-center rounded-lg border border-border bg-muted/60">
                    <Icon className="size-4 text-muted-foreground" />
                  </div>
                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex min-w-0 items-center justify-between gap-3">
                      <div className="min-w-0 truncate font-medium">
                        {execution.toolName || t("chat.toolCards.tools.tool")}
                      </div>
                      {durationLabel ? (
                        <span className="shrink-0 text-xs text-muted-foreground">
                          {durationLabel}
                        </span>
                      ) : null}
                    </div>
                    <div className="line-clamp-2 break-all text-xs text-muted-foreground">
                      {summary}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="flex h-48 items-center justify-center rounded-xl border border-border bg-card text-sm text-muted-foreground">
            {t("computer.replay.empty")}
          </div>
        )}
      </div>
    </ScrollArea>
  );
}

function SharedArtifactsSnapshot({ run }: { run: SharedRunSummary }) {
  const { t } = useT("translation");

  if (run.fileChanges.length === 0) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-sm text-muted-foreground">
        {t("artifacts.empty.noChanges")}
      </div>
    );
  }

  return (
    <ScrollArea className="h-full min-h-0 [&_[data-slot=scroll-area-viewport]]:overflow-x-hidden">
      <div className="space-y-3 p-4">
        {run.fileChanges.map((change, index) => {
          const Icon = getFileChangeIcon(change.status);
          const hasLineChanges =
            (change.added_lines ?? 0) > 0 || (change.deleted_lines ?? 0) > 0;
          return (
            <div
              key={`${change.path}-${index}`}
              className="rounded-xl border border-border bg-card p-3"
            >
              <div className="flex min-w-0 items-center gap-3">
                <Icon
                  className={cn(
                    "size-5 shrink-0",
                    getFileChangeTone(change.status),
                  )}
                />
                <div className="min-w-0 flex-1">
                  <div
                    className="truncate text-sm font-medium"
                    title={change.path}
                  >
                    {change.path}
                  </div>
                  {change.old_path ? (
                    <div
                      className="truncate text-xs text-muted-foreground"
                      title={change.old_path}
                    >
                      {change.old_path}
                    </div>
                  ) : null}
                </div>
                <Badge variant="secondary" className="shrink-0">
                  {change.status}
                </Badge>
              </div>
              {hasLineChanges ? (
                <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
                  <span className="text-primary">
                    +{change.added_lines ?? 0} {t("fileChange.linesAdded")}
                  </span>
                  <span className="text-destructive">
                    -{change.deleted_lines ?? 0} {t("fileChange.linesDeleted")}
                  </span>
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </ScrollArea>
  );
}

export function SessionShareExecutionPanel({
  snapshot,
}: SessionShareExecutionPanelProps) {
  const { t } = useT("translation");
  const runs = React.useMemo(
    () =>
      snapshot.runs.map((run) =>
        mapSharedRunToRunResponse(run, snapshot.session.sessionId),
      ),
    [snapshot.runs, snapshot.session.sessionId],
  );
  const [selectedRunId, setSelectedRunId] = React.useState(
    () => snapshot.runs.at(-1)?.runId,
  );
  const [rightTab, setRightTab] = React.useState("computer");

  React.useEffect(() => {
    setSelectedRunId((current) => {
      if (current && snapshot.runs.some((run) => run.runId === current)) {
        return current;
      }
      return snapshot.runs.at(-1)?.runId;
    });
  }, [snapshot.runs]);

  const selectedRunIndex = Math.max(
    0,
    snapshot.runs.findIndex((run) => run.runId === selectedRunId),
  );
  const selectedRun = snapshot.runs[selectedRunIndex] ?? snapshot.runs.at(-1);

  if (!selectedRun) {
    return (
      <div className="flex h-full items-center justify-center bg-muted/30 p-6 text-sm text-muted-foreground">
        {t("chat.timelineEmpty")}
      </div>
    );
  }

  return (
    <Tabs
      value={rightTab}
      onValueChange={setRightTab}
      className="flex h-full min-h-0 flex-col bg-muted/30"
    >
      <PanelHeader
        content={
          <div className="flex min-w-0 items-center gap-2 overflow-hidden">
            <ExecutionTabsSwitch
              rightTab={rightTab}
              highlightId={`share-${snapshot.share.shareId}`}
              showArtifactsTab
              showComputerTab
            />
          </div>
        }
        action={<StatusBadge status={selectedRun.status} />}
      />
      <RunEvolutionTimeline
        runs={runs}
        selectedRunId={selectedRun.runId}
        onSelectRun={setSelectedRunId}
      />
      <div className="min-h-0 flex-1 overflow-hidden">
        <TabsContent
          value="computer"
          className="h-full min-h-0 data-[state=inactive]:hidden"
        >
          <SharedComputerSnapshot
            run={selectedRun}
            runNumber={selectedRunIndex + 1}
          />
        </TabsContent>
        <TabsContent
          value="artifacts"
          className="h-full min-h-0 data-[state=inactive]:hidden"
        >
          <SharedArtifactsSnapshot run={selectedRun} />
        </TabsContent>
      </div>
    </Tabs>
  );
}
