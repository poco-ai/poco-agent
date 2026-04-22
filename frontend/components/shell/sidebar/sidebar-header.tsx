"use client";

import * as React from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import {
  PanelLeftClose,
  PanelLeftOpen,
  PenSquare,
  Search,
  Sparkles,
  Bookmark,
  Clock,
  Brain,
  Shield,
} from "lucide-react";

import { useT } from "@/lib/i18n/client";
import { useLanguage } from "@/hooks/use-language";
import { useMemoryFeatureEnabled } from "@/hooks/use-memory-feature-enabled";
import { useMobileSidebar } from "@/hooks/use-mobile-sidebar";
import { useUserAccount } from "@/features/user";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";

// ---------------------------------------------------------------------------
// Navigation items
// ---------------------------------------------------------------------------

const TOP_NAV_ITEMS = [
  {
    id: "search",
    labelKey: "sidebar.search",
    defaultLabel: "Search",
    icon: Search,
    href: null,
  },
  {
    id: "capabilities",
    labelKey: "sidebar.library",
    defaultLabel: "Capabilities",
    icon: Sparkles,
    href: "/capabilities",
  },
  {
    id: "presets",
    labelKey: "sidebar.presets",
    defaultLabel: "Presets",
    icon: Bookmark,
    href: "/presets",
  },
  {
    id: "scheduled-tasks",
    labelKey: "sidebar.scheduledTasks",
    defaultLabel: "Scheduled Tasks",
    icon: Clock,
    href: "/capabilities/scheduled-tasks",
  },
  {
    id: "memories",
    labelKey: "sidebar.memories",
    defaultLabel: "Memories",
    icon: Brain,
    href: "/memories",
  },
  {
    id: "admin",
    labelKey: "sidebar.admin",
    defaultLabel: "System Admin",
    icon: Shield,
    href: "/admin",
  },
] as const;

