"use client";

import * as React from "react";

import { useT } from "@/lib/i18n/client";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type {
  RunScheduleMode,
  RunScheduleValue,
} from "@/features/task-composer/model/run-schedule";

function pad2(value: number): string {
  return String(value).padStart(2, "0");
}

function toDatetimeLocal(date: Date): string {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}T${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
}

function humanizeDatetimeLocal(value: string): string {
  const trimmed = (value || "").trim();
  if (!trimmed) return "";
  return trimmed.replace("T", " ");
}

function defaultScheduledAt(): string {
  const d = new Date();
  d.setMinutes(d.getMinutes() + 30);
  d.setSeconds(0);
  d.setMilliseconds(0);
  return toDatetimeLocal(d);
}

export function RunScheduleDialog({
  open,
  onOpenChange,
  value,
  onSave,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  value: RunScheduleValue;
  onSave: (next: RunScheduleValue) => void;
}) {
  const { t } = useT("translation");

  const [mode, setMode] = React.useState<RunScheduleMode>(value.schedule_mode);
  const [scheduledAt, setScheduledAt] = React.useState<string>(
    value.scheduled_at || "",
  );
  const [timezone, setTimezone] = React.useState<string>(
    value.timezone || "UTC",
  );

  React.useEffect(() => {
    if (!open) return;
    setMode(value.schedule_mode);
    setScheduledAt(value.scheduled_at || "");
    setTimezone(value.timezone || "UTC");
  }, [open, value]);

  const preview = React.useMemo(() => {
    if (mode === "nightly") return t("hero.runSchedule.summary.nightly");
    if (mode === "scheduled") {
      return t("hero.runSchedule.summary.scheduled", {
        datetime: humanizeDatetimeLocal(scheduledAt),
        timezone,
      });
    }
    return t("hero.runSchedule.summary.immediate");
  }, [mode, scheduledAt, t, timezone]);

  const canSave = mode !== "scheduled" || (scheduledAt || "").trim().length > 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{t("hero.runSchedule.dialogTitle")}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="run-schedule-mode">
              {t("hero.runSchedule.fields.mode")}
            </Label>
            <Select
              value={mode}
              onValueChange={(v) => {
                const next = v as RunScheduleMode;
                setMode(next);
                if (next === "scheduled" && !(scheduledAt || "").trim()) {
                  setScheduledAt(defaultScheduledAt());
                }
              }}
            >
              <SelectTrigger id="run-schedule-mode" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="immediate">
                  {t("hero.runSchedule.modes.immediate")}
                </SelectItem>
                <SelectItem value="scheduled">
                  {t("hero.runSchedule.modes.scheduled")}
                </SelectItem>
                <SelectItem value="nightly">
                  {t("hero.runSchedule.modes.nightly")}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {mode === "scheduled" ? (
            <div className="space-y-2">
              <Label htmlFor="run-schedule-at">
                {t("hero.runSchedule.fields.scheduledAt")}
              </Label>
              <Input
                id="run-schedule-at"
                type="datetime-local"
                value={scheduledAt}
                onChange={(e) => setScheduledAt(e.target.value)}
              />
              <div className="text-xs text-muted-foreground">
                {t("hero.runSchedule.timezoneHint", { timezone })}
              </div>
            </div>
          ) : null}

          <div className="text-xs text-muted-foreground">
            {t("hero.runSchedule.preview", { summary: preview })}
          </div>
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            {t("common.cancel")}
          </Button>
          <Button
            type="button"
            disabled={!canSave}
            onClick={() => {
              onSave({
                schedule_mode: mode,
                timezone: timezone.trim() || "UTC",
                scheduled_at:
                  mode === "scheduled" ? (scheduledAt || "").trim() : null,
              });
              onOpenChange(false);
            }}
          >
            {t("common.save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
