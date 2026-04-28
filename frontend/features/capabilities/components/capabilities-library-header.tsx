"use client";

import type * as React from "react";

import { Sparkles } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { PageHeaderShell } from "@/components/shared/page-header-shell";
import { useT } from "@/lib/i18n/client";

interface CapabilitiesLibraryHeaderProps {
  mobileLeading?: React.ReactNode;
  hideSidebarTrigger?: boolean;
  title?: string;
  subtitle?: string;
  icon?: LucideIcon;
}

export function CapabilitiesLibraryHeader({
  mobileLeading,
  hideSidebarTrigger,
  title,
  subtitle,
  icon: Icon = Sparkles,
}: CapabilitiesLibraryHeaderProps) {
  const { t } = useT("translation");
  const headerTitle = title ?? t("library.title");
  const headerSubtitle = subtitle ?? t("library.subtitle");

  return (
    <PageHeaderShell
      hideSidebarTrigger={hideSidebarTrigger}
      mobileLeading={mobileLeading}
      left={
        <div className="flex min-w-0 items-center gap-3">
          <Icon
            className="hidden size-5 text-muted-foreground md:block"
            aria-hidden="true"
          />
          <div className="min-w-0">
            <p className="text-base font-semibold leading-tight">
              {headerTitle}
            </p>
            <p className="text-xs text-muted-foreground">{headerSubtitle}</p>
          </div>
        </div>
      }
    />
  );
}
