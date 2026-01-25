"use client";

import { useMemo, useState } from "react";

import { McpHeader } from "@/features/mcp/components/mcp-header";
import { McpGrid } from "@/features/mcp/components/mcp-grid";
import { McpSettingsDialog } from "@/features/mcp/components/mcp-settings-dialog";
import { useMcpCatalog } from "@/features/mcp/hooks/use-mcp-catalog";
import { PullToRefresh } from "@/components/ui/pull-to-refresh";

export function McpPageClient() {
  const {
    items,
    servers,
    installs,
    selectedServer,
    setSelectedServer,
    toggleInstall,
    updateServer,
    createServer,
    refresh,
    isLoading,
    loadingId,
  } = useMcpCatalog();
  const [isCreating, setIsCreating] = useState(false);

  const activeItem = useMemo(() => {
    if (!selectedServer) return null;
    return items.find((entry) => entry.server.id === selectedServer.id) || null;
  }, [items, selectedServer]);

  return (
    <>
      <McpHeader onAddMcp={() => setIsCreating(true)} />

      <div className="flex flex-1 flex-col overflow-hidden">
        <PullToRefresh onRefresh={refresh} isLoading={isLoading}>
          <div className="flex flex-1 flex-col px-6 py-6 overflow-auto">
            <div className="w-full max-w-4xl mx-auto">
              <McpGrid
                servers={servers}
                installs={installs}
                loadingId={loadingId}
                onToggleInstall={toggleInstall}
                onEditServer={(server) => setSelectedServer(server)}
              />
            </div>
          </div>
        </PullToRefresh>
      </div>

      {(activeItem || isCreating) && (
        <McpSettingsDialog
          item={activeItem}
          open={Boolean(activeItem || isCreating)}
          isNew={isCreating}
          onClose={() => {
            setSelectedServer(null);
            setIsCreating(false);
          }}
          onSave={async ({ serverId, name, serverConfig }) => {
            if (isCreating) {
              if (!name) return;
              const created = await createServer(name, serverConfig);
              if (created) {
                await toggleInstall(created.id);
              }
            } else if (serverId) {
              await updateServer(serverId, serverConfig);
            }
          }}
        />
      )}
    </>
  );
}
