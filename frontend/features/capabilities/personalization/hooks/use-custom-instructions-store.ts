"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { useT } from "@/lib/i18n/client";
import { customInstructionsService } from "@/features/capabilities/personalization/api/custom-instructions-api";
import type {
  CustomInstructionsSettings,
  CustomInstructionsUpsertInput,
} from "@/features/capabilities/personalization/types";

export function useCustomInstructionsStore() {
  const { t } = useT("translation");
  const [settings, setSettings] = useState<CustomInstructionsSettings | null>(
    null,
  );
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      try {
        const data = await customInstructionsService.get();
        setSettings(data);
      } catch (error) {
        console.error(
          "[Personalization] Failed to fetch custom instructions:",
          error,
        );
        toast.error(t("library.personalization.toasts.error"));
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, [t]);

  const refresh = useCallback(async () => {
    try {
      const data = await customInstructionsService.get();
      setSettings(data);
      toast.success(t("library.personalization.toasts.refreshed"));
    } catch (error) {
      console.error("[Personalization] refresh failed:", error);
      toast.error(t("library.personalization.toasts.error"));
    }
  }, [t]);

  const save = useCallback(
    async (input: CustomInstructionsUpsertInput) => {
      setIsSaving(true);
      try {
        const updated = await customInstructionsService.upsert(input);
        setSettings(updated);
        toast.success(t("library.personalization.toasts.saved"));
        return updated;
      } catch (error) {
        console.error("[Personalization] save failed:", error);
        toast.error(t("library.personalization.toasts.error"));
        return null;
      } finally {
        setIsSaving(false);
      }
    },
    [t],
  );

  const clear = useCallback(async () => {
    setIsSaving(true);
    try {
      await customInstructionsService.remove();
      setSettings({ enabled: false, content: "", updated_at: null });
      toast.success(t("library.personalization.toasts.cleared"));
    } catch (error) {
      console.error("[Personalization] clear failed:", error);
      toast.error(t("library.personalization.toasts.error"));
    } finally {
      setIsSaving(false);
    }
  }, [t]);

  return {
    settings,
    isLoading,
    isSaving,
    refresh,
    save,
    clear,
  };
}
