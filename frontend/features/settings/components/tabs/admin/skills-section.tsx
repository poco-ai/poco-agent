"use client";

import * as React from "react";

import { SkillsGrid } from "@/features/capabilities/skills/components/skills-grid";
import { SkillImportDialog } from "@/features/capabilities/skills/components/skill-import-dialog";
import { SkillSettingsDialog } from "@/features/capabilities/skills/components/skill-settings-dialog";
import type {
  Skill,
  SkillUpdateInput,
} from "@/features/capabilities/skills/types";
import { adminApi } from "@/features/settings/api/admin-api";
import { useT } from "@/lib/i18n/client";

import { AdminSectionError, AdminSectionLoading } from "./shared";
import { AdminCatalogShell } from "./admin-catalog-shell";

interface AdminSkillsSectionProps {
  isLoading: boolean;
  hasError: boolean;
  skills: Skill[];
  onRetry: () => void;
  onUpdate: (skillId: number, input: SkillUpdateInput) => Promise<void>;
  onDelete: (skillId: number) => Promise<void>;
}

export function AdminSkillsSection({
  isLoading,
  hasError,
  skills,
  onRetry,
  onUpdate,
  onDelete,
}: AdminSkillsSectionProps) {
  const { t } = useT("translation");
  const [searchQuery, setSearchQuery] = React.useState("");
  const [importOpen, setImportOpen] = React.useState(false);
  const [selectedSkillId, setSelectedSkillId] = React.useState<number | null>(
    null,
  );

  const filteredSkills = React.useMemo(() => {
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
        (skill.description || "").toLowerCase().includes(lowerQuery) ||
        repo.toLowerCase().includes(lowerQuery) ||
        filename.toLowerCase().includes(lowerQuery)
      );
    });
  }, [skills, searchQuery]);

  const selectedSkill = React.useMemo(
    () => skills.find((skill) => skill.id === selectedSkillId) ?? null,
    [selectedSkillId, skills],
  );

  return (
    <>
      <AdminCatalogShell
        title={t("settings.admin.skillsTitle")}
        description={t("settings.admin.skillsDescription")}
        summary={`${t("settings.admin.skillsTitle")} · ${filteredSkills.length}`}
        searchValue={searchQuery}
        onSearchChange={setSearchQuery}
        searchPlaceholder={t("library.skillsPage.searchPlaceholder")}
      >
        {isLoading ? <AdminSectionLoading /> : null}
        {hasError ? <AdminSectionError onRetry={onRetry} /> : null}
        <div
          className={
            isLoading || hasError ? "pointer-events-none opacity-60" : undefined
          }
        >
          <SkillsGrid
            skills={filteredSkills}
            installs={[]}
            isLoading={isLoading}
            displayMode="admin"
            onOpenSkillSettings={(skill) => setSelectedSkillId(skill.id)}
            onDeleteSkill={(skillId) => void onDelete(skillId)}
            createCardLabel={t("library.skillsPage.addCard")}
            onCreate={() => setImportOpen(true)}
          />
        </div>
      </AdminCatalogShell>

      <SkillImportDialog
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onImported={async () => {
          setImportOpen(false);
          await onRetry();
        }}
        importApi={{
          discover: adminApi.importSystemSkillDiscover,
          commit: adminApi.importSystemSkillCommit,
          getJob: adminApi.getSystemSkillImportJob,
        }}
      />

      <SkillSettingsDialog
        skill={selectedSkill}
        skills={skills}
        open={selectedSkill !== null}
        onClose={() => setSelectedSkillId(null)}
        onSaveSkill={onUpdate}
        allowSystemEdit
        showPolicyControls
      />
    </>
  );
}
