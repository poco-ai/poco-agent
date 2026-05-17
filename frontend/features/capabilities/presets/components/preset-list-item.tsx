"use client";

import * as React from "react";

import { PresetGlyph } from "@/features/capabilities/presets/components/preset-glyph";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
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
  return (
    <button
      type="button"
      onClick={() => onSelect(preset)}
      className={cn(
        "flex w-full items-center gap-1 rounded-md px-2 py-1 text-left text-sm transition-colors",
        selected
          ? "bg-muted text-foreground"
          : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
      )}
      aria-current={selected ? "true" : undefined}
    >
      <PresetGlyph preset={preset} variant="picker" />
      <span className="truncate font-medium">{preset.name}</span>
    </button>
  );
}
