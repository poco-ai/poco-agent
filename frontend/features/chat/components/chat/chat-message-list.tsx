"use client";

import * as React from "react";
import { ArrowDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { AssistantMessage } from "./messages/assistant-message";
import { UserMessage } from "./messages/user-message";
import type { ChatMessage, UsageResponse } from "@/features/chat/types";
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
  contentPaddingClassName?: string;
  scrollButtonClassName?: string;
}

export function ChatMessageList({
  messages,
  isTyping,
  sessionStatus,
  repoUrl,
  gitBranch,
  runUsageByUserMessageId,
  onEditMessage,
  contentPaddingClassName,
  scrollButtonClassName,
}: ChatMessageListProps) {
  const { t } = useT("translation");
  const scrollRef = React.useRef<HTMLDivElement>(null);
  const scrollAreaRef = React.useRef<HTMLDivElement>(null);
  const [showScrollButton, setShowScrollButton] = React.useState(false);
  const [isUserScrolling, setIsUserScrolling] = React.useState(false);
  const lastMessageCountRef = React.useRef(messages.length);
  const hasInitializedRef = React.useRef(false);

  const firstUserMessageId = React.useMemo(() => {
    const first = messages.find((msg) => msg.role === "user");
    return first?.id ?? null;
  }, [messages]);

  // Check if user has scrolled up
  const checkScrollPosition = React.useCallback(() => {
    if (!scrollAreaRef.current) return;

    const viewport = scrollAreaRef.current.querySelector(
      "[data-radix-scroll-area-viewport]",
    );
    if (!viewport) return;

    const { scrollTop, scrollHeight, clientHeight } = viewport;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;

    // If user is more than 100px from bottom, consider them as scrolling up
    const isNearBottom = distanceFromBottom < 100;
    setIsUserScrolling(!isNearBottom);

    // Show scroll button if not near bottom
    setShowScrollButton(!isNearBottom);
  }, []);

  // Handle scroll events
  React.useEffect(() => {
    const scrollArea = scrollAreaRef.current;
    if (!scrollArea) return;

    const viewport = scrollArea.querySelector(
      "[data-radix-scroll-area-viewport]",
    );
    if (!viewport) return;

    let scrollTimeout: NodeJS.Timeout;
    const handleScroll = () => {
      clearTimeout(scrollTimeout);
      scrollTimeout = setTimeout(() => {
        checkScrollPosition();
      }, 100);
    };

    viewport.addEventListener("scroll", handleScroll);
    return () => {
      viewport.removeEventListener("scroll", handleScroll);
      clearTimeout(scrollTimeout);
    };
  }, [checkScrollPosition]);

  const prevIsTypingRef = React.useRef(isTyping);

  // Initial scroll to bottom when component mounts with existing messages
  React.useEffect(() => {
    if (
      !hasInitializedRef.current &&
      messages.length > 0 &&
      scrollRef.current
    ) {
      scrollRef.current.scrollIntoView({ behavior: "auto" });
      hasInitializedRef.current = true;
    }
  }, [messages]);

  // Auto-scroll to bottom when new messages arrive (only if user is not scrolling)
  React.useEffect(() => {
    const hasNewMessages = messages.length > lastMessageCountRef.current;
    const isTypingStarted = isTyping && !prevIsTypingRef.current;

    lastMessageCountRef.current = messages.length;
    prevIsTypingRef.current = isTyping;

    if (
      scrollRef.current &&
      !isUserScrolling &&
      (hasNewMessages || isTypingStarted)
    ) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }

    // Show scroll button when new messages arrive while user is scrolling
    if (hasNewMessages && isUserScrolling) {
      setShowScrollButton(true);
    }
  }, [messages, isTyping, isUserScrolling]);

  // Scroll to bottom handler
  const scrollToBottom = React.useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
      setIsUserScrolling(false);
      setShowScrollButton(false);
    }
  }, []);

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

  if (messages.length === 0 && !isTyping) {
    return null;
  }

  return (
    <div className="relative h-full w-full min-w-0 overflow-hidden">
      <ScrollArea ref={scrollAreaRef} className="h-full w-full min-w-0">
        <div
          className={cn(
            "w-full min-w-0 max-w-full space-y-4 py-6",
            contentPaddingClassName ?? "px-6",
          )}
        >
          {messages.map((message, index) => {
            if (message.role === "user") {
              return (
                <UserMessage
                  key={message.id}
                  content={message.content}
                  attachments={message.attachments}
                  repoUrl={message.id === firstUserMessageId ? repoUrl : null}
                  gitBranch={
                    message.id === firstUserMessageId ? gitBranch : null
                  }
                  onEdit={onEditMessage}
                />
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
              <AssistantMessage
                key={message.id}
                message={message}
                runUsage={runUsage}
                sessionStatus={sessionStatus}
              />
            );
          })}
          {isTyping && (
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
          )}
          <div ref={scrollRef} />
        </div>
      </ScrollArea>

      {/* Scroll to bottom button */}
      {showScrollButton && (
        <div
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
