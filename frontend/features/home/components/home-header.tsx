"use client";

import * as React from "react";
import { Coins } from "lucide-react";

import { useT } from "@/lib/i18n/client";
import { Button } from "@/components/ui/button";
import { CreditsPopover } from "./credits-popover";
import { UserMenu } from "@/features/user/components/user-menu";
import { RepoLinkButton } from "@/components/shared/repo-link-button";
import { PageHeaderShell } from "@/components/shared/page-header-shell";
import type { SettingsTabId } from "@/features/settings/types";
import type { ModelConfigResponse } from "@/features/chat/types";
import type {
  ModelCatalogOption,
  ModelSelection,
} from "@/features/chat/lib/model-catalog";
import { ModelSelector } from "@/features/chat/components/chat/model-selector";

interface HomeHeaderProps {
  onOpenSettings?: (tab?: SettingsTabId) => void;
  modelConfig?: ModelConfigResponse | null;
  modelOptions?: ModelCatalogOption[];
  selectedModel?: ModelSelection | null;
  onSelectModel?: (selection: ModelSelection | null) => void;
}

export function HomeHeader({
  onOpenSettings,
  modelConfig,
  modelOptions = [],
  selectedModel,
  onSelectModel,
}: HomeHeaderProps) {
  const { t } = useT("translation");

  const defaultModel = (modelConfig?.default_model || "").trim();
  const defaultSelection = React.useMemo(() => {
    const defaultOption = modelOptions.find((option) => option.isDefault);
    return defaultOption
      ? {
          modelId: defaultOption.modelId,
          providerId: defaultOption.providerId,
        }
      : null;
  }, [modelOptions]);
  const hasSelectableModel = React.useMemo(
    () => modelOptions.some((option) => option.isAvailable),
    [modelOptions],
  );

  const isSelectorReady = Boolean(
    defaultModel && onSelectModel && hasSelectableModel,
  );

  return (
    <PageHeaderShell
      left={
        <div className="flex items-center gap-2">
          <ModelSelector
            options={modelOptions}
            selection={selectedModel ?? null}
            defaultSelection={defaultSelection}
            fallbackLabel={
              selectedModel?.modelId || defaultModel || t("status.loading")
            }
            onChange={onSelectModel ?? (() => undefined)}
            disabled={!isSelectorReady}
            triggerClassName="h-10 gap-2 px-2"
          />
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
