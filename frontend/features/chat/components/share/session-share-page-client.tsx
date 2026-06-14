"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Swiper, SwiperSlide } from "swiper/react";
import { Navigation } from "swiper/modules";
import type { Swiper as SwiperType } from "swiper";
import "swiper/css";
import "swiper/css/navigation";
import {
  ArrowUp,
  Ellipsis,
  GitFork,
  Layers,
  Loader2,
  LockKeyhole,
  MessageSquare,
  Monitor,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PanelHeader } from "@/components/shared/panel-header";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { Skeleton } from "@/components/ui/skeleton";
import { ChatMessageList } from "@/features/chat/components/chat/chat-message-list";
import {
  mapSharedRunToRunResponse,
  SessionShareExecutionPanel,
  SharedArtifactsSnapshot,
  SharedComputerSnapshot,
} from "@/features/chat/components/share/session-share-execution-panel";
import { MobileRunSheet } from "@/features/chat/components/layout/mobile-run-sheet";
import { MobileRunTimeline } from "@/features/chat/components/layout/mobile-run-timeline";
import { sessionShareApi } from "@/features/chat/api/session-share-api";
import { parseMessages } from "@/features/chat/services/message-parser";
import type { ChatMessage, SessionShareSnapshot } from "@/features/chat/types";
import { useLanguage } from "@/hooks/use-language";
import { useIsMobile } from "@/hooks/use-mobile";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

type ShareAuthStatus = "anonymous" | "authenticated" | "stale";

