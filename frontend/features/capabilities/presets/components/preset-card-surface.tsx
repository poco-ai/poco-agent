"use client";

import * as React from "react";
import { Bot, Brain, Server, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { PRESET_ICON_MAP } from "@/features/capabilities/presets/lib/preset-visuals";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

interface PresetCardSurfaceProps {
  preset: Preset;
  selected?: boolean;
  iconTone?: "accent" | "muted";
  selectedBackgroundColor?: string;
  meta?: React.ReactNode;
  onActivate?: () => void;
  onClick?: React.MouseEventHandler<HTMLDivElement>;
  onKeyDown?: React.KeyboardEventHandler<HTMLDivElement>;
  disabled?: boolean;
  className?: string;
}

export function PresetCardSurface({
  preset,
  selected = false,
  iconTone = "accent",
  selectedBackgroundColor,
  meta,
  onActivate,
  onClick,
  onKeyDown,
  disabled = false,
  className,
}: PresetCardSurfaceProps) {
  const { t } = useT("translation");
  const accentColor = preset.color || "var(--primary)";
  const iconName = preset.icon in PRESET_ICON_MAP ? preset.icon : "default";
  const isInteractive =
    !disabled &&
    (typeof onActivate === "function" ||
      typeof onClick === "function" ||
      typeof onKeyDown === "function");
  const iconColor =
    iconTone === "accent" ? accentColor : "var(--muted-foreground)";
  const iconBackgroundColor =
    iconTone === "accent"
      ? preset.color
        ? `${preset.color}12`
        : "color-mix(in srgb, var(--primary) 7%, transparent)"
      : "color-mix(in srgb, var(--muted) 90%, transparent)";

  const getCountBadgeProps = (count: number) =>
    count > 0
      ? {
          variant: "secondary" as const,
          className: "gap-1.5",
        }
      : {
          variant: "outline" as const,
          className: "gap-1.5 text-muted-foreground/50",
        };

  const handleKeyDown = React.useCallback(
    (event: React.KeyboardEvent<HTMLDivElement>) => {
      if (!isInteractive) return;
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        onActivate();
      }
    },
    [isInteractive, onActivate],
  );

  return (
    <Card
      role={isInteractive ? "button" : undefined}
      tabIndex={isInteractive ? 0 : undefined}
      onClick={isInteractive ? (onClick ?? onActivate) : undefined}
      onKeyDown={isInteractive ? (onKeyDown ?? handleKeyDown) : undefined}
      aria-pressed={isInteractive ? selected : undefined}
      className={cn(
        "overflow-hidden rounded-2xl border border-border/60 bg-card transition-all duration-200",
        isInteractive &&
          "cursor-pointer hover:border-border hover:shadow-sm focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50",
        selected && "border-border shadow-sm ring-1 ring-border/60",
        disabled && "pointer-events-none opacity-70",
        className,
      )}
      style={
        selected && selectedBackgroundColor
          ? { backgroundColor: selectedBackgroundColor }
          : undefined
      }
    >
      <CardContent className="p-0">
        <div className="flex items-start gap-4 p-5">
          <div
            className="flex size-12 shrink-0 items-center justify-center rounded-2xl border border-border/60"
            style={{
              color: iconColor,
              backgroundColor: iconBackgroundColor,
            }}
          >
            {React.createElement(PRESET_ICON_MAP[iconName], {
              className: "size-5",
            })}
          </div>

          <div className="min-w-0 flex-1 space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="truncate text-base font-semibold text-foreground">
                  {preset.name}
                </div>
                <div className="mt-1 text-sm text-muted-foreground">
                  {preset.description?.trim() ||
                    t("library.presetsPage.emptyDescription")}
                </div>
              </div>

              {meta ? <div className="shrink-0">{meta}</div> : null}
            </div>

            <div className="flex flex-wrap gap-2">
              <Badge {...getCountBadgeProps(preset.skill_ids.length)}>
                <Sparkles className="size-3" />
                {preset.skill_ids.length}
              </Badge>
              <Badge {...getCountBadgeProps(preset.mcp_server_ids.length)}>
                <Server className="size-3" />
                {preset.mcp_server_ids.length}
              </Badge>
              <Badge {...getCountBadgeProps(preset.plugin_ids.length)}>
                <Brain className="size-3" />
                {preset.plugin_ids.length}
              </Badge>
              <Badge {...getCountBadgeProps(preset.subagent_configs.length)}>
                <Bot className="size-3" />
                {preset.subagent_configs.length}
              </Badge>
              {preset.browser_enabled ? (
                <Badge variant="outline">
                  {t("library.presetsPage.flags.browser")}
                </Badge>
              ) : null}
              {preset.memory_enabled ? (
                <Badge variant="outline">
                  {t("library.presetsPage.flags.memory")}
                </Badge>
              ) : null}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
