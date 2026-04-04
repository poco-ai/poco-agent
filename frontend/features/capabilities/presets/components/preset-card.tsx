"use client";

import * as React from "react";
import { PresetCardSurface } from "@/features/capabilities/presets/components/preset-card-surface";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";

interface PresetCardProps {
  preset: Preset;
  badgeLabels?: string[];
  onEdit: (preset: Preset) => void;
}

export function PresetCard({
  preset,
  badgeLabels,
  onEdit,
}: PresetCardProps) {
  const handleOpenEdit = React.useCallback(() => {
    onEdit(preset);
  }, [onEdit, preset]);

  return (
    <PresetCardSurface
      preset={preset}
      badgeLabels={badgeLabels}
      onActivate={handleOpenEdit}
    />
  );
}
