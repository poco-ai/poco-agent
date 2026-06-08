"use client";

import * as React from "react";
import {
  CircleDot,
  MessageCircle,
  PlayCircle,
  Radio,
  Sparkles,
} from "lucide-react";

import type { ConversationTimelineItem } from "@/features/chat/types";
import { cn } from "@/lib/utils";

interface ConversationTimelineRailProps {
  title: string;
  items: ConversationTimelineItem[];
  activeItemId?: string | null;
  emptyLabel?: string;
  className?: string;
  onSelectItem?: (item: ConversationTimelineItem) => void;
}

function getTimelineIcon(item: ConversationTimelineItem) {
  if (item.itemType === "run") return PlayCircle;
  if (item.itemType === "channel_event") return Radio;
  if (item.role === "assistant" || item.metadata.source === "imported_agent_session") {
    return Sparkles;
  }
  if (item.itemType === "message" || item.itemType === "channel_message") {
    return MessageCircle;
  }
  return CircleDot;
}

function formatTimelineTime(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "";
  return new Intl.DateTimeFormat(undefined, {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
}

export function ConversationTimelineRail({
  title,
  items,
  activeItemId,
  emptyLabel,
  className,
  onSelectItem,
}: ConversationTimelineRailProps) {
  return (
    <aside
      className={cn(
        "flex h-full min-h-0 w-56 shrink-0 flex-col border-l border-border bg-card/50",
        className,
      )}
    >
      <div className="border-b border-border px-4 py-3">
        <p className="truncate text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
          {title}
        </p>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-3 py-3">
        {items.length === 0 ? (
          <p className="px-1 py-2 text-sm text-muted-foreground">
            {emptyLabel}
          </p>
        ) : (
          <div className="relative space-y-2">
            <div className="absolute bottom-3 left-[15px] top-3 w-px bg-border" />
            {items.map((item) => {
              const Icon = getTimelineIcon(item);
              const active = item.id === activeItemId;
              return (
                <button
                  key={item.id}
                  type="button"
                  disabled={!onSelectItem}
                  onClick={() => onSelectItem?.(item)}
                  className={cn(
                    "relative flex w-full min-w-0 items-start gap-2 rounded-md px-1 py-1.5 text-left transition-colors",
                    onSelectItem && "hover:bg-muted/40",
                    active && "bg-primary/10",
                  )}
                >
                  <span
                    className={cn(
                      "relative z-10 mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full border bg-background text-muted-foreground",
                      active && "border-primary text-primary",
                    )}
                  >
                    <Icon className="size-3.5" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-xs font-medium text-foreground">
                      {item.label}
                    </span>
                    <span className="mt-0.5 block truncate text-[11px] text-muted-foreground">
                      {item.status || item.role || formatTimelineTime(item.createdAt)}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </aside>
  );
}
