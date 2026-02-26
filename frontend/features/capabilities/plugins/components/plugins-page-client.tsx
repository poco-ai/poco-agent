"use client";

import { useState, useCallback, useMemo } from "react";
import { toast } from "sonner";

import { PluginsGrid } from "@/features/capabilities/plugins/components/plugins-grid";
import { PluginImportDialog } from "@/features/capabilities/plugins/components/plugin-import-dialog";
import { usePluginCatalog } from "@/features/capabilities/plugins/hooks/use-plugin-catalog";
import { PullToRefresh } from "@/components/ui/pull-to-refresh";
import { PaginatedGrid } from "@/components/ui/paginated-grid";
import { usePagination } from "@/hooks/use-pagination";
import { pluginsService } from "@/features/capabilities/plugins/api/plugins-api";
import { useT } from "@/lib/i18n/client";
import { CapabilityContentShell } from "@/features/capabilities/components/capability-content-shell";
import { HeaderSearchInput } from "@/components/shared/header-search-input";

const PAGE_SIZE = 10;

export function PluginsPageClient() {
  const { t } = useT("translation");
  const {
    plugins,
    installs,
    loadingId,
    isLoading,
    installPlugin,
    deletePlugin,
    setEnabled,
    refresh,
  } = usePluginCatalog();
  const [importOpen, setImportOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const filteredPlugins = useMemo(() => {
    if (!searchQuery) return plugins;
    const lowerQuery = searchQuery.toLowerCase();
    return plugins.filter((plugin) => {
      const repo =
        typeof plugin.source?.repo === "string" ? plugin.source.repo : "";
      const filename =
        typeof plugin.source?.filename === "string"
          ? plugin.source.filename
          : "";
      const description =
        typeof plugin.description === "string" ? plugin.description : "";
      return (
        plugin.name.toLowerCase().includes(lowerQuery) ||
        description.toLowerCase().includes(lowerQuery) ||
        repo.toLowerCase().includes(lowerQuery) ||
        filename.toLowerCase().includes(lowerQuery)
      );
    });
  }, [plugins, searchQuery]);

  const pagination = usePagination(filteredPlugins, { pageSize: PAGE_SIZE });

  const handleBatchToggle = useCallback(
    async (enabled: boolean) => {
      try {
        await Promise.all(
          installs.map((install) =>
            pluginsService.updateInstall(install.id, { enabled }),
          ),
        );
        refresh();
      } catch (error) {
        console.error("[PluginsPageClient] Failed to batch toggle:", error);
        toast.error(t("library.pluginsManager.toasts.actionFailed"));
      }
    },
    [installs, refresh, t],
  );

  const toolbarSlot = (
    <HeaderSearchInput
      value={searchQuery}
      onChange={setSearchQuery}
      placeholder={t("library.pluginsPage.searchPlaceholder")}
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
              totalItems={filteredPlugins.length}
            >
              <PluginsGrid
                plugins={pagination.paginatedData}
                installs={installs}
                loadingId={loadingId}
                isLoading={isLoading}
                onInstall={installPlugin}
                onDeletePlugin={deletePlugin}
                onToggleEnabled={setEnabled}
                onBatchToggle={handleBatchToggle}
                createCardLabel={t("library.pluginsPage.addCard")}
                onCreate={() => setImportOpen(true)}
                toolbarSlot={toolbarSlot}
              />
            </PaginatedGrid>
          </CapabilityContentShell>
        </PullToRefresh>
      </div>

      <PluginImportDialog
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onImported={refresh}
      />
    </>
  );
}
