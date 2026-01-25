"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import type { Skill, UserSkillInstall } from "@/features/skills/types";
import { skillsService } from "@/features/skills/services/skills-service";
import { useT } from "@/lib/i18n/client";
import { playMcpInstallSound } from "@/lib/utils/sound";

export interface SkillDisplayItem {
  skill: Skill;
  install?: UserSkillInstall;
}

export function useSkillCatalog() {
  const { t } = useT("translation");
  const [skills, setSkills] = useState<Skill[]>([]);
  const [installs, setInstalls] = useState<UserSkillInstall[]>([]);
  const [loadingId, setLoadingId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    try {
      const [skillsData, installsData] = await Promise.all([
        skillsService.listSkills(),
        skillsService.listInstalls(),
      ]);
      setSkills(skillsData);
      setInstalls(installsData);
    } catch (error) {
      console.error("[Skills] Failed to fetch data:", error);
      toast.error(
        t("library.skillsManager.toasts.loadError", "加载技能列表失败"),
      );
    } finally {
      setIsLoading(false);
    }
  }, [t]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const installSkill = useCallback(
    async (skillId: number) => {
      setLoadingId(skillId);
      try {
        const created = await skillsService.createInstall({
          skill_id: skillId,
          enabled: true,
        });
        setInstalls((prev) => [created, ...prev]);
        toast.success(
          t("library.skillsManager.toasts.installed", "技能已安装"),
        );
        playMcpInstallSound();
      } catch (error) {
        console.error("[Skills] install failed:", error);
        toast.error(
          t("library.skillsManager.toasts.actionError", "操作失败，请稍后再试"),
        );
      } finally {
        setLoadingId(null);
      }
    },
    [t],
  );

  const uninstallSkill = useCallback(
    async (installId: number) => {
      setLoadingId(installId);
      try {
        await skillsService.deleteInstall(installId);
        setInstalls((prev) => prev.filter((i) => i.id !== installId));
        toast.success(
          t("library.skillsManager.toasts.uninstalled", "技能已卸载"),
        );
      } catch (error) {
        console.error("[Skills] uninstall failed:", error);
        toast.error(
          t("library.skillsManager.toasts.actionError", "操作失败，请稍后再试"),
        );
      } finally {
        setLoadingId(null);
      }
    },
    [t],
  );

  const setEnabled = useCallback(
    async (installId: number, enabled: boolean) => {
      setLoadingId(installId);
      // Find skill name for toast message
      const install = installs.find((i) => i.id === installId);
      const skill = install
        ? skills.find((s) => s.id === install.skill_id)
        : null;
      const skillName =
        skill?.name || t("library.skillsManager.unknownSkill", "未知技能");

      // Optimistic update
      setInstalls((prev) =>
        prev.map((i) => (i.id === installId ? { ...i, enabled } : i)),
      );
      try {
        const updated = await skillsService.updateInstall(installId, {
          enabled,
        });
        setInstalls((prev) =>
          prev.map((i) => (i.id === installId ? updated : i)),
        );
        toast.success(
          enabled
            ? `${skillName} ${t("library.skillsManager.toasts.enabled", "已启用")}`
            : `${skillName} ${t("library.skillsManager.toasts.disabled", "已停用")}`,
        );
        if (enabled) {
          playMcpInstallSound();
        }
      } catch (error) {
        console.error("[Skills] setEnabled failed:", error);
        // Rollback
        setInstalls((prev) =>
          prev.map((i) =>
            i.id === installId ? { ...i, enabled: !enabled } : i,
          ),
        );
        toast.error(
          t("library.skillsManager.toasts.actionError", "操作失败，请稍后再试"),
        );
      } finally {
        setLoadingId(null);
      }
    },
    [t, installs, skills],
  );

  const items: SkillDisplayItem[] = useMemo(() => {
    return skills.map((skill) => ({
      skill,
      install: installs.find((i) => i.skill_id === skill.id),
    }));
  }, [skills, installs]);

  return {
    skills,
    installs,
    items,
    isLoading,
    loadingId,
    refresh,
    installSkill,
    uninstallSkill,
    setEnabled,
  };
}
