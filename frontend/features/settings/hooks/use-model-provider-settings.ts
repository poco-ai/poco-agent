"use client";

import * as React from "react";
import { toast } from "sonner";

import { modelConfigService } from "@/features/home/api/model-config-api";
import { envVarsService } from "@/features/capabilities/env-vars/api/env-vars-api";
import type { EnvVar } from "@/features/capabilities/env-vars/types";
import type { ModelConfigResponse, ModelProvider } from "@/features/chat/types";
import { invalidateModelCatalog } from "@/features/chat/lib/model-catalog-state";
import { useT } from "@/lib/i18n/client";
import type { ApiProviderConfig } from "@/features/settings/types";

function normalizeModelIds(modelIds: string[]): string[] {
  const seen = new Set<string>();
  const ordered: string[] = [];

  modelIds.forEach((modelId) => {
    const segments = (modelId || "")
      .split(/[,\n，]+/)
      .map((item) => item.trim())
      .filter(Boolean);

    segments.forEach((segment) => {
      if (seen.has(segment)) {
        return;
      }
      seen.add(segment);
      ordered.push(segment);
    });
  });

  return ordered;
}

function buildProviderConfig(
  provider: ModelProvider,
  envVars: EnvVar[],
  status?: {
    savingProviderId?: string | null;
  },
): ApiProviderConfig {
  const providerModels = Array.isArray(provider.models) ? provider.models : [];
  const hasStoredUserKey = envVars.some(
    (item) => item.scope === "user" && item.key === provider.api_key_env_key,
  );
  const hasStoredUserBaseUrl = envVars.some(
    (item) => item.scope === "user" && item.key === provider.base_url_env_key,
  );

  return {
    providerId: provider.provider_id,
    displayName: provider.display_name,
    apiKeyEnvKey: provider.api_key_env_key,
    baseUrlEnvKey: provider.base_url_env_key,
    credentialState: provider.credential_state,
    defaultBaseUrl: provider.default_base_url,
    effectiveBaseUrl: provider.effective_base_url,
    baseUrlSource: provider.base_url_source,
    models: providerModels,
    selectedModelIds: providerModels.map((item) => item.model_id),
    modelDraft: "",
    keyInput: "",
    baseUrlInput:
      provider.base_url_source === "user" ? provider.effective_base_url : "",
    hasStoredUserKey,
    hasStoredUserBaseUrl,
    isSaving: status?.savingProviderId === provider.provider_id,
    enabled: true,
  };
}

