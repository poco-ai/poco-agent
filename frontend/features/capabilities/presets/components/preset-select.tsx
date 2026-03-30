"use client";

import { Sparkles } from "lucide-react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import { useT } from "@/lib/i18n/client";

interface PresetSelectProps {
  presets: Preset[];
  value: number | null;
  onChange: (value: number | null) => void;
  disabled?: boolean;
}

export function PresetSelect({
  presets,
  value,
  onChange,
  disabled = false,
}: PresetSelectProps) {
  const { t } = useT("translation");

  return (
    <Select
      value={value === null ? "none" : String(value)}
      onValueChange={(next) => onChange(next === "none" ? null : Number(next))}
      disabled={disabled}
    >
      <SelectTrigger className="w-full rounded-xl border-border/60 bg-background/80 sm:w-[220px]">
        <SelectValue placeholder={t("library.presetsPage.picker.placeholder")}>
          <span className="inline-flex items-center gap-2">
            <Sparkles className="size-4" />
            <span>
              {value === null
                ? t("library.presetsPage.picker.none")
                : presets.find((preset) => preset.preset_id === value)?.name}
            </span>
          </span>
        </SelectValue>
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="none">
          {t("library.presetsPage.picker.none")}
        </SelectItem>
        {presets.map((preset) => (
          <SelectItem key={preset.preset_id} value={String(preset.preset_id)}>
            {preset.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
