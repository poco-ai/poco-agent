"use client";

import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { PresetGlyph } from "@/features/capabilities/presets/components/preset-glyph";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

interface PresetCardSurfaceProps {
  preset: Preset;
  selected?: boolean;
  selectedVariant?: "neutral" | "primary";
  meta?: React.ReactNode;
  selectionIndicator?: React.ReactNode;
  badgeLabels?: string[];
  onActivate?: () => void;
  onClick?: React.MouseEventHandler<HTMLDivElement>;
  onKeyDown?: React.KeyboardEventHandler<HTMLDivElement>;
  disabled?: boolean;
  className?: string;
}

export function PresetCardSurface({
  preset,
  selected = false,
  selectedVariant = "neutral",
  meta,
  selectionIndicator,
  badgeLabels = [],
  onActivate,
  onClick,
  onKeyDown,
  disabled = false,
  className,
}: PresetCardSurfaceProps) {
  const { t } = useT("translation");
  const isInteractive =
    !disabled &&
    (typeof onActivate === "function" ||
      typeof onClick === "function" ||
      typeof onKeyDown === "function");

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
        selected &&
          (selectedVariant === "primary"
            ? "border-primary/30 bg-primary/10 shadow-sm ring-1 ring-primary/20"
            : "border-foreground/15 bg-muted/[0.22] shadow-sm ring-1 ring-border/60"),
        disabled && "pointer-events-none opacity-70",
        className,
      )}
    >
      <CardContent className="p-0">
        <div className="flex min-h-[150px]">
          <div className="flex w-[160px] shrink-0 flex-col items-center justify-center gap-3 px-4 py-5 text-center">
            <PresetGlyph preset={preset} variant="card" />
            <div className="w-full space-y-3">
              <div className="line-clamp-2 text-base font-semibold leading-6 text-foreground">
                {preset.name}
              </div>
              {selectionIndicator ? (
                <div className="flex items-center justify-center">
                  {selectionIndicator}
                </div>
              ) : null}
            </div>
          </div>
          <div className="w-px shrink-0 bg-border/60" />
          <div className="flex min-w-0 flex-1 flex-col px-5 py-5">
            <div className="flex items-start justify-end">
              {meta ? <div className="shrink-0">{meta}</div> : null}
            </div>
            <div
              className={cn(
                "min-w-0 flex flex-1 items-center",
                meta ? "mt-3" : "",
              )}
            >
              <div className="line-clamp-4 overflow-hidden text-sm leading-6 text-muted-foreground">
                {preset.description?.trim() ||
                  t("library.presetsPage.emptyDescription")}
              </div>
            </div>
            {badgeLabels.length > 0 ? (
              <div className="mt-4 flex flex-wrap gap-2">
                {badgeLabels.map((label) => (
                  <Badge
                    key={label}
                    variant="outline"
                    className="max-w-[9rem] truncate overflow-hidden whitespace-nowrap text-muted-foreground"
                    title={label}
                  >
                    {label}
                  </Badge>
                ))}
              </div>
            ) : (
              <div className="mt-0 text-sm leading-5 text-muted-foreground/75">
                {t("library.presetsPage.emptyBadgesHint")}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
