"use client";

import * as React from "react";
import {
  Check,
  ChevronsUpDown,
  Loader2,
  RotateCcw,
  Save,
  X,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Input } from "@/components/ui/input";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n/client";
import type { ApiProviderConfig } from "@/features/settings/types";

function getStatusLabel(
  t: (key: string) => string,
  credentialState: ApiProviderConfig["credentialState"],
) {
  if (credentialState === "user") {
    return t("settings.providerStatusUser");
  }
  if (credentialState === "system") {
    return t("settings.providerStatusSystem");
  }
  return t("settings.providerStatusNone");
}

interface ProviderModelFieldProps {
  config: ApiProviderConfig;
  onChange: (patch: Partial<ApiProviderConfig>) => void;
  onDiscover: () => void;
}

function ProviderModelField({
  config,
  onChange,
  onDiscover,
}: ProviderModelFieldProps) {
  const { t } = useT("translation");
  const [open, setOpen] = React.useState(false);
  const discoveryAttemptedRef = React.useRef(false);
  const query = config.modelDraft.trim().toLowerCase();
  const discoveredModels = React.useMemo(
    () =>
      Array.isArray(config.discoveredModels) ? config.discoveredModels : [],
    [config.discoveredModels],
  );
  const discoveredOptions = React.useMemo(
    () =>
      discoveredModels.filter((item) =>
        item.model_id.toLowerCase().includes(query),
      ),
    [discoveredModels, query],
  );

  React.useEffect(() => {
    if (!open) {
      discoveryAttemptedRef.current = false;
      return;
    }
    if (
      discoveryAttemptedRef.current ||
      !config.supportsModelDiscovery ||
      config.isDiscovering ||
      discoveredModels.length > 0
    ) {
      return;
    }
    discoveryAttemptedRef.current = true;
    void onDiscover();
  }, [
    config.isDiscovering,
    config.supportsModelDiscovery,
    discoveredModels.length,
    onDiscover,
    open,
  ]);

  const addModel = React.useCallback(
    (modelId: string) => {
      const clean = modelId.trim();
      if (!clean) {
        return;
      }
      if (config.selectedModelIds.includes(clean)) {
        onChange({ modelDraft: "" });
        return;
      }
      onChange({
        selectedModelIds: [...config.selectedModelIds, clean],
        modelDraft: "",
      });
    },
    [config.selectedModelIds, onChange],
  );

  const removeModel = React.useCallback(
    (modelId: string) => {
      onChange({
        selectedModelIds: config.selectedModelIds.filter(
          (item) => item !== modelId,
        ),
      });
    },
    [config.selectedModelIds, onChange],
  );

  return (
    <div className="space-y-2">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            type="button"
            variant="outline"
            role="combobox"
            aria-expanded={open}
            disabled={config.isSaving}
            className="h-auto min-h-11 w-full justify-between px-3 py-2 text-left"
          >
            <div className="flex min-w-0 flex-1 flex-wrap items-center gap-1.5">
              {config.selectedModelIds.length > 0 ? (
                config.selectedModelIds.map((modelId) => (
                  <span
                    key={modelId}
                    className="inline-flex items-center gap-1 rounded-full border border-border/70 bg-muted px-2 py-0.5 text-xs text-foreground"
                  >
                    <span className="truncate max-w-[180px]">{modelId}</span>
                    <span
                      role="button"
                      tabIndex={0}
                      className="text-muted-foreground transition hover:text-foreground"
                      onClick={(event) => {
                        event.stopPropagation();
                        removeModel(modelId);
                      }}
                      onKeyDown={(event) => {
                        if (event.key !== "Enter" && event.key !== " ") {
                          return;
                        }
                        event.preventDefault();
                        event.stopPropagation();
                        removeModel(modelId);
                      }}
                    >
                      <X className="size-3" />
                    </span>
                  </span>
                ))
              ) : (
                <span className="text-sm text-muted-foreground">
                  {t("settings.providerModelsPlaceholder")}
                </span>
              )}
            </div>
            <ChevronsUpDown className="ml-2 size-4 shrink-0 text-muted-foreground" />
          </Button>
        </PopoverTrigger>
        <PopoverContent
          align="start"
          className="w-[--radix-popover-trigger-width] p-0"
        >
          <Command>
            <CommandInput
              value={config.modelDraft}
              onValueChange={(value) => onChange({ modelDraft: value })}
              placeholder={t("settings.providerModelsSearchPlaceholder")}
            />
            <CommandList>
              {config.isDiscovering ? (
                <div className="flex items-center gap-2 px-3 py-3 text-sm text-muted-foreground">
                  <Loader2 className="size-4 animate-spin" />
                  <span>{t("settings.providerModelsDiscovering")}</span>
                </div>
              ) : null}
              {config.supportsModelDiscovery ? null : (
                <div className="px-3 py-2 text-xs text-muted-foreground">
                  {t("settings.providerModelsManualHint")}
                </div>
              )}
              <CommandEmpty>{t("settings.providerModelsEmpty")}</CommandEmpty>
              {query ? (
                <CommandItem
                  value={`__custom__:${config.modelDraft}`}
                  onSelect={() => addModel(config.modelDraft)}
                >
                  <Check className="size-4 opacity-0" />
                  <span>
                    {t("settings.providerModelsUseCustom", {
                      model: config.modelDraft.trim(),
                    })}
                  </span>
                </CommandItem>
              ) : null}
              {discoveredOptions.map((item) => {
                const isSelected = config.selectedModelIds.includes(
                  item.model_id,
                );
                return (
                  <CommandItem
                    key={item.model_id}
                    value={item.model_id}
                    onSelect={() => addModel(item.model_id)}
                  >
                    <Check
                      className={cn(
                        "size-4",
                        isSelected ? "opacity-100" : "opacity-0",
                      )}
                    />
                    <span className="truncate">{item.model_id}</span>
                  </CommandItem>
                );
              })}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
  );
}

