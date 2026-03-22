"use client";

import * as React from "react";

import { apiClient, API_ENDPOINTS } from "@/services/api-client";
import type { ModelConfigResponse } from "@/features/chat/types";
import { buildModelCatalogOptions } from "@/features/chat/lib/model-catalog";
import { getModelCatalogInvalidatedEventName } from "@/features/chat/lib/model-catalog-state";

export function useModelCatalog(options?: { enabled?: boolean }) {
  const enabled = options?.enabled ?? true;
  const [modelConfig, setModelConfig] =
    React.useState<ModelConfigResponse | null>(null);
  const [isLoading, setIsLoading] = React.useState(enabled);
  const modelOptions = React.useMemo(
    () => buildModelCatalogOptions(modelConfig),
    [modelConfig],
  );

  const refresh = React.useCallback(async () => {
    if (!enabled) {
      return;
    }

    setIsLoading(true);
    try {
      const nextConfig = await apiClient.get<ModelConfigResponse>(
        API_ENDPOINTS.models,
      );
      setModelConfig(nextConfig);
    } catch (error) {
      console.error("[Chat] Failed to load model catalog:", error);
    } finally {
      setIsLoading(false);
    }
  }, [enabled]);

  React.useEffect(() => {
    if (!enabled) {
      setIsLoading(false);
      return;
    }

    void refresh();
  }, [enabled, refresh]);

  React.useEffect(() => {
    if (!enabled || typeof window === "undefined") {
      return;
    }

    const eventName = getModelCatalogInvalidatedEventName();
    const handleInvalidated = () => {
      void refresh();
    };

    window.addEventListener(eventName, handleInvalidated);
    return () => {
      window.removeEventListener(eventName, handleInvalidated);
    };
  }, [enabled, refresh]);

  return {
    modelConfig,
    modelOptions,
    isLoading,
    refresh,
  };
}
