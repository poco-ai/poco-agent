"use client";

import {
  ExternalLink,
  HelpCircle,
  RefreshCw,
  Sparkles,
  UserCog,
} from "lucide-react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { useT } from "@/lib/i18n/client";
import type { UserCredits, UserProfile } from "@/features/user/types";

interface AccountSettingsTabProps {
  profile: UserProfile | null;
  credits: UserCredits | null;
  isLoading: boolean;
}

export function AccountSettingsTab({
  profile,
  credits,
  isLoading,
}: AccountSettingsTabProps) {
  const { t } = useT("translation");

  const displayName =
    profile?.displayName || profile?.email || profile?.id || "U";

  return (
    <div className="flex-1 overflow-y-auto p-5">
      <div className="mb-6 flex items-center gap-4">
        <Avatar className="size-14 bg-primary">
          {profile?.avatar ? (
            <AvatarImage src={profile.avatar} alt={displayName} />
          ) : null}
          <AvatarFallback className="bg-primary text-xl text-primary-foreground">
            {displayName[0]?.toUpperCase() || "U"}
          </AvatarFallback>
        </Avatar>

        <div className="min-w-0 flex-1">
          {isLoading ? (
            <div className="space-y-2">
              <div className="h-5 w-32 animate-pulse rounded bg-muted" />
              <div className="h-4 w-48 animate-pulse rounded bg-muted" />
            </div>
          ) : (
            <>
              <div className="truncate text-base font-medium">
                {displayName}
              </div>
              <div className="truncate text-sm text-muted-foreground">
                {profile?.email || profile?.id}
              </div>
            </>
          )}
        </div>

        <div className="flex gap-2">
          <Button variant="outline" size="icon" className="size-8">
            <UserCog className="size-4" />
          </Button>
          <Button variant="outline" size="icon" className="size-8">
            <ExternalLink className="size-4" />
          </Button>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-border bg-card">
        <div className="flex items-center justify-between border-b border-dashed border-border p-4">
          <span className="font-medium">{profile?.planName}</span>
          <Button
            size="sm"
            className="h-7 rounded-full bg-primary px-4 text-xs font-bold text-primary-foreground hover:bg-primary/90"
          >
            {t("settings.upgrade")}
          </Button>
        </div>

        <div className="space-y-5 p-4">
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Sparkles className="size-4" />
                <span className="text-sm font-medium">
                  {t("settings.credits")}
                </span>
                <HelpCircle className="size-3.5 opacity-50" />
              </div>
              <span className="text-xl font-bold tracking-tight">
                {credits?.total}
              </span>
            </div>
            <div className="flex items-center justify-between pl-6 text-xs text-muted-foreground/60">
              <span>{t("settings.freeCredits")}</span>
              <span>{credits?.free}</span>
            </div>
          </div>

          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-muted-foreground">
                <RefreshCw className="size-4" />
                <span className="text-sm font-medium">
                  {t("settings.dailyRefresh")}
                </span>
                <HelpCircle className="size-3.5 opacity-50" />
              </div>
              <span className="text-xl font-bold tracking-tight">
                {credits?.dailyRefreshCurrent}
              </span>
            </div>
            <div className="pl-6 text-xs text-muted-foreground/60">
              {t("settings.dailyRefreshHint", {
                time: credits?.refreshTime,
                max: credits?.dailyRefreshMax,
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