interface ApiProviderSectionProps {
  config: ApiProviderConfig;
  onChange: (patch: Partial<ApiProviderConfig>) => void;
  onSave: () => Promise<void> | void;
  onClear: () => Promise<void> | void;
  onDiscover: () => Promise<void> | void;
}

function ApiProviderSection({
  config,
  onChange,
  onSave,
  onClear,
  onDiscover,
}: ApiProviderSectionProps) {
  const { t } = useT("translation");
  const statusLabel = getStatusLabel(t, config.credentialState);
  const canClear =
    config.hasStoredUserKey ||
    config.hasStoredUserBaseUrl ||
    config.selectedModelIds.length > 0;
  const storedBaseUrl = React.useMemo(
    () =>
      config.baseUrlSource === "user" ? config.effectiveBaseUrl.trim() : "",
    [config.baseUrlSource, config.effectiveBaseUrl],
  );
  const storedModelIds = React.useMemo(
    () => config.models.map((item) => item.model_id),
    [config.models],
  );
  const hasChanges =
    config.keyInput.trim().length > 0 ||
    config.baseUrlInput.trim() !== storedBaseUrl ||
    JSON.stringify(config.selectedModelIds) !== JSON.stringify(storedModelIds);

  return (
    <section className="space-y-4 rounded-3xl border border-border/60 bg-card/60 p-5 shadow-[var(--shadow-sm)]">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <h3 className="text-base font-medium text-foreground">
            {config.displayName}
          </h3>
          <Badge variant="outline">{statusLabel}</Badge>
        </div>
        <div className="flex items-center gap-1 self-start">
          {canClear ? (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="size-8"
              onClick={() => void onClear()}
              disabled={config.isSaving}
              title={t("settings.providerClearCustom")}
            >
              <RotateCcw className="size-4" />
            </Button>
          ) : null}
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-8"
            onClick={() => void onSave()}
            disabled={config.isSaving || !hasChanges}
            title={t("common.save")}
          >
            {config.isSaving ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Save className="size-4" />
            )}
          </Button>
        </div>
      </div>

      <Input
        type="password"
        value={config.keyInput}
        onChange={(event) =>
          onChange({
            keyInput: event.target.value,
            discoveredModels: [],
          })
        }
        placeholder={t("settings.providerApiKeyPlaceholder", {
          provider: config.displayName,
        })}
        disabled={config.isSaving}
      />

      <Input
        value={config.baseUrlInput}
        onChange={(event) =>
          onChange({
            baseUrlInput: event.target.value,
            discoveredModels: [],
          })
        }
        placeholder={config.defaultBaseUrl}
        disabled={config.isSaving}
      />

      <ProviderModelField
        config={config}
        onChange={onChange}
        onDiscover={onDiscover}
      />

      <p className="text-xs text-muted-foreground">
        {t("settings.providerFieldAnnotation")}
      </p>
    </section>
  );
}

interface ModelsSettingsTabProps {
  providers: ApiProviderConfig[];
  isLoading: boolean;
  onChangeProvider: (
    providerId: string,
    patch: Partial<ApiProviderConfig>,
  ) => void;
  onSaveProvider: (providerId: string) => Promise<void> | void;
  onClearProvider: (providerId: string) => Promise<void> | void;
  onDiscoverProviderModels: (providerId: string) => Promise<void> | void;
}

export function ModelsSettingsTab({
  providers,
  isLoading,
  onChangeProvider,
  onSaveProvider,
  onClearProvider,
  onDiscoverProviderModels,
}: ModelsSettingsTabProps) {
  const { t } = useT("translation");

  return (
    <div className="flex-1 space-y-8 overflow-y-auto p-6">
      <section className="space-y-2">
        <h3 className="text-sm font-medium text-foreground">
          {t("settings.modelConfigTitle")}
        </h3>
        <p className="text-sm text-muted-foreground">
          {t("settings.providerConfigDescription")}
        </p>
      </section>

      <section className="space-y-4">
        {isLoading ? (
          <div className="rounded-3xl border border-border/60 bg-card/60 p-5 text-sm text-muted-foreground">
            {t("status.loading")}
          </div>
        ) : providers.length > 0 ? (
          providers.map((provider) => (
            <ApiProviderSection
              key={provider.providerId}
              config={provider}
              onChange={(patch) => onChangeProvider(provider.providerId, patch)}
              onSave={() => onSaveProvider(provider.providerId)}
              onClear={() => onClearProvider(provider.providerId)}
              onDiscover={() => onDiscoverProviderModels(provider.providerId)}
            />
          ))
        ) : (
          <div className="rounded-3xl border border-border/60 bg-card/60 p-5 text-sm text-muted-foreground">
            {t("settings.providerListEmpty")}
          </div>
        )}
      </section>
    </div>
  );
}