const ICON_ANIMATIONS: Record<string, string> = {
  search:
    "transition-transform duration-300 group-hover/menu-item:scale-110 group-hover/menu-item:-translate-y-0.5",
  capabilities:
    "transition-all duration-300 group-hover/menu-item:rotate-12 group-hover/menu-item:scale-110",
  presets:
    "transition-transform duration-300 group-hover/menu-item:-translate-y-0.5 group-hover/menu-item:scale-110",
  "scheduled-tasks":
    "transition-transform duration-500 group-hover/menu-item:rotate-[360deg]",
  memories:
    "transition-transform duration-300 group-hover/menu-item:scale-110 group-hover/menu-item:rotate-6",
  admin:
    "transition-transform duration-300 group-hover/menu-item:scale-110 group-hover/menu-item:-translate-y-0.5",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface SidebarHeaderSectionProps {
  onNewTask: () => void;
  onOpenSearch: () => void;
}

export function SidebarHeaderSection({
  onNewTask,
  onOpenSearch,
}: SidebarHeaderSectionProps) {
  const { t } = useT("translation");
  const router = useRouter();
  const lng = useLanguage();
  const memoryFeatureEnabled = useMemoryFeatureEnabled();
  const { profile } = useUserAccount();
  const isSystemAdmin = profile?.systemRole === "admin";
  const { toggleSidebar } = useSidebar();
  const { closeMobileSidebar } = useMobileSidebar();
  const isMacPlatform = React.useMemo(() => {
    if (typeof navigator === "undefined") return false;
    return /Mac|iPhone|iPad|iPod/.test(navigator.platform);
  }, []);

  return (
    <SidebarHeader className="px-2 gap-2 pb-2">
      {/* Logo and collapse toggle - logo in fixed 3rem zone so it doesn't move during collapse */}
      <div className="mb-3 flex items-center pt-2 -mx-2">
        <div className="flex w-[var(--sidebar-width-icon)] shrink-0 items-center justify-center">
          <button
            onClick={toggleSidebar}
            className="group/logo relative flex size-6.5 shrink-0 items-center justify-center overflow-hidden transition-all active:scale-95"
            type="button"
            style={{ border: "none", boxShadow: "none" }}
          >
            <span className="flex items-center justify-center w-full h-full">
              <Image
                src="/logo.svg"
                alt="Poco"
                width={26}
                height={26}
                sizes="26px"
                className="size-full object-cover transition-opacity group-data-[collapsible=icon]:group-hover/logo:opacity-0"
                style={{ border: "none", boxShadow: "none" }}
              />
            </span>
            <PanelLeftOpen className="absolute hidden size-4 group-data-[collapsible=icon]:group-hover/logo:block" />
          </button>
        </div>
        <div className="flex min-w-0 flex-1 items-center justify-between gap-1 pl-0.1 pr-2 group-data-[collapsible=icon]:hidden">
          <span
            onClick={() => router.push(lng ? `/${lng}/home` : "/")}
            className="text-2xl font-bold tracking-tight text-sidebar-foreground cursor-pointer transition-opacity font-brand"
          >
            Poco
          </span>
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleSidebar}
            className="size-8 shrink-0 text-sidebar-foreground hover:bg-sidebar-accent focus-visible:ring-0 focus-visible:border-transparent focus-visible:outline-none"
          >
            <PanelLeftClose className="size-4" />
          </Button>
        </div>
      </div>

      {/* New task button */}
      <SidebarMenu className="group-data-[collapsible=icon]:px-0">
        <SidebarMenuItem>
          <SidebarMenuButton
            onClick={() => {
              onNewTask();
              closeMobileSidebar();
            }}
            data-onboarding="sidebar-new-task"
            className="h-[36px] min-w-0 max-w-[calc(var(--sidebar-width)-16px)] w-full justify-start gap-3 rounded-[10px] px-3 py-[7.5px] text-muted-foreground transition-colors hover:bg-sidebar-accent focus-visible:ring-0 focus-visible:outline-none group-data-[collapsible=icon]:w-[var(--sidebar-width-icon)] group-data-[collapsible=icon]:max-w-[var(--sidebar-width-icon)] group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0 group/new-task"
            tooltip={t("sidebar.newTaskWithShortcut", {
              shortcut: isMacPlatform ? "⇧⌘O" : "Shift+Ctrl+O",
              defaultValue: "New Task (⇧⌘O)",
            })}
          >
            <PenSquare className="size-4 shrink-0 transition-transform duration-200 group-hover/new-task:rotate-12 group-hover/new-task:scale-110" />
            <span className="text-sm truncate group-data-[collapsible=icon]:hidden">
              {t("sidebar.newTask")}
            </span>
            <span className="ml-auto text-xs text-muted-foreground opacity-0 transition-opacity group-hover/new-task:opacity-70 group-data-[collapsible=icon]:hidden">
              {isMacPlatform ? "⇧⌘O" : "⇧Ctrl+O"}
            </span>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>

      {/* Navigation items */}
      {TOP_NAV_ITEMS.map(({ id, labelKey, defaultLabel, icon: Icon, href }) => {
        if (id === "memories" && !memoryFeatureEnabled) {
          return null;
        }
        if (id === "admin" && !isSystemAdmin) {
          return null;
        }

        const isSearch = id === "search";
        const iconAnimation = ICON_ANIMATIONS[id] ?? "";

        return (
          <SidebarMenu key={id} className="group-data-[collapsible=icon]:px-0">
            <SidebarMenuItem className="group/menu-item">
              <SidebarMenuButton
                onClick={() => {
                  if (isSearch) {
                    onOpenSearch();
                    closeMobileSidebar();
                    return;
                  }
                  if (href) {
                    router.push(lng ? `/${lng}${href}` : href);
                    closeMobileSidebar();
                  }
                }}
                data-onboarding={
                  id === "capabilities" ? "sidebar-capabilities" : undefined
                }
                className={cn(
                  "h-[36px] min-w-0 max-w-[calc(var(--sidebar-width)-16px)] w-full justify-start gap-3 rounded-[10px] px-3 py-[7.5px] text-muted-foreground transition-colors hover:bg-sidebar-accent focus-visible:ring-0 focus-visible:outline-none group-data-[collapsible=icon]:w-[var(--sidebar-width-icon)] group-data-[collapsible=icon]:max-w-[var(--sidebar-width-icon)] group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0",
                )}
                tooltip={t(labelKey, defaultLabel)}
              >
                <Icon className={cn("size-4 shrink-0", iconAnimation)} />
                <span className="text-sm truncate group-data-[collapsible=icon]:hidden">
                  {t(labelKey, defaultLabel)}
                </span>
                {id === "search" && (
                  <span className="ml-auto text-xs text-muted-foreground opacity-0 transition-opacity group-hover/menu-item:opacity-70 group-data-[collapsible=icon]:hidden">
                    {isMacPlatform ? "⌘K" : "Ctrl+K"}
                  </span>
                )}
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        );
      })}
    </SidebarHeader>
  );
}
