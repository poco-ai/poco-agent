"use client";

import * as React from "react";
import { ChatPanel } from "../execution/chat-panel/chat-panel";
import { MobileExecutionView } from "./mobile-execution-view";
import { useExecutionSession } from "@/features/chat/hooks/use-execution-session";
import { useTaskHistoryContext } from "@/features/projects/contexts/task-history-context";
import { useIsMobile } from "@/hooks/use-mobile";

import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { useT } from "@/lib/i18n/client";
import {
  ChatPanelSkeleton,
  RightPanelSkeleton,
} from "@/features/chat/components/layout/execution-container-skeletons";
import { ExecutionTabsSwitch } from "@/features/chat/components/layout/execution-tabs-switch";
import { DesktopExecutionLayout } from "@/features/chat/components/layout/desktop-execution-layout";

interface ExecutionContainerProps {
  sessionId: string;
}

export function ExecutionContainer({ sessionId }: ExecutionContainerProps) {
  const { t } = useT("translation");
  const { refreshTasks } = useTaskHistoryContext();
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

  const defaultRightTab = isSessionActive ? "computer" : "artifacts";
  const [rightTab, setRightTab] = React.useState<string>(defaultRightTab);
  const [isRightPanelCollapsed, setIsRightPanelCollapsed] =
    React.useState(false);
  const didManualSwitchRef = React.useRef(false);
  const prevDefaultRef = React.useRef<string>(defaultRightTab);
  const lastSessionIdRef = React.useRef<string | null>(null);
  const executionTabsHighlightId = React.useId();

  // Reset right panel tab when session changes.
  React.useEffect(() => {
    if (lastSessionIdRef.current === sessionId) return;
    lastSessionIdRef.current = sessionId;
    didManualSwitchRef.current = false;
    prevDefaultRef.current = defaultRightTab;
    setRightTab(defaultRightTab);
  }, [defaultRightTab, sessionId]);

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
  }, [isMobile]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex h-dvh min-h-0 min-w-0 overflow-hidden bg-background select-text">
        <ResizablePanelGroup direction="horizontal" className="min-h-0 min-w-0">
          <ResizablePanel
            defaultSize={45}
            minSize={30}
            className="min-h-0 min-w-0 overflow-hidden"
          >
            <ChatPanelSkeleton />
          </ResizablePanel>

          <ResizableHandle withHandle />

          <ResizablePanel
            defaultSize={55}
            minSize={30}
            className="min-h-0 min-w-0 overflow-hidden"
          >
            <RightPanelSkeleton />
          </ResizablePanel>
        </ResizablePanelGroup>
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
        updateSession={updateSession}
      />
    );
  }

  const tabsSwitch = (
    <ExecutionTabsSwitch
      rightTab={rightTab}
      isSessionActive={isSessionActive}
      sessionStatus={session?.status}
      highlightId={executionTabsHighlightId}
    />
  );

  const chatPanel = (
    <ChatPanel
      session={session}
      statePatch={session?.state_patch}
      progress={session?.progress}
      currentStep={session?.state_patch.current_step ?? undefined}
      updateSession={updateSession}
      isRightPanelCollapsed={isRightPanelCollapsed}
      onToggleRightPanel={() =>
        setIsRightPanelCollapsed((collapsed) => !collapsed)
      }
    />
  );

  return (
    <DesktopExecutionLayout
      sessionId={sessionId}
      session={session}
      rightTab={rightTab}
      onRightTabChange={(value) => {
        didManualSwitchRef.current = true;
        setRightTab(value);
      }}
      isRightPanelCollapsed={isRightPanelCollapsed}
      chatPanel={chatPanel}
      tabsSwitch={tabsSwitch}
      browserEnabled={browserEnabled}
    />
  );
}
