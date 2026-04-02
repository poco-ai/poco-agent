"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { useT } from "@/lib/i18n/client";
import { presetsService } from "@/features/capabilities/presets/api/presets-api";
import type {
  Preset,
  PresetCreateInput,
  PresetUpdateInput,
} from "@/features/capabilities/presets/lib/preset-types";

export function usePresetCatalog() {
  const { t } = useT("translation");
  const [presets, setPresets] = useState<Preset[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [savingKey, setSavingKey] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await presetsService.listPresets({ revalidate: 0 });
      setPresets(data);
    } catch (error) {
      console.error("[Presets] Failed to fetch:", error);
      toast.error(t("library.presetsPage.toasts.loadError"));
    } finally {
      setIsLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const createPreset = useCallback(
    async (input: PresetCreateInput) => {
      setSavingKey("create");
      try {
        const created = await presetsService.createPreset(input);
        setPresets((prev) =>
          [created, ...prev].sort((a, b) => a.name.localeCompare(b.name)),
        );
        toast.success(t("library.presetsPage.toasts.created"));
        return created;
      } catch (error) {
        console.error("[Presets] create failed:", error);
        toast.error(t("library.presetsPage.toasts.saveFailed"));
        return null;
      } finally {
        setSavingKey(null);
      }
    },
    [t],
  );

  const updatePreset = useCallback(
    async (presetId: number, input: PresetUpdateInput) => {
      setSavingKey(String(presetId));
      try {
        const updated = await presetsService.updatePreset(presetId, input);
        setPresets((prev) =>
          prev
            .map((preset) => (preset.preset_id === presetId ? updated : preset))
            .sort((a, b) => a.name.localeCompare(b.name)),
        );
        toast.success(t("library.presetsPage.toasts.updated"));
        return updated;
      } catch (error) {
        console.error("[Presets] update failed:", error);
        toast.error(t("library.presetsPage.toasts.saveFailed"));
        return null;
      } finally {
        setSavingKey(null);
      }
    },
    [t],
  );

  const deletePreset = useCallback(
    async (presetId: number) => {
      setSavingKey(String(presetId));
      try {
        await presetsService.deletePreset(presetId);
        setPresets((prev) =>
          prev.filter((preset) => preset.preset_id !== presetId),
        );
        toast.success(t("library.presetsPage.toasts.deleted"));
      } catch (error) {
        console.error("[Presets] delete failed:", error);
        toast.error(t("library.presetsPage.toasts.deleteFailed"));
      } finally {
        setSavingKey(null);
      }
    },
    [t],
  );

  return {
    presets,
    isLoading,
    savingKey,
    refresh,
    createPreset,
    updatePreset,
    deletePreset,
  };
}
