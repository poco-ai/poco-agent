"use client";

import { useCallback, useState } from "react";
import { toast } from "sonner";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useT } from "@/lib/i18n/client";
import { envVarsService } from "@/features/capabilities/env-vars/services/env-vars-service";
import type { EnvVar } from "@/features/capabilities/env-vars/types";

export interface EnvVarUpsertInput {
  key: string;
  value?: string;
  description?: string | null;
}

const ENV_VARS_QUERY_KEY = ["envVars"] as const;
const EMPTY_ENV_VARS: EnvVar[] = [];

export function useEnvVarsStore() {
  const { t } = useT("translation");
  const [savingEnvKey, setSavingEnvKey] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const envVarsQuery = useQuery({
    queryKey: ENV_VARS_QUERY_KEY,
    queryFn: () => envVarsService.list(),
  });

  const envVars = envVarsQuery.data ?? EMPTY_ENV_VARS;

  const createMutation = useMutation({
    mutationFn: envVarsService.create,
    onSuccess: (created) => {
      queryClient.setQueryData<EnvVar[]>(ENV_VARS_QUERY_KEY, (prev) => [
        ...(prev ?? []),
        created,
      ]);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({
      id,
      input,
    }: {
      id: number;
      input: Parameters<typeof envVarsService.update>[1];
    }) => envVarsService.update(id, input),
    onSuccess: (updated) => {
      queryClient.setQueryData<EnvVar[]>(ENV_VARS_QUERY_KEY, (prev) =>
        (prev ?? []).map((item) => (item.id === updated.id ? updated : item)),
      );
    },
  });

  const removeMutation = useMutation({
    mutationFn: (id: number) => envVarsService.remove(id),
    onSuccess: (_resp, id) => {
      queryClient.setQueryData<EnvVar[]>(ENV_VARS_QUERY_KEY, (prev) =>
        (prev ?? []).filter((item) => item.id !== id),
      );
    },
  });

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
          await updateMutation.mutateAsync({
            id: existing.id,
            input: {
              value: value?.trim() ? value.trim() : undefined,
              description: description ?? existing.description,
            },
          });
          toast.success(t("library.envVars.toasts.updated"));
        } else {
          const trimmedValue = (value ?? "").trim();
          if (!trimmedValue) {
            toast.error(t("library.envVars.toasts.error"));
            return;
          }
          await createMutation.mutateAsync({
            key: normalizedKey,
            value: trimmedValue,
            description: description ?? undefined,
          });
          toast.success(t("library.envVars.toasts.created"));
        }
      } catch (error) {
        console.error("[EnvVars] upsert failed", error);
        toast.error(t("library.envVars.toasts.error"));
      } finally {
        setSavingEnvKey(null);
      }
    },
    [createMutation, envVars, t, updateMutation],
  );

  const removeEnvVar = useCallback(
    async (envVarId: number) => {
      try {
        await removeMutation.mutateAsync(envVarId);
        toast.success(t("library.envVars.toasts.deleted"));
      } catch (error) {
        console.error("[EnvVars] remove failed", error);
        toast.error(t("library.envVars.toasts.error"));
      }
    },
    [removeMutation, t],
  );

  const refreshEnvVars = useCallback(async () => {
    try {
      await envVarsQuery.refetch();
      toast.success(t("library.envVars.toasts.refreshed"));
    } catch (error) {
      console.error("[EnvVars] refresh failed", error);
      toast.error(t("library.envVars.toasts.error"));
    }
  }, [envVarsQuery, t]);

  return {
    envVars,
    isLoading: envVarsQuery.isLoading,
    upsertEnvVar,
    removeEnvVar,
    savingEnvKey,
    refreshEnvVars,
  };
}
