"use client";

import { Layers, MessageSquare, Monitor } from "lucide-react";
import { PanelHeader } from "@/components/shared/panel-header";
import { ChatInput } from "@/features/chat/components/execution/chat-panel/chat-input";
import { SkeletonCircle, SkeletonItem } from "@/components/ui/skeleton-shimmer";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useT } from "@/lib/i18n/client";

const shimmerDelay = (index: number) => ({
  animationDelay: `${index * 0.08}s`,
});

export function ChatPanelSkeleton() {
  const { t } = useT("translation");
  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      <PanelHeader
        icon={MessageSquare}
        title={t("chat.executionTitle")}
        description={t("chat.emptyStateDesc")}
      />
      <div className="flex-1 min-h-0 overflow-hidden px-4">
        <div
          className="flex h-full w-full flex-col gap-4 py-6"
          aria-busy="true"
        >
          <div className="flex items-start gap-3">
            <SkeletonCircle className="h-8 w-8" style={shimmerDelay(0)} />
            <SkeletonItem className="w-[70%]" style={shimmerDelay(1)} />
          </div>
          <div className="flex items-start justify-end">
            <SkeletonItem className="w-[68%]" style={shimmerDelay(2)} />
          </div>
          <div className="flex items-start gap-3">
            <SkeletonCircle className="h-8 w-8" style={shimmerDelay(3)} />
            <SkeletonItem className="w-[60%]" style={shimmerDelay(4)} />
          </div>
          <div className="flex items-start justify-end">
            <SkeletonItem className="w-[55%]" style={shimmerDelay(5)} />
          </div>
        </div>
      </div>
      <ChatInput onSend={() => undefined} disabled />
    </div>
  );
}

export function RightPanelSkeleton() {
  const { t } = useT("translation");
  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden bg-muted/30">
      <PanelHeader
        content={
          <Tabs defaultValue="computer" className="min-w-0">
            <TabsList className="min-w-0 max-w-full overflow-hidden font-serif">
              <TabsTrigger value="computer" className="!flex-none min-w-0 px-2">
                <Monitor className="size-4" />
                <span className="whitespace-nowrap">
                  {t("mobile.computer")}
                </span>
              </TabsTrigger>
              <TabsTrigger
                value="artifacts"
                className="!flex-none min-w-0 px-2"
              >
                <Layers className="size-4" />
                <span className="whitespace-nowrap">
                  {t("mobile.artifacts")}
                </span>
              </TabsTrigger>
            </TabsList>
          </Tabs>
        }
      />
      <div className="flex-1 min-h-0 overflow-hidden p-3 sm:p-4">
        <div className="flex h-full flex-col gap-3">
          <div className="flex-1 min-h-0 overflow-hidden rounded-xl border bg-card p-4">
            <SkeletonItem
              className="h-full w-full min-h-0"
              style={shimmerDelay(0)}
            />
          </div>
          <SkeletonItem
            className="h-10 min-h-0 w-full"
            style={shimmerDelay(1)}
          />
          <div className="h-[220px] min-w-0 overflow-hidden rounded-xl border bg-card p-3">
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, index) => (
                <SkeletonItem
                  key={`timeline-skeleton-${index}`}
                  className="h-10 min-h-0 w-full rounded-md px-2 py-2"
                  style={shimmerDelay(index + 2)}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
