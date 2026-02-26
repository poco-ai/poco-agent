"use client";

import { useState, useCallback, useMemo } from "react";
import { toast } from "sonner";

import { SkillsGrid } from "@/features/capabilities/skills/components/skills-grid";
import { SkillImportDialog } from "@/features/capabilities/skills/components/skill-import-dialog";
import { useSkillCatalog } from "@/features/capabilities/skills/hooks/use-skill-catalog";
import { PullToRefresh } from "@/components/ui/pull-to-refresh";
import { PaginatedGrid } from "@/components/ui/paginated-grid";
import { usePagination } from "@/hooks/use-pagination";
import { skillsService } from "@/features/capabilities/skills/api/skills-api";
import { useT } from "@/lib/i18n/client";
import { CapabilityContentShell } from "@/features/capabilities/components/capability-content-shell";
import { HeaderSearchInput } from "@/components/shared/header-search-input";

const PAGE_SIZE = 10;

export function SkillsPageClient() {
  const { t } = useT("translation");
  const {
    skills,
    installs,
    loadingId,
    isLoading,
    installSkill,
    deleteSkill,
    setEnabled,
    refresh,
  } = useSkillCatalog();
  const [importOpen, setImportOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const filteredSkills = useMemo(() => {
    if (!searchQuery) return skills;
    const lowerQuery = searchQuery.toLowerCase();
    return skills.filter((skill) => {
      const repo =
        typeof skill.source?.repo === "string" ? skill.source.repo : "";
      const filename =
        typeof skill.source?.filename === "string" ? skill.source.filename : "";
      return (
        skill.name.toLowerCase().includes(lowerQuery) ||
        repo.toLowerCase().includes(lowerQuery) ||
        filename.toLowerCase().includes(lowerQuery)
      );
    });
  }, [skills, searchQuery]);

  const pagination = usePagination(filteredSkills, { pageSize: PAGE_SIZE });

  // Batch toggle all skills
  const handleBatchToggle = useCallback(
    async (enabled: boolean) => {
      try {
        await Promise.all(
          installs.map((install) =>
            skillsService.updateInstall(install.id, { enabled }),
          ),
        );
        // Refresh the installs list
        refresh();
      } catch (error) {
        console.error("[SkillsPageClient] Failed to batch toggle:", error);
        toast.error(t("library.skillsManager.toasts.actionFailed"));
      }
    },
    [installs, refresh, t],
  );

  const toolbarSlot = (
    <HeaderSearchInput
      value={searchQuery}
      onChange={setSearchQuery}
      placeholder={t("library.skillsPage.searchPlaceholder")}
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
              totalItems={filteredSkills.length}
            >
              <SkillsGrid
                skills={pagination.paginatedData}
                installs={installs}
                loadingId={loadingId}
                isLoading={isLoading}
                onInstall={installSkill}
                onDeleteSkill={deleteSkill}
                onToggleEnabled={setEnabled}
                onBatchToggle={handleBatchToggle}
                createCardLabel={t("library.skillsPage.addCard")}
                onCreate={() => setImportOpen(true)}
                toolbarSlot={toolbarSlot}
              />
            </PaginatedGrid>
          </CapabilityContentShell>
        </PullToRefresh>
      </div>

      <SkillImportDialog
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onImported={refresh}
      />
    </>
  );
}
