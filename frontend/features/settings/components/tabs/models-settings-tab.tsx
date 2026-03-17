"use client";

import * as React from "react";
import { Loader2, Plus, RotateCcw, Save, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
  inputId: string;
  onChange: (patch: Partial<ApiProviderConfig>) => void;
}

function ProviderModelField({
  config,
  inputId,
  onChange,
}: ProviderModelFieldProps) {
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
          id={inputId}
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
              <span className="max-w-[180px] truncate">{modelId}</span>
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
  const apiKeyInputId = `${config.providerId}-api-key`;
  const baseUrlInputId = `${config.providerId}-base-url`;
  const modelInputId = `${config.providerId}-model`;
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
    config.modelDraft.trim().length > 0 ||
    JSON.stringify(config.selectedModelIds) !== JSON.stringify(storedModelIds);

  return (
    <section className="space-y-5 rounded-[28px] border border-border/60 bg-card/70 p-5 shadow-[var(--shadow-sm)] sm:p-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-base font-medium text-foreground">
              {config.displayName}
            </h3>
            <Badge variant="outline">{statusLabel}</Badge>
            <Badge
              variant={
                config.selectedModelIds.length > 0 ? "secondary" : "outline"
              }
            >
              {config.selectedModelIds.length}
            </Badge>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {canClear ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void onClear()}
              disabled={config.isSaving}
            >
              <RotateCcw className="size-4" />
              {t("settings.providerClearCustom")}
            </Button>
          ) : null}
          <Button
            type="button"
            size="sm"
            onClick={() => void onSave()}
            disabled={config.isSaving || !hasChanges}
          >
            {config.isSaving ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Save className="size-4" />
            )}
            {t("common.save")}
          </Button>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor={apiKeyInputId}>
            {t("settings.providerApiKeyLabel", {
              provider: config.displayName,
            })}
          </Label>
          <Input
            id={apiKeyInputId}
            type="password"
            value={config.keyInput}
            onChange={(event) => onChange({ keyInput: event.target.value })}
            placeholder={t("settings.providerApiKeyPlaceholder", {
              provider: config.displayName,
            })}
            disabled={config.isSaving}
          />
          <p className="text-xs text-muted-foreground">
            {t("settings.providerApiKeyHint")}
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor={baseUrlInputId}>
            {t("settings.providerBaseUrlLabel")}
          </Label>
          <Input
            id={baseUrlInputId}
            value={config.baseUrlInput}
            onChange={(event) => onChange({ baseUrlInput: event.target.value })}
            placeholder={config.defaultBaseUrl}
            disabled={config.isSaving}
          />
          <p className="text-xs text-muted-foreground">
            {t("settings.providerBaseUrlHint")}
          </p>
        </div>
      </div>

      <div className="space-y-3 rounded-2xl border border-border/50 bg-background/70 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <Label htmlFor={modelInputId}>{t("settings.sidebar.models")}</Label>
          <Badge variant="outline">{config.selectedModelIds.length}</Badge>
        </div>
        <ProviderModelField
          config={config}
          inputId={modelInputId}
          onChange={onChange}
        />
      </div>
    </section>
  );
}

function ProviderTabTrigger({ config }: { config: ApiProviderConfig }) {
  const { t } = useT("translation");
  const statusLabel = getStatusLabel(t, config.credentialState);

  return (
    <TabsTrigger
      value={config.providerId}
      className="h-auto min-w-[150px] flex-none items-start justify-between gap-3 rounded-2xl border border-transparent px-4 py-3 text-left text-foreground transition-all data-[state=active]:border-border/80 data-[state=active]:bg-background data-[state=active]:shadow-[var(--shadow-sm)]"
    >
      <div className="min-w-0 space-y-1">
        <p className="truncate text-sm font-medium">{config.displayName}</p>
        <p className="truncate text-xs text-muted-foreground">{statusLabel}</p>
      </div>
      <Badge
        variant={config.selectedModelIds.length > 0 ? "secondary" : "outline"}
      >
        {config.selectedModelIds.length}
      </Badge>
    </TabsTrigger>
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
  const [activeProviderId, setActiveProviderId] = React.useState("");

  React.useEffect(() => {
    if (providers.length === 0) {
      if (activeProviderId) {
        setActiveProviderId("");
      }
      return;
    }

    const hasActiveProvider = providers.some(
      (provider) => provider.providerId === activeProviderId,
    );
    if (!hasActiveProvider) {
      setActiveProviderId(providers[0].providerId);
    }
  }, [activeProviderId, providers]);

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
        ) : providers.length > 0 && activeProviderId ? (
          <Tabs
            value={activeProviderId}
            onValueChange={setActiveProviderId}
            className="gap-4"
          >
            <TabsList className="h-auto w-full flex-wrap justify-start gap-1 rounded-[28px] bg-muted/50 p-1">
              {providers.map((provider) => (
                <ProviderTabTrigger
                  key={provider.providerId}
                  config={provider}
                />
              ))}
            </TabsList>

            {providers.map((provider) => (
              <TabsContent
                key={provider.providerId}
                value={provider.providerId}
                className="mt-0"
              >
                <ApiProviderSection
                  config={provider}
                  onChange={(patch) =>
                    onChangeProvider(provider.providerId, patch)
                  }
                  onSave={() => onSaveProvider(provider.providerId)}
                  onClear={() => onClearProvider(provider.providerId)}
                />
              </TabsContent>
            ))}
          </Tabs>
        ) : (
          <div className="rounded-3xl border border-border/60 bg-card/60 p-5 text-sm text-muted-foreground">
            {t("settings.providerListEmpty")}
          </div>
        )}
      </section>
    </div>
  );
}
