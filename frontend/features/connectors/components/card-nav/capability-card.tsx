"use client";

import * as React from "react";
import { AlertTriangle, ExternalLink, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  CapabilityItemList,
  type CapabilityItem,
} from "./capability-item-list";

const cardBaseStyles = cn(
  "group relative flex flex-col rounded-lg border border-border/50 bg-muted/30 px-4 pt-2 pb-4",
  "transition-all duration-300 ease-[cubic-bezier(0.23,1,0.32,1)]",
  "hover:bg-muted/40 hover:shadow-[0_4px_12px_-2px_rgba(var(--foreground),0.05)]",
  "min-w-[330px] shrink-0",
  "md:min-w-0 md:shrink",
);

interface CapabilityCardProps {
  icon: LucideIcon;
  title: string;
  items: CapabilityItem[];
  emptyText: string;
  isLoading: boolean;
  hasFetched: boolean;
  onToggle: (toggleId: number, currentEnabled: boolean) => void;
  onNavigate: () => void;
  showWarning?: boolean;
  onWarningClick?: () => void;
}

export function CapabilityCard({
  icon: Icon,
  title,
  items,
  emptyText,
  isLoading,
  hasFetched,
  onToggle,
  onNavigate,
  showWarning = false,
  onWarningClick,
}: CapabilityCardProps) {
  return (
    <article
      className={cardBaseStyles}
      aria-labelledby={`capability-card-${title}-heading`}
    >
      <header className="mb-2 flex min-w-0 shrink-0 items-center justify-between gap-3">
        <div className="flex min-w-0 items-center justify-start gap-2.5">
          <Icon className="size-4 shrink-0 text-muted-foreground" aria-hidden />
          <h3
            id={`capability-card-${title}-heading`}
            className="text-base font-semibold tracking-[-0.01em] truncate"
          >
            {title}
          </h3>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {showWarning && onWarningClick && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onWarningClick();
              }}
              className="flex items-center justify-center size-6 rounded-full hover:bg-amber-500/20 transition-colors"
              title="View details"
            >
              <AlertTriangle className="size-4 text-amber-500" aria-hidden />
            </button>
          )}
          <button
            type="button"
            onClick={onNavigate}
            className="flex items-center justify-center size-8 rounded-md text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-foreground/20"
            aria-label={`Open ${title}`}
          >
            <ExternalLink className="size-4" aria-hidden />
          </button>
        </div>
      </header>
      <div className="min-h-0 flex-1">
        <CapabilityItemList
          items={items}
          emptyText={emptyText}
          isLoading={isLoading}
          hasFetched={hasFetched}
          onToggle={onToggle}
        />
      </div>
    </article>
  );
}
