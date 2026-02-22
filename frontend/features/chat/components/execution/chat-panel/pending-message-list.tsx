"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import {
  Pencil,
  Trash2,
  ChevronDown,
  ChevronRight,
  Circle,
  ArrowUp,
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
  onSend: (index: number) => void;
  onModify: (index: number) => void;
  onDelete: (index: number) => void;
  className?: string;
}

export function PendingMessageList({
  messages,
  onSend,
  onModify,
  onDelete,
  className,
}: PendingMessageListProps) {
  const { t } = useT("translation");
  const [isOpen, setIsOpen] = React.useState(true);

  if (messages.length === 0) return null;

  return (
    <div className={cn("px-4 pb-2", className)}>
      <div className="rounded-lg border border-border bg-card/50 shadow-sm overflow-hidden">
        <Collapsible open={isOpen} onOpenChange={setIsOpen} className="w-full">
          <div className="flex items-center justify-between px-3 py-2 bg-muted/20">
            <CollapsibleTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="p-0 h-auto hover:bg-transparent font-medium flex items-center gap-2 text-sm text-foreground"
              >
                {isOpen ? (
                  <ChevronDown className="size-4" />
                ) : (
                  <ChevronRight className="size-4" />
                )}
                {messages.length} {t("pending.queued")}
              </Button>
            </CollapsibleTrigger>
          </div>

          <CollapsibleContent>
            <div className="flex flex-col p-2 pt-0 gap-1">
              {messages.map((msg, index) => (
                <div
                  key={index}
                  className="group flex items-center gap-3 rounded-md px-3 py-2 text-sm hover:bg-muted/50 transition-colors"
                >
                  <Circle className="size-3 text-muted-foreground shrink-0" />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-foreground font-medium">
                        {msg.content}
                      </span>
                      {msg.attachments && msg.attachments.length > 0 && (
                        <span className="text-xs text-muted-foreground">
                          {t("chatPanel.fileAttachment", {
                            count: msg.attachments.length,
                          })}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-7 text-muted-foreground hover:text-foreground"
                      onClick={() => onModify(index)}
                      title={t("pending.modify")}
                    >
                      <Pencil className="size-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-7 text-muted-foreground hover:text-foreground"
                      onClick={() => onSend(index)}
                      title={t("pending.send")}
                    >
                      <ArrowUp className="size-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-7 text-muted-foreground hover:text-destructive"
                      onClick={() => onDelete(index)}
                      title={t("pending.delete")}
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CollapsibleContent>
        </Collapsible>
      </div>
    </div>
  );
}
