"use client";

import * as React from "react";
import { motion } from "motion/react";
import { ChatPanel } from "../execution/chat-panel/chat-panel";
import { ArtifactsPanel } from "../execution/file-panel/artifacts-panel";
import { ComputerPanel } from "../execution/computer-panel/computer-panel";
import { MobileExecutionView } from "./mobile-execution-view";
import { useExecutionSession } from "@/features/chat/hooks/use-execution-session";
import { useTaskHistoryContext } from "@/features/projects/contexts/task-history-context";
import { useIsMobile } from "@/hooks/use-mobile";
import { Layers, Monitor, MessageSquare } from "lucide-react";

import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PanelHeader } from "@/components/shared/panel-header";
import { ChatInput } from "../execution/chat-panel/chat-input";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";
import { SkeletonCircle, SkeletonItem } from "@/components/ui/skeleton-shimmer";

interface ExecutionContainerProps {
  sessionId: string;
}

const shimmerDelay = (index: number) => ({
  animationDelay: `${index * 0.08}s`,
});

function ChatPanelSkeleton() {
  const { t } = useT("translation");
  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      <PanelHeader
        icon={MessageSquare}
        title={t("chat.executionTitle")}
        description={t("chat.emptyStateDesc")}
      />
      <div className="flex-1 min-h-0 overflow-hidden px-4">
        <div
          className="flex h-full w-full flex-col gap-4 py-6"
          aria-busy="true"
        >
          <div className="flex items-start gap-3">
            <SkeletonCircle className="h-8 w-8" style={shimmerDelay(0)} />
            <SkeletonItem className="w-[70%]" style={shimmerDelay(1)} />
          </div>
          <div className="flex items-start justify-end">
            <SkeletonItem className="w-[68%]" style={shimmerDelay(2)} />
          </div>
          <div className="flex items-start gap-3">
            <SkeletonCircle className="h-8 w-8" style={shimmerDelay(3)} />
            <SkeletonItem className="w-[60%]" style={shimmerDelay(4)} />
          </div>
          <div className="flex items-start justify-end">
            <SkeletonItem className="w-[55%]" style={shimmerDelay(5)} />
          </div>
        </div>
      </div>
      <ChatInput onSend={() => undefined} disabled />
    </div>
  );
}

