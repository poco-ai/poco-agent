"use client";

import { useState, useCallback, useMemo } from "react";
import { toast } from "sonner";

import { SkillsGrid } from "@/features/capabilities/skills/components/skills-grid";
import { SkillImportDialog } from "@/features/capabilities/skills/components/skill-import-dialog";
import { SkillSettingsDialog } from "@/features/capabilities/skills/components/skill-settings-dialog";
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
  const [selectedSkillId, setSelectedSkillId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const filteredSkills = useMemo(() => {
    const normalizedSkills = [...skills].sort((left, right) => {
      if (left.scope === right.scope) {
        return left.name.localeCompare(right.name);
      }
      return left.scope === "system" ? -1 : 1;
    });

    if (!searchQuery) return normalizedSkills;
    const lowerQuery = searchQuery.toLowerCase();
    return normalizedSkills.filter((skill) => {
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

  const selectedSkill = useMemo(
    () => skills.find((skill) => skill.id === selectedSkillId) ?? null,
    [selectedSkillId, skills],
  );

  const pagination = usePagination(filteredSkills, { pageSize: PAGE_SIZE });

  // Batch toggle all skills
  const handleBatchToggle = useCallback(
    async (enabled: boolean) => {
      try {
        const targetInstalls = enabled
          ? installs
          : installs.filter((install) => {
              const skill = skills.find((item) => item.id === install.skill_id);
              return !skill?.force_enabled;
            });
        if (targetInstalls.length === 0) {
          toast.message(
            t("library.skillsManager.toasts.noEligibleBatchToggle"),
          );
          return;
        }
        await Promise.all(
          targetInstalls.map((install) =>
            skillsService.updateInstall(install.id, { enabled }),
          ),
        );
        refresh();
      } catch (error) {
        console.error("[SkillsPageClient] Failed to batch toggle:", error);
        toast.error(t("library.skillsManager.toasts.actionFailed"));
      }
    },
    [installs, refresh, skills, t],
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
                displayMode="runtime"
                onInstall={installSkill}
                onDeleteSkill={deleteSkill}
                onOpenSkillSettings={(skill) => setSelectedSkillId(skill.id)}
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
      <SkillSettingsDialog
        skill={selectedSkill}
        skills={skills}
        open={selectedSkill !== null}
        onClose={() => setSelectedSkillId(null)}
        onSaved={refresh}
      />
    </>
  );
}
