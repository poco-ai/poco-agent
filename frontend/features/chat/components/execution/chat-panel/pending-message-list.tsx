"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import {
  Pencil,
  Trash2,
  ChevronDown,
  ChevronRight,
  ArrowUp,
  Loader2,
  Sparkles,
} from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

import type { PendingMessage } from "./hooks/use-pending-messages";

interface PendingMessageListProps {
  messages: PendingMessage[];
  queuedCount?: number;
  nextPreview?: string | null;
  isLoading?: boolean;
  onSend: (messageId: string) => void | Promise<void>;
  onModify: (messageId: string) => void | Promise<void>;
  onDelete: (messageId: string) => void | Promise<void>;
  className?: string;
}

function getMessagePreview(
  message: PendingMessage | null | undefined,
  t: (key: string, options?: Record<string, unknown>) => string,
): string | null {
  if (!message) return null;

  const content = message.content?.trim();
  if (content) {
    return content;
  }

  if ((message.attachments?.length ?? 0) > 0) {
    return t("chatPanel.fileAttachment", {
      count: message.attachments?.length ?? 0,
    });
  }

  return null;
}

function QueueDecoration({ isLoading }: { isLoading: boolean }) {
  return (
    <div
      aria-hidden="true"
      className="relative flex h-10 w-20 shrink-0 items-center justify-center overflow-hidden rounded-full border border-primary/15 bg-gradient-to-r from-primary/10 via-background to-primary/10"
    >
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,var(--primary)_0%,transparent_68%)] opacity-10" />
      <div className="absolute inset-x-3 top-1/2 h-px -translate-y-1/2 bg-gradient-to-r from-transparent via-primary/30 to-transparent" />
      <div className="flex items-center gap-1.5">
        {[0, 1, 2].map((index) => (
          <span
            key={index}
            className={cn(
              "inline-flex rounded-full bg-primary/75 shadow-[0_0_18px_color-mix(in_oklab,var(--primary)_35%,transparent)]",
              index === 1 ? "size-2.5" : "size-2",
              isLoading ? "animate-bounce" : "animate-pulse",
            )}
            style={{
              animationDelay: `${index * 0.18}s`,
              animationDuration: isLoading ? "1s" : "1.8s",
            }}
          />
        ))}
      </div>
      <Sparkles
        className={cn(
          "absolute right-2 top-1.5 size-3 text-primary/70",
          isLoading ? "animate-pulse" : "animate-bounce",
        )}
        style={{ animationDuration: "1.6s" }}
      />
    </div>
  );
}

export function PendingMessageList({
  messages,
  queuedCount = 0,
  nextPreview,
  isLoading = false,
  onSend,
  onModify,
  onDelete,
  className,
}: PendingMessageListProps) {
  const { t } = useT("translation");
  const [isOpen, setIsOpen] = React.useState(true);
  const totalQueuedCount = Math.max(messages.length, queuedCount);
  const firstMessage = messages[0];
  const summaryPreview =
    getMessagePreview(firstMessage, t) ?? nextPreview?.trim() ?? null;

  if (totalQueuedCount === 0 && !isLoading) return null;

  return (
    <div className={cn("px-4 pb-3", className)}>
      <div className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-sm">
        <Collapsible open={isOpen} onOpenChange={setIsOpen} className="w-full">
          <div className="flex items-center justify-between gap-3 border-b border-border/70 bg-muted/25 px-3 py-2.5">
            <CollapsibleTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="flex h-auto min-w-0 items-center gap-3 p-0 text-left text-sm font-medium text-foreground hover:bg-transparent"
              >
                {isOpen ? (
                  <ChevronDown className="size-4 shrink-0" />
                ) : (
                  <ChevronRight className="size-4 shrink-0" />
                )}
                <span className="inline-flex size-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                  {totalQueuedCount}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-foreground">
                    {totalQueuedCount} {t("pending.queued")}
                  </span>
                  {summaryPreview ? (
                    <span className="block truncate text-xs text-muted-foreground">
                      {summaryPreview}
                    </span>
                  ) : null}
                </span>
              </Button>
            </CollapsibleTrigger>

            <div className="flex shrink-0 items-center gap-2">
              <span className="sr-only">
                {isLoading
                  ? t("status.loading")
                  : firstMessage
                    ? firstMessage.status === "paused"
                      ? t("pending.pending")
                      : t("pending.queued")
                    : t("pending.queued")}
              </span>
              <QueueDecoration isLoading={isLoading} />
            </div>
          </div>

          <CollapsibleContent>
            <div className="flex flex-col gap-2 p-2">
              {messages.length === 0 ? (
                <div className="rounded-lg border border-dashed border-border bg-muted/20 px-3 py-3">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    {isLoading ? (
                      <Loader2 className="size-4 animate-spin" />
                    ) : (
                      <ArrowUp className="size-4" />
                    )}
                    <span>
                      {isLoading ? t("status.loading") : t("pending.queued")}
                    </span>
                  </div>
                  {summaryPreview ? (
                    <p className="mt-2 line-clamp-2 text-sm text-foreground">
                      {summaryPreview}
                    </p>
                  ) : null}
                </div>
              ) : (
                messages.map((message, index) => {
                  const isNextMessage = index === 0;
                  const preview = getMessagePreview(message, t);

                  return (
                    <div
                      key={message.id}
                      className={cn(
                        "group flex items-start gap-3 rounded-lg border px-3 py-3 text-sm transition-colors",
                        isNextMessage
                          ? "border-primary/30 bg-primary/5"
                          : "border-border/70 bg-background/80 hover:bg-muted/30",
                      )}
                    >
                      <span
                        className={cn(
                          "inline-flex size-6 shrink-0 items-center justify-center rounded-full border text-xs font-semibold",
                          isNextMessage
                            ? "border-primary/40 bg-primary/10 text-primary"
                            : "border-border bg-background text-muted-foreground",
                        )}
                      >
                        {index + 1}
                      </span>

                      <div className="min-w-0 flex-1">
                        {message.attachments &&
                        message.attachments.length > 0 ? (
                          <div className="text-xs text-muted-foreground">
                            {t("chatPanel.fileAttachment", {
                              count: message.attachments.length,
                            })}
                          </div>
                        ) : null}
                        {preview ? (
                          <p className="mt-1 line-clamp-2 text-sm font-medium text-foreground">
                            {preview}
                          </p>
                        ) : null}
                      </div>

                      <div className="flex shrink-0 items-center gap-1 opacity-100 transition-opacity md:opacity-0 md:group-hover:opacity-100">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8 text-muted-foreground hover:text-foreground"
                          onClick={() => void onModify(message.id)}
                          title={t("pending.modify")}
                        >
                          <Pencil className="size-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8 text-muted-foreground hover:text-foreground"
                          onClick={() => void onSend(message.id)}
                          title={t("pending.send")}
                        >
                          <ArrowUp className="size-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8 text-muted-foreground hover:text-destructive"
                          onClick={() => void onDelete(message.id)}
                          title={t("pending.delete")}
                        >
                          <Trash2 className="size-3.5" />
                        </Button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </CollapsibleContent>
        </Collapsible>
      </div>
    </div>
  );
}
