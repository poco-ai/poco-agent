"use client";

import * as React from "react";
import { ChevronDown, Coins } from "lucide-react";

import { useT } from "@/lib/i18n/client";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { CreditsPopover } from "./credits-popover";
import { UserMenu } from "@/features/user/components/user-menu";
import { RepoLinkButton } from "@/components/shared/repo-link-button";
import { PageHeaderShell } from "@/components/shared/page-header-shell";
import type { SettingsTabId } from "@/features/settings/types";
import type { ModelConfigResponse } from "@/features/chat/types";

interface HomeHeaderProps {
  onOpenSettings?: (tab?: SettingsTabId) => void;
  modelConfig?: ModelConfigResponse | null;
  selectedModel?: string | null;
  onSelectModel?: (model: string | null) => void;
}

export function HomeHeader({
  onOpenSettings,
  modelConfig,
  selectedModel,
  onSelectModel,
}: HomeHeaderProps) {
  const { t } = useT("translation");

  const defaultModel = (modelConfig?.default_model || "").trim();
  const effectiveModel = (selectedModel || defaultModel).trim();

  const modelItems = React.useMemo(() => {
    const items: string[] = [];
    const seen = new Set<string>();

    const push = (value: string) => {
      const cleaned = (value || "").trim();
      if (!cleaned) return;
      if (seen.has(cleaned)) return;
      seen.add(cleaned);
      items.push(cleaned);
    };

    push(defaultModel);
    for (const item of modelConfig?.model_list || []) {
      push(item);
    }
    return items;
  }, [defaultModel, modelConfig?.model_list]);

  const isSelectorReady = Boolean(defaultModel && onSelectModel);

  return (
    <PageHeaderShell
      left={
        <div className="flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-10 gap-2 px-2"
                title={t("header.switchModel")}
                disabled={!isSelectorReady}
              >
                <span className="min-w-0 max-w-[220px] truncate text-base font-medium font-serif">
                  {effectiveModel || t("status.loading")}
                </span>
                <ChevronDown className="size-3.5 text-muted-foreground" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-60">
              {defaultModel ? (
                <>
                  <DropdownMenuItem
                    onClick={() => onSelectModel?.(null)}
                    className="flex items-center justify-between gap-3"
                  >
                    <div className="min-w-0">
                      <div className="truncate font-medium">{defaultModel}</div>
                      <div className="text-xs text-muted-foreground">
                        {t("models.defaultTag")}
                      </div>
                    </div>
                    {!selectedModel ? (
                      <div className="text-primary text-sm">✓</div>
                    ) : null}
                  </DropdownMenuItem>
                  {modelItems.filter((m) => m !== defaultModel).length > 0 ? (
                    <DropdownMenuSeparator />
                  ) : null}
                </>
              ) : null}

              {modelItems
                .filter((m) => m !== defaultModel)
                .map((m) => (
                  <DropdownMenuItem
                    key={m}
                    onClick={() => onSelectModel?.(m)}
                    className="flex items-center justify-between gap-3"
                  >
                    <div className="min-w-0 truncate font-medium">{m}</div>
                    {m === selectedModel ? (
                      <div className="text-primary text-sm">✓</div>
                    ) : null}
                  </DropdownMenuItem>
                ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      }
      right={
        <div className="flex items-center gap-1">
          <RepoLinkButton
            size="sm"
            className="flex size-8 items-center justify-center rounded-full p-0"
          />
          <CreditsPopover
            trigger={
              <Button
                variant="ghost"
                size="sm"
                className="mx-1 flex size-8 items-center justify-center rounded-full p-0 text-muted-foreground hover:bg-accent hover:text-foreground"
              >
                <Coins className="size-3.5" />
              </Button>
            }
            onViewUsage={() => onOpenSettings?.("usage")}
          />
          <UserMenu onOpenSettings={(tab) => onOpenSettings?.(tab)} />
        </div>
      }
    />
  );
}
