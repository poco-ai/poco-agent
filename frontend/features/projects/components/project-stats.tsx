"use client";

import * as React from "react";
import { CalendarClock, MessageSquareText, Sparkles } from "lucide-react";

import { useLanguage } from "@/hooks/use-language";
import { useT } from "@/lib/i18n/client";

interface ProjectStatsProps {
  sessionCount: number;
  presetCount: number;
  updatedAt?: string;
}

function formatUpdatedAt(updatedAt: string | undefined, locale: string) {
  if (!updatedAt) return null;

  const date = new Date(updatedAt);
  if (Number.isNaN(date.getTime())) return null;

  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
  }).format(date);
}

export function ProjectStats({
  sessionCount,
  presetCount,
  updatedAt,
}: ProjectStatsProps) {
  const { t } = useT("translation");
  const lng = useLanguage() || "en";
  const updatedLabel =
    formatUpdatedAt(updatedAt, lng) || t("project.detail.unknownUpdatedAt");

  const items = [
    {
      key: "sessions",
      icon: MessageSquareText,
      value: sessionCount.toString(),
      label: t("project.detail.stats.sessions"),
    },
    {
      key: "presets",
      icon: Sparkles,
      value: presetCount.toString(),
      label: t("project.detail.stats.presets"),
    },
    {
      key: "updated",
      icon: CalendarClock,
      value: updatedLabel,
      label: t("project.detail.stats.updated"),
    },
  ];

  return (
    <section className="grid gap-3 sm:grid-cols-3">
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <div
            key={item.key}
            className="rounded-2xl border border-border/60 bg-muted/20 px-4 py-4"
          >
            <div className="mb-3 flex items-center gap-2 text-muted-foreground">
              <Icon className="size-4" />
              <span className="text-xs font-medium uppercase tracking-[0.16em]">
                {item.label}
              </span>
            </div>
            <p className="text-lg font-semibold text-foreground">
              {item.value}
            </p>
          </div>
        );
      })}
    </section>
  );
}
