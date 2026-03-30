"use client";

"use client";

import * as React from "react";
import {
  Bot,
  Brain,
  MoreHorizontal,
  Pencil,
  Server,
  Sparkles,
  Trash2,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { PRESET_ICON_MAP } from "@/features/capabilities/presets/lib/preset-visuals";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import { useT } from "@/lib/i18n/client";

interface PresetCardProps {
  preset: Preset;
  isBusy?: boolean;
  onEdit: (preset: Preset) => void;
  onDelete: (preset: Preset) => void;
}

export function PresetCard({
  preset,
  isBusy = false,
  onEdit,
  onDelete,
}: PresetCardProps) {
  const { t } = useT("translation");
  const accentColor = preset.color || "var(--primary)";
  const iconName = preset.icon in PRESET_ICON_MAP ? preset.icon : "default";

  return (
    <Card className="overflow-hidden rounded-2xl border-border/60">
      <CardContent className="p-0">
        <div className="flex items-start gap-4 p-5">
          <div
            className="flex size-12 shrink-0 items-center justify-center rounded-2xl border border-border/60 bg-muted/40"
            style={{ color: accentColor }}
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

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="size-8">
                    <MoreHorizontal className="size-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => onEdit(preset)}>
                    <Pencil className="size-4" />
                    <span>{t("common.edit")}</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => onDelete(preset)}
                    disabled={isBusy}
                    className="text-destructive focus:text-destructive"
                  >
                    <Trash2 className="size-4" />
                    <span>{t("common.delete")}</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            <div className="flex flex-wrap gap-2">
              <Badge variant="secondary" className="gap-1.5">
                <Sparkles className="size-3" />
                {preset.skill_ids.length}
              </Badge>
              <Badge variant="secondary" className="gap-1.5">
                <Server className="size-3" />
                {preset.mcp_server_ids.length}
              </Badge>
              <Badge variant="secondary" className="gap-1.5">
                <Brain className="size-3" />
                {preset.plugin_ids.length}
              </Badge>
              <Badge variant="secondary" className="gap-1.5">
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
