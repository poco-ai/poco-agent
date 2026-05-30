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
    case "failed":
      return <CircleAlert className={className} />;
    case "pin":
      return <Pin className={className} />;
    default:
      return <CircleAlert className={className} />;
  }
}

function getToneClassName(tone: PersistentRuntimeStatusPresentation["tone"]): string {
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

export function PersistentRuntimeBadge({
  status,
  label,
  pinnedLabel,
  className,
}: {
  status: PersistentRuntimeStatusPresentation;
  label: string;
  pinnedLabel?: string;
  className?: string;
}) {
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
