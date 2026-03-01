"use client";

import * as React from "react";
import {
  ArrowDown,
  ArrowUp,
  Bot,
  Check,
  Clock3,
  Coins,
  Copy,
  GitBranch,
  Loader2,
  RotateCcw,
  ThumbsUp,
} from "lucide-react";
import { MessageContent } from "./message-content";
import { TypingIndicator } from "./typing-indicator";
import type {
  ChatMessage,
  MessageBlock,
  UsageResponse,
} from "@/features/chat/types";
import { Button } from "@/components/ui/button";
import { useT } from "@/lib/i18n/client";

interface AssistantMessageProps {
  message: ChatMessage;
  runUsage?: UsageResponse | null;
  sessionStatus?: string;
  onRegenerate?: () => void;
  onCreateBranch?: () => void;
  isCreatingBranch?: boolean;
  disableBranchAction?: boolean;
}

function pickNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function formatCostUsd(value: number | null | undefined): string | null {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  return "$" + value.toFixed(3);
}

function formatDurationMs(value: number | null | undefined): string | null {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) {
    return null;
  }
  const seconds = value / 1000;
  // Keep it compact and consistent across locales.
  return seconds >= 60 ? `${Math.round(seconds)}s` : `${seconds.toFixed(1)}s`;
}

export function AssistantMessage({
  message,
  runUsage,
  sessionStatus,
  onRegenerate,
  onCreateBranch,
  isCreatingBranch = false,
  disableBranchAction = false,
}: AssistantMessageProps) {
  const { t } = useT("translation");
  const [isCopied, setIsCopied] = React.useState(false);
  const [isLiked, setIsLiked] = React.useState(false);
  const isStreaming = message.status === "streaming";

  // Helper function to extract text content from message
  const getTextContent = (content: string | MessageBlock[]): string => {
    if (typeof content === "string") {
      return content;
    }

    // If it's an array of blocks, extract text from TextBlock
    if (Array.isArray(content)) {
      const textBlocks = content.filter(
        (block: MessageBlock) => block._type === "TextBlock",
      );
      return textBlocks
        .map((block: MessageBlock) =>
          block._type === "TextBlock" ? block.text : "",
        )
        .join("\n\n");
    }

    return String(content);
  };

  const onCopy = async () => {
    try {
      const textContent = getTextContent(message.content);
      await navigator.clipboard.writeText(textContent);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy message", err);
    }
  };

  const onLike = () => {
    setIsLiked(!isLiked);
    // TODO: Send feedback to API
  };

  const usageJson = runUsage?.usage_json as
    | Record<string, unknown>
    | null
    | undefined;
  const inputTokens = pickNumber(usageJson?.input_tokens);
  const outputTokens = pickNumber(usageJson?.output_tokens);
  const costLabel = formatCostUsd(runUsage?.total_cost_usd);
  const durationLabel = formatDurationMs(runUsage?.total_duration_ms);
  const usageSegments: React.ReactNode[] = [];
  if (costLabel) {
    usageSegments.push(
      <span key="cost" className="inline-flex items-center gap-1">
        <Coins className="size-3" />
        {costLabel}
      </span>,
    );
  }
  if (inputTokens !== null) {
    usageSegments.push(
      <span key="input" className="inline-flex items-center gap-1">
        <ArrowUp className="size-3" />
        {inputTokens.toLocaleString()}
      </span>,
    );
  }
  if (outputTokens !== null) {
    usageSegments.push(
      <span key="output" className="inline-flex items-center gap-1">
        <ArrowDown className="size-3" />
        {outputTokens.toLocaleString()}
      </span>,
    );
  }
  if (durationLabel) {
    usageSegments.push(
      <span key="duration" className="inline-flex items-center gap-1">
        <Clock3 className="size-3" />
        {durationLabel}
      </span>,
    );
  }
  const showUsage = !!runUsage && !isStreaming && usageSegments.length > 0;
  const timestampLabel =
    message.timestamp && !isNaN(new Date(message.timestamp).getTime())
      ? new Date(message.timestamp).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        })
      : null;

  return (
    <div className="group w-full min-w-0 animate-in fade-in slide-in-from-left-4 duration-300">
      <div className="flex w-full min-w-0 items-center gap-1.5">
        <div className="size-7 shrink-0 rounded-full border border-border bg-muted flex items-center justify-center">
          <Bot className="size-3.5 text-muted-foreground" />
        </div>
        <span className="shrink-0 text-xl font-bold text-foreground font-brand">
          Poco
        </span>
        {timestampLabel ? (
          <span className="ml-auto shrink-0 text-xs text-muted-background/40 opacity-0 transition-opacity group-hover:opacity-100">
            {timestampLabel}
          </span>
        ) : null}
      </div>

      <div className="mt-2 w-full min-w-0 overflow-hidden break-words text-base text-foreground [overflow-wrap:anywhere]">
        <MessageContent
          content={message.content}
          sessionStatus={sessionStatus}
        />
        {isStreaming && <TypingIndicator />}
      </div>

      <div className="mt-2 flex min-w-0 items-center gap-2 pt-2">
        <div className="shrink-0 flex items-center gap-1 opacity-100 transition-opacity md:opacity-0 md:group-hover:opacity-100">
          <Button
            variant="ghost"
            size="icon"
            className="size-7 text-muted-foreground hover:text-foreground"
            onClick={onCopy}
            title={t("chat.copyMessage")}
          >
            {isCopied ? (
              <Check className="size-3.5" />
            ) : (
              <Copy className="size-3.5" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className={`size-7 hover:text-foreground ${
              isLiked
                ? "text-primary hover:text-primary/90"
                : "text-muted-foreground"
            }`}
            onClick={onLike}
            title={t("chat.likeResponse")}
          >
            <ThumbsUp className={`size-3.5 ${isLiked ? "fill-current" : ""}`} />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="size-7 text-muted-foreground hover:text-foreground disabled:opacity-40"
            onClick={onRegenerate}
            disabled={!onRegenerate || isStreaming}
            title={t("chat.regenerate")}
          >
            <RotateCcw className="size-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="size-7 text-muted-foreground hover:text-foreground disabled:opacity-40"
            onClick={onCreateBranch}
            disabled={
              !onCreateBranch ||
              isStreaming ||
              disableBranchAction ||
              isCreatingBranch
            }
            title={t("chat.createBranch")}
          >
            {isCreatingBranch ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <GitBranch className="size-3.5" />
            )}
          </Button>
        </div>

        {showUsage ? (
          <div className="w-0 flex-1 overflow-hidden text-right font-mono text-xs tabular-nums text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100">
            <div className="truncate">
              {usageSegments.map((segment, index) => (
                <React.Fragment key={index}>
                  {index > 0 ? " · " : null}
                  {segment}
                </React.Fragment>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
