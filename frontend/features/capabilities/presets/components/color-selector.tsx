"use client";

import { Input } from "@/components/ui/input";
import { PRESET_COLOR_OPTIONS } from "@/features/capabilities/presets/lib/preset-visuals";
import { cn } from "@/lib/utils";

interface ColorSelectorProps {
  value: string;
  onChange: (value: string) => void;
}

export function ColorSelector({ value, onChange }: ColorSelectorProps) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {PRESET_COLOR_OPTIONS.map((color) => {
          const isActive = color.toLowerCase() === value.toLowerCase();
          return (
            <button
              key={color}
              type="button"
              onClick={() => onChange(color)}
              className={cn(
                "size-8 rounded-full border-2 transition-transform hover:scale-105",
                isActive ? "border-foreground" : "border-transparent",
              )}
              style={{ backgroundColor: color }}
              aria-label={color}
            />
          );
        })}
      </div>
      <Input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="#0ea5e9"
        className="font-mono"
      />
    </div>
  );
}
