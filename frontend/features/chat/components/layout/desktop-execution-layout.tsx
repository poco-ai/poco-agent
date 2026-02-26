"use client";

import * as React from "react";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { PanelHeader } from "@/components/shared/panel-header";
import { Tabs, TabsContent } from "@/components/ui/tabs";
import { ComputerPanel } from "@/features/chat/components/execution/computer-panel/computer-panel";
import { ArtifactsPanel } from "@/features/chat/components/execution/file-panel/artifacts-panel";
import type { ExecutionSession } from "@/features/chat/types";

interface DesktopExecutionLayoutProps {
  sessionId: string;
  session: ExecutionSession | null;
  rightTab: string;
  onRightTabChange: (value: string) => void;
  isRightPanelCollapsed: boolean;
  chatPanel: React.ReactNode;
  tabsSwitch: React.ReactNode;
  browserEnabled: boolean;
}

export function DesktopExecutionLayout({
  sessionId,
  session,
  rightTab,
  onRightTabChange,
  isRightPanelCollapsed,
  chatPanel,
  tabsSwitch,
  browserEnabled,
}: DesktopExecutionLayoutProps) {
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

        {!isRightPanelCollapsed ? (
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
