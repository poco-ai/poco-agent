"use client";

import * as React from "react";
import {
  Loader2,
  Plus,
  RotateCcw,
  Save,
  X,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
}

function ProviderModelField({ config, onChange }: ProviderModelFieldProps) {
  const { t } = useT("translation");
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

  const commitDraft = React.useCallback(() => {
    addModel(config.modelDraft);
  }, [addModel, config.modelDraft]);

  const handleDraftKeyDown = React.useCallback(
    (event: React.KeyboardEvent<HTMLInputElement>) => {
      if (event.key !== "Enter" && event.key !== ",") {
        return;
      }
      event.preventDefault();
      commitDraft();
    },
    [commitDraft],
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
      <div className="flex items-center gap-2">
        <Input
          value={config.modelDraft}
          onChange={(event) => onChange({ modelDraft: event.target.value })}
          onKeyDown={handleDraftKeyDown}
          placeholder={t("settings.providerModelsSearchPlaceholder")}
          disabled={config.isSaving}
        />
        <Button
          type="button"
          variant="outline"
          size="icon"
          className="size-10 shrink-0"
          onClick={commitDraft}
          disabled={config.isSaving || config.modelDraft.trim().length === 0}
          title={t("settings.providerModelsAdd")}
          aria-label={t("settings.providerModelsAdd")}
        >
          <Plus className="size-4" />
        </Button>
      </div>
      {config.selectedModelIds.length > 0 ? (
        <div className="flex min-w-0 flex-wrap items-center gap-1.5">
          {config.selectedModelIds.map((modelId) => (
            <span
              key={modelId}
              className="inline-flex items-center gap-1 rounded-full border border-border/70 bg-muted px-2 py-0.5 text-xs text-foreground"
            >
              <span className="truncate max-w-[180px]">{modelId}</span>
              <span
                role="button"
                tabIndex={0}
                className="text-muted-foreground transition hover:text-foreground"
                onClick={() => removeModel(modelId)}
                onKeyDown={(event) => {
                  if (event.key !== "Enter" && event.key !== " ") {
                    return;
                  }
                  event.preventDefault();
                  removeModel(modelId);
                }}
              >
                <X className="size-3" />
              </span>
            </span>
          ))}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">
          {t("settings.providerModelsPlaceholder")}
        </p>
      )}
    </div>
  );
}

interface ApiProviderSectionProps {
  config: ApiProviderConfig;
  onChange: (patch: Partial<ApiProviderConfig>) => void;
  onSave: () => Promise<void> | void;
  onClear: () => Promise<void> | void;
}

function ApiProviderSection({
  config,
  onChange,
  onSave,
  onClear,
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
        onChange={(event) => onChange({ keyInput: event.target.value })}
        placeholder={t("settings.providerApiKeyPlaceholder", {
          provider: config.displayName,
        })}
        disabled={config.isSaving}
      />

      <Input
        value={config.baseUrlInput}
        onChange={(event) => onChange({ baseUrlInput: event.target.value })}
        placeholder={config.defaultBaseUrl}
        disabled={config.isSaving}
      />

      <ProviderModelField config={config} onChange={onChange} />

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
}

export function ModelsSettingsTab({
  providers,
  isLoading,
  onChangeProvider,
  onSaveProvider,
  onClearProvider,
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
