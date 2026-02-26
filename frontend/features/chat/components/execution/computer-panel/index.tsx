"use client";

import * as React from "react";
import {
  Monitor,
  CheckCircle2,
  XCircle,
  ChevronLeft,
  ChevronRight,
  Pause,
  Play,
  Layers,
  Globe,
  SquareTerminal,
  Wrench,
  Pencil,
  FileEdit,
  FileText,
  Folder,
  Search,
} from "lucide-react";
import { PanelHeader } from "@/components/shared/panel-header";
import { ScrollArea } from "@/components/ui/scroll-area";
import { SkeletonCircle, SkeletonItem } from "@/components/ui/skeleton-shimmer";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n/client";
import { getBrowserScreenshotAction } from "@/features/chat/actions/query-actions";
import type { ToolExecutionResponse } from "@/features/chat/types";
import { useToolExecutions } from "./hooks/use-tool-executions";
import { ApiError } from "@/lib/errors";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { motion } from "motion/react";
import { BrowserViewer } from "./browser-viewer";
import { GenericToolViewer } from "./generic-tool-viewer";
import { TerminalViewer } from "./terminal-viewer";
import {
  clampIndex,
  COMPUTER_GENERIC_TOOL_NAMES,
  getBrowserStepLabel,
  getFrameAdvanceDelayMs,
  getGenericToolSummary,
  normalizeToolName,
  POCO_PLAYWRIGHT_MCP_PREFIX,
  truncateMiddle,
} from "@/features/chat/components/execution/computer-panel/replay/replay-utils";

interface ComputerPanelProps {
  sessionId: string;
  sessionStatus?: "pending" | "running" | "completed" | "failed" | "canceled";
  browserEnabled?: boolean;
  headerAction?: React.ReactNode;
  hideHeader?: boolean;
}

type ReplayFilter = "all" | "browser" | "terminal" | "tool";
type ReplayKind = "browser" | "terminal" | "tool";

interface ReplayFrame {
  kind: ReplayKind;
  execution: ToolExecutionResponse;
  label: string;
}

function renderToolKindIcon(toolName: string): React.ReactNode {
  const normalizedToolName = normalizeToolName(toolName);
  switch (normalizedToolName) {
    case "edit":
      return <Pencil className="size-4 text-muted-foreground" />;
    case "write":
      return <FileEdit className="size-4 text-muted-foreground" />;
    case "read":
      return <FileText className="size-4 text-muted-foreground" />;
    case "glob":
      return <Folder className="size-4 text-muted-foreground" />;
    case "grep":
      return <Search className="size-4 text-muted-foreground" />;
    default:
      return <Wrench className="size-4 text-muted-foreground" />;
  }
}

