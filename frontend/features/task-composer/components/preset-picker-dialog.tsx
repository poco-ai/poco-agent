"use client";

import * as React from "react";
import { Check, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { getPresetIcon } from "@/features/capabilities/presets/lib/preset-visuals";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

interface PresetPickerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  presets: Preset[];
  value: number | null;
  onChange: (value: number | null) => void;
}

interface PresetOptionRowProps {
  title: string;
  description: string;
  selectedLabel: string;
  selected: boolean;
  onSelect: () => void;
  icon: React.ReactNode;
}

function PresetOptionRow({
  title,
  description,
  selectedLabel,
  selected,
  onSelect,
  icon,
}: PresetOptionRowProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "flex w-full items-start gap-3 rounded-2xl border px-4 py-3 text-left transition-colors",
        selected
          ? "border-primary/40 bg-primary/10 shadow-sm"
          : "border-border/70 bg-background hover:border-border hover:bg-accent/40",
      )}
    >
      <div className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-xl border border-border/60 bg-muted/60 text-foreground">
        {icon}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-medium text-foreground">
            {title}
          </span>
          {selected ? (
            <span className="inline-flex items-center rounded-full bg-primary/12 px-2 py-0.5 text-[11px] font-medium text-primary">
              <Check className="mr-1 size-3" />
              {selectedLabel}
            </span>
          ) : null}
        </div>
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      </div>
    </button>
  );
}

export function PresetPickerDialog({
  open,
  onOpenChange,
  presets,
  value,
  onChange,
}: PresetPickerDialogProps) {
  const { t } = useT("translation");

  const handleSelect = React.useCallback(
    (nextValue: number | null) => {
      onChange(nextValue);
      onOpenChange(false);
    },
    [onChange, onOpenChange],
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl gap-0 overflow-hidden p-0">
        <DialogHeader className="border-b border-border/60 px-6 py-5">
          <DialogTitle>
            {t("library.presetsPage.picker.dialogTitle")}
          </DialogTitle>
          <DialogDescription>
            {t("library.presetsPage.picker.dialogDescription")}
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="max-h-[min(65vh,28rem)]">
          <div className="space-y-2 p-4">
            <PresetOptionRow
              title={t("library.presetsPage.picker.none")}
              description={t("library.presetsPage.picker.noneDescription")}
              selectedLabel={t("library.presetsPage.picker.selected")}
              selected={value === null}
              onSelect={() => handleSelect(null)}
              icon={<Sparkles className="size-4" />}
            />

            {presets.map((preset) => {
              const Icon = getPresetIcon(preset.icon);
              return (
                <PresetOptionRow
                  key={preset.preset_id}
                  title={preset.name}
                  description={
                    preset.description?.trim() ||
                    t("library.presetsPage.emptyDescription")
                  }
                  selectedLabel={t("library.presetsPage.picker.selected")}
                  selected={preset.preset_id === value}
                  onSelect={() => handleSelect(preset.preset_id)}
                  icon={
                    <Icon
                      className="size-4"
                      style={preset.color ? { color: preset.color } : undefined}
                    />
                  }
                />
              );
            })}
          </div>
        </ScrollArea>

        <div className="border-t border-border/60 px-4 py-3">
          <Button
            type="button"
            variant="ghost"
            className="w-full justify-center rounded-xl"
            onClick={() => onOpenChange(false)}
          >
            {t("common.cancel")}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
