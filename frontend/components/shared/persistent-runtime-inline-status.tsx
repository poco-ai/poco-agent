"use client";

import {
  AlertTriangle,
  Bot,
  CircleAlert,
  Flame,
  MoonStar,
  Square,
  Trash2,
} from "lucide-react";

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type {
  PersistentRuntimeStatusPresentation,
  RuntimeStatusIconKey,
} from "@/lib/persistent-runtime-status";
import { cn } from "@/lib/utils";

function RuntimeInlineIcon({
  iconKey,
  className,
}: {
  iconKey: RuntimeStatusIconKey;
  className?: string;
}) {
  switch (iconKey) {
    case "running":
      return <Bot className={className} />;
    case "warmIdle":
      return <Flame className={className} />;
    case "sleeping":
      return <MoonStar className={className} />;
    case "stopped":
      return <Square className={className} />;
    case "stale":
      return <AlertTriangle className={className} />;
    case "removed":
      return <Trash2 className={className} />;
    default:
      return <CircleAlert className={className} />;
  }
}

function getIconClassName(tone: PersistentRuntimeStatusPresentation["tone"]): string {
  switch (tone) {
    case "success":
      return "text-emerald-300";
    case "warning":
      return "text-amber-300";
    case "danger":
      return "text-rose-300";
    default:
      return "text-muted-foreground";
  }
}

export function PersistentRuntimeInlineStatus({
  status,
  text,
  tooltip,
  className,
}: {
  status: PersistentRuntimeStatusPresentation;
  text: string;
  tooltip?: string;
  className?: string;
}) {
  const label = (
    <span className="inline-flex items-center gap-1.5">
      <span>:</span>
      <RuntimeInlineIcon
        iconKey={status.iconKey}
        className={cn("size-3.5", getIconClassName(status.tone))}
      />
      <span>{text}</span>
    </span>
  );

  if (!tooltip) {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1.5 text-xs text-muted-foreground",
          className,
        )}
      >
        {label}
      </span>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-xs text-muted-foreground",
        className,
      )}
    >
      <span>:</span>
      <RuntimeInlineIcon
        iconKey={status.iconKey}
        className={cn("size-3.5", getIconClassName(status.tone))}
      />
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            className="inline-flex items-center border-b border-transparent p-0 text-xs text-muted-foreground transition-[color,border-color] duration-200 hover:border-current hover:text-foreground"
          >
            {text}
          </button>
        </TooltipTrigger>
        <TooltipContent sideOffset={6}>{tooltip}</TooltipContent>
      </Tooltip>
    </span>
  );
}
