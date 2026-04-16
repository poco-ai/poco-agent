"use client";

import * as React from "react";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { PanelHeader } from "@/components/shared/panel-header";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent } from "@/components/ui/tabs";
import { ComputerPanel } from "@/features/chat/components/execution/computer-panel/computer-panel";
import { ArtifactsPanel } from "@/features/chat/components/execution/file-panel/artifacts-panel";
import { RunEvolutionTimeline } from "@/features/chat/components/layout/run-evolution-timeline";
import type {
  ExecutionSession,
  FileChange,
  RunResponse,
} from "@/features/chat/types";
import { useT } from "@/lib/i18n/client";
import { Button } from "@/components/ui/button";

interface DesktopExecutionLayoutProps {
  sessionId: string;
  session: ExecutionSession | null;
  runs: RunResponse[];
  selectedRunId?: string;
  selectedRun: RunResponse | null;
  selectedRunFileChanges?: FileChange[];
  legacySessionReplayAvailable?: boolean;
  legacySessionArtifactsAvailable?: boolean;
  onSelectRun: (runId: string) => void;
  onFollowCurrentRun: () => void;
  isViewingHistory: boolean;
  rightTab: string;
  onRightTabChange: (value: string) => void;
  isRightPanelCollapsed: boolean;
  showRightPanel: boolean;
  showArtifactsTab: boolean;
  showComputerTab: boolean;
  chatPanel: React.ReactNode;
  tabsSwitch: React.ReactNode;
  browserEnabled: boolean;
}

type PanelStatus =
  | "queued"
  | "claimed"
  | "pending"
  | "running"
  | "canceling"
  | "completed"
  | "failed"
  | "canceled";

export function DesktopExecutionLayout({
  sessionId,
  session,
  runs,
  selectedRunId,
  selectedRun,
  selectedRunFileChanges,
  legacySessionReplayAvailable = false,
  legacySessionArtifactsAvailable = false,
  onSelectRun,
  onFollowCurrentRun,
  isViewingHistory,
  rightTab,
  onRightTabChange,
  isRightPanelCollapsed,
  showRightPanel,
  showArtifactsTab,
  showComputerTab,
  chatPanel,
  tabsSwitch,
  browserEnabled,
}: DesktopExecutionLayoutProps) {
  const { t } = useT("translation");
  const panelStatus = (selectedRun?.status ?? session?.status) as
    | PanelStatus
    | undefined;
  const isComputerLive =
    showComputerTab &&
    rightTab === "computer" &&
    (selectedRun?.status === "running" ||
      selectedRun?.status === "pending" ||
      selectedRun?.status === "queued" ||
      selectedRun?.status === "claimed" ||
      selectedRun?.status === "canceling");

  return (
    <div className="flex h-dvh min-h-0 min-w-0 overflow-hidden bg-background select-text">
      <ResizablePanelGroup direction="horizontal" className="min-h-0 min-w-0">
        <ResizablePanel
          defaultSize={45}
          minSize={30}
          className="min-h-0 min-w-0 overflow-hidden"
        >
          <div className="h-full w-full min-h-0 min-w-0 flex flex-col overflow-hidden">
            {chatPanel}
          </div>
        </ResizablePanel>

        {showRightPanel && !isRightPanelCollapsed ? (
          <>
            <ResizableHandle withHandle />
            <ResizablePanel
              defaultSize={55}
              minSize={30}
              className="min-h-0 min-w-0 overflow-hidden"
            >
              <div className="h-full w-full min-h-0 min-w-0 flex flex-col overflow-hidden bg-muted/30">
                <Tabs
                  value={rightTab}
                  onValueChange={onRightTabChange}
                  className="h-full min-h-0 flex flex-col"
                >
                  <PanelHeader
                    content={
                      <div className="flex min-w-0 items-center gap-2 overflow-hidden">
                        {tabsSwitch}
                      </div>
                    }
                    action={
                      <div className="flex items-center gap-2">
                        {isViewingHistory ? (
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={onFollowCurrentRun}
                          >
                            {t("computer.replay.liveLabel")}
                          </Button>
                        ) : null}
                        {isComputerLive ? (
                          <Badge
                            variant="outline"
                            className="h-6 items-center gap-1.5 rounded-full border-primary/15 bg-primary/10 px-2.5 text-[11px] font-semibold text-primary"
                            aria-label={t("computer.status.live")}
                            title={t("computer.status.live")}
                          >
                            <span className="relative flex size-2 shrink-0">
                              <span
                                aria-hidden
                                className="absolute inset-0 rounded-full bg-primary/25 motion-safe:animate-ping"
                              />
                              <span
                                aria-hidden
                                className="relative size-2 rounded-full bg-primary"
                              />
                            </span>
                            <span>{t("computer.replay.liveLabel")}</span>
                          </Badge>
                        ) : selectedRun ? (
                          <Badge variant="outline" className="h-6 rounded-full">
                            {selectedRun.status}
                          </Badge>
                        ) : null}
                      </div>
                    }
                  />
                  <RunEvolutionTimeline
                    runs={runs}
                    selectedRunId={selectedRunId}
                    onSelectRun={onSelectRun}
                  />
                  <div className="flex-1 min-h-0 overflow-hidden">
                    {showComputerTab ? (
                      <TabsContent
                        value="computer"
                        className="h-full min-h-0 data-[state=inactive]:hidden"
                      >
                        <ComputerPanel
                          runId={selectedRunId}
                          legacySessionReplayAvailable={
                            legacySessionReplayAvailable
                          }
                          sessionStatus={panelStatus}
                          browserEnabled={browserEnabled}
                          hideHeader
                        />
                      </TabsContent>
                    ) : null}
                    {showArtifactsTab ? (
                      <TabsContent
                        value="artifacts"
                        className="h-full min-h-0 data-[state=inactive]:hidden"
                      >
                        <ArtifactsPanel
                          fileChanges={selectedRunFileChanges}
                          sessionId={sessionId}
                          runId={selectedRunId}
                          legacySessionArtifactsAvailable={
                            legacySessionArtifactsAvailable
                          }
                          sessionStatus={panelStatus}
                          hideHeader
                        />
                      </TabsContent>
                    ) : null}
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
