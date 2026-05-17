"use client";

import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { CapabilitySourceAvatar } from "@/features/capabilities/components/capability-source-avatar";
import type { SourceInfo } from "@/features/capabilities/types/source";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

interface SubAgentListItemProps {
  name: string;
  description?: string | null;
  tools?: string[] | null;
  mode?: "raw" | "structured";
  enabled?: boolean;
  source?: SourceInfo | null;
  selected?: boolean;
  onClick?: () => void;
  trailing?: React.ReactNode;
  disabled?: boolean;
}

export function SubAgentListItem({
  name,
  description,
  tools,
  mode = "structured",
  enabled = true,
  source,
  selected = false,
  onClick,
  trailing,
  disabled = false,
}: SubAgentListItemProps) {
  const { t } = useT("translation");
  const modeLabel =
    mode === "structured"
      ? t("library.subAgents.mode.structured")
      : t("library.subAgents.mode.raw");
  const toolsLabel =
    Array.isArray(tools) && tools.length > 0 ? tools.join(", ") : "";

  const content = (
    <div
      className={cn(
        "group flex items-center gap-4 rounded-xl border border-border/70 bg-card px-4 py-3 min-h-[64px]",
        onClick && "transition-colors hover:bg-accent/30",
        selected && "border-primary/30 bg-primary/10",
        disabled && "opacity-50",
      )}
    >
      <CapabilitySourceAvatar
        name={name}
        source={source}
        status={enabled ? "active" : "inactive"}
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium font-mono">{name}</span>
          <Badge variant="outline" className="text-xs text-muted-foreground">
            {modeLabel}
          </Badge>
        </div>
        {description ? (
          <p className="text-sm text-muted-foreground truncate">{description}</p>
        ) : null}
        {toolsLabel ? (
          <p className="text-xs text-muted-foreground font-mono mt-1 truncate">
            {toolsLabel}
          </p>
        ) : null}
      </div>
      {trailing ? <div className="flex shrink-0 items-center gap-2">{trailing}</div> : null}
    </div>
  );

  if (!onClick) {
    return content;
  }

  return (
    <button
      type="button"
      onClick={onClick}
      className="block w-full text-left"
      disabled={disabled}
      aria-pressed={selected}
    >
      {content}
    </button>
  );
}
