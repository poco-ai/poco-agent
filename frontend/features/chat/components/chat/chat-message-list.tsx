"use client";

import * as React from "react";
import { ArrowDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { AssistantMessage } from "./messages/assistant-message";
import { UserMessage } from "./messages/user-message";
import type {
  ChatMessage,
  MessageBlock,
  UsageResponse,
} from "@/features/chat/types";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

export interface ChatMessageListProps {
  messages: ChatMessage[];
  isTyping?: boolean;
  sessionStatus?: string;
  repoUrl?: string | null;
  gitBranch?: string | null;
  runUsageByUserMessageId?: Record<string, UsageResponse | null>;
  onEditMessage?: (content: string) => void;
  showUserPromptTimeline?: boolean;
  contentPaddingClassName?: string;
  scrollButtonClassName?: string;
}

interface UserPromptTimelineItem {
  id: string;
  index: number;
  preview: string;
  timestampLabel: string | null;
}

function extractMessageText(content: string | MessageBlock[]): string {
  if (typeof content === "string") {
    return content;
  }

  return content
    .filter(
      (block): block is { _type: "TextBlock"; text: string } =>
        block._type === "TextBlock",
    )
    .map((block) => block.text)
    .join("\n\n");
}

function isEditableElement(element: Element | null): boolean {
  if (!(element instanceof HTMLElement)) {
    return false;
  }

  if (element.isContentEditable) {
    return true;
  }

  const tagName = element.tagName;
  if (tagName === "INPUT" || tagName === "TEXTAREA" || tagName === "SELECT") {
    return true;
  }

  return (
    Boolean(element.closest("[contenteditable='true']")) ||
    Boolean(element.closest("[role='textbox']"))
  );
}

export function ChatMessageList({
  messages,
  isTyping,
  sessionStatus,
  repoUrl,
  gitBranch,
  runUsageByUserMessageId,
  onEditMessage,
  showUserPromptTimeline = false,
  contentPaddingClassName,
  scrollButtonClassName,
}: ChatMessageListProps) {
  const { t, i18n } = useT("translation");
  const scrollRef = React.useRef<HTMLDivElement>(null);
  const scrollAreaRef = React.useRef<HTMLDivElement>(null);
  const userMessageElementsRef = React.useRef<Map<string, HTMLDivElement>>(
    new Map(),
  );
  const [showScrollButton, setShowScrollButton] = React.useState(false);
  const [isUserScrolling, setIsUserScrolling] = React.useState(false);
  const [activeUserMessageId, setActiveUserMessageId] = React.useState<
    string | null
  >(null);
  const lastMessageCountRef = React.useRef(messages.length);
  const hasInitializedRef = React.useRef(false);

  const firstUserMessageId = React.useMemo(() => {
    const first = messages.find((msg) => msg.role === "user");
    return first?.id ?? null;
  }, [messages]);

  const userPromptTimelineItems = React.useMemo<
    UserPromptTimelineItem[]
  >(() => {
    const locale = i18n.language || undefined;

    return messages
      .filter((message) => message.role === "user")
      .map((message, index) => {
        const plainText = extractMessageText(message.content).trim();
        const preview = plainText || t("chat.userPromptTimelineEmpty");

        let timestampLabel: string | null = null;
        if (message.timestamp) {
          const parsedDate = new Date(message.timestamp);
          if (!Number.isNaN(parsedDate.getTime())) {
            timestampLabel = new Intl.DateTimeFormat(locale, {
              month: "2-digit",
              day: "2-digit",
              hour: "2-digit",
              minute: "2-digit",
            }).format(parsedDate);
          }
        }

        return {
          id: message.id,
          index: index + 1,
          preview,
          timestampLabel,
        };
      });
  }, [i18n.language, messages, t]);

  const userPromptTimelineIds = React.useMemo(
    () => userPromptTimelineItems.map((item) => item.id),
    [userPromptTimelineItems],
  );

  const getScrollViewport = React.useCallback(() => {
    if (!scrollAreaRef.current) return null;
    return scrollAreaRef.current.querySelector<HTMLElement>(
      "[data-radix-scroll-area-viewport]",
    );
  }, []);

  const scrollViewportToBottom = React.useCallback(
    (behavior: ScrollBehavior = "auto") => {
      const viewport = getScrollViewport();
      if (!viewport) return;
      viewport.scrollTo({
        top: viewport.scrollHeight,
        behavior,
      });
    },
    [getScrollViewport],
  );

  // Check if user has scrolled up
  const checkScrollPosition = React.useCallback(() => {
    const viewport = getScrollViewport();
    if (!viewport) return;

    const { scrollTop, scrollHeight, clientHeight } = viewport;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;

    // If user is more than 100px from bottom, consider them as scrolling up
    const isNearBottom = distanceFromBottom < 100;
    setIsUserScrolling(!isNearBottom);

    // Show scroll button if not near bottom
    setShowScrollButton(!isNearBottom);
  }, [getScrollViewport]);

  const updateActiveUserMessage = React.useCallback(() => {
    if (!showUserPromptTimeline || userPromptTimelineItems.length === 0) {
      setActiveUserMessageId(null);
      return;
    }

    const viewport = getScrollViewport();
    if (!viewport) return;

    const viewportRect = viewport.getBoundingClientRect();
    const viewportCenterY = viewportRect.top + viewportRect.height / 2;
    let closestMessageId: string | null = null;
    let minDistance = Number.POSITIVE_INFINITY;

    userPromptTimelineItems.forEach((item) => {
      const element = userMessageElementsRef.current.get(item.id);
      if (!element) return;

      const rect = element.getBoundingClientRect();
      const elementCenterY = rect.top + rect.height / 2;
      const distance = Math.abs(elementCenterY - viewportCenterY);

      if (distance < minDistance) {
        minDistance = distance;
        closestMessageId = item.id;
      }
    });

    if (closestMessageId) {
      setActiveUserMessageId((current) =>
        current === closestMessageId ? current : closestMessageId,
      );
    }
  }, [getScrollViewport, showUserPromptTimeline, userPromptTimelineItems]);

  const scrollToUserMessage = React.useCallback(
    (messageId: string, behavior: ScrollBehavior = "auto") => {
      const element = userMessageElementsRef.current.get(messageId);
      if (!element) return;
      const viewport = getScrollViewport();
      if (!viewport) return;

      const viewportRect = viewport.getBoundingClientRect();
      const elementRect = element.getBoundingClientRect();
      const elementOffsetTop = elementRect.top - viewportRect.top;
      const centeredTop =
        viewport.scrollTop +
        elementOffsetTop -
        viewport.clientHeight / 2 +
        elementRect.height / 2;
      const maxScrollTop = viewport.scrollHeight - viewport.clientHeight;

      viewport.scrollTo({
        top: Math.max(0, Math.min(centeredTop, maxScrollTop)),
        behavior,
      });
      setActiveUserMessageId(messageId);
    },
    [getScrollViewport],
  );

  // Handle scroll events
  React.useEffect(() => {
    const viewport = getScrollViewport();
    if (!viewport) return;

    let scrollTimeout: NodeJS.Timeout;
    let rafId = 0;
    const handleScroll = () => {
      clearTimeout(scrollTimeout);
      scrollTimeout = setTimeout(() => {
        checkScrollPosition();
      }, 100);
      if (rafId) {
        window.cancelAnimationFrame(rafId);
      }
      rafId = window.requestAnimationFrame(() => {
        updateActiveUserMessage();
      });
    };

    viewport.addEventListener("scroll", handleScroll);
    checkScrollPosition();
    updateActiveUserMessage();
    return () => {
      viewport.removeEventListener("scroll", handleScroll);
      clearTimeout(scrollTimeout);
      if (rafId) {
        window.cancelAnimationFrame(rafId);
      }
    };
  }, [checkScrollPosition, getScrollViewport, updateActiveUserMessage]);

  const prevIsTypingRef = React.useRef(isTyping);

  // Initial scroll to bottom when component mounts with existing messages
  React.useEffect(() => {
    if (
      !hasInitializedRef.current &&
      messages.length > 0 &&
      scrollRef.current
    ) {
      scrollViewportToBottom("auto");
      hasInitializedRef.current = true;
    }
  }, [messages, scrollViewportToBottom]);

  // Auto-scroll to bottom when new messages arrive (only if user is not scrolling)
  React.useEffect(() => {
    const hasNewMessages = messages.length > lastMessageCountRef.current;
    const isTypingStarted = isTyping && !prevIsTypingRef.current;

    lastMessageCountRef.current = messages.length;
    prevIsTypingRef.current = isTyping;

    if (!isUserScrolling && (hasNewMessages || isTyping)) {
      scrollViewportToBottom(
        isTyping
          ? "auto"
          : hasNewMessages || isTypingStarted
            ? "smooth"
            : "auto",
      );
    }

    // Show scroll button when new messages arrive while user is scrolling
    if (hasNewMessages && isUserScrolling) {
      setShowScrollButton(true);
    }
  }, [messages, isTyping, isUserScrolling, scrollViewportToBottom]);

  React.useEffect(() => {
    if (!isTyping || isUserScrolling) return;

    const scrollArea = scrollAreaRef.current;
    if (!scrollArea) return;

    const content = scrollArea.querySelector<HTMLElement>(
      "[data-chat-scroll-content]",
    );
    if (!content) return;

    const keepBottom = () => {
      scrollViewportToBottom("auto");
    };

    keepBottom();

    const resizeObserver = new ResizeObserver(() => {
      keepBottom();
    });
    resizeObserver.observe(content);

    return () => {
      resizeObserver.disconnect();
    };
  }, [isTyping, isUserScrolling, scrollViewportToBottom]);

  React.useEffect(() => {
    if (!showUserPromptTimeline) {
      setActiveUserMessageId(null);
      return;
    }

    const rafId = window.requestAnimationFrame(() => {
      updateActiveUserMessage();
    });
    return () => window.cancelAnimationFrame(rafId);
  }, [showUserPromptTimeline, updateActiveUserMessage, messages.length]);

  // Scroll to bottom handler
  const scrollToBottom = React.useCallback(() => {
    scrollViewportToBottom("smooth");
    setIsUserScrolling(false);
    setShowScrollButton(false);
  }, [scrollViewportToBottom]);

  React.useEffect(() => {
    if (!showUserPromptTimeline || userPromptTimelineIds.length === 0) return;

    const handleTimelineNavigation = (event: KeyboardEvent) => {
      if (event.defaultPrevented) return;
      if (event.metaKey || event.ctrlKey || event.altKey) return;

      const key = event.key.toLowerCase();
      if (key !== "j" && key !== "k") return;
      if (isEditableElement(document.activeElement)) return;

      const currentIndex = activeUserMessageId
        ? userPromptTimelineIds.indexOf(activeUserMessageId)
        : -1;

      if (key === "j") {
        const nextIndex =
          currentIndex < 0
            ? 0
            : Math.min(currentIndex + 1, userPromptTimelineIds.length - 1);
        if (nextIndex === currentIndex) return;
        event.preventDefault();
        event.stopPropagation();
        scrollToUserMessage(userPromptTimelineIds[nextIndex], "auto");
        return;
      }

      const prevIndex =
        currentIndex < 0
          ? userPromptTimelineIds.length - 1
          : Math.max(currentIndex - 1, 0);
      if (prevIndex === currentIndex) return;
      event.preventDefault();
      event.stopPropagation();
      scrollToUserMessage(userPromptTimelineIds[prevIndex], "auto");
    };

    window.addEventListener("keydown", handleTimelineNavigation, true);
    return () => {
      window.removeEventListener("keydown", handleTimelineNavigation, true);
    };
  }, [
    activeUserMessageId,
    scrollToUserMessage,
    showUserPromptTimeline,
    userPromptTimelineIds,
  ]);

  const lastAssistantIndexToUserMessageId = React.useMemo(() => {
    const map = new Map<number, string>();
    let currentUserMessageId: string | null = null;
    let lastAssistantIndex: number | null = null;

    messages.forEach((msg, idx) => {
      if (msg.role === "user") {
        if (currentUserMessageId && lastAssistantIndex !== null) {
          map.set(lastAssistantIndex, currentUserMessageId);
        }
        currentUserMessageId = msg.id;
        lastAssistantIndex = null;
        return;
      }

      if (msg.role === "assistant" && currentUserMessageId) {
        lastAssistantIndex = idx;
      }
    });

    if (currentUserMessageId && lastAssistantIndex !== null) {
      map.set(lastAssistantIndex, currentUserMessageId);
    }

    return map;
  }, [messages]);

  const shouldRenderUserPromptTimeline =
    showUserPromptTimeline && userPromptTimelineItems.length > 0;

  if (messages.length === 0 && !isTyping) {
    return null;
  }

  return (
    <div
      className="relative h-full w-full min-w-0 overflow-hidden"
      data-chat-message-list
    >
      <ScrollArea
        ref={scrollAreaRef}
        className="h-full w-full min-w-0"
        data-chat-scroll-area
      >
        <div
          data-chat-scroll-content
          className={cn(
            "w-full min-w-0 max-w-full space-y-4 py-6",
            contentPaddingClassName ?? "px-6",
          )}
        >
          {messages.map((message, index) => {
            if (message.role === "user") {
              return (
                <div
                  key={message.id}
                  data-user-message-id={message.id}
                  data-chat-export-item
                  ref={(element) => {
                    if (element) {
                      userMessageElementsRef.current.set(message.id, element);
                    } else {
                      userMessageElementsRef.current.delete(message.id);
                    }
                  }}
                >
                  <UserMessage
                    content={message.content}
                    attachments={message.attachments}
                    repoUrl={message.id === firstUserMessageId ? repoUrl : null}
                    gitBranch={
                      message.id === firstUserMessageId ? gitBranch : null
                    }
                    onEdit={onEditMessage}
                  />
                </div>
              );
            }

            const userMessageIdForUsage =
              message.role === "assistant"
                ? lastAssistantIndexToUserMessageId.get(index)
                : undefined;
            const runUsage =
              userMessageIdForUsage && runUsageByUserMessageId
                ? (runUsageByUserMessageId[userMessageIdForUsage] ?? null)
                : undefined;

            return (
              <div key={message.id} data-chat-export-item>
                <AssistantMessage
                  message={message}
                  runUsage={runUsage}
                  sessionStatus={sessionStatus}
                />
              </div>
            );
          })}
          {isTyping && (
            <div data-chat-export-item>
              <AssistantMessage
                message={{
                  id: "typing",
                  role: "assistant",
                  content: "",
                  status: "streaming",
                  timestamp: new Date().toISOString(),
                }}
                sessionStatus={sessionStatus}
              />
            </div>
          )}
          <div ref={scrollRef} />
        </div>
      </ScrollArea>

      {shouldRenderUserPromptTimeline ? (
        <div
          className="pointer-events-none absolute inset-y-6 right-2 z-20 hidden md:block"
          data-chat-export-skip
        >
          <div className="pointer-events-auto relative h-full w-8">
            <div className="absolute top-0 bottom-0 left-1/2 w-px -translate-x-1/2 bg-border/80" />
            <TooltipProvider delayDuration={120}>
              {userPromptTimelineItems.map((item, itemIndex) => {
                const topPercent =
                  userPromptTimelineItems.length === 1
                    ? 50
                    : (itemIndex / (userPromptTimelineItems.length - 1)) * 100;
                const isActive = item.id === activeUserMessageId;

                return (
                  <Tooltip key={item.id}>
                    <TooltipTrigger asChild>
                      <button
                        type="button"
                        className={cn(
                          "absolute left-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border transition-all focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                          isActive
                            ? "h-3.5 w-3.5 border-primary bg-primary shadow-sm"
                            : "h-2.5 w-2.5 border-border bg-muted hover:h-3.5 hover:w-3.5 hover:border-primary/60 hover:bg-primary/70",
                        )}
                        style={{ top: `${topPercent}%` }}
                        onClick={() => scrollToUserMessage(item.id, "auto")}
                        aria-label={t("chat.userPromptTimelineJump", {
                          index: item.index,
                        })}
                      />
                    </TooltipTrigger>
                    <TooltipContent
                      side="left"
                      sideOffset={10}
                      className="!bg-transparent !p-0 !text-foreground !shadow-none"
                    >
                      <div className="w-80 max-w-[70vw] overflow-hidden rounded-lg border border-border bg-popover/95 p-0 text-popover-foreground shadow-lg backdrop-blur supports-[backdrop-filter]:bg-popover/90">
                        <div className="border-b border-border px-3 py-2 text-[11px] font-medium text-muted-foreground">
                          {item.timestampLabel ?? "--:--"}
                        </div>
                        <div className="px-3 py-2">
                          <p className="line-clamp-4 whitespace-pre-wrap break-words text-sm leading-5 [overflow-wrap:anywhere]">
                            {item.preview}
                          </p>
                        </div>
                      </div>
                    </TooltipContent>
                  </Tooltip>
                );
              })}
            </TooltipProvider>
          </div>
        </div>
      ) : null}

      {/* Scroll to bottom button */}
      {showScrollButton && (
        <div
          data-chat-export-skip
          className={cn(
            "absolute bottom-6 right-6 z-10 animate-in fade-in slide-in-from-bottom-4 duration-300",
            scrollButtonClassName,
          )}
        >
          <Button
            variant="outline"
            size="icon"
            onClick={scrollToBottom}
            className="h-10 w-10 rounded-full shadow-lg hover:shadow-xl transition-shadow bg-background"
            title={t("chat.scrollToLatestMessage")}
          >
            <ArrowDown className="h-5 w-5" />
          </Button>
        </div>
      )}
    </div>
  );
}
