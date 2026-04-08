"use client";

import * as React from "react";
import { Home, LogOut, Settings } from "lucide-react";

import { useT } from "@/lib/i18n/client";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useUserAccount } from "@/features/user/hooks/use-user-account";
import type { SettingsTabId } from "@/features/settings/types";

interface UserMenuProps {
  trigger?: React.ReactNode;
  onOpenSettings: (tab?: SettingsTabId) => void;
}

export function UserMenu({ trigger, onOpenSettings }: UserMenuProps) {
  const { t } = useT("translation");
  const { profile, logout } = useUserAccount();
  const [isDesktop, setIsDesktop] = React.useState(false);

  React.useEffect(() => {
    if (typeof window === "undefined") return;
    const mediaQuery = window.matchMedia("(min-width: 768px)");
    const updateMatches = () => setIsDesktop(mediaQuery.matches);
    updateMatches();
    mediaQuery.addEventListener("change", updateMatches);
    return () => mediaQuery.removeEventListener("change", updateMatches);
  }, []);

  const displayName =
    profile?.displayName || profile?.email || t("sidebar.defaultUserName");
  const avatarInitial = displayName.charAt(0).toUpperCase() || "U";

  const triggerNode = trigger || (
    <Avatar className="size-8 cursor-pointer">
      {profile?.avatar ? (
        <AvatarImage src={profile.avatar} alt={displayName} />
      ) : null}
      <AvatarFallback className="bg-muted text-xs text-muted-foreground">
        {avatarInitial}
      </AvatarFallback>
    </Avatar>
  );

  const content = (
    <div className="flex flex-col gap-1">
      <Button
        variant="ghost"
        size="sm"
        className="h-8 justify-start px-2 font-normal"
        onClick={() => window.open("https://poco-ai.com", "_blank")}
      >
        <Home className="mr-2 size-4" />
        {t("userMenu.home")}
      </Button>
      <Button
        variant="ghost"
        size="sm"
        className="h-8 justify-start px-2 font-normal"
        onClick={() => onOpenSettings()}
      >
        <Settings className="mr-2 size-4" />
        {t("userMenu.settings")}
      </Button>
      <Separator className="my-1" />
      <Button
        variant="ghost"
        size="sm"
        className="h-8 justify-start px-2 font-normal text-destructive hover:bg-destructive/10 hover:text-destructive"
        onClick={() => void logout()}
      >
        <LogOut className="mr-2 size-4" />
        {t("userMenu.logout")}
      </Button>
    </div>
  );

  if (isDesktop) {
    return (
      <HoverCard openDelay={200} closeDelay={150}>
        <HoverCardTrigger asChild>{triggerNode}</HoverCardTrigger>
        <HoverCardContent className="w-64 p-2" align="end" sideOffset={8}>
          {content}
        </HoverCardContent>
      </HoverCard>
    );
  }

  return (
    <Popover>
      <PopoverTrigger asChild>{triggerNode}</PopoverTrigger>
      <PopoverContent className="w-64 p-2" align="end" sideOffset={8}>
        {content}
      </PopoverContent>
    </Popover>
  );
}