export function ComputerPanel({
  sessionId,
  sessionStatus,
  headerAction,
  hideHeader = false,
}: ComputerPanelProps) {
  const { t } = useT("translation");
  const isActive = sessionStatus === "running" || sessionStatus === "pending";

  const { executions, isLoading, isLoadingMore, hasMore, loadMore } =
    useToolExecutions({
      sessionId,
      isActive,
      pollingIntervalMs: 2000,
      limit: 100,
    });

  // --- Screenshot caching (persists across tab switches) ---
  const screenshotCacheRef = React.useRef(new Map<string, string | null>());
  const [browserScreenshotUrls, setBrowserScreenshotUrls] = React.useState<
    Record<string, string | null>
  >({});
  const inflightRef = React.useRef(new Set<string>());

  const fetchBrowserScreenshot = React.useCallback(
    async (toolUseId: string, retryOn404: boolean): Promise<void> => {
      const id = toolUseId.trim();
      if (
        !id ||
        screenshotCacheRef.current.has(id) ||
        inflightRef.current.has(id)
      ) {
        return;
      }

      inflightRef.current.add(id);

      const fetchWithRetry = async (attempts = 0): Promise<void> => {
        try {
          const res = await getBrowserScreenshotAction({
            sessionId,
            toolUseId: id,
          });
          screenshotCacheRef.current.set(id, res.url);
          setBrowserScreenshotUrls((prev) => ({ ...prev, [id]: res.url }));
        } catch (err) {
          const statusCode =
            err instanceof ApiError
              ? err.statusCode
              : (err as { statusCode?: number })?.statusCode;

          if (statusCode === 404 && retryOn404 && attempts < 10) {
            setTimeout(() => fetchWithRetry(attempts + 1), 800);
            return;
          }

          screenshotCacheRef.current.set(id, null);
          setBrowserScreenshotUrls((prev) => ({ ...prev, [id]: null }));
        } finally {
          inflightRef.current.delete(id);
        }
      };

      await fetchWithRetry();
    },
    [sessionId],
  );

  const replayFramesAll: ReplayFrame[] = React.useMemo(() => {
    const frames: ReplayFrame[] = [];
    for (const e of executions) {
      const toolName = e.tool_name || "";
      const normalizedToolName = normalizeToolName(toolName);

      if (normalizedToolName === "bash") {
        const cmd =
          typeof e.tool_input?.["command"] === "string"
            ? (e.tool_input?.["command"] as string)
            : "";
        frames.push({
          kind: "terminal",
          execution: e,
          label: cmd
            ? truncateMiddle(cmd, 80)
            : t("computer.terminal.unknownCommand"),
        });
        continue;
      }

      if (toolName.startsWith(POCO_PLAYWRIGHT_MCP_PREFIX)) {
        frames.push({
          kind: "browser",
          execution: e,
          label: getBrowserStepLabel(e),
        });
        continue;
      }

      if (COMPUTER_GENERIC_TOOL_NAMES.has(normalizedToolName)) {
        const summary = getGenericToolSummary(e);
        frames.push({
          kind: "tool",
          execution: e,
          label: summary
            ? truncateMiddle(summary, 80)
            : (toolName || t("chat.toolCards.tools.tool")).trim(),
        });
      }
    }
    return frames;
  }, [executions, t]);

  const browserCount = React.useMemo(
    () => replayFramesAll.filter((f) => f.kind === "browser").length,
    [replayFramesAll],
  );
  const terminalCount = React.useMemo(
    () => replayFramesAll.filter((f) => f.kind === "terminal").length,
    [replayFramesAll],
  );
  const toolCount = React.useMemo(
    () => replayFramesAll.filter((f) => f.kind === "tool").length,
    [replayFramesAll],
  );

  const [replayFilter, setReplayFilter] = React.useState<ReplayFilter>("all");
  const [isPlaying, setIsPlaying] = React.useState(false);
  const [isRealtimePlaying, setIsRealtimePlaying] = React.useState(false);
  const [followLatest, setFollowLatest] = React.useState(true);
  const [selectedFrameId, setSelectedFrameId] = React.useState<string | null>(
    null,
  );
  const [sliderProgress, setSliderProgress] = React.useState(0);

  const replayFrames: ReplayFrame[] = React.useMemo(() => {
    if (replayFilter === "browser") {
      return replayFramesAll.filter((f) => f.kind === "browser");
    }
    if (replayFilter === "terminal") {
      return replayFramesAll.filter((f) => f.kind === "terminal");
    }
    if (replayFilter === "tool") {
      return replayFramesAll.filter((f) => f.kind === "tool");
    }
    return replayFramesAll;
  }, [replayFilter, replayFramesAll]);

  const availableKinds = React.useMemo(() => {
    const kinds: ReplayKind[] = [];
    if (browserCount > 0) kinds.push("browser");
    if (terminalCount > 0) kinds.push("terminal");
    if (toolCount > 0) kinds.push("tool");
    return kinds;
  }, [browserCount, terminalCount, toolCount]);

  React.useEffect(() => {
    if (replayFilter === "all") return;
    if (!availableKinds.includes(replayFilter)) {
      setReplayFilter("all");
    }
  }, [availableKinds, replayFilter]);

  const selectedIndex = React.useMemo(() => {
    if (!selectedFrameId) return -1;
    return replayFrames.findIndex((f) => f.execution.id === selectedFrameId);
  }, [replayFrames, selectedFrameId]);

  const selectedFrame = selectedIndex >= 0 ? replayFrames[selectedIndex] : null;
  const sliderMax = Math.max(0, replayFrames.length - 1);

  const stopPlayback = React.useCallback(() => {
    setIsPlaying(false);
    setIsRealtimePlaying(false);
  }, []);

  // Stop playback when filter changes (avoid surprising jumps).
  React.useEffect(() => {
    stopPlayback();
  }, [replayFilter, stopPlayback]);

  // In live session mode, always follow latest frames instead of local replay controls.
  React.useEffect(() => {
    if (!isActive) return;
    stopPlayback();
    setFollowLatest(true);
  }, [isActive, stopPlayback]);

  // Keep selection valid; default to the latest completed step (or latest any step).
  React.useEffect(() => {
    if (replayFrames.length === 0) {
      if (selectedFrameId !== null) setSelectedFrameId(null);
      stopPlayback();
      return;
    }

    const exists =
      selectedFrameId &&
      replayFrames.some((f) => f.execution.id === selectedFrameId);

    if (exists) {
      if (followLatest && !isPlaying) {
        const lastId = replayFrames[replayFrames.length - 1]?.execution.id;
        if (lastId && selectedFrameId !== lastId) {
          setSelectedFrameId(lastId);
        }
      }
      return;
    }

    const latestCompleted = [...replayFrames]
      .reverse()
      .find((f) => Boolean(f.execution.tool_output));
    const pick =
      latestCompleted?.execution.id ||
      replayFrames[replayFrames.length - 1]!.execution.id;
    setSelectedFrameId(pick);
    setFollowLatest(true);
    stopPlayback();
  }, [followLatest, isPlaying, replayFrames, selectedFrameId, stopPlayback]);

  // Playback: advance frame-by-frame with a natural cadence.
  React.useEffect(() => {
    if (!isPlaying) return;
    if (!selectedFrame) return;
    if (selectedIndex < 0) return;

    if (selectedIndex >= replayFrames.length - 1) {
      if (isRealtimePlaying && isActive) {
        // Keep realtime mode active while waiting for new frames.
        return;
      }
      stopPlayback();
      return;
    }

    const delayMs = getFrameAdvanceDelayMs(selectedFrame.kind);
    const id = window.setTimeout(() => {
      const next = replayFrames[selectedIndex + 1];
      if (next) {
        setSelectedFrameId(next.execution.id);
        setFollowLatest(selectedIndex + 1 >= replayFrames.length - 1);
      }
    }, delayMs);
    return () => window.clearTimeout(id);
  }, [
    isActive,
    isPlaying,
    replayFrames,
    isRealtimePlaying,
    selectedFrame,
    selectedIndex,
    stopPlayback,
  ]);

  // Smooth progress animation while playing so the slider doesn't jump.
  React.useEffect(() => {
    if (!isPlaying || !selectedFrame || selectedIndex < 0) {
      setSliderProgress(Math.max(0, selectedIndex));
      return;
    }

    if (selectedIndex >= replayFrames.length - 1) {
      setSliderProgress(Math.max(0, selectedIndex));
      return;
    }

    const delayMs = getFrameAdvanceDelayMs(selectedFrame.kind);
    const start = performance.now();
    let rafId = 0;

    const tick = (now: number) => {
      const elapsed = now - start;
      const ratio = Math.min(1, Math.max(0, elapsed / delayMs));
      setSliderProgress(selectedIndex + ratio);
      if (ratio < 1) {
        rafId = window.requestAnimationFrame(tick);
      }
    };

    rafId = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(rafId);
  }, [isPlaying, replayFrames.length, selectedFrame, selectedIndex]);

  const selectedBrowserToolUseId =
    selectedFrame?.kind === "browser" &&
    typeof selectedFrame.execution.tool_use_id === "string"
      ? selectedFrame.execution.tool_use_id
      : null;
  const selectedBrowserIsDone = Boolean(
    selectedFrame?.kind === "browser" && selectedFrame.execution.tool_output,
  );

  // Fetch screenshot URL on demand for the selected browser step (cache per tool_use_id).
  React.useEffect(() => {
    if (!selectedBrowserToolUseId) return;
    if (!selectedBrowserIsDone) return;
    if (selectedBrowserToolUseId in browserScreenshotUrls) return;
    void fetchBrowserScreenshot(selectedBrowserToolUseId, isActive);
  }, [
    browserScreenshotUrls,
    fetchBrowserScreenshot,
    isActive,
    selectedBrowserIsDone,
    selectedBrowserToolUseId,
  ]);

  // Prefetch screenshots for the next 1-2 browser steps to keep playback smooth.
  React.useEffect(() => {
    if (!selectedFrame) return;
    if (selectedIndex < 0) return;

    const candidates = replayFrames
      .slice(selectedIndex + 1, selectedIndex + 3)
      .filter((f) => f.kind === "browser")
      .map((f) => f.execution)
      .filter(
        (e) =>
          Boolean(e.tool_output) &&
          typeof e.tool_use_id === "string" &&
          Boolean(e.tool_use_id),
      )
      .map((e) => e.tool_use_id as string);

    for (const toolUseId of candidates) {
      if (toolUseId in browserScreenshotUrls) continue;
      void fetchBrowserScreenshot(toolUseId, isActive);
    }
  }, [
    browserScreenshotUrls,
    fetchBrowserScreenshot,
    isActive,
    replayFrames,
    selectedFrame,
    selectedIndex,
  ]);

  const selectedBrowserUrl =
    selectedBrowserToolUseId &&
    selectedBrowserToolUseId in browserScreenshotUrls
      ? browserScreenshotUrls[selectedBrowserToolUseId]
      : undefined;

  const viewer = (() => {
    if (!selectedFrame) {
      return (
        <div className="h-full w-full bg-muted/30 flex items-center justify-center">
          <div className="text-sm text-muted-foreground">
            {t("computer.replay.empty")}
          </div>
        </div>
      );
    }

    if (selectedFrame.kind === "browser") {
      return (
        <BrowserViewer
          isDone={selectedBrowserIsDone}
          toolUseId={selectedBrowserToolUseId}
          screenshotUrl={selectedBrowserUrl}
        />
      );
    }
    if (selectedFrame.kind === "tool") {
      return <GenericToolViewer execution={selectedFrame.execution} />;
    }
    return <TerminalViewer execution={selectedFrame.execution} />;
  })();

  const canGoPrev = replayFrames.length > 0 && selectedIndex > 0;
  const canGoNext =
    replayFrames.length > 0 &&
    selectedIndex >= 0 &&
    selectedIndex < replayFrames.length - 1;
  const isLiveSession = isActive;

  const goToIndex = React.useCallback(
    (index: number) => {
      if (replayFrames.length === 0) return;
      const safe = clampIndex(index, 0, replayFrames.length - 1);
      const frame = replayFrames[safe];
      if (!frame) return;
      stopPlayback();
      setSelectedFrameId(frame.execution.id);
      setFollowLatest(safe === replayFrames.length - 1);
    },
    [replayFrames, stopPlayback],
  );

  const handleRealtimeToggle = React.useCallback(() => {
    if (replayFrames.length === 0) return;
    if (isPlaying && isRealtimePlaying) {
      stopPlayback();
      return;
    }

    const isAtEnd = selectedIndex >= replayFrames.length - 1;
    if (isAtEnd) {
      const firstFrame = replayFrames[0];
      if (!firstFrame) return;
      // Prevent keep-selection effect from snapping back to the latest frame.
      setFollowLatest(false);
      setSelectedFrameId(firstFrame.execution.id);
      // Let selection update first so replay starts from frame 0 smoothly.
      window.requestAnimationFrame(() => {
        setIsRealtimePlaying(true);
        setIsPlaying(true);
        setFollowLatest(true);
      });
      return;
    }

    setIsRealtimePlaying(true);
    setIsPlaying(true);
    setFollowLatest(true);
  }, [isPlaying, isRealtimePlaying, replayFrames, selectedIndex, stopPlayback]);

  const controls = (
    <div className="min-w-0 space-y-1">
      <div className="flex min-w-0 items-center gap-2 overflow-hidden">
        <Button
          type="button"
          variant="outline"
          size="icon-sm"
          onClick={() => goToIndex(selectedIndex - 1)}
          disabled={!canGoPrev}
          title={t("computer.replay.controls.prev")}
          aria-label={t("computer.replay.controls.prev")}
          className="shrink-0"
        >
          <ChevronLeft className="size-4" />
        </Button>

        <Button
          type="button"
          variant="outline"
          size="icon-sm"
          onClick={handleRealtimeToggle}
          disabled={replayFrames.length === 0}
          title={
            isPlaying && isRealtimePlaying
              ? t("computer.replay.controls.pause")
              : t("computer.replay.controls.play")
          }
          aria-label={
            isPlaying && isRealtimePlaying
              ? t("computer.replay.controls.pause")
              : t("computer.replay.controls.play")
          }
          className="shrink-0"
        >
          {isPlaying && isRealtimePlaying ? (
            <Pause className="size-4" />
          ) : (
            <Play className="size-4" />
          )}
        </Button>

        <Button
          type="button"
          variant="outline"
          size="icon-sm"
          onClick={() => goToIndex(selectedIndex + 1)}
          disabled={!canGoNext}
          title={t("computer.replay.controls.next")}
          aria-label={t("computer.replay.controls.next")}
          className="shrink-0"
        >
          <ChevronRight className="size-4" />
        </Button>

        <div className="min-w-0 flex-1 pl-1">
          <Slider
            min={0}
            max={sliderMax}
            value={[clampIndex(sliderProgress, 0, sliderMax)]}
            minVisibleRange
            onValueChange={(value) => {
              const nextIndex = value[0] ?? 0;
              goToIndex(nextIndex);
            }}
            disabled={replayFrames.length <= 1}
            className="w-full min-w-0"
          />
        </div>
      </div>

      {executions.length >= 2000 ? (
        <div className="truncate text-[11px] text-muted-foreground">
          {t("computer.replay.limitHint", { limit: "2000" })}
        </div>
      ) : null}
    </div>
  );

  const hasMultipleTypes = availableKinds.length > 1;

  const filterOptions = React.useMemo(
    () =>
      [
        {
          value: "all" as const,
          label: t("computer.replay.filter.all"),
          Icon: Layers,
        },
        browserCount > 0
          ? {
              value: "browser" as const,
              label: t("computer.replay.filter.browser"),
              Icon: Globe,
            }
          : null,
        terminalCount > 0
          ? {
              value: "terminal" as const,
              label: t("computer.replay.filter.terminal"),
              Icon: SquareTerminal,
            }
          : null,
        toolCount > 0
          ? {
              value: "tool" as const,
              label: t("chat.toolCards.tools.tool"),
              Icon: Wrench,
            }
          : null,
      ].filter(Boolean) as Array<{
        value: ReplayFilter;
        label: string;
        Icon: React.ComponentType<{ className?: string }>;
      }>,
    [browserCount, terminalCount, t, toolCount],
  );

  const filterToggleGroup = hasMultipleTypes ? (
    <div className="flex h-full flex-col items-center gap-1 p-1">
      {filterOptions.map(({ value, label, Icon }) => (
        <Tooltip key={value}>
          <TooltipTrigger asChild>
            <button
              type="button"
              onClick={() => setReplayFilter(value)}
              aria-label={label}
              className={cn(
                "flex size-11 items-center justify-center rounded-md transition-colors",
                replayFilter === value
                  ? "bg-accent text-accent-foreground"
                  : "hover:bg-muted/50 text-muted-foreground",
              )}
            >
              <Icon className="size-4" />
            </button>
          </TooltipTrigger>
          <TooltipContent side="right" sideOffset={8}>
            {label}
          </TooltipContent>
        </Tooltip>
      ))}
    </div>
  ) : null;

  // Infinite scroll sentinel ref and auto-scroll ref
  const sentinelRef = React.useRef<HTMLDivElement>(null);
  const selectedFrameRef = React.useRef<HTMLButtonElement>(null);
  const scrollAreaRef = React.useRef<HTMLDivElement>(null);

  // Setup infinite scroll
  React.useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && hasMore && !isLoadingMore) {
          loadMore();
        }
      },
      { threshold: 0.1, rootMargin: "100px" },
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasMore, isLoadingMore, loadMore]);

  // Auto-scroll to selected frame
  React.useEffect(() => {
    if (!selectedFrameId) return;
    // Small delay to ensure DOM is updated
    setTimeout(() => {
      selectedFrameRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
    }, 50);
  }, [selectedFrameId]);

  // Render skeleton placeholders
  const renderSkeletons = (count: number) => (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonItem
          key={`skeleton-${i}`}
          className="h-10 min-h-0 w-full"
          style={{ animationDelay: `${i * 0.08}s` }}
        />
      ))}
    </>
  );

  const timelineList = (
    <ScrollArea className="h-full" ref={scrollAreaRef}>
      <div className="flex h-full flex-col space-y-1 p-2">
        {isLoading && replayFrames.length === 0 ? (
          <>{renderSkeletons(5)}</>
        ) : replayFrames.length === 0 ? (
          <div className="flex flex-1 items-center justify-center rounded-lg bg-muted/30 px-4 py-6 text-center text-sm text-muted-foreground">
            {t("computer.replay.empty")}
          </div>
        ) : (
          <motion.div
            initial="hidden"
            animate="visible"
            variants={{
              hidden: {},
              visible: {
                transition: {
                  staggerChildren: 0.05,
                },
              },
            }}
          >
            {replayFrames.map((frame, idx) => {
              const isSelected = frame.execution.id === selectedFrameId;
              const isDone = Boolean(frame.execution.tool_output);
              const isError = frame.execution.is_error;
              const kindIcon =
                frame.kind === "browser" ? (
                  <Globe className="size-4 text-muted-foreground" />
                ) : frame.kind === "tool" ? (
                  renderToolKindIcon(frame.execution.tool_name || "")
                ) : (
                  <SquareTerminal className="size-4 text-muted-foreground" />
                );
              const statusIcon = !isDone ? (
                <SkeletonCircle className="size-4" />
              ) : isError ? (
                <XCircle className="size-4 text-destructive" />
              ) : (
                <CheckCircle2 className="size-4 text-primary" />
              );
              const durationSec = frame.execution.duration_ms
                ? (frame.execution.duration_ms / 1000).toFixed(1)
                : null;
              return (
                <motion.button
                  key={frame.execution.id}
                  ref={isSelected ? selectedFrameRef : undefined}
                  type="button"
                  variants={{
                    hidden: { opacity: 0, y: 10 },
                    visible: { opacity: 1, y: 0 },
                  }}
                  transition={{ duration: 0.2, ease: "easeOut" }}
                  className={cn(
                    "h-10 w-full min-w-0 max-w-full overflow-hidden rounded-md px-2 py-2 text-left transition-colors flex items-center gap-2",
                    isSelected
                      ? "bg-accent text-accent-foreground"
                      : "hover:bg-muted/50",
                  )}
                  onClick={() => {
                    setIsPlaying(false);
                    setSelectedFrameId(frame.execution.id);
                    setFollowLatest(idx === replayFrames.length - 1);
                  }}
                >
                  <div className="shrink-0 flex items-center gap-2">
                    {statusIcon}
                    {kindIcon}
                  </div>
                  <div className="w-0 flex-1 min-w-0 overflow-hidden">
                    <div className="text-xs font-mono truncate leading-tight">
                      {frame.label}
                    </div>
                  </div>
                  {durationSec && (
                    <div className="shrink-0 whitespace-nowrap text-xs text-muted-foreground tabular-nums">
                      {durationSec}s
                    </div>
                  )}
                </motion.button>
              );
            })}
            {hasMore && <div ref={sentinelRef} className="h-1" />}
          </motion.div>
        )}
      </div>
    </ScrollArea>
  );

  return (
    <div className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden">
      {!hideHeader ? (
        <PanelHeader
          icon={Monitor}
          title={t("computer.title")}
          description={t("computer.description")}
          content={
            headerAction ? (
              <div className="flex min-w-0 items-center overflow-hidden">
                {headerAction}
              </div>
            ) : undefined
          }
        />
      ) : null}
      <div className="flex-1 min-h-0 overflow-hidden p-3 sm:p-4">
        <div className="h-full min-h-0 flex flex-col gap-3">
          <div className="relative flex-1 min-h-0 overflow-hidden rounded-xl border bg-card">
            {viewer}
            {isLiveSession ? (
              <div className="absolute bottom-2 right-2 rounded-full border bg-card/90 px-2 py-0.5 text-[11px] font-medium text-primary shadow-sm">
                {t("computer.replay.liveLabel")}
              </div>
            ) : null}
          </div>

          {!isLiveSession ? controls : null}

          {!isLiveSession ? (
            hasMultipleTypes ? (
              <div className="h-[220px] min-w-0 overflow-hidden rounded-xl border bg-card flex">
                <div className="shrink-0 border-r p-1">{filterToggleGroup}</div>
                <div className="flex-1 min-w-0">{timelineList}</div>
              </div>
            ) : (
              <div className="h-[220px] min-w-0 overflow-hidden rounded-xl border bg-card">
                {timelineList}
              </div>
            )
          ) : null}
        </div>
      </div>
    </div>
  );
}
