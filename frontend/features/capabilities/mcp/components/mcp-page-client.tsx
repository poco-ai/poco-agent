"use client";

import { useMemo, useState, useCallback } from "react";
import { toast } from "sonner";

import { McpGrid } from "@/features/capabilities/mcp/components/mcp-grid";
import { McpSettingsDialog } from "@/features/capabilities/mcp/components/mcp-settings-dialog";
import { useMcpCatalog } from "@/features/capabilities/mcp/hooks/use-mcp-catalog";
import { PullToRefresh } from "@/components/ui/pull-to-refresh";
import { PaginatedGrid } from "@/components/ui/paginated-grid";
import { usePagination } from "@/hooks/use-pagination";
import { mcpService } from "@/features/capabilities/mcp/api/mcp-api";
import { useT } from "@/lib/i18n/client";
import { CapabilityContentShell } from "@/features/capabilities/components/capability-content-shell";
import { HeaderSearchInput } from "@/components/shared/header-search-input";

const PAGE_SIZE = 10;

export function McpPageClient() {
  const { t } = useT("translation");
  const {
    items,
    servers,
    installs,
    selectedServer,
    setSelectedServer,
    toggleInstall,
    updateServer,
    createServer,
    deleteServer,
    refresh,
    isLoading,
    loadingId,
  } = useMcpCatalog();
  const [isCreating, setIsCreating] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const filteredServers = useMemo(() => {
    if (!searchQuery) return servers;
    const lowerQuery = searchQuery.toLowerCase();
    return servers.filter((server) => {
      const description =
        typeof server.description === "string" ? server.description : "";
      return (
        server.name.toLowerCase().includes(lowerQuery) ||
        description.toLowerCase().includes(lowerQuery) ||
        String(server.id).includes(lowerQuery)
      );
    });
  }, [servers, searchQuery]);

  const pagination = usePagination(filteredServers, { pageSize: PAGE_SIZE });

  // Batch toggle all MCPs
  const handleBatchToggle = useCallback(
    async (enabled: boolean) => {
      try {
        const targetInstalls = enabled
          ? installs
          : installs.filter((install) => {
              const server = servers.find(
                (item) => item.id === install.server_id,
              );
              return !server?.force_enabled;
            });
        if (targetInstalls.length === 0) {
          toast.message(t("library.mcpLibrary.toasts.noEligibleBatchToggle"));
          return;
        }
        await Promise.all(
          targetInstalls.map((install) =>
            mcpService.updateInstall(install.id, { enabled }),
          ),
        );
        refresh();
      } catch (error) {
        console.error("[McpPageClient] Failed to batch toggle:", error);
        toast.error(t("library.mcpLibrary.toasts.actionFailed"));
      }
    },
    [installs, refresh, servers, t],
  );

  const activeItem = useMemo(() => {
    if (!selectedServer) return null;
    return items.find((entry) => entry.server.id === selectedServer.id) || null;
  }, [items, selectedServer]);

  const toolbarSlot = (
    <HeaderSearchInput
      value={searchQuery}
      onChange={setSearchQuery}
      placeholder={t("library.mcpLibrary.searchPlaceholder")}
      className="w-full md:w-64"
    />
  );

  return (
    <>
      <div className="flex flex-1 flex-col overflow-hidden">
        <PullToRefresh onRefresh={refresh} isLoading={isLoading}>
          <CapabilityContentShell>
            <PaginatedGrid
              currentPage={pagination.currentPage}
              totalPages={pagination.totalPages}
              pageSize={pagination.pageSize}
              onPageChange={pagination.goToPage}
              onPageSizeChange={pagination.setPageSize}
              totalItems={filteredServers.length}
            >
              <McpGrid
                servers={pagination.paginatedData}
                installs={installs}
                loadingId={loadingId}
                isLoading={isLoading}
                displayMode="runtime"
                onToggleInstall={toggleInstall}
                onDeleteServer={deleteServer}
                onEditServer={(server) => setSelectedServer(server)}
                onBatchToggle={handleBatchToggle}
                createCardLabel={t("library.mcpLibrary.addCard")}
                onCreate={() => setIsCreating(true)}
                toolbarSlot={toolbarSlot}
              />
            </PaginatedGrid>
          </CapabilityContentShell>
        </PullToRefresh>
      </div>

      {(activeItem || isCreating) && (
        <McpSettingsDialog
          item={activeItem}
          open={Boolean(activeItem || isCreating)}
          isNew={isCreating}
          readOnly={Boolean(activeItem) && !isCreating}
          onClose={() => {
            setSelectedServer(null);
            setIsCreating(false);
          }}
          onSave={async ({ serverId, name, description, serverConfig }) => {
            if (isCreating) {
              const created = await createServer(
                name ?? "",
                serverConfig,
                description,
              );
              await toggleInstall(created.id);
            } else if (serverId) {
              await updateServer(serverId, serverConfig, description);
            } else {
              throw new Error(t("library.mcpLibrary.toasts.error"));
            }
          }}
        />
      )}
    </>
  );
}
