"use client";

import * as React from "react";
import { Settings, PowerOff, AlertTriangle, Trash2 } from "lucide-react";

import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { SkeletonShimmer } from "@/components/ui/skeleton-shimmer";
import { StaggeredList } from "@/components/ui/staggered-entrance";
import type {
  McpServer,
  UserMcpInstall,
} from "@/features/capabilities/mcp/types";
import { getEffectiveInstallState } from "@/features/capabilities/lib/install-policy";
import { useT } from "@/lib/i18n/client";
import { CapabilityCreateCard } from "@/features/capabilities/components/capability-create-card";
import { CapabilitySourceAvatar } from "@/features/capabilities/components/capability-source-avatar";

const MCP_LIMIT = 3;

interface McpGridProps {
  servers: McpServer[];
  installs: UserMcpInstall[];
  loadingId?: number | null;
  isLoading?: boolean;
  displayMode?: "personal" | "runtime" | "admin";
  onToggleInstall?: (serverId: number) => void;
  onDeleteServer?: (serverId: number) => void;
  onEditServer?: (server: McpServer) => void;
  onBatchToggle?: (enabled: boolean) => void;
  createCardLabel?: string;
  onCreate?: () => void;
  toolbarSlot?: React.ReactNode;
}

export function McpGrid({
  servers,
  installs,
  loadingId,
  isLoading = false,
  displayMode = "personal",
  onToggleInstall,
  onDeleteServer,
  onEditServer,
  onBatchToggle,
  createCardLabel,
  onCreate,
  toolbarSlot,
}: McpGridProps) {
  const { t } = useT("translation");
  const hoverActionsClass =
    "flex items-center gap-2 transition-opacity md:opacity-0 md:pointer-events-none md:group-hover:opacity-100 md:group-hover:pointer-events-auto";
  const installByServerId = React.useMemo(() => {
    const map = new Map<number, UserMcpInstall>();
    for (const install of installs) {
      map.set(install.server_id, install);
    }
    return map;
  }, [installs]);
  const visibleServers = React.useMemo(() => {
    if (displayMode === "admin") {
      return servers.filter((server) => server.scope === "system");
    }
    if (displayMode === "personal") {
      return servers.filter((server) => server.scope !== "system");
    }
    return servers;
  }, [displayMode, servers]);
  const enabledCount = React.useMemo(
    () =>
      visibleServers.reduce((count, server) => {
        const install = installByServerId.get(server.id);
        return (
          count + (getEffectiveInstallState(server, install).isEnabled ? 1 : 0)
        );
      }, 0),
    [installByServerId, visibleServers],
  );

  return (
    <div className="space-y-6">
      {/* Warning alert */}
      {enabledCount > MCP_LIMIT && (
        <Alert className="border-amber-500/50 bg-amber-500/10 text-amber-600 dark:text-amber-500 [&>svg]:text-amber-600 dark:[&>svg]:text-amber-500 *:data-[slot=alert-description]:text-amber-600/90 dark:*:data-[slot=alert-description]:text-amber-500/90">
          <AlertTriangle className="size-4" />
          <AlertDescription>
            {t("hero.warnings.tooManyMcps", { count: enabledCount })}
          </AlertDescription>
        </Alert>
      )}

      {/* Action bar */}
      <div className="rounded-xl bg-muted/50 px-5 py-3 flex flex-wrap items-center gap-3 md:flex-nowrap md:justify-between">
        <span className="text-sm text-muted-foreground">
          {t("mcpGrid.enabledServers", { count: enabledCount })}
        </span>
        <div className="flex flex-1 flex-nowrap items-center justify-end gap-2 overflow-x-auto">
          {enabledCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onBatchToggle?.(false)}
              className="gap-2"
              aria-label={t("mcpGrid.turnOffAll")}
            >
              <PowerOff className="size-4" />
              <span className="hidden sm:inline">
                {t("mcpGrid.turnOffAll")}
              </span>
            </Button>
          )}
          {toolbarSlot}
        </div>
      </div>

      <div className="space-y-3">
        {createCardLabel ? (
          <CapabilityCreateCard label={createCardLabel} onClick={onCreate} />
        ) : null}

        {isLoading && servers.length === 0 ? (
          <SkeletonShimmer count={5} itemClassName="min-h-[64px]" gap="md" />
        ) : visibleServers.length === 0 ? (
          <div className="rounded-xl border border-border/50 bg-muted/10 px-4 py-6 text-sm text-muted-foreground text-center">
            {t("mcpGrid.noMcpServers")}
          </div>
        ) : (
          <StaggeredList
            items={visibleServers}
            show={!isLoading}
            keyExtractor={(server) => server.id}
            staggerDelay={50}
            duration={400}
            renderItem={(server) => {
              const install = installByServerId.get(server.id);
              const installState = getEffectiveInstallState(server, install);
              const isEnabled = installState.isEnabled;
              const isRowLoading = loadingId === server.id;
              const avatarStatus =
                enabledCount > MCP_LIMIT && isEnabled
                  ? "error"
                  : isEnabled
                    ? "active"
                    : "inactive";

              return (
                <div
                  className={`group flex items-center gap-4 rounded-xl border px-4 py-3 min-h-[64px] ${
                    installState.isInstalled
                      ? "border-border/70 bg-card"
                      : "border-border/40 bg-muted/20"
                  }`}
                >
                  <CapabilitySourceAvatar
                    name={server.name}
                    source={server.source}
                    status={avatarStatus}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium">{server.name}</span>
                      <Badge
                        variant="outline"
                        className="text-xs text-muted-foreground"
                      >
                        {server.scope === "system"
                          ? t("mcpGrid.system")
                          : t("mcpGrid.user")}
                      </Badge>
                      {server.default_enabled && !server.force_enabled ? (
                        <Badge variant="secondary" className="text-xs">
                          {t("common.default")}
                        </Badge>
                      ) : null}
                      {server.force_enabled ? (
                        <Badge variant="destructive" className="text-xs">
                          {t("common.forced")}
                        </Badge>
                      ) : null}
                    </div>
                    {server.description && (
                      <p className="mt-1 truncate text-xs text-muted-foreground">
                        {server.description}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    <div className={hoverActionsClass}>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-8"
                        onClick={() => onEditServer?.(server)}
                        title={t("mcpGrid.settings")}
                      >
                        <Settings className="size-4" />
                      </Button>
                      {server.scope === "user" && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8"
                          onClick={() => onDeleteServer?.(server.id)}
                          disabled={isRowLoading}
                          title={t("common.delete")}
                        >
                          <Trash2 className="size-4" />
                        </Button>
                      )}
                    </div>
                    {displayMode === "admin" ? null : (
                      <Switch
                        checked={isEnabled}
                        onCheckedChange={() => onToggleInstall?.(server.id)}
                        disabled={isRowLoading || server.force_enabled}
                      />
                    )}
                  </div>
                </div>
              );
            }}
          />
        )}
      </div>
    </div>
  );
}
