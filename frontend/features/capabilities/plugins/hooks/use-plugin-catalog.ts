"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import type {
  Plugin,
  UserPluginInstall,
} from "@/features/capabilities/plugins/types";
import { pluginsService } from "@/features/capabilities/plugins/api/plugins-api";
import { useT } from "@/lib/i18n/client";
import {
  getStartupPreloadPromise,
  getStartupPreloadValue,
  hasStartupPreloadValue,
  invalidateStartupPreloadValues,
} from "@/lib/startup-preload";
import { playInstallSound } from "@/lib/utils/sound";

export interface PluginDisplayItem {
  plugin: Plugin;
  install?: UserPluginInstall;
}

export function usePluginCatalog() {
  const { t } = useT("translation");
  const preloadPlugins = getStartupPreloadValue("plugins");
  const preloadInstalls = getStartupPreloadValue("pluginInstalls");
  const hasPreloadedCatalog =
    hasStartupPreloadValue("plugins") &&
    hasStartupPreloadValue("pluginInstalls");
  const [plugins, setPlugins] = useState<Plugin[]>(
    hasPreloadedCatalog ? (preloadPlugins ?? []) : [],
  );
  const [installs, setInstalls] = useState<UserPluginInstall[]>(
    hasPreloadedCatalog ? (preloadInstalls ?? []) : [],
  );
  const [loadingId, setLoadingId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(!hasPreloadedCatalog);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    try {
      const [pluginsData, installsData] = await Promise.all([
        pluginsService.listPlugins(),
        pluginsService.listInstalls(),
      ]);
      setPlugins(pluginsData);
      setInstalls(installsData);
    } catch (error) {
      console.error("[Plugins] Failed to fetch data:", error);
      toast.error(t("library.pluginsManager.toasts.loadError"));
    } finally {
      setIsLoading(false);
    }
  }, [t]);

  useEffect(() => {
    let active = true;

    const refreshSilently = async () => {
      try {
        const [pluginsData, installsData] = await Promise.all([
          pluginsService.listPlugins(),
          pluginsService.listInstalls(),
        ]);
        if (!active) return;
        setPlugins(pluginsData);
        setInstalls(installsData);
      } catch (error) {
        // Keep preload data as fallback, avoid user-facing toast for background refresh.
        console.error("[Plugins] Silent refresh failed:", error);
      }
    };

    const hydrateAndRefresh = async () => {
      const canUsePreload =
        hasStartupPreloadValue("plugins") &&
        hasStartupPreloadValue("pluginInstalls");
      if (canUsePreload) {
        setPlugins(getStartupPreloadValue("plugins") ?? []);
        setInstalls(getStartupPreloadValue("pluginInstalls") ?? []);
        setIsLoading(false);
        void refreshSilently();
        return;
      }

      const preloadPromise = getStartupPreloadPromise();
      if (preloadPromise) {
        await preloadPromise;
        if (!active) return;

        const hasHydratedCatalog =
          hasStartupPreloadValue("plugins") &&
          hasStartupPreloadValue("pluginInstalls");
        if (hasHydratedCatalog) {
          setPlugins(getStartupPreloadValue("plugins") ?? []);
          setInstalls(getStartupPreloadValue("pluginInstalls") ?? []);
          setIsLoading(false);
          void refreshSilently();
          return;
        }
      }

      if (!active) return;
      await refresh();
    };

    hydrateAndRefresh();

    return () => {
      active = false;
    };
  }, [refresh]);

  const installPlugin = useCallback(
    async (pluginId: number) => {
      setLoadingId(pluginId);
      const previouslyEnabled = installs.filter((install) => install.enabled);
      try {
        if (previouslyEnabled.length > 0) {
          await pluginsService.bulkUpdateInstalls({
            enabled: false,
            install_ids: previouslyEnabled.map((install) => install.id),
          });
        }
        const created = await pluginsService.createInstall({
          plugin_id: pluginId,
          enabled: true,
        });
        setInstalls((prev) => [
          created,
          ...prev.map((install) =>
            previouslyEnabled.some((enabled) => enabled.id === install.id)
              ? { ...install, enabled: false }
              : install,
          ),
        ]);
        const installNote =
          previouslyEnabled.length > 0
            ? ` ${t("library.pluginsManager.toasts.exclusiveEnabled")}`
            : "";
        toast.success(
          `${t("library.pluginsManager.toasts.installed")}${installNote}`,
        );
        playInstallSound();
        invalidateStartupPreloadValues(["pluginInstalls"]);
      } catch (error) {
        console.error("[Plugins] install failed:", error);
        if (previouslyEnabled.length > 0) {
          try {
            await pluginsService.bulkUpdateInstalls({
              enabled: true,
              install_ids: previouslyEnabled.map((install) => install.id),
            });
          } catch (restoreError) {
            console.error(
              "[Plugins] restore enabled presets failed:",
              restoreError,
            );
          }
        }
        toast.error(t("library.pluginsManager.toasts.actionError"));
      } finally {
        setLoadingId(null);
      }
    },
    [installs, t],
  );

  const deletePlugin = useCallback(
    async (pluginId: number) => {
      setLoadingId(pluginId);
      try {
        await pluginsService.deletePlugin(pluginId);
        setPlugins((prev) => prev.filter((plugin) => plugin.id !== pluginId));
        setInstalls((prev) =>
          prev.filter((install) => install.plugin_id !== pluginId),
        );
        toast.success(t("common.deleted"));
        invalidateStartupPreloadValues(["plugins", "pluginInstalls"]);
      } catch (error) {
        console.error("[Plugins] delete failed:", error);
        toast.error(t("library.pluginsManager.toasts.actionError"));
      } finally {
        setLoadingId(null);
      }
    },
    [t],
  );

  const setEnabled = useCallback(
    async (installId: number, enabled: boolean) => {
      setLoadingId(installId);
      const previousInstalls = installs;
      const install = installs.find((i) => i.id === installId);
      const plugin = install
        ? plugins.find((p) => p.id === install.plugin_id)
        : null;
      const pluginName =
        plugin?.name || t("library.pluginsManager.unknownPlugin");
      const otherEnabled = enabled
        ? installs.filter((i) => i.enabled && i.id !== installId)
        : [];
      const shouldRestoreOthers = enabled && otherEnabled.length > 0;

      setInstalls((prev) =>
        prev.map((i) => {
          if (i.id === installId) return { ...i, enabled };
          if (enabled && otherEnabled.some((other) => other.id === i.id)) {
            return { ...i, enabled: false };
          }
          return i;
        }),
      );
      try {
        if (shouldRestoreOthers) {
          await pluginsService.bulkUpdateInstalls({
            enabled: false,
            install_ids: otherEnabled.map((installItem) => installItem.id),
          });
        }
        const updated = await pluginsService.updateInstall(installId, {
          enabled,
        });
        setInstalls((prev) =>
          prev.map((i) => {
            if (i.id === installId) return updated;
            if (enabled && otherEnabled.some((other) => other.id === i.id)) {
              return { ...i, enabled: false };
            }
            return i;
          }),
        );
        toast.success(
          enabled
            ? `${pluginName} ${t("library.pluginsManager.toasts.enabled")}${
                otherEnabled.length > 0
                  ? ` ${t("library.pluginsManager.toasts.exclusiveEnabled")}`
                  : ""
              }`
            : `${pluginName} ${t("library.pluginsManager.toasts.disabled")}`,
        );
        if (enabled) {
          playInstallSound();
        }
        invalidateStartupPreloadValues(["pluginInstalls"]);
      } catch (error) {
        console.error("[Plugins] setEnabled failed:", error);
        if (shouldRestoreOthers) {
          try {
            await pluginsService.bulkUpdateInstalls({
              enabled: true,
              install_ids: otherEnabled.map((installItem) => installItem.id),
            });
          } catch (restoreError) {
            console.error(
              "[Plugins] restore enabled presets failed:",
              restoreError,
            );
          }
        }
        setInstalls(previousInstalls);
        toast.error(t("library.pluginsManager.toasts.actionError"));
      } finally {
        setLoadingId(null);
      }
    },
    [t, installs, plugins],
  );

  const items: PluginDisplayItem[] = useMemo(() => {
    return plugins.map((plugin) => ({
      plugin,
      install: installs.find((i) => i.plugin_id === plugin.id),
    }));
  }, [plugins, installs]);

  return {
    plugins,
    installs,
    items,
    isLoading,
    loadingId,
    refresh,
    installPlugin,
    deletePlugin,
    setEnabled,
  };
}
