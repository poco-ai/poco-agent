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
import type {
  DeliverableResponse,
  DeliverableVersionResponse,
  ExecutionSession,
} from "@/features/chat/types";
import { useT } from "@/lib/i18n/client";

interface DesktopExecutionLayoutProps {
  sessionId: string;
  session: ExecutionSession | null;
  rightTab: string;
  onRightTabChange: (value: string) => void;
  isRightPanelCollapsed: boolean;
  showRightPanel: boolean;
  showArtifactsTab: boolean;
  showComputerTab: boolean;
  chatPanel: React.ReactNode;
  tabsSwitch: React.ReactNode;
  browserEnabled: boolean;
  deliverables: DeliverableResponse[];
  versionMap: Record<string, DeliverableVersionResponse>;
  selectedDeliverableId: string | null;
  selectedDeliverableVersionId: string | null;
  processMode: "deliverable" | "session";
  onSelectDeliverable: (
    deliverableId: string,
    versionId: string | null,
  ) => void;
  onProcessModeChange: (mode: "deliverable" | "session") => void;
  onOpenDeliverablePreview: (deliverableId: string, versionId: string) => void;
  onOpenDeliverableProcess: (deliverableId: string, versionId: string) => void;
}

export function DesktopExecutionLayout({
  sessionId,
  session,
  rightTab,
  onRightTabChange,
  isRightPanelCollapsed,
  showRightPanel,
  showArtifactsTab,
  showComputerTab,
  chatPanel,
  tabsSwitch,
  browserEnabled,
  deliverables,
  versionMap,
  selectedDeliverableId,
  selectedDeliverableVersionId,
  processMode,
  onSelectDeliverable,
  onProcessModeChange,
  onOpenDeliverablePreview,
  onOpenDeliverableProcess,
}: DesktopExecutionLayoutProps) {
  const { t } = useT("translation");
  const isComputerLive =
    showComputerTab &&
    rightTab === "computer" &&
    (session?.status === "running" || session?.status === "pending");

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
                      <div className="flex min-w-0 items-center overflow-hidden">
                        {tabsSwitch}
                      </div>
                    }
                    action={
                      isComputerLive ? (
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
                      ) : undefined
                    }
                  />
                  <div className="flex-1 min-h-0 overflow-hidden">
                    {showComputerTab ? (
                      <TabsContent
                        value="computer"
                        className="h-full min-h-0 data-[state=inactive]:hidden"
                      >
                        <ComputerPanel
                          sessionId={sessionId}
                          sessionStatus={session?.status}
                          browserEnabled={browserEnabled}
                          selectedDeliverableVersionId={
                            selectedDeliverableVersionId
                          }
                          processMode={processMode}
                          onProcessModeChange={onProcessModeChange}
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
                          fileChanges={
                            session?.state_patch.workspace_state?.file_changes
                          }
                          sessionId={sessionId}
                          sessionStatus={session?.status}
                          workspaceExportStatus={session?.workspace_export_status}
                          deliverables={deliverables}
                          versionMap={versionMap}
                          selectedDeliverableId={selectedDeliverableId}
                          onSelectDeliverable={onSelectDeliverable}
                          onOpenDeliverablePreview={onOpenDeliverablePreview}
                          onOpenDeliverableProcess={onOpenDeliverableProcess}
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