export function useModelProviderSettings(options?: { enabled?: boolean }) {
  const enabled = options?.enabled ?? true;
  const { t } = useT("translation");
  const [modelConfig, setModelConfig] =
    React.useState<ModelConfigResponse | null>(null);
  const [envVars, setEnvVars] = React.useState<EnvVar[]>([]);
  const [providerConfigs, setProviderConfigs] = React.useState<
    ApiProviderConfig[]
  >([]);
  const [isLoading, setIsLoading] = React.useState(true);
  const [savingProviderId, setSavingProviderId] = React.useState<string | null>(
    null,
  );

  const rebuildProviderConfigs = React.useCallback(
    (
      nextModelConfig: ModelConfigResponse,
      nextEnvVars: EnvVar[],
      status?: {
        savingProviderId?: string | null;
      },
    ) => {
      setProviderConfigs((prev) => {
        const previousMap = new Map(
          prev.map((item) => [item.providerId, item]),
        );
        return nextModelConfig.providers.map((provider) => {
          const nextProvider = buildProviderConfig(
            provider,
            nextEnvVars,
            status,
          );
          const previous = previousMap.get(provider.provider_id);
          if (!previous) {
            return nextProvider;
          }
          return {
            ...nextProvider,
            modelDraft: previous.modelDraft,
            enabled: previous.enabled,
          };
        });
      });
    },
    [],
  );

  const refresh = React.useCallback(async () => {
    if (!enabled) return;
    setIsLoading(true);
    try {
      const [nextModelConfig, nextEnvVars] = await Promise.all([
        modelConfigService.get(),
        envVarsService.list(),
      ]);
      setModelConfig(nextModelConfig);
      setEnvVars(nextEnvVars);
      rebuildProviderConfigs(nextModelConfig, nextEnvVars);
    } catch (error) {
      console.error("[Settings] Failed to load provider settings:", error);
      toast.error(t("settings.providerSaveError"));
    } finally {
      setIsLoading(false);
    }
  }, [enabled, rebuildProviderConfigs, t]);

  React.useEffect(() => {
    if (!enabled) return;
    void refresh();
  }, [enabled, refresh]);

  const setProviderPatch = React.useCallback(
    (providerId: string, patch: Partial<ApiProviderConfig>) => {
      setProviderConfigs((prev) =>
        prev.map((item) =>
          item.providerId === providerId ? { ...item, ...patch } : item,
        ),
      );
    },
    [],
  );

  const findUserEnvVar = React.useCallback(
    (key: string) =>
      envVars.find((item) => item.scope === "user" && item.key === key) ?? null,
    [envVars],
  );

  const upsertUserEnvVar = React.useCallback(
    async (key: string, value: string, description: string) => {
      const existing = findUserEnvVar(key);
      if (existing) {
        await envVarsService.update(existing.id, {
          value,
          description,
        });
        return;
      }
      await envVarsService.create({
        key,
        value,
        description,
      });
    },
    [findUserEnvVar],
  );

  const deleteUserEnvVar = React.useCallback(
    async (key: string) => {
      const existing = findUserEnvVar(key);
      if (!existing) return;
      await envVarsService.remove(existing.id);
    },
    [findUserEnvVar],
  );

  const saveProvider = React.useCallback(
    async (providerId: string) => {
      const provider = providerConfigs.find(
        (item) => item.providerId === providerId,
      );
      if (!provider) return;
      const nextModelIds = normalizeModelIds([
        ...provider.selectedModelIds,
        provider.modelDraft,
      ]);

      setSavingProviderId(providerId);
      setProviderPatch(providerId, { isSaving: true });
      try {
        const keyValue = provider.keyInput.trim();
        const baseUrlValue = provider.baseUrlInput.trim();
        const keyDescription = `${provider.displayName} API key`;
        const baseUrlDescription = `${provider.displayName} base URL`;

        if (keyValue) {
          await upsertUserEnvVar(
            provider.apiKeyEnvKey,
            keyValue,
            keyDescription,
          );
        }

        if (baseUrlValue) {
          await upsertUserEnvVar(
            provider.baseUrlEnvKey,
            baseUrlValue,
            baseUrlDescription,
          );
        } else {
          await deleteUserEnvVar(provider.baseUrlEnvKey);
        }

        await modelConfigService.updateProviderModels(providerId, {
          model_ids: nextModelIds,
        });

        const [nextModelConfig, nextEnvVars] = await Promise.all([
          modelConfigService.get(),
          envVarsService.list(),
        ]);
        setModelConfig(nextModelConfig);
        setEnvVars(nextEnvVars);
        rebuildProviderConfigs(nextModelConfig, nextEnvVars);
        setProviderPatch(providerId, { modelDraft: "" });
        invalidateModelCatalog();
        toast.success(t("settings.providerSaveSuccess"));
      } catch (error) {
        console.error("[Settings] Failed to save provider settings:", error);
        toast.error(t("settings.providerSaveError"));
      } finally {
        setSavingProviderId(null);
        setProviderPatch(providerId, { isSaving: false });
      }
    },
    [
      deleteUserEnvVar,
      providerConfigs,
      rebuildProviderConfigs,
      setProviderPatch,
      t,
      upsertUserEnvVar,
    ],
  );

  const clearCustomProvider = React.useCallback(
    async (providerId: string) => {
      const provider = providerConfigs.find(
        (item) => item.providerId === providerId,
      );
      if (!provider) return;

      setSavingProviderId(providerId);
      setProviderPatch(providerId, { isSaving: true });
      try {
        await Promise.all([
          deleteUserEnvVar(provider.apiKeyEnvKey),
          deleteUserEnvVar(provider.baseUrlEnvKey),
          modelConfigService.updateProviderModels(providerId, {
            model_ids: [],
          }),
        ]);
        const [nextModelConfig, nextEnvVars] = await Promise.all([
          modelConfigService.get(),
          envVarsService.list(),
        ]);
        setModelConfig(nextModelConfig);
        setEnvVars(nextEnvVars);
        rebuildProviderConfigs(nextModelConfig, nextEnvVars);
        setProviderPatch(providerId, { modelDraft: "" });
        invalidateModelCatalog();
        toast.success(t("settings.providerClearSuccess"));
      } catch (error) {
        console.error("[Settings] Failed to clear provider settings:", error);
        toast.error(t("settings.providerSaveError"));
      } finally {
        setSavingProviderId(null);
        setProviderPatch(providerId, { isSaving: false });
      }
    },
    [
      deleteUserEnvVar,
      providerConfigs,
      rebuildProviderConfigs,
      setProviderPatch,
      t,
    ],
  );

  return {
    modelConfig,
    providerConfigs,
    isLoading,
    savingProviderId,
    setProviderPatch,
    saveProvider,
    clearCustomProvider,
    refresh,
  };
}
