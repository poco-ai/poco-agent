"use client";

import * as React from "react";
import { ChevronDown } from "lucide-react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useT } from "@/lib/i18n/client";
import type {
  ModelCatalogOption,
  ModelSelection,
} from "@/features/chat/lib/model-catalog";

interface ModelSelectorProps {
  options: ModelCatalogOption[];
  selection: ModelSelection | null;
  defaultSelection?: ModelSelection | null;
  fallbackLabel?: string;
  onChange: (selection: ModelSelection | null) => void;
  disabled?: boolean;
  triggerClassName?: string;
}

function getCredentialLabel(
  t: (key: string) => string,
  credentialState: ModelCatalogOption["credentialState"],
) {
  if (credentialState === "user") {
    return t("settings.providerStatusUser");
  }
  if (credentialState === "system") {
    return t("settings.providerStatusSystem");
  }
  return t("settings.providerStatusNone");
}

function isSameOption(
  option: ModelCatalogOption | null | undefined,
  selection: ModelSelection | null | undefined,
): boolean {
  return (
    (option?.modelId || "") === (selection?.modelId || "") &&
    (option?.providerId || "") === (selection?.providerId || "")
  );
}

export function ModelSelector({
  options,
  selection,
  defaultSelection,
  fallbackLabel,
  onChange,
  disabled = false,
  triggerClassName,
}: ModelSelectorProps) {
  const { t } = useT("translation");

  const defaultOption = React.useMemo(
    () =>
      options.find(
        (option) =>
          option.modelId === (defaultSelection?.modelId || "").trim() &&
          option.providerId === (defaultSelection?.providerId || "").trim(),
      ) ?? null,
    [defaultSelection?.modelId, defaultSelection?.providerId, options],
  );

  const selectedOption = React.useMemo(() => {
    const modelId = (selection?.modelId || "").trim();
    const providerId = (selection?.providerId || "").trim();
    if (!modelId) {
      return defaultOption;
    }
    return (
      options.find(
        (option) =>
          option.modelId === modelId &&
          (providerId ? option.providerId === providerId : true),
      ) ?? defaultOption
    );
  }, [defaultOption, options, selection?.modelId, selection?.providerId]);

  const canOpen = !disabled && options.some((option) => option.isAvailable);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className={triggerClassName}
          disabled={!canOpen}
          title={t("header.switchModel")}
        >
          <span className="max-w-[220px] truncate font-medium font-serif">
            {selectedOption?.displayName ||
              fallbackLabel ||
              t("status.loading")}
          </span>
          <ChevronDown className="ml-2 size-3.5 text-muted-foreground" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-72">
        {defaultOption ? (
          <>
            <DropdownMenuItem
              onClick={() => onChange(null)}
              disabled={!defaultOption.isAvailable}
              className="flex items-start justify-between gap-3 p-3"
            >
              <div className="min-w-0 flex-1">
                <div className="truncate font-medium">
                  {defaultOption.displayName}
                </div>
                <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                  <span>{t("models.defaultTag")}</span>
                  <span>/</span>
                  <span>{defaultOption.providerName}</span>
                  <span>/</span>
                  <span>
                    {getCredentialLabel(t, defaultOption.credentialState)}
                  </span>
                </div>
              </div>
              {isSameOption(defaultOption, selection ?? defaultSelection) ? (
                <div className="text-primary text-sm">✓</div>
              ) : null}
            </DropdownMenuItem>
            {options.some((option) => !option.isDefault) ? (
              <DropdownMenuSeparator />
            ) : null}
          </>
        ) : null}

        {options
          .filter((option) => !option.isDefault)
          .map((option) => (
            <DropdownMenuItem
              key={option.optionKey}
              onClick={() =>
                onChange({
                  modelId: option.modelId,
                  providerId: option.providerId,
                })
              }
              disabled={!option.isAvailable}
              className="flex items-start justify-between gap-3 p-3"
            >
              <div className="min-w-0 flex-1">
                <div className="truncate font-medium">{option.displayName}</div>
                <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                  <span>{option.providerName}</span>
                  <Badge variant="outline" className="h-5 px-1.5 text-[10px]">
                    {getCredentialLabel(t, option.credentialState)}
                  </Badge>
                </div>
              </div>
              {isSameOption(option, selection) ? (
                <div className="text-primary text-sm">✓</div>
              ) : null}
            </DropdownMenuItem>
          ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
