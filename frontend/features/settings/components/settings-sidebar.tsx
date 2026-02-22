"use client";

import * as React from "react";
import Image from "next/image";
import { ExternalLink, HelpCircle } from "lucide-react";

import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n/client";
import type {
  SettingsSidebarItem,
  SettingsTabId,
} from "@/features/settings/types";

interface SettingsSidebarProps {
  items: SettingsSidebarItem[];
  activeTab: SettingsTabId;
  onSelectTab: (tab: SettingsTabId) => void;
}

export function SettingsSidebar({
  items,
  activeTab,
  onSelectTab,
}: SettingsSidebarProps) {
  const { t } = useT("translation");

  return (
    <div className="w-64 shrink-0 border-r border-border bg-muted/30">
      <div className="flex h-full flex-col">
        <div className="flex items-center gap-2 px-4 py-3">
          <span className="flex size-6.5 shrink-0 items-center justify-center">
            <Image
              src="/logo.svg"
              alt="Poco"
              width={26}
              height={26}
              sizes="26px"
              className="size-full object-cover"
            />
          </span>
          <span className="text-2xl font-bold leading-none tracking-tight text-foreground font-brand">
            Poco
          </span>
        </div>

        <div className="min-h-0 flex-1 space-y-0.5 overflow-y-auto px-2 py-2">
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelectTab(item.id)}
              className={cn(
                "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                activeTab === item.id
                  ? "bg-accent font-medium text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
              )}
            >
              <item.icon className="size-4" />
              {item.label}
            </button>
          ))}
        </div>

        <div className="shrink-0 border-t border-border p-4">
          <button
            type="button"
            onClick={() => window.open(t("settings.getHelpUrl"), "_blank")}
            className="flex w-full items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <HelpCircle className="size-4" />
            <span>{t("settings.getHelp")}</span>
            <ExternalLink className="ml-auto size-3" />
          </button>
        </div>
      </div>
    </div>
  );
}
