"use client";

import * as React from "react";
import { Swiper, SwiperSlide } from "swiper/react";
import { Navigation } from "swiper/modules";
import type { Swiper as SwiperType } from "swiper";
import "swiper/css";
import "swiper/css/navigation";
import { useSidebar } from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { ChatPanel } from "../execution/chat-panel/chat-panel";
import { ArtifactsPanel } from "../execution/file-panel/artifacts-panel";
import { ComputerPanel } from "../execution/computer-panel/computer-panel";
import type { ExecutionSession, RunResponse } from "@/features/chat/types";
import { useT } from "@/lib/i18n/client";
import {
  Ellipsis,
  Layers,
  MessageSquare,
  Monitor,
  PanelLeft,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { MobileRunTimeline } from "./mobile-run-timeline";
import { MobileRunSheet } from "./mobile-run-sheet";

interface MobileExecutionViewProps {
  session: ExecutionSession | null;
  sessionId?: string;
  runs: RunResponse[];
  selectedRunId?: string;
  currentRunId?: string;
  isViewingHistory: boolean;
  legacySessionReplayAvailable?: boolean;
  legacySessionArtifactsAvailable?: boolean;
  onSelectRun: (runId: string) => void;
  onFollowCurrentRun: () => void;
  updateSession: (newSession: Partial<ExecutionSession>) => void;
  showArtifactsTab: boolean;
  showComputerTab: boolean;
}

export function MobileExecutionView({
  session,
  sessionId,
  runs,
  selectedRunId,
  currentRunId,
  isViewingHistory,
  legacySessionReplayAvailable = false,
  legacySessionArtifactsAvailable = false,
  onSelectRun,
  onFollowCurrentRun,
  updateSession,
  showArtifactsTab,
  showComputerTab,
}: MobileExecutionViewProps) {
  const { t } = useT("translation");
  const { setOpenMobile } = useSidebar();
  const [activeIndex, setActiveIndex] = React.useState(0);
  const [hasFooterSelection, setHasFooterSelection] = React.useState(false);
  const [runSheetOpen, setRunSheetOpen] = React.useState(false);
  const swiperRef = React.useRef<SwiperType | null>(null);
  const browserEnabled = Boolean(
    session?.config_snapshot?.browser_enabled ||
    session?.state_patch?.browser?.enabled,
  );
  const selectedRun =
    runs.find((run) => run.run_id === selectedRunId) ?? runs.at(-1) ?? null;
  const selectedRunIndex = selectedRunId
    ? runs.findIndex((run) => run.run_id === selectedRunId)
    : -1;
  const selectedRunFileChanges =
    selectedRun?.state_patch?.workspace_state?.file_changes ?? [];
  const panelStatus = (selectedRun?.status ?? session?.status) as
    | "queued"
    | "claimed"
    | "pending"
    | "running"
    | "canceling"
    | "completed"
    | "failed"
    | "canceled"
    | undefined;

  const extraPanels = React.useMemo(
    () => [
      ...(showComputerTab
        ? [
            {
              key: "computer" as const,
              label: t("mobile.computer"),
              icon: Monitor,
            },
          ]
        : []),
      ...(showArtifactsTab
        ? [
            {
              key: "artifacts" as const,
              label: t("mobile.artifacts"),
              icon: Layers,
            },
          ]
        : []),
    ],
    [showArtifactsTab, showComputerTab, t],
  );
  const showFilePanel = extraPanels.length > 0;

  React.useEffect(() => {
    setActiveIndex(0);
    setHasFooterSelection(true);

    if (swiperRef.current && swiperRef.current.activeIndex !== 0) {
      swiperRef.current.slideTo(0, 0);
    }
  }, [extraPanels.length, sessionId]);

  const footerTabs = [
    {
      label: t("mobile.chat"),
      icon: MessageSquare,
      index: 0,
    },
    ...extraPanels.map((panel, index) => ({
      ...panel,
      index: index + 1,
    })),
  ] as const;

  return (
    <div className="flex h-full w-full select-text flex-col overflow-hidden">
      <div className="z-50 shrink-0 border-b bg-background px-3 py-2">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setOpenMobile(true)}
            aria-label={t("sidebar.openMain")}
            title={t("sidebar.openMain")}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-border/60 bg-background text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <PanelLeft className="size-4" />
          </button>

          {showFilePanel ? (
            <>
              <MobileRunTimeline
                runs={runs}
                selectedRunId={selectedRunId}
                onSelectRun={onSelectRun}
              />
              {runs.length > 1 ? (
                <Button
                  type="button"
                  variant="outline"
                  size="icon-sm"
                  className="h-8 w-8 shrink-0 rounded-full"
                  aria-label={t("mobile.runs.openAll")}
                  title={t("mobile.runs.openAll")}
                  onClick={() => setRunSheetOpen(true)}
                >
                  <Ellipsis className="size-4" />
                </Button>
              ) : null}
            </>
          ) : null}
        </div>

        {showFilePanel ? (
          <div className="mt-2 space-y-2">
            {isViewingHistory && selectedRunIndex >= 0 ? (
              <div className="flex items-center gap-2 rounded-full border border-primary/15 bg-primary/10 px-2 py-1 text-xs text-muted-foreground">
                <span className="min-w-0 flex-1 truncate">
                  {t("mobile.runs.viewingHistory", {
                    number: selectedRunIndex + 1,
                  })}
                </span>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-6 rounded-full px-2 text-xs text-primary"
                  onClick={onFollowCurrentRun}
                >
                  {t("mobile.runs.backToCurrent")}
                </Button>
              </div>
            ) : null}

            <div className="relative min-w-0 rounded-full border border-border/60 bg-muted/60 p-1 font-serif">
              <div
                className={cn(
                  "pointer-events-none absolute inset-y-1 left-1 rounded-full border border-primary/30 bg-primary shadow-sm transition-[transform,opacity] duration-300 ease-out",
                  hasFooterSelection ? "opacity-100" : "opacity-0",
                )}
                style={{
                  width: `calc((100% - 0.5rem) / ${footerTabs.length})`,
                  transform: `translateX(${activeIndex * 100}%)`,
                }}
              />

              <div
                className="relative grid"
                style={{
                  gridTemplateColumns: `repeat(${footerTabs.length}, minmax(0, 1fr))`,
                }}
              >
                {footerTabs.map((tab) => {
                  const Icon = tab.icon;
                  const isActive = activeIndex === tab.index;

                  return (
                    <button
                      key={tab.index}
                      type="button"
                      onClick={() => {
                        setHasFooterSelection(true);
                        swiperRef.current?.slideTo(tab.index);
                      }}
                      className={cn(
                        "z-10 flex h-8 flex-row items-center justify-center gap-1.5 rounded-full px-2 transition-colors",
                        isActive
                          ? "font-semibold text-primary-foreground"
                          : "text-muted-foreground",
                      )}
                    >
                      <Icon className="size-4" />
                      <span className="text-xs font-medium leading-none">
                        {tab.label}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        ) : null}
      </div>

      <div className="min-h-0 flex-1">
        {showFilePanel ? (
          <Swiper
            modules={[Navigation]}
            spaceBetween={0}
            slidesPerView={1}
            allowTouchMove
            className="h-full"
            onSlideChange={(swiper) => {
              setActiveIndex(swiper.activeIndex);
              setHasFooterSelection(true);
            }}
            onSwiper={(swiper) => {
              swiperRef.current = swiper;
            }}
          >
            <SwiperSlide className="h-full">
              <div
                className={cn(
                  "h-full",
                  activeIndex === 0 ? "bg-background" : "bg-muted/50",
                )}
              >
                <ChatPanel
                  session={session}
                  statePatch={session?.state_patch}
                  progress={session?.progress}
                  currentStep={session?.state_patch.current_step ?? undefined}
                  updateSession={updateSession}
                  onIconClick={() => setOpenMobile(true)}
                  hideHeader
                />
              </div>
            </SwiperSlide>
            {extraPanels.map((panel, index) => (
              <SwiperSlide key={panel.key} className="h-full">
                <div
                  className={cn(
                    "h-full",
                    activeIndex === index + 1 ? "bg-background" : "bg-muted/50",
                  )}
                >
                  {panel.key === "computer" ? (
                    sessionId ? (
                      <ComputerPanel
                        runId={selectedRunId}
                        legacySessionReplayAvailable={
                          legacySessionReplayAvailable
                        }
                        sessionStatus={panelStatus}
                        browserEnabled={browserEnabled}
                        hideHeader
                      />
                    ) : null
                  ) : (
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
                  )}
                </div>
              </SwiperSlide>
            ))}
          </Swiper>
        ) : (
          <ChatPanel
            session={session}
            statePatch={session?.state_patch}
            progress={session?.progress}
            currentStep={session?.state_patch.current_step ?? undefined}
            updateSession={updateSession}
            onIconClick={() => setOpenMobile(true)}
            hideHeader
          />
        )}
      </div>

      <MobileRunSheet
        open={runSheetOpen}
        onOpenChange={setRunSheetOpen}
        runs={runs}
        selectedRunId={selectedRunId}
        currentRunId={currentRunId}
        onSelectRun={onSelectRun}
        onFollowCurrentRun={onFollowCurrentRun}
      />
    </div>
  );
}
