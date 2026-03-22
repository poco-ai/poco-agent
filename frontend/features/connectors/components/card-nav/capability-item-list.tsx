"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { SkeletonText } from "@/components/ui/skeleton-shimmer";
import { StaggeredEntrance } from "@/components/ui/staggered-entrance";

export interface CapabilityItem {
  id: number;
  name: string;
  enabled: boolean;
  toggleId: number;
}

const scrollbarStyles =
  "-mr-1 pr-2 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-transparent [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:transition-colors group-hover:[&::-webkit-scrollbar-thumb]:bg-muted-foreground/20 [&.is-scrolling::-webkit-scrollbar-thumb]:bg-muted-foreground/20";

interface CapabilityItemListProps {
  items: CapabilityItem[];
  emptyText: string;
  isLoading: boolean;
  hasFetched: boolean;
  onToggle: (toggleId: number, currentEnabled: boolean) => void;
}

export function CapabilityItemList({
  items,
  emptyText,
  isLoading,
  hasFetched,
  onToggle,
}: CapabilityItemListProps) {
  const [isScrolling, setIsScrolling] = React.useState(false);
  const scrollTimeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );

  const handleScroll = React.useCallback(() => {
    setIsScrolling(true);
    if (scrollTimeoutRef.current) {
      clearTimeout(scrollTimeoutRef.current);
    }
    scrollTimeoutRef.current = setTimeout(() => {
      setIsScrolling(false);
      scrollTimeoutRef.current = null;
    }, 500);
  }, []);

  React.useEffect(
    () => () => {
      if (scrollTimeoutRef.current) clearTimeout(scrollTimeoutRef.current);
    },
    [],
  );

  if (isLoading && !hasFetched) {
    return (
      <div className="flex flex-col gap-1" role="status" aria-label="Loading">
        <SkeletonText className="h-3 w-20" />
        <SkeletonText className="h-3 w-24" />
        <SkeletonText className="h-3 w-16" />
      </div>
    );
  }

  if (items.length === 0) {
    return <p className="text-xs italic text-muted-foreground">{emptyText}</p>;
  }

  return (
    <div
      onScroll={handleScroll}
      className={cn(
        "flex flex-col gap-1 max-h-[180px] overflow-y-auto",
        scrollbarStyles,
        isScrolling && "is-scrolling",
      )}
    >
      <StaggeredEntrance show={hasFetched} staggerDelay={30} duration={300}>
        {items.map((item) => (
          <CapabilityItemRow key={item.id} item={item} onToggle={onToggle} />
        ))}
      </StaggeredEntrance>
    </div>
  );
}

interface CapabilityItemRowProps {
  item: CapabilityItem;
  onToggle: (toggleId: number, currentEnabled: boolean) => void;
}

function CapabilityItemRow({ item, onToggle }: CapabilityItemRowProps) {
  const handleClick = React.useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onToggle(item.toggleId, item.enabled);
    },
    [item.toggleId, item.enabled, onToggle],
  );

  return (
    <button
      type="button"
      onClick={handleClick}
      className={cn(
        "group/item flex items-center gap-2.5 pl-0 pr-2.5 py-1.5 text-xs font-medium rounded-md transition-all duration-200 text-left w-full cursor-pointer select-none",
        "text-muted-foreground hover:text-foreground hover:bg-muted/60 active:bg-muted/80",
      )}
    >
      <span
        className={cn(
          "w-2 h-2 rounded-full transition-all duration-300 flex-shrink-0",
          item.enabled
            ? "bg-primary shadow-[0_0_6px_-1px_hsl(var(--primary)/0.6)] scale-100"
            : "scale-90 bg-muted-foreground/30 group-hover/item:bg-muted-foreground/50",
        )}
        aria-hidden
      />
      <span className="flex-1 truncate tracking-tight opacity-90 group-hover/item:opacity-100">
        {item.name}
      </span>
    </button>
  );
}
