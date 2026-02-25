"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { useT } from "@/lib/i18n/client";
import { envVarsService } from "@/features/capabilities/env-vars/api/env-vars-api";
import type { EnvVar } from "@/features/capabilities/env-vars/types";

export interface EnvVarUpsertInput {
  key: string;
  value?: string;
  description?: string | null;
}

export function useEnvVarsStore() {
  const { t } = useT("translation");
  const [envVars, setEnvVars] = useState<EnvVar[]>([]);
  const [savingEnvKey, setSavingEnvKey] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch data on mount
  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      try {
        const data = await envVarsService.list();
        setEnvVars(data);
      } catch (error) {
        console.error("[EnvVars] Failed to fetch:", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, []);

  const upsertEnvVar = useCallback(
    async ({ key, value, description }: EnvVarUpsertInput) => {
      const normalizedKey = key.trim();
      if (!normalizedKey) {
        toast.error(t("library.envVars.toasts.keyRequired"));
        return;
      }

      setSavingEnvKey(normalizedKey);

      try {
        const existing = envVars.find(
          (item) => item.key === normalizedKey && item.scope === "user",
        );
        if (existing) {
          const updated = await envVarsService.update(existing.id, {
            value: value?.trim() ? value.trim() : undefined,
            description: description ?? existing.description,
          });
          setEnvVars((prev) =>
            prev.map((item) => (item.id === existing.id ? updated : item)),
          );
          toast.success(t("library.envVars.toasts.updated"));
        } else {
          const trimmedValue = (value ?? "").trim();
          if (!trimmedValue) {
            toast.error(t("library.envVars.toasts.error"));
            return;
          }
          const created = await envVarsService.create({
            key: normalizedKey,
            value: trimmedValue,
            description: description ?? undefined,
          });
          setEnvVars((prev) => [...prev, created]);
          toast.success(t("library.envVars.toasts.created"));
        }
      } catch (error) {
        console.error("[EnvVars] upsert failed", error);
        toast.error(t("library.envVars.toasts.error"));
      } finally {
        setSavingEnvKey(null);
      }
    },
    [envVars, t],
  );

  const removeEnvVar = useCallback(
    async (envVarId: number) => {
      try {
        await envVarsService.remove(envVarId);
        setEnvVars((prev) => prev.filter((item) => item.id !== envVarId));
        toast.success(t("library.envVars.toasts.deleted"));
      } catch (error) {
        console.error("[EnvVars] remove failed", error);
        toast.error(t("library.envVars.toasts.error"));
      }
    },
    [t],
  );

  const refreshEnvVars = useCallback(async () => {
    try {
      const latest = await envVarsService.list();
      setEnvVars(latest);
      toast.success(t("library.envVars.toasts.refreshed"));
    } catch (error) {
      console.error("[EnvVars] refresh failed", error);
      toast.error(t("library.envVars.toasts.error"));
    }
  }, [t]);

  return {
    envVars,
    isLoading,
    upsertEnvVar,
    removeEnvVar,
    savingEnvKey,
    refreshEnvVars,
  };
}
