"use client";

import * as React from "react";
import { Swiper, SwiperSlide } from "swiper/react";
import { Navigation } from "swiper/modules";
import type { Swiper as SwiperType } from "swiper";
import "swiper/css";
import "swiper/css/navigation";
import { useSidebar } from "@/components/ui/sidebar";
import { ChatPanel } from "../execution/chat-panel/chat-panel";
import { ArtifactsPanel } from "../execution/file-panel/artifacts-panel";
import { ComputerPanel } from "../execution/computer-panel/computer-panel";
import type {
  DeliverableResponse,
  DeliverableVersionResponse,
  ExecutionSession,
} from "@/features/chat/types";
import { useT } from "@/lib/i18n/client";
import { MessageSquare, Layers, Monitor, PanelLeft } from "lucide-react";
import { cn } from "@/lib/utils";

interface MobileExecutionViewProps {
  session: ExecutionSession | null;
  sessionId?: string;
  updateSession: (newSession: Partial<ExecutionSession>) => void;
  showArtifactsTab: boolean;
  showComputerTab: boolean;
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

export function MobileExecutionView({
  session,
  sessionId,
  updateSession,
  showArtifactsTab,
  showComputerTab,
  deliverables,
  versionMap,
  selectedDeliverableId,
  selectedDeliverableVersionId,
  processMode,
  onSelectDeliverable,
  onProcessModeChange,
  onOpenDeliverablePreview,
  onOpenDeliverableProcess,
}: MobileExecutionViewProps) {
  const { t } = useT("translation");
  const { setOpenMobile } = useSidebar();
  const [activeIndex, setActiveIndex] = React.useState(0);
  const [hasFooterSelection, setHasFooterSelection] = React.useState(false);
  const swiperRef = React.useRef<SwiperType | null>(null);
  const browserEnabled = Boolean(
    session?.config_snapshot?.browser_enabled ||
    session?.state_patch?.browser?.enabled,
  );

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
      <div className="z-50 shrink-0 border-b bg-background px-3 py-1.5">
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
            <div className="relative min-w-0 flex-1 rounded-full border border-border/60 bg-muted/60 p-1 font-serif">
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
          ) : null}
        </div>
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
                    ) : null
                  ) : (
                    <ArtifactsPanel
                      fileChanges={
                        session?.state_patch.workspace_state?.file_changes
                      }
                      sessionId={sessionId}
                      sessionStatus={session?.status}
                      deliverables={deliverables}
                      versionMap={versionMap}
                      selectedDeliverableId={selectedDeliverableId}
                      onSelectDeliverable={onSelectDeliverable}
                      onOpenDeliverablePreview={onOpenDeliverablePreview}
                      onOpenDeliverableProcess={onOpenDeliverableProcess}
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
    </div>
  );
}
