"use client";

import * as React from "react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { ModelSelector } from "./model-selector";
import { UsageTooltip } from "./usage-tooltip";
import type { UsageStats } from "@/types";
import { PageHeaderShell } from "@/components/shared/page-header-shell";
import type {
  ModelCatalogOption,
  ModelSelection,
} from "@/features/chat/lib/model-catalog";

// Default usage stats for now
const DEFAULT_USAGE_STATS: UsageStats = {
  credits: 0,
  tokensUsed: 0,
  duration: 0,
  todayUsage: 0,
  weekUsage: 0,
  monthUsage: 0,
};

interface ChatHeaderProps {
  modelOptions: ModelCatalogOption[];
  selectedModel: ModelSelection | null;
  defaultSelection?: ModelSelection | null;
  onModelChange: (selection: ModelSelection | null) => void;
  title?: string;
}

export function ChatHeader({
  modelOptions,
  selectedModel,
  defaultSelection,
  onModelChange,
  title,
}: ChatHeaderProps) {
  const usageStats = React.useMemo(() => DEFAULT_USAGE_STATS, []);

  return (
    <PageHeaderShell
      left={
        <div className="flex items-center gap-3 sm:gap-4">
          <ModelSelector
            options={modelOptions}
            selection={selectedModel}
            defaultSelection={defaultSelection}
            fallbackLabel={selectedModel?.modelId || undefined}
            onChange={onModelChange}
          />
          {title ? (
            <>
              <div className="hidden h-4 w-px bg-border sm:block" />
              <h1 className="max-w-[140px] truncate text-sm font-medium sm:max-w-md sm:text-base font-serif">
                {title}
              </h1>
            </>
          ) : null}
        </div>
      }
      right={
        <div className="flex items-center gap-4">
          <UsageTooltip stats={usageStats} />
          <Avatar className="size-8">
            <AvatarFallback className="bg-muted text-muted-foreground text-xs font-medium">
              U
            </AvatarFallback>
          </Avatar>
        </div>
      }
    />
  );
}
