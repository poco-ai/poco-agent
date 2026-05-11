"use client";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import type { ServerAgentItem } from "@/features/servers/model/types";
import { cn } from "@/lib/utils";

function getAgentPreset(
  agent: ServerAgentItem,
  presets: Preset[],
): Preset | null {
  return presets.find((preset) => preset.preset_id === agent.presetId) ?? null;
}

function getFallbackLabel(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) {
    return "?";
  }
  return trimmed
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");
}

function getAgentAvatarUrl(
  agent: ServerAgentItem,
  preset: Preset | null,
): string {
  const presetVisualUrl = preset?.visual_url?.trim();
  if (presetVisualUrl) {
    return presetVisualUrl;
  }
  const visualKey = agent.visualKey.trim();
  return visualKey ? `/api/v1/presets/visuals/${visualKey}/content` : "";
}

export function ServerAgentAvatar({
  agent,
  presets,
  className,
  fallbackClassName,
}: {
  agent: ServerAgentItem;
  presets: Preset[];
  className?: string;
  fallbackClassName?: string;
}) {
  const preset = getAgentPreset(agent, presets);
  const avatarUrl = getAgentAvatarUrl(agent, preset);
  const fallbackLabel = getFallbackLabel(agent.displayName || agent.handle);

  return (
    <Avatar className={cn("rounded-md border border-border", className)}>
      {avatarUrl ? (
        <AvatarImage src={avatarUrl} alt={agent.displayName} />
      ) : null}
      <AvatarFallback
        className={cn(
          "rounded-md bg-muted text-xs font-semibold text-foreground",
          fallbackClassName,
        )}
      >
        {fallbackLabel}
      </AvatarFallback>
    </Avatar>
  );
}