export function SessionSharePageClient({
  token,
  authStatus,
}: {
  token: string;
  authStatus: ShareAuthStatus;
}) {
  const router = useRouter();
  const lng = useLanguage();
  const { t } = useT("translation");
  const [snapshot, setSnapshot] = React.useState<SessionShareSnapshot | null>(
    null,
  );
  const [isLoading, setIsLoading] = React.useState(true);
  const [isForking, setIsForking] = React.useState(false);

  React.useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    void sessionShareApi
      .getSnapshot(token)
      .then((result) => {
        if (!cancelled) {
          setSnapshot(result);
        }
      })
      .catch((error) => {
        console.error("[SessionSharePage] load share failed", error);
        if (!cancelled) {
          toast.error(t("chat.shareLoadFailed"));
          setSnapshot(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [t, token]);

  const parsedMessages = React.useMemo(() => {
    if (!snapshot) return [];
    return parseMessages(
      snapshot.messages,
      snapshot.runs.map((run) => run.userMessageId),
    ).messages;
  }, [snapshot]);
  const canFork = authStatus === "authenticated";

  const handleFork = React.useCallback(async () => {
    if (!canFork || isForking) return;
    setIsForking(true);
    try {
      const forked = await sessionShareApi.forkShare(token);
      toast.success(t("chat.shareForkCreated"));
      router.push(
        lng ? `/${lng}/chat/${forked.sessionId}` : `/chat/${forked.sessionId}`,
      );
    } catch (error) {
      console.error("[SessionSharePage] fork share failed", error);
      toast.error(t("chat.shareForkFailed"));
    } finally {
      setIsForking(false);
    }
  }, [canFork, isForking, lng, router, t, token]);
  const showExecutionPanel = Boolean(snapshot && snapshot.runs.length > 0);
  const isMobile = useIsMobile();

  if (isMobile && snapshot && showExecutionPanel) {
    return (
      <SessionShareMobileView
        snapshot={snapshot}
        parsedMessages={parsedMessages}
        canFork={canFork}
        isForking={isForking}
        onFork={handleFork}
      />
    );
  }

  return (
    <div className="flex h-dvh min-h-0 min-w-0 overflow-hidden bg-background text-foreground select-text">
      <ResizablePanelGroup
        key={showExecutionPanel ? "share-with-execution" : "share-transcript"}
        direction="horizontal"
        className="min-h-0 min-w-0"
      >
        <ResizablePanel
          defaultSize={showExecutionPanel ? 45 : 100}
          minSize={35}
          className="min-h-0 min-w-0 overflow-hidden"
        >
          <div className="flex h-full min-h-0 min-w-0 flex-col bg-background">
            <PanelHeader
              icon={MessageSquare}
              title={snapshot?.session.title || t("chat.sharedConversation")}
              description={
                snapshot
                  ? t("chat.shareSourceStatus", {
                      status: snapshot.session.status,
                    })
                  : t("chat.shareLoading")
              }
              action={
                <div className="flex min-w-0 items-center gap-2">
                  <Badge variant="secondary" className="h-8 shrink-0 gap-1.5">
                    <LockKeyhole className="size-3" />
                    {t("chat.readonly")}
                  </Badge>
                  {canFork ? (
                    <Button
                      type="button"
                      size="sm"
                      onClick={() => void handleFork()}
                      disabled={!snapshot || isForking}
                    >
                      {isForking ? (
                        <Loader2 className="size-4 animate-spin" />
                      ) : (
                        <GitFork className="size-4" />
                      )}
                      {t("chat.forkToMyChats")}
                    </Button>
                  ) : null}
                </div>
              }
            />

            <div className="min-h-0 flex-1 overflow-hidden">
              {isLoading ? (
                <div className="space-y-4 px-6 py-6">
                  {Array.from({ length: 5 }).map((_, index) => (
                    <Skeleton key={index} className="h-24 rounded-md" />
                  ))}
                </div>
              ) : snapshot ? (
                <ChatMessageList
                  messages={parsedMessages}
                  sessionStatus={snapshot.session.status}
                  showUserPromptTimeline
                  contentPaddingClassName="px-6 md:px-10 lg:px-12"
                />
              ) : (
                <div className="px-6 py-10 text-sm text-muted-foreground">
                  {t("chat.shareNotFound")}
                </div>
              )}
            </div>

            <div className="shrink-0 border-t border-border px-4 py-3">
              <div className="flex min-h-11 items-center gap-3 rounded-xl border border-border bg-muted/30 px-4 text-sm text-muted-foreground">
                <span className="min-w-0 flex-1 truncate">
                  {t("chat.shareReadonlyComposerPlaceholder")}
                </span>
                <Button
                  type="button"
                  size="icon"
                  variant="secondary"
                  disabled
                  aria-label={t("chat.readonly")}
                  className="size-8 shrink-0"
                >
                  <ArrowUp className="size-4" />
                </Button>
              </div>
            </div>
          </div>
        </ResizablePanel>

        {showExecutionPanel && snapshot ? (
          <div className="hidden min-h-0 min-w-0 lg:contents">
            <ResizableHandle withHandle />
            <ResizablePanel
              defaultSize={55}
              minSize={30}
              className="min-h-0 min-w-0 overflow-hidden"
            >
              <SessionShareExecutionPanel snapshot={snapshot} />
            </ResizablePanel>
          </div>
        ) : null}
      </ResizablePanelGroup>
    </div>
  );
}

function ReadonlyComposer() {
  const { t } = useT("translation");

  return (
    <div className="shrink-0 border-t border-border px-4 py-3">
      <div className="flex min-h-11 items-center gap-3 rounded-xl border border-border bg-muted/30 px-4 text-sm text-muted-foreground">
        <span className="min-w-0 flex-1 truncate">
          {t("chat.shareReadonlyComposerPlaceholder")}
        </span>
        <Button
          type="button"
          size="icon"
          variant="secondary"
          disabled
          aria-label={t("chat.readonly")}
          className="size-8 shrink-0"
        >
          <ArrowUp className="size-4" />
        </Button>
      </div>
    </div>
  );
}

function SessionShareMobileView({
  snapshot,
  parsedMessages,
  canFork,
  isForking,
  onFork,
}: {
  snapshot: SessionShareSnapshot;
  parsedMessages: ChatMessage[];
  canFork: boolean;
  isForking: boolean;
  onFork: () => void;
}) {
  const { t } = useT("translation");
  const [activeIndex, setActiveIndex] = React.useState(0);
  const [hasFooterSelection, setHasFooterSelection] = React.useState(false);
  const [runSheetOpen, setRunSheetOpen] = React.useState(false);
  const [selectedRunId, setSelectedRunId] = React.useState(
    () => snapshot.runs.at(-1)?.runId,
  );
  const swiperRef = React.useRef<SwiperType | null>(null);
  const runs = React.useMemo(
    () =>
      snapshot.runs.map((run) =>
        mapSharedRunToRunResponse(run, snapshot.session.sessionId),
      ),
    [snapshot.runs, snapshot.session.sessionId],
  );

  React.useEffect(() => {
    setSelectedRunId((current) => {
      if (current && snapshot.runs.some((run) => run.runId === current)) {
        return current;
      }
      return snapshot.runs.at(-1)?.runId;
    });
  }, [snapshot.runs]);

  React.useEffect(() => {
    setActiveIndex(0);
    setHasFooterSelection(true);
    swiperRef.current?.slideTo(0, 0);
  }, [snapshot.share.shareId]);

  const selectedRun =
    snapshot.runs.find((run) => run.runId === selectedRunId) ??
    snapshot.runs.at(-1);
  const currentRunId = snapshot.runs.at(-1)?.runId;
  const selectedRunIndex = selectedRunId
    ? snapshot.runs.findIndex((run) => run.runId === selectedRunId)
    : -1;
  const showRunNavigation = snapshot.runs.length > 1;
  const isViewingHistory = Boolean(
    selectedRunId && currentRunId && selectedRunId !== currentRunId,
  );
  const footerTabs = [
    {
      key: "chat" as const,
      label: t("mobile.chat"),
      icon: MessageSquare,
      index: 0,
    },
    {
      key: "computer" as const,
      label: t("mobile.computer"),
      icon: Monitor,
      index: 1,
    },
    {
      key: "artifacts" as const,
      label: t("mobile.artifacts"),
      icon: Layers,
      index: 2,
    },
  ];

  return (
    <div className="flex h-dvh min-h-0 w-full select-text flex-col overflow-hidden bg-background text-foreground">
      <div className="z-50 shrink-0 border-b bg-background px-3 py-2">
        <div className="flex min-w-0 items-center gap-2">
          <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
            <div className="flex min-w-0 items-center gap-2">
              <MessageSquare className="size-4 shrink-0 text-muted-foreground" />
              <span className="min-w-0 truncate text-sm font-semibold">
                {snapshot.session.title || t("chat.sharedConversation")}
              </span>
            </div>
            <span className="truncate text-xs text-muted-foreground">
              {t("chat.shareSourceStatus", {
                status: snapshot.session.status,
              })}
            </span>
          </div>
          <Badge variant="secondary" className="h-8 shrink-0 gap-1.5">
            <LockKeyhole className="size-3" />
            {t("chat.readonly")}
          </Badge>
          {canFork ? (
            <Button
              type="button"
              size="icon"
              variant="outline"
              onClick={onFork}
              disabled={isForking}
              aria-label={t("chat.forkToMyChats")}
              title={t("chat.forkToMyChats")}
              className="size-8 shrink-0"
            >
              {isForking ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <GitFork className="size-4" />
              )}
            </Button>
          ) : null}
        </div>

        <div className="mt-2 space-y-2">
          {showRunNavigation ? (
            <div className="flex items-center gap-2">
              <div className="min-w-0 flex-1 overflow-hidden">
                <MobileRunTimeline
                  runs={runs}
                  selectedRunId={selectedRunId}
                  onSelectRun={setSelectedRunId}
                />
              </div>
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
            </div>
          ) : null}

          {showRunNavigation && isViewingHistory && selectedRunIndex >= 0 ? (
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
                onClick={() => setSelectedRunId(currentRunId)}
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
                    key={tab.key}
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
      </div>

      <div className="min-h-0 flex-1">
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
                "flex h-full min-h-0 flex-col",
                activeIndex === 0 ? "bg-background" : "bg-muted/50",
              )}
            >
              <div className="min-h-0 flex-1 overflow-hidden">
                <ChatMessageList
                  messages={parsedMessages}
                  sessionStatus={snapshot.session.status}
                  showUserPromptTimeline
                  contentPaddingClassName="px-4"
                />
              </div>
              <ReadonlyComposer />
            </div>
          </SwiperSlide>
          <SwiperSlide className="h-full">
            <div
              className={cn(
                "h-full",
                activeIndex === 1 ? "bg-background" : "bg-muted/50",
              )}
            >
              {selectedRun ? <SharedComputerSnapshot run={selectedRun} /> : null}
            </div>
          </SwiperSlide>
          <SwiperSlide className="h-full">
            <div
              className={cn(
                "h-full",
                activeIndex === 2 ? "bg-background" : "bg-muted/50",
              )}
            >
              {selectedRun ? <SharedArtifactsSnapshot run={selectedRun} /> : null}
            </div>
          </SwiperSlide>
        </Swiper>
      </div>

      <MobileRunSheet
        open={runSheetOpen}
        onOpenChange={setRunSheetOpen}
        runs={runs}
        selectedRunId={selectedRunId}
        currentRunId={currentRunId}
        onSelectRun={setSelectedRunId}
        onFollowCurrentRun={() => setSelectedRunId(currentRunId)}
      />
    </div>
  );
}
