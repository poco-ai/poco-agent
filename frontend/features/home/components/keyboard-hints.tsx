"use client";

import * as React from "react";

import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

interface KeyboardHintsProps {
  className?: string;
}

export function KeyboardHints({ className }: KeyboardHintsProps) {
  const { t } = useT("translation");

  return (
    <div
      className={cn(
        "pointer-events-none flex flex-wrap items-center justify-center gap-1 text-[11px] text-muted-foreground/70",
        className,
      )}
    >
      <kbd className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px]">
        /
      </kbd>
      <span className="text-muted-foreground/60">
        {t("hints.slashCommand")}
        {t("hints.separator")}
      </span>
      <kbd className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px]">
        Shift
      </kbd>
      <span className="text-muted-foreground/60">+</span>
      <kbd className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px]">
        Enter
      </kbd>
      <span className="text-muted-foreground/60">
        {t("hints.newLine")}
        {t("hints.separator")}
      </span>
      <kbd className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px]">
        Enter
      </kbd>
      <span className="text-muted-foreground/60">{t("hints.send")}</span>
    </div>
  );
}
