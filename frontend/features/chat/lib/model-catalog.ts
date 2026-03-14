import type {
  CredentialState,
  ModelConfigResponse,
  ModelDefinition,
  ModelProvider,
} from "@/features/chat/types";

export interface ModelCatalogOption {
  optionKey: string;
  modelId: string;
  displayName: string;
  providerId: string;
  providerName: string;
  credentialState: CredentialState;
  isAvailable: boolean;
  isDefault: boolean;
}

export interface ModelSelection {
  modelId: string | null;
  providerId: string | null;
}

function buildProviderMap(
  providers: ModelConfigResponse["providers"] | undefined,
): Map<string, ModelProvider> {
  return new Map(
    (providers ?? []).map((provider) => [provider.provider_id, provider]),
  );
}

function buildOptionKey(providerId: string, modelId: string): string {
  return `${providerId}:${modelId}`;
}

function getOrderedModels(modelConfig: ModelConfigResponse): ModelDefinition[] {
  const orderedModels: ModelDefinition[] = [];
  const seen = new Set<string>();

  const push = (model: ModelDefinition | undefined) => {
    if (!model) {
      return;
    }
    const key = buildOptionKey(model.provider_id, model.model_id);
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    orderedModels.push(model);
  };

  const defaultModelId = (modelConfig.default_model || "").trim();
  push(
    modelConfig.models.find((model) => model.model_id === defaultModelId) ??
      undefined,
  );
  modelConfig.models.forEach(push);

  return orderedModels;
}

export function buildModelCatalogOptions(
  modelConfig: ModelConfigResponse | null | undefined,
): ModelCatalogOption[] {
  if (!modelConfig) {
    return [];
  }

  const defaultModel = (modelConfig.default_model || "").trim();
  const providerMap = buildProviderMap(modelConfig.providers);

  return getOrderedModels(modelConfig).map((model) => {
    const provider = providerMap.get(model.provider_id);
    const credentialState = provider?.credential_state ?? "none";

    return {
      optionKey: buildOptionKey(model.provider_id, model.model_id),
      modelId: model.model_id,
      displayName: model.display_name,
      providerId: model.provider_id,
      providerName: provider?.display_name ?? model.provider_id,
      credentialState,
      isAvailable: !model.requires_credentials || credentialState !== "none",
      isDefault: model.model_id === defaultModel,
    };
  });
}

export function findModelCatalogOption(
  modelConfig: ModelConfigResponse | null | undefined,
  selection: ModelSelection | null | undefined,
): ModelCatalogOption | null {
  const modelId = (selection?.modelId || "").trim();
  const providerId = (selection?.providerId || "").trim();
  if (!modelId) {
    return null;
  }

  const options = buildModelCatalogOptions(modelConfig);
  if (providerId) {
    return (
      options.find(
        (option) =>
          option.modelId === modelId && option.providerId === providerId,
      ) ?? null
    );
  }

  return options.find((option) => option.modelId === modelId) ?? null;
}

export function normalizeModelSelection(
  selection: ModelSelection | null | undefined,
): ModelSelection {
  const modelId = (selection?.modelId || "").trim() || null;
  const providerId = (selection?.providerId || "").trim() || null;
  return {
    modelId,
    providerId: modelId ? providerId : null,
  };
}
