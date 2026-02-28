"use client";

import * as React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import type {
  McpServer,
  UserMcpInstall,
} from "@/features/capabilities/mcp/types";
import { mcpService } from "@/features/capabilities/mcp/api/mcp-api";
import { useEnvVarsStore } from "@/features/capabilities/env-vars/hooks/use-env-vars-store";
import { useT } from "@/lib/i18n/client";
import {
  getStartupPreloadPromise,
  getStartupPreloadValue,
  hasStartupPreloadValue,
  invalidateStartupPreloadValues,
} from "@/lib/startup-preload";
import { CheckCircle2, CircleOff } from "lucide-react";
import { playInstallSound } from "@/lib/utils/sound";

export interface McpDisplayItem {
  server: McpServer;
  install?: UserMcpInstall;
}

export function useMcpCatalog() {
  const { t } = useT("translation");
  const preloadServers = getStartupPreloadValue("mcpServers");
  const preloadInstalls = getStartupPreloadValue("mcpInstalls");
  const hasPreloadedCatalog =
    hasStartupPreloadValue("mcpServers") &&
    hasStartupPreloadValue("mcpInstalls");
  const [servers, setServers] = useState<McpServer[]>(
    hasPreloadedCatalog ? (preloadServers ?? []) : [],
  );
  const [installs, setInstalls] = useState<UserMcpInstall[]>(
    hasPreloadedCatalog ? (preloadInstalls ?? []) : [],
  );
  const [selectedServer, setSelectedServer] = useState<McpServer | null>(null);
  const [loadingId, setLoadingId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(!hasPreloadedCatalog);
  const envVarStore = useEnvVarsStore();

  const refresh = useCallback(async () => {
    setIsLoading(true);
    try {
      const [serversData, installsData] = await Promise.all([
        mcpService.listServers(),
        mcpService.listInstalls(),
      ]);
      setServers(serversData);
      setInstalls(installsData);
    } catch (error) {
      console.error("[MCP] Failed to fetch data:", error);
      toast.error(t("library.mcpLibrary.toasts.error"));
    } finally {
      setIsLoading(false);
    }
  }, [t]);

  useEffect(() => {
    let active = true;

    const refreshSilently = async () => {
      try {
        const [serversData, installsData] = await Promise.all([
          mcpService.listServers(),
          mcpService.listInstalls(),
        ]);
        if (!active) return;
        setServers(serversData);
        setInstalls(installsData);
      } catch (error) {
        // Keep preload data as fallback, avoid user-facing toast for background refresh.
        console.error("[MCP] Silent refresh failed:", error);
      }
    };

    const hydrateAndRefresh = async () => {
      const canUsePreload =
        hasStartupPreloadValue("mcpServers") &&
        hasStartupPreloadValue("mcpInstalls");
      if (canUsePreload) {
        setServers(getStartupPreloadValue("mcpServers") ?? []);
        setInstalls(getStartupPreloadValue("mcpInstalls") ?? []);
        setIsLoading(false);
        void refreshSilently();
        return;
      }

      const preloadPromise = getStartupPreloadPromise();
      if (preloadPromise) {
        await preloadPromise;
        if (!active) return;

        const hasHydratedCatalog =
          hasStartupPreloadValue("mcpServers") &&
          hasStartupPreloadValue("mcpInstalls");
        if (hasHydratedCatalog) {
          setServers(getStartupPreloadValue("mcpServers") ?? []);
          setInstalls(getStartupPreloadValue("mcpInstalls") ?? []);
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

  const toggleInstall = useCallback(
    async (serverId: number) => {
      const install = installs.find((entry) => entry.server_id === serverId);
      setLoadingId(serverId);

      // Optimistic update - update UI immediately
      const optimisticEnabled = install ? !install.enabled : true;
      if (install) {
        setInstalls((prev) =>
          prev.map((item) =>
            item.id === install.id
              ? { ...item, enabled: optimisticEnabled }
              : item,
          ),
        );
      } else {
        // Create a temporary install for optimistic UI
        const tempInstall: UserMcpInstall = {
          id: -1, // temporary ID
          user_id: "", // temporary user_id
          server_id: serverId,
          enabled: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        setInstalls((prev) => [...prev, tempInstall]);
      }

      try {
        const server = servers.find((s) => s.id === serverId);
        const serverName = server?.name || "";

        if (install) {
          const updated = await mcpService.updateInstall(install.id, {
            enabled: optimisticEnabled,
          });
          // Update with real data from server
          setInstalls((prev) =>
            prev.map((item) => (item.id === install.id ? updated : item)),
          );
          toast.success(
            `${serverName} MCP ${
              updated.enabled
                ? t("library.mcpLibrary.toasts.enabled")
                : t("library.mcpLibrary.toasts.disabled")
            }`,
            {
              icon: updated.enabled
                ? React.createElement(CheckCircle2, {
                    className: "size-4 text-foreground",
                  })
                : React.createElement(CircleOff, {
                    className: "size-4 text-muted-foreground",
                  }),
            },
          );
          // Play sound on enable
          if (updated.enabled) {
            playInstallSound();
          }
          // Trigger success haptic feedback
          if (typeof window !== "undefined" && "vibrate" in navigator) {
            navigator.vibrate(50);
          }
          invalidateStartupPreloadValues(["mcpInstalls"]);
        } else {
          const created = await mcpService.createInstall({
            server_id: serverId,
            enabled: true,
          });
          // Replace temporary install with real one
          setInstalls((prev) =>
            prev.map((item) =>
              item.server_id === serverId && item.id === -1 ? created : item,
            ),
          );
          toast.success(
            `${serverName} MCP ${t("library.mcpLibrary.toasts.enabled")}`,
            {
              icon: React.createElement(CheckCircle2, {
                className: "size-4 text-primary",
              }),
            },
          );
          // Play sound on installation
          playInstallSound();
          // Trigger success haptic feedback
          if (typeof window !== "undefined" && "vibrate" in navigator) {
            navigator.vibrate(50);
          }
          invalidateStartupPreloadValues(["mcpInstalls"]);
        }
      } catch (error) {
        console.error("[MCP] toggle failed:", error);
        // Rollback optimistic update on error
        if (install) {
          setInstalls((prev) =>
            prev.map((item) =>
              item.id === install.id
                ? { ...item, enabled: install.enabled }
                : item,
            ),
          );
        } else {
          setInstalls((prev) =>
            prev.filter(
              (item) => !(item.server_id === serverId && item.id === -1),
            ),
          );
        }
        toast.error(t("library.mcpLibrary.toasts.error"));
      } finally {
        setLoadingId(null);
      }
    },
    [installs, servers, t],
  );

  const updateServer = useCallback(
    async (serverId: number, server_config: Record<string, unknown>) => {
      setLoadingId(serverId);
      try {
        const updated = await mcpService.updateServer(serverId, {
          server_config,
        });
        setServers((prev) =>
          prev.map((item) => (item.id === serverId ? updated : item)),
        );
        toast.success(t("library.mcpLibrary.toasts.updated"));
        playInstallSound();
        invalidateStartupPreloadValues(["mcpServers"]);
        return updated;
      } catch (error) {
        console.error("[MCP] update failed:", error);
        throw error;
      } finally {
        setLoadingId(null);
      }
    },
    [t],
  );

  const createServer = useCallback(
    async (name: string, server_config: Record<string, unknown>) => {
      setLoadingId(-1);
      try {
        const created = await mcpService.createServer({
          name,
          server_config,
        });
        setServers((prev) => [created, ...prev]);
        toast.success(t("library.mcpLibrary.toasts.created"));
        playInstallSound();
        invalidateStartupPreloadValues(["mcpServers"]);
        return created;
      } catch (error) {
        console.error("[MCP] create failed:", error);
        throw error;
      } finally {
        setLoadingId(null);
      }
    },
    [t],
  );

  const deleteServer = useCallback(
    async (serverId: number) => {
      setLoadingId(serverId);
      try {
        await mcpService.deleteServer(serverId);
        await refresh();
        const server = servers.find((s) => s.id === serverId);
        const serverName = server?.name || "";
        toast.success(`${serverName} MCP ${t("common.deleted")}`);
        invalidateStartupPreloadValues(["mcpServers", "mcpInstalls"]);
      } catch (error) {
        console.error("[MCP] delete failed:", error);
        toast.error(t("library.mcpLibrary.toasts.error"));
      } finally {
        setLoadingId(null);
      }
    },
    [refresh, servers, t],
  );

  const items: McpDisplayItem[] = useMemo(() => {
    return servers.map((server) => ({
      server,
      install: installs.find((entry) => entry.server_id === server.id),
    }));
  }, [servers, installs]);

  return {
    items,
    servers,
    installs,
    isLoading,
    envVars: envVarStore.envVars,
    selectedServer,
    setSelectedServer,
    toggleInstall,
    updateServer,
    createServer,
    deleteServer,
    refresh,
    loadingId,
    savingEnvKey: envVarStore.savingEnvKey,
    refreshEnvVars: envVarStore.refreshEnvVars,
    upsertEnvVar: envVarStore.upsertEnvVar,
    removeEnvVar: envVarStore.removeEnvVar,
  };
}