function RightPanelSkeleton() {
  const { t } = useT("translation");
  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden bg-muted/30">
      <PanelHeader
        content={
          <Tabs defaultValue="computer" className="min-w-0">
            <TabsList className="min-w-0 max-w-full overflow-hidden font-serif">
              <TabsTrigger value="computer" className="!flex-none min-w-0 px-2">
                <Monitor className="size-4" />
                <span className="whitespace-nowrap">
                  {t("mobile.computer")}
                </span>
              </TabsTrigger>
              <TabsTrigger
                value="artifacts"
                className="!flex-none min-w-0 px-2"
              >
                <Layers className="size-4" />
                <span className="whitespace-nowrap">
                  {t("mobile.artifacts")}
                </span>
              </TabsTrigger>
            </TabsList>
          </Tabs>
        }
      />
      <div className="flex-1 min-h-0 overflow-hidden p-3 sm:p-4">
        <div className="flex h-full flex-col gap-3">
          <div className="flex-1 min-h-0 overflow-hidden rounded-xl border bg-card p-4">
            <SkeletonItem
              className="h-full w-full min-h-0"
              style={shimmerDelay(0)}
            />
          </div>
          <SkeletonItem
            className="h-10 min-h-0 w-full"
            style={shimmerDelay(1)}
          />
          <div className="h-[220px] min-w-0 overflow-hidden rounded-xl border bg-card p-3">
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, index) => (
                <SkeletonItem
                  key={`timeline-skeleton-${index}`}
                  className="h-10 min-h-0 w-full rounded-md px-2 py-2"
                  style={shimmerDelay(index + 2)}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
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
          <p className="text-destructive mb-2">Error loading session</p>
          <p className="text-muted-foreground text-sm">
            {error.message || "Unknown error"}
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

  // Desktop resizable layout — sliding pill animation (same as home ModeToggle)
  const tabsSwitch = (
    <TabsList className="min-w-0 max-w-full overflow-hidden font-serif">
      <TabsTrigger
        value="computer"
        asChild
        className="!flex-none min-w-0 border-transparent data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:border-transparent"
      >
        <button
          type="button"
          className={cn(
            "relative inline-flex h-[calc(100%-1px)] flex-1 min-w-0 items-center justify-center gap-1.5 rounded-md px-2 py-1 text-sm font-medium whitespace-nowrap transition-colors focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:ring-offset-1",
            rightTab === "computer"
              ? "text-primary-foreground"
              : "text-muted-foreground",
          )}
        >
          {rightTab === "computer" ? (
            <motion.div
              layoutId={`execution-tabs-${executionTabsHighlightId}`}
              className="absolute inset-0 rounded-md bg-primary shadow-sm"
              transition={{ type: "spring", stiffness: 440, damping: 40 }}
            />
          ) : null}
          <Monitor className="relative z-10 size-4 shrink-0" />
          <span className="relative z-10 truncate">{t("mobile.computer")}</span>
          {session?.status && isSessionActive ? (
            <span
              className="relative z-10 ml-1 inline-flex shrink-0"
              aria-label={t("computer.status.live")}
              title={t("computer.status.live")}
            >
              <span
                aria-hidden
                className="size-2 rounded-full bg-primary-foreground/80 motion-safe:animate-pulse"
              />
            </span>
          ) : null}
        </button>
      </TabsTrigger>
      <TabsTrigger
        value="artifacts"
        asChild
        className="!flex-none min-w-0 border-transparent data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:border-transparent"
      >
        <button
          type="button"
          className={cn(
            "relative inline-flex h-[calc(100%-1px)] flex-1 min-w-0 items-center justify-center gap-1.5 rounded-md px-2 py-1 text-sm font-medium whitespace-nowrap transition-colors focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:ring-offset-1",
            rightTab === "artifacts"
              ? "text-primary-foreground"
              : "text-muted-foreground",
          )}
        >
          {rightTab === "artifacts" ? (
            <motion.div
              layoutId={`execution-tabs-${executionTabsHighlightId}`}
              className="absolute inset-0 rounded-md bg-primary shadow-sm"
              transition={{ type: "spring", stiffness: 440, damping: 40 }}
            />
          ) : null}
          <Layers className="relative z-10 size-4 shrink-0" />
          <span className="relative z-10 truncate">
            {t("mobile.artifacts")}
          </span>
        </button>
      </TabsTrigger>
    </TabsList>
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
    <div className="flex h-dvh min-h-0 min-w-0 overflow-hidden bg-background select-text">
      <ResizablePanelGroup direction="horizontal" className="min-h-0 min-w-0">
        {/* Left panel - Chat with status cards (45%) */}
        <ResizablePanel
          defaultSize={45}
          minSize={30}
          className="min-h-0 min-w-0 overflow-hidden"
        >
          <div className="h-full w-full min-h-0 min-w-0 flex flex-col overflow-hidden">
            {chatPanel}
          </div>
        </ResizablePanel>

        {!isRightPanelCollapsed ? (
          <>
            <ResizableHandle withHandle />

            {/* Right panel - Artifacts (55%) */}
            <ResizablePanel
              defaultSize={55}
              minSize={30}
              className="min-h-0 min-w-0 overflow-hidden"
            >
              <div className="h-full w-full min-h-0 min-w-0 flex flex-col overflow-hidden bg-muted/30">
                <Tabs
                  value={rightTab}
                  onValueChange={(value) => {
                    didManualSwitchRef.current = true;
                    setRightTab(value);
                  }}
                  className="h-full min-h-0 flex flex-col"
                >
                  <PanelHeader
                    content={
                      <div className="flex min-w-0 items-center overflow-hidden">
                        {tabsSwitch}
                      </div>
                    }
                  />
                  <div className="flex-1 min-h-0 overflow-hidden">
                    <TabsContent
                      value="computer"
                      className="h-full min-h-0 data-[state=inactive]:hidden"
                    >
                      <ComputerPanel
                        sessionId={sessionId}
                        sessionStatus={session?.status}
                        browserEnabled={browserEnabled}
                        hideHeader
                      />
                    </TabsContent>
                    <TabsContent
                      value="artifacts"
                      className="h-full min-h-0 data-[state=inactive]:hidden"
                    >
                      <ArtifactsPanel
                        fileChanges={
                          session?.state_patch.workspace_state?.file_changes
                        }
                        sessionId={sessionId}
                        sessionStatus={session?.status}
                        hideHeader
                      />
                    </TabsContent>
                  </div>
                </Tabs>
              </div>
            </ResizablePanel>
          </>
        ) : null}
      </ResizablePanelGroup>
    </div>
  );
}
