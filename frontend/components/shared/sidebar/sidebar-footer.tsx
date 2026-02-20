"use client";

import * as React from "react";
import {
  Bot,
  Trash2,
  X,
  Settings2,
  Moon,
  Sun,
  Languages,
  SlidersHorizontal,
} from "lucide-react";

import { useT } from "@/lib/i18n/client";
import { Button } from "@/components/ui/button";
import { SidebarFooter, useSidebar } from "@/components/ui/sidebar";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useThemeMode } from "@/hooks/use-theme-mode";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  useBackendPreference,
  type BackendOption,
} from "@/features/settings/hooks/use-backend-preference";
import { useSettingsLanguage } from "@/features/settings/hooks/use-settings-language";
import { useUserAccount } from "@/features/user/hooks/use-user-account";
import type { SettingsTabId } from "@/features/settings/types";

// ---------------------------------------------------------------------------
// Selection mode footer
// ---------------------------------------------------------------------------

interface SelectionFooterProps {
  selectedCount: number;
  onCancel: () => void;
  onDelete: () => void;
}

function SelectionFooter({
  selectedCount,
  onCancel,
  onDelete,
}: SelectionFooterProps) {
  const { t } = useT("translation");

  return (
    <div className="flex items-center justify-between w-full animate-in slide-in-from-bottom duration-200 px-1">
      <Button
        variant="ghost"
        size="icon"
        onClick={onCancel}
        className="size-8 text-muted-foreground hover:bg-sidebar-accent"
        title={t("common.cancel")}
      >
        <X className="size-4" />
      </Button>
      <div className="text-xs text-muted-foreground font-medium">
        {selectedCount}
      </div>
      <Button
        variant="ghost"
        size="icon"
        onClick={onDelete}
        disabled={selectedCount === 0}
        className="size-8 text-destructive hover:text-destructive hover:bg-destructive/10"
        title={t("common.delete")}
      >
        <Trash2 className="size-4" />
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Mobile footer
// ---------------------------------------------------------------------------

interface MobileFooterProps {
  onOpenSettings: () => void;
}

function MobileFooter({ onOpenSettings }: MobileFooterProps) {
  const { t } = useT("translation");
  const { profile } = useUserAccount();

  const userName = profile?.email
    ? profile.email.split("@")[0] || profile.email
    : t("sidebar.defaultUserName");
  const avatarInitial = userName.charAt(0).toUpperCase() || "U";

  return (
    <button
      type="button"
      onClick={onOpenSettings}
      className="flex w-full items-center justify-between gap-3 rounded-2xl border border-sidebar-border/60 bg-sidebar-accent/30 px-3 py-2 text-left text-sidebar-foreground transition hover:bg-sidebar-accent/50"
    >
      <div className="flex items-center gap-3">
        <Avatar className="size-10 border border-sidebar-border/60">
          {profile?.avatar ? (
            <AvatarImage src={profile.avatar} alt={userName} />
          ) : null}
          <AvatarFallback className="bg-sidebar text-sidebar-foreground/80">
            {avatarInitial}
          </AvatarFallback>
        </Avatar>
        <div className="flex flex-col text-left">
          <span className="text-sm font-semibold leading-tight truncate max-w-[120px]">
            {userName}
          </span>
          <span className="text-xs text-muted-foreground">
            {t("sidebar.settings")}
          </span>
        </div>
      </div>
      <span className="inline-flex size-8 items-center justify-center rounded-full bg-sidebar-accent/40">
        <Settings2 className="size-4" />
      </span>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Desktop footer (settings quick-access toolbar)
// ---------------------------------------------------------------------------

interface DesktopFooterProps {
  onOpenSettings: () => void;
}

function DesktopFooter({ onOpenSettings }: DesktopFooterProps) {
  const { t } = useT("translation");
  const { mode, setMode } = useThemeMode();
  const { currentLanguage, changeLanguage } = useSettingsLanguage();
  const { backend, setBackend } = useBackendPreference();

  const handleThemeSelect = React.useCallback(
    (nextTheme: string) => {
      if (nextTheme === "light" || nextTheme === "dark") setMode(nextTheme);
    },
    [setMode],
  );

  const handleBackendSelect = React.useCallback(
    (nextBackend: string) => {
      if (nextBackend === "claude-code")
        setBackend(nextBackend as BackendOption);
    },
    [setBackend],
  );

  return (
    <div className="flex w-full items-center justify-between px-1 group-data-[collapsible=icon]:px-0">
      <Button
        variant="ghost"
        size="icon"
        onClick={onOpenSettings}
        className="size-8 text-muted-foreground hover:bg-sidebar-accent"
        title={t("sidebar.settings")}
      >
        <SlidersHorizontal className="size-4" />
      </Button>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="size-8 text-muted-foreground hover:bg-sidebar-accent"
            title={t("settings.dialogTitle")}
          >
            <Settings2 className="size-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" side="top" className="w-48">
          {/* Backend */}
          <DropdownMenuSub>
            <DropdownMenuSubTrigger>
              <Bot className="size-4" />
              <span>{t("settings.backend")}</span>
            </DropdownMenuSubTrigger>
            <DropdownMenuSubContent>
              <DropdownMenuRadioGroup
                value={backend}
                onValueChange={handleBackendSelect}
              >
                <DropdownMenuRadioItem value="claude-code">
                  {t("settings.claudeCode")}
                </DropdownMenuRadioItem>
              </DropdownMenuRadioGroup>
            </DropdownMenuSubContent>
          </DropdownMenuSub>

          {/* Theme */}
          <DropdownMenuSub>
            <DropdownMenuSubTrigger>
              {mode === "dark" ? (
                <Moon className="size-4" />
              ) : (
                <Sun className="size-4" />
              )}
              <span>{t("settings.theme")}</span>
            </DropdownMenuSubTrigger>
            <DropdownMenuSubContent>
              <DropdownMenuRadioGroup
                value={mode}
                onValueChange={handleThemeSelect}
              >
                <DropdownMenuRadioItem value="light">
                  {t("settings.lightMode")}
                </DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="dark">
                  {t("settings.darkMode")}
                </DropdownMenuRadioItem>
              </DropdownMenuRadioGroup>
            </DropdownMenuSubContent>
          </DropdownMenuSub>

          {/* Language */}
          <DropdownMenuSub>
            <DropdownMenuSubTrigger>
              <Languages className="size-4" />
              <span>{t("settings.language")}</span>
            </DropdownMenuSubTrigger>
            <DropdownMenuSubContent>
              <DropdownMenuRadioGroup
                value={currentLanguage}
                onValueChange={changeLanguage}
              >
                <DropdownMenuRadioItem value="en">
                  {t("settings.english")}
                </DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="zh">
                  {t("settings.simplifiedChinese")}
                </DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="fr">
                  {t("settings.french")}
                </DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="ja">
                  {t("settings.japanese")}
                </DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="de">
                  {t("settings.german")}
                </DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="ru">
                  {t("settings.russian")}
                </DropdownMenuRadioItem>
              </DropdownMenuRadioGroup>
            </DropdownMenuSubContent>
          </DropdownMenuSub>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Composed footer
// ---------------------------------------------------------------------------

interface SidebarFooterSectionProps {
  isSelectionMode: boolean;
  selectedCount: number;
  onCancelSelection: () => void;
  onDeleteSelected: () => void;
  onOpenSettings: (tab?: SettingsTabId) => void;
}

export function SidebarFooterSection({
  isSelectionMode,
  selectedCount,
  onCancelSelection,
  onDeleteSelected,
  onOpenSettings,
}: SidebarFooterSectionProps) {
  const { isMobile, setOpenMobile } = useSidebar();

  const handleOpenSettings = React.useCallback(() => {
    onOpenSettings();
    if (isMobile) setOpenMobile(false);
  }, [isMobile, onOpenSettings, setOpenMobile]);

  return (
    <SidebarFooter className="border-t border-sidebar-border p-2 group-data-[collapsible=icon]:p-2 relative bg-sidebar">
      {isSelectionMode ? (
        <SelectionFooter
          selectedCount={selectedCount}
          onCancel={onCancelSelection}
          onDelete={onDeleteSelected}
        />
      ) : isMobile ? (
        <MobileFooter onOpenSettings={handleOpenSettings} />
      ) : (
        <DesktopFooter onOpenSettings={() => onOpenSettings()} />
      )}
    </SidebarFooter>
  );
}
