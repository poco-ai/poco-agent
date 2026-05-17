"use client";

import * as React from "react";
import { ChevronRight } from "lucide-react";

import { PresetGlyph } from "@/features/capabilities/presets/components/preset-glyph";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

interface PresetListItemProps {
  preset: Preset;
  selected?: boolean;
  onSelect: (preset: Preset) => void;
}

export function PresetListItem({
  preset,
  selected = false,
  onSelect,
}: PresetListItemProps) {
  const { t } = useT("translation");

  return (
    <button
      type="button"
      onClick={() => onSelect(preset)}
      className={cn(
        "flex w-full items-center gap-3 rounded-2xl border px-3 py-3 text-left transition-colors",
        selected
          ? "border-primary/30 bg-primary/10 shadow-sm"
          : "border-border/60 bg-card/70 hover:bg-accent/40",
      )}
      aria-pressed={selected}
    >
      <PresetGlyph preset={preset} variant="picker" />
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-medium text-foreground">
          {preset.name}
        </div>
        <div className="mt-1 truncate text-xs text-muted-foreground">
          {preset.description?.trim() ||
            t("library.presetsPage.emptyDescription")}
        </div>
      </div>
      <ChevronRight
        className={cn(
          "size-4 shrink-0 text-muted-foreground transition-transform",
          selected && "translate-x-0.5 text-foreground",
        )}
      />
    </button>
  );
}
