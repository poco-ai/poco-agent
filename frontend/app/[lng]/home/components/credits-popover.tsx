"use client";

import * as React from "react";
import { ChevronRight, Sparkles, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";
import { Separator } from "@/components/ui/separator";

import { useUserAccount } from "@/hooks/use-user-account";

interface CreditsPopoverProps {
  trigger: React.ReactNode;
  // Optional override or initial data
  initialCredits?: number;
}

export function CreditsPopover({
  trigger,
  initialCredits,
}: CreditsPopoverProps) {
  const { profile, credits, isLoading } = useUserAccount();

  return (
    <HoverCard openDelay={200}>
      <HoverCardTrigger asChild>{trigger}</HoverCardTrigger>
      <HoverCardContent
        className="w-80 p-0 overflow-hidden border-border bg-card shadow-xl"
        align="end"
        sideOffset={8}
      >
        <div className="flex flex-col">
          {/* Header Section */}
          <div className="flex items-center justify-between p-5 pb-4">
            <h3 className="text-xl font-semibold tracking-tight">
              {isLoading ? "..." : profile?.planName}
            </h3>
          </div>

          <Separator className="bg-border/50 border-dashed" />

          {/* Credits Section */}
          <div className="p-5 space-y-6">
            {/* Total Credits */}
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Sparkles className="size-4" />
                  <span className="text-sm font-medium">积分</span>
                </div>
                <span className="text-xl font-bold tracking-tight">
                  {isLoading
                    ? "..."
                    : (credits?.total ?? initialCredits)?.toLocaleString()}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs text-muted-foreground/60 pl-6">
                <span>免费积分</span>
                <span>
                  {isLoading ? "..." : credits?.free.toLocaleString()}
                </span>
              </div>
            </div>

            {/* Daily Refresh Section */}
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <RefreshCw className="size-4" />
                  <span className="text-sm font-medium">每日刷新积分</span>
                </div>
                <span className="text-xl font-bold tracking-tight">
                  {isLoading ? "..." : credits?.dailyRefreshCurrent}
                </span>
              </div>
              <div className="text-xs text-muted-foreground/60 pl-6">
                每天 {isLoading ? "..." : credits?.refreshTime} 刷新为{" "}
                {isLoading ? "..." : credits?.dailyRefreshMax}
              </div>
            </div>
          </div>

          {/* Footer Link */}
          <div className="p-4 pt-0">
            <Button
              variant="ghost"
              className="h-auto p-0 text-muted-foreground hover:text-primary text-xs flex items-center gap-1 hover:bg-transparent"
            >
              查看使用情况
              <ChevronRight className="size-3" />
            </Button>
          </div>
        </div>
      </HoverCardContent>
    </HoverCard>
  );
}
