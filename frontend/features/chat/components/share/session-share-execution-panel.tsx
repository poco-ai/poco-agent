"use client";

import * as React from "react";
import { CheckCircle2, Circle, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent } from "@/components/ui/tabs";
import { PanelHeader } from "@/components/shared/panel-header";
import { ComputerPanel } from "@/features/chat/components/execution/computer-panel";
import { DocumentViewer } from "@/features/chat/components/execution/file-panel/document-viewer";
import { FileChangesList } from "@/features/chat/components/execution/file-panel/file-changes-list";
import {
  FileSidebar,
  downloadFileFromUrl,
} from "@/features/chat/components/execution/file-panel/file-sidebar";
import { ExecutionTabsSwitch } from "@/features/chat/components/layout/execution-tabs-switch";
import { RunEvolutionTimeline } from "@/features/chat/components/layout/run-evolution-timeline";
import type {
  FileNode,
  RunResponse,
  SessionShareSnapshot,
  SharedRunSummary,
  SharedToolExecution,
  ToolExecutionResponse,
} from "@/features/chat/types";
import { useT } from "@/lib/i18n/client";

interface SessionShareExecutionPanelProps {
  snapshot: SessionShareSnapshot;
}

type RunStatus =
  | "queued"
  | "claimed"
  | "pending"
  | "running"
  | "canceling"
  | "completed"
  | "failed"
  | "canceled";

const RUN_STATUSES = new Set<string>([
  "queued",
  "claimed",
  "pending",
  "running",
  "canceling",
  "completed",
  "failed",
  "canceled",
]);

const normalizePath = (path: string) => path.replace(/^\/+/, "");

function asRunStatus(status: string): RunStatus | undefined {
  return RUN_STATUSES.has(status) ? (status as RunStatus) : undefined;
}

function findFileByPath(
  nodes: FileNode[],
  targetPath: string,
): FileNode | undefined {
  const normalizedTarget = normalizePath(targetPath);
  for (const node of nodes) {
    if (node.type === "file" && normalizePath(node.path) === normalizedTarget) {
      return node;
    }
    if (node.children?.length) {
      const found = findFileByPath(node.children, targetPath);
      if (found) return found;
    }
  }
  return undefined;
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

function mapSharedToolExecution(
  execution: SharedToolExecution,
): ToolExecutionResponse {
  return {
    id: execution.id,
    run_id: execution.runId ?? null,
    message_id: execution.messageId ?? null,
    tool_use_id: execution.toolUseId ?? null,
    tool_name: execution.toolName,
    tool_input: execution.toolInput ?? null,
    tool_output: execution.toolOutput ?? null,
    is_error: execution.isError,
    duration_ms: execution.durationMs ?? null,
    created_at: execution.createdAt,
    updated_at: execution.updatedAt,
  };
}

function SharedComputerSnapshot({ run }: { run: SharedRunSummary }) {
  const toolExecutions = React.useMemo(
    () => run.toolExecutions.map(mapSharedToolExecution),
    [run.toolExecutions],
  );
  const screenshotUrlByToolUseId = React.useMemo(() => {
    const urls = new Map<string, string>();
    for (const execution of run.toolExecutions) {
      if (execution.toolUseId && execution.browserScreenshotUrl) {
        urls.set(execution.toolUseId, execution.browserScreenshotUrl);
      }
    }
    return urls;
  }, [run.toolExecutions]);
  const getBrowserScreenshotUrl = React.useCallback(
    (toolUseId: string) => screenshotUrlByToolUseId.get(toolUseId) ?? null,
    [screenshotUrlByToolUseId],
  );
  return (
    <ComputerPanel
      runId={run.runId}
      sessionStatus={asRunStatus(run.status)}
      hideHeader
      toolExecutions={toolExecutions}
      getBrowserScreenshotUrl={getBrowserScreenshotUrl}
    />
  );
}

function SharedArtifactsSnapshot({ run }: { run: SharedRunSummary }) {
  const { t } = useT("translation");
  const [selectedPath, setSelectedPath] = React.useState<string | null>(null);
  const files = run.workspaceFiles;
  const selectedFile = React.useMemo(() => {
    if (!selectedPath) return undefined;
    return findFileByPath(files, selectedPath);
  }, [files, selectedPath]);

  React.useEffect(() => {
    setSelectedPath(null);
  }, [run.runId]);

  const handleFileSelect = React.useCallback((file: FileNode) => {
    if (file.type === "file") {
      setSelectedPath(file.path);
    }
  }, []);

  const handleFileChangeClick = React.useCallback(
    (path: string) => {
      const file = findFileByPath(files, path);
      if (file) {
        setSelectedPath(file.path);
      }
    },
    [files],
  );

  const handleDownloadNode = React.useCallback(async (node: FileNode) => {
    if (node.type !== "file" || !node.url) return;
    await downloadFileFromUrl(node.url, node.name);
  }, []);

  if (run.fileChanges.length === 0 && files.length === 0) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-sm text-muted-foreground">
        {t("artifacts.empty.noChanges")}
      </div>
    );
  }

  return (
    <div className="grid h-full min-h-0 grid-cols-[minmax(0,70%)_minmax(0,30%)] overflow-hidden">
      <div className="min-h-0 min-w-0 overflow-hidden border-r border-border/60 bg-background p-3">
        <div className="h-full min-h-0 overflow-hidden rounded-xl border bg-card">
          {selectedFile ? (
            <DocumentViewer file={selectedFile} />
          ) : (
            <FileChangesList
              fileChanges={run.fileChanges}
              sessionStatus={asRunStatus(run.status)}
              onFileClick={handleFileChangeClick}
            />
          )}
        </div>
      </div>
      <div className="min-h-0 min-w-0 overflow-hidden bg-muted/30">
        <FileSidebar
          files={files}
          selectedFile={selectedFile}
          onFileSelect={handleFileSelect}
          embedded
          onDownloadNode={handleDownloadNode}
        />
      </div>
    </div>
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
          <SharedComputerSnapshot run={selectedRun} />
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
