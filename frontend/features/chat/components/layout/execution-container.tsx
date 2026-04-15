"use client";

import * as React from "react";
import { ChatPanel } from "../execution/chat-panel/chat-panel";
import { MobileExecutionView } from "./mobile-execution-view";
import { useExecutionSession } from "@/features/chat/hooks/use-execution-session";
import { useTaskHistoryContext } from "@/features/projects/contexts/task-history-context";
import { useIsMobile } from "@/hooks/use-mobile";
import { useT } from "@/lib/i18n/client";
import { ChatPanelSkeleton } from "@/features/chat/components/layout/execution-container-skeletons";
import { ExecutionTabsSwitch } from "@/features/chat/components/layout/execution-tabs-switch";
import { DesktopExecutionLayout } from "@/features/chat/components/layout/desktop-execution-layout";
import { useToolExecutions } from "@/features/chat/components/execution/computer-panel/hooks/use-tool-executions";
import {
  getRunsBySessionAction,
  getToolExecutionsAction,
} from "@/features/chat/actions/query-actions";
import type { RunResponse } from "@/features/chat/types";

interface ExecutionContainerProps {
  sessionId: string;
}

export function ExecutionContainer({ sessionId }: ExecutionContainerProps) {
  const { t } = useT("translation");
  const { refreshTasks } = useTaskHistoryContext();
  const [runs, setRuns] = React.useState<RunResponse[]>([]);
  const [selectedRunId, setSelectedRunId] = React.useState<string | null>(null);
  const [isPinnedToHistory, setIsPinnedToHistory] = React.useState(false);
  const [hasLegacySessionReplay, setHasLegacySessionReplay] =
    React.useState(false);
  const { session, isLoading, error, updateSession } = useExecutionSession({
    sessionId,
    onPollingStop: refreshTasks,
  });
  const isMobile = useIsMobile();
  const isSessionActive =
    session?.status === "running" || session?.status === "pending";
  const browserEnabled = Boolean(
    session?.config_snapshot?.browser_enabled ||
    session?.state_patch?.browser?.enabled,
  );
  const fileChanges = session?.state_patch.workspace_state?.file_changes ?? [];
  const hasLocalMountArtifacts =
    session?.config_snapshot?.filesystem_mode === "local_mount" &&
    (session.config_snapshot.local_mounts?.length ?? 0) > 0;
  const hasArtifacts = fileChanges.length > 0 || hasLocalMountArtifacts;
  const activeRun = React.useMemo(
    () =>
      runs.find((run) =>
        ["queued", "claimed", "running", "canceling"].includes(run.status),
      ) ?? null,
    [runs],
  );
  const latestRun = React.useMemo(
    () => (runs.length > 0 ? runs[runs.length - 1] : null),
    [runs],
  );
  const effectiveSelectedRunId =
    selectedRunId ?? activeRun?.run_id ?? latestRun?.run_id ?? null;
  const selectedRun = React.useMemo(
    () => runs.find((run) => run.run_id === effectiveSelectedRunId) ?? null,
    [effectiveSelectedRunId, runs],
  );
  const { executions, isLoading: isLoadingToolExecutions } = useToolExecutions({
    runId: effectiveSelectedRunId ?? undefined,
    isActive:
      selectedRun?.run_id != null &&
      selectedRun.run_id === activeRun?.run_id &&
      isSessionActive,
    pollingIntervalMs: 2000,
    limit: 1,
  });
  const hasComputerRecords = executions.length > 0 || runs.length > 0;
  const selectedRunFileChanges =
    selectedRun?.state_patch?.workspace_state?.file_changes ?? [];
  const hasSelectedRunWorkspace = Boolean(
    selectedRun?.workspace_manifest_key ||
    selectedRun?.workspace_files_prefix ||
    selectedRun?.workspace_archive_key ||
    selectedRun?.workspace_export_status === "ready",
  );
  const hasAnyRunArtifacts = runs.some(
    (run) =>
      (run.state_patch?.workspace_state?.file_changes?.length ?? 0) > 0 ||
      Boolean(
        run.workspace_manifest_key ||
        run.workspace_files_prefix ||
        run.workspace_archive_key ||
        run.workspace_export_status === "ready",
      ),
  );
  const hasSelectedRunArtifacts =
    selectedRunFileChanges.length > 0 ||
    hasSelectedRunWorkspace ||
    hasLocalMountArtifacts;
  const showArtifactsTab =
    hasSelectedRunArtifacts || hasArtifacts || hasAnyRunArtifacts;
  const legacySessionArtifactsAvailable = Boolean(
    !hasSelectedRunArtifacts &&
    (fileChanges.length > 0 ||
      session?.workspace_export_status === "ready" ||
      hasLocalMountArtifacts),
  );
  const legacySessionReplayAvailable = Boolean(
    effectiveSelectedRunId && executions.length === 0 && hasLegacySessionReplay,
  );
  const showComputerTab = hasComputerRecords || isLoadingToolExecutions;
  const showFilePanel = showArtifactsTab || showComputerTab;

  const defaultRightTab = React.useMemo(() => {
    if (showComputerTab) {
      return "computer";
    }
    if (showArtifactsTab) {
      return "artifacts";
    }
    return "computer";
  }, [showArtifactsTab, showComputerTab]);
  const [rightTab, setRightTab] = React.useState<string>(defaultRightTab);
  const [isRightPanelCollapsed, setIsRightPanelCollapsed] =
    React.useState(false);
  const effectiveRightPanelCollapsed = isRightPanelCollapsed || !showFilePanel;
  const didManualSwitchRef = React.useRef(false);
  const prevDefaultRef = React.useRef<string>(defaultRightTab);
  const lastSessionIdRef = React.useRef<string | null>(null);
  const executionTabsHighlightId = React.useId();

  const loadRuns = React.useCallback(async () => {
    try {
      const data = await getRunsBySessionAction({ sessionId });
      setRuns(data);
    } catch (error) {
      console.error("[ExecutionContainer] Failed to load runs:", error);
    }
  }, [sessionId]);

  // Reset right panel tab when session changes.
  React.useEffect(() => {
    if (lastSessionIdRef.current === sessionId) return;
    lastSessionIdRef.current = sessionId;
    didManualSwitchRef.current = false;
    prevDefaultRef.current = defaultRightTab;
    setRightTab(defaultRightTab);
    setRuns([]);
    setSelectedRunId(null);
    setIsPinnedToHistory(false);
  }, [defaultRightTab, sessionId]);

  React.useEffect(() => {
    void loadRuns();
  }, [loadRuns]);

  React.useEffect(() => {
    let cancelled = false;

    const loadLegacyReplay = async () => {
      try {
        const data = await getToolExecutionsAction({
          sessionId,
          limit: 1,
          offset: 0,
        });
        if (!cancelled) {
          setHasLegacySessionReplay(data.length > 0);
        }
      } catch (error) {
        if (!cancelled) {
          setHasLegacySessionReplay(false);
        }
        console.error(
          "[ExecutionContainer] Failed to load legacy replay availability:",
          error,
        );
      }
    };

    void loadLegacyReplay();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  React.useEffect(() => {
    if (!isSessionActive) return;
    const id = window.setInterval(() => {
      void loadRuns();
    }, 3000);
    return () => window.clearInterval(id);
  }, [isSessionActive, loadRuns]);

  React.useEffect(() => {
    if (!session?.status) return;
    if (!["completed", "failed", "canceled"].includes(session.status)) return;
    void loadRuns();
  }, [loadRuns, session?.status]);

  React.useEffect(() => {
    if (isPinnedToHistory) return;
    const nextRunId = activeRun?.run_id ?? latestRun?.run_id ?? null;
    if (nextRunId && nextRunId !== selectedRunId) {
      setSelectedRunId(nextRunId);
    }
  }, [activeRun?.run_id, isPinnedToHistory, latestRun?.run_id, selectedRunId]);

  // Smart default: switch to artifacts on completion only if user didn't manually switch.
  React.useEffect(() => {
    if (prevDefaultRef.current === defaultRightTab) return;
    prevDefaultRef.current = defaultRightTab;
    if (!didManualSwitchRef.current) {
      setRightTab(defaultRightTab);
    }
  }, [defaultRightTab]);

  React.useEffect(() => {
    if (isMobile) return;
    if (!showFilePanel) return;

    const handleToggleRightPanel = (event: KeyboardEvent) => {
      if (!event.ctrlKey) return;
      if (event.key.toLowerCase() !== "l") return;
      event.preventDefault();
      event.stopPropagation();
      setIsRightPanelCollapsed((prev) => !prev);
    };

    window.addEventListener("keydown", handleToggleRightPanel, true);
    return () => {
      window.removeEventListener("keydown", handleToggleRightPanel, true);
    };
  }, [isMobile, showFilePanel]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex h-dvh min-h-0 min-w-0 overflow-hidden bg-background select-text">
        <div className="h-full w-full min-h-0 min-w-0 overflow-hidden">
          <ChatPanelSkeleton />
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-dvh bg-background select-text">
        <div className="text-center">
          <p className="text-destructive mb-2">
            {t("chat.errors.loadSession", "Error loading session")}
          </p>
          <p className="text-muted-foreground text-sm">
            {error.message || t("common.unknownError", "Unknown error")}
          </p>
        </div>
      </div>
    );
  }

  // Mobile view (under 768px)
  if (isMobile) {
    return (
      <MobileExecutionView
        session={session}
        sessionId={sessionId}
        runs={runs}
        selectedRunId={effectiveSelectedRunId ?? undefined}
        legacySessionReplayAvailable={legacySessionReplayAvailable}
        legacySessionArtifactsAvailable={legacySessionArtifactsAvailable}
        onSelectRun={(runId) => {
          setSelectedRunId(runId);
          setIsPinnedToHistory(runId !== activeRun?.run_id);
        }}
        updateSession={updateSession}
        showArtifactsTab={showArtifactsTab}
        showComputerTab={showComputerTab}
      />
    );
  }

  const tabsSwitch = (
    <ExecutionTabsSwitch
      rightTab={rightTab}
      highlightId={executionTabsHighlightId}
      showArtifactsTab={showArtifactsTab}
      showComputerTab={showComputerTab}
    />
  );

  const chatPanel = (
    <ChatPanel
      session={session}
      statePatch={session?.state_patch}
      progress={session?.progress}
      currentStep={session?.state_patch.current_step ?? undefined}
      updateSession={updateSession}
      showRightPanelToggle
      isRightPanelToggleDisabled={!showFilePanel}
      isRightPanelCollapsed={effectiveRightPanelCollapsed}
      onToggleRightPanel={
        showFilePanel
          ? () => setIsRightPanelCollapsed((collapsed) => !collapsed)
          : undefined
      }
    />
  );

  return (
    <DesktopExecutionLayout
      sessionId={sessionId}
      session={session}
      runs={runs}
      selectedRunId={effectiveSelectedRunId ?? undefined}
      selectedRun={selectedRun}
      legacySessionReplayAvailable={legacySessionReplayAvailable}
      legacySessionArtifactsAvailable={legacySessionArtifactsAvailable}
      onSelectRun={(runId) => {
        setSelectedRunId(runId);
        setIsPinnedToHistory(runId !== activeRun?.run_id);
      }}
      onFollowCurrentRun={() => {
        const currentRunId = activeRun?.run_id ?? latestRun?.run_id ?? null;
        setSelectedRunId(currentRunId);
        setIsPinnedToHistory(false);
      }}
      isViewingHistory={Boolean(
        selectedRun?.run_id &&
        activeRun?.run_id &&
        selectedRun.run_id !== activeRun.run_id,
      )}
      rightTab={rightTab}
      onRightTabChange={(value) => {
        didManualSwitchRef.current = true;
        setRightTab(value);
      }}
      isRightPanelCollapsed={effectiveRightPanelCollapsed}
      showRightPanel={showFilePanel}
      showArtifactsTab={showArtifactsTab}
      showComputerTab={showComputerTab}
      chatPanel={chatPanel}
      tabsSwitch={tabsSwitch}
      browserEnabled={browserEnabled}
      selectedRunFileChanges={selectedRunFileChanges}
    />
  );
}
