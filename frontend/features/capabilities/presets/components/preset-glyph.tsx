"use client";

import Image from "next/image";

import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import type { PresetGlyphVariant } from "@/features/capabilities/presets/lib/preset-visuals";
import {
  getPresetGlyphFrameClassName,
  getPresetGlyphImageClassName,
} from "@/features/capabilities/presets/lib/preset-visuals";

interface PresetGlyphProps {
  preset: Pick<Preset, "name" | "visual_key" | "visual_url">;
  variant: PresetGlyphVariant;
}

function getFallbackLabel(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");
}

export function PresetGlyph({ preset, variant }: PresetGlyphProps) {
  return (
    <div className={getPresetGlyphFrameClassName(variant)} aria-hidden="true">
      {preset.visual_url ? (
        <Image
          src={preset.visual_url}
          alt=""
          width={68}
          height={68}
          unoptimized
          className={getPresetGlyphImageClassName(variant)}
        />
      ) : (
        <span className="text-xs font-semibold tracking-[0.18em] text-muted-foreground">
          {getFallbackLabel(preset.name || preset.visual_key)}
        </span>
      )}
    </div>
  );
}
