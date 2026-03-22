"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import {
  Pencil,
  Trash2,
  ChevronDown,
  ChevronRight,
  ArrowUp,
  Clock3,
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

export function PendingMessageList({
  messages,
  queuedCount = 0,
  onSend,
  onModify,
  onDelete,
  className,
}: PendingMessageListProps) {
  const { t } = useT("translation");
  const [isOpen, setIsOpen] = React.useState(true);
  const totalQueuedCount = Math.max(messages.length, queuedCount);
  if (totalQueuedCount === 0) return null;

  return (
    <div className={cn("px-4 pb-3", className)}>
      <div className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-sm">
        <Collapsible open={isOpen} onOpenChange={setIsOpen} className="w-full">
          <div className="border-b border-border/70 bg-muted/25 px-3 py-2.5">
            <CollapsibleTrigger asChild>
              <button
                type="button"
                className="flex w-full items-center gap-2 text-left text-sm font-medium text-foreground"
              >
                {isOpen ? (
                  <ChevronDown className="size-4 shrink-0" />
                ) : (
                  <ChevronRight className="size-4 shrink-0" />
                )}
                <span className="block truncate text-sm font-medium text-foreground">
                  {totalQueuedCount} {t("pending.queued")}
                </span>
              </button>
            </CollapsibleTrigger>
          </div>

          <CollapsibleContent>
            <div className="flex flex-col gap-2 p-2">
              {messages.map((message) => {
                const preview = getMessagePreview(message, t);

                return (
                  <div
                    key={message.id}
                    className="group flex items-center gap-3 rounded-lg border border-border/70 bg-background/80 px-3 py-3 text-sm transition-colors hover:bg-muted/30"
                  >
                    <Clock3 className="size-4 shrink-0 self-center text-muted-foreground" />

                    <div className="min-w-0 flex-1 self-stretch">
                      <div className="flex h-full min-h-8 flex-col justify-center">
                        {message.attachments &&
                        message.attachments.length > 0 ? (
                          <div className="text-xs text-muted-foreground">
                            {t("chatPanel.fileAttachment", {
                              count: message.attachments.length,
                            })}
                          </div>
                        ) : null}
                        {preview ? (
                          <p className="line-clamp-2 text-sm font-medium text-foreground">
                            {preview}
                          </p>
                        ) : null}
                      </div>
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
              })}
            </div>
          </CollapsibleContent>
        </Collapsible>
      </div>
    </div>
  );
}
