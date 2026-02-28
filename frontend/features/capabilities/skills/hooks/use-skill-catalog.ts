"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import type {
  Skill,
  UserSkillInstall,
} from "@/features/capabilities/skills/types";
import { skillsService } from "@/features/capabilities/skills/api/skills-api";
import { useT } from "@/lib/i18n/client";
import {
  getStartupPreloadPromise,
  getStartupPreloadValue,
  hasStartupPreloadValue,
  invalidateStartupPreloadValues,
} from "@/lib/startup-preload";
import { playInstallSound } from "@/lib/utils/sound";

export interface SkillDisplayItem {
  skill: Skill;
  install?: UserSkillInstall;
}

export function useSkillCatalog() {
  const { t } = useT("translation");
  const preloadSkills = getStartupPreloadValue("skills");
  const preloadInstalls = getStartupPreloadValue("skillInstalls");
  const hasPreloadedCatalog =
    hasStartupPreloadValue("skills") && hasStartupPreloadValue("skillInstalls");
  const [skills, setSkills] = useState<Skill[]>(
    hasPreloadedCatalog ? (preloadSkills ?? []) : [],
  );
  const [installs, setInstalls] = useState<UserSkillInstall[]>(
    hasPreloadedCatalog ? (preloadInstalls ?? []) : [],
  );
  const [loadingId, setLoadingId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(!hasPreloadedCatalog);

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
      toast.error(t("library.skillsManager.toasts.loadError"));
    } finally {
      setIsLoading(false);
    }
  }, [t]);

  useEffect(() => {
    let active = true;

    const refreshSilently = async () => {
      try {
        const [skillsData, installsData] = await Promise.all([
          skillsService.listSkills(),
          skillsService.listInstalls(),
        ]);
        if (!active) return;
        setSkills(skillsData);
        setInstalls(installsData);
      } catch (error) {
        // Keep preload data as fallback, avoid user-facing toast for background refresh.
        console.error("[Skills] Silent refresh failed:", error);
      }
    };

    const hydrateAndRefresh = async () => {
      const canUsePreload =
        hasStartupPreloadValue("skills") &&
        hasStartupPreloadValue("skillInstalls");
      if (canUsePreload) {
        setSkills(getStartupPreloadValue("skills") ?? []);
        setInstalls(getStartupPreloadValue("skillInstalls") ?? []);
        setIsLoading(false);
        void refreshSilently();
        return;
      }

      const preloadPromise = getStartupPreloadPromise();
      if (preloadPromise) {
        await preloadPromise;
        if (!active) return;

        const hasHydratedCatalog =
          hasStartupPreloadValue("skills") &&
          hasStartupPreloadValue("skillInstalls");
        if (hasHydratedCatalog) {
          setSkills(getStartupPreloadValue("skills") ?? []);
          setInstalls(getStartupPreloadValue("skillInstalls") ?? []);
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

  const installSkill = useCallback(
    async (skillId: number) => {
      setLoadingId(skillId);
      try {
        const created = await skillsService.createInstall({
          skill_id: skillId,
          enabled: true,
        });
        setInstalls((prev) => [created, ...prev]);
        toast.success(t("library.skillsManager.toasts.installed"));
        playInstallSound();
        invalidateStartupPreloadValues(["skillInstalls"]);
      } catch (error) {
        console.error("[Skills] install failed:", error);
        toast.error(t("library.skillsManager.toasts.actionError"));
      } finally {
        setLoadingId(null);
      }
    },
    [t],
  );

  const deleteSkill = useCallback(
    async (skillId: number) => {
      setLoadingId(skillId);
      try {
        await skillsService.deleteSkill(skillId);
        setSkills((prev) => prev.filter((skill) => skill.id !== skillId));
        setInstalls((prev) =>
          prev.filter((install) => install.skill_id !== skillId),
        );
        toast.success(t("common.deleted"));
        invalidateStartupPreloadValues(["skills", "skillInstalls"]);
      } catch (error) {
        console.error("[Skills] delete failed:", error);
        toast.error(t("library.skillsManager.toasts.actionError"));
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
      const skillName = skill?.name || t("library.skillsManager.unknownSkill");

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
            ? `${skillName} ${t("library.skillsManager.toasts.enabled")}`
            : `${skillName} ${t("library.skillsManager.toasts.disabled")}`,
        );
        if (enabled) {
          playInstallSound();
        }
        invalidateStartupPreloadValues(["skillInstalls"]);
      } catch (error) {
        console.error("[Skills] setEnabled failed:", error);
        // Rollback
        setInstalls((prev) =>
          prev.map((i) =>
            i.id === installId ? { ...i, enabled: !enabled } : i,
          ),
        );
        toast.error(t("library.skillsManager.toasts.actionError"));
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
    deleteSkill,
    setEnabled,
  };
}
