"use client";

import {
  AlertTriangle,
  Bot,
  CircleAlert,
  Flame,
  MoonStar,
  Pin,
  Square,
  Trash2,
} from "lucide-react";

import { cn } from "@/lib/utils";
import type {
  PersistentRuntimeStatusPresentation,
  RuntimeStatusIconKey,
} from "@/lib/persistent-runtime-status";

function RuntimeStatusIcon({
  iconKey,
  className,
}: {
  iconKey: RuntimeStatusIconKey;
  className?: string;
}) {
  switch (iconKey) {
    case "running":
      return <Bot className={cn("fill-current", className)} />;
    case "warmIdle":
      return <Flame className={cn("fill-current", className)} />;
    case "sleeping":
      return <MoonStar className={cn("fill-current", className)} />;
    case "stopped":
      return <Square className={cn("fill-current", className)} />;
    case "stale":
      return <AlertTriangle className={cn("fill-current", className)} />;
    case "removed":
      return <Trash2 className={cn("fill-current", className)} />;
    case "failed":
      return <CircleAlert className={cn("fill-current", className)} />;
    case "pin":
      return <Pin className={cn("fill-current", className)} />;
    default:
      return <CircleAlert className={cn("fill-current", className)} />;
  }
}

function getToneClassName(
  tone: PersistentRuntimeStatusPresentation["tone"],
): string {
  switch (tone) {
    case "success":
      return "border-emerald-500/30 bg-emerald-500/10 text-emerald-700";
    case "warning":
      return "border-amber-500/30 bg-amber-500/10 text-amber-700";
    case "danger":
      return "border-rose-500/30 bg-rose-500/10 text-rose-700";
    default:
      return "border-border bg-background text-muted-foreground";
  }
}

function getIconOnlyToneClassName(
  tone: PersistentRuntimeStatusPresentation["tone"],
): string {
  switch (tone) {
    case "success":
      return "bg-emerald-500/16 text-emerald-300";
    case "warning":
      return "bg-amber-500/18 text-amber-300";
    case "danger":
      return "bg-rose-500/18 text-rose-300";
    default:
      return "bg-muted text-muted-foreground";
  }
}

export function PersistentRuntimeBadge({
  status,
  label,
  pinnedLabel,
  iconOnly = false,
  className,
}: {
  status: PersistentRuntimeStatusPresentation;
  label: string;
  pinnedLabel?: string;
  iconOnly?: boolean;
  className?: string;
}) {
  if (iconOnly) {
    return (
      <span
        title={label}
        aria-label={label}
        className={cn(
          "inline-flex size-5 items-center justify-center rounded-full",
          getIconOnlyToneClassName(status.tone),
          className,
        )}
      >
        <RuntimeStatusIcon iconKey={status.iconKey} className="size-3" />
      </span>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
        getToneClassName(status.tone),
        className,
      )}
    >
      <RuntimeStatusIcon iconKey={status.iconKey} className="size-3.5" />
      <span>{label}</span>
      {status.isPinned && pinnedLabel ? (
        <span className="inline-flex items-center gap-1 rounded-full bg-background/70 px-1.5 py-0.5 text-[11px] text-foreground">
          <RuntimeStatusIcon iconKey="pin" className="size-3" />
          <span>{pinnedLabel}</span>
        </span>
      ) : null}
    </span>
  );
}
